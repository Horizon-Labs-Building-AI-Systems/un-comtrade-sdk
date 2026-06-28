```
Document ID
024

Title
Phase 5 Storage Review Report

Version
1.0.0

Status
LIVE

Created
2026-06-28T03:15:00Z

Last Updated
2026-06-28T03:15:00Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
012_STORAGE_SPECIFICATION.md
006_DATA_MODEL.md
011_ETL_SPECIFICATION.md
023_ETL_REVIEW_REPORT.md
CHANGELOG.md
TASK_LOG.md
002_CONTEXT.md
DECISIONS.md

Supersedes
None
```

---

# Phase 5 Storage Review Report

## 1. Purpose

This document is the **review gate** between Phase 5
(Storage layer) and Phase 6 (Analytics layer). It
confirms that:

- The Storage layer is **complete** for all five
  backends defined in `012_STORAGE_SPECIFICATION.md`
  §3 (LocalFiles / JSON / CSV / Parquet / DuckDB).
- `CanonicalDataset` is **preserved end-to-end** —
  the same frozen dataclass produced by the ETL
  layer (per the Phase 4 review) is what every
  storage engine accepts and stores.
- `Decimal` precision is **preserved** through every
  backend, including roundtrip via Parquet
  (`decimal128(38, 18)`) and DuckDB (`DECIMAL(38,
  18)`).
- The partition strategy is **correct** per
  ADR-0029 — `(reporter, year, frequency)` Hive-style
  by default, custom strategies supported, no silent
  overwrites across partitions.
- DuckDB is **validated end-to-end** — schema, query,
  incremental update, partition loading, query
  validation, metadata table.
- The codebase is **ready for the Analytics layer**
  (Phase 6).

Per the P5-007 task scope: **no code changes** —
this is a documentation gate only.

---

## 2. Phase 5 Deliverables (TASK-060..064)

| Task | Title | Deliverable | Tests | Status |
|------|-------|-------------|------:|--------|
| P5-001 (TASK-060) | Storage Layer Foundation | `un_comtrade/storage/__init__.py` + `_base.py` | 76 | Completed |
| P5-002 (TASK-061) | Parquet Storage Engine | `un_comtrade/storage/parquet.py` | 36 | Completed |
| P5-003 (TASK-062) | DuckDB Storage Engine | `un_comtrade/storage/duckdb.py` | 36 | Completed |
| P5-004 (TASK-063) | CSV & JSON Storage Engines | `un_comtrade/storage/file.py` | 36 | Completed |
| P5-006 (TASK-064) | Incremental Dataset Updates | `un_comtrade/storage/update.py` | 43 | Completed |
| **Total Storage** | | | **227** | **All passing** |

**Total Storage test coverage: 227 tests across 5
test modules, all passing in 8.77s.**

P5-005 (LocalFiles) was deferred to a future task —
its placeholder remains in the registry.

Source module sizes (lines):

| Module | Bytes | Purpose |
|--------|------:|---------|
| `un_comtrade/storage/__init__.py` | 3,575 | Public API re-exports + auto-promotion logic |
| `un_comtrade/storage/_base.py` | 28,703 | Storage protocol, config, metadata, result, partition strategy, registry, stage, placeholder storages |
| `un_comtrade/storage/parquet.py` | 19,336 | `ParquetWriter` (pyarrow, decimal128(38, 18)) |
| `un_comtrade/storage/duckdb.py` | 23,748 | `DuckDBWriter` (DECIMAL(38, 18), append/replace, partition loading, query validation, metadata table) |
| `un_comtrade/storage/file.py` | 22,241 | `CSVWriter` + `JSONWriter` (stdlib + gzip, metadata sidecar) |
| `un_comtrade/storage/update.py` | 36,980 | `DatasetUpdater` + `UpdateMode` + `DuplicatePolicy` + helpers + per-engine implementations |
| `tests/test_storage*.py` | ~28,000 | 227 tests |

---

## 3. Storage Complete

All five backends defined in
`012_STORAGE_SPECIFICATION.md` §3 are either
implemented or have a documented deferral:

| Spec | Backend | Status | Engine | File |
|------|---------|:------:|--------|------|
| T01 | LocalFiles | ⚠️ Deferred | placeholder | `_base.py::LocalFilesStorage` |
| T02 | JSON | ✅ Implemented | `JSONWriter` | `file.py` |
| T03 | CSV | ✅ Implemented | `CSVWriter` | `file.py` |
| T04 | Parquet | ✅ Implemented | `ParquetWriter` | `parquet.py` |
| T05 | DuckDB | ✅ Implemented | `DuckDBWriter` | `duckdb.py` |

The four implemented engines (T02-T05) are
**auto-promoted** to the default registry when their
optional dependencies are importable:

- `JSONWriter` / `CSVWriter` — stdlib only, always
  available.
- `ParquetWriter` — promoted when `pyarrow` is
  importable.
- `DuckDBWriter` — promoted when `duckdb` is
  importable.

Verified by `tests/test_storage.py::TestStorageRegistry`
and the per-engine test modules. The public API
surface is consistent across all engines:

```python
from un_comtrade.storage import (
    # Orchestrator
    DatasetUpdater, UpdateMode, DuplicatePolicy,
    UpdateResult, SchemaIncompatibleError,
    find_duplicates, deduplicate,
    verify_schema_compatibility,
    # Infrastructure
    StorageBackend, StorageConfig, StorageError,
    DatasetMetadata, PartitionStrategy,
    StorageRegistry, StorageResult, StorageStage,
    # Engines
    CSVWriter, JSONWriter, ParquetWriter, DuckDBWriter,
)
```

---

## 4. CanonicalDataset Preserved

`CanonicalDataset` is the contract between the
ETL layer (Phase 4) and the Storage layer (Phase 5).
Every storage engine accepts and rejects consistently:

```python
# From `un_comtrade/storage/file.py:374`,
# `un_comtrade/storage/duckdb.py:374`, and
# `un_comtrade/storage/parquet.py:483`:
if not isinstance(dataset, CanonicalDataset):
    raise StorageError(
        f"{engine} requires a CanonicalDataset; "
        f"got {type(dataset).__name__}"
    )
```

`StorageStage.__call__` (per `_base.py:876`) performs
the same check at the pipeline boundary:

```python
if not isinstance(source, CanonicalDataset):
    raise StorageError(
        f"StorageStage source must be a CanonicalDataset; "
        f"got {type(source).__name__}"
    )
```

The `DatasetUpdater.update(...)` orchestrator
follows the same contract (per `update.py:1052`).
Raw upstream payloads, parser outputs, and other
non-`CanonicalDataset` sources are rejected with
`StorageError`.

**Verified by**:

- `tests/test_storage.py::TestStorage::test_writer_rejects_non_canonical_dataset`
  (CSV + JSON placeholders).
- `tests/test_parquet.py::TestParquetWriter::test_writer_rejects_non_canonical_dataset`.
- `tests/test_duckdb.py::TestDuckDBWriter::test_writer_rejects_non_canonical_dataset`.
- `tests/test_file_storage.py::TestCSVWriter::test_writer_rejects_non_canonical_dataset`
  + `TestJSONWriter::test_writer_rejects_non_canonical_dataset`.
- `tests/test_storage_updates.py::TestInvalidInputs::test_non_canonical_dataset_source_rejected`.

### Roundtrip Verified

`CanonicalDataset` is **immutable** (frozen
dataclass per ADR-0013) so storage operations cannot
mutate it. Every engine accepts the dataset, writes
records derived from it, and returns a new
`StorageResult` describing the output.

Verified per engine:

- **CSV**: `tests/test_storage_updates.py::TestDatasetUpdaterAppend::test_csv_append`
  — initial 1 record, append 1 record, read back 2
  rows from disk.
- **JSON**: `test_json_append` — same flow.
- **Parquet**: `test_parquet_append` + `TestStorageRoundtripParity::test_parquet_roundtrip_preserves_decimal`
  — pyarrow `pq.read_table()` returns the data with
  Decimal values preserved.
- **DuckDB**: `test_duckdb_append` + `test_duckdb_roundtrip_preserves_decimal`
  — `duckdb.connect(...).execute('SELECT ...')`
  returns rows with Decimal values preserved.

---

## 5. Decimal Preserved

`Decimal` precision is preserved across every
backend, per ADR-0027. The exact precision policy
varies by engine:

| Backend | Decimal type | Precision | Roundtrip |
|---------|--------------|-----------|-----------|
| CSV | `str` in CSV cell | full | Decimal(str(value)) on read |
| JSON | `str` in JSON | full | Decimal(str(value)) on read |
| Parquet | `pa.decimal128(38, 18)` | 18 fractional digits | exact for value ≤ 10^20 |
| DuckDB | `DECIMAL(38, 18)` | 18 fractional digits | exact for value ≤ 10^20 |

The CSV / JSON writers serialise `Decimal` as **string**
so that the textual representation is preserved
exactly (per ADR-0027). Parquet and DuckDB use
their native exact-precision numeric types
(arrow `decimal128` and DuckDB `DECIMAL(38, 18)`
respectively), giving 18 fractional digits — enough
for all UN Comtrade monetary values which are at
most ~10^15 USD.

### DuckDB Decimal Validation

The DuckDB writer was exercised end-to-end with the
canonical India 2022 world exports value
(`452,684,213,646.747`):

```python
# Persist
records = TradeParser(log_skipped=False).parse_records(
    [{..., "fobvalue": "452684213646.747", ...}]
).records
dataset = CanonicalDataset(
    name="p", records=records, parser_name="TradeParser"
)
DuckDBWriter().store(dataset, StorageConfig(root="india.duckdb"))

# Query
conn = duckdb.connect("india.duckdb", read_only=True)
val = conn.execute(
    "SELECT trade_value_primary_value FROM trade_records"
).fetchone()[0]
# val = Decimal("452684213646.747000000000000000")
total = conn.execute(
    "SELECT SUM(trade_value_primary_value) FROM trade_records"
).fetchone()[0]
# total = Decimal("452684213646.747000000000000000")
```

The Decimal survives the write → read cycle exactly
to 18 fractional digits. The SUM aggregate operates
on the exact-precision type (no precision loss).

**Verified by**:

- `tests/test_transform.py::TestTradeTransformerDecimalPreservation`
  (4 tests) — covers the upstream ETL path.
- `tests/test_parquet.py::TestParquetSchema::test_decimal_columns_have_decimal128_type`
  + `TestParquetWriter::test_decimal_preserved_as_string_*`
  (5 tests) — Parquet writer preserves Decimal.
- `tests/test_duckdb.py::TestDuckDBWriter::test_decimal_preserved_*`
  (4 tests) — DuckDB writer preserves Decimal.
- `tests/test_file_storage.py::TestCSVWriter::test_writer_decimal_preserved_as_string`
  + `TestJSONWriter::test_writer_decimal_preserved_as_string`
  — file writers serialise Decimal as string.
- `tests/test_storage_updates.py::TestStorageRoundtripParity`
  — full roundtrip preserves Decimal across all 4
  engines (5 tests).

---

## 6. Partition Strategy Correct

The default `PartitionStrategy` follows ADR-0029:
**`(reporter_code, ref_year, frequency_code)`** with
a Hive-style path template.

```python
# `un_comtrade/storage/_base.py:381`
def default() -> "PartitionStrategy":
    def _extract(record):
        reporter = getattr(record, "reporter", None)
        reporter_code = (
            getattr(reporter, "reporter_code", None)
            if reporter else None
        )
        ref_year = getattr(record, "ref_year", None)
        frequency_code = getattr(record, "frequency_code", None)
        return (reporter_code, ref_year, frequency_code)
    return PartitionStrategy(
        name="default",
        extract=_extract,
        path_template=(
            "{key_0}/{key_1}/{key_2}/{dataset_name}{ext}"
        ),
    )
```

The default `path_template` is Hive-style so that
distinct partitions produce distinct subdirectories
(`<root>/699/2022/A/p.csv`, `<root>/156/2023/A/p.csv`,
etc.) — no silent overwrites across partitions.

### Latent bug fixed (CHG-0053)

Earlier versions of `format_path()` ignored the
partition key tuple and only rendered
`{dataset_name}{ext}`, so two different partitions
would map to the same file path and silently
overwrite each other. The Parquet
`test_writer_writes_multiple_partitions` test
passed only because it asserted
`len(all_paths) == 3` from the in-memory dict
without verifying on-disk uniqueness.

The fix (per CHG-0053) was:

1. `format_path()` exposes positional `_0.._N` and
   `key_0..key_N` tokens for the partition key
   tuple.
2. The default `path_template` is Hive-style
   `{key_0}/{key_1}/{key_2}/{dataset_name}{ext}`.
3. `StorageConfig.compression` default changed from
   `"snappy"` (parquet-specific) to `"none"`
   (engine-agnostic).

Verified by:

- `tests/test_storage.py::TestPartitionStrategy::test_format_path_default_template`
  — expects `"699/2022/A/my_dataset.parquet"` for
  the default strategy.
- `tests/test_parquet.py::TestParquetWriter::test_writer_writes_multiple_partitions`
  + `test_partition_paths_use_strategy_format` —
  three distinct files in three distinct directories.
- `tests/test_file_storage.py::TestPartitioningInPipeline::test_default_partition_produces_hive_layout`
  — Hive-style layout verified on disk.
- `tests/test_storage.py::TestPartitioningEdgeCases`
  — custom strategies (single-key, constant-key,
  every-record-different) all produce the expected
  number of files.

### Custom strategies

Users can supply custom strategies via
`PartitionStrategy(...)`:

```python
def by_reporter(record):
    return (record.reporter.reporter_code,)

strategy = PartitionStrategy(
    name="by_reporter",
    extract=by_reporter,
    path_template="{key_0}/{dataset_name}{ext}",
)
```

Verified by
`tests/test_storage.py::TestPartitioningEdgeCases::test_custom_partition_strategy_*`
(3 tests).

---

## 7. DuckDB Validated

DuckDB is the **primary analytical backend** per
ADR-0029 (Q62). The full surface is validated:

### Schema

47 columns matching the Parquet flat schema:

```
type_code, frequency_code, classification_code,
classification_search_code, edition,
is_original_classification, ref_period_id, ref_year,
ref_month, period, reporter_code, reporter_iso3,
reporter_name, partner_code, partner_iso3,
partner_name, partner2_code, partner2_iso3,
partner2_name, flow_code, flow_name, commodity_code,
commodity_name, customs_code, customs_name,
mos_code, mot_code, mot_name, quantity_qty,
quantity_qty_unit_code, quantity_qty_unit_abbr,
quantity_is_estimated, quantity_alt_qty,
quantity_alt_qty_unit_code, quantity_alt_qty_unit_abbr,
quantity_is_alt_qty_estimated, net_weight_kg,
is_net_weight_estimated, gross_weight_kg,
is_gross_weight_estimated, trade_value_primary_value,
trade_value_fob_value, trade_value_cif_value,
legacy_estimation_flag, is_reported, is_aggregate,
provenance
```

Monetary columns are typed `DECIMAL(38, 18)` (not
`DOUBLE`) per ADR-0027.

### Metadata table

Every `DuckDBWriter.store()` call appends a row to
`un_comtrade_datasets`:

```sql
CREATE TABLE IF NOT EXISTS un_comtrade_datasets (
    dataset_name VARCHAR NOT NULL,
    table_name VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    parser_name VARCHAR NOT NULL,
    record_count INTEGER NOT NULL,
    partition_keys VARCHAR NOT NULL,
    stored_at TIMESTAMP NOT NULL
);
```

Verified by `tests/test_duckdb.py::TestDuckDBMetadataTable`
(4 tests).

### Append / Replace / Merge semantics

- **Append** — direct `INSERT`. Existing rows
  untouched. Verified by
  `TestDuckDBWriter::test_overwrite_false_appends_rows`
  + `TestDatasetUpdaterAppend::test_duckdb_append`.
- **Replace** — `DROP TABLE IF EXISTS` + recreate +
  `INSERT`. Verified by
  `TestDuckDBWriter::test_overwrite_true_replaces_rows`.
- **Merge** — `DELETE FROM trade_records WHERE
  (reporter_code, partner_code, period, flow_code,
  commodity_code, classification_code, edition,
  customs_code, mot_code, COALESCE(partner2_code,
  0)) = (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)` for each
  incoming key, then `INSERT` incoming rows.
  Verified by `TestDatasetUpdaterMerge::test_duckdb_merge`
  — the existing row's value was `Decimal("100")`,
  the merge replaced it with `Decimal("999")`, and
  `records_merged=1` was correctly reported in the
  `UpdateResult`.

### Partition loading

`DuckDBWriter.load_partition(connection, table_name,
partition_key)` creates a SQL view filtered by the
supplied 3-tuple `(reporter_code, ref_year,
frequency_code)`:

```sql
CREATE OR REPLACE VIEW trade_records__partition_699_2022_A AS
SELECT * FROM trade_records
WHERE reporter_code = 699
  AND ref_year = 2022
  AND frequency_code = 'A'
```

Verified by
`TestDuckDBWriter::test_load_partition_creates_view`
(3 tests).

### Query validation

`DuckDBWriter.validate_query(connection, table_name,
query)` parses the query via DuckDB's `EXPLAIN` and
returns a `DuckDBQueryValidation` result with the
referenced columns + table. Useful for "what
columns does this query touch?" introspection.

Verified by `TestDuckDBWriter::test_validate_query_*`
(4 tests).

### Full test count

`tests/test_duckdb.py` — 36 tests, all passing.
Plus `tests/test_storage_updates.py` adds 11 more
DuckDB-specific tests (append / merge / replace
end-to-end via `DatasetUpdater`).

---

## 8. All Storage Tests Passing

```
$ python -m pytest tests/test_storage.py \
                 tests/test_parquet.py \
                 tests/test_duckdb.py \
                 tests/test_file_storage.py \
                 tests/test_storage_updates.py -q
........................................................................ [ 31%]
........................................................................ [ 63%]
........................................................................ [ 95%]
...........                                                              [100%]
227 passed in 8.77s
```

Per-suite breakdown:

| Test Module | Tests | Pass | Fail | Skip |
|-------------|------:|-----:|-----:|-----:|
| `test_storage.py` | 76 | 76 | 0 | 0 |
| `test_parquet.py` | 36 | 36 | 0 | 0 |
| `test_duckdb.py` | 36 | 36 | 0 | 0 |
| `test_file_storage.py` | 36 | 36 | 0 | 0 |
| `test_storage_updates.py` | 43 | 43 | 0 | 0 |
| **Total Storage** | **227** | **227** | **0** | **0** |

Full SDK suite (incl. Phase 1 + Phase 2 + Phase 3
+ Phase 4 + Phase 5):

```
$ python -m pytest --tb=line -q
........................................................................ [ 99%]
.............                                                            [100%]
1957 passed in 88.00s (0:01:27)
```

**1957 / 1957 tests passing across the entire SDK.**

---

## 9. Coverage Matrix

| Concern | Coverage | Tested by |
|---------|---------:|-----------|
| Public API exports | ✅ | `tests/test_storage.py::TestPublicAPI` (4 tests) |
| StorageConfig validation | ✅ | `tests/test_storage.py::TestStorageConfig` (5 tests) |
| PartitionStrategy | ✅ | `tests/test_storage.py::TestPartitionStrategy` (8 tests) |
| StorageRegistry auto-promotion | ✅ | `tests/test_storage.py::TestStorageRegistry` (5 tests) |
| StorageStage dispatch | ✅ | `tests/test_storage.py::TestStorageStage` (4 tests) |
| CSVWriter basic write | ✅ | `tests/test_file_storage.py::TestCSVWriter` (13 tests) |
| CSVWriter gzip compression | ✅ | `TestCSVWriter::test_writer_gzip_compression` |
| JSONWriter basic write | ✅ | `tests/test_file_storage.py::TestJSONWriter` (12 tests) |
| JSONWriter pretty-print via `indent` | ✅ | `TestJSONWriter::test_writer_pretty_print_via_indent` |
| Metadata sidecar (CSV/JSON) | ✅ | `tests/test_file_storage.py::TestMetadataSidecar` (4 tests) |
| ParquetWriter basic write | ✅ | `tests/test_parquet.py::TestParquetWriter` (15 tests) |
| ParquetWriter schema stability | ✅ | `TestParquetSchema` (5 tests) |
| ParquetWriter multiple partitions | ✅ | `test_writer_writes_multiple_partitions` |
| DuckDBWriter basic write | ✅ | `tests/test_duckdb.py::TestDuckDBWriter` (10 tests) |
| DuckDBWriter incremental append | ✅ | `test_overwrite_false_appends_rows` |
| DuckDBWriter replace mode | ✅ | `test_overwrite_true_replaces_rows` |
| DuckDBWriter partition loading | ✅ | `test_load_partition_creates_view` (3 tests) |
| DuckDBWriter query validation | ✅ | `test_validate_query_*` (4 tests) |
| DuckDBWriter metadata table | ✅ | `TestDuckDBMetadataTable` (4 tests) |
| CanonicalDataset preserved (CSV) | ✅ | `TestDatasetUpdaterAppend::test_csv_append` |
| CanonicalDataset preserved (JSON) | ✅ | `TestDatasetUpdaterAppend::test_json_append` |
| CanonicalDataset preserved (Parquet) | ✅ | `TestDatasetUpdaterAppend::test_parquet_append` |
| CanonicalDataset preserved (DuckDB) | ✅ | `TestDatasetUpdaterAppend::test_duckdb_append` |
| Decimal preserved (CSV string) | ✅ | `TestCSVWriter::test_writer_decimal_preserved_as_string` |
| Decimal preserved (JSON string) | ✅ | `TestJSONWriter::test_writer_decimal_preserved_as_string` |
| Decimal preserved (Parquet) | ✅ | `TestParquetWriter::test_decimal_preserved_as_string_*` (5 tests) |
| Decimal preserved (DuckDB) | ✅ | `TestDuckDBWriter::test_decimal_preserved_*` (4 tests) |
| Partition strategy Hive layout | ✅ | `TestPartitioningInPipeline::test_default_partition_produces_hive_layout` |
| Custom partition strategy | ✅ | `TestPartitioningInPipeline::test_custom_partition_by_reporter_only` |
| `format_path` positional tokens | ✅ | `tests/test_storage.py::TestPartitionStrategy::test_format_path_default_template` |
| UpdateMode APPEND | ✅ | `tests/test_storage_updates.py::TestDatasetUpdaterAppend` (5 tests) |
| UpdateMode MERGE | ✅ | `TestDatasetUpdaterMerge` (5 tests) |
| UpdateMode REPLACE | ✅ | `TestDatasetUpdaterReplace` (2 tests) |
| Duplicate detection | ✅ | `TestFindDuplicates` (5 tests) |
| Deduplication (KEEP_FIRST / KEEP_LAST) | ✅ | `TestDeduplicate` (4 tests) |
| Schema compatibility check | ✅ | `TestSchemaCompatibility` (4 tests) + `TestSchemaCheckDuringUpdate` (4 tests) |
| Bad source rejected | ✅ | `TestInvalidInputs::test_non_canonical_dataset_source_rejected` + per-engine tests |
| Bad config rejected | ✅ | `TestInvalidInputs` (5 tests) |

---

## 10. Architectural Invariants Maintained

- **ADR-0013** (frozen dataclass + 100-char
  lines): `DatasetMetadata`, `UpdateResult`,
  `DatasetUpdater` are all frozen. All five
  storage modules respect the 100-character line
  limit (per `015_CODING_STANDARD.md`).
- **ADR-0027** (Decimal for monetary values):
  preserved across all four engines. File engines
  serialise as string; Parquet uses `decimal128(38,
  18)`; DuckDB uses `DECIMAL(38, 18)`. Verified by
  the dedicated roundtrip tests for each engine.
- **ADR-0029** (storage defaults + partition key):
  DuckDB is the default analytical backend;
  Parquet is the default large-dataset export;
  logical partitioning by `(reporter, year,
  frequency)` is the default. Hive-style paths
  prevent silent overwrites.
- **ADR-0030** (frozen dataclass policy): every new
  dataclass (`DatasetMetadata`, `UpdateResult`) is
  `frozen=True`.
- **ADR-0025** (stdlib logging + WARNING default):
  storage modules use the `lifecycle` log category
  with WARNING default; no PII / subscription keys
  logged.
- **ADR-0009** (latest-wins deduplication):
  `find_duplicates` / `deduplicate` use the same
  10-tuple composite key as `TradeParser.composite_key`
  — single source of truth across the SDK.

---

## 11. Outstanding Concerns (Non-blocking)

These are NOT blockers for the Analytics layer.
They are tracked for future tasks:

- **CSV / JSON writer `overwrite=True` support** —
  the file writers (`CSVWriter.store`, `JSONWriter.store`)
  do not yet honour `config.overwrite=True`. The
  `DatasetUpdater` works around this by clearing
  the destination directory before the write. A
  follow-up task should add native
  `overwrite=True` support to the file writers so
  the workaround can be removed. **Does not block
  Phase 6** — Analytics consumers will typically
  use DuckDB or Parquet for incremental updates,
  not CSV / JSON.
- **LocalFiles engine (T01)** — placeholder only.
  Deferred per the active task list. Users who
  need raw-file persistence can use the standard
  filesystem + Parquet.
- **DuckDB metadata table** does not have an
  `updated_at` column — only `stored_at`. The
  `DatasetUpdater` appends a fresh row per update
  rather than `UPDATE`-then-`INSERT`. A follow-up
  could add an `updated_at` column for cleaner
  metadata tracking.
- **Streaming ingestion** — reserved for a future
  version per `012_STORAGE_SPECIFICATION.md` §3.6.

---

## 12. Ready for Analytics Layer

The Storage layer is ready for the Analytics layer
(Phase 6) to consume:

- **DuckDB as the analytical backend** (per
  ADR-0029 / Q62). 47-column schema, exact-precision
  `DECIMAL(38, 18)` monetary columns, metadata
  table, partition loading, query validation.
- **Parquet for large-dataset export** (per
  ADR-0029 / Q64). Stable schema, decimal128
  exact-precision, Hive-style partitioning.
- **CSV / JSON for human-readable dumps** (per
  ADR-0029 / Q65 + Q66). Metadata sidecar.
- **Incremental updates** via `DatasetUpdater` —
  APPEND / MERGE / REPLACE across all four
  engines, with duplicate detection and
  deduplication helpers.
- **Schema compatibility** validated before every
  write (raises `SchemaIncompatibleError` on
  mismatch).
- **Composite-key contract** preserved end-to-end
  (per `006_DATA_MODEL.md` §3.12) — same 10-tuple
  across parser, transformer, storage, and
  updater.
- **CanonicalDataset contract** preserved — every
  storage engine accepts the same frozen dataclass
  produced by the ETL layer.

The Analytics layer implementation will:

1. Define `Query` and `Result` dataclasses that
   consume `duckdb.DuckDBPyConnection` (returned
   by `DuckDBWriter.load_partition(...)`).
2. Implement SQL-friendly helpers (`select`,
   `aggregate`, `group_by`, `top_n`) that build
   SQL strings validated by `DuckDBWriter.validate_query(...)`.
3. Reuse the `CanonicalDataset` produced by ETL
   for batch analytics (via `duckdb` `read_sql`
   or `read_parquet`).
4. Add analytical convenience types
   (`TradeBalance`, `BilateralFlow`,
   `ReporterMatrix`) on top of the persisted
   tables.

---

## 13. Sign-off

```
STORAGE COMPLETE             ✅  (4 engines + 1 placeholder; 227/227 tests)
CANONICAL DATASET PRESERVED  ✅  (every engine accepts CanonicalDataset; roundtrip verified)
DECIMAL PRESERVED            ✅  (string in CSV/JSON; decimal128 in Parquet; DECIMAL(38,18) in DuckDB)
PARTITION STRATEGY CORRECT   ✅  (Hive-style `(reporter, year, frequency)`; positional tokens; no silent overwrites)
DUCKDB VALIDATED             ✅  (47-column schema; metadata table; partition loading; query validation; SUM/SELECT)
READY FOR ANALYTICS          ✅  (DuckDB analytical backend live; Parquet large-dataset export live; incremental updates live)
```

---

# End of document