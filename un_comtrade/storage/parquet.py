"""Concrete Parquet storage engine.

Implements the `Storage` protocol for the
`StorageBackend.PARQUET` backend per
`012_STORAGE_SPECIFICATION.md` §3.4 (T04). Uses
`pyarrow` to:

- Convert each `TradeRecord` in a `CanonicalDataset`
  to a row in a `pyarrow.Table`.
- Apply a stable Arrow schema (column names +
  types) so the persisted schema is reproducible
  across runs.
- Preserve `Decimal` precision by mapping every
  monetary / quantity field to `pa.decimal128`
  with explicit precision / scale.
- Write one Parquet file per partition key
  (using the supplied `PartitionStrategy`,
  defaulting to `(reporter, year, frequency)`
  per ADR-0029).
- Emit a `StorageResult` with full
  `DatasetMetadata` (per the P5-001 framework).

Per the P5-002 task scope:

- **Parquet writer** — `pyarrow.parquet.write_table`.
- **Schema preservation** — fixed Arrow schema
  with explicit types; the same schema is used on
  every write so the persisted schema is stable.
- **Decimal preservation** — `Decimal` monetary
  and quantity fields are coerced to
  `decimal128(38, 18)` (canonical precision /
  scale) so the persisted values are exact, not
  float-truncated.
- **Partitioning** — one file per partition key
  via `PartitionStrategy.partition_records()` +
  `PartitionStrategy.format_path()`.

Usage::

    from un_comtrade.storage.parquet import ParquetWriter
    from un_comtrade.storage import (
        StorageConfig, PartitionStrategy,
    )
    from un_comtrade.transform import CanonicalDataset

    writer = ParquetWriter()
    result = writer.store(
        dataset=canonical_dataset,
        config=StorageConfig(
            root="/data/trade",
            partition_strategy=PartitionStrategy.default(),
            compression="snappy",
        ),
    )
    # result.partitions is {key: (file_path,)}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Mapping,
    Sequence,
)

from ..etl import PipelineContext, StageKind  # noqa: F401  (kept for IDE consistency)
from ..exceptions import ComtradeError
from ..logging import get_logger
from ..transform import CanonicalDataset  # noqa: F401  (runtime check)
from ._base import (
    DatasetMetadata,
    PartitionStrategy,
    StorageBackend,
    StorageConfig,
    StorageError,
    StorageResult,
)
from .file import (
    _sort_records_deterministically,
    _row_to_record,
    _read_metadata_sidecar,
    _build_dataset_from_metadata,
)


if TYPE_CHECKING:
    import pyarrow as pa  # type: ignore[import-not-found]
    import pyarrow.parquet as pq  # type: ignore[import-not-found]

    from ..models import TradeRecord


__all__ = ["PARQUET_SCHEMA_VERSION", "ParquetWriter", "parquet_schema"]


_logger = get_logger("lifecycle")


#: Schema version stamped on every persisted dataset.
#: Bumped when the persisted schema changes in a
#: non-backward-compatible way.
PARQUET_SCHEMA_VERSION: str = "1.0.0"

#: Standard decimal precision / scale used for
#: monetary and quantity fields. `decimal128(38, 18)`
#: supports up to 38 significant digits with 18 digits
#: after the decimal point — sufficient for trade
#: monetary values (per `006_DATA_MODEL.md` §14.4).
_DECIMAL_PRECISION: int = 38
_DECIMAL_SCALE: int = 18


# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------


def parquet_schema() -> "pa.Schema":
    """Return the canonical Arrow schema for a
    `TradeRecord`.

    The schema is deterministic and stable across
    runs. Column order matches `TradeRecord`'s
    field declaration order. Decimal columns use
    `decimal128(38, 18)`; nullable fields use
    `pyarrow` nullable types; `provenance` is a
    `pa.string()` (JSON-serialised provenance).
    """
    import pyarrow as pa  # type: ignore[import-not-found]

    decimal_t = pa.decimal128(_DECIMAL_PRECISION, _DECIMAL_SCALE)
    return pa.schema(
        [
            # Identifier / metadata
            ("type_code", pa.string(), False),
            ("frequency_code", pa.string(), False),
            ("classification_code", pa.string(), False),
            ("classification_search_code", pa.string(), True),
            ("edition", pa.string(), False),
            ("is_original_classification", pa.bool_(), True),
            # Period
            ("ref_period_id", pa.int64(), True),
            ("ref_year", pa.int32(), False),
            ("ref_month", pa.int32(), False),
            ("period", pa.string(), False),
            # Subjects (flattened — record-embedded
            # models become scalar columns)
            ("reporter_code", pa.int32(), False),
            ("reporter_iso3", pa.string(), True),
            ("reporter_name", pa.string(), True),
            ("partner_code", pa.int32(), False),
            ("partner_iso3", pa.string(), True),
            ("partner_name", pa.string(), True),
            ("partner2_code", pa.int32(), True),
            ("partner2_iso3", pa.string(), True),
            ("partner2_name", pa.string(), True),
            ("flow_code", pa.string(), False),
            ("flow_name", pa.string(), True),
            ("commodity_code", pa.string(), False),
            ("commodity_name", pa.string(), True),
            # Procedural
            ("customs_code", pa.string(), False),
            ("customs_name", pa.string(), True),
            ("mos_code", pa.string(), False),
            ("mot_code", pa.int32(), False),
            ("mot_name", pa.string(), True),
            # Quantities (Decimal-preserving)
            ("quantity_qty", decimal_t, True),
            ("quantity_qty_unit_code", pa.int32(), False),
            ("quantity_qty_unit_abbr", pa.string(), True),
            ("quantity_is_estimated", pa.bool_(), False),
            ("quantity_alt_qty", decimal_t, True),
            ("quantity_alt_qty_unit_code", pa.int32(), True),
            ("quantity_alt_qty_unit_abbr", pa.string(), True),
            ("quantity_is_alt_qty_estimated", pa.bool_(), False),
            ("net_weight_kg", decimal_t, True),
            ("is_net_weight_estimated", pa.bool_(), False),
            ("gross_weight_kg", decimal_t, True),
            ("is_gross_weight_estimated", pa.bool_(), False),
            # Monetary (Decimal-preserving)
            ("trade_value_primary_value", decimal_t, False),
            ("trade_value_fob_value", decimal_t, True),
            ("trade_value_cif_value", decimal_t, True),
            # Flags
            ("legacy_estimation_flag", pa.int32(), False),
            ("is_reported", pa.bool_(), False),
            ("is_aggregate", pa.bool_(), False),
            # Provenance (serialised as JSON string)
            ("provenance", pa.string(), True),
        ]
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _decimal_or_none(value: Any) -> Any:
    """Return a `Decimal` or `None` for Arrow
    consumption.

    `pyarrow.decimal128` accepts `Decimal`, `int`,
    `str`, `float`, or `None`. Returning `None`
    preserves nulls; returning a `Decimal` preserves
    exact precision (no float truncation).
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _record_to_row(record: Any, schema: "pa.Schema") -> dict[str, Any]:
    """Convert a `TradeRecord` to a flat column dict
    matching `parquet_schema()`.

    The function is permissive: it accepts any
    object that exposes the documented
    `TradeRecord` attributes (so stub records work
    in tests as well as canonical instances).
    """
    reporter = getattr(record, "reporter", None)
    partner = getattr(record, "partner", None)
    partner2 = getattr(record, "partner2", None)
    flow = getattr(record, "flow", None)
    commodity = getattr(record, "commodity", None)
    quantity = getattr(record, "quantity", None)
    trade_value = getattr(record, "trade_value", None)
    provenance = getattr(record, "provenance", None)

    import json as _json

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
        "quantity_qty": _decimal_or_none(
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
        "quantity_alt_qty": _decimal_or_none(
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
        "net_weight_kg": _decimal_or_none(
            getattr(record, "net_weight_kg", None)
        ),
        "is_net_weight_estimated": getattr(
            record, "is_net_weight_estimated", None
        ),
        "gross_weight_kg": _decimal_or_none(
            getattr(record, "gross_weight_kg", None)
        ),
        "is_gross_weight_estimated": getattr(
            record, "is_gross_weight_estimated", None
        ),
        # Monetary
        "trade_value_primary_value": _decimal_or_none(
            getattr(trade_value, "primary_value", None)
        ),
        "trade_value_fob_value": _decimal_or_none(
            getattr(trade_value, "fob_value", None)
        ),
        "trade_value_cif_value": _decimal_or_none(
            getattr(trade_value, "cif_value", None)
        ),
        # Flags
        "legacy_estimation_flag": getattr(
            record, "legacy_estimation_flag", None
        ),
        "is_reported": getattr(record, "is_reported", None),
        "is_aggregate": getattr(record, "is_aggregate", None),
        # Provenance (serialised as JSON; null stays null)
        "provenance": (
            _json.dumps(provenance, default=str)
            if provenance is not None
            else None
        ),
    }


def _build_table(
    records: Sequence[Any],
    schema: "pa.Schema",
) -> "pa.Table":
    """Build a `pyarrow.Table` from a list of records
    using the supplied schema.

    Columns are built in schema-defined order to
    match the schema exactly.
    """
    import pyarrow as pa  # type: ignore[import-not-found]

    columns: dict[str, list[Any]] = {name: [] for name in schema.names}
    for record in records:
        row = _record_to_row(record, schema)
        for col_name in schema.names:
            columns[col_name].append(row[col_name])
    return pa.table(columns, schema=schema)


# ---------------------------------------------------------------------------
# ParquetWriter (concrete Storage implementation)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParquetWriter:
    """Concrete `Storage` for the PARQUET backend.

    Persists a `CanonicalDataset` to one Parquet file
    per partition key. The default partition
    strategy is `(reporter_code, ref_year,
    frequency_code)` per ADR-0029; callers can
    override via `StorageConfig.partition_strategy`.

    The persisted schema is fixed (see
    `parquet_schema()`) and stable across runs.
    Decimal values are preserved exactly via
    `decimal128(38, 18)`.

    This class implements the `Storage` Protocol
    from `un_comtrade.storage._base`. It is
    registered automatically as the
    `StorageBackend.PARQUET` backend when
    `un_comtrade.storage` is imported (if pyarrow
    is installed). Callers may also instantiate it
    directly and pass it to `StorageStage`.
    """

    backend: StorageBackend = StorageBackend.PARQUET

    def store(
        self,
        dataset: CanonicalDataset,
        config: StorageConfig,
    ) -> StorageResult:
        """Persist `dataset` to Parquet files under
        `config.root`.

        One file is written per partition key.
        Filenames are derived from
        `config.partition_strategy.format_path(...)`.

        Returns a `StorageResult` with full
        `DatasetMetadata`. Raises `StorageError` on
        I/O failures or unsupported configurations.
        """
        try:
            import pyarrow as pa  # noqa: F401  # type: ignore[import-not-found]
            import pyarrow.parquet as pq  # type: ignore[import-not-found]
        except ImportError as exc:
            raise StorageError(
                "ParquetWriter requires pyarrow; "
                "install with `pip install pyarrow`"
            ) from exc

        if not isinstance(dataset, CanonicalDataset):
            raise StorageError(
                f"ParquetWriter.store requires a "
                f"CanonicalDataset; got {type(dataset).__name__}"
            )

        if dataset.is_empty:
            # Empty dataset: produce a metadata-only
            # result (no files written). The pipeline
            # is informed via the result.
            return StorageResult(
                backend=self.backend,
                destination=str(config.root),
                metadata=DatasetMetadata(
                    dataset_name=dataset.name,
                    schema_version=dataset.schema_version,
                    parser_name=dataset.parser_name,
                    record_count=0,
                    skipped=dataset.skipped,
                    duplicates_removed=dataset.duplicates_removed,
                    source_count=dataset.source_count,
                    extracted_at=dataset.extracted_at,
                    stored_at=datetime.now(timezone.utc),
                    partition_keys=(),
                    backend=self.backend,
                    destination=str(config.root),
                    extra={
                        "parquet_schema_version": PARQUET_SCHEMA_VERSION,
                    },
                ),
                partitions={},
                byte_size=0,
            )

        partition_strategy = (
            config.partition_strategy
            if config.partition_strategy is not None
            else PartitionStrategy.default()
        )

        schema = parquet_schema()

        # Group records by partition key.
        records_list = list(dataset.records)
        # F-001: sort deterministically before
        # partitioning so the on-disk order matches
        # the read-back order (round-trip equality).
        records_list = _sort_records_deterministically(records_list)
        groups = partition_strategy.partition_records(records_list)

        # Resolve the root path.
        root = Path(config.root)

        # Per-partition write.
        partitions: dict[tuple, tuple[str, ...]] = {}
        total_byte_size = 0
        for key, group_records in groups.items():
            file_name = partition_strategy.format_path(
                dataset.name, self.backend, key
            )
            file_path = root / file_name
            file_path.parent.mkdir(parents=True, exist_ok=True)

            table = _build_table(group_records, schema)

            # PyArrow's default write behaviour:
            # create a single-file Parquet output. We
            # pass the compression codec via the
            # `compression` argument.
            try:
                pq.write_table(
                    table,
                    file_path,
                    compression=config.compression,
                )
            except Exception as exc:
                raise StorageError(
                    f"ParquetWriter failed to write "
                    f"{file_path}: {exc}"
                ) from exc

            partitions[key] = (str(file_path),)
            total_byte_size += file_path.stat().st_size

        # Build the result metadata.
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
            partition_keys=tuple(partitions.keys()),
            backend=self.backend,
            destination=str(root),
            extra={
                "parquet_schema_version": PARQUET_SCHEMA_VERSION,
                "compression": config.compression,
                "arrow_schema_version": str(schema.metadata) if schema.metadata else None,
            },
        )

        result = StorageResult(
            backend=self.backend,
            destination=str(root),
            metadata=metadata,
            partitions=partitions,
            byte_size=total_byte_size,
        )

        _logger.debug(
            "ParquetWriter stored %d records in %d "
            "partition(s) under %s (schema=%s)",
            result.record_count,
            len(partitions),
            str(root),
            PARQUET_SCHEMA_VERSION,
        )
        return result

    def __repr__(self) -> str:
        return f"ParquetWriter(backend={self.backend.value!r})"

    # ------------------------------------------------------------------
    # F-001: Read side (inverse of store)
    # ------------------------------------------------------------------

    def read(self, config: StorageConfig) -> CanonicalDataset:
        """Reload a Parquet dataset previously persisted
        by `ParquetWriter.store`.

        Per `012_STORAGE_SPECIFICATION.md` §11, the
        retrieval is on-demand and returns the dataset
        as a `CanonicalDataset`.

        Parameters
        ----------
        config
            `StorageConfig` with the same `root` and
            `partition_strategy` used at write time. The
            `table_name` is ignored for Parquet. The
            `dataset_name` is taken from the metadata
            sidecar or from the file name.

        Returns
        -------
        `CanonicalDataset` reconstructed from the
        persisted Parquet rows + sidecar metadata.
        """
        try:
            import pyarrow.parquet as _pq
        except ImportError as exc:  # pragma: no cover
            raise StorageError(
                "Parquet read requires pyarrow; "
                "install with `pip install pyarrow`"
            ) from exc

        root = Path(config.root)
        if not root.exists():
            raise StorageError(
                f"Parquet read destination does not exist: {root}"
            )
        files = sorted(root.rglob("*.parquet"), key=lambda p: str(p))
        if not files:
            raise StorageError(
                f"No Parquet files under {root}"
            )
        tables = [_pq.read_table(f) for f in files]
        if len(tables) == 1:
            combined = tables[0]
        else:
            combined = tables[0]
            for t in tables[1:]:
                combined = _concat_arrow_tables(combined, t)
        # Convert Arrow table rows to flat dicts.
        # pyarrow's to_pylist() converts each column to
        # the appropriate Python type (Decimal for
        # decimal128 columns); we then stringify
        # Decimals back to strings so `_row_to_record`
        # can re-parse them with the standard
        # `_str_to_decimal` helper.
        rows: list[dict[str, Any]] = []
        for raw_row in combined.to_pylist():
            stringified: dict[str, Any] = {}
            for k, v in raw_row.items():
                if isinstance(v, Decimal):
                    stringified[k] = str(v)
                else:
                    stringified[k] = v
            rows.append(stringified)
        records = [_row_to_record(r) for r in rows]
        # F-001: sort deterministically so the
        # round-trip order matches the on-disk order.
        records = _sort_records_deterministically(records)
        # Determine dataset_name.
        sidecar_files = list(root.glob("*.meta.json"))
        if sidecar_files:
            dataset_name = sidecar_files[0].stem.removesuffix(".meta")
        else:
            dataset_name = files[0].stem
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
                parser_name="ParquetReader",
                source_count=len(records),
            )
        _logger.debug(
            "ParquetWriter read %d records from %s",
            len(records),
            str(root),
        )
        return ds


def _concat_arrow_tables(t1: Any, t2: Any) -> Any:
    """Concatenate two pyarrow tables vertically (append rows)."""
    try:
        import pyarrow as _pa
        return _pa.concat_tables([t1, t2])
    except Exception:
        # Fallback: manual concat by columns.
        import pyarrow as _pa
        return _pa.table(
            {
                name: _pa.concat_arrays(
                    [t1.column(name), t2.column(name)]
                )
                for name in t1.column_names
            }
        )