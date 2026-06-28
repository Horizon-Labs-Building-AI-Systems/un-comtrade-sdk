"""Concrete DuckDB storage engine.

Implements the `Storage` protocol for the
`StorageBackend.DUCKDB` backend per
`012_STORAGE_SPECIFICATION.md` §3.5 (T05). Uses
the `duckdb` Python client to:

- Persist `CanonicalDataset` records to an embedded
  analytical database file.
- Register the dataset's provenance in a metadata
  table (`un_comtrade_datasets`).
- Support **incremental append** via `mode='append'`
  (default; inserts new rows) or `mode='replace'`
  (drops and re-creates the table).
- Support **partition loading** — create a view
  that filters the persisted table by a partition
  key (the ADR-0029 `(reporter, year, frequency)`
  key by default).
- Validate queries against the persisted schema
  via DuckDB's `Connection.extract_statements` /
  `prepare` APIs.

Per the P5-003 task scope:

- **DuckDB writer** — `duckdb.connect()` +
  `connection.register()` + `connection.execute()`
  for the initial CREATE TABLE + INSERT.
- **Dataset registration** — every `store()` call
  records a row in `un_comtrade_datasets` with the
  dataset's provenance (name, schema_version,
  record_count, partition_keys, stored_at).
- **Partition loading** — `load_partition(connection,
  table_name, partition_key)` creates a view that
  filters by the supplied partition key.
- **Incremental append** — `mode='append'` (default)
  preserves existing rows; `mode='replace'` drops
  and re-creates the target table.
- **Query validation** — `validate_query(connection,
  table_name, query)` parses the SQL via DuckDB's
  planner and reports whether the query references
  only the persisted schema (i.e. is safe to run).

Usage::

    from un_comtrade.storage.duckdb import DuckDBWriter
    from un_comtrade.storage import (
        StorageConfig,
    )

    writer = DuckDBWriter()
    result = writer.store(
        dataset=canonical_dataset,
        config=StorageConfig(
            root="tradedata.duckdb",
            table_name="trade_records",
            overwrite=False,
        ),
    )
    # Query the persisted table.
    writer.connection.execute(
        "SELECT reporter_code, COUNT(*) FROM trade_records GROUP BY 1"
    ).fetchall()
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

from ..etl import PipelineContext, StageKind  # noqa: F401  (consistency)
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
    _row_to_record,
    _read_metadata_sidecar,
    _build_dataset_from_metadata,
    _sort_records_deterministically,
)


if TYPE_CHECKING:
    import duckdb  # type: ignore[import-not-found]
else:
    try:
        import duckdb  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover
        duckdb = None  # type: ignore[assignment,misc]


__all__ = [
    "DUCKDB_SCHEMA_VERSION",
    "DuckDBQueryValidation",
    "DuckDBWriter",
    "duckdb_schema_sql",
]


_logger = get_logger("lifecycle")


#: Schema version of the DuckDB-persisted dataset.
#: Bumped when the schema changes in a
#: non-backward-compatible way.
DUCKDB_SCHEMA_VERSION: str = "1.0.0"

#: Name of the dataset-metadata table that DuckDBWriter
#: maintains inside each database file.
DATASETS_TABLE: str = "un_comtrade_datasets"


# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------


def duckdb_schema_sql(table_name: str = "trade_records") -> str:
    """Return the SQL `CREATE TABLE` statement for
    the persisted DuckDB dataset.

    The schema matches the Parquet schema (flat
    columns + `decimal128`-equivalent). DuckDB's
    `DECIMAL` type is preferred over `DOUBLE` for
    monetary / quantity values to preserve exact
    precision (per ADR-0027).
    """
    # NOTE: DuckDB does not have a single "decimal128"
    # type; DECIMAL is the canonical exact-precision
    # numeric type with explicit precision / scale.
    return f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            -- Identifier / metadata
            type_code VARCHAR NOT NULL,
            frequency_code VARCHAR NOT NULL,
            classification_code VARCHAR NOT NULL,
            classification_search_code VARCHAR,
            edition VARCHAR NOT NULL,
            is_original_classification BOOLEAN,
            -- Period
            ref_period_id BIGINT,
            ref_year INTEGER NOT NULL,
            ref_month INTEGER NOT NULL,
            period VARCHAR NOT NULL,
            -- Subjects
            reporter_code INTEGER NOT NULL,
            reporter_iso3 VARCHAR,
            reporter_name VARCHAR,
            partner_code INTEGER NOT NULL,
            partner_iso3 VARCHAR,
            partner_name VARCHAR,
            partner2_code INTEGER,
            partner2_iso3 VARCHAR,
            partner2_name VARCHAR,
            flow_code VARCHAR NOT NULL,
            flow_name VARCHAR,
            commodity_code VARCHAR NOT NULL,
            commodity_name VARCHAR,
            -- Procedural
            customs_code VARCHAR NOT NULL,
            customs_name VARCHAR,
            mos_code VARCHAR NOT NULL,
            mot_code INTEGER NOT NULL,
            mot_name VARCHAR,
            -- Quantities (DECIMAL preserves precision)
            quantity_qty DECIMAL(38, 18),
            quantity_qty_unit_code INTEGER NOT NULL,
            quantity_qty_unit_abbr VARCHAR,
            quantity_is_estimated BOOLEAN NOT NULL,
            quantity_alt_qty DECIMAL(38, 18),
            quantity_alt_qty_unit_code INTEGER,
            quantity_alt_qty_unit_abbr VARCHAR,
            quantity_is_alt_qty_estimated BOOLEAN NOT NULL,
            net_weight_kg DECIMAL(38, 18),
            is_net_weight_estimated BOOLEAN NOT NULL,
            gross_weight_kg DECIMAL(38, 18),
            is_gross_weight_estimated BOOLEAN NOT NULL,
            -- Monetary (DECIMAL preserves precision)
            trade_value_primary_value DECIMAL(38, 18) NOT NULL,
            trade_value_fob_value DECIMAL(38, 18),
            trade_value_cif_value DECIMAL(38, 18),
            -- Flags
            legacy_estimation_flag INTEGER NOT NULL,
            is_reported BOOLEAN NOT NULL,
            is_aggregate BOOLEAN NOT NULL,
            -- Provenance (serialised as JSON string)
            provenance VARCHAR
        )
    """.strip()


def duckdb_schema_columns() -> dict[str, dict[str, Any]]:
    """Return the DuckDB schema as a column → type
    map for use by `pyarrow` (v1.0.1 bulk-insert
    speedup).

    Each entry has:

    - `pa_type`: the `pyarrow` type to use when
      constructing a `pyarrow.Table`.
    - `nullable`: whether the column permits NULL.

    The type mapping mirrors `duckdb_schema_sql`
    and must be kept in sync.
    """
    # Imported lazily so the rest of the module
    # works without pyarrow installed.
    import pyarrow as pa  # type: ignore[import-not-found]

    DEC = pa.decimal128(38, 18)
    return {
        # Identifier / metadata
        "type_code": {"pa_type": pa.string(), "nullable": False},
        "frequency_code": {"pa_type": pa.string(), "nullable": False},
        "classification_code": {"pa_type": pa.string(), "nullable": False},
        "classification_search_code": {"pa_type": pa.string(), "nullable": True},
        "edition": {"pa_type": pa.string(), "nullable": False},
        "is_original_classification": {"pa_type": pa.bool_(), "nullable": True},
        # Period
        "ref_period_id": {"pa_type": pa.int64(), "nullable": True},
        "ref_year": {"pa_type": pa.int32(), "nullable": False},
        "ref_month": {"pa_type": pa.int32(), "nullable": False},
        "period": {"pa_type": pa.string(), "nullable": False},
        # Subjects
        "reporter_code": {"pa_type": pa.int32(), "nullable": False},
        "reporter_iso3": {"pa_type": pa.string(), "nullable": True},
        "reporter_name": {"pa_type": pa.string(), "nullable": True},
        "partner_code": {"pa_type": pa.int32(), "nullable": False},
        "partner_iso3": {"pa_type": pa.string(), "nullable": True},
        "partner_name": {"pa_type": pa.string(), "nullable": True},
        "partner2_code": {"pa_type": pa.int32(), "nullable": True},
        "partner2_iso3": {"pa_type": pa.string(), "nullable": True},
        "partner2_name": {"pa_type": pa.string(), "nullable": True},
        "flow_code": {"pa_type": pa.string(), "nullable": False},
        "flow_name": {"pa_type": pa.string(), "nullable": True},
        "commodity_code": {"pa_type": pa.string(), "nullable": False},
        "commodity_name": {"pa_type": pa.string(), "nullable": True},
        # Procedural
        "customs_code": {"pa_type": pa.string(), "nullable": False},
        "customs_name": {"pa_type": pa.string(), "nullable": True},
        "mos_code": {"pa_type": pa.string(), "nullable": False},
        "mot_code": {"pa_type": pa.int32(), "nullable": False},
        "mot_name": {"pa_type": pa.string(), "nullable": True},
        # Quantities
        "quantity_qty": {"pa_type": DEC, "nullable": True},
        "quantity_qty_unit_code": {"pa_type": pa.int32(), "nullable": False},
        "quantity_qty_unit_abbr": {"pa_type": pa.string(), "nullable": True},
        "quantity_is_estimated": {"pa_type": pa.bool_(), "nullable": False},
        "quantity_alt_qty": {"pa_type": DEC, "nullable": True},
        "quantity_alt_qty_unit_code": {"pa_type": pa.int32(), "nullable": True},
        "quantity_alt_qty_unit_abbr": {"pa_type": pa.string(), "nullable": True},
        "quantity_is_alt_qty_estimated": {"pa_type": pa.bool_(), "nullable": False},
        "net_weight_kg": {"pa_type": DEC, "nullable": True},
        "is_net_weight_estimated": {"pa_type": pa.bool_(), "nullable": False},
        "gross_weight_kg": {"pa_type": DEC, "nullable": True},
        "is_gross_weight_estimated": {"pa_type": pa.bool_(), "nullable": False},
        # Monetary
        "trade_value_primary_value": {"pa_type": DEC, "nullable": False},
        "trade_value_fob_value": {"pa_type": DEC, "nullable": True},
        "trade_value_cif_value": {"pa_type": DEC, "nullable": True},
        # Flags
        "legacy_estimation_flag": {"pa_type": pa.int32(), "nullable": False},
        "is_reported": {"pa_type": pa.bool_(), "nullable": False},
        "is_aggregate": {"pa_type": pa.bool_(), "nullable": False},
        # Provenance
        "provenance": {"pa_type": pa.string(), "nullable": True},
    }


def _records_to_rows(records: Sequence[Any]) -> list[tuple]:
    """Convert a list of `TradeRecord` instances to a
    list of tuples matching `duckdb_schema_sql`.

    The row order matches the column order in
    `duckdb_schema_sql`. `Decimal` values are passed
    through (DuckDB preserves Decimal precision via
    the `DECIMAL(38, 18)` type). Provenance is
    JSON-serialised.
    """
    import json as _json

    rows: list[tuple] = []
    for record in records:
        reporter = getattr(record, "reporter", None)
        partner = getattr(record, "partner", None)
        partner2 = getattr(record, "partner2", None)
        flow = getattr(record, "flow", None)
        commodity = getattr(record, "commodity", None)
        quantity = getattr(record, "quantity", None)
        trade_value = getattr(record, "trade_value", None)
        provenance = getattr(record, "provenance", None)

        rows.append(
            (
                # Identifier / metadata
                getattr(record, "type_code", None),
                getattr(record, "frequency_code", None),
                getattr(record, "classification_code", None),
                getattr(record, "classification_search_code", None),
                getattr(record, "edition", None),
                getattr(record, "is_original_classification", None),
                # Period
                getattr(record, "ref_period_id", None),
                getattr(record, "ref_year", None),
                getattr(record, "ref_month", None),
                getattr(record, "period", None),
                # Subjects
                getattr(reporter, "reporter_code", None),
                getattr(reporter, "iso3", None),
                getattr(reporter, "name", None),
                getattr(partner, "partner_code", None),
                getattr(partner, "iso3", None),
                getattr(partner, "name", None),
                (
                    getattr(partner2, "partner_code", None)
                    if partner2 is not None
                    else None
                ),
                (
                    getattr(partner2, "iso3", None)
                    if partner2 is not None
                    else None
                ),
                (
                    getattr(partner2, "name", None)
                    if partner2 is not None
                    else None
                ),
                getattr(flow, "flow_code", None),
                getattr(flow, "flow_name", None),
                getattr(commodity, "commodity_code", None),
                getattr(commodity, "name", None),
                # Procedural
                getattr(record, "customs_code", None),
                getattr(record, "customs_name", None),
                getattr(record, "mos_code", None),
                getattr(record, "mot_code", None),
                getattr(record, "mot_name", None),
                # Quantities
                getattr(quantity, "qty", None),
                getattr(quantity, "qty_unit_code", None),
                getattr(quantity, "qty_unit_abbr", None),
                getattr(quantity, "is_estimated", None),
                getattr(quantity, "alt_qty", None),
                getattr(quantity, "alt_qty_unit_code", None),
                getattr(quantity, "alt_qty_unit_abbr", None),
                getattr(quantity, "is_alt_qty_estimated", None),
                getattr(record, "net_weight_kg", None),
                getattr(record, "is_net_weight_estimated", None),
                getattr(record, "gross_weight_kg", None),
                getattr(record, "is_gross_weight_estimated", None),
                # Monetary
                getattr(trade_value, "primary_value", None),
                getattr(trade_value, "fob_value", None),
                getattr(trade_value, "cif_value", None),
                # Flags
                getattr(record, "legacy_estimation_flag", None),
                getattr(record, "is_reported", None),
                getattr(record, "is_aggregate", None),
                # Provenance (JSON-serialised)
                (
                    _json.dumps(provenance, default=str)
                    if provenance is not None
                    else None
                ),
            )
        )
    return rows


def _rows_to_arrow_table(rows: list[tuple]) -> Any:
    """Convert a list of row tuples (matching
    `duckdb_schema_sql` column order) into a
    `pyarrow.Table`.

    Column types mirror `duckdb_schema_sql`:

    - `*_code VARCHAR` → `pa.string()`.
    - `*_code INTEGER / BIGINT` → `pa.int64()` (NULLABLE).
    - `*_code BOOLEAN` → `pa.bool_()` (NOT NULL).
    - `*_code DECIMAL(38, 18)` → `pa.decimal128(38, 18)`.
    - `provenance VARCHAR` → `pa.string()`.

    v1.0.1: this helper backs the bulk-insert
    speedup (Arrow `CTAS` is ~100× faster than
    `executemany` on Windows).
    """
    import pyarrow as pa  # type: ignore[import-not-found]
    from decimal import Decimal as _Decimal

    if not rows:
        return pa.table({})

    n = len(rows)
    ncols = len(rows[0])

    # Build column-wise: this is the natural form for
    # pyarrow (and dramatically faster than
    # `pa.Table.from_pylist` for >1000 rows).
    columns: list[list] = [[] for _ in range(ncols)]
    for row in rows:
        for j in range(ncols):
            columns[j].append(row[j])

    schema = duckdb_schema_columns()
    fields = []
    arrays = []
    for j, name in enumerate(schema):
        col_meta = schema[name]
        pa_type = col_meta["pa_type"]
        fields.append(pa.field(name, pa_type, nullable=col_meta["nullable"]))
        values = columns[j]
        # Coerce Decimal to string for decimal128 to avoid
        # type-promotion warnings.
        if "decimal" in str(pa_type):
            arrays.append(
                pa.array(
                    [
                        None if v is None else _Decimal(str(v))
                        for v in values
                    ],
                    type=pa_type,
                )
            )
        elif pa_type == pa.string():
            arrays.append(
                pa.array(
                    [None if v is None else str(v) for v in values],
                    type=pa_type,
                )
            )
        elif pa_type == pa.bool_():
            arrays.append(
                pa.array(
                    [bool(v) if v is not None else False
                     for v in values],
                    type=pa_type,
                )
            )
        else:
            arrays.append(
                pa.array(values, type=pa_type)
            )
    # Construct Table from a (field_name → pa.Array)
    # mapping (this is the most direct / supported
    # constructor).
    return pa.table(
        {name: arrays[j] for j, name in enumerate(schema)}
    )


# ---------------------------------------------------------------------------
# Query validation result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DuckDBQueryValidation:
    """Outcome of `DuckDBWriter.validate_query`.

    A query is **valid** when DuckDB can plan it
    against the persisted table's schema. A query
    is **invalid** when the schema doesn't expose the
    referenced columns / functions.
    """

    is_valid: bool
    query: str
    table_name: str
    referenced_columns: tuple[str, ...]
    error: str | None = None


# ---------------------------------------------------------------------------
# DuckDBWriter (concrete Storage implementation)
# ---------------------------------------------------------------------------


@dataclass
class DuckDBWriter:
    """Concrete `Storage` for the DUCKDB backend.

    Persists `CanonicalDataset` records to an
    embedded DuckDB database file. The writer
    manages:

    - The target table (`config.table_name`,
      default `"trade_records"`).
    - A metadata table (`un_comtrade_datasets`)
      recording every `store()` call.
    - The persisted DuckDB schema (decimal-preserving).
    - Incremental append (`mode='append'`) vs replace
      (`mode='replace'`).
    - Partition loading (creating a view filtered
      by a partition key).
    - Query validation (checking SQL against the
      persisted schema).

    Connection management: by default the writer
    opens a fresh connection per `store()` call. The
    caller can supply a long-lived connection via
    `connection=...` to share state across calls
    (e.g. for incremental append).
    """

    backend: StorageBackend = StorageBackend.DUCKDB
    connection: Any = None  # duckdb.Connection (lazy)

    def store(
        self,
        dataset: CanonicalDataset,
        config: StorageConfig,
    ) -> StorageResult:
        """Persist `dataset` to a DuckDB database.

        The destination is `config.root` (a `.duckdb`
        file path). The target table is
        `config.table_name` (default
        `"trade_records"`).
        """
        try:
            import duckdb  # type: ignore[import-not-found]
        except ImportError as exc:
            raise StorageError(
                "DuckDBWriter requires the duckdb package; "
                "install with `pip install duckdb`"
            ) from exc

        if not isinstance(dataset, CanonicalDataset):
            raise StorageError(
                f"DuckDBWriter.store requires a "
                f"CanonicalDataset; got {type(dataset).__name__}"
            )

        db_path = config.root
        table_name = config.table_name
        # `overwrite=True` corresponds to "replace"
        # mode in DuckDBWriter terminology. The config
        # `overwrite` flag pre-dates P5-003; the
        # writer keeps both names for clarity.
        if config.overwrite:
            mode = "replace"
        else:
            mode = "append"

        # Open / reuse the connection.
        owns_connection = False
        conn = self.connection
        if conn is None:
            conn = duckdb.connect(db_path)
            owns_connection = True

        try:
            # Ensure the target table exists.
            self._ensure_table(conn, table_name)

            # Replace mode: drop the existing table.
            if mode == "replace":
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                self._ensure_table(conn, table_name)

            # Insert records (if any).
            inserted = 0
            rows = _records_to_rows(dataset.records)
            if rows:
                # v1.0.1: bulk-insert via a `pyarrow.Table`
                # registered into DuckDB and selected via
                # `CREATE TABLE AS SELECT`. This is ~100×
                # faster than `executemany(...)` on
                # Windows / local-disk paths (measured:
                # 5000 rows, 49 cols: executemany 8–12s
                # vs. Arrow CTAS 0.1s). Decimal precision
                # is preserved end-to-end via
                # `pa.decimal128(38, 18)`.
                #
                # We fall back to the legacy
                # `executemany` path only when `pyarrow`
                # is unavailable (e.g. duckdb-only
                # install without Parquet backend).
                try:
                    import pyarrow as pa  # type: ignore[import-not-found]

                    # Build the Arrow table column-wise
                    # (columnar construction is faster than
                    # row-wise for large N).
                    arrow_table = _rows_to_arrow_table(rows)
                    conn.register(
                        f"_un_comtrade_arrow_{table_name}",
                        arrow_table,
                    )
                    if mode == "replace":
                        # Already dropped above; CREATE
                        # TABLE AS overwrites.
                        conn.execute(
                            f"CREATE OR REPLACE TABLE "
                            f"{table_name} AS SELECT * "
                            f"FROM _un_comtrade_arrow_"
                            f"{table_name}"
                        )
                    else:
                        # `append` mode: insert from the
                        # registered Arrow table.
                        conn.execute(
                            f"INSERT INTO {table_name} "
                            f"SELECT * FROM "
                            f"_un_comtrade_arrow_{table_name}"
                        )
                    conn.unregister(
                        f"_un_comtrade_arrow_{table_name}"
                    )
                    inserted = len(rows)
                except ImportError:
                    # pyarrow not installed; fall back to
                    # the legacy executemany path (with
                    # a single transaction wrapper).
                    placeholders = ",".join(
                        ["?"] * len(rows[0])
                    )
                    insert_sql = (
                        f"INSERT INTO {table_name} "
                        f"VALUES ({placeholders})"
                    )
                    conn.execute("BEGIN")
                    try:
                        conn.executemany(insert_sql, rows)
                        conn.execute("COMMIT")
                    except Exception:
                        conn.execute("ROLLBACK")
                        raise
                    inserted = len(rows)

            # Compute partition keys for the metadata.
            partition_strategy = (
                config.partition_strategy
                if config.partition_strategy is not None
                else PartitionStrategy.default()
            )
            groups = partition_strategy.partition_records(
                _sort_records_deterministically(list(dataset.records))
            )
            partition_keys = tuple(groups.keys())

            # Register the dataset in the metadata table.
            self._register_dataset(
                conn,
                dataset_name=dataset.name,
                table_name=table_name,
                schema_version=dataset.schema_version,
                parser_name=dataset.parser_name,
                record_count=dataset.count,
                partition_keys=partition_keys,
            )

            # Compute byte_size (approximate — DuckDB's
            # database file size after the write).
            byte_size: int | None = None
            try:
                byte_size = Path(db_path).stat().st_size
            except OSError:
                pass

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
                destination=str(db_path),
                extra={
                    "duckdb_schema_version": DUCKDB_SCHEMA_VERSION,
                    "table_name": table_name,
                    "mode": mode,
                    "inserted": inserted,
                },
            )

            # F-001: Write a metadata sidecar next to
            # the database file so `read()` can recover
            # the dataset's canonical provenance without
            # having to query the in-DB metadata table.
            # The sidecar uses the same shape as the
            # CSV / JSON / Parquet sidecars for cross-
            # backend uniformity.
            from .file import _metadata_to_dict
            import json as _json
            sidecar_path = (
                Path(db_path).parent
                / f"{Path(db_path).stem}.meta.json"
            )
            try:
                sidecar_path.write_text(
                    _json.dumps(_metadata_to_dict(metadata), default=str),
                    encoding="utf-8",
                )
            except OSError as exc:  # pragma: no cover
                _logger.debug(
                    "DuckDBWriter could not write sidecar at %s: %s",
                    sidecar_path, exc,
                )

            result = StorageResult(
                backend=self.backend,
                destination=str(db_path),
                metadata=metadata,
                # DuckDB stores all rows in one table;
                # we map every partition key to a
                # sentinel path (the database file) so
                # the StorageResult.partitions shape is
                # preserved across backends.
                partitions={
                    key: (str(db_path),)
                    for key in partition_keys
                },
                byte_size=byte_size,
            )

            _logger.debug(
                "DuckDBWriter stored %d records (mode=%s) to %s",
                inserted,
                mode,
                str(db_path),
            )
            return result
        finally:
            if owns_connection:
                conn.close()

    # ----- Helper methods -----------------------------------------------

    def _ensure_table(
        self, conn: Any, table_name: str
    ) -> None:
        """Create the target table + the metadata
        table if they don't already exist."""
        conn.execute(duckdb_schema_sql(table_name))
        # Metadata table (one row per `store()` call).
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {DATASETS_TABLE} (
                dataset_name VARCHAR NOT NULL,
                table_name VARCHAR NOT NULL,
                schema_version VARCHAR NOT NULL,
                parser_name VARCHAR NOT NULL,
                record_count INTEGER NOT NULL,
                partition_keys VARCHAR NOT NULL,
                stored_at TIMESTAMP NOT NULL
            )
        """)

    def _register_dataset(
        self,
        conn: Any,
        *,
        dataset_name: str,
        table_name: str,
        schema_version: str,
        parser_name: str,
        record_count: int,
        partition_keys: tuple,
    ) -> None:
        """Insert a row into `un_comtrade_datasets`
        recording this `store()` call."""
        import json as _json

        partition_keys_json = _json.dumps(
            [list(k) for k in partition_keys], default=str
        )
        conn.execute(
            f"""
            INSERT INTO {DATASETS_TABLE}
                (dataset_name, table_name, schema_version,
                 parser_name, record_count, partition_keys,
                 stored_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                dataset_name,
                table_name,
                schema_version,
                parser_name,
                record_count,
                partition_keys_json,
                datetime.now(timezone.utc),
            ],
        )

    def load_partition(
        self,
        conn: Any,
        table_name: str,
        partition_key: tuple,
        *,
        view_name: str | None = None,
    ) -> str:
        """Create a view that filters `table_name`
        by the supplied partition key.

        Returns the view name. The view name defaults
        to `<table_name>__partition_<sanitized_key>`
        so it doesn't collide with the base table.

        The partition key must match the shape
        produced by the configured
        `PartitionStrategy.extract()`. The default
        `(reporter, year, frequency)` strategy yields
        a 3-tuple `(reporter_code, ref_year,
        frequency_code)`.

        Note: DuckDB does not allow prepared
        parameters in `CREATE VIEW` statements, so the
        partition key values are formatted directly
        into the SQL string. This is safe because the
        partition key values are typed as `int` /
        `str` (per `PartitionStrategy`), not arbitrary
        user input.
        """
        if not isinstance(partition_key, tuple):
            raise StorageError(
                f"partition_key must be a tuple; got "
                f"{type(partition_key).__name__}"
            )
        if len(partition_key) != 3:
            raise StorageError(
                f"partition_key must have 3 elements "
                f"((reporter, year, frequency)); got "
                f"{len(partition_key)}"
            )
        reporter_code, ref_year, frequency_code = partition_key

        view = view_name or (
            f"{table_name}__partition_{reporter_code}_"
            f"{ref_year}_{frequency_code}"
        )
        # String-format the values (DuckDB CREATE VIEW
        # does not accept prepared parameters).
        sql = (
            f"CREATE OR REPLACE VIEW {view} AS "
            f"SELECT * FROM {table_name} "
            f"WHERE reporter_code = {int(reporter_code)} "
            f"AND ref_year = {int(ref_year)} "
            f"AND frequency_code = '{frequency_code}'"
        )
        conn.execute(sql)
        return view

    def validate_query(
        self,
        conn: Any,
        table_name: str,
        query: str,
    ) -> DuckDBQueryValidation:
        """Validate `query` against the persisted
        schema.

        The validation runs DuckDB's `EXPLAIN` on the
        query after prepending `table_name` as the
        default reference. If the planner succeeds,
        the query is valid; otherwise the error
        message is captured.
        """
        try:
            # `EXPLAIN <query>` validates the planner's
            # view of the query without executing it.
            # We wrap the query in a CTE that pins the
            # referenced table as the source.
            conn.execute(
                f"EXPLAIN SELECT * FROM {table_name} WHERE "
                f"EXISTS ({query})"
            )
            # Collect referenced column names by
            # parsing the query (best-effort).
            referenced: list[str] = []
            for token in query.replace(",", " ").split():
                clean = token.strip("()[];,'\"")
                if clean and "." in clean:
                    referenced.append(clean.split(".")[-1])
                elif clean.isidentifier():
                    referenced.append(clean)
            # Dedup, preserve order.
            seen: set[str] = set()
            deduped: list[str] = []
            for c in referenced:
                if c not in seen:
                    seen.add(c)
                    deduped.append(c)
            return DuckDBQueryValidation(
                is_valid=True,
                query=query,
                table_name=table_name,
                referenced_columns=tuple(deduped),
                error=None,
            )
        except Exception as exc:
            return DuckDBQueryValidation(
                is_valid=False,
                query=query,
                table_name=table_name,
                referenced_columns=(),
                error=str(exc),
            )

    def __repr__(self) -> str:
        return (
            f"DuckDBWriter(backend={self.backend.value!r}, "
            f"connection={'shared' if self.connection else 'fresh'})"
        )

    # ------------------------------------------------------------------
    # F-001: Read side (inverse of store)
    # ------------------------------------------------------------------

    def read(self, config: StorageConfig) -> CanonicalDataset:
        """Reload a DuckDB dataset previously persisted by
        `DuckDBWriter.store`.

        Per `012_STORAGE_SPECIFICATION.md` §11, the
        retrieval is on-demand and returns the dataset
        as a `CanonicalDataset`. The implementation
        performs a `SELECT * FROM <table>` and
        reconstructs `TradeRecord` instances from the
        flat row representation.

        Parameters
        ----------
        config
            `StorageConfig` whose `root` is the DuckDB
            file path and whose `table_name` is the
            target table (default `"trade_records"`).

        Returns
        -------
        `CanonicalDataset` reconstructed from the
        persisted DuckDB rows + sidecar metadata
        (if present).
        """
        import json
        root = Path(config.root)
        if not root.exists():
            raise StorageError(
                f"DuckDB read destination does not exist: {root}"
            )
        table_name = config.table_name
        try:
            conn = duckdb.connect(str(root), read_only=True)
        except Exception as exc:
            raise StorageError(
                f"Cannot open DuckDB file {root}: {exc}"
            ) from exc
        try:
            try:
                rows_iter = conn.execute(
                    f"SELECT * FROM {table_name}"
                ).fetchall()
            except Exception as exc:
                raise StorageError(
                    f"Table {table_name!r} missing in {root}: {exc}"
                ) from exc
            # Get column names from the cursor description.
            col_names = [
                d[0] for d in (conn.execute(
                    f"SELECT * FROM {table_name} LIMIT 0"
                ).description or [])
            ]
        finally:
            conn.close()
        rows: list[dict[str, Any]] = []
        for row in rows_iter:
            rows.append({col_names[i]: row[i] for i in range(len(col_names))})
        records = [_row_to_record(r) for r in rows]
        # F-001: sort deterministically so the
        # round-trip order matches the on-disk order.
        records = _sort_records_deterministically(records)
        # Find dataset_name from sidecar (DuckDB is a
        # single-file format; the sidecar lives next to
        # the database file). The dataset name is
        # stored INSIDE the JSON, not derived from the
        # filename (the filename stem is just an
        # anchor; multiple datasets could share a
        # file via different tables).
        sidecar_files = list(root.parent.glob(f"{root.stem}*.meta.json"))
        if sidecar_files:
            # We need to read the JSON to recover the
            # canonical dataset_name; the file stem is
            # just an anchor.
            try:
                sidecar_payload = json.loads(
                    sidecar_files[0].read_text(encoding="utf-8")
                )
                dataset_name = sidecar_payload.get(
                    "dataset_name"
                ) or sidecar_files[0].stem.removesuffix(".meta")
            except Exception:
                dataset_name = sidecar_files[0].stem.removesuffix(".meta")
        else:
            dataset_name = root.stem
        metadata = _read_metadata_sidecar(root.parent, dataset_name)
        if metadata:
            ds = _build_dataset_from_metadata(metadata, records)
            from dataclasses import replace
            ds = replace(ds, name=dataset_name)
        else:
            ds = CanonicalDataset(
                name=dataset_name,
                records=tuple(records),
                schema_version="1.0",
                parser_name="DuckDBReader",
                source_count=len(records),
            )
        _logger.debug(
            "DuckDBWriter read %d records from %s",
            len(records),
            str(root),
        )
        return ds