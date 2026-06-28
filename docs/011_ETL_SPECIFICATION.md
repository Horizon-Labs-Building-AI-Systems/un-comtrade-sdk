```
Document ID
011

Title
Data Processing & ETL Pipeline Specification

Version
0.1.0

Status
DRAFT

Created
2026-06-26T20:29:56Z

Last Updated
2026-06-26T20:29:56Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
010_INFRASTRUCTURE_SPEC.md

Supersedes
None
```

---

# 1. ETL Overview

## 1.1 Purpose

The Data Processing & ETL Pipeline (the ETL layer) is
the highest-level orchestration layer of the SDK. The
ETL layer consumes the trade layer, the metadata
layer, and the infrastructure layer, and produces a
validated, normalised, deduplicated, quality-checked
canonical dataset that is suitable for storage,
analytics, and downstream applications.

The ETL layer is the contract that the consumer's
data pipeline depends on. The consumer SHALL NOT
interact with the upstream wire format directly. The
consumer SHALL interact with the canonical model
through the ETL layer.

## 1.2 Position within architecture

The ETL layer is the highest layer of the SDK. The
layer is owned by the `un_comtrade.etl` module (a
new module under the `un_comtrade` package; the
module name is reserved by this document). The layer
is invoked by the SDK consumer; the layer depends
on the trade layer, the metadata layer, the
infrastructure layer, the storage layer, and the
export layer.

## 1.3 Relationship to Trade Layer

The ETL layer consumes the trade layer. The ETL
layer does not issue HTTP calls; the trade layer
issues the calls through the transport layer. The
ETL layer treats the trade layer as the canonical
source of trade data.

The ETL layer relies on the trade layer for:

- Query composition.
- Code resolution.
- Endpoint selection.
- Response normalisation.
- Pagination.
- Retry.
- Error handling.

The ETL layer does not duplicate any of the above
responsibilities.

## 1.4 Relationship to Canonical Data Model

The ETL layer is the boundary between the upstream
wire format and the canonical data model. The
canonical data model is declared in
`006_DATA_MODEL.md`. The ETL layer produces entities
of the canonical data model; the consumer receives
the entities and SHALL NOT see the upstream wire
format.

## 1.5 Relationship to Storage Layer

The ETL layer is the producer of the data that the
storage layer persists. The ETL layer hands off the
canonical entities to the storage layer through the
documented interface. The storage layer is
documented in `011_STORAGE_SPECIFICATION.md` (the
next task).

The ETL layer does not perform filesystem I/O. The
storage layer is the only layer that performs
filesystem I/O.

## 1.6 Relationship to Infrastructure Layer

The ETL layer consumes the infrastructure services
declared in `010_INFRASTRUCTURE_SPEC.md`. The
infrastructure services are:

- Configuration (I01).
- Retry (I02).
- Timeout (I03).
- Logging (I04).
- Cache (I05).
- Progress Reporting (I06).
- Resume Support (I07).
- Error Handling (I08).
- Request Tracking (I09).
- Diagnostics (I10).
- Security (I11).

The ETL layer does not implement any of the
infrastructure services. The ETL layer invokes the
services through the documented interfaces.

## 1.7 Relationship to Analytics Layer

The ETL layer produces a canonical dataset that the
analytics layer consumes. The analytics layer is
out of scope of the SDK. The ETL layer treats the
analytics layer as a downstream consumer.

The ETL layer does not compute analytics. The ETL
layer produces the data; the analytics layer
consumes the data.

---

# 2. ETL Pipeline Overview

The ETL pipeline is the end-to-end processing chain
that converts an upstream response into a canonical
dataset. The pipeline is composed of 9 stages.

```
API Response
    |
    v
Extraction
    |
    v
Validation
    |
    v
Transformation
    |
    v
Normalization
    |
    v
Deduplication
    |
    v
Quality Check
    |
    v
Export
    |
    v
Storage
```

## 2.1 API Response

The API response is the raw JSON payload returned
by the trade layer. The payload has the documented
top-level keys (`elapsedTime`, `count`, `data`,
`error`) and the documented record shape (47
fields).

## 2.2 Extraction

The extraction stage receives the API response and
produces a stream of raw records. The extraction
stage does not validate, transform, or normalise
the records. The extraction stage is the entry
point of the ETL pipeline.

## 2.3 Validation

The validation stage validates each raw record
against the canonical data model. The validation
rules are declared in section 4 of this document.
A failed validation is recorded as a row-level
error; the record is either dropped or marked as
quarantined, depending on the rule.

## 2.4 Transformation

The transformation stage converts the raw record
into a transformed record. The transformation
rules are declared in section 5 of this document.
The transformation includes field mapping, datatype
conversion, identifier conversion, and unit
conversion.

## 2.5 Normalization

The normalisation stage converts the transformed
record into a canonical entity. The normalisation
rules are declared in section 6 of this document
and in `006_DATA_MODEL.md` §13. The normalisation
includes the canonical field mapping, the canonical
naming, and the resolution of metadata codes to
descriptions.

## 2.6 Deduplication

The deduplication stage removes duplicate records
based on the composite primary key declared in
`006_DATA_MODEL.md` §3. The deduplication rules
are declared in section 7 of this document.

## 2.7 Quality Check

The quality check stage verifies the quality of the
canonical dataset against the documented quality
rules. The quality rules are declared in section 8
of this document. A failed quality check is recorded
as a dataset-level warning; the dataset is still
returned to the consumer.

## 2.8 Export

The export stage packages the canonical dataset
into the requested output format. The export rules
are declared in section 9 of this document. The
default output format is the canonical entities; the
consumer can request JSON, CSV, or Parquet.

## 2.9 Storage

The storage stage hands off the canonical dataset
to the storage layer. The storage rules are
declared in `011_STORAGE_SPECIFICATION.md`. The
ETL layer does not perform the storage itself; the
ETL layer invokes the storage layer through the
documented interface.

---

# 3. Extraction Strategy

The extraction strategy declares how the ETL layer
receives data from the trade layer.

## 3.1 Input sources

The ETL layer receives data from:

- The trade layer's single request (T01–T11,
  F01–F02, P01–P04, C01–C03).
- The trade layer's batch processing.
- The trade layer's download workflows (country
  download, world download, HS code download,
  multi-year download, multi-partner download).
- The trade layer's async delivery (A01–A03).
- The trade layer's bulk download (A04–A05).

## 3.2 Supported response types

The ETL layer supports every response type declared
in the trade layer. Each response type is mapped to
a canonical entity type by the normalisation stage.

## 3.3 Input validation

The ETL layer validates the input before the
extraction stage. The input validation checks:

- The response envelope has the documented top-level
  keys.
- The `data` array is a JSON array.
- The `count` is a non-negative integer.
- The `error` is an empty string on success.

A failed input validation raises a `TradeError`.

## 3.4 Partial responses

A partial response is a response where the number
of records is less than the per-call cap but is not
the last page. The ETL layer treats a partial
response as a fatal error and raises a `TradeError`.

## 3.5 Incomplete datasets

An incomplete dataset is a dataset where the
extraction is interrupted by a network failure, a
process crash, or a consumer cancellation. The
ETL layer records the state of the extraction in
the resume checkpoint. The consumer can resume
the extraction from the last successful combination.

## 3.6 Streaming considerations

A streaming extraction is reserved for a future
version. The MVP supports a single batch extraction;
the ETL layer receives the entire response before
the extraction stage begins.

## 3.7 Extraction ownership

The extraction stage is owned by the ETL layer.
The stage is implemented in the `un_comtrade.etl`
module.

---

# 4. Validation Strategy

The validation strategy declares the rules that the
ETL layer applies to a raw record before the record
is transformed.

## 4.1 Schema validation

The validation stage validates that every field
of the raw record is present in the upstream
schema. A missing field is a validation error
when the field is declared in the canonical data
model as required.

## 4.2 Required fields

The validation stage validates that every required
field of the canonical entity is present in the
raw record. The required fields are declared in
`006_DATA_MODEL.md` §11.1. A missing required field
is a fatal validation error.

## 4.3 Datatype validation

The validation stage validates that the value of
every field of the raw record has the expected
datatype. The expected datatypes are declared in
`006_DATA_MODEL.md` §4. A field with an unexpected
datatype is a fatal validation error.

## 4.4 Range validation

The validation stage validates that the value of
every numeric field is within the expected range.
The expected ranges are declared in
`006_DATA_MODEL.md` §11.3. A field with an out-of-
range value is a fatal validation error.

## 4.5 Enum validation

The validation stage validates that the value of
every enumerated field is one of the allowed
values. The allowed values are declared in
`006_DATA_MODEL.md` §8. A field with an unknown
value is a fatal validation error.

## 4.6 Relationship validation

The validation stage validates that every reference
in the raw record resolves to a known entity. The
validation invokes the metadata layer for every
code. A code that does not resolve is a fatal
validation error.

## 4.7 Cross-field validation

The validation stage validates the cross-field
dependencies of the canonical entity. The cross-
field dependencies are declared in
`006_DATA_MODEL.md` §11.5. A cross-field
violation is a fatal validation error.

## 4.8 Version validation

The validation stage validates that the version of
the upstream schema is consistent with the version
expected by the ETL layer. A version mismatch is
a fatal validation error.

## 4.9 Expected behaviour for invalid records

A fatal validation error is recorded in the
`Response` envelope as a warning. The record is
either dropped or marked as quarantined, depending
on the rule. The default behaviour is to drop the
record and record a warning. The consumer can
configure the ETL layer to quarantine the record
instead.

## 4.10 Validation ownership

The validation stage is owned by the ETL layer.
The stage is implemented in the `un_comtrade.etl`
module. The validation rules are declarative; the
implementation is the responsibility of the
validation standard (`012_TESTING_STANDARD.md`).

---

# 5. Transformation Strategy

The transformation strategy declares the rules that
the ETL layer applies to convert a raw record into a
transformed record.

## 5.1 Field mapping

The transformation stage maps every upstream field
to the corresponding canonical field. The mapping
is declared in `006_DATA_MODEL.md` §13.1. The
mapping includes the snake_case renaming of every
camelCase field name.

The field mapping is the canonical binding between
the upstream wire format and the canonical data
model. The mapping SHALL NOT change the meaning
of any field.

## 5.2 Datatype conversion

The transformation stage converts every upstream
datatype to the canonical datatype. The conversion
rules are declared in `006_DATA_MODEL.md` §13.2.
The conversion includes:

- String trimming.
- Integer parsing.
- Float parsing.
- Boolean parsing.
- Date parsing (ISO-8601).
- Date-time parsing (ISO-8601 with `Z` suffix).

A failed conversion is a validation error.

## 5.3 Identifier conversion

The transformation stage converts every identifier
to the canonical form. The conversion rules are
declared in `006_DATA_MODEL.md` §13.3. The
conversion includes:

- Country code as integer.
- ISO codes as uppercase strings.
- Classification code as uppercase string.
- Edition code as uppercase string.
- Period as `YYYY` or `YYYYMM`.

## 5.4 Unit conversion

The transformation stage converts every unit to the
canonical unit. The conversion rules are declared
in `006_DATA_MODEL.md` §13.3. The conversion
includes:

- Monetary values to US dollars.
- Weights to kilograms.

The upstream does not produce values in other
currencies or other weight units, so the conversion
is the identity.

## 5.5 Timestamp normalization

The transformation stage converts every timestamp
to UTC. The conversion rules are declared in
`006_DATA_MODEL.md` §13.2. The conversion
includes:

- Periods as `YYYY` or `YYYYMM`.
- Date-time fields as ISO-8601 with `Z` suffix.

## 5.6 Code-to-name resolution

The transformation stage resolves every code to a
human-readable name through the metadata layer. The
resolution is a documented interface between the
ETL layer and the metadata layer.

The resolution is performed for the following
fields:

- `reporter_code` → `reporter_name`.
- `partner_code` → `partner_name`.
- `partner2_code` → `partner2_name`.
- `flow_code` → `flow_name`.
- `commodity_code` → `commodity_name`.
- `mot_code` → `mot_name`.
- `customs_code` → `customs_name`.
- `classification_code` → `classification_search_code`.
- `qty_unit_code` → `qty_unit_abbr`.

A code that does not resolve is preserved as a
string. The name is set to `null` and a warning
is recorded.

## 5.7 Derived fields

The transformation stage computes the derived
fields declared in `006_DATA_MODEL.md` §13.4. The
derived fields are:

- `commodity_level` — derived from the length of
  `commodity_code`.
- `commodity_is_leaf` — derived from the upstream
  `isLeaf` field.
- `commodity_is_aggregate` — derived from the
  upstream `isAggregate` field.
- `is_reporter` — derived from the absence of
  `entry_expired_date` for a country.
- `period_year` and `period_month` — derived from
  the upstream `period` field.
- `balance_usd` — computed for a trade balance
  record.
- `asymmetry_usd` — computed for a bilateral record.

## 5.8 Canonical naming

The transformation stage normalises the
human-readable names to a canonical casing. The
canonical casing is title case for names and
lowercase for notes.

## 5.9 Transformation ownership

The transformation stage is owned by the ETL
layer. The stage is implemented in the
`un_comtrade.etl` module. The transformation
rules are declarative; the implementation is the
responsibility of the validation standard.

---

# 6. Normalization Strategy

The normalisation strategy declares the rules that
the ETL layer applies to convert a transformed
record into a canonical entity.

## 6.1 Canonical field mapping

The normalisation stage applies the canonical field
mapping declared in `006_DATA_MODEL.md` §4. The
mapping is the canonical binding between the
transformed record and the canonical entity. The
mapping SHALL NOT change the meaning of any field.

## 6.2 Consistent naming

The normalisation stage ensures that the
human-readable names are consistent across the
dataset. The consistency is verified by comparing
the resolved name for a code against the expected
name in the metadata catalogue.

## 6.3 Missing value handling

The normalisation stage preserves missing values
as `null` in the canonical entity. The normalisation
stage SHALL NOT infer a default value for a
missing value. A missing value is recorded as a
row-level warning.

## 6.4 Unknown value handling

The normalisation stage preserves unknown values
as a string in the canonical entity. The
normalisation stage SHALL NOT reject a record on
the basis of an unknown value. An unknown value
is recorded as a row-level warning.

## 6.5 Default value policy

The normalisation stage SHALL NOT apply default
values. The canonical entity records the actual
value returned by the upstream, including `null`
and unknown values.

## 6.6 Relationship resolution

The normalisation stage resolves the relationships
between entities. The resolution invokes the
metadata layer for every relationship. A
relationship that does not resolve is recorded as
a row-level warning.

## 6.7 Reference metadata usage

The normalisation stage uses the metadata catalogue
to resolve every code in the record. The catalogue
is loaded by the metadata layer and is accessed
through the documented interface.

## 6.8 Normalization ownership

The normalisation stage is owned by the ETL layer.
The stage is implemented in the `un_comtrade.etl`
module. The normalisation rules are declarative;
the implementation is the responsibility of the
validation standard.

---

# 7. Deduplication Strategy

The deduplication strategy declares the rules that
the ETL layer applies to remove duplicate records
from a canonical dataset.

## 7.1 Duplicate detection concepts

A duplicate is a record whose composite primary
key matches the composite primary key of another
record in the same dataset. The composite primary
key of a `TradeRecord` is declared in
`006_DATA_MODEL.md` §3.12.

## 7.2 Identity rules

The identity rules are declared in
`006_DATA_MODEL.md` §12. The composite primary key
of a `TradeRecord` is:

```
(reporter_code, partner_code, period, flow_code,
 commodity_code, classification_code, edition,
 customs_code, mot_code, partner2_code)
```

A `TradeRecord` whose composite primary key matches
another `TradeRecord` is a duplicate.

## 7.3 Conflict resolution policy

When two records have the same composite primary
key, the ETL layer applies the conflict resolution
policy declared in section 7.4. The default
conflict resolution policy is "latest wins"; the
record with the latest `ref_period_id` is
retained.

## 7.4 Duplicate removal expectations

The ETL layer removes duplicates by retaining the
record selected by the conflict resolution policy
and dropping the other records. The dropped records
are recorded in the `Response` envelope as a
warning.

## 7.5 Source precedence

The source precedence is:

- An authenticated response has higher precedence
  than a public preview response.
- A response with `is_reported=true` has higher
  precedence than a response with `is_reported=
  false`.
- A response with a later `ref_period_id` has higher
  precedence than a response with an earlier
  `ref_period_id`.

## 7.6 Version awareness

The deduplication stage is version-aware. A record
from a newer schema version has higher precedence
than a record from an older schema version. The
schema version is recorded on the record by the
upstream.

## 7.7 Deduplication ownership

The deduplication stage is owned by the ETL layer.
The stage is implemented in the `un_comtrade.etl`
module. The deduplication rules are declarative;
the implementation is the responsibility of the
validation standard.

---

# 8. Data Quality Rules

The data quality rules declare the expected quality
of the canonical dataset. The rules are checked by
the quality check stage of the pipeline.

## 8.1 Completeness

- **Definition.** Every required field is present.
- **Expected behaviour.** The quality check records
  the count of records that fail the completeness
  check. A failed completeness check is recorded as
  a row-level warning.

## 8.2 Consistency

- **Definition.** The values of related fields are
  consistent.
- **Expected behaviour.** The quality check records
  the count of records that fail the consistency
  check. A failed consistency check is recorded as
  a row-level warning.

## 8.3 Uniqueness

- **Definition.** The composite primary key of every
  record is unique within the dataset.
- **Expected behaviour.** The quality check records
  the count of duplicate records. A duplicate is
  resolved by the deduplication stage. A residual
  duplicate is recorded as a row-level warning.

## 8.4 Validity

- **Definition.** Every value satisfies the
  validation rules of the canonical data model.
- **Expected behaviour.** The quality check records
  the count of records that fail the validity check.
  A failed validity check is recorded as a row-level
  warning.

## 8.5 Referential integrity

- **Definition.** Every reference in the record
  resolves to a known entity.
- **Expected behaviour.** The quality check records
  the count of records that fail the referential
  integrity check. A failed referential integrity
  check is recorded as a row-level warning.

## 8.6 Accuracy (where verifiable)

- **Definition.** The values are consistent with the
  expected range and the expected format.
- **Expected behaviour.** The quality check records
  the count of records that fail the accuracy check.
  A failed accuracy check is recorded as a row-level
  warning.

## 8.7 Quality score

The ETL layer MAY compute a quality score for the
dataset. The quality score is the ratio of records
that pass every quality check to the total number
of records. The quality score is recorded in the
`Response` envelope.

## 8.8 Quality ownership

The quality check stage is owned by the ETL layer.
The stage is implemented in the `un_comtrade.etl`
module. The quality rules are declarative; the
implementation is the responsibility of the
validation standard.

---

# 9. Export Strategy

The export strategy declares how the ETL layer
packages the canonical dataset into the requested
output format.

## 9.1 Canonical objects

The default output format is the canonical objects.
The canonical objects are the entities declared in
`006_DATA_MODEL.md`. The consumer receives the
entities as native Python objects.

## 9.2 JSON

The ETL layer can export the canonical dataset as
JSON. The JSON serialisation follows the rules
declared in `006_DATA_MODEL.md` §14.1. The output
is a single JSON object with the documented top-
level keys.

## 9.3 CSV

The ETL layer can export the canonical dataset as
CSV. The CSV serialisation follows the rules
declared in `006_DATA_MODEL.md` §14.2. The output
is a CSV file with the documented header.

## 9.4 Parquet

The ETL layer can export the canonical dataset as
Parquet. The Parquet serialisation follows the
rules declared in `006_DATA_MODEL.md` §14.3. The
output is a Parquet file with the documented
schema.

## 9.5 Tabular datasets

A tabular dataset is a dataset that is intended for
direct consumption by a tabular analysis tool. The
tabular dataset is a CSV or a Parquet file with a
denormalised schema.

## 9.6 Future database export

A future version of the ETL layer MAY support
direct export to a database. The database layout
is out of scope of this document.

## 9.7 Export ownership

The export stage is owned by the ETL layer. The
stage is implemented in the `un_comtrade.etl`
module. The export rules are declarative; the
implementation is the responsibility of the
packaging specification (`013_PACKAGING_SPEC.md`).

---

# 10. Schema Evolution Strategy

The schema evolution strategy declares how the ETL
layer handles changes in the upstream schema and in
the canonical data model.

## 10.1 Backward compatibility

The ETL layer SHALL preserve backward compatibility
within a major SDK version. A change in the upstream
schema that does not change the canonical data
model is handled by the normalisation stage.

## 10.2 New fields

A new field in the upstream schema is preserved in
the canonical entity only if the field is declared
in the data model. A new field that is not declared
in the data model is ignored and MAY be logged as
a warning.

## 10.3 Deprecated fields

A deprecated field in the upstream schema is
preserved in the canonical entity as long as the
field is declared in the data model. A deprecated
field that is removed from the data model is
removed from the canonical entity. The removal is
announced in the changelog.

## 10.4 Removed fields

A removed field in the upstream schema is preserved
in the canonical entity as `null`. The ETL layer
does not raise an error on a removed field.

## 10.5 Field renaming

A renamed field in the upstream schema is
preserved under the new canonical name. The ETL
layer maps the new upstream name to the canonical
name through the field mapping. A renamed field
that is not mapped is preserved under the old
canonical name with a warning.

## 10.6 Version compatibility

A change in the schema version is recorded in the
`Response` envelope. The ETL layer SHALL NOT raise
an error on a schema version change within the
documented compatibility window. A schema version
change outside the compatibility window is a
fatal validation error.

## 10.7 Migration expectations

A consumer who upgrades the SDK SHALL be able to
migrate the canonical dataset without code changes
within a major SDK version. A migration that
requires code changes is announced in the
changelog and is recorded in the decisions log.

## 10.8 Schema evolution ownership

The schema evolution strategy is owned by the ETL
layer. The strategy is implemented in the
`un_comtrade.etl` module. The strategy is declarative;
the implementation is the responsibility of the
validation standard and the testing standard.

---

# 11. Error Handling

The error handling section declares the ETL-specific
errors and the expected behaviour of the ETL layer
when an error occurs.

## 11.1 Validation failures

A validation failure is a record that does not
satisfy the validation rules. The ETL layer records
the failure as a row-level warning and either drops
the record or marks it as quarantined.

## 11.2 Transformation failures

A transformation failure is a record that cannot
be transformed into a canonical entity. The ETL
layer records the failure as a row-level warning
and drops the record.

## 11.3 Unknown metadata

An unknown metadata code is a code that does not
resolve through the metadata layer. The ETL layer
records the unknown code as a row-level warning and
preserves the code as a string.

## 11.4 Duplicate conflicts

A duplicate conflict is two records with the same
composite primary key. The ETL layer resolves the
conflict by the documented conflict resolution
policy and records the dropped record as a
warning.

## 11.5 Schema mismatches

A schema mismatch is an upstream schema version
that is not consistent with the expected version.
The ETL layer raises a `TradeError` and aborts the
extraction.

## 11.6 Export failures

An export failure is a failure to package the
canonical dataset into the requested output
format. The ETL layer raises a `TradeError` and
returns the error message to the consumer.

## 11.7 Recovery expectations

The ETL layer recovers from validation failures
through the row-level warning mechanism. The ETL
layer recovers from transformation failures
through the row-level warning mechanism. The ETL
layer recovers from schema mismatches by aborting
the extraction. The ETL layer recovers from export
failures by retrying the export with the same
format.

---

# 12. Pipeline Lifecycle

The pipeline lifecycle describes the path that a
record follows from input to storage.

```
Input
    |
    v
Extract
    |
    v
Validate
    |
    v
Transform
    |
    v
Normalize
    |
    v
Deduplicate
    |
    v
Quality Check
    |
    v
Export
    |
    v
Complete
```

## 12.1 Input

The input is the API response received from the
trade layer. The input carries the top-level keys
and the records.

## 12.2 Extract

The extract stage receives the API response and
produces a stream of raw records. The extract
stage is the entry point of the pipeline.

## 12.3 Validate

The validate stage validates each raw record
against the canonical data model. The validation
rules are declared in section 4 of this document.

## 12.4 Transform

The transform stage converts the raw record into a
transformed record. The transformation rules are
declared in section 5 of this document.

## 12.5 Normalize

The normalise stage converts the transformed record
into a canonical entity. The normalisation rules
are declared in section 6 of this document.

## 12.6 Deduplicate

The deduplicate stage removes duplicate records.
The deduplication rules are declared in section 7
of this document.

## 12.7 Quality Check

The quality check stage verifies the quality of the
canonical dataset. The quality rules are declared
in section 8 of this document.

## 12.8 Export

The export stage packages the canonical dataset
into the requested output format. The export rules
are declared in section 9 of this document.

## 12.9 Complete

The complete stage hands off the canonical dataset
to the storage layer. The storage rules are
declared in `011_STORAGE_SPECIFICATION.md`.

---

# 13. Performance Considerations

The performance considerations section declares the
expected performance characteristics of the ETL
layer.

## 13.1 Large datasets

A large dataset is a dataset that exceeds 250,000
records. The ETL layer processes a large dataset
through the batch processing strategy. The total
latency is the sum of the per-page latencies plus
the backoff time plus the validation, transformation,
and normalisation time.

## 13.2 Memory considerations

The memory consumption of the ETL layer is bounded
by the per-call cap. The ETL layer does not load
the entire result into memory before processing;
the ETL layer processes the records in a streaming
fashion.

## 13.3 Incremental processing

An incremental processing is a processing that
consumes only the records that have changed since
the last successful extraction. The ETL layer
supports incremental processing through the
watermark strategy declared in the ETL
specification.

## 13.4 Batch processing

A batch processing is a processing that consumes
a batch of records at a time. The ETL layer
processes records in batches whose size is
configurable. The default batch size is 1,000
records.

## 13.5 Pipeline scalability

The ETL layer scales linearly with the size of the
input dataset. The ETL layer does not impose a
process-level limit.

---

# 14. Integration Points

The integration points section declares how the
ETL layer interacts with the other layers of the
SDK.

## 14.1 Trade Layer

The ETL layer consumes the trade layer for the
extraction of trade data. The trade layer is the
only source of trade data for the ETL layer. The
ETL layer treats the trade layer as a black box
and interacts with it through the documented
public surface.

## 14.2 Metadata Layer

The ETL layer consumes the metadata layer for the
resolution of every code in a record. The
metadata layer is the only source of metadata
information for the ETL layer. The ETL layer
treats the metadata layer as a black box and
interacts with it through the documented public
surface.

## 14.3 Infrastructure Layer

The ETL layer consumes the infrastructure services
for configuration, retry, timeout, logging, cache,
progress reporting, resume support, error
handling, request tracking, diagnostics, and
security. The ETL layer treats the infrastructure
layer as a black box and interacts with it
through the documented interfaces.

## 14.4 Storage Layer

The ETL layer hands off the canonical dataset to
the storage layer. The storage layer is the only
layer that performs filesystem I/O. The ETL
layer interacts with the storage layer through
the documented interface.

## 14.5 Analytics Layer

The ETL layer produces a canonical dataset that the
analytics layer consumes. The analytics layer is
out of scope of the SDK. The ETL layer does not
interact with the analytics layer directly.

## 14.6 Export Layer

The ETL layer invokes the export layer to package
the canonical dataset into the requested output
format. The export layer is the only layer that
performs output formatting.

## 14.7 Boundaries

The ETL layer is the boundary between the upstream
wire format and the canonical data model. The
ETL layer is also the boundary between the in-
memory dataset and the persisted dataset. The
ETL layer is also the boundary between the
SDK's internal model and the consumer's external
model.

---

# 15. Data Lineage

The data lineage section declares how the
provenance of a record is preserved through the
ETL pipeline.

## 15.1 Source identification

Every record carries a `provenance` field that
identifies the source of the record. The source
identification includes:

- The endpoint family (T1, T2, ..., P1, ...).
- The endpoint URL.
- The subscription key fingerprint (a hash of the
  key, not the key itself).
- The extraction timestamp.

## 15.2 Transformation stages

Every record carries the list of transformation
stages that the record has passed through. The
list is a sequence of stage names: `extract`,
`validate`, `transform`, `normalise`,
`deduplicate`, `quality_check`, `export`,
`store`.

## 15.3 Normalization tracking

Every record carries the normalisation stage that
the record has passed through. The normalisation
stage records the canonical entity type and the
canonical field set.

## 15.4 Version awareness

Every record carries the upstream schema version
that the record was extracted from. The schema
version is recorded by the upstream.

## 15.5 Lineage ownership

The data lineage strategy is owned by the ETL
layer. The strategy is implemented in the
`un_comtrade.etl` module. The lineage metadata is
stored in the canonical entity's `provenance`
field.

---

# 16. Future Extensibility

The future extensibility section declares how new
datasets, transformations, validation rules, and
export targets can be introduced without affecting
existing consumers.

## 16.1 New datasets

A new dataset is added in a minor version. The new
dataset SHALL be documented in the trade layer
specification. The ETL layer SHALL be updated to
handle the new dataset through the documented
interface.

## 16.2 New transformations

A new transformation is added in a minor version.
The new transformation SHALL be documented in
section 5 of this document. The new transformation
SHALL NOT change the output of an existing
transformation.

## 16.3 New validation rules

A new validation rule is added in a minor version.
The new rule SHALL be documented in section 4 of
this document. The new rule SHALL NOT change the
behaviour of an existing rule.

## 16.4 New export targets

A new export target is added in a minor version.
The new target SHALL be documented in section 9
of this document. The new target SHALL be
discoverable through the documented interface.

## 16.5 Deprecation

A deprecated dataset, transformation, validation
rule, or export target is preserved in the SDK
until the deprecation period expires. The
deprecation is recorded in the changelog and the
decisions log.

---

# 17. Assumptions

The assumptions below are recorded for
traceability. An assumption that turns out to be
false is recorded in `DECISIONS.md` as a
correction and is propagated to the relevant
specification documents.

## 17.1 Verified assumptions

- The trade layer returns a `Response` envelope
  with the documented top-level keys. Verified
  by the trade layer specification and by live
  request.
- The trade layer applies the documented
  normalisation rules. Verified by the trade
  layer specification.
- The metadata layer resolves every code in a
  record. Verified by the metadata layer
  specification.
- The canonical data model declares 25 entities.
  Verified by the data model specification.

## 17.2 Inferred assumptions

- The conflict resolution policy "latest wins" is
  a reasonable default. The default is not
  verified against the consumer.
- The batch size of 1,000 records is a reasonable
  default. The default is not verified against
  the consumer.
- The quality score is a useful summary metric.
  The metric is not verified against the
  consumer.
- The provenance field is a useful traceability
  mechanism. The mechanism is not verified
  against the consumer.

## 17.3 Local design decisions

- The ETL layer is owned by a new module,
  `un_comtrade.etl`. The module name is a local
  design decision; the implementation may
  collapse the ETL layer into the trade layer if
  the architecture permits it.
- The ETL pipeline is composed of 9 stages. The
  stages are a local design decision; the
  implementation may collapse stages if the
  implementation permits it.
- The default conflict resolution policy is
  "latest wins". The policy is a local design
  decision; the consumer can override the policy
  through a configuration parameter.
- The default batch size is 1,000 records. The
  batch size is a local design decision; the
  consumer can override the batch size through a
  configuration parameter.
- The default output format is the canonical
  objects. The format is a local design
  decision; the consumer can override the format
  through a configuration parameter.
- The default behaviour on a validation failure
  is to drop the record. The behaviour is a
  local design decision; the consumer can
  override the behaviour through a configuration
  parameter.

---

# 18. Open Questions

The questions below are recorded for future
resolution. Each question is described with the
impact and the suggested verification.

- **OQ-ETL-001 (High).** Should the ETL layer
  expose a streaming output for very large
  datasets? **Impact.** A streaming output
  would reduce memory consumption. **Suggested
  verification.** Confirm with the consumer
  requirements.

- **OQ-ETL-002 (High).** Should the ETL layer
  support a parallel validation and transformation
  of records? **Impact.** A parallel processing
  would reduce the per-dataset latency. **Suggested
  verification.** Confirm with the consumer
  requirements.

- **OQ-ETL-003 (Medium).** Should the ETL layer
  support a custom conflict resolution policy
  through a documented extension point? **Impact.**
  A custom policy would enable consumer-specific
  deduplication. **Suggested verification.**
  Confirm with the consumer requirements.

- **OQ-ETL-004 (Medium).** Should the ETL layer
  support a custom validation rule through a
  documented extension point? **Impact.** A
  custom rule would enable consumer-specific
  quality checks. **Suggested verification.**
  Confirm with the consumer requirements.

- **OQ-ETL-005 (Medium).** Should the ETL layer
  support a custom quality score formula through
  a documented extension point? **Impact.** A
  custom formula would enable consumer-specific
  quality scoring. **Suggested verification.**
  Confirm with the consumer requirements.

- **OQ-ETL-006 (Medium).** Should the ETL layer
  support a `quarantine=True` flag that, when set,
  routes failed records to a quarantine store
  instead of dropping them? **Impact.** A
  quarantine mechanism would improve the
  consumer experience. **Suggested verification.**
  Confirm with the consumer requirements.

- **OQ-ETL-007 (Medium).** Should the ETL layer
  support a direct export to a database through a
  documented extension point? **Impact.** A
  direct export would enable pipeline-free
  loading. **Suggested verification.** Confirm
  with the storage requirements.

- **OQ-ETL-008 (Low).** Should the ETL layer
  support a watermark strategy that records the
  last successful period per (reporter, partner,
  flow, commodity) tuple? **Impact.** A
  watermark strategy would enable incremental
  extraction. **Suggested verification.** Confirm
  with the consumer requirements.

- **OQ-ETL-009 (Low).** Should the ETL layer
  support a `diff=True` flag that, when set,
  consumes the upstream diff endpoint (OQ-TL-014)
  and returns only the changed records?
  **Impact.** A diff mechanism would enable
  change-data-capture workflows. **Suggested
  verification.** Confirm with the storage
  requirements.

- **OQ-ETL-010 (Low).** Should the ETL layer
  expose a `get_provenance(record_id)` method
  that returns the full provenance chain of a
  record? **Impact.** A provenance-chain method
  would improve the consumer experience.
  **Suggested verification.** Confirm with the
  consumer requirements.

---

# End of document
