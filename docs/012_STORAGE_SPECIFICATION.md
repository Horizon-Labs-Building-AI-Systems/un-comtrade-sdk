```
Document ID
012

Title
Storage & Persistence Architecture Specification

Version
0.1.0

Status
DRAFT

Created
2026-06-26T20:33:20Z

Last Updated
2026-06-26T20:33:20Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
011_ETL_SPECIFICATION.md

Supersedes
None
```

---

# 1. Storage Layer Overview

## 1.1 Purpose

The Storage & Persistence Layer (the storage layer) is
the lower layer of the SDK that is responsible for
persisting the canonical dataset produced by the ETL
layer. The storage layer is the only layer that
performs filesystem I/O. The storage layer is the
boundary between the in-memory canonical model and
the persisted canonical model.

The storage layer is the contract that every
downstream consumer depends on. The analytics layer
and the application layer consume the persisted
dataset through the documented interface. The
consumer SHALL NOT depend on the in-memory
representation; the consumer SHALL depend on the
persisted representation.

## 1.2 Responsibilities

The storage layer is responsible for:

- Persisting the canonical dataset produced by the
  ETL layer.
- Versioning the persisted dataset.
- Organising the persisted dataset in a documented
  folder hierarchy.
- Naming the persisted dataset files in a documented
  convention.
- Serialising the canonical dataset in a documented
  format.
- Retrieving the persisted dataset through a
  documented interface.
- Verifying the integrity of the persisted dataset.
- Archiving the persisted dataset after the
  retention period expires.
- Providing a documented interface for the
  analytics layer and the application layer.

## 1.3 Position within architecture

The storage layer is the L8 layer declared in
`003_ARCHITECTURE.md` §4. The layer is owned by the
`un_comtrade.storage` module declared in
`003_ARCHITECTURE.md` §9.2. The layer is invoked by
the ETL layer (L7's consumer) to persist the
canonical dataset. The layer is invoked by the
metadata layer (L3) to persist the metadata cache.
The layer is invoked by the analytics layer and the
application layer to retrieve the persisted dataset.

## 1.4 Relationship to ETL

The storage layer is the persistence boundary for
the ETL layer. The ETL layer hands off the canonical
dataset to the storage layer through the documented
interface. The storage layer validates the dataset
before persisting, persists the dataset in the
documented format, and returns a persistence handle
to the ETL layer.

The storage layer does not modify the canonical
dataset. The canonical dataset is the source of
truth. The storage layer is a faithful reproducer
of the canonical dataset.

## 1.5 Relationship to Analytics

The storage layer is the source of the dataset that
the analytics layer consumes. The analytics layer
is out of scope of the SDK. The analytics layer
interacts with the storage layer through the
documented interface.

The storage layer does not perform analytics. The
storage layer is the substrate; the analytics layer
is the consumer.

## 1.6 Relationship to Applications

The storage layer is the source of the dataset that
the application layer consumes. The application
layer is out of scope of the SDK. The application
layer interacts with the storage layer through the
documented interface.

The storage layer does not perform application
logic. The storage layer is the substrate; the
application layer is the consumer.

---

# 2. Storage Philosophy

The storage layer is governed by the principles
below. Each principle is binding for every future
storage implementation.

## 2.1 Canonical data only

The storage layer persists only the canonical data
model declared in `006_DATA_MODEL.md`. The storage
layer does not persist the upstream wire format.
The canonical model is the source of truth; the
wire format is one possible projection of the
canonical model.

## 2.2 Immutable source datasets

A source dataset is the original extraction of a
trade data query. A source dataset is immutable
once persisted. A source dataset SHALL NOT be
modified. A re-extraction produces a new source
dataset, not a modification of the existing one.

## 2.3 Technology-independent architecture

The storage layer is technology-independent. The
storage layer exposes a documented abstract
interface; the concrete storage backend is a
documented implementation behind the interface.
The consumer SHALL NOT depend on the concrete
backend.

## 2.4 Separation of logical and physical storage

The storage layer separates the logical
organisation of the dataset from the physical
organisation of the dataset. The logical
organisation is declared in section 5 of this
document. The physical organisation is the
responsibility of the concrete backend.

## 2.5 Deterministic organization

The storage layer organises the dataset in a
deterministic fashion. Given a canonical dataset
and a configuration, the storage layer produces
the same persisted layout across runs. A consumer
that reads the dataset SHALL observe the same
layout regardless of when the dataset was
persisted.

## 2.6 Backward compatibility

The storage layer preserves backward compatibility
within a major SDK version. A change in the
persistence format that does not change the
canonical model is handled by the storage layer
without breaking the consumer. A change in the
canonical model is governed by the schema
evolution strategy declared in
`011_ETL_SPECIFICATION.md` §10.

## 2.7 Append-only versioning

The storage layer persists a new version of a
dataset on every change. The previous version is
retained until the retention period expires. A
rollback is supported by retrieving an older
version.

## 2.8 Idempotent persistence

The persistence of a canonical dataset is
idempotent within a version. Persisting the same
dataset twice produces the same persisted layout
without duplication. A re-persistence updates the
recorded timestamp without modifying the data.

## 2.9 Lazy materialisation

The storage layer materialises the dataset lazily.
A consumer that requests a subset of the dataset
receives only the subset. The full dataset is not
materialised unless the consumer explicitly requests
it.

---

# 3. Storage Targets

The storage layer supports the targets below. Each
target is documented with its purpose, its typical
use cases, its strengths, its limitations, its
recommended scenarios, and its future support
status.

## 3.1 Target T01 — Local Files

- **Purpose.** Persist the canonical dataset as
  files on the local filesystem.
- **Typical use cases.** Single-process workloads,
  development, small datasets.
- **Strengths.** Zero external dependencies, simple
  to debug, easy to inspect.
- **Limitations.** Not shared across processes,
  not scalable to large datasets, no concurrent
  access.
- **Recommended scenarios.** Development,
  single-process pipelines, small datasets (under
  10 GB).
- **Future support status.** Supported in the MVP.

## 3.2 Target T02 — JSON Files

- **Purpose.** Persist the canonical dataset as
  JSON files.
- **Typical use cases.** Schema-validated storage,
  metadata catalogues, small trade datasets.
- **Strengths.** Human-readable, schema-validated
  by JSON parsers, well-supported by every language.
- **Limitations.** Not efficient for large
  datasets, not columnar.
- **Recommended scenarios.** Metadata catalogues,
  small trade datasets, debugging.
- **Future support status.** Supported in the MVP.

## 3.3 Target T03 — CSV Files

- **Purpose.** Persist the canonical dataset as
  CSV files.
- **Typical use cases.** Interchange with tabular
  tools, hand-off to analysts.
- **Strengths.** Widely supported, easy to inspect,
  spreadsheet-compatible.
- **Limitations.** No schema, no nested types,
  precision loss for some numeric types.
- **Recommended scenarios.** Hand-off to analysts,
  ingestion into a third-party tool.
- **Future support status.** Supported in the MVP.

## 3.4 Target T04 — Parquet Files

- **Purpose.** Persist the canonical dataset as
  Parquet files.
- **Typical use cases.** Columnar analytics,
  large datasets, integration with data lakes.
- **Strengths.** Columnar storage, efficient
  compression, schema-validated, well-supported
  by every language.
- **Limitations.** Not human-readable, requires a
  Parquet reader.
- **Recommended scenarios.** Large trade datasets,
  columnar analytics, data lake ingestion.
- **Future support status.** Supported in the MVP.

## 3.5 Target T05 — DuckDB

- **Purpose.** Persist the canonical dataset in an
  embedded analytical database.
- **Typical use cases.** Local analytical queries,
  embedded pipelines, single-machine data
  warehouse.
- **Strengths.** Embedded, SQL-compatible, fast
  columnar execution, supports Parquet natively.
- **Limitations.** Single-machine, not
  distributed.
- **Recommended scenarios.** Embedded analytics,
  single-machine data warehouse, exploratory
  analysis.
- **Future support status.** Supported in a future
  version (out of MVP scope).

## 3.6 Target T06 — PostgreSQL

- **Purpose.** Persist the canonical dataset in a
  PostgreSQL database.
- **Typical use cases.** Production deployments,
  multi-process access, integration with a
  warehouse.
- **Strengths.** Production-grade, multi-process,
  SQL-compatible, transactional, well-supported.
- **Limitations.** Requires a server, requires
  schema management.
- **Recommended scenarios.** Production
  deployments, multi-process access, integration
  with a warehouse.
- **Future support status.** Supported in a future
  version (out of MVP scope).

## 3.7 Target T07 — Cloud Object Storage (Future)

- **Purpose.** Persist the canonical dataset in a
  cloud object store.
- **Typical use cases.** Cloud-native deployments,
  data lake ingestion, multi-region access.
- **Strengths.** Scalable, durable, multi-region.
- **Limitations.** Network latency, cost.
- **Recommended scenarios.** Cloud-native
  deployments, data lake ingestion.
- **Future support status.** Reserved for a future
  version.

## 3.8 Summary

| ID    | Target                       | MVP? | Future? | Default? |
| ----- | ---------------------------- | ---- | ------- | -------- |
| T01   | Local Files                  | Yes  | Yes     | No       |
| T02   | JSON Files                   | Yes  | Yes     | No       |
| T03   | CSV Files                    | Yes  | Yes     | No       |
| T04   | Parquet Files                | Yes  | Yes     | **Yes** (large datasets) |
| T05   | DuckDB                       | Yes  | Yes     | **Yes** (analytical) |
| T06   | PostgreSQL                   | No   | Yes     | No       |
| T07   | Cloud Object Storage         | No   | Yes     | No       |

**Default targets** (per Architecture Freeze Questions Q62, Q64):

- **Analytical storage:** DuckDB (T05) is the primary analytical backend.
- **Large-dataset export:** Parquet (T04) is the default export format for large datasets.
- **Compatibility / spreadsheet:** CSV (T03) remains supported.
- **Canonical persistence:** Local files (T01) and JSON files (T02) remain supported for low-volume use cases.

---

# 4. Persistence Lifecycle

The persistence lifecycle describes the path that a
canonical dataset follows from input to archival.

```
Canonical Records
    |
    v
Validation
    |
    v
Storage Selection
    |
    v
Persistence
    |
    v
Verification
    |
    v
Retrieval
    |
    v
Archival
```

## 4.1 Canonical Records

The input is the canonical dataset produced by the
ETL layer. The dataset carries the entities declared
in `006_DATA_MODEL.md` and the provenance declared
in `011_ETL_SPECIFICATION.md` §15.

## 4.2 Validation

The validation stage validates the dataset against
the persistence schema. The validation rules are
declared in section 12 of this document. A failed
validation is recorded as a dataset-level error
and the persistence is aborted.

## 4.3 Storage Selection

The storage selection stage selects the storage
target for the dataset. The selection is based on
the configuration and on the dataset metadata. The
default target is the local filesystem with the
JSON format.

## 4.4 Persistence

The persistence stage persists the dataset to the
selected target. The persistence is atomic: the
dataset is either fully persisted or not at all.
A partial persistence is detected by the
verification stage and triggers a rollback.

## 4.5 Verification

The verification stage verifies the persisted
dataset. The verification rules are declared in
section 12 of this document. A failed verification
triggers a re-persistence from the canonical
dataset.

## 4.6 Retrieval

The retrieval stage retrieves a persisted dataset
through the documented interface. The retrieval
is on-demand; the storage layer does not pre-
materialise the dataset.

## 4.7 Archival

The archival stage moves a dataset to the archive
after the retention period expires. The archive is
a documented location separate from the active
location.

---

# 5. Logical Data Organization

The storage layer organises the canonical dataset
into the logical categories below. The categories
are declared at the logical level; the physical
layout is the responsibility of the concrete
backend.

## 5.1 Metadata

The metadata category contains the reference
catalogues. The metadata is persisted by the
metadata layer. The metadata is immutable once
persisted.

## 5.2 Trade Data

The trade data category contains the canonical
trade records. The trade data is persisted by the
ETL layer. The trade data is versioned on every
extraction.

## 5.3 Reference Data

The reference data category contains the data
items, the trade data items, and the publication
notes. The reference data is persisted by the
metadata layer and the trade layer. The reference
data is versioned on every upstream update.

## 5.4 Export Data

The export data category contains the data that the
ETL layer has exported to a specific output format.
The export data is persisted by the ETL layer. The
export data is versioned on every export.

## 5.5 Temporary Data

The temporary data category contains the data that
the SDK creates during a single operation. The
temporary data is persisted for the duration of the
operation and is deleted when the operation
completes.

## 5.6 Cached Data

The cached data category contains the data that the
SDK caches for performance. The cached data is
persisted by the metadata layer and the trade
layer. The cached data is versioned on every
upstream update.

## 5.7 Quarantined Data

The quarantined data category contains the data that
the ETL layer has quarantined due to a validation
failure. The quarantined data is persisted by the
ETL layer. The quarantined data is retained until
the consumer explicitly deletes it.

## 5.8 Relationships

The relationships between the categories are
declared in the data model. The storage layer
preserves the relationships through the foreign-
key-style references between entities.

## 5.9 Versioned Data

The versioned data category contains the data that
the storage layer persists with a version
identifier. The versioned data is retained for
the retention period. The versioned data is
archived after the retention period expires.

---

# 6. Folder Organization

The folder organization is the logical layout of
the persisted dataset. The folder organization is
declarative; the physical layout is the
responsibility of the concrete backend.

## 6.1 Top-Level Folders

The top-level folders are:

- `metadata/` — the metadata catalogues.
- `trade/` — the trade data.
- `reference/` — the reference data.
- `export/` — the export data.
- `cache/` — the cached data.
- `quarantine/` — the quarantined data.
- `archive/` — the archived data.

## 6.2 Folder Ownership

The ownership of each folder is:

- `metadata/` — owned by the metadata layer.
- `trade/` — owned by the ETL layer.
- `reference/` — owned by the metadata layer and
  the trade layer.
- `export/` — owned by the ETL layer.
- `cache/` — owned by the metadata layer and the
  trade layer.
- `quarantine/` — owned by the ETL layer.
- `archive/` — owned by the storage layer.

## 6.3 Retention Expectations

The retention expectations are:

- `metadata/` — 30 days for static catalogues, 7 days
  for slow-changing catalogues.
- `trade/` — the retention period is configurable;
  the default is 30 days.
- `reference/` — the retention period is
  configurable; the default is 7 days.
- `export/` — the retention period is configurable;
  the default is 30 days.
- `cache/` — the cache lifetime per resource
  family.
- `quarantine/` — the retention period is
  configurable; the default is 90 days.
- `archive/` — the retention period is
  configurable; the default is 365 days.

## 6.4 Temporary vs Persistent

The `cache/` and `quarantine/` folders may contain
temporary data. The other folders contain persistent
data. The distinction is recorded in the folder
ownership and the retention expectations.

## 6.5 Naming Consistency

The folder names are lowercase, single-word,
documented in this document. The folder names SHALL
NOT be modified without updating this document.

---

# 7. File Naming Standards

The file naming standards declare the convention for
naming the persisted files. The standards are
declarative; the implementation is the
responsibility of the concrete backend.

## 7.1 Dataset Naming

A dataset name is a human-readable identifier of
the dataset. The dataset name is lowercase, hyphen-
separated, and uses the canonical entity name
from the data model.

Examples:

- `reporters.json` — the reporters catalogue.
- `partners.json` — the partners catalogue.
- `hs.json` — the combined HS catalogue.
- `india-exports-2022-annual.json` — India's 2022
  annual exports.

## 7.2 Metadata Naming

A metadata file name is the lowercased
`collection_type` of the resource. The extension
is `.json` for JSON files, `.csv` for CSV files,
`.parquet` for Parquet files.

## 7.3 Trade Dataset Naming

A trade dataset name is:

```
<reporter>-<flow>-<period>-<frequency>-<classification>.<extension>
```

Where:

- `<reporter>` is the reporter code or the
  human-readable name.
- `<flow>` is the flow code (`X`, `M`, `RX`, `RM`).
- `<period>` is the period (`2022` for annual,
  `202201` for monthly).
- `<frequency>` is the frequency code (`A`, `M`).
- `<classification>` is the classification code
  (`HS`, `H6`, `S4`, etc.).
- `<extension>` is the file extension.

Examples:

- `india-X-2022-A-HS.json` — India's 2022 annual
  exports in HS classification as JSON.
- `world-M-202201-M-H6.parquet` — World's January
  2022 monthly imports in HS 2022 as Parquet.

## 7.4 Version Suffixes

A version suffix is appended to the file name when
the dataset is versioned. The version suffix is
`-v<major>-<minor>-<patch>`. The suffix is optional;
the absence of a suffix indicates the latest version.

Examples:

- `india-X-2022-A-HS-v1-0-0.json` — India's 2022
  annual exports, version 1.0.0.

## 7.5 Timestamp Conventions

A timestamp is appended to the file name when the
file is a snapshot. The timestamp is the
extraction timestamp in ISO-8601 format with `Z`
suffix.

Examples:

- `india-X-2022-A-HS-20240115T120000Z.json` —
  India's 2022 annual exports, extracted on
  2024-01-15 at 12:00:00 UTC.

## 7.6 Partition Naming

A partition is a sub-division of a dataset. The
partition name is appended to the file name with a
`-p<partition>` suffix. The partition is optional;
the absence of a suffix indicates the unpartitioned
dataset.

Examples:

- `india-X-2022-A-HS-p1.json` — India's 2022 annual
  exports, partition 1.
- `india-X-2022-A-HS-p1.json` for partition 1 and
  `india-X-2022-A-HS-p2.json` for partition 2.

## 7.7 File Extensions

The file extension is the serialisation format. The
documented extensions are:

- `.json` — JSON.
- `.csv` — CSV.
- `.parquet` — Parquet.
- `.duckdb` — DuckDB.
- `.sql` — SQL dump (future).

## 7.8 Collision Handling

A file name collision is detected when the storage
layer attempts to persist a file with the same name
as an existing file. The collision is resolved by
appending a version suffix or a timestamp suffix.
The collision is recorded in the storage log.

---

# 8. Dataset Versioning

The dataset versioning strategy declares how the
storage layer versions a dataset.

## 8.1 Dataset Versions

A dataset version is a unique identifier of a
specific state of the dataset. A dataset version is
recorded on every persistence. The version is
composed of:

- The dataset identifier.
- The version identifier.
- The timestamp of the persistence.
- The provenance chain.

## 8.2 Metadata Versions

A metadata version is the version of the
metadata catalogue. The metadata version is
recorded by the metadata layer. A metadata version
change triggers a refresh.

## 8.3 Schema Versions

A schema version is the version of the canonical
data model. The schema version is recorded in
the `provenance` field of every record. A schema
version change triggers a migration.

## 8.4 Compatibility

A dataset is backward compatible within a major
version of the SDK. A change in the dataset
version that does not change the canonical data
model is backward compatible. A change that does
change the canonical data model is governed by
the schema evolution strategy.

## 8.5 Replacement Strategy

A new dataset version replaces an old dataset
version when the new version is persisted. The old
version is retained in the archive for the
retention period. The new version is the active
version.

## 8.6 Retention Expectations

A dataset version is retained for the retention
period. The default retention period is 30 days
for trade data, 7 days for reference data, 365
days for archived data. The retention period is
configurable.

## 8.7 Rollback Concepts

A rollback is the act of restoring a previous
version of a dataset as the active version. A
rollback is supported by retrieving the previous
version from the archive and persisting it as the
active version.

A rollback is recorded in the storage log. A
rollback SHALL NOT delete the rolled-forward
version; the rolled-forward version is retained in
the archive.

---

# 9. Indexing Strategy

The indexing strategy declares the logical indexes
that the storage layer exposes. The indexes are
declarative; the physical implementation is the
responsibility of the concrete backend.

## 9.1 Reporter Index

The reporter index is an index on the `reporter_code`
field. The reporter index supports the lookup of
records by reporter.

## 9.2 Partner Index

The partner index is an index on the `partner_code`
field. The partner index supports the lookup of
records by partner.

## 9.3 HS Code Index

The HS code index is an index on the `commodity_code`
field. The HS code index supports the lookup of
records by commodity.

## 9.4 Trade Flow Index

The trade flow index is an index on the `flow_code`
field. The trade flow index supports the lookup of
records by flow.

## 9.5 Period Index

The period index is an index on the `period` field.
The period index supports the lookup of records by
period.

## 9.6 Classification Index

The classification index is an index on the
`classification_code` and `edition` fields. The
classification index supports the lookup of records
by classification.

## 9.7 Composite Identifiers

The composite identifier index is an index on the
composite primary key declared in
`006_DATA_MODEL.md` §3. The composite identifier
index supports the deduplication and the lookup of
records by composite key.

## 9.8 Lookup Behaviour

The lookup behaviour is:

- A lookup by a single field returns every record
  that matches the field.
- A lookup by a composite key returns at most one
  record.
- A lookup by a range (period) returns every record
  in the range.
- A lookup by a partial match (e.g. HS chapter)
  returns every record whose `commodity_code` starts
  with the partial match.

---

# 10. Serialization Formats

The serialisation formats section declares the
expected behaviour of the storage layer when
serialising a canonical dataset. The rules are
declarative; the implementation is the
responsibility of the concrete backend.

## 10.1 JSON

- **Encoding.** UTF-8.
- **Field names.** snake_case.
- **Top-level shape.** A JSON object with the
  documented top-level keys.
- **Determinism.** Deterministic; the output for a
  given input is the same across runs.
- **Nulls.** JSON `null`.
- **Dates.** ISO-8601 strings.
- **Date-times.** ISO-8601 strings with `Z` suffix.
- **Numbers.** Full precision.
- **Arrays.** JSON arrays.
- **Compatibility.** Backward compatible within a
  major SDK version.

## 10.2 CSV

- **Encoding.** UTF-8.
- **Field names.** snake_case.
- **Header.** The first row of the file lists the
  field names in the documented order.
- **Delimiters.** Comma; the field is quoted when
  the field contains a comma, a quote, or a
  newline.
- **Nulls.** Empty string.
- **Dates.** ISO-8601 strings.
- **Numbers.** Full precision.
- **Arrays.** Comma-separated values inside the
  cell.
- **Compatibility.** Backward compatible within a
  major SDK version.

## 10.3 Parquet

- **Encoding.** UTF-8.
- **Field names.** snake_case.
- **Schema.** The Parquet schema reflects the
  canonical data model.
- **Decimals.** Sufficient precision to represent
  the value without loss.
- **Dates.** Parquet DATE or ISO-8601 strings.
- **Date-times.** Parquet TIMESTAMP or ISO-8601
  strings.
- **Compression.** Snappy (default), Gzip, or
  uncompressed.
- **Compatibility.** Backward compatible within a
  major SDK version.

## 10.4 DuckDB

- **Schema.** The DuckDB schema reflects the
  canonical data model.
- **Storage.** Single file or directory.
- **Compression.** Native.
- **Compatibility.** Backward compatible within a
  major SDK version.

## 10.5 PostgreSQL

- **Schema.** The PostgreSQL schema reflects the
  canonical data model.
- **Engine.** PostgreSQL 12 or later.
- **Encoding.** UTF-8.
- **Compatibility.** Backward compatible within a
  major SDK version.

## 10.6 Canonical Object Serialization

The canonical object serialisation is the in-memory
representation of a canonical entity. The
serialisation is the source of truth for the
storage formats. A change in the canonical object
serialisation is a change in the canonical data
model.

## 10.7 Encoding

The default encoding is UTF-8. The encoding is
configurable. The encoding SHALL be consistent
within a dataset.

## 10.8 Compression

The default compression is Snappy for Parquet. The
default compression is none for CSV and JSON. The
compression is configurable. The compression SHALL
be documented in the dataset metadata.

---

# 11. Retrieval Strategy

The retrieval strategy declares how the storage
layer returns a persisted dataset to the consumer.

## 11.1 Single Dataset Retrieval

A single dataset retrieval returns one dataset by
its identifier. The retrieval is on-demand; the
storage layer does not pre-materialise the dataset.
The retrieval returns the dataset in the
documented format.

## 11.2 Metadata Retrieval

A metadata retrieval returns a metadata catalogue
by its `collection_type`. The retrieval is on-
demand; the storage layer does not pre-materialise
the catalogue. The retrieval returns the catalogue
in the documented format.

## 11.3 Trade Retrieval

A trade retrieval returns a trade dataset by its
identifier. The retrieval is on-demand; the storage
layer does not pre-materialise the dataset. The
retrieval returns the dataset in the documented
format.

## 11.4 Bulk Retrieval

A bulk retrieval returns every dataset that matches
a filter. The filter is a documented predicate.
The retrieval is on-demand; the storage layer does
not pre-materialise the datasets.

## 11.5 Filtered Retrieval

A filtered retrieval returns the records of a
dataset that match a filter. The filter is a
documented predicate over the canonical data
model. The retrieval is on-demand.

## 11.6 Version-Aware Retrieval

A version-aware retrieval returns the active
version of a dataset by default. A consumer can
request a specific version by providing the version
identifier.

## 11.7 Expected Behaviour

A retrieval returns a dataset in the documented
format. A retrieval is idempotent: the same query
returns the same result. A retrieval SHALL NOT
modify the persisted dataset.

---

# 12. Data Integrity

The data integrity section declares the integrity
expectations of the storage layer.

## 12.1 Atomic Persistence

A persistence is atomic. The dataset is either
fully persisted or not at all. A partial
persistence is detected by the verification
stage and triggers a rollback.

## 12.2 Consistency

A persisted dataset SHALL be consistent with the
canonical dataset. A consumer that retrieves a
persisted dataset SHALL observe the canonical
dataset. A drift between the canonical and the
persisted dataset is a defect.

## 12.3 Duplicate Prevention

The storage layer SHALL prevent the persistence of
duplicate records within a dataset version. A
duplicate is detected by the composite primary
key. A duplicate is recorded as a warning and is
resolved by the deduplication policy of the ETL
layer.

## 12.4 Referential Integrity

A persisted dataset SHALL preserve the referential
integrity of the canonical data model. A reference
that does not resolve is recorded as a warning
and is preserved as a string.

## 12.5 Schema Compatibility

A persisted dataset SHALL be schema-compatible
with the current canonical data model. A schema
incompatibility triggers a migration. The
migration strategy is declared in
`011_ETL_SPECIFICATION.md` §10.

## 12.6 Version Compatibility

A persisted dataset SHALL be version-compatible
with the current SDK version. A version
incompatibility is recorded as a warning and is
preserved for the retention period.

## 12.7 Validation Before Persistence

The storage layer validates the dataset before
persistence. A failed validation is a fatal error
and the persistence is aborted. The validation
rules are declared in section 4 of this document.

## 12.8 Integrity Verification

The storage layer verifies the integrity of the
persisted dataset. The verification is performed
on every retrieval. A failed verification triggers
a re-persistence from the canonical dataset.

---

# 13. Storage Performance

The storage performance section declares the
expected performance characteristics of the storage
layer.

## 13.1 Large Datasets

A large dataset is a dataset that exceeds 10 GB.
The storage layer processes a large dataset in
chunks. The chunk size is configurable. The
default chunk size is 1,000 records.

## 13.2 Read Performance

The read performance is bounded by the
serialisation format and the storage backend.
Parquet reads are columnar and are faster than
JSON reads for selective queries. The storage
layer does not impose a maximum read time.

## 13.3 Write Performance

The write performance is bounded by the
serialisation format and the storage backend.
Parquet writes are typically faster than JSON
writes for large datasets. The storage layer does
not impose a maximum write time.

## 13.4 Bulk Imports

A bulk import is the persistence of a large
dataset in a single call. The storage layer
processes a bulk import as a single transaction.
The bulk import is atomic.

## 13.5 Bulk Exports

A bulk export is the retrieval of a large dataset
in a single call. The storage layer processes a
bulk export as a single transaction. The bulk
export is atomic.

## 13.6 Partitioning Concepts

A partition is a sub-division of a dataset. The
storage layer MAY persist a dataset as a set of
partitions. The partition key is documented. The
default partition key is `period`.

## 13.7 Scalability Expectations

The storage layer scales linearly with the size of
the dataset. The storage layer does not impose a
process-level limit. The storage layer is expected
to scale to billions of records through the
documented targets.

---

# 14. Integration Points

The integration points section declares how the
storage layer interacts with the other layers of
the SDK.

## 14.1 ETL Layer

The storage layer is the persistence boundary for
the ETL layer. The ETL layer hands off the canonical
dataset to the storage layer through the documented
interface. The storage layer validates, persists,
and verifies the dataset.

## 14.2 Metadata Layer

The storage layer is the persistence boundary for
the metadata layer. The metadata layer hands off
the metadata catalogue to the storage layer through
the documented interface. The storage layer
persists the catalogue in the documented format.

## 14.3 Trade Layer

The storage layer is the persistence boundary for
the trade layer. The trade layer hands off the
trade response to the storage layer through the
documented interface. The storage layer persists
the response as a trade dataset.

## 14.4 Analytics Layer

The storage layer is the source of the dataset for
the analytics layer. The analytics layer is out of
scope of the SDK. The analytics layer interacts
with the storage layer through the documented
interface.

## 14.5 Future Applications

The storage layer is the source of the dataset for
the application layer. The application layer is
out of scope of the SDK. The application layer
interacts with the storage layer through the
documented interface.

## 14.6 Boundaries

The storage layer is the boundary between the in-
memory canonical model and the persisted canonical
model. The storage layer is also the boundary
between the SDK's internal model and the
consumer's external model. The storage layer is
also the boundary between the active dataset and
the archived dataset.

---

# 15. Future Extensibility

The future extensibility section declares how new
storage targets can be introduced without affecting
the rest of the architecture.

## 15.1 Cloud Object Storage

A cloud object storage target is added in a future
version. The target SHALL be documented in section
3 of this document. The target SHALL conform to
the abstract storage interface.

## 15.2 Data Lake

A data lake target is added in a future version.
The target SHALL be documented in section 3 of
this document. The target SHALL conform to the
abstract storage interface.

## 15.3 Alternative Databases

An alternative database target (e.g. Snowflake,
BigQuery, Redshift) is added in a future version.
The target SHALL be documented in section 3 of
this document. The target SHALL conform to the
abstract storage interface.

## 15.4 Future File Formats

A future file format (e.g. Avro, ORC) is added in a
future version. The format SHALL be documented in
section 10 of this document. The format SHALL
conform to the abstract serialisation interface.

## 15.5 Deprecation

A deprecated storage target or file format is
preserved in the SDK until the deprecation period
expires. The deprecation is recorded in the
changelog and the decisions log.

## 15.6 Abstract Storage Interface

A new storage target is added by implementing the
abstract storage interface. The abstract storage
interface declares:

- `persist(dataset, target, version)` — persist a
  dataset to a target.
- `retrieve(dataset_id, version)` — retrieve a
  dataset from a target.
- `list_versions(dataset_id)` — list the versions
  of a dataset.
- `delete(dataset_id, version)` — delete a specific
  version of a dataset.
- `archive(dataset_id, version)` — archive a
  specific version of a dataset.

---

# 16. Assumptions

The assumptions below are recorded for
traceability. An assumption that turns out to be
false is recorded in `DECISIONS.md` as a
correction and is propagated to the relevant
specification documents.

## 16.1 Verified Assumptions

- The canonical data model declares 25 entities.
  Verified.
- The ETL layer produces a canonical dataset with
  a `provenance` field. Verified by the ETL
  specification.
- The metadata layer produces a `MetadataCollection`
  for every reference table. Verified by the
  metadata layer specification.
- The trade layer produces a `Response` for every
  trade query. Verified by the trade layer
  specification.

## 16.2 Inferred Assumptions

- The default retention period is 30 days for trade
  data, 7 days for reference data, and 365 days
  for archived data. The defaults are inferred
  from common practice; the consumer can override
  the defaults.
- The default partition key is `period`. The
  default is inferred from common practice; the
  consumer can override the default.
- The default compression is Snappy for Parquet.
  The default is inferred from common practice; the
  consumer can override the default.
- The default encoding is UTF-8. The default is
  inferred from common practice; the consumer can
  override the default.
- The default chunk size is 1,000 records. The
  default is inferred from common practice; the
  consumer can override the default.

## 16.3 Local Design Decisions

- The MVP supports the local files, JSON, CSV,
  Parquet, and DuckDB targets. DuckDB is the
  primary analytical backend. PostgreSQL and
  cloud object storage targets are reserved for
  future versions.
- Datasets are partitioned logically by reporter,
  year, and frequency to support scalability and
  future analytics (per Architecture Freeze
  Question Q67).
- Every storage operation validates schema
  compatibility before writing (per Architecture
  Freeze Question Q69).
- The storage adapters expose a common interface
  to enable future storage backends without
  changing higher layers (per Architecture Freeze
  Question Q68).
- The SDK stores only canonical data; raw API
  responses exist transiently only during
  processing (per Architecture Freeze Question
  Q61).
- The folder organization is the logical layout;
  the physical layout is the responsibility of the
  concrete backend.
- The versioning strategy is append-only with
  retention. A rollback is supported.
- The integrity verification is performed on every
  retrieval. The verification is fast.
- The bulk import and bulk export are atomic. The
  storage layer does not provide a partial
  transaction.
- The lazy materialisation is the default. A
  consumer that wants eager materialisation can
  override the default through a configuration
  parameter.

---

# 17. Open Questions

The questions below are recorded for future
resolution. Each question is described with the
impact and the suggested verification.

- **OQ-SL-001 (High).** What is the exact retention
  period for each data category? **Impact.** The
  retention period affects the storage cost and
  the consumer's data availability.
  **Suggested verification.** Confirm with the
  consumer requirements.

- **OQ-SL-002 (High).** What is the exact partition
  strategy for trade data? **Impact.** The
  partition strategy affects the query
  performance. **Suggested verification.** Run a
  performance experiment with different
  partition keys.

- **OQ-SL-003 (Medium).** Should the storage layer
  support a custom serialiser through a documented
  extension point? **Impact.** A custom serialiser
  would enable consumer-specific output formats.
  **Suggested verification.** Confirm with the
  consumer requirements.

- **OQ-SL-004 (Medium).** Should the storage layer
  support a custom target through a documented
  extension point? **Impact.** A custom target
  would enable consumer-specific backends.
  **Suggested verification.** Confirm with the
  consumer requirements.

- **OQ-SL-005 (Medium).** Should the storage layer
  support a versioning strategy that retains every
  intermediate version, or only the latest version
  per period? **Impact.** The versioning strategy
  affects the storage cost and the rollback
  capability. **Suggested verification.** Confirm
  with the consumer requirements.

- **OQ-SL-006 (Medium).** Should the storage layer
  support a remote storage target (e.g. S3) in
  the MVP, or defer it to a future version?
  **Impact.** A remote target would enable
  cloud-native deployments. **Suggested
  verification.** Confirm with the consumer
  requirements.

- **OQ-SL-007 (Medium).** Should the storage layer
  support a column-store target (e.g. DuckDB) in
  the MVP, or defer it to a future version?
  **Impact.** A column-store target would enable
  embedded analytics. **Suggested verification.**
  Confirm with the consumer requirements.

- **OQ-SL-008 (Low).** Should the storage layer
  support a custom metadata field on every
  persisted record, so that the consumer can
  attach application-specific tags? **Impact.**
  A custom metadata field would enable richer
  provenance. **Suggested verification.** Confirm
  with the consumer requirements.

- **OQ-SL-009 (Low).** Should the storage layer
  support a `compact()` operation that merges
  multiple versions of a dataset into a single
  version? **Impact.** A compact operation would
  reduce the storage cost over time. **Suggested
  verification.** Confirm with the consumer
  requirements.

- **OQ-SL-010 (Low).** Should the storage layer
  support a `vacuum()` operation that deletes
  archived datasets after the retention period?
  **Impact.** A vacuum operation would
  automatically clean up the storage. **Suggested
  verification.** Confirm with the consumer
  requirements.

---

# End of document
