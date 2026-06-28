```
Document ID
006

Title
Canonical Data Model Specification

Version
0.1.0

Status
DRAFT

Created
2026-06-26T20:07:45Z

Last Updated
2026-06-26T20:07:45Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
005_API_ENDPOINT_CATALOG.md

Supersedes
None
```

---

# 1. Data Model Overview

## 1.1 Purpose

The Canonical Data Model Specification defines the stable
internal domain model of the UN Comtrade Python SDK. The
model is the single source of truth for every SDK model,
ETL normalisation, storage schema, analytics input, and
future serialisation format that the project produces or
consumes.

The model is deliberately decoupled from the wire format
of the UN Comtrade API. The upstream API exposes its
records as a flat JSON object with 47 fields; the
canonical model is a richer, type-safe, normalised
representation that the upstream wire format is mapped
into by the normalisation layer.

## 1.2 Design philosophy

The model is governed by the following principles. Each
principle is binding for every future model revision.

- **Canonical, not reflective.** The model represents the
  domain, not the wire format. The wire format is one
  possible projection of the model.
- **Stable across upstream evolution.** A change in the
  upstream field name or wire shape is a change in the
  normalisation layer, not in the model.
- **Explicit nullability.** Every field declares whether
  it is nullable, conditionally nullable, or
  non-nullable. The reason is recorded.
- **Documented provenance.** Every field declares its
  source: verified from the upstream, derived from a
  combination of upstream fields, or computed locally.
- **Verifiable identity.** Every entity declares a
  primary identifier and, where applicable, a natural
  key. Identifiers are stable for the lifetime of the
  entity.
- **Minimal coupling.** Entities are coupled through
  declared relationships. A change in one entity SHALL
  NOT require a change in another except through the
  declared relationship.

## 1.3 Canonical model vs. API response model

The canonical model and the API response model are two
distinct projections of the same domain. The
relationship between them is summarised in the table
below.

| Aspect              | API response model              | Canonical model                |
| ------------------- | ------------------------------- | ------------------------------ |
| Owner               | Upstream UN Comtrade API        | This project                   |
| Format              | JSON object, 47 fields, flat    | Typed entities, structured     |
| Naming              | camelCase (`reporterCode`)      | snake_case (`reporter_code`)   |
| Nullability         | Inconsistent                    | Explicit, documented            |
| Identifier case     | Mixed (`partnerISO` vs `W00`)   | String codes, ISO-3 uppercase  |
| Estimation flags    | `legacyEstimationFlag` integer  | Boolean + integer reason       |
| Description fields  | `cmdDesc` may be null           | Description is a separate field |
| Aggregations        | Mixed in same payload           | Explicit `is_aggregate` field  |
| Provenance          | Implicit (publisher unknown)    | Explicit `provenance` block    |

## 1.4 Stability goals

The model is stable across a major SDK version. The
following changes do not require a major version
increment:

- Adding a new field to an existing entity, when the
  field is nullable.
- Adding a new entity.
- Adding a new value to an existing enumeration, when
  the new value is documented in the upstream.
- Adding a new relationship between existing entities.

The following changes require a major version increment
and a recorded decision:

- Removing an entity.
- Removing a field.
- Renaming a field.
- Changing the datatype of a field.
- Changing the nullability of a field from nullable to
  non-nullable.
- Changing the meaning of a field.

## 1.5 Versioning strategy

The data model is versioned independently of the SDK.
The version of the data model is incremented when a
change to the model is committed. The SDK version is
incremented when the SDK code that consumes the model
is changed. A binding model change SHALL be reflected
in the SDK version in the same release.

---

# 2. Entity Catalog

The entity catalog is the inventory of every domain
entity defined by the canonical model. Each entity is
specified in section 3 and its fields in section 4.

## 2.1 Identity entities

- **E01 Country.** A political entity that reports trade
  data and/or is a partner in a trade record. The
  entity unifies reporters and partners; the
  `is_reporter` flag distinguishes them.
- **E02 Classification.** A product classification system
  (HS, SITC, BEC, EBOPS, etc.). A classification has
  one or more editions.
- **E03 ClassificationEdition.** A specific edition of a
  classification (HS 2022, HS 2017, SITC Rev.4, etc.).
- **E04 CommodityCode.** A product code in the context
  of a specific classification edition.
- **E05 TradeFlow.** The direction of a trade (import,
  export, re-import, re-export).
- **E06 TransportMode.** The mode of transport used when
  goods cross the border.
- **E07 CustomsProcedure.** The customs procedure applied
  to a trade.
- **E08 QuantityUnit.** A unit of measurement for
  quantities in a trade record.
- **E09 Frequency.** The time granularity of a query or
  a record (annual, monthly).
- **E10 Period.** A reference period in time.
- **E11 ModeOfSupply.** The mode of supply for a
  services trade.

## 2.2 Trade entities

- **E12 TradeRecord.** A single trade observation — the
  canonical equivalent of the upstream 47-field record.
- **E13 TariffLineRecord.** A line-level trade
  observation, derived from the upstream tariffline
  payload.
- **E14 TradeBalanceRecord.** A trade-balance observation
  that pairs an export value and an import value for
  the same query.
- **E15 BilateralRecord.** A bilateral observation that
  pairs a reported value and a mirror value.
- **E16 StandardUnitValue.** A reference unit value and
  range for a commodity.
- **E17 PublicationNote.** A publication note attached to
  a release.

## 2.3 Administrative entities

- **E18 DataAvailabilityRecord.** A data availability
  observation, used to size a query before issuing it.
- **E19 AsyncRequestHandle.** A handle returned by the
  async submit endpoint.
- **E20 AsyncRequestStatus.** A status observation
  returned by the async check endpoint.

## 2.4 Envelope entities

- **E21 Request.** A canonical request descriptor.
- **E22 Response.** A canonical response envelope.
- **E23 ErrorResponse.** A canonical error envelope.
- **E24 MetadataCollection.** A collection of reference
  records, used as a typed handoff shape for the
  metadata endpoints.
- **E25 Pagination.** A pagination cursor. (The upstream
  API does not expose pagination, but the canonical
  model reserves the entity for future compatibility.)

## 2.5 Summary

| ID    | Entity                  | Primary identifier            |
| ----- | ----------------------- | ----------------------------- |
| E01   | Country                 | `country_code`                |
| E02   | Classification          | `classification_code`         |
| E03   | ClassificationEdition   | `classification_code`, `edition` |
| E04   | CommodityCode           | `commodity_code`, `classification_code`, `edition` |
| E05   | TradeFlow               | `flow_code`                   |
| E06   | TransportMode           | `mot_code`                    |
| E07   | CustomsProcedure        | `customs_code`                |
| E08   | QuantityUnit            | `qty_unit_code`               |
| E09   | Frequency               | `frequency_code`              |
| E10   | Period                  | `period`                      |
| E11   | ModeOfSupply            | `mos_code`                    |
| E12   | TradeRecord             | composite, see §3.12          |
| E13   | TariffLineRecord        | composite, see §3.13          |
| E14   | TradeBalanceRecord      | composite, see §3.14          |
| E15   | BilateralRecord         | composite, see §3.15          |
| E16   | StandardUnitValue       | `cmd_code`, `period`          |
| E17   | PublicationNote         | `period`, `reporter_code`     |
| E18   | DataAvailabilityRecord  | `reporter_code`, `period`     |
| E19   | AsyncRequestHandle      | `request_id`                  |
| E20   | AsyncRequestStatus      | `request_id`                  |
| E21   | Request                 | n/a (transient)               |
| E22   | Response                | n/a (transient)               |
| E23   | ErrorResponse           | n/a (transient)               |
| E24   | MetadataCollection      | `collection_type`             |
| E25   | Pagination              | n/a (reserved)                |

---

# 3. Entity Specifications

This section specifies every entity declared in the
catalog. For each entity, the specification records
the description, the primary key, the unique
constraints, the business rules, the relationships, the
validation rules, and the lifecycle.

## 3.1 E01 Country

- **Description.** A political entity that appears in a
  trade record as a reporter or as a partner. The
  entity is unified across the two roles; the role is
  recorded on the relationship, not on the entity.
- **Primary key.** `country_code` (integer).
- **Unique constraints.** `(country_code)` is unique. The
  tuple `(iso_alpha2, iso_alpha3)` is unique.
- **Business rules.** A country is uniquely identified
  by its `country_code`. A country may have an
  expiration date; an expired country SHALL NOT be
  used as a reporter. A country may be a group
  aggregate; group countries SHALL be used only as
  partners, not as reporters.
- **Relationships.** Referenced by E12 TradeRecord
  (twice — as reporter and as partner) and by E18
  DataAvailabilityRecord.
- **Validation rules.** `country_code` SHALL be a
  non-negative integer. `iso_alpha2` SHALL be a
  two-letter ISO 3166-1 alpha-2 code. `iso_alpha3`
  SHALL be a three-letter ISO 3166-1 alpha-3 code.
  `entry_effective_date` SHALL be a valid ISO-8601
  date. `entry_expired_date`, if present, SHALL be a
  valid ISO-8601 date later than
  `entry_effective_date`.
- **Lifecycle.** A country is created when the
  reference catalogue publishes a new code, persists
  through the validity window, and is retired when
  `entry_expired_date` is set. A retired country
  remains in the catalogue for historical queries.

## 3.2 E02 Classification

- **Description.** A product classification system.
- **Primary key.** `classification_code` (string).
- **Unique constraints.** `(classification_code)` is
  unique.
- **Business rules.** A classification is identified by
  a short code (e.g. `HS`, `SITC`, `BEC`, `EBOPS`).
  The classification has at least one edition.
- **Relationships.** Composed of one or more
  ClassificationEdition entities (E03). Referenced by
  every trade record (E12–E17).
- **Validation rules.** `classification_code` SHALL be a
  non-empty string from the upstream reference
  catalogue. `display_name` SHALL be a non-empty
  string.
- **Lifecycle.** A classification is created when the
  reference catalogue publishes it. A classification
  is retired when the upstream removes the
  classification from the catalogue.

## 3.3 E03 ClassificationEdition

- **Description.** A specific edition of a
  classification.
- **Primary key.** `(classification_code, edition)`.
- **Unique constraints.** The composite key is unique.
- **Business rules.** An edition is a version of a
  classification (e.g. HS 2022, SITC Rev.4). The
  edition SHALL be one of the documented values for
  the classification.
- **Relationships.** Owned by E02 Classification.
  Composed of one or more CommodityCode entities
  (E04).
- **Validation rules.** `edition` SHALL match the
  upstream convention for the classification.
- **Lifecycle.** An edition is created when the
  upstream publishes the edition. The edition is
  retired when the upstream supersedes it.

## 3.4 E04 CommodityCode

- **Description.** A product code in the context of a
  specific classification edition.
- **Primary key.**
  `(commodity_code, classification_code, edition)`.
- **Unique constraints.** The composite key is unique.
  The wildcard `TOTAL` SHALL NOT collide with a real
  code.
- **Business rules.** A commodity code identifies a
  product in a classification. The same text may
  appear in multiple editions with different
  meanings; the edition is part of the key.
- **Relationships.** Owned by E03 ClassificationEdition.
  Referenced by E12 TradeRecord and E13
  TariffLineRecord.
- **Validation rules.** `commodity_code` SHALL be a
  string of the documented length for the
  classification (2, 4, or 6 digits for HS). The
  wildcard `TOTAL` is allowed and selects every
  commodity.
- **Lifecycle.** A commodity code is created when the
  upstream publishes it. A commodity code may be
  reclassified in a later edition; the old code
  remains valid for historical queries.

## 3.5 E05 TradeFlow

- **Description.** The direction of a trade.
- **Primary key.** `flow_code` (string).
- **Unique constraints.** `(flow_code)` is unique.
- **Business rules.** The trade flow is one of the
  documented values. The value `M` represents import,
  `X` represents export, `RX` represents re-export,
  `RM` represents re-import.
- **Relationships.** Referenced by E12 TradeRecord and
  E13 TariffLineRecord.
- **Validation rules.** `flow_code` SHALL be one of the
  documented values in the trade flow catalogue.
- **Lifecycle.** A trade flow is created when the
  upstream publishes it. A trade flow is retired
  when the upstream removes it.

## 3.6 E06 TransportMode

- **Description.** A mode of transport.
- **Primary key.** `mot_code` (string or integer).
- **Unique constraints.** `(mot_code)` is unique.
- **Business rules.** A transport mode is identified
  by a code; the total is `0`.
- **Relationships.** Referenced by E12 TradeRecord and
  E13 TariffLineRecord.
- **Validation rules.** `mot_code` SHALL be a value
  from the modes of transport catalogue.
- **Lifecycle.** A transport mode is created when the
  upstream publishes it. A transport mode is retired
  when the upstream removes it.

## 3.7 E07 CustomsProcedure

- **Description.** A customs procedure applied to a
  trade.
- **Primary key.** `customs_code` (string).
- **Unique constraints.** `(customs_code)` is unique.
- **Business rules.** A customs procedure is identified
  by a code; the total is `C00`.
- **Relationships.** Referenced by E12 TradeRecord and
  E13 TariffLineRecord.
- **Validation rules.** `customs_code` SHALL be a value
  from the customs catalogue.
- **Lifecycle.** A customs procedure is created when
  the upstream publishes it. A customs procedure is
  retired when the upstream removes it.

## 3.8 E08 QuantityUnit

- **Description.** A unit of measurement for
  quantities.
- **Primary key.** `qty_unit_code` (integer).
- **Unique constraints.** `(qty_unit_code)` is unique.
- **Business rules.** The total is `-1` (not
  applicable). A value of `8` is kilograms.
- **Relationships.** Referenced by E12 TradeRecord and
  E13 TariffLineRecord.
- **Validation rules.** `qty_unit_code` SHALL be a
  value from the quantity unit catalogue.
- **Lifecycle.** A quantity unit is created when the
  upstream publishes it. A quantity unit is retired
  when the upstream removes it.

## 3.9 E09 Frequency

- **Description.** A time granularity.
- **Primary key.** `frequency_code` (string).
- **Unique constraints.** `(frequency_code)` is unique.
- **Business rules.** The value `A` represents annual,
  `M` represents monthly.
- **Relationships.** Referenced by every period and by
  every query.
- **Validation rules.** `frequency_code` SHALL be one
  of the documented values.
- **Lifecycle.** A frequency is created when the
  upstream publishes it. A frequency is retired when
  the upstream removes it.

## 3.10 E10 Period

- **Description.** A reference period in time.
- **Primary key.** `(period, frequency_code)`.
- **Unique constraints.** The composite key is unique.
- **Business rules.** A period is a year for annual
  data (`2022`) or a year-month for monthly data
  (`202201`). The format is enforced by the
  `frequency_code`.
- **Relationships.** Referenced by E12 TradeRecord,
  E13 TariffLineRecord, and every query.
- **Validation rules.** For `frequency_code='A'`,
  `period` SHALL be a four-digit year. For
  `frequency_code='M'`, `period` SHALL be a six-digit
  year-month.
- **Lifecycle.** A period is created when the upstream
  publishes data for the period. The period is
  superseded when the upstream revises the data for
  the period.

## 3.11 E11 ModeOfSupply

- **Description.** A mode of supply for a services
  trade.
- **Primary key.** `mos_code` (string).
- **Unique constraints.** `(mos_code)` is unique.
- **Business rules.** The total is `0`.
- **Relationships.** Referenced by E12 TradeRecord
  when `type_code='S'`.
- **Validation rules.** `mos_code` SHALL be a value
  from the modes of supply catalogue.
- **Lifecycle.** A mode of supply is created when the
  upstream publishes it. A mode of supply is retired
  when the upstream removes it.

## 3.12 E12 TradeRecord

- **Description.** A single trade observation. The
  canonical equivalent of the upstream 47-field record.
- **Primary key.** Composite:
  `(reporter_code, partner_code, period, flow_code,
  commodity_code, classification_code, edition,
  customs_code, mot_code, partner2_code)`. The primary
  key is unique within the upstream dataset.
- **Unique constraints.** The composite key is unique.
- **Business rules.** A trade record represents one
  trade observation between a reporter and a partner
  for a given period, flow, commodity, and
  classification edition. The record is the canonical
  form of an upstream record.
- **Relationships.** References E01 Country (twice — as
  reporter and as partner), E04 CommodityCode, E05
  TradeFlow, E06 TransportMode, E07 CustomsProcedure,
  E08 QuantityUnit, E09 Frequency, E10 Period, E11
  ModeOfSupply, E03 ClassificationEdition.
- **Validation rules.** `primary_value` SHALL be a
  non-negative number. `qty` SHALL be a non-negative
  number when present. The combination of reporter,
  partner, period, flow, commodity, classification,
  edition, customs, transport mode, and secondary
  partner SHALL be unique.
- **Lifecycle.** A trade record is created when the
  normalisation layer produces it from an upstream
  response. The record is superseded when the
  upstream revises the data.

## 3.13 E13 TariffLineRecord

- **Description.** A line-level trade observation.
  Structurally similar to a TradeRecord but carrying
  line-level metadata.
- **Primary key.** Composite, as E12, plus a
  `line_id` derived from the upstream.
- **Unique constraints.** The composite key is unique.
- **Business rules.** A tariffline record is a
  trade record at the most granular level reported
  by the upstream. The `line_id` is upstream-defined
  and SHALL be preserved.
- **Relationships.** As E12.
- **Validation rules.** As E12. `line_id` SHALL be a
  non-empty string.
- **Lifecycle.** As E12.

## 3.14 E14 TradeBalanceRecord

- **Description.** A trade-balance observation that
  pairs an export value and an import value for the
  same query.
- **Primary key.** Composite:
  `(reporter_code, partner_code, period, commodity_code,
  classification_code, edition, customs_code, mot_code,
  partner2_code)`.
- **Unique constraints.** The composite key is unique.
- **Business rules.** A trade balance record contains
  both the export and the import value for the same
  query. The balance is the difference between the
  two values.
- **Relationships.** As E12.
- **Validation rules.** As E12. `export_value` and
  `import_value` SHALL be non-negative numbers.
- **Lifecycle.** As E12.

## 3.15 E15 BilateralRecord

- **Description.** A bilateral observation that pairs
  a reported value and a mirror value.
- **Primary key.** Composite, as E12.
- **Unique constraints.** The composite key is unique.
- **Business rules.** A bilateral record contains both
  the value reported by the reporter and the value
  reported by the partner. The asymmetry is the
  difference between the two values.
- **Relationships.** As E12.
- **Validation rules.** As E12. `reported_value` and
  `mirror_value` SHALL be non-negative numbers.
- **Lifecycle.** As E12.

## 3.16 E16 StandardUnitValue

- **Description.** A reference unit value and range
  for a commodity.
- **Primary key.** `(commodity_code, period,
  classification_code, edition)`.
- **Unique constraints.** The composite key is unique.
- **Business rules.** A standard unit value record
  provides a reference price for a commodity. The
  record is used to detect price outliers.
- **Relationships.** References E04 CommodityCode, E10
  Period, E03 ClassificationEdition.
- **Validation rules.** `unit_value` SHALL be a
  non-negative number.
- **Lifecycle.** A standard unit value is created
  when the upstream publishes it. The value is
  superseded when the upstream revises the reference.

## 3.17 E17 PublicationNote

- **Description.** A publication note attached to a
  release.
- **Primary key.** `(period, reporter_code,
  classification_code, edition)`.
- **Unique constraints.** The composite key is unique.
- **Business rules.** A publication note records the
  publication version of a captured dataset. The
  record is used to tag stored data with its
  provenance.
- **Relationships.** References E01 Country, E10
  Period, E03 ClassificationEdition.
- **Validation rules.** `note_text` SHALL be a
  non-empty string.
- **Lifecycle.** A publication note is created when
  the upstream publishes the release. The note is
  superseded when the upstream revises the release.

## 3.18 E18 DataAvailabilityRecord

- **Description.** A data availability observation,
  used to size a query before issuing it.
- **Primary key.** `(reporter_code, period,
  classification_code, edition)`.
- **Unique constraints.** The composite key is unique.
- **Business rules.** A data availability record
  records the count of records available for the
  combination of reporter, period, and classification.
- **Relationships.** References E01 Country, E10
  Period, E03 ClassificationEdition.
- **Validation rules.** `record_count` SHALL be a
  non-negative integer.
- **Lifecycle.** As E12.

## 3.19 E19 AsyncRequestHandle

- **Description.** A handle returned by the async
  submit endpoint.
- **Primary key.** `request_id` (string, UUID).
- **Unique constraints.** `(request_id)` is unique.
- **Business rules.** A handle identifies an async
  request. The handle is used to poll for status and
  to download the result.
- **Relationships.** None.
- **Validation rules.** `request_id` SHALL be a
  non-empty string.
- **Lifecycle.** A handle is created when the
  upstream accepts the async request. The handle is
  retired when the result is downloaded or the
  request expires.

## 3.20 E20 AsyncRequestStatus

- **Description.** A status observation returned by
  the async check endpoint.
- **Primary key.** `request_id` (string, UUID).
- **Unique constraints.** `(request_id)` is unique.
- **Business rules.** A status observation records the
  state of an async request.
- **Relationships.** References E19 AsyncRequestHandle.
- **Validation rules.** `status` SHALL be one of the
  documented values.
- **Lifecycle.** As E19.

## 3.21 E21 Request

- **Description.** A canonical request descriptor.
- **Primary key.** None (transient).
- **Unique constraints.** None.
- **Business rules.** A request is a transient
  descriptor that captures every parameter of a
  call to the SDK.
- **Relationships.** None.
- **Validation rules.** The request SHALL be valid
  against the rules of the targeted endpoint.
- **Lifecycle.** A request is created when the
  consumer calls an SDK method. The request is
  consumed when the SDK issues the call.

## 3.22 E22 Response

- **Description.** A canonical response envelope.
- **Primary key.** None (transient).
- **Unique constraints.** None.
- **Business rules.** A response is a transient
  envelope that wraps the records returned by an
  SDK call, the elapsed time, the count, and the
  error message.
- **Relationships.** Composed of zero or more records
  (E12–E17).
- **Validation rules.** `count` SHALL equal the
  number of records. `elapsed_seconds` SHALL be a
  non-negative number.
- **Lifecycle.** A response is created when the
  upstream returns the payload. The response is
  consumed when the SDK returns it to the consumer.

## 3.23 E23 ErrorResponse

- **Description.** A canonical error envelope.
- **Primary key.** None (transient).
- **Unique constraints.** None.
- **Business rules.** An error response captures the
  HTTP status, the upstream body, the upstream
  message, and the SDK-internal error category.
- **Relationships.** None.
- **Validation rules.** `http_status` SHALL be a
  non-negative integer in the documented range.
  `category` SHALL be one of the documented
  categories.
- **Lifecycle.** An error response is created when
  the upstream returns a non-2xx response. The
  error response is consumed when the SDK raises
  the corresponding exception.

## 3.24 E24 MetadataCollection

- **Description.** A typed collection of reference
  records.
- **Primary key.** `collection_type` (string).
- **Unique constraints.** `(collection_type)` is
  unique.
- **Business rules.** A metadata collection is a
  typed handoff shape that groups a set of
  reference records of the same kind.
- **Relationships.** Composed of zero or more
  reference entities (E01, E02, E05, E06, E07, E08,
  E11).
- **Validation rules.** `collection_type` SHALL be
  one of the documented values. The records SHALL
  be of the kind declared by `collection_type`.
- **Lifecycle.** A metadata collection is created
  when the metadata layer loads a reference table.
  The collection is superseded when the metadata
  layer refreshes the table.

## 3.25 E25 Pagination

- **Description.** A pagination cursor. Reserved.
- **Primary key.** None.
- **Unique constraints.** None.
- **Business rules.** The upstream API does not
  expose pagination. The entity is reserved for
  future compatibility.
- **Relationships.** None.
- **Validation rules.** None.
- **Lifecycle.** N/A.

---

# 4. Field Specifications

This section documents the field set of every entity.
The trade entities (E12–E15) reuse a common field
set; the common field set is documented first. The
identity entities and the envelope entities have their
own field sets.

The source of each field is recorded in parentheses:

- **(Verified)** — verified by live request during
  the research documented in `004_API_RESEARCH.md`.
- **(Documented)** — present in the official upstream
  documentation but not exercised during the
  research.
- **(Derived)** — derived locally from a combination
  of upstream fields.
- **(Computed)** — computed locally from upstream
  fields.
- **(Reserved)** — reserved for future use; the
  upstream may or may not produce the value.

## 4.1 E01 Country

| Field                    | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| ------------------------ | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| country_code             | integer  | yes      | no       | n/a     | ≥ 0            | non-negative | n/a | `699`   | (Verified) |
| short_name               | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | `India` | (Verified) |
| long_name                | string   | yes      | no       | n/a     | non-empty      | n/a         | n/a | `India` | (Verified) |
| note                     | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | `India, excluding Sikkim` | (Verified) |
| iso_alpha2               | string   | no       | yes      | n/a     | 2 letters      | ISO 3166-1 | n/a | `IN` | (Verified) |
| iso_alpha3               | string   | yes      | no       | n/a     | 3 letters      | ISO 3166-1 | n/a | `IND` | (Verified) |
| entry_effective_date     | string   | yes      | no       | n/a     | ISO-8601 date  | n/a         | n/a | `1975-01-01` | (Verified) |
| entry_expired_date       | string   | no       | yes      | n/a     | ISO-8601 date  | > entry_effective_date | n/a | `1974-12-31` | (Verified) |
| is_group                 | boolean  | yes      | no       | false   | true, false    | n/a         | n/a | `false` | (Verified) |
| is_reporter              | boolean  | no       | yes      | derived | true, false    | derived from entry_expired_date | n/a | `true` | (Derived) |

## 4.2 E02 Classification

| Field                  | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| ---------------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| classification_code    | string   | yes      | no       | n/a     | non-empty      | n/a         | n/a | `HS`   | (Verified) |
| display_name           | string   | yes      | no       | n/a     | non-empty      | n/a         | n/a | `Combined HS` | (Verified) |
| description            | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | `The classification of Combined HS — goods` | (Verified) |
| edition_count          | integer  | no       | yes      | derived | ≥ 0            | derived     | n/a | `1`     | (Derived) |

## 4.3 E03 ClassificationEdition

| Field                  | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| ---------------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| classification_code    | string   | yes      | no       | n/a     | non-empty      | FK to E02   | n/a | `HS`   | (Verified) |
| edition                | string   | yes      | no       | n/a     | non-empty      | matches upstream convention | n/a | `H6` | (Verified) |
| display_name           | string   | yes      | no       | n/a     | non-empty      | n/a         | n/a | `HS 2022` | (Documented) |
| year_introduced        | integer  | no       | yes      | n/a     | 1900..2100     | n/a         | year | `2022` | (Documented) |

## 4.4 E04 CommodityCode

| Field                  | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| ---------------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| commodity_code         | string   | yes      | no       | n/a     | non-empty      | length per classification | n/a | `090111` | (Verified) |
| classification_code    | string   | yes      | no       | n/a     | non-empty      | FK to E02   | n/a | `HS`   | (Verified) |
| edition                | string   | yes      | no       | n/a     | non-empty      | FK to E03   | n/a | `H6`   | (Verified) |
| description            | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | `Coffee, not roasted, not decaffeinated` | (Documented) |
| parent_code            | string   | no       | yes      | n/a     | non-empty      | FK to E04   | n/a | `0901` | (Derived) |
| level                  | integer  | no       | yes      | derived | 2..6 for HS    | derived from length | n/a | `6` | (Computed) |
| is_leaf                | boolean  | no       | yes      | derived | true, false    | derived     | n/a | `true` | (Computed) |

## 4.5 E05 TradeFlow

| Field          | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| -------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| flow_code      | string   | yes      | no       | n/a     | documented     | n/a         | n/a | `X`     | (Verified) |
| display_name   | string   | yes      | no       | n/a     | non-empty      | n/a         | n/a | `Export` | (Verified) |
| description    | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | `Outflow of goods` | (Verified) |

## 4.6 E06 TransportMode

| Field          | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| -------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| mot_code       | integer  | yes      | no       | n/a     | documented     | n/a         | n/a | `0`     | (Verified) |
| display_name   | string   | yes      | no       | n/a     | non-empty      | n/a         | n/a | `TOTAL MOT` | (Verified) |
| description    | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | `Total mode of transport` | (Verified) |

## 4.7 E07 CustomsProcedure

| Field          | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| -------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| customs_code   | string   | yes      | no       | n/a     | documented     | n/a         | n/a | `C00`   | (Verified) |
| display_name   | string   | yes      | no       | n/a     | non-empty      | n/a         | n/a | `TOTAL CPC` | (Verified) |
| description    | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | `Total customs procedure` | (Verified) |

## 4.8 E08 QuantityUnit

| Field           | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| --------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| qty_unit_code   | integer  | yes      | no       | n/a     | documented     | n/a         | n/a | `8`     | (Verified) |
| abbreviation    | string   | yes      | no       | n/a     | non-empty      | n/a         | n/a | `kg`    | (Verified) |
| display_name    | string   | yes      | no       | n/a     | non-empty      | n/a         | n/a | `Kilograms` | (Verified) |

## 4.9 E09 Frequency

| Field             | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| ----------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| frequency_code    | string   | yes      | no       | n/a     | `A`, `M`       | n/a         | n/a | `A`     | (Verified) |
| display_name      | string   | yes      | no       | n/a     | non-empty      | n/a         | n/a | `Annual` | (Documented) |
| description       | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | `Annual reference period` | (Documented) |

## 4.10 E10 Period

| Field             | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| ----------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| period            | string   | yes      | no       | n/a     | per frequency_code | format | n/a | `2022` | (Verified) |
| frequency_code    | string   | yes      | no       | n/a     | `A`, `M`       | FK to E09   | n/a | `A`     | (Verified) |
| year              | integer  | yes      | no       | n/a     | derived        | derived from period | year | `2022` | (Computed) |
| month             | integer  | no       | yes      | n/a     | 1..12          | derived from period when frequency_code='M' | month | `1` | (Computed) |

## 4.11 E11 ModeOfSupply

| Field          | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| -------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| mos_code       | string   | yes      | no       | n/a     | documented     | n/a         | n/a | `0`     | (Documented) |
| display_name   | string   | yes      | no       | n/a     | non-empty      | n/a         | n/a | `TOTAL MOS` | (Documented) |
| description    | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | `Total mode of supply` | (Documented) |

## 4.12 E12 TradeRecord — common fields

The following fields are common to E12, E13, E14, and
E15. Entity-specific extensions are documented in the
entity sections below.

| Field                | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| -------------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| type_code            | string   | yes      | no       | n/a     | `C`, `S`       | n/a         | n/a | `C`     | (Verified) |
| frequency_code       | string   | yes      | no       | n/a     | `A`, `M`       | FK to E09   | n/a | `A`     | (Verified) |
| classification_code  | string   | yes      | no       | n/a     | documented     | FK to E02   | n/a | `H6`   | (Verified) |
| classification_search_code | string | no    | yes      | n/a     | documented     | derived     | n/a | `HS`   | (Verified) |
| edition              | string   | yes      | no       | n/a     | documented     | FK to E03   | n/a | `H6`   | (Verified) |
| is_original_classification | boolean | no  | yes      | true    | true, false    | n/a         | n/a | `true`  | (Verified) |
| ref_period_id        | integer  | no       | yes      | n/a     | ≥ 0            | upstream-defined | n/a | `20220101` | (Verified) |
| ref_year             | integer  | yes      | no       | n/a     | 1900..2100     | n/a         | year | `2022` | (Verified) |
| ref_month            | integer  | yes      | no       | n/a     | 1..12 or 52    | 52 = annual | month | `52` | (Verified) |
| period               | string   | yes      | no       | n/a     | per frequency_code | format | n/a | `2022` | (Verified) |
| reporter_code        | integer  | yes      | no       | n/a     | documented     | FK to E01   | n/a | `699`   | (Verified) |
| reporter_iso3        | string   | no       | yes      | n/a     | 3 letters      | ISO 3166-1 | n/a | `IND` | (Verified) |
| reporter_name        | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | `India` | (Verified) |
| partner_code         | integer  | yes      | no       | n/a     | documented     | FK to E01, special `0` for World | n/a | `0` | (Verified) |
| partner_iso3         | string   | no       | yes      | n/a     | 3 letters or `W00` | ISO 3166-1 or sentinel | n/a | `W00` | (Verified) |
| partner_name         | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | `World` | (Verified) |
| partner2_code        | integer  | no       | yes      | 0       | documented     | FK to E01   | n/a | `0`     | (Verified) |
| partner2_iso3        | string   | no       | yes      | `W00`   | 3 letters or `W00` | ISO 3166-1 or sentinel | n/a | `W00` | (Verified) |
| partner2_name        | string   | no       | yes      | `World` | non-empty      | n/a         | n/a | `World` | (Verified) |
| flow_code            | string   | yes      | no       | n/a     | documented     | FK to E05   | n/a | `X`     | (Verified) |
| flow_name            | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | `Export` | (Verified) |
| commodity_code       | string   | yes      | no       | n/a     | documented or `TOTAL` | FK to E04 | n/a | `TOTAL` | (Verified) |
| commodity_name       | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | `All Commodities` | (Verified) |
| commodity_level      | integer  | no       | yes      | derived | 0..6 for HS    | derived from length | n/a | `0` | (Computed) |
| commodity_is_leaf    | boolean  | no       | yes      | derived | true, false    | derived     | n/a | `false` | (Computed) |
| commodity_is_aggregate | boolean | no      | yes      | derived | true, false    | derived     | n/a | `true`  | (Computed) |
| customs_code         | string   | yes      | no       | `C00`   | documented     | FK to E07   | n/a | `C00`   | (Verified) |
| customs_name         | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | `TOTAL CPC` | (Verified) |
| mos_code             | string   | yes      | no       | `0`     | documented     | FK to E11   | n/a | `0`     | (Verified) |
| mot_code             | integer  | yes      | no       | 0       | documented     | FK to E06   | n/a | `0`     | (Verified) |
| mot_name             | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | `TOTAL MOT` | (Verified) |
| qty_unit_code        | integer  | yes      | no       | n/a     | documented     | FK to E08   | n/a | `-1`    | (Verified) |
| qty_unit_abbr        | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | `N/A`   | (Verified) |
| qty                  | number   | no       | yes      | n/a     | ≥ 0            | n/a         | per unit | `0` | (Verified) |
| is_qty_estimated     | boolean  | no       | yes      | false   | true, false    | n/a         | n/a | `false` | (Verified) |
| alt_qty_unit_code    | integer  | no       | yes      | n/a     | documented     | FK to E08   | n/a | `-1`    | (Verified) |
| alt_qty_unit_abbr    | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | `N/A`   | (Verified) |
| alt_qty              | number   | no       | yes      | n/a     | ≥ 0            | n/a         | per unit | `0` | (Verified) |
| is_alt_qty_estimated | boolean  | no       | yes      | false   | true, false    | n/a         | n/a | `false` | (Verified) |
| net_weight_kg        | number   | no       | yes      | n/a     | ≥ 0            | n/a         | kilogram | `0` | (Verified) |
| is_net_weight_estimated | boolean | no     | yes      | false   | true, false    | n/a         | n/a | `false` | (Verified) |
| gross_weight_kg      | number   | no       | yes      | n/a     | ≥ 0            | n/a         | kilogram | `0` | (Verified) |
| is_gross_weight_estimated | boolean | no   | yes      | false   | true, false    | n/a         | n/a | `false` | (Verified) |
| fob_value_usd        | number   | no       | yes      | n/a     | ≥ 0            | n/a         | US dollar | `161815.553` | (Verified) |
| cif_value_usd        | number   | no       | yes      | n/a     | ≥ 0            | n/a         | US dollar | `0` | (Verified) |
| primary_value_usd    | number   | yes      | no       | n/a     | ≥ 0            | n/a         | US dollar | `161815.553` | (Verified) |
| legacy_estimation_flag | integer | no      | yes      | 0       | ≥ 0            | documented | n/a | `0` | (Verified) |
| is_reported          | boolean  | no       | yes      | false   | true, false    | n/a         | n/a | `true`  | (Verified) |
| is_aggregate         | boolean  | no       | yes      | false   | true, false    | n/a         | n/a | `false` | (Verified) |
| provenance           | object   | no       | yes      | n/a     | n/a            | derived     | n/a | see §13 | (Derived) |

## 4.13 E13 TariffLineRecord

Inherits the common fields of E12 (see §4.12) and adds
the fields below.

| Field          | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| -------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| line_id        | string   | yes      | no       | n/a     | non-empty      | upstream-defined | n/a | n/a | (Documented) |

## 4.14 E14 TradeBalanceRecord

Inherits the common fields of E12 (see §4.12) and
adds the fields below. `flow_code` and `flow_name`
are not applicable and are replaced by
`export_value_usd` and `import_value_usd`.

| Field             | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| ----------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| export_value_usd  | number   | yes      | no       | n/a     | ≥ 0            | n/a         | US dollar | n/a | (Documented) |
| import_value_usd  | number   | yes      | no       | n/a     | ≥ 0            | n/a         | US dollar | n/a | (Documented) |
| balance_usd       | number   | yes      | no       | derived | n/a            | computed    | US dollar | n/a | (Computed) |

## 4.15 E15 BilateralRecord

Inherits the common fields of E12 (see §4.12) and
adds the fields below. `primary_value_usd` is replaced
by `reported_value_usd` and `mirror_value_usd`.

| Field              | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| ------------------ | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| reported_value_usd | number   | yes      | no       | n/a     | ≥ 0            | n/a         | US dollar | n/a | (Documented) |
| mirror_value_usd   | number   | yes      | no       | n/a     | ≥ 0            | n/a         | US dollar | n/a | (Documented) |
| asymmetry_usd      | number   | yes      | no       | derived | n/a            | computed    | US dollar | n/a | (Computed) |

## 4.16 E16 StandardUnitValue

| Field                | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| -------------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| commodity_code       | string   | yes      | no       | n/a     | documented     | FK to E04   | n/a | `010391` | (Documented) |
| period               | string   | yes      | no       | n/a     | per frequency_code | format | n/a | `2022` | (Documented) |
| classification_code  | string   | yes      | no       | n/a     | documented     | FK to E02   | n/a | `HS`   | (Documented) |
| edition              | string   | yes      | no       | n/a     | documented     | FK to E03   | n/a | `H6`   | (Documented) |
| flow_code            | string   | no       | yes      | n/a     | documented     | FK to E05   | n/a | `X`     | (Documented) |
| qty_unit_code        | integer  | yes      | no       | n/a     | documented     | FK to E08   | n/a | `8`     | (Documented) |
| unit_value_usd       | number   | yes      | no       | n/a     | ≥ 0            | n/a         | US dollar per unit | n/a | (Documented) |
| lower_bound_usd      | number   | no       | yes      | n/a     | ≥ 0            | n/a         | US dollar per unit | n/a | (Documented) |
| upper_bound_usd      | number   | no       | yes      | n/a     | ≥ 0            | n/a         | US dollar per unit | n/a | (Documented) |

## 4.17 E17 PublicationNote

| Field                | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| -------------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| period               | string   | yes      | no       | n/a     | per frequency_code | format | n/a | `2022` | (Documented) |
| reporter_code        | integer  | yes      | no       | n/a     | documented     | FK to E01   | n/a | `699`   | (Documented) |
| classification_code  | string   | yes      | no       | n/a     | documented     | FK to E02   | n/a | `HS`   | (Documented) |
| edition              | string   | yes      | no       | n/a     | documented     | FK to E03   | n/a | `H6`   | (Documented) |
| note_text            | string   | yes      | no       | n/a     | non-empty      | n/a         | n/a | n/a     | (Documented) |
| published_at         | string   | no       | yes      | n/a     | ISO-8601 date-time | n/a    | n/a | n/a     | (Documented) |

## 4.18 E18 DataAvailabilityRecord

| Field                | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| -------------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| reporter_code        | integer  | yes      | no       | n/a     | documented     | FK to E01   | n/a | `699`   | (Documented) |
| period               | string   | yes      | no       | n/a     | per frequency_code | format | n/a | `2022` | (Documented) |
| classification_code  | string   | yes      | no       | n/a     | documented     | FK to E02   | n/a | `HS`   | (Documented) |
| edition              | string   | yes      | no       | n/a     | documented     | FK to E03   | n/a | `H6`   | (Documented) |
| record_count         | integer  | yes      | no       | n/a     | ≥ 0            | n/a         | n/a | n/a     | (Documented) |
| published_at         | string   | no       | yes      | n/a     | ISO-8601 date-time | n/a    | n/a | n/a     | (Documented) |

## 4.19 E19 AsyncRequestHandle

| Field        | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| ------------ | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| request_id   | string   | yes      | no       | n/a     | non-empty      | UUID format recommended | n/a | n/a | (Documented) |
| submitted_at | string   | no       | yes      | n/a     | ISO-8601 date-time | n/a    | n/a | n/a     | (Documented) |

## 4.20 E20 AsyncRequestStatus

| Field        | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| ------------ | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| request_id   | string   | yes      | no       | n/a     | non-empty      | UUID format recommended | n/a | n/a | (Documented) |
| status       | string   | yes      | no       | n/a     | `Pending`, `Running`, `Completed`, `Failed`, `Expired` | n/a | n/a | `Completed` | (Documented) |
| progress     | number   | no       | yes      | n/a     | 0..1           | n/a         | ratio | `0.5`   | (Documented) |
| message      | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | n/a     | (Documented) |
| completed_at | string   | no       | yes      | n/a     | ISO-8601 date-time | n/a    | n/a | n/a     | (Documented) |

## 4.21 E21 Request

| Field                | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| -------------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| type_code            | string   | yes      | no       | n/a     | `C`, `S`       | n/a         | n/a | `C`     | (Verified) |
| frequency_code       | string   | yes      | no       | n/a     | `A`, `M`       | FK to E09   | n/a | `A`     | (Verified) |
| classification_code  | string   | yes      | no       | n/a     | documented     | FK to E02   | n/a | `HS`   | (Verified) |
| edition              | string   | no       | yes      | n/a     | documented     | FK to E03   | n/a | `H6`   | (Verified) |
| reporter_code        | integer  | yes      | no       | n/a     | documented     | FK to E01   | n/a | `699`   | (Verified) |
| partner_code         | integer  | no       | yes      | n/a     | documented     | FK to E01, special `0` | n/a | `0` | (Verified) |
| partner2_code        | integer  | no       | yes      | n/a     | documented     | FK to E01   | n/a | `156`   | (Verified) |
| flow_code            | string   | no       | yes      | n/a     | documented     | FK to E05   | n/a | `X`     | (Verified) |
| commodity_code       | string   | no       | yes      | n/a     | documented or `TOTAL` | FK to E04 | n/a | `TOTAL` | (Verified) |
| customs_code         | string   | no       | yes      | `C00`   | documented     | FK to E07   | n/a | `C00`   | (Verified) |
| mot_code             | integer  | no       | yes      | 0       | documented     | FK to E06   | n/a | `0`     | (Verified) |
| mos_code             | string   | no       | yes      | `0`     | documented     | FK to E11   | n/a | `0`     | (Verified) |
| period               | string   | yes      | no       | n/a     | per frequency_code | format | n/a | `2022` | (Verified) |
| max_records          | integer  | no       | yes      | n/a     | per endpoint    | ≤ endpoint cap | n/a | `500` | (Verified) |
| breakdown_mode       | string   | no       | yes      | `classic` | `classic`, `plus` | n/a  | n/a | `classic` | (Verified) |
| aggregate_by         | array of string | no | yes    | n/a     | documented     | n/a         | n/a | `["cmdCode"]` | (Documented) |
| include_desc         | boolean  | no       | yes      | true    | true, false    | n/a         | n/a | `true`  | (Verified) |
| count_only           | boolean  | no       | yes      | false   | true, false    | n/a         | n/a | `false` | (Verified) |

## 4.22 E22 Response

| Field           | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| --------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| elapsed_seconds | number   | yes      | no       | n/a     | ≥ 0            | n/a         | second | `0.27`  | (Verified) |
| count           | integer  | yes      | no       | n/a     | ≥ 0            | n/a         | n/a | `1`     | (Verified) |
| records         | array of object | no  | yes      | n/a     | n/a            | n/a         | n/a | `[{...}]` | (Verified) |
| error           | string   | no       | yes      | `""`     | non-empty on failure | n/a    | n/a | `""`    | (Verified) |
| upstream_url    | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | n/a     | (Derived) |
| request         | object   | no       | yes      | n/a     | n/a            | n/a         | n/a | E21     | (Derived) |

## 4.23 E23 ErrorResponse

| Field            | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| ---------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| http_status      | integer  | yes      | no       | n/a     | documented     | n/a         | n/a | `401`   | (Verified) |
| upstream_body    | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | n/a     | (Verified) |
| upstream_message | string   | no       | yes      | n/a     | non-empty      | n/a         | n/a | n/a     | (Verified) |
| category         | string   | yes      | no       | n/a     | documented     | n/a         | n/a | `AuthenticationError` | (Derived) |
| retryable        | boolean  | yes      | no       | derived | true, false    | derived     | n/a | `false` | (Derived) |
| occurred_at      | string   | yes      | no       | n/a     | ISO-8601 date-time | n/a    | n/a | n/a     | (Computed) |

## 4.24 E24 MetadataCollection

| Field            | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| ---------------- | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| collection_type  | string   | yes      | no       | n/a     | documented     | n/a         | n/a | `reporters` | (Verified) |
| records          | array of object | yes | no       | n/a     | n/a            | n/a         | n/a | `[{...}]` | (Verified) |
| fetched_at       | string   | yes      | no       | n/a     | ISO-8601 date-time | n/a    | n/a | n/a     | (Computed) |
| source_url       | string   | yes      | no       | n/a     | non-empty      | n/a         | n/a | n/a     | (Verified) |

## 4.25 E25 Pagination

| Field        | Datatype | Required | Nullable | Default | Allowed Values | Validation | Units | Example | Source |
| ------------ | -------- | -------- | -------- | ------- | -------------- | ---------- | ----- | ------- | ------ |
| (reserved)   | n/a      | n/a      | n/a      | n/a     | n/a            | n/a         | n/a | n/a     | (Reserved) |

---

# 5. Data Types

The data types below are the approved logical data
types for the canonical model. The data types are
implementation-independent; the implementation chooses
the concrete representation.

| Logical type | Usage |
| ------------ | ----- |
| String       | Free-form text, codes, names, notes. Encoded as UTF-8. |
| Integer      | Whole numbers. Encoded as 64-bit signed integers in the implementation. |
| Float        | Approximate numbers. Encoded as IEEE-754 double precision in the implementation. Used only for non-monetary approximate values. Trade values SHALL NOT use Float. |
| Decimal      | Exact numbers, used for ALL trade monetary values (primary_value, cif_value, fob_value, netweight, etc.). Encoded as a fixed-point decimal in the implementation. Required to avoid floating-point precision issues per Architecture Freeze Question Q52. |
| Boolean      | True/false. |
| Date         | Calendar date. Encoded as ISO-8601 (`YYYY-MM-DD`). |
| DateTime     | Calendar date and time. Encoded as ISO-8601 (`YYYY-MM-DDTHH:MM:SSZ`) in UTC. |
| Enum         | A closed set of allowed values, declared in §8. Unknown upstream values are preserved as `UNKNOWN` plus the raw upstream value. |
| Array        | A homogeneous collection of values. |
| Object       | A composite value with named fields. |
| Nullable     | A modifier indicating that the value may be absent. Missing values remain absent; the SDK never invents default values. |
| Reserved     | A placeholder for future use. |

The model uses the following rules:

- Monetary values SHALL be expressed in US dollars.
- Weights SHALL be expressed in kilograms.
- Quantities SHALL be expressed in the unit
  identified by `qty_unit_code` and `qty_unit_abbr`.
- Dates SHALL be encoded as ISO-8601 strings, not
  as native date types. The implementation may cast
  to a native date type at the boundary.
- Date-times SHALL be encoded as ISO-8601 strings in
  UTC.

---

# 6. Nullability Rules

The nullability rules below are the binding rules for
the canonical model. A field declared nullable may be
absent; a field declared non-nullable SHALL be present;
a field declared conditionally nullable may be absent
under documented conditions.

| Field class                       | Nullability | Reason |
| --------------------------------- | ----------- | ------ |
| Primary key                       | non-nullable | The primary key identifies the entity. |
| Natural key (ISO codes)            | nullable    | The upstream may not have an ISO code (e.g. group aggregates). |
| `note` on Country                 | nullable    | The upstream records a note only for selected codes. |
| `entry_expired_date` on Country   | nullable    | The field is present only for expired codes. |
| Description fields                | nullable    | The upstream returns `null` when `includeDesc=false`. |
| `cmdDesc` on TradeRecord          | nullable    | The upstream returns `null` when `includeDesc=false`. |
| Quantity fields                   | nullable    | The upstream may not report a quantity. |
| Weight fields                     | nullable    | The upstream may not report a weight. |
| Value fields (fob, cif)           | nullable    | The upstream records `fobvalue` for exports and `cifvalue` for imports. The other is null. |
| `alt_qty*` fields                 | nullable    | The upstream may not report an alternate quantity. |
| `mot_name`, `customs_name`        | nullable    | Same as description fields. |
| `partner2_*` fields               | nullable    | The secondary partner is optional. |
| `published_at` on E17, E18        | nullable    | The upstream may not expose the publication date. |
| `unit_value_usd` on E16           | non-nullable | The reference value is the entity. |
| `error` on E22                    | nullable    | The field is empty on success. |
| `http_status` on E23              | non-nullable | The HTTP status is the identifier. |
| `records` on E24                  | non-nullable | The collection is the entity. |

---

# 7. Relationships

The relationships below describe the connections
between entities. Every relationship is declared with
its cardinality, its direction, and its constraint.

- E01 Country → E12 TradeRecord (reporter). Cardinality
  one-to-many. Direction: Country is referenced by
  TradeRecord. Constraint: the reporter SHALL exist in
  the catalogue and SHALL NOT be expired.
- E01 Country → E12 TradeRecord (partner). Cardinality
  one-to-many. Direction: Country is referenced by
  TradeRecord. Constraint: the partner SHALL exist in
  the catalogue. The partner MAY be a group aggregate
  (partner_code = 0 for World).
- E02 Classification → E03 ClassificationEdition.
  Cardinality one-to-many. Direction: Classification
  composes ClassificationEdition.
- E03 ClassificationEdition → E04 CommodityCode.
  Cardinality one-to-many. Direction: ClassificationEdition
  composes CommodityCode.
- E03 ClassificationEdition → E12 TradeRecord. Cardinality
  one-to-many. Direction: ClassificationEdition is
  referenced by TradeRecord.
- E04 CommodityCode → E12 TradeRecord. Cardinality
  one-to-many. Direction: CommodityCode is referenced
  by TradeRecord.
- E05 TradeFlow → E12 TradeRecord. Cardinality
  one-to-many. Direction: TradeFlow is referenced by
  TradeRecord.
- E06 TransportMode → E12 TradeRecord. Cardinality
  one-to-many. Direction: TransportMode is referenced
  by TradeRecord.
- E07 CustomsProcedure → E12 TradeRecord. Cardinality
  one-to-many. Direction: CustomsProcedure is referenced
  by TradeRecord.
- E08 QuantityUnit → E12 TradeRecord. Cardinality
  one-to-many. Direction: QuantityUnit is referenced by
  TradeRecord.
- E09 Frequency → E10 Period. Cardinality one-to-many.
  Direction: Frequency defines the format of Period.
- E10 Period → E12 TradeRecord. Cardinality one-to-many.
  Direction: Period is referenced by TradeRecord.
- E11 ModeOfSupply → E12 TradeRecord. Cardinality
  one-to-many. Direction: ModeOfSupply is referenced
  by TradeRecord (services only).
- E12 TradeRecord ↔ E13 TariffLineRecord. Cardinality
  one-to-many. Direction: a TradeRecord may be
  aggregated from TariffLineRecords; a TariffLineRecord
  is aggregated into a TradeRecord. The relationship
  is informational; the canonical model preserves both
  shapes.
- E14 TradeBalanceRecord → E12 TradeRecord (twice).
  Cardinality many-to-many. Direction: a TradeBalance
  references one export and one import.
- E15 BilateralRecord → E12 TradeRecord (twice).
  Cardinality many-to-many. Direction: a Bilateral
  references one reported and one mirror.
- E18 DataAvailabilityRecord → E01 Country.
  Cardinality many-to-one.
- E19 AsyncRequestHandle → E20 AsyncRequestStatus.
  Cardinality one-to-one.
- E22 Response → E12 TradeRecord. Cardinality
  one-to-many. A response composes records.
- E23 ErrorResponse ↔ E22 Response. Cardinality
  one-to-one. An error response replaces a normal
  response.
- E24 MetadataCollection → E01 Country, E02
  Classification, E05 TradeFlow, E06 TransportMode,
  E07 CustomsProcedure, E08 QuantityUnit, E11
  ModeOfSupply. Cardinality one-to-one per kind.

---

# 8. Enumerations

The enumerations below are the closed sets of values
for fields that accept a small, documented set of
values.

## 8.1 TypeCode

- Allowed values: `C`, `S`.
- Meaning: `C` for commodities (goods), `S` for
  services.
- Source: verified by live request.
- Future extensibility: a new value is a breaking
  change.

## 8.2 FrequencyCode

- Allowed values: `A`, `M`.
- Meaning: `A` for annual, `M` for monthly.
- Source: verified by live request.
- Future extensibility: a new value is a breaking
  change.

## 8.3 TradeFlowCode

- Allowed values: `M`, `X`, `RX`, `RM`, plus the
  `plus`-mode derived codes.
- Meaning: `M` for import, `X` for export, `RX` for
  re-export, `RM` for re-import.
- Source: verified by live request.
- Future extensibility: a new value is added in a
  minor version when the upstream publishes it.

## 8.4 BreakdownMode

- Allowed values: `classic`, `plus`.
- Meaning: `classic` for the legacy breakdown,
  `plus` for the extended breakdown.
- Source: verified by live request.
- Future extensibility: a new value is added in a
  minor version.

## 8.5 EstimationCategory

The upstream `legacyEstimationFlag` is an integer.
The canonical model exposes a derived boolean plus the
integer reason. The integer values are documented in
the upstream; the canonical model records the
documented values.

- Allowed values: `0` (no estimation), `1` through `9`
  (estimation categories, documented in the upstream).
- Meaning: the reason an estimate was substituted.
- Source: documented, not verified.
- Future extensibility: a new value is added in a
  minor version.

## 8.6 AsyncStatus

- Allowed values: `Pending`, `Running`, `Completed`,
  `Failed`, `Expired`.
- Meaning: the state of an async request.
- Source: documented.
- Future extensibility: a new value is added in a
  minor version.

## 8.7 ErrorCategory

- Allowed values: `AuthenticationError`, `RateLimitError`,
  `EndpointNotFoundError`, `UpstreamError`, `ValidationError`,
  `ReferenceError`, `TradeError`, `StorageError`,
  `ConfigurationError`.
- Meaning: the SDK-internal category of an error.
- Source: derived from the architecture and the
  endpoint catalog.
- Future extensibility: a new value is added in a
  minor version.

## 8.8 DataType

- Allowed values: `String`, `Integer`, `Float`,
  `Decimal`, `Boolean`, `Date`, `DateTime`, `Enum`,
  `Array`, `Object`.
- Meaning: the logical data type of a field.
- Source: this document.
- Future extensibility: a new value is added in a
  minor version.

---

# 9. Request Models

The canonical request model is the E21 entity. The
model captures every parameter accepted by an SDK
method. The model is transient; it is created at the
boundary and consumed by the call.

## 9.1 Required fields

- `type_code`
- `frequency_code`
- `classification_code`
- `reporter_code`
- `period`

## 9.2 Optional fields

- `edition`
- `partner_code`
- `partner2_code`
- `flow_code`
- `commodity_code`
- `customs_code`
- `mot_code`
- `mos_code`
- `max_records`
- `breakdown_mode`
- `aggregate_by`
- `include_desc`
- `count_only`

## 9.3 Validation

The request SHALL be valid against the rules of the
targeted endpoint. The validation is performed by the
validation layer before the call is issued.

## 9.4 Relationships

The request references the entities of section 2.1
through their primary keys. The request is the bridge
between the consumer and the upstream API.

---

# 10. Response Models

The canonical response model is the E22 entity. The
response is a transient envelope that wraps the
records returned by the SDK call.

## 10.1 Raw API response

The raw API response is the JSON object returned by
the upstream. The object has four top-level keys:
`elapsedTime`, `count`, `data`, `error`.

## 10.2 Canonical SDK response

The canonical SDK response is the E22 entity. The
canonical response renames `elapsedTime` to
`elapsed_seconds`, `data` to `records`, and adds
`upstream_url` and `request` for traceability.

## 10.3 Normalisation expectations

The normalisation layer is responsible for:

- Converting the upstream field names to the canonical
  snake_case field names.
- Converting the upstream `elapsedTime` string to a
  number of seconds.
- Renaming `data` to `records`.
- Converting null descriptions into explicit
  `description_unavailable` flags.
- Preserving the upstream URL on the response for
  traceability.
- Attaching the originating request to the response
  for traceability.

---

# 11. Validation Rules

The validation rules below are the binding rules for
the canonical model. Every field is validated against
the rules declared in section 4. The rules are
enforced by the validation layer.

## 11.1 Required fields

The fields listed below SHALL be present on every
instance of the entity.

- E12 TradeRecord: `type_code`, `frequency_code`,
  `classification_code`, `edition`, `reporter_code`,
  `partner_code`, `flow_code`, `commodity_code`,
  `period`, `primary_value_usd`.
- E22 Response: `elapsed_seconds`, `count`, `records`,
  `error`.
- E23 ErrorResponse: `http_status`, `category`,
  `retryable`, `occurred_at`.

## 11.2 Length limits

- `commodity_code` SHALL be at most 6 digits for HS.
- `iso_alpha2` SHALL be exactly 2 characters.
- `iso_alpha3` SHALL be exactly 3 characters.
- `flow_code` SHALL be at most 2 characters.

## 11.3 Numeric ranges

- `country_code` SHALL be a non-negative integer.
- `period` SHALL be a positive integer in the
  documented range.
- `qty` SHALL be a non-negative number.
- `primary_value_usd` SHALL be a non-negative number.
- `max_records` SHALL be a positive integer.

## 11.4 Allowed formats

- `period` SHALL be `YYYY` for annual data, `YYYYMM`
  for monthly data.
- `iso_alpha2` SHALL match ISO 3166-1 alpha-2.
- `iso_alpha3` SHALL match ISO 3166-1 alpha-3.
- `date` fields SHALL match ISO-8601 (`YYYY-MM-DD`).
- `date-time` fields SHALL match ISO-8601 with `Z`
  suffix for UTC.

## 11.5 Cross-field dependencies

- When `frequency_code='M'`, `period` SHALL be
  `YYYYMM` and `ref_month` SHALL be in 1..12.
- When `frequency_code='A'`, `ref_month` SHALL be 52.
- When `flow_code='X'`, `fob_value_usd` SHALL be
  non-null and `cif_value_usd` SHALL be null.
- When `flow_code='M'`, `cif_value_usd` SHALL be
  non-null and `fob_value_usd` SHALL be null.

## 11.6 Business constraints

- `partner_code=0` (World) SHALL be used only as a
  partner, not as a reporter.
- A country with `entry_expired_date` in the past
  SHALL NOT be used as a reporter.
- `commodity_code='TOTAL'` is allowed only when
  `breakdown_mode='classic'`.

---

# 12. Identity Rules

The identity rules below are the binding rules for
entity identification. Every entity is identified by
its primary key. The primary key is stable for the
lifetime of the entity.

## 12.1 Primary identifiers

- E01 Country: `country_code` (integer).
- E02 Classification: `classification_code` (string).
- E03 ClassificationEdition: `(classification_code,
  edition)`.
- E04 CommodityCode: `(commodity_code,
  classification_code, edition)`.
- E05 TradeFlow: `flow_code` (string).
- E06 TransportMode: `mot_code` (integer).
- E07 CustomsProcedure: `customs_code` (string).
- E08 QuantityUnit: `qty_unit_code` (integer).
- E09 Frequency: `frequency_code` (string).
- E10 Period: `(period, frequency_code)`.
- E11 ModeOfSupply: `mos_code` (string).
- E12 TradeRecord: composite, see §3.12.
- E13 TariffLineRecord: composite, see §3.13.
- E14 TradeBalanceRecord: composite, see §3.14.
- E15 BilateralRecord: composite, see §3.15.
- E16 StandardUnitValue: `(commodity_code, period,
  classification_code, edition)`.
- E17 PublicationNote: `(period, reporter_code,
  classification_code, edition)`.
- E18 DataAvailabilityRecord: `(reporter_code, period,
  classification_code, edition)`.
- E19 AsyncRequestHandle: `request_id`.
- E20 AsyncRequestStatus: `request_id`.
- E21 Request: transient.
- E22 Response: transient.
- E23 ErrorResponse: transient.
- E24 MetadataCollection: `collection_type`.
- E25 Pagination: reserved.

## 12.2 Natural keys

- E01 Country: `(iso_alpha3, validity)` is a natural
  key for the current period; the validity window is
  part of the natural key.
- E05 TradeFlow: `flow_code` is a natural key.
- E09 Frequency: `frequency_code` is a natural key.

## 12.3 Composite keys

- E03, E04, E10, E12, E13, E14, E15, E16, E17, E18 use
  composite keys. The composite key SHALL NOT be
  partial; every component SHALL be non-null.

## 12.4 Stable identifiers

- The country code of an economy is stable across the
  validity window. The code may change when the
  economy is split, merged, or renamed; the old code
  is retired.
- The classification code is stable across editions.
- The HS edition code is stable across the validity
  window.

## 12.5 Generated identifiers

- E19 AsyncRequestHandle: the `request_id` is
  generated by the upstream and is opaque to the SDK.
- E20 AsyncRequestStatus: the `request_id` is the
  same as the handle.

---

# 13. Normalization Rules

The normalisation layer is responsible for converting
the upstream JSON response into the canonical model.
The rules below are the binding rules for the
conversion.

## 13.1 Renaming

- `reporterCode` → `reporter_code`
- `reporterISO` → `reporter_iso3`
- `reporterDesc` → `reporter_name`
- `partnerCode` → `partner_code`
- `partnerISO` → `partner_iso3`
- `partnerDesc` → `partner_name`
- `partner2Code` → `partner2_code`
- `partner2ISO` → `partner2_iso3`
- `partner2Desc` → `partner2_name`
- `flowCode` → `flow_code`
- `flowDesc` → `flow_name`
- `cmdCode` → `commodity_code`
- `cmdDesc` → `commodity_name`
- `classificationCode` → `classification_code`
- `classificationSearchCode` → `classification_search_code`
- `customsCode` → `customs_code`
- `customsDesc` → `customs_name`
- `motCode` → `mot_code`
- `motDesc` → `mot_name`
- `mosCode` → `mos_code`
- `qtyUnitCode` → `qty_unit_code`
- `qtyUnitAbbr` → `qty_unit_abbr`
- `qty` → `qty`
- `isQtyEstimated` → `is_qty_estimated`
- `altQtyUnitCode` → `alt_qty_unit_code`
- `altQtyUnitAbbr` → `alt_qty_unit_abbr`
- `altQty` → `alt_qty`
- `isAltQtyEstimated` → `is_alt_qty_estimated`
- `netWgt` → `net_weight_kg`
- `isNetWgtEstimated` → `is_net_weight_estimated`
- `grossWgt` → `gross_weight_kg`
- `isGrossWgtEstimated` → `is_gross_weight_estimated`
- `cifvalue` → `cif_value_usd`
- `fobvalue` → `fob_value_usd`
- `primaryValue` → `primary_value_usd`
- `legacyEstimationFlag` → `legacy_estimation_flag`
- `isReported` → `is_reported`
- `isAggregate` → `is_aggregate`
- `refPeriodId` → `ref_period_id`
- `refYear` → `ref_year`
- `refMonth` → `ref_month`
- `isOriginalClassification` → `is_original_classification`
- `aggrLevel` → `commodity_level`
- `isLeaf` → `commodity_is_leaf`

## 13.2 Type conversion

- `elapsedTime` (string) → `elapsed_seconds` (number).
  The string is parsed by stripping the unit suffix
  (`" secs"`) and converting the remaining number to
  a float.
- `period` (string) → `period` (string) and `year`
  (integer) and `month` (integer, nullable). The
  conversion depends on `frequency_code`.

## 13.3 Unit normalisation

- All monetary values are normalised to US dollars.
  The upstream does not produce values in other
  currencies, so the conversion is the identity.
- All weights are normalised to kilograms. The
  upstream records weights in kilograms, so the
  conversion is the identity.
- Quantities are preserved in the unit declared by
  the upstream (`qty_unit_code` and `qty_unit_abbr`).

## 13.4 Derived fields

- `commodity_level` is derived from the length of
  `commodity_code`. For HS: length 2 → chapter (level
  2), length 4 → heading (level 4), length 6 →
  subheading (level 6).
- `commodity_is_leaf` is true when the record is the
  most granular level reported.
- `commodity_is_aggregate` is true when the record
  is an aggregate of finer rows.
- `balance_usd` on E14 is computed as
  `export_value_usd - import_value_usd`.
- `asymmetry_usd` on E15 is computed as
  `reported_value_usd - mirror_value_usd`.
- `is_reporter` on E01 is true when
  `entry_expired_date` is null.

## 13.5 Missing values

- A missing field is recorded as null. The consumer
  SHALL NOT infer a value from a missing field.
- A null description is preserved as null. The
  consumer MAY interpret a null description as
  "description unavailable" only when
  `includeDesc=true` was passed to the call.

## 13.6 Unknown values

- An unknown code SHALL be preserved as a string.
  The consumer MAY resolve the code against the
  catalogue after the fact. The canonical model
  does not enforce a referential integrity check at
  normalisation time; the check is performed by the
  validation layer before the call.

---

# 14. Serialization Rules

The canonical model is serialised to the formats
below. The serialisation rules are compatibility
requirements; the implementation chooses the
concrete serialiser.

## 14.1 JSON

- Field names SHALL be serialised in snake_case.
- The encoding SHALL be UTF-8.
- The serialisation SHALL be deterministic: the
  output for a given input SHALL be the same across
  runs.
- Null fields SHALL be serialised as JSON `null`.
- Arrays SHALL be serialised as JSON arrays.
- Dates SHALL be serialised as ISO-8601 strings.
- Date-times SHALL be serialised as ISO-8601 strings
  in UTC.

## 14.2 CSV

- Field names SHALL be serialised in snake_case.
- The header row SHALL list every field of the
  entity in the documented order.
- The encoding SHALL be UTF-8.
- Arrays SHALL be serialised as comma-separated
  values inside the cell.
- Null fields SHALL be serialised as the empty
  string.
- Numbers SHALL be serialised with full precision.

## 14.3 Parquet

- Field names SHALL be serialised in snake_case.
- Strings SHALL be stored as UTF-8.
- Decimals SHALL be stored at sufficient precision to
  represent the value without loss.
- Dates SHALL be stored as ISO-8601 strings or as
  Parquet DATE, at the implementer's choice.
- Date-times SHALL be stored as ISO-8601 strings or
  as Parquet TIMESTAMP, at the implementer's
  choice.

## 14.4 Database records

- A database record SHALL map the canonical fields
  to columns. The mapping is the responsibility of
  the storage layer.
- Monetary values SHALL be stored as DECIMAL, not as
  FLOAT.
- Dates SHALL be stored as DATE.
- Date-times SHALL be stored as TIMESTAMP.

## 14.5 Python objects

- The canonical model maps to a Python object
  through a future implementation task. The mapping
  is not the responsibility of this document.
- The model SHALL NOT be designed to depend on any
  specific Python representation.

---

# 15. Future Extensibility

The model is extended by the rules below. Every
extension is recorded in the changelog and the
decisions log.

## 15.1 New entities

A new entity is added in a minor version. The new
entity SHALL be documented in this document with the
same level of detail as the existing entities. The
new entity SHALL NOT introduce a breaking change to
the existing entities.

## 15.2 New fields

A new field is added in a minor version. The new
field SHALL be nullable by default. The new field
SHALL be documented in the field specification of
the affected entity. The new field SHALL NOT change
the meaning of an existing field.

## 15.3 New values

A new value of an existing enumeration is added in a
minor version when the upstream publishes the value.
The new value SHALL be documented in section 8 of
this document. The new value SHALL NOT change the
meaning of an existing value.

## 15.4 New relationships

A new relationship between existing entities is added
in a minor version. The new relationship SHALL be
documented in section 7 of this document. The new
relationship SHALL NOT change the cardinality of an
existing relationship.

## 15.5 Deprecation

A documented entity, field, value, or relationship
may be marked deprecated by adding a deprecation
note to this document and a deprecation warning to
the SDK. The deprecation period SHALL last at least
one minor release before the element is removed in
the next major release.

---

# 16. Assumptions

The assumptions below are recorded for traceability.
An assumption that turns out to be false is recorded
in `DECISIONS.md` as a correction and is propagated
to the relevant specification documents.

## 16.1 Verified assumptions

The following are verified by the live research
recorded in `004_API_RESEARCH.md`.

- The upstream response has four top-level keys:
  `elapsedTime`, `count`, `data`, `error`. Verified.
- A trade record has 47 fields. Verified.
- The reporter code for India is 699. Verified.
- The historical reporter code 356 is expired on
  1974-12-31. Verified.
- The preview endpoint uses `reportercode` (lowercase).
  Verified.
- The authenticated endpoint uses `reporterCode`
  (camelCase). Verified.
- The preview endpoint is capped at 500 records.
  Verified.
- The authenticated endpoint is capped at 250,000
  records. Verified.
- The 401 response body is structured as
  `{ "statusCode": 401, "message": "..." }`. Verified.
- The 429 response body is empty. Verified.
- The CORS headers are not set. Verified.

## 16.2 Inferred assumptions

The following are inferred from the upstream
documentation but are not verified by live request.

- The `legacyEstimationFlag` integer values are
  documented in the upstream; the canonical mapping
  is preserved.
- The `aggrLevel` semantics is documented in the
  upstream; the canonical mapping is preserved.
- The data availability endpoint URL is documented
  in the official `comtradeapicall` package; the
  canonical path is preserved.
- The async delivery and bulk download endpoint
  URLs are documented in the official
  `comtradeapicall` package; the canonical paths
  are preserved.

## 16.3 Local design decisions

The following are local design decisions made during
the modelling. They are recorded here for
traceability.

- The canonical model unifies reporters and partners
  into a single Country entity, distinguished by a
  derived `is_reporter` flag. The upstream
  separates the two catalogues; the canonical model
  chooses unification for ergonomic reasons.
- The canonical model exposes monetary values in a
  `_usd` suffix field. The upstream records the
  currency implicitly; the canonical model
  documents the currency explicitly.
- The canonical model adds an `is_aggregate` boolean
  in addition to the `legacy_estimation_flag`
  integer. The boolean is derived from the integer
  for the consumer's convenience.
- The canonical model reserves E25 Pagination even
  though the upstream does not support pagination.
  The reservation is for future compatibility.

---

# 17. Open Questions

The questions below are recorded for future
resolution. Each question is described with the
impact and the suggested verification.

- **OQ-DM-001 (High).** What is the canonical mapping
  of the `legacyEstimationFlag` integer values to
  the `EstimationCategory` enumeration? The integer
  values are documented in the upstream but not
  captured in this document. **Impact.** The
  normalisation layer cannot map the value
  without a documented mapping. **Suggested
  verification.** Read the upstream
  `TradeDataItems.json` reference and document the
  mapping.

- **OQ-DM-002 (High).** What is the canonical mapping
  of the `aggrLevel` integer values to a documented
  hierarchy? The integer values are documented but
  not captured. **Impact.** The normalisation layer
  cannot derive `commodity_is_leaf` without a
  documented mapping. **Suggested verification.**
  Cross-reference the HS classification tree.

- **OQ-DM-003 (Medium).** Is the `partner2Code`
  parameter honoured on the public preview, or only
  on the `plus` breakdown? **Impact.** The trade
  layer exposes a parameter that may not have an
  effect on the classic preview. **Suggested
  verification.** Issue a probe with and without
  the parameter.

- **OQ-DM-004 (Medium).** What is the response shape
  of E17 PublicationNote and E18 DataAvailabilityRecord?
  **Impact.** The data model cannot finalise the
  field set without a verified response shape.
  **Suggested verification.** Exercise the
  publication note endpoint and the data
  availability endpoint with a valid key.

- **OQ-DM-005 (Low).** Should the canonical model
  expose `partner_code=0` (World) as a constant or
  as a sentinel string? **Impact.** The consumer
  code that handles the World partner is different
  from the consumer code that handles a regular
  country. **Suggested verification.** Document the
  convention in the SDK specification.

- **OQ-DM-006 (Low).** Should the canonical model
  include a `DataType` field on E12 TradeRecord to
  reflect whether the record is goods or services?
  The upstream records the type via `type_code`;
  the canonical model could also record it via a
  derived boolean. **Impact.** The consumer can
  filter by `type_code` already; the boolean is
  redundant. **Suggested verification.** Confirm
  the consumer ergonomics with the SDK
  specification.

- **OQ-DM-007 (Low).** Should the canonical model
  include a `ValidityWindow` entity to model the
  validity of a country or classification? The
  upstream records the validity on the entity
  itself. **Impact.** A separate entity would
  normalise the validity concept across country
  codes, classification codes, and edition codes.
  **Suggested verification.** Confirm the consumer
  ergonomics with the SDK specification.

- **OQ-DM-008 (Low).** Should the canonical model
  expose the `provenance` block as a first-class
  entity? The current model records `provenance` as
  a derived object on E12. **Impact.** A
  first-class entity would allow the storage layer
  to record provenance in a structured way.
  **Suggested verification.** Confirm with the
  storage specification.

---

# End of document
