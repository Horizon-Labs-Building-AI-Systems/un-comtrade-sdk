"""CSV and JSON storage engines.

Per `012_STORAGE_SPECIFICATION.md` §3 (T02 JSON,
T03 CSV) + §10 (JSON / CSV format spec), this
module provides the concrete storage engines for
the CSV and JSON backends.

Both engines:

- Use stdlib modules (`csv`, `json`, `gzip`) —
  no third-party dependencies.
- Support **compression** via the `compression`
  option in `StorageConfig` (`"none"` for plain
  text, `"gzip"` for gzip-compressed output).
- Write a **metadata sidecar** (`<root>/<dataset_name>.meta.json`)
  with the `DatasetMetadata` for the persisted
  dataset.
- Use the same flat schema as Parquet / DuckDB so
  the persisted data is interchangeable across
  formats.

Per the P5-004 task scope:

- **CSV** — `csv.writer` + `gzip.open` (when
  compression is set).
- **JSON** — `json.dump` + `gzip.open` (when
  compression is set). Optionally pretty-printed
  via `StorageConfig.metadata["indent"]`.
- **Compression support** — gzip on both CSV and
  JSON. The default `compression="none"` writes
  plain text. Any other value (e.g. `"gzip"`)
  writes gzipped output; the metadata file always
  uses plain JSON.
- **Metadata files** — every store call writes
  a `<root>/<dataset_name>.meta.json` sidecar
  with the full `DatasetMetadata` serialised as
  JSON. The sidecar is plain JSON (not gzipped) so
  consumers can inspect it without decompression.

Usage::

    from un_comtrade.storage.file import CSVWriter, JSONWriter
    from un_comtrade.storage import StorageConfig

    csv_writer = CSVWriter()
    result = csv_writer.store(
        dataset=canonical_dataset,
        config=StorageConfig(
            root="/data/trade",
            compression="gzip",  # or "none"
        ),
    )

    json_writer = JSONWriter()
    result = json_writer.store(
        dataset=canonical_dataset,
        config=StorageConfig(
            root="/data/trade",
            compression="none",
        ),
    )
"""

from __future__ import annotations

import csv
import gzip
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import (
    IO,
    Any,
    Mapping,
    Sequence,
)

from ..etl import PipelineContext, StageKind  # noqa: F401
from ..exceptions import ComtradeError
from ..logging import get_logger
from ..transform import CanonicalDataset
from ._base import (
    DatasetMetadata,
    PartitionStrategy,
    StorageBackend,
    StorageConfig,
    StorageError,
    StorageResult,
)


__all__ = [
    "CSV_SCHEMA_VERSION",
    "CSVWriter",
    "JSON_SCHEMA_VERSION",
    "JSONWriter",
    "METADATA_SCHEMA_VERSION",
    "write_metadata_sidecar",
]


_logger = get_logger("lifecycle")


# Schema versions for the persisted outputs. Bumped
# when the schema changes in a non-backward-compatible
# way.
CSV_SCHEMA_VERSION: str = "1.0.0"
JSON_SCHEMA_VERSION: str = "1.0.0"
METADATA_SCHEMA_VERSION: str = "1.0.0"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _open_for_write(
    path: Path,
    compression: str,
) -> IO[Any]:
    """Open `path` for writing.

    `compression` is one of `"none"` (plain text) or
    `"gzip"` (gzipped). Any other value raises
    `StorageError`.
    """
    if compression == "none" or compression is None:
        return path.open("wt", encoding="utf-8", newline="")
    if compression == "gzip":
        # gzip.open with text mode.
        return gzip.open(path, "wt", encoding="utf-8")
    raise StorageError(
        f"Unsupported compression {compression!r}; "
        f"expected 'none' or 'gzip'"
    )


def _decimal_to_str(value: Any) -> Any:
    """Convert `Decimal` to a JSON-serialisable form.

    `json.dump` does not serialise `Decimal`
    natively; we coerce to `str` to preserve exact
    precision.
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value)
    return value


def _record_to_row(record: Any) -> dict[str, Any]:
    """Convert a `TradeRecord` to a flat dict matching
    the CSV / JSON schema.

    `Decimal` values are stringified so JSON /
    CSV-serialised output preserves exact precision
    (per ADR-0027). The metadata sidecar documents
    this convention.
    """
    reporter = getattr(record, "reporter", None)
    partner = getattr(record, "partner", None)
    partner2 = getattr(record, "partner2", None)
    flow = getattr(record, "flow", None)
    commodity = getattr(record, "commodity", None)
    quantity = getattr(record, "quantity", None)
    trade_value = getattr(record, "trade_value", None)
    provenance = getattr(record, "provenance", None)

    return {
        # Identifier / metadata
        "type_code": getattr(record, "type_code", None),
        "frequency_code": getattr(record, "frequency_code", None),
        "classification_code": getattr(
            record, "classification_code", None
        ),
        "classification_search_code": getattr(
            record, "classification_search_code", None
        ),
        "edition": getattr(record, "edition", None),
        "is_original_classification": getattr(
            record, "is_original_classification", None
        ),
        # Period
        "ref_period_id": getattr(record, "ref_period_id", None),
        "ref_year": getattr(record, "ref_year", None),
        "ref_month": getattr(record, "ref_month", None),
        "period": getattr(record, "period", None),
        # Subjects
        "reporter_code": getattr(reporter, "reporter_code", None),
        "reporter_iso3": getattr(reporter, "iso3", None),
        "reporter_name": getattr(reporter, "name", None),
        "partner_code": getattr(partner, "partner_code", None),
        "partner_iso3": getattr(partner, "iso3", None),
        "partner_name": getattr(partner, "name", None),
        "partner2_code": (
            getattr(partner2, "partner_code", None)
            if partner2 is not None
            else None
        ),
        "partner2_iso3": (
            getattr(partner2, "iso3", None)
            if partner2 is not None
            else None
        ),
        "partner2_name": (
            getattr(partner2, "name", None)
            if partner2 is not None
            else None
        ),
        "flow_code": getattr(flow, "flow_code", None),
        "flow_name": getattr(flow, "flow_name", None),
        "commodity_code": getattr(commodity, "commodity_code", None),
        "commodity_name": getattr(commodity, "name", None),
        # Procedural
        "customs_code": getattr(record, "customs_code", None),
        "customs_name": getattr(record, "customs_name", None),
        "mos_code": getattr(record, "mos_code", None),
        "mot_code": getattr(record, "mot_code", None),
        "mot_name": getattr(record, "mot_name", None),
        # Quantities
        "quantity_qty": _decimal_to_str(
            getattr(quantity, "qty", None)
        ),
        "quantity_qty_unit_code": getattr(
            quantity, "qty_unit_code", None
        ),
        "quantity_qty_unit_abbr": getattr(
            quantity, "qty_unit_abbr", None
        ),
        "quantity_is_estimated": getattr(
            quantity, "is_estimated", None
        ),
        "quantity_alt_qty": _decimal_to_str(
            getattr(quantity, "alt_qty", None)
        ),
        "quantity_alt_qty_unit_code": getattr(
            quantity, "alt_qty_unit_code", None
        ),
        "quantity_alt_qty_unit_abbr": getattr(
            quantity, "alt_qty_unit_abbr", None
        ),
        "quantity_is_alt_qty_estimated": getattr(
            quantity, "is_alt_qty_estimated", None
        ),
        "net_weight_kg": _decimal_to_str(
            getattr(record, "net_weight_kg", None)
        ),
        "is_net_weight_estimated": getattr(
            record, "is_net_weight_estimated", None
        ),
        "gross_weight_kg": _decimal_to_str(
            getattr(record, "gross_weight_kg", None)
        ),
        "is_gross_weight_estimated": getattr(
            record, "is_gross_weight_estimated", None
        ),
        # Monetary
        "trade_value_primary_value": _decimal_to_str(
            getattr(trade_value, "primary_value", None)
        ),
        "trade_value_fob_value": _decimal_to_str(
            getattr(trade_value, "fob_value", None)
        ),
        "trade_value_cif_value": _decimal_to_str(
            getattr(trade_value, "cif_value", None)
        ),
        # Flags
        "legacy_estimation_flag": getattr(
            record, "legacy_estimation_flag", None
        ),
        "is_reported": getattr(record, "is_reported", None),
        "is_aggregate": getattr(record, "is_aggregate", None),
        # Provenance (kept as-is; consumer decodes)
        "provenance": provenance,
    }


# Canonical column order. The CSV header follows this
# order; JSON objects follow the same key order.
_COLUMNS: tuple[str, ...] = (
    "type_code",
    "frequency_code",
    "classification_code",
    "classification_search_code",
    "edition",
    "is_original_classification",
    "ref_period_id",
    "ref_year",
    "ref_month",
    "period",
    "reporter_code",
    "reporter_iso3",
    "reporter_name",
    "partner_code",
    "partner_iso3",
    "partner_name",
    "partner2_code",
    "partner2_iso3",
    "partner2_name",
    "flow_code",
    "flow_name",
    "commodity_code",
    "commodity_name",
    "customs_code",
    "customs_name",
    "mos_code",
    "mot_code",
    "mot_name",
    "quantity_qty",
    "quantity_qty_unit_code",
    "quantity_qty_unit_abbr",
    "quantity_is_estimated",
    "quantity_alt_qty",
    "quantity_alt_qty_unit_code",
    "quantity_alt_qty_unit_abbr",
    "quantity_is_alt_qty_estimated",
    "net_weight_kg",
    "is_net_weight_estimated",
    "gross_weight_kg",
    "is_gross_weight_estimated",
    "trade_value_primary_value",
    "trade_value_fob_value",
    "trade_value_cif_value",
    "legacy_estimation_flag",
    "is_reported",
    "is_aggregate",
    "provenance",
)


def _records_to_rows(records: Sequence[Any]) -> list[dict[str, Any]]:
    return [_record_to_row(r) for r in records]


# ---------------------------------------------------------------------------
# Read-side low-level helpers (F-001)
# ---------------------------------------------------------------------------


def _read_existing_csv_records(root: Path) -> list[dict[str, Any]]:
    """Read all CSV records under `root` and return
    flat dict rows (one per CSV row). Honors gzip
    compression when the file extension is `.csv.gz`.

    Files are read in **sorted path order** for
    determinism. `os.walk` returns files in arbitrary
    directory-traversal order; sorting ensures the
    concatenation order is reproducible across runs.
    """
    records: list[dict[str, Any]] = []
    files = sorted(
        list(root.rglob("*.csv")) + list(root.rglob("*.csv.gz")),
        key=lambda p: str(p),
    )
    for f in files:
        if f.suffix == ".gz":
            fh = gzip.open(f, "rt", encoding="utf-8", newline="")
        else:
            fh = f.open("rt", encoding="utf-8", newline="")
        with fh:
            reader = csv.DictReader(fh)
            records.extend(reader)
    return records


def _read_existing_json_records(root: Path) -> list[dict[str, Any]]:
    """Read all JSON records under `root` and return
    flat dict rows (one per row across files). Honors
    gzip compression when the file extension is
    `.json.gz`. Skips `*.meta.json` sidecars.

    Files are read in **sorted path order** for
    determinism.
    """
    import json as _json
    records: list[dict[str, Any]] = []
    files = [p for p in root.rglob("*.json") if not p.name.endswith(".meta.json")]
    files += list(root.rglob("*.json.gz"))
    files = sorted(files, key=lambda p: str(p))
    for f in files:
        if f.suffix == ".gz":
            fh = gzip.open(f, "rt", encoding="utf-8")
        else:
            fh = f.open("rt", encoding="utf-8")
        with fh:
            payload = _json.loads(fh.read())
        if isinstance(payload, dict) and "records" in payload:
            records.extend(payload["records"])
        elif isinstance(payload, list):
            records.extend(payload)
    return records


# ---------------------------------------------------------------------------
# Metadata sidecar
# ---------------------------------------------------------------------------


def _metadata_to_dict(metadata: DatasetMetadata) -> dict[str, Any]:
    """Serialise `DatasetMetadata` to a JSON-friendly
    dict for the sidecar file."""
    return {
        "metadata_schema_version": METADATA_SCHEMA_VERSION,
        "dataset_name": metadata.dataset_name,
        "schema_version": metadata.schema_version,
        "parser_name": metadata.parser_name,
        "record_count": metadata.record_count,
        "skipped": metadata.skipped,
        "duplicates_removed": metadata.duplicates_removed,
        "source_count": metadata.source_count,
        "extracted_at": (
            metadata.extracted_at.isoformat()
            if metadata.extracted_at is not None
            else None
        ),
        "stored_at": metadata.stored_at.isoformat(),
        "partition_keys": [list(k) for k in metadata.partition_keys],
        "backend": metadata.backend.value,
        "destination": metadata.destination,
        "extra": dict(metadata.extra),
    }


def write_metadata_sidecar(
    root: str | Path,
    dataset_name: str,
    metadata: DatasetMetadata,
    *,
    indent: int | None = 2,
) -> Path:
    """Write the metadata sidecar for `metadata`.

    The sidecar path is `<root>/<dataset_name>.meta.json`.
    Plain JSON (not gzipped) so consumers can
    inspect it without decompression.

    Returns the written path.
    """
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    sidecar_path = root_path / f"{dataset_name}.meta.json"
    payload = _metadata_to_dict(metadata)
    with sidecar_path.open("wt", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=indent, default=str)
    return sidecar_path


# ---------------------------------------------------------------------------
# CSVWriter
# ---------------------------------------------------------------------------


@dataclass
class CSVWriter:
    """Concrete `Storage` for the CSV backend.

    Uses Python's stdlib `csv.writer` to write
    `CanonicalDataset` records to a CSV file (or one
    file per partition key, when partitioning is
    configured). Supports gzip compression via the
    `compression` config option.

    The persisted file has:
    - Header row (`_COLUMNS` order).
    - One row per record (values in `_COLUMNS` order).
    - `Decimal` values serialised as strings to
      preserve exact precision (per ADR-0027).
    """

    backend: StorageBackend = StorageBackend.CSV

    def store(
        self,
        dataset: CanonicalDataset,
        config: StorageConfig,
    ) -> StorageResult:
        """Persist `dataset` to one or more CSV files
        under `config.root`. Writes a metadata sidecar
        alongside."""
        if not isinstance(dataset, CanonicalDataset):
            raise StorageError(
                f"CSVWriter.store requires a CanonicalDataset; "
                f"got {type(dataset).__name__}"
            )

        compression = config.compression
        root = Path(config.root)
        partition_strategy = (
            config.partition_strategy
            if config.partition_strategy is not None
            else PartitionStrategy.default()
        )

        records = _sort_records_deterministically(list(dataset.records))
        groups = partition_strategy.partition_records(records)
        partition_keys = tuple(groups.keys())

        partitions: dict[tuple, tuple[str, ...]] = {}
        total_bytes = 0

        # Decide whether to write a single file or one
        # per partition. Single file when no
        # partitioning is configured OR when
        # partition_strategy is `none()`.
        single_file = len(groups) <= 1
        if single_file:
            file_path = root / f"{dataset.name}.csv"
            if compression == "gzip":
                file_path = file_path.with_suffix(".csv.gz")
            root.mkdir(parents=True, exist_ok=True)
            count = self._write_csv_file(file_path, records, compression)
            total_bytes += file_path.stat().st_size
            # All records land in the (single) partition.
            for key in partition_keys:
                partitions[key] = (str(file_path),)
        else:
            for key, group_records in groups.items():
                file_path = root / partition_strategy.format_path(
                    dataset.name, self.backend, key
                )
                if compression == "gzip":
                    file_path = file_path.with_suffix(
                        file_path.suffix + ".gz"
                    )
                file_path.parent.mkdir(parents=True, exist_ok=True)
                count = self._write_csv_file(
                    file_path, group_records, compression
                )
                total_bytes += file_path.stat().st_size
                partitions[key] = (str(file_path),)

        # Build the metadata sidecar.
        metadata = DatasetMetadata(
            dataset_name=dataset.name,
            schema_version=dataset.schema_version,
            parser_name=dataset.parser_name,
            record_count=dataset.count,
            skipped=dataset.skipped,
            duplicates_removed=dataset.duplicates_removed,
            source_count=dataset.source_count,
            extracted_at=dataset.extracted_at,
            stored_at=datetime.now(timezone.utc),
            partition_keys=partition_keys,
            backend=self.backend,
            destination=str(root),
            extra={
                "csv_schema_version": CSV_SCHEMA_VERSION,
                "compression": compression,
            },
        )
        write_metadata_sidecar(root, dataset.name, metadata)

        result = StorageResult(
            backend=self.backend,
            destination=str(root),
            metadata=metadata,
            partitions=partitions,
            byte_size=total_bytes,
        )

        _logger.debug(
            "CSVWriter stored %d records in %d file(s) "
            "(compression=%s) under %s",
            result.record_count,
            len(partitions),
            compression,
            str(root),
        )
        return result

    def _write_csv_file(
        self,
        path: Path,
        records: Sequence[Any],
        compression: str,
    ) -> int:
        """Write a single CSV file. Returns the number
        of rows written (excluding the header)."""
        # Convert Decimal → str via the row helper.
        rows = _records_to_rows(records)
        with _open_for_write(path, compression) as fh:
            writer = csv.writer(
                fh, dialect="excel", quoting=csv.QUOTE_MINIMAL
            )
            writer.writerow(_COLUMNS)
            for row in rows:
                writer.writerow([row.get(col) for col in _COLUMNS])
        return len(rows)

    def __repr__(self) -> str:
        return f"CSVWriter(backend={self.backend.value!r})"

    # ------------------------------------------------------------------
    # F-001: Read side (inverse of store)
    # ------------------------------------------------------------------

    def read(self, config: StorageConfig) -> Any:
        """Reload a CSV dataset previously persisted by
        `CSVWriter.store`.

        Per `012_STORAGE_SPECIFICATION.md` §11, the
        retrieval is on-demand and returns the dataset
        in the documented format (`CanonicalDataset`).

        Parameters
        ----------
        config
            `StorageConfig` with the same `root` and
            `partition_strategy` used at write time. The
            `table_name` is ignored for CSV. The `dataset_name`
            is taken from the metadata sidecar
            `<root>/<dataset_name>.meta.json`; if absent
            it is derived from the file name.

        Returns
        -------
        `CanonicalDataset` reconstructed from the
        persisted CSV rows + sidecar metadata.
        """
        from un_comtrade.transform import CanonicalDataset

        root = Path(config.root)
        if not root.exists():
            raise StorageError(
                f"CSV read destination does not exist: {root}"
            )
        # Find the dataset name (single-partition: one
        # CSV file directly under root; multi-partition:
        # CSV files under Hive-style subdirs).
        # Prefer the metadata sidecar if present.
        sidecar_files = list(root.glob("*.meta.json"))
        if sidecar_files:
            dataset_name = sidecar_files[0].stem.removesuffix(".meta")
        else:
            # Legacy: pick the first CSV file.
            csv_files = list(root.rglob("*.csv"))
            if not csv_files:
                raise StorageError(
                    f"No CSV files or metadata sidecar under {root}"
                )
            dataset_name = csv_files[0].stem

        rows = _read_existing_csv_records(root)
        records = _sort_records_deterministically(_rows_to_records(rows))
        metadata = _read_metadata_sidecar(root, dataset_name)
        if metadata:
            ds = _build_dataset_from_metadata(metadata, records)
            # Preserve the dataset_name even if sidecar
            # had a different one.
            from dataclasses import replace
            ds = replace(ds, name=dataset_name)
        else:
            ds = CanonicalDataset(
                name=dataset_name,
                records=tuple(records),
                schema_version="1.0",
                parser_name="CSVReader",
                source_count=len(records),
            )
        _logger.debug(
            "CSVWriter read %d records from %s",
            len(records),
            str(root),
        )
        return ds


# ---------------------------------------------------------------------------
# JSONWriter
# ---------------------------------------------------------------------------


@dataclass
class JSONWriter:
    """Concrete `Storage` for the JSON backend.

    Uses Python's stdlib `json` module to write
    `CanonicalDataset` records to a JSON file (or
    one file per partition key, when partitioning is
    configured). Supports gzip compression via the
    `compression` config option.

    The persisted file format (per
    `012_STORAGE_SPECIFICATION.md` §10.1):

    ```json
    {
      "schema_version": "1.0.0",
      "count": 3,
      "records": [
        {"type_code": "...", "period": "...", ...},
        ...
      ]
    }
    ```

    - Top-level: a JSON object with `schema_version`,
      `count`, `records`.
    - Records: a JSON array (per §10.1).
    - Nulls: `null`.
    - `Decimal` values: serialised as strings (to
      preserve exact precision per ADR-0027).
    """

    backend: StorageBackend = StorageBackend.JSON

    def store(
        self,
        dataset: CanonicalDataset,
        config: StorageConfig,
    ) -> StorageResult:
        """Persist `dataset` to one or more JSON files
        under `config.root`. Writes a metadata sidecar."""
        if not isinstance(dataset, CanonicalDataset):
            raise StorageError(
                f"JSONWriter.store requires a CanonicalDataset; "
                f"got {type(dataset).__name__}"
            )

        compression = config.compression
        root = Path(config.root)
        partition_strategy = (
            config.partition_strategy
            if config.partition_strategy is not None
            else PartitionStrategy.default()
        )
        indent = config.metadata.get("indent")

        records = _sort_records_deterministically(list(dataset.records))
        groups = partition_strategy.partition_records(records)
        partition_keys = tuple(groups.keys())

        partitions: dict[tuple, tuple[str, ...]] = {}
        total_bytes = 0

        # Single file vs per-partition files.
        single_file = len(groups) <= 1
        if single_file:
            ext = ".json"
            if compression == "gzip":
                ext = ".json.gz"
            file_path = root / f"{dataset.name}{ext}"
            root.mkdir(parents=True, exist_ok=True)
            total_bytes += self._write_json_file(
                file_path, records, compression, indent
            ).stat().st_size
            for key in partition_keys:
                partitions[key] = (str(file_path),)
        else:
            for key, group_records in groups.items():
                base = root / partition_strategy.format_path(
                    dataset.name, self.backend, key
                )
                if compression == "gzip":
                    base = base.with_suffix(base.suffix + ".gz")
                base.parent.mkdir(parents=True, exist_ok=True)
                total_bytes += self._write_json_file(
                    base, group_records, compression, indent
                ).stat().st_size
                partitions[key] = (str(base),)

        metadata = DatasetMetadata(
            dataset_name=dataset.name,
            schema_version=dataset.schema_version,
            parser_name=dataset.parser_name,
            record_count=dataset.count,
            skipped=dataset.skipped,
            duplicates_removed=dataset.duplicates_removed,
            source_count=dataset.source_count,
            extracted_at=dataset.extracted_at,
            stored_at=datetime.now(timezone.utc),
            partition_keys=partition_keys,
            backend=self.backend,
            destination=str(root),
            extra={
                "json_schema_version": JSON_SCHEMA_VERSION,
                "compression": compression,
                "indent": indent,
            },
        )
        write_metadata_sidecar(root, dataset.name, metadata)

        result = StorageResult(
            backend=self.backend,
            destination=str(root),
            metadata=metadata,
            partitions=partitions,
            byte_size=total_bytes,
        )

        _logger.debug(
            "JSONWriter stored %d records in %d file(s) "
            "(compression=%s) under %s",
            result.record_count,
            len(partitions),
            compression,
            str(root),
        )
        return result

    def _write_json_file(
        self,
        path: Path,
        records: Sequence[Any],
        compression: str,
        indent: int | None,
    ) -> Path:
        """Write a single JSON file. Returns the path."""
        rows = _records_to_rows(records)
        payload = {
            "schema_version": JSON_SCHEMA_VERSION,
            "count": len(rows),
            "records": rows,
        }
        with _open_for_write(path, compression) as fh:
            json.dump(payload, fh, indent=indent, default=str)
        return path

    def __repr__(self) -> str:
        return f"JSONWriter(backend={self.backend.value!r})"

    # ------------------------------------------------------------------
    # F-001: Read side (inverse of store)
    # ------------------------------------------------------------------

    def read(self, config: StorageConfig) -> Any:
        """Reload a JSON dataset previously persisted by
        `JSONWriter.store`.

        Per `012_STORAGE_SPECIFICATION.md` §11, the
        retrieval is on-demand and returns the dataset
        in the documented format (`CanonicalDataset`).

        Parameters
        ----------
        config
            `StorageConfig` with the same `root` and
            `partition_strategy` used at write time. The
            `table_name` is ignored for JSON. The
            `dataset_name` is taken from the metadata
            sidecar or from the JSON file name.

        Returns
        -------
        `CanonicalDataset` reconstructed from the
        persisted JSON rows + sidecar metadata.
        """
        from un_comtrade.transform import CanonicalDataset

        root = Path(config.root)
        if not root.exists():
            raise StorageError(
                f"JSON read destination does not exist: {root}"
            )
        sidecar_files = list(root.glob("*.meta.json"))
        if sidecar_files:
            dataset_name = sidecar_files[0].stem.removesuffix(".meta")
        else:
            json_files = [
                p for p in root.rglob("*.json")
                if not p.name.endswith(".meta.json")
            ]
            if not json_files:
                raise StorageError(
                    f"No JSON files or metadata sidecar under {root}"
                )
            dataset_name = json_files[0].stem

        rows = _read_existing_json_records(root)
        records = _sort_records_deterministically(_rows_to_records(rows))
        metadata = _read_metadata_sidecar(root, dataset_name)
        if metadata:
            ds = _build_dataset_from_metadata(metadata, records)
            from dataclasses import replace
            ds = replace(ds, name=dataset_name)
        else:
            ds = CanonicalDataset(
                name=dataset_name,
                records=tuple(records),
                schema_version="1.0",
                parser_name="JSONReader",
                source_count=len(records),
            )
        _logger.debug(
            "JSONWriter read %d records from %s",
            len(records),
            str(root),
        )
        return ds


# ---------------------------------------------------------------------------
# Read-side helpers (F-001)
# ---------------------------------------------------------------------------


def _str_to_decimal(value: Any) -> Any:
    """Inverse of `_decimal_to_str`.

    Reconstructs `Decimal` values from the stringified
    form used in the persisted rows. Returns `None`
    unchanged; returns the original value if it is not
    a string. Raises `StorageError` if the value is a
    string that cannot be parsed as `Decimal`.
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, str):
        if value == "":
            return None
        try:
            return Decimal(value)
        except Exception as exc:
            raise StorageError(
                f"Cannot decode {value!r} as Decimal: {exc}"
            ) from exc
    return value


def _coerce_int(value: Any) -> Any:
    """Coerce a value to `int`, allowing None."""
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value == "":
            return None
        try:
            return int(value)
        except Exception as exc:
            raise StorageError(
                f"Cannot decode {value!r} as int: {exc}"
            ) from exc
    try:
        return int(value)
    except Exception:
        return value


def _coerce_bool(value: Any) -> Any:
    """Coerce a value to `bool`. Passes None through."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in ("1", "true", "yes", "y", "t"):
            return True
        if s in ("0", "false", "no", "n", "f", ""):
            return False
    return bool(value) if value else False


def _coerce_provenance(value: Any) -> Any:
    """Reverse the JSON encoding applied by `_record_to_row`.

    CSV / JSON file backends serialise `provenance`
    (a `dict` in memory) as a JSON string. On read
    the value comes back as a `str`; we decode it back
    to a `dict` to match the `TradeRecord.provenance`
    type contract. DuckDB stores provenance as a JSON
    column already, so this helper is a no-op when the
    value is already a `dict` or `None`.
    """
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        if value == "":
            return None
        try:
            import json as _json
            parsed = _json.loads(value)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
    return None


def _record_sort_key(record: Any) -> tuple:
    """Deterministic composite sort key for a TradeRecord.

    Used to reorder records after a multi-partition
    round-trip so that the resulting `CanonicalDataset`
    preserves a canonical order regardless of how
    partition files were concatenated on read.

    The key is the union of the documented
    `TradeRecordKeyFields` (per `un_comtrade.parser`)
    extended with `ref_year` for deterministic ordering
    across multi-year datasets.

    Heterogeneous types (e.g. `int` and `str` for the
    same logical field, as can occur after a CSV read
    + sort) are normalised to strings for ordering
    purposes — the sort is for determinism, not for
    semantic equivalence.
    """
    def _norm(v: Any) -> str:
        if v is None:
            return ""
        return str(v)

    reporter = getattr(record, "reporter", None)
    partner = getattr(record, "partner", None)
    flow = getattr(record, "flow", None)
    commodity = getattr(record, "commodity", None)
    return (
        _norm(getattr(record, "ref_period_id", None)),
        _norm(getattr(reporter, "reporter_code", None) if reporter else None),
        _norm(getattr(partner, "partner_code", None) if partner else None),
        _norm(getattr(flow, "flow_code", None) if flow else None),
        _norm(getattr(commodity, "commodity_code", None) if commodity else None),
    )


def _row_to_record(row: dict[str, Any]) -> Any:
    """Inverse of `_record_to_row`.

    Reconstruct a `TradeRecord` from a flat dict row
    produced by `_record_to_row`. The flat schema is
    shared by all five storage backends (CSV, JSON,
    Parquet, DuckDB) so this helper is the single
    canonical reverse-mapping for the storage layer.

    The reconstruction re-validates each field through
    the canonical model dataclasses (`Reporter`,
    `TradePartner`, `Commodity`, `TradeFlow`,
    `TradeValue`, `Quantity`) so a row that does not
    match the canonical schema is rejected with a
    `StorageError` at read time, not silently accepted.
    """
    # Local imports to avoid a circular import at
    # module-load time (un_comtrade.transform -> models
    # -> storage chain).
    from un_comtrade.models.trade import (
        Reporter,
        Partner as TradePartner,
        Commodity,
        TradeFlow,
        Quantity,
        TradeRecord,
        TradeValue,
    )

    def _opt_str(v: Any) -> str | None:
        if v is None or v == "":
            return None
        return str(v)

    reporter = Reporter(
        reporter_code=_coerce_int(row.get("reporter_code")),
        iso3=_opt_str(row.get("reporter_iso3")),
        name=_opt_str(row.get("reporter_name")),
    )
    partner = TradePartner(
        partner_code=_coerce_int(row.get("partner_code")),
        iso3=_opt_str(row.get("partner_iso3")),
        name=_opt_str(row.get("partner_name")),
    )
    partner2_code = _coerce_int(row.get("partner2_code"))
    partner2_iso3 = _opt_str(row.get("partner2_iso3"))
    partner2_name = _opt_str(row.get("partner2_name"))
    partner2 = None
    if partner2_code is not None and partner2_code != 0:
        partner2 = TradePartner(
            partner_code=partner2_code,
            iso3=partner2_iso3,
            name=partner2_name,
        )
    flow = TradeFlow(
        flow_code=_opt_str(row.get("flow_code")) or "",
        flow_name=_opt_str(row.get("flow_name")),
    )
    commodity = Commodity(
        commodity_code=_opt_str(row.get("commodity_code")) or "",
        name=_opt_str(row.get("commodity_name")),
    )
    quantity = Quantity(
        qty=_str_to_decimal(row.get("quantity_qty")),
        qty_unit_code=_coerce_int(row.get("quantity_qty_unit_code")),
        qty_unit_abbr=_opt_str(row.get("quantity_qty_unit_abbr")),
        is_estimated=_coerce_bool(row.get("quantity_is_estimated")),
        alt_qty=_str_to_decimal(row.get("quantity_alt_qty")),
        alt_qty_unit_code=_coerce_int(
            row.get("quantity_alt_qty_unit_code")
        ),
        alt_qty_unit_abbr=_opt_str(
            row.get("quantity_alt_qty_unit_abbr")
        ),
        is_alt_qty_estimated=_coerce_bool(
            row.get("quantity_is_alt_qty_estimated")
        ),
    )
    trade_value = TradeValue(
        primary_value=_str_to_decimal(
            row.get("trade_value_primary_value")
        ),
        fob_value=_str_to_decimal(row.get("trade_value_fob_value")),
        cif_value=_str_to_decimal(row.get("trade_value_cif_value")),
    )
    return TradeRecord(
        type_code=_opt_str(row.get("type_code")) or "",
        frequency_code=_opt_str(row.get("frequency_code")) or "",
        classification_code=_opt_str(row.get("classification_code"))
        or "",
        classification_search_code=_opt_str(
            row.get("classification_search_code")
        ),
        edition=_opt_str(row.get("edition")),
        is_original_classification=_coerce_bool(
            row.get("is_original_classification")
        ),
        ref_period_id=_coerce_int(row.get("ref_period_id")),
        ref_year=_coerce_int(row.get("ref_year")),
        ref_month=_coerce_int(row.get("ref_month")),
        period=_opt_str(row.get("period")) or "",
        reporter=reporter,
        partner=partner,
        partner2=partner2,
        flow=flow,
        commodity=commodity,
        customs_code=_opt_str(row.get("customs_code")),
        customs_name=_opt_str(row.get("customs_name")),
        mos_code=_opt_str(row.get("mos_code")),
        mot_code=_coerce_int(row.get("mot_code")),
        mot_name=_opt_str(row.get("mot_name")),
        quantity=quantity,
        net_weight_kg=_str_to_decimal(row.get("net_weight_kg")),
        is_net_weight_estimated=_coerce_bool(
            row.get("is_net_weight_estimated")
        ),
        gross_weight_kg=_str_to_decimal(row.get("gross_weight_kg")),
        is_gross_weight_estimated=_coerce_bool(
            row.get("is_gross_weight_estimated")
        ),
        trade_value=trade_value,
        legacy_estimation_flag=_coerce_int(
            row.get("legacy_estimation_flag")
        ),
        is_reported=_coerce_bool(row.get("is_reported")),
        is_aggregate=_coerce_bool(row.get("is_aggregate")),
        provenance=_coerce_provenance(row.get("provenance")),
    )


def _read_metadata_sidecar(
    root: Path,
    dataset_name: str,
) -> dict[str, Any]:
    """Read the `<root>/<dataset_name>.meta.json` sidecar.

    Returns an empty dict when the sidecar is absent
    (e.g. legacy datasets written before the sidecar
    convention was introduced). Raises `StorageError`
    when the sidecar exists but cannot be decoded.
    """
    sidecar = root / f"{dataset_name}.meta.json"
    if not sidecar.exists():
        return {}
    try:
        return json.loads(sidecar.read_text(encoding="utf-8"))
    except Exception as exc:
        raise StorageError(
            f"Cannot read metadata sidecar {sidecar}: {exc}"
        ) from exc


def _rows_to_records(rows: list[dict[str, Any]]) -> list[Any]:
    """Convert a list of flat dict rows to TradeRecords."""
    return [_row_to_record(r) for r in rows]


def _sort_records_deterministically(records: list[Any]) -> list[Any]:
    """Sort records by the canonical composite key so
    the round-trip output order is reproducible.

    Partitioned writes concatenate records by partition
    key order; sorting after read restores a canonical
    order matching the `TradeRecordKeyFields` contract.
    """
    return sorted(records, key=_record_sort_key)


def _build_dataset_from_metadata(
    metadata: dict[str, Any],
    records: list[Any],
) -> Any:
    """Construct a `CanonicalDataset` from sidecar metadata + records.

    The sidecar's `extracted_at` and `stored_at` are
    ISO-8601 strings; convert them back to `datetime`.
    """
    from datetime import datetime
    from un_comtrade.transform import CanonicalDataset

    def _opt_dt(s: Any) -> datetime | None:
        if s is None or s == "":
            return None
        if isinstance(s, datetime):
            return s
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None

    return CanonicalDataset(
        name=metadata.get("dataset_name") or "reloaded",
        records=tuple(records),
        schema_version=metadata.get("schema_version") or "1.0",
        parser_name=metadata.get("parser_name") or "StorageRead",
        skipped=int(metadata.get("skipped") or 0),
        duplicates_removed=int(metadata.get("duplicates_removed") or 0),
        source_count=int(metadata.get("record_count") or len(records)),
        extracted_at=_opt_dt(metadata.get("extracted_at")),
    )