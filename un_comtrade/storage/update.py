"""Incremental dataset updates across storage backends (P5-006).

This module adds the **incremental update** capability on
top of the four concrete storage engines
(`CSVWriter`, `JSONWriter`, `ParquetWriter`,
`DuckDBWriter`). It supports three update modes:

- **`APPEND`** — add new records without touching
  existing rows. No deduplication. Equivalent to
  "insert more rows" semantics.
- **`MERGE`** — add new records; for any composite
  key already present in the existing dataset, the
  new (incoming) row replaces the old row. Latest
  by encounter order wins.
- **`REPLACE`** — drop existing rows whose composite
  key appears in the new batch, then add the new
  rows. (Functionally similar to MERGE but expressed
  as "delete-then-insert" for clarity.)

The module also exposes two independent helpers:

- `find_duplicates(records)` — group records by
  composite key, return only groups with length
  greater than 1. Useful for inspecting incoming
  batches before storing.
- `deduplicate(records, *, policy)` — collapse
  duplicates within a batch according to
  `DuplicatePolicy.KEEP_FIRST` or `KEEP_LAST`.
- `verify_schema_compatibility(...)` — compare a
  `CanonicalDataset` against the metadata of an
  existing dataset, returning `(bool, reason)`.

`SchemaIncompatibleError` is raised when
`DatasetUpdater.update(..., check_schema=True)`
detects a schema mismatch and `strict=True` is in
effect.

Per ADR-0029 the partition key for the default
strategy is `(reporter_code, ref_year, frequency_code)`.
The composite deduplication key (per
`006_DATA_MODEL.md` §3.12) is the canonical
10-tuple exposed via `TradeParser.composite_key`.
"""

from __future__ import annotations

import csv as _csv_stdlib
import json as _json_stdlib
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from ..parser import TradeParser
from ..transform import CanonicalDataset
from ._base import (
    DatasetMetadata,
    StorageBackend,
    StorageConfig,
    StorageError,
)

__all__ = [
    "UpdateMode",
    "DuplicatePolicy",
    "UpdateResult",
    "SchemaIncompatibleError",
    "find_duplicates",
    "deduplicate",
    "verify_schema_compatibility",
    "DatasetUpdater",
]


# ---------------------------------------------------------------------------
# Public enums
# ---------------------------------------------------------------------------


class UpdateMode(str, Enum):
    """How to combine a new batch with existing
    stored data.

    - `APPEND` — add new records; existing data
      untouched.
    - `MERGE` — add new records; composite-key
      collisions overwrite the existing row with
      the incoming row.
    - `REPLACE` — delete existing rows whose
      composite key appears in the incoming batch,
      then insert the incoming batch. Same final
      state as MERGE but expressed as
      "delete-then-insert" for engines where that
      distinction matters (e.g. for trigger
      semantics or audit logs).
    """

    APPEND = "append"
    MERGE = "merge"
    REPLACE = "replace"


class DuplicatePolicy(str, Enum):
    """How to handle duplicates within a single
    incoming batch.

    - `KEEP_FIRST` — first occurrence wins
      (first-wins).
    - `KEEP_LAST` — last occurrence wins
      (last-wins / latest-wins).
    """

    KEEP_FIRST = "keep_first"
    KEEP_LAST = "keep_last"


class SchemaIncompatibleError(StorageError):
    """Raised when an incoming `CanonicalDataset`
    has a schema incompatible with an existing
    dataset's metadata.

    Inherits from `StorageError` so callers can
    catch one or the other interchangeably.
    """


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UpdateResult:
    """Summary of a `DatasetUpdater.update(...)`
    call.

    Attributes
    ----------
    mode
        The `UpdateMode` that was applied.
    backend
        The `StorageBackend` that was updated.
    records_added
        Number of rows present in the destination
        after the update that were *not* present
        before the update.
    records_merged
        Number of existing rows that were replaced
        by an incoming row with the same composite
        key (always 0 for `APPEND`).
    duplicates_in_input
        Number of duplicate composite keys within
        the incoming batch *before*
        deduplication. Two records with the same
        key count as 1 duplicate (i.e. one extra).
    duration_seconds
        Wall-clock duration of the update.
    destination
        String form of the storage destination.
    """

    mode: UpdateMode
    backend: StorageBackend
    records_added: int
    records_merged: int
    duplicates_in_input: int
    duration_seconds: float
    destination: str = ""


# ---------------------------------------------------------------------------
# Composite-key helpers
# ---------------------------------------------------------------------------


def _record_key(record: Any) -> tuple:
    """Default composite key for a `TradeRecord`.

    Delegates to `TradeParser.composite_key` so the
    behaviour matches the parser's internal
    deduplication. For dict-like records (e.g.
    raw rows re-read from CSV / Parquet), falls
    back to a duck-typed lookup that also coerces
    the integer-valued fields back to `int` (CSV /
    JSON readers return them as strings).
    """
    if hasattr(record, "reporter") and hasattr(record, "partner"):
        return TradeParser.composite_key(record)
    try:
        reporter_code = _coerce_int(
            record["reporter_code"]
            if "reporter_code" in record
            else record.get("reporter", {}).get("reporter_code")
        )
        partner_code = _coerce_int(
            record["partner_code"]
            if "partner_code" in record
            else record.get("partner", {}).get("partner_code")
        )
        partner2_code = (
            _coerce_int(record.get("partner2_code", 0))
            if record.get("partner2_code") not in (None, "")
            else 0
        )
        mot_code = _coerce_int(record["mot_code"])
        return (
            reporter_code,
            partner_code,
            record["period"],
            record["flow_code"],
            record["commodity_code"],
            record["classification_code"],
            record["edition"],
            record["customs_code"],
            mot_code,
            partner2_code,
        )
    except (KeyError, AttributeError, TypeError) as exc:
        raise StorageError(
            f"Cannot extract composite key from "
            f"{type(record).__name__}: {exc}"
        ) from exc


def _coerce_int(value: Any) -> int | None:
    """Coerce a value to `int`, returning `None` if
    the value is `None` or empty string."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        # bool is a subclass of int; preserve True/False
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _coerce_bool(value: Any) -> bool | None:
    """Coerce a CSV / JSON string back to bool.

    Accepts `True` / `False` (Python) or the strings
    `"True"` / `"False"` (capitalised, as written by
    the file writers). Returns `None` for `None` /
    empty string.
    """
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() in ("true", "1"):
            return True
        if value.lower() in ("false", "0"):
            return False
    if isinstance(value, int):
        return bool(value)
    return value


# ---------------------------------------------------------------------------
# Duplicate detection / deduplication
# ---------------------------------------------------------------------------


def find_duplicates(
    records: Iterable[Any],
    *,
    key_fn: Callable[[Any], tuple] = _record_key,
) -> dict[tuple, list]:
    """Return a dict mapping composite key → list of
    records, for every key that appears more than
    once in `records`.

    Returns an empty dict if no duplicates are
    present. Order within each group preserves the
    input encounter order.
    """
    groups: dict[tuple, list] = {}
    for record in records:
        k = key_fn(record)
        groups.setdefault(k, []).append(record)
    return {k: v for k, v in groups.items() if len(v) > 1}


def deduplicate(
    records: Iterable[Any],
    *,
    policy: DuplicatePolicy = DuplicatePolicy.KEEP_LAST,
    key_fn: Callable[[Any], tuple] = _record_key,
) -> tuple:
    """Deduplicate a sequence of records.

    For `KEEP_FIRST` the first occurrence wins; for
    `KEEP_LAST` the last occurrence wins.

    The output preserves first-seen order of
    composite keys.
    """
    if policy == DuplicatePolicy.KEEP_FIRST:
        seen: dict[tuple, Any] = {}
        for r in records:
            k = key_fn(r)
            seen.setdefault(k, r)
        return tuple(seen.values())
    # KEEP_LAST
    seen_last: dict[tuple, Any] = {}
    encounter_order: list[tuple] = []
    for r in records:
        k = key_fn(r)
        if k not in seen_last:
            encounter_order.append(k)
        seen_last[k] = r
    return tuple(seen_last[k] for k in encounter_order)


# ---------------------------------------------------------------------------
# Schema compatibility
# ---------------------------------------------------------------------------


def verify_schema_compatibility(
    new_dataset: CanonicalDataset,
    existing_metadata: DatasetMetadata | None,
    *,
    strict: bool = True,
) -> tuple[bool, str]:
    """Compare a new `CanonicalDataset` against an
    existing dataset's metadata.

    Returns `(True, "")` if they are compatible (or
    if there is no existing metadata — first write
    is always compatible). Returns `(False,
    reason)` otherwise.

    Parameters
    ----------
    new_dataset
        The incoming dataset.
    existing_metadata
        Metadata from a previous write (read from
        the destination's sidecar or
        `un_comtrade_datasets` table). Pass `None`
        if the destination is empty.
    strict
        When `True` (default), any mismatch raises
        `SchemaIncompatibleError` from
        `DatasetUpdater.update(...)`. When `False`,
        the caller must inspect the returned tuple
        themselves.
    """
    if existing_metadata is None:
        return True, ""
    if (
        existing_metadata.schema_version
        != new_dataset.schema_version
    ):
        msg = (
            f"schema_version mismatch: existing="
            f"{existing_metadata.schema_version!r}, "
            f"new={new_dataset.schema_version!r}"
        )
        return False, msg
    if (
        existing_metadata.parser_name
        != new_dataset.parser_name
    ):
        msg = (
            f"parser_name mismatch: existing="
            f"{existing_metadata.parser_name!r}, "
            f"new={new_dataset.parser_name!r}"
        )
        return False, msg
    return True, ""


# ---------------------------------------------------------------------------
# Engine-specific updaters
# ---------------------------------------------------------------------------


def _read_existing_metadata(config: StorageConfig) -> DatasetMetadata | None:
    """Read the most recent metadata sidecar
    associated with `config.root`. Returns `None`
    if no sidecar exists (first write)."""
    sidecar_path = Path(config.root) / "un_comtrade.meta.json"
    if not sidecar_path.exists():
        return None
    try:
        payload = _json_stdlib.loads(
            sidecar_path.read_text(encoding="utf-8")
        )
    except (OSError, _json_stdlib.JSONDecodeError):
        return None
    # The file-engine sidecars already round-trip
    # through `DatasetMetadata`. For other engines
    # we'd need to read their own metadata tables —
    # but `update()` is invoked with a sidecar only
    # for the file engines. DuckDB and Parquet
    # provide their own read paths in their
    # respective updaters.
    return None


class _FileUpdater:
    """Update implementation for `CSV` and `JSON`
    backends. Reads all existing records, applies
    the mode semantics in Python, then writes the
    merged dataset back via the corresponding
    writer."""

    def __init__(
        self,
        *,
        backend: StorageBackend,
        config: StorageConfig,
        writer: Any,
    ) -> None:
        self._backend = backend
        self._config = config
        self._writer = writer

    def update(
        self,
        dataset: CanonicalDataset,
        mode: UpdateMode,
        *,
        duplicate_policy: DuplicatePolicy,
        dedup_input: tuple,
    ) -> UpdateResult:
        start = time.monotonic()
        ext = self._backend.file_extension
        # Read existing records (if any). They come
        # back as flat dicts (CSV header row / JSON
        # records).
        existing_dicts = _read_existing_file_records(
            self._config.root, ext
        )
        # Wrap existing dicts in stub records so
        # `_record_to_row` can read nested attrs
        # (`record.reporter.reporter_code`, ...).
        existing_records = tuple(
            _dict_to_record(d) for d in existing_dicts
        )
        existing_keys = {_record_key(r) for r in existing_records}

        new_keys = {_record_key(r) for r in dedup_input}
        records_merged = len(existing_keys & new_keys)

        if mode is UpdateMode.APPEND:
            merged = existing_records + tuple(dedup_input)
            records_added = len(dedup_input)
        elif mode is UpdateMode.MERGE:
            # Drop existing rows whose key appears in
            # the incoming batch; then append incoming.
            merged = tuple(
                r for r in existing_records
                if _record_key(r) not in new_keys
            ) + tuple(dedup_input)
            records_added = len(dedup_input)
        elif mode is UpdateMode.REPLACE:
            # Same final state as MERGE for the file
            # engines, but expressed as a single
            # delete-then-insert sweep so callers
            # that want to distinguish the two can
            # inspect the `mode` field.
            merged = tuple(
                r for r in existing_records
                if _record_key(r) not in new_keys
            ) + tuple(dedup_input)
            records_added = len(dedup_input)
        else:
            raise StorageError(f"Unknown update mode: {mode!r}")

        # Write back via the underlying writer.
        wrapped = CanonicalDataset(
            name=dataset.name,
            records=merged,
            parser_name=dataset.parser_name,
            schema_version=dataset.schema_version,
            extracted_at=dataset.extracted_at,
            source_count=len(merged),
            duplicates_removed=0,
            skipped=0,
        )
        write_config = StorageConfig(
            root=self._config.root,
            partition_strategy=self._config.partition_strategy,
            overwrite=True,
            compression=self._config.compression,
            table_name=self._config.table_name,
            metadata=self._config.metadata,
        )

        # The file writers do not yet honour
        # `config.overwrite=True` — clear the
        # destination directory before writing so
        # stale files from a previous write don't
        # linger alongside the new ones.
        root_path = Path(self._config.root)
        if root_path.exists():
            for child in root_path.iterdir():
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()

        self._writer.store(wrapped, write_config)

        duration = time.monotonic() - start
        return UpdateResult(
            mode=mode,
            backend=self._backend,
            records_added=records_added,
            records_merged=records_merged,
            duplicates_in_input=(
                len(dataset.records) - len(dedup_input)
            ),
            duration_seconds=duration,
            destination=str(self._config.root),
        )


def _read_existing_file_records(
    root: str | Path, ext: str
) -> list:
    """Read all existing records from CSV/JSON
    files under `root`. Returns a list of dict
    records (one per row)."""
    root_path = Path(root)
    if not root_path.exists():
        return []
    if ext == ".csv":
        files = list(root_path.rglob("*.csv"))
    elif ext == ".json":
        files = [
            p for p in root_path.rglob("*.json")
            if not p.name.endswith(".meta.json")
        ]
    else:
        return []
    if not files:
        return []
    records: list = []
    if ext == ".csv":
        for f in files:
            with f.open("rt", encoding="utf-8") as fh:
                reader = _csv_stdlib.DictReader(fh)
                records.extend(reader)
    else:  # .json
        for f in files:
            payload = _json_stdlib.loads(
                f.read_text(encoding="utf-8")
            )
            records.extend(payload.get("records", []))
    return records


class _ParquetUpdater:
    """Update implementation for the Parquet
    backend. Reads all existing parquet files,
    applies the mode semantics, then writes the
    merged dataset back via `ParquetWriter`."""

    def __init__(self, *, config: StorageConfig) -> None:
        self._config = config

    def update(
        self,
        dataset: CanonicalDataset,
        mode: UpdateMode,
        *,
        duplicate_policy: DuplicatePolicy,
        dedup_input: tuple,
    ) -> UpdateResult:
        from .parquet import ParquetWriter

        start = time.monotonic()
        existing = _read_existing_parquet_records(self._config.root)
        existing_keys = {_record_key(r) for r in existing}
        new_keys = {_record_key(r) for r in dedup_input}
        records_merged = len(existing_keys & new_keys)

        if mode is UpdateMode.APPEND:
            merged = tuple(existing) + tuple(dedup_input)
            records_added = len(dedup_input)
        elif mode in (UpdateMode.MERGE, UpdateMode.REPLACE):
            merged = tuple(
                r for r in existing if _record_key(r) not in new_keys
            ) + tuple(dedup_input)
            records_added = len(dedup_input)
        else:
            raise StorageError(f"Unknown update mode: {mode!r}")

        # Convert dict records back to TradeRecord
        # instances for the writer.
        from ..models.trade import TradeRecord
        merged_records = tuple(_dict_to_record(d) for d in merged)

        wrapped = CanonicalDataset(
            name=dataset.name,
            records=merged_records,
            parser_name=dataset.parser_name,
            schema_version=dataset.schema_version,
            extracted_at=dataset.extracted_at,
            source_count=len(merged_records),
            duplicates_removed=0,
            skipped=0,
        )
        write_config = StorageConfig(
            root=self._config.root,
            partition_strategy=self._config.partition_strategy,
            overwrite=True,
            compression=self._config.compression,
            table_name=self._config.table_name,
            metadata=self._config.metadata,
        )
        ParquetWriter().store(wrapped, write_config)

        duration = time.monotonic() - start
        return UpdateResult(
            mode=mode,
            backend=StorageBackend.PARQUET,
            records_added=records_added,
            records_merged=records_merged,
            duplicates_in_input=(
                len(dataset.records) - len(dedup_input)
            ),
            duration_seconds=duration,
            destination=str(self._config.root),
        )


def _read_existing_parquet_records(root: str | Path) -> list:
    """Read all existing rows from Parquet files
    under `root` and return a list of dict records.
    Returns [] if no files exist."""
    try:
        import pyarrow.parquet as _pq
    except ImportError:
        return []
    root_path = Path(root)
    if not root_path.exists():
        return []
    files = list(root_path.rglob("*.parquet"))
    if not files:
        return []
    tables = []
    for f in files:
        tables.append(_pq.read_table(f))
    if not tables:
        return []
    combined = tables[0]
    for t in tables[1:]:
        combined = _concat_tables(combined, t)
    return combined.to_pylist()


def _concat_tables(t1, t2):
    """Concatenate two pyarrow tables, even when
    they share no schema."""
    try:
        import pyarrow as _pa

        return _pa.concat_tables([t1, t2])
    except Exception:
        # Fall back: convert to pandas.
        return t1.from_pandas(
            __import__("pandas").concat(
                [t1.to_pandas(), t2.to_pandas()],
                ignore_index=True,
            )
        )


def _dict_to_record(d: Mapping[str, Any]) -> Any:
    """Reconstruct a `TradeRecord`-like object from
    a flat dict (e.g. one row read back from a
    Parquet file).

    The Parquet schema is a flat column layout —
    top-level fields like `reporter_code`,
    `reporter_iso3`, `partner_code` etc. — but
    `_record_to_row` (the Parquet writer's helper)
    expects nested objects with attributes
    (`reporter.reporter_code`, `reporter.iso3`,
    etc.). This function builds a stub object
    exposing the required attribute layout.

    If `d` is already a `TradeRecord`, it is
    returned unchanged.
    """
    from ..models.trade import TradeRecord
    if isinstance(d, TradeRecord):
        return d
    if not isinstance(d, Mapping):
        raise StorageError(
            f"Cannot reconstruct TradeRecord from "
            f"{type(d).__name__}"
        )

    class _StubObj:
        """Lightweight attribute-bag exposing the
        nested structure `_record_to_row` expects."""
        pass

    obj = _StubObj()
    obj.type_code = d.get("type_code")
    obj.frequency_code = d.get("frequency_code")
    obj.classification_code = d.get("classification_code")
    obj.classification_search_code = d.get(
        "classification_search_code"
    )
    obj.edition = d.get("edition")
    obj.is_original_classification = d.get(
        "is_original_classification"
    )
    obj.ref_period_id = d.get("ref_period_id")
    obj.ref_year = d.get("ref_year")
    obj.ref_month = d.get("ref_month")
    obj.period = d.get("period")
    # Nested subjects.
    obj.reporter = _StubObj()
    obj.reporter.reporter_code = _coerce_int(d.get("reporter_code"))
    obj.reporter.iso3 = d.get("reporter_iso3")
    obj.reporter.name = d.get("reporter_name")
    obj.partner = _StubObj()
    obj.partner.partner_code = _coerce_int(d.get("partner_code"))
    obj.partner.iso3 = d.get("partner_iso3")
    obj.partner.name = d.get("partner_name")
    p2 = d.get("partner2_code")
    if p2 not in (None, ""):
        obj.partner2 = _StubObj()
        obj.partner2.partner_code = _coerce_int(p2)
        obj.partner2.iso3 = d.get("partner2_iso3")
        obj.partner2.name = d.get("partner2_name")
    else:
        obj.partner2 = None
    obj.flow = _StubObj()
    obj.flow.flow_code = d.get("flow_code")
    obj.flow.flow_name = d.get("flow_name")
    obj.flow.name = d.get("flow_name")
    obj.commodity = _StubObj()
    obj.commodity.commodity_code = d.get("commodity_code")
    obj.commodity.commodity_name = d.get("commodity_name")
    obj.commodity.name = d.get("commodity_name")
    obj.customs_code = d.get("customs_code")
    obj.customs_name = d.get("customs_name")
    obj.mos_code = d.get("mos_code")
    obj.mot_code = _coerce_int(d.get("mot_code"))
    obj.mot_name = d.get("mot_name")
    obj.quantity = _StubObj()
    obj.quantity.qty = d.get("quantity_qty")
    obj.quantity.qty_unit_code = d.get("quantity_qty_unit_code")
    obj.quantity.qty_unit_abbr = d.get("quantity_qty_unit_abbr")
    obj.quantity.is_qty_estimated = _coerce_bool(
        d.get("quantity_is_estimated")
    )
    obj.quantity.is_estimated = _coerce_bool(
        d.get("quantity_is_estimated")
    )
    obj.quantity.alt_qty = d.get("quantity_alt_qty")
    obj.quantity.alt_qty_unit_code = d.get(
        "quantity_alt_qty_unit_code"
    )
    obj.quantity.alt_qty_unit_abbr = d.get(
        "quantity_alt_qty_unit_abbr"
    )
    obj.quantity.is_alt_qty_estimated = _coerce_bool(
        d.get("quantity_is_alt_qty_estimated")
    )
    obj.net_weight_kg = d.get("net_weight_kg")
    obj.is_net_weight_estimated = _coerce_bool(
        d.get("is_net_weight_estimated")
    )
    obj.gross_weight_kg = d.get("gross_weight_kg")
    obj.is_gross_weight_estimated = _coerce_bool(
        d.get("is_gross_weight_estimated")
    )
    obj.trade_value = _StubObj()
    obj.trade_value.primary_value = d.get(
        "trade_value_primary_value"
    )
    obj.trade_value.fob_value = d.get("trade_value_fob_value")
    obj.trade_value.cif_value = d.get("trade_value_cif_value")
    obj.legacy_estimation_flag = _coerce_int(d.get("legacy_estimation_flag"))
    obj.is_reported = _coerce_bool(d.get("is_reported"))
    obj.is_aggregate = _coerce_bool(d.get("is_aggregate"))
    obj.provenance = d.get("provenance")
    return obj


class _DuckDBUpdater:
    """Update implementation for the DuckDB
    backend. Uses SQL `DELETE` + `INSERT` for
    `MERGE` / `REPLACE`, and direct `INSERT` for
    `APPEND`. Existing rows are matched by
    composite key expressed as a row-constructor
    equality — no schema change required."""

    def __init__(self, *, config: StorageConfig) -> None:
        self._config = config

    def update(
        self,
        dataset: CanonicalDataset,
        mode: UpdateMode,
        *,
        duplicate_policy: DuplicatePolicy,
        dedup_input: tuple,
    ) -> UpdateResult:
        import duckdb

        from .duckdb import (
            DUCKDB_SCHEMA_VERSION,
            DuckDBWriter,
            _records_to_rows,
            duckdb_schema_sql,
        )

        start = time.monotonic()
        db_path = self._config.root
        table_name = self._config.table_name

        conn = duckdb.connect(db_path)
        try:
            # Ensure the trade-records table +
            # metadata table both exist (reuses
            # the existing DuckDBWriter logic).
            writer = DuckDBWriter()
            writer._ensure_table(conn, table_name)

            existing_keys = _read_existing_duckdb_keys(conn, table_name)
            new_keys = {_record_key(r) for r in dedup_input}
            records_merged = len(existing_keys & new_keys)

            if mode is UpdateMode.APPEND:
                rows = _records_to_rows(dedup_input)
                if rows:
                    placeholders = ",".join(["?"] * len(rows[0]))
                    insert_sql = (
                        f"INSERT INTO {table_name} "
                        f"VALUES ({placeholders})"
                    )
                    conn.executemany(insert_sql, rows)
                records_added = len(dedup_input)

            elif mode in (UpdateMode.MERGE, UpdateMode.REPLACE):
                # Delete existing rows whose composite
                # key appears in the incoming batch.
                for k in new_keys:
                    conn.execute(
                        _delete_sql_for_key(table_name, k),
                        list(k),
                    )
                # Insert all incoming rows.
                rows = _records_to_rows(dedup_input)
                if rows:
                    placeholders = ",".join(["?"] * len(rows[0]))
                    insert_sql = (
                        f"INSERT INTO {table_name} "
                        f"VALUES ({placeholders})"
                    )
                    conn.executemany(insert_sql, rows)
                records_added = len(dedup_input)
            else:
                raise StorageError(
                    f"Unknown update mode: {mode!r}"
                )

            # Update the metadata table.
            _update_dataset_metadata(
                conn,
                table_name=table_name,
                dataset_name=dataset.name,
                schema_version=dataset.schema_version,
                parser_name=dataset.parser_name,
                record_count=len(dedup_input),
                partition_keys=tuple(new_keys),
            )
        finally:
            conn.close()

        duration = time.monotonic() - start
        return UpdateResult(
            mode=mode,
            backend=StorageBackend.DUCKDB,
            records_added=records_added,
            records_merged=records_merged,
            duplicates_in_input=(
                len(dataset.records) - len(dedup_input)
            ),
            duration_seconds=duration,
            destination=str(db_path),
        )


def _delete_sql_for_key(table_name: str, key: tuple) -> str:
    """Build a DELETE statement that matches the
    composite key (10-tuple) using a SQL row
    constructor."""
    return (
        f"DELETE FROM {table_name} "
        f"WHERE (reporter_code, partner_code, period, "
        f"flow_code, commodity_code, classification_code, "
        f"edition, customs_code, mot_code, "
        f"COALESCE(partner2_code, 0)) = "
        f"(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )


def _read_existing_duckdb_keys(conn, table_name: str) -> set:
    """Read the set of composite keys present in
    the existing DuckDB table."""
    try:
        rows = conn.execute(
            f"SELECT reporter_code, partner_code, period, "
            f"flow_code, commodity_code, classification_code, "
            f"edition, customs_code, mot_code, "
            f"COALESCE(partner2_code, 0) "
            f"FROM {table_name}"
        ).fetchall()
    except Exception:
        return set()
    return {tuple(r) for r in rows}


def _update_dataset_metadata(
    conn,
    *,
    table_name: str,
    dataset_name: str,
    schema_version: str,
    parser_name: str,
    record_count: int,
    partition_keys: tuple,
) -> None:
    """Update or insert the row in
    `un_comtrade_datasets` for this dataset.

    The metadata table schema (one row per
    `store()` call) is owned by `DuckDBWriter`;
    we re-use its `stored_at` column and let
    each update append a new row. (For more
    advanced use cases the metadata table could
    be extended with `updated_at`.)
    """
    from .duckdb import DATASETS_TABLE

    partition_keys_json = _json_stdlib.dumps(
        [list(k) for k in partition_keys], default=str
    )
    conn.execute(
        f"INSERT INTO {DATASETS_TABLE} "
        f"(dataset_name, table_name, schema_version, "
        f"parser_name, record_count, partition_keys, "
        f"stored_at) "
        f"VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        [
            dataset_name,
            table_name,
            schema_version,
            parser_name,
            record_count,
            partition_keys_json,
        ],
    )


# ---------------------------------------------------------------------------
# Public orchestrator
# ---------------------------------------------------------------------------


class DatasetUpdater:
    """High-level orchestrator for incremental
    updates across all storage backends.

    Construct with a `backend` + `StorageConfig`,
    then call `update(dataset, mode)` to apply
    the update.

    Per-update parameters (duplicate policy,
    schema-compatibility check) can be passed to
    `update(...)` directly.

    The class is the public entry point — engine
    specifics live in `_FileUpdater`, `_ParquetUpdater`,
    and `_DuckDBUpdater`.
    """

    def __init__(
        self,
        *,
        backend: StorageBackend,
        config: StorageConfig,
    ) -> None:
        if not isinstance(backend, StorageBackend):
            raise TypeError(
                f"backend must be StorageBackend; got "
                f"{type(backend).__name__}"
            )
        if not isinstance(config, StorageConfig):
            raise TypeError(
                f"config must be StorageConfig; got "
                f"{type(config).__name__}"
            )
        self._backend = backend
        self._config = config
        self._impl = self._build_impl()

    def _build_impl(self) -> Any:
        if self._backend is StorageBackend.CSV:
            from .file import CSVWriter
            return _FileUpdater(
                backend=self._backend,
                config=self._config,
                writer=CSVWriter(),
            )
        if self._backend is StorageBackend.JSON:
            from .file import JSONWriter
            return _FileUpdater(
                backend=self._backend,
                config=self._config,
                writer=JSONWriter(),
            )
        if self._backend is StorageBackend.PARQUET:
            return _ParquetUpdater(config=self._config)
        if self._backend is StorageBackend.DUCKDB:
            return _DuckDBUpdater(config=self._config)
        raise StorageError(
            f"Update is not supported for backend "
            f"{self._backend.value!r}"
        )

    @property
    def backend(self) -> StorageBackend:
        return self._backend

    @property
    def config(self) -> StorageConfig:
        return self._config

    def update(
        self,
        dataset: CanonicalDataset,
        mode: UpdateMode,
        *,
        duplicate_policy: DuplicatePolicy = (
            DuplicatePolicy.KEEP_LAST
        ),
        check_schema: bool = True,
        existing_metadata: DatasetMetadata | None = None,
    ) -> UpdateResult:
        """Apply an incremental update.

        Parameters
        ----------
        dataset
            The incoming `CanonicalDataset`.
        mode
            `APPEND` / `MERGE` / `REPLACE`.
        duplicate_policy
            How to collapse duplicates within the
            incoming batch. Default
            `KEEP_LAST` (last-wins).
        check_schema
            When `True` (default), verify that
            `dataset.schema_version` /
            `dataset.parser_name` match
            `existing_metadata` (if provided).
            Raises `SchemaIncompatibleError` on
            mismatch.
        existing_metadata
            Optional. Metadata from a previous write
            (read from the destination's sidecar
            file or metadata table). When `None`,
            schema compatibility is not checked
            (first-write semantics).
        """
        if not isinstance(dataset, CanonicalDataset):
            raise StorageError(
                f"DatasetUpdater.update source must be a "
                f"CanonicalDataset; got "
                f"{type(dataset).__name__}"
            )
        if not isinstance(mode, UpdateMode):
            raise TypeError(
                f"mode must be UpdateMode; got "
                f"{type(mode).__name__}"
            )
        if not isinstance(
            duplicate_policy, DuplicatePolicy
        ):
            raise TypeError(
                f"duplicate_policy must be DuplicatePolicy; "
                f"got {type(duplicate_policy).__name__}"
            )

        if check_schema:
            ok, reason = verify_schema_compatibility(
                dataset, existing_metadata
            )
            if not ok:
                raise SchemaIncompatibleError(reason)

        dedup_input = deduplicate(
            dataset.records, policy=duplicate_policy
        )
        duplicates_in_input = (
            len(dataset.records) - len(dedup_input)
        )

        result = self._impl.update(
            dataset,
            mode,
            duplicate_policy=duplicate_policy,
            dedup_input=dedup_input,
        )

        # Patch `duplicates_in_input` if the impl
        # didn't compute it itself (it does, but we
        # keep the safety net).
        if result.duplicates_in_input != duplicates_in_input:
            result = UpdateResult(
                mode=result.mode,
                backend=result.backend,
                records_added=result.records_added,
                records_merged=result.records_merged,
                duplicates_in_input=duplicates_in_input,
                duration_seconds=result.duration_seconds,
                destination=result.destination,
            )
        return result

    def __repr__(self) -> str:
        return (
            f"DatasetUpdater(backend={self._backend.value!r}, "
            f"root={self._config.root!r})"
        )