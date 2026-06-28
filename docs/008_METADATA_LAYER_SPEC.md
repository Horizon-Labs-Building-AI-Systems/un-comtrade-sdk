```
Document ID
008

Title
Metadata Management Layer Specification

Version
0.1.0

Status
DRAFT

Created
2026-06-26T20:18:28Z

Last Updated
2026-06-26T20:18:28Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
007_SDK_SPECIFICATION.md

Supersedes
None
```

---

# 1. Metadata Overview

## 1.1 Purpose

The Metadata Management Layer (the metadata layer) is
the lower layer of the SDK that is responsible for
acquiring, validating, normalising, caching, version-
tracking, persisting, refreshing, and exposing the
reference catalogues of the UN Comtrade database.
Every other layer of the SDK depends on the metadata
layer for the resolution of codes and for the
discovery of the supported surface.

The metadata layer is the canonical owner of every
metadata artefact in the SDK. No other layer
duplicates the metadata. No other layer performs
network I/O against the metadata endpoints.

## 1.2 Importance

The metadata layer is the foundation of every trade
data query. A trade record carries a reporter code,
a partner code, a commodity code, a flow code, a
transport mode code, a customs procedure code, a
quantity unit code, a classification code, and an
edition code. Each of these codes is resolved against
the metadata layer before the call is issued, and is
again resolved after the call to attach the human-
readable descriptions to the normalised record.

The metadata layer is also the foundation of every
diagnostic workflow. A consumer who needs to
understand the meaning of a record consults the
metadata layer first.

## 1.3 Relationship to the SDK

The metadata layer is owned by the `un_comtrade.metadata`
module declared in `003_ARCHITECTURE.md` §9.2. The
layer is invoked by the SDK client layer (§5.2 of
the architecture) on every metadata method and on
every trade method that requires a code resolution.

The metadata layer does not invoke the trade layer.
The metadata layer does not invoke the export layer.
The metadata layer does not invoke the storage layer
to write the response to a cache; the storage layer
is invoked by the metadata layer to persist the
catalogue and the cache, but the metadata layer does
not receive a Response from the storage layer.

## 1.4 Relationship to trade data

The metadata layer is the contract for every code
that appears on a trade record. The metadata layer
is consulted by the validation layer before a trade
query is issued, and by the normalisation layer after
a trade response is received.

The metadata layer is also consulted by the SDK
client layer when the consumer passes a code as a
string that the SDK can resolve (e.g. an ISO-3 code
that the SDK resolves to a numeric code).

---

# 2. Metadata Inventory

The metadata inventory lists every metadata resource
that the metadata layer is responsible for. Each
resource is documented with its purpose, its source
endpoint, its canonical model, its update frequency,
and its SDK importance.

## 2.1 Resource R01 — List of References

- **Purpose.** Enumerate the available reference
  tables.
- **Source endpoint.** M1 of
  `005_API_ENDPOINT_CATALOG.md` —
  `GET /files/v1/app/reference/ListofReferences.json`.
- **Canonical model.** A list of reference metadata
  records (no canonical entity in the data model; the
  list is exposed as an array of strings or as a
  `MetadataCollection` of string records).
- **Update frequency.** Static.
- **SDK importance.** High. The list is used to
  enumerate the catalogue at startup.

## 2.2 Resource R02 — Reporters

- **Purpose.** Enumerate the reporter countries and
  areas.
- **Source endpoint.** M2 —
  `GET /files/v1/app/reference/Reporters.json`.
- **Canonical model.** `Country` entity (E01).
- **Update frequency.** Quarterly to annually. The
  exact cadence is unverified.
- **SDK importance.** High. The reporters catalogue is
  consulted by every trade query and by every
  diagnostic.

## 2.3 Resource R03 — Partners

- **Purpose.** Enumerate the partner countries and
  areas.
- **Source endpoint.** M3 —
  `GET /files/v1/app/reference/partnerAreas.json`.
- **Canonical model.** `Country` entity (E01).
- **Update frequency.** Quarterly to annually.
- **SDK importance.** High.

## 2.4 Resource R04 — HS Combined Classification

- **Purpose.** Enumerate the harmonised system codes
  across every edition.
- **Source endpoint.** M4 —
  `GET /files/v1/app/reference/HS.json`.
- **Canonical model.** `CommodityCode` entity (E04).
- **Update frequency.** With each HS revision (every
  five years approximately).
- **SDK importance.** High. The HS list is consulted
  by every commodity lookup.

## 2.5 Resource R05 — HS Per-Edition Classification

- **Purpose.** Enumerate the harmonised system codes
  for a specific edition.
- **Source endpoint.** M5 —
  `GET /files/v1/app/reference/H{0..6}.json`.
- **Canonical model.** `CommodityCode` entity (E04).
- **Update frequency.** With each HS revision.
- **SDK importance.** High.

## 2.6 Resource R06 — SITC Classification

- **Purpose.** Enumerate the SITC codes.
- **Source endpoint.** M6 —
  `GET /files/v1/app/reference/S{1..4}.json` and
  `/files/v1/app/reference/SS.json`.
- **Canonical model.** `CommodityCode` entity (E04).
- **Update frequency.** With each SITC revision.
- **SDK importance.** Medium.

## 2.7 Resource R07 — BEC Classification

- **Purpose.** Enumerate the BEC codes.
- **Source endpoint.** M7 —
  `GET /files/v1/app/reference/B4.json` and
  `/files/v1/app/reference/B5.json`.
- **Canonical model.** `CommodityCode` entity (E04).
- **Update frequency.** With each BEC revision.
- **SDK importance.** Low.

## 2.8 Resource R08 — EBOPS Classification

- **Purpose.** Enumerate the EBOPS codes.
- **Source endpoint.** M8 —
  `GET /files/v1/app/reference/EB{02,10,10S}.json` and
  `/files/v1/app/reference/EB.json`.
- **Canonical model.** `CommodityCode` entity (E04).
- **Update frequency.** With each EBOPS revision.
- **SDK importance.** Low. Only relevant to
  `type_code='S'`.

## 2.9 Resource R09 — Frequency

- **Purpose.** Enumerate the frequency codes.
- **Source endpoint.** M9 —
  `GET /files/v1/app/reference/Frequency.json`.
- **Canonical model.** `Frequency` entity (E09).
- **Update frequency.** Static.
- **SDK importance.** High. The frequency list is
  consulted by every period validation.

## 2.10 Resource R10 — Trade Flows

- **Purpose.** Enumerate the trade flow codes.
- **Source endpoint.** M10 —
  `GET /files/v1/app/reference/tradeRegimes.json`.
- **Canonical model.** `TradeFlow` entity (E05).
- **Update frequency.** Static.
- **SDK importance.** High. The flow list is
  consulted by every trade query.

## 2.11 Resource R11 — Customs Procedure Codes

- **Purpose.** Enumerate the customs procedure codes.
- **Source endpoint.** M11 —
  `GET /files/v1/app/reference/CustomsCodes.json`.
- **Canonical model.** `CustomsProcedure` entity
  (E07).
- **Update frequency.** Stable.
- **SDK importance.** Medium.

## 2.12 Resource R12 — Modes of Transport

- **Purpose.** Enumerate the mode of transport codes.
- **Source endpoint.** M12 —
  `GET /files/v1/app/reference/ModeOfTransportCodes.json`.
- **Canonical model.** `TransportMode` entity (E06).
- **Update frequency.** Stable.
- **SDK importance.** Medium.

## 2.13 Resource R13 — Modes of Supply

- **Purpose.** Enumerate the mode of supply codes.
- **Source endpoint.** M13 —
  `GET /files/v1/app/reference/ModeOfSupply.json`.
- **Canonical model.** `ModeOfSupply` entity (E11).
- **Update frequency.** Stable.
- **SDK importance.** Low. Only relevant to
  `type_code='S'`.

## 2.14 Resource R14 — Quantity Units

- **Purpose.** Enumerate the quantity unit codes.
- **Source endpoint.** M14 —
  `GET /files/v1/app/reference/QuantityUnits.json`.
- **Canonical model.** `QuantityUnit` entity (E08).
- **Update frequency.** Stable.
- **SDK importance.** Medium. The quantity units
  are consulted by the normalisation layer to attach
  a human-readable abbreviation to a record.

## 2.15 Resource R15 — Data Items

- **Purpose.** Enumerate the data item (column)
  codes.
- **Source endpoint.** M15 —
  `GET /files/v1/app/reference/TradeDataItems.json`.
- **Canonical model.** A `DataItem` record (no
  separate entity in the data model; the records are
  exposed as a `MetadataCollection` of structured
  records).
- **Update frequency.** With each schema change.
- **SDK importance.** High. The data item catalogue
  is the source of truth for the field-level
  documentation.

## 2.16 Resource R16 — Trade Data Availability

- **Purpose.** Enumerate the data currently available.
- **Source endpoint.** D1 of the catalog — the URL
  is **Unverified** at the date of this document.
- **Canonical model.** `DataAvailabilityRecord` (E18).
- **Update frequency.** Per upstream update.
- **SDK importance.** Medium. Used to size a query
  before issuing it.

## 2.17 Resource R17 — Publication Notes

- **Purpose.** Return publication notes and
  per-release metadata.
- **Source endpoint.** U2 of the catalog — the URL
  is **Documented** but not exercised.
- **Canonical model.** `PublicationNote` (E17).
- **Update frequency.** Per upstream update.
- **SDK importance.** Medium. Used to tag stored data
  with its provenance.

## 2.18 Summary

| ID    | Resource                 | Endpoint | Canonical model        | Importance |
| ----- | ------------------------ | -------- | ---------------------- | ---------- |
| R01   | List of References       | M1       | string list            | High       |
| R02   | Reporters                | M2       | E01 Country            | High       |
| R03   | Partners                 | M3       | E01 Country            | High       |
| R04   | HS Combined              | M4       | E04 CommodityCode      | High       |
| R05   | HS Per-Edition           | M5       | E04 CommodityCode      | High       |
| R06   | SITC                     | M6       | E04 CommodityCode      | Medium     |
| R07   | BEC                      | M7       | E04 CommodityCode      | Low        |
| R08   | EBOPS                    | M8       | E04 CommodityCode      | Low        |
| R09   | Frequency                | M9       | E09 Frequency          | High       |
| R10   | Trade Flows              | M10      | E05 TradeFlow          | High       |
| R11   | Customs Procedure Codes  | M11      | E07 CustomsProcedure   | Medium     |
| R12   | Modes of Transport       | M12      | E06 TransportMode      | Medium     |
| R13   | Modes of Supply          | M13      | E11 ModeOfSupply       | Low        |
| R14   | Quantity Units           | M14      | E08 QuantityUnit       | Medium     |
| R15   | Data Items               | M15      | DataItem (collection)  | High       |
| R16   | Data Availability        | D1       | E18 DataAvailabilityRecord | Medium |
| R17   | Publication Notes        | U2       | E17 PublicationNote    | Medium     |

---

# 3. Metadata Lifecycle

The metadata lifecycle describes the path that a
metadata resource follows from discovery to
retirement. The lifecycle is the same for every
resource; the parameters of the lifecycle (refresh
cadence, cache lifetime, etc.) are resource-specific.

```
Discovery
    |
    v
Download
    |
    v
Validation
    |
    v
Normalization
    |
    v
Caching
    |
    v
Persistence
    |
    v
Exposure
    |
    v
Refresh
    |
    v
Retirement
```

## 3.1 Discovery

Discovery is the process by which the metadata layer
identifies the available resources. Discovery uses
the R01 list of references as the canonical source.
A consumer can also discover a resource by passing
its identifier to the metadata layer; the metadata
layer resolves the identifier to a source endpoint.

## 3.2 Download

Download is the process by which the metadata layer
fetches the raw JSON payload from the upstream
endpoint. The download is performed by the transport
layer. The metadata layer does not perform network
I/O directly.

The download may be:

- **Initial.** The first time the resource is
  requested.
- **Incremental.** A subsequent download triggered
  by a refresh.
- **Manual.** Triggered by a consumer request.
- **Automatic.** Triggered by a refresh policy.

The download is skipped when the resource is in the
cache and the cache is fresh.

## 3.3 Validation

Validation is the process by which the metadata
layer verifies that the downloaded payload is well-
formed and consistent with the expected schema. The
validation rules are declared in section 5 of this
document.

A failed validation triggers a recovery strategy
declared in section 12.

## 3.4 Normalization

Normalisation is the process by which the metadata
layer converts the raw JSON payload into the
canonical model. The normalisation rules are declared
in section 6 of this document.

Normalisation produces a `MetadataCollection` (E24)
that contains the canonical records. The collection
is the input to the caching and persistence stages.

## 3.5 Caching

Caching is the process by which the metadata layer
stores the normalised collection in memory for fast
access. The caching rules are declared in section 7
of this document.

The cache is the first line of defence against
upstream latency. The cache lifetime is resource-
specific and is declared in section 7.4.

## 3.6 Persistence

Persistence is the process by which the metadata
layer stores the normalised collection on disk. The
persistence rules are declared in section 8 of this
document.

Persistence enables the cache to survive a process
restart. The persisted collection is the source of
the in-memory cache on startup.

## 3.7 Exposure

Exposure is the process by which the metadata layer
makes the canonical records available to the SDK
client layer. The exposure rules are declared in
section 14 of this document.

The exposure is through the public methods M01–M18
of the SDK specification.

## 3.8 Refresh

Refresh is the process by which the metadata layer
re-downloads a resource when the cache expires or
when the consumer requests a refresh. The refresh
rules are declared in section 10 of this document.

The refresh may be:

- **Manual.** Triggered by a consumer call.
- **Automatic.** Triggered by a scheduled policy.
- **Startup.** Triggered when the SDK starts and the
  cache is empty or expired.

## 3.9 Retirement

Retirement is the process by which the metadata
layer removes a resource from the catalogue. A
retired resource remains in the cache until the
cache lifetime expires, but is not refreshed
automatically. The retired resource is preserved
for historical queries.

A retired resource SHALL NOT be re-introduced
without a major version increment of the metadata
layer.

---

# 4. Download Strategy

The download strategy declares how the metadata layer
fetches a resource from the upstream endpoint.

## 4.1 Initial download

The initial download is performed when the
metadata layer is asked to expose a resource for
the first time in a process. The download fetches
the resource from the upstream endpoint, validates
the response, normalises the response, and populates
the cache.

## 4.2 Incremental updates

The upstream does not expose an incremental
download endpoint. Every download is a full
download. The metadata layer optimises by reusing
the cached collection when the cache is fresh.

## 4.3 Manual refresh

A manual refresh is triggered by a consumer call.
The metadata layer exposes a method to refresh a
resource explicitly. The manual refresh bypasses
the cache freshness check and always re-downloads.

## 4.4 Automatic refresh

An automatic refresh is triggered by a scheduled
policy. The policy is resource-specific. The
metadata layer exposes a configuration parameter
to enable or disable automatic refresh.

## 4.5 Failure recovery

A download failure is handled by the retry policy
declared in `007_SDK_SPECIFICATION.md` §7.3. The
metadata layer retries with exponential backoff up
to the configured maximum. When the retry budget
is exhausted, the metadata layer raises a
`ReferenceError`.

## 4.6 Partial downloads

The upstream endpoint is a single file. A partial
download is detected by a failed integrity check
(declared in section 5.7). A partial download is
treated as a download failure and triggers the
failure recovery strategy.

## 4.7 Concurrent downloads

When two consumers request the same uncached
resource concurrently, the metadata layer SHALL
serialise the download. The second consumer waits
for the first download to complete. The
serialisation prevents two simultaneous downloads
of the same resource.

---

# 5. Validation Strategy

The validation strategy declares the rules that the
metadata layer applies to a downloaded resource
before the resource is normalised.

## 5.1 Required fields

The metadata layer validates that every required
field of the canonical entity is present in the
downloaded payload. A missing required field is a
fatal validation error and triggers the failure
recovery strategy.

The required fields of each entity are declared in
`006_DATA_MODEL.md` §11.1 and in the per-entity
field specification.

## 5.2 Missing fields

A missing optional field is recorded as `null` in
the canonical record. The metadata layer SHALL NOT
infer a default value for a missing optional field.

## 5.3 Duplicate handling

The metadata layer validates that the primary key
of every record in the downloaded payload is
unique. A duplicate primary key is a fatal
validation error and triggers the failure recovery
strategy.

## 5.4 Invalid values

The metadata layer validates that the value of
every field of every record satisfies the validation
rules declared in `006_DATA_MODEL.md` §11. An
invalid value is a fatal validation error.

## 5.5 Unknown values

An unknown value (e.g. a code that is not in the
expected range) is preserved in the canonical
record. The metadata layer SHALL NOT reject the
record on the basis of an unknown value. The
unknown value SHALL be exposed to the consumer
through the canonical record.

## 5.6 Version consistency

The metadata layer validates that the version of
the resource (where the upstream exposes a version)
is consistent with the version that the metadata
layer expected. A version mismatch is a fatal
validation error and triggers a full re-download.

## 5.7 Integrity verification

The metadata layer verifies the integrity of the
downloaded payload by checking the size and the
structure. A failed integrity check is a fatal
validation error.

## 5.8 Cross-record consistency

The metadata layer validates the cross-record
consistency of the downloaded payload. For
example, the metadata layer validates that every
country code referenced by a reference is
defined in the country reference itself.

---

# 6. Normalization Strategy

The normalisation strategy declares the rules that
the metadata layer applies to convert the raw
upstream payload into the canonical model.

## 6.1 Field mapping

The metadata layer maps every upstream field to the
corresponding canonical field. The mapping is
declared in `006_DATA_MODEL.md` §13.1. The mapping
includes the snake_case renaming of every camelCase
field name.

## 6.2 Datatype conversion

The metadata layer converts the upstream datatypes
to the canonical datatypes declared in
`006_DATA_MODEL.md` §4. The conversion includes:

- String trimming.
- Integer parsing.
- Float parsing.
- Boolean parsing (`true`, `false`, `1`, `0`).
- Date parsing (ISO-8601).

A failed conversion is a fatal validation error.

## 6.3 Identifier normalization

The metadata layer normalises identifiers to the
canonical form. The normalisation includes:

- Country code as integer.
- ISO codes as uppercase strings.
- Classification code as uppercase string.
- Edition code as uppercase string.
- Period as `YYYY` or `YYYYMM` depending on
  `frequency_code`.

## 6.4 Naming normalization

The metadata layer normalises human-readable names
to a canonical casing. The casing is title case
for names and lowercase for notes.

## 6.5 Relationship mapping

The metadata layer maps the upstream relationships
to the canonical relationships. The mapping includes
the cardinality of the relationships and the
constraints.

The metadata layer does not enforce referential
integrity at normalisation time. The integrity check
is performed by the validation layer on a per-call
basis.

## 6.6 Derived fields

The metadata layer computes the derived fields
declared in `006_DATA_MODEL.md` §13.4. The derived
fields are computed from the upstream fields and
attached to the canonical record.

## 6.7 MetadataCollection assembly

The metadata layer assembles the normalised records
into a `MetadataCollection` (E24). The collection
carries the `collection_type`, the records, the
fetched-at timestamp, and the source URL.

---

# 7. Caching Strategy

The caching strategy declares how the metadata layer
caches the normalised collection. The cache is the
first line of defence against upstream latency.

## 7.1 Purpose

The purpose of the cache is to reduce the number of
upstream calls, to reduce the latency of metadata
resolution, and to enable the SDK to function when
the upstream is temporarily unavailable.

## 7.2 Cache scope

The cache scope is per-process. Each `ComtradeClient`
instance has its own in-memory cache. The persisted
cache is shared across processes.

## 7.3 Cache ownership

The cache is owned by the metadata layer. No other
layer reads or writes the cache. The trade layer
delegates code resolution to the metadata layer
through the documented interface.

## 7.4 Refresh triggers

The cache is refreshed when:

- The cache lifetime has expired.
- A consumer requests a manual refresh.
- The metadata layer detects a version mismatch.
- The SDK starts and the cache is empty.

The cache lifetime is resource-specific:

- Static resources (R01, R09, R10): 30 days.
- Slow-changing resources (R02, R03, R11, R12,
  R13, R14): 7 days.
- Versioned resources (R04, R05, R06, R07, R08):
  the lifetime is the upstream publication cycle,
  with a minimum of 1 day and a maximum of 30 days.
- Schema resources (R15): the lifetime is the
  upstream schema publication cycle, with a
  minimum of 1 day.
- Operational resources (R16, R17): 1 day.

## 7.5 Expiration policy

The expiration policy is time-based. A cache entry
is considered expired when its age exceeds the
resource-specific lifetime. The age is measured
from the time the entry was first cached.

## 7.6 Invalidation strategy

The cache is invalidated when:

- A consumer requests an explicit invalidation.
- A refresh detects a version mismatch.
- The cache lifetime has expired.

The cache is not invalidated when the upstream is
temporarily unavailable; the cache continues to
serve the consumer until the cache lifetime
expires.

## 7.7 Offline behaviour

When the upstream is unavailable, the cache
continues to serve the consumer. The metadata layer
does not raise an error when the cache is fresh
and the upstream is unavailable. The metadata
layer raises a `ReferenceError` only when the
cache is empty or expired and the upstream is
unavailable.

## 7.8 Memory considerations

The cache SHALL be bounded by the documented
catalogue size. The largest catalogue is R04 (HS
combined) with 8,262 entries. The metadata layer
MAY use a per-resource maximum.

## 7.9 Cache key

The cache key is the resource identifier. The
metadata layer does not key the cache on the
consumer's input; the cache is shared across
consumers within a process.

---

# 8. Persistence Strategy

The persistence strategy declares how the metadata
layer persists the normalised collection on disk.
The persisted collection is the source of the in-
memory cache on startup.

## 8.1 Logical persistence

The metadata layer persists each resource as a
single file. The file format is JSON. The file
encodes the `MetadataCollection` declared in
`006_DATA_MODEL.md` §4.24.

## 8.2 Memory

The in-memory cache is the primary source of the
metadata during a process. The memory is bounded
by the cache size declared in section 7.8.

## 8.3 Local files

The local files are the secondary source of the
metadata. The files are written to the configured
cache directory. The file naming convention is
documented in section 8.7.

## 8.4 Future database support

A future version of the metadata layer MAY support
a database-backed persistence. The database layout
is out of scope of this document.

## 8.5 Cache recovery

The metadata layer recovers the cache on startup
by reading the persisted files. A file that fails
to parse is treated as a cache miss. A file that
fails the integrity check is deleted and treated
as a cache miss.

## 8.6 Version tracking

The metadata layer records the version of each
persisted file. The version is the canonical
version of the resource, derived from the upstream
publication date and the resource's identifier.
A version mismatch between the persisted file and
the upstream triggers a refresh.

## 8.7 File naming convention

The file naming convention is:

```
<cache_directory>/<collection_type>.json
```

For example:

```
~/.un_comtrade/cache/reporters.json
~/.un_comtrade/cache/HS.json
```

The file name is the lowercased `collection_type`
of the resource.

## 8.8 File format

The file format is JSON. The file content is the
serialised `MetadataCollection` (E24). The
serialisation follows the rules of
`006_DATA_MODEL.md` §14.1.

---

# 9. Search Strategy

The search strategy declares how the metadata layer
exposes search capabilities to the SDK client layer.

## 9.1 Country lookup

A country lookup is a search by code. The lookup
returns the `Country` entity that matches the code.
The lookup is exact. The lookup is exposed through
the M02 (`get_country`) and M04 (`get_partner`)
methods of the SDK specification.

## 9.2 Partner lookup

A partner lookup is the same as a country lookup,
against the partner catalogue.

## 9.3 HS code lookup

An HS code lookup is a search by code. The lookup
returns the `CommodityCode` entity that matches the
code in the given edition. The lookup is exact.
The lookup is exposed through the M09
(`get_hs_code`) method of the SDK specification.

## 9.4 Keyword search

A keyword search is a search by text. The search
returns the `CommodityCode` entities whose
description contains the keyword. The match is
case-insensitive and substring-based. The search
is exposed through the M10 (`search_hs`) method of
the SDK specification.

## 9.5 Prefix search

A prefix search is a search by code prefix. The
search returns the `CommodityCode` entities whose
code starts with the prefix. The match is exact
on the prefix. The search is exposed through a
future method (OQ-SDK-005) and is reserved for the
metadata layer.

## 9.6 Identifier search

An identifier search is a search by any identifier
field (code, ISO-2, ISO-3). The search returns the
`Country` entities that match the identifier. The
match is exact. The search is exposed through a
future method (reserved).

## 9.7 Case sensitivity

The case sensitivity of the search is declared per
search type:

- Country lookup: case-insensitive on `iso_alpha2`
  and `iso_alpha3`.
- HS code lookup: case-insensitive on the code
  itself (HS codes are numeric).
- Keyword search: case-insensitive on the
  description.
- Prefix search: case-insensitive on the code.
- Identifier search: case-insensitive on the
  identifier.

## 9.8 Expected behaviour

A search returns zero or more records. A search
that returns zero records is a successful empty
result, not an error. A search that encounters a
cache miss triggers a download and then re-runs
the search against the fresh cache.

---

# 10. Refresh Strategy

The refresh strategy declares when and how the
metadata layer refreshes a cached resource.

## 10.1 Manual refresh

A manual refresh is triggered by a consumer call.
The metadata layer exposes a method to refresh a
resource explicitly. The manual refresh bypasses
the cache freshness check and always re-downloads.

## 10.2 Automatic refresh

An automatic refresh is triggered by a scheduled
policy. The policy is resource-specific. The
metadata layer exposes a configuration parameter
to enable or disable automatic refresh.

## 10.3 Startup refresh

A startup refresh is triggered when the SDK starts.
The startup refresh reads the persisted files and
compares the recorded version with the upstream
version. A version mismatch triggers a download.

## 10.4 Version checks

A version check compares the version of the cached
resource with the version exposed by the upstream.
The version check is performed:

- On every cache miss.
- On every manual refresh.
- On every startup refresh.
- On every automatic refresh.

## 10.5 Refresh failures

A refresh failure is handled by the retry policy
declared in `007_SDK_SPECIFICATION.md` §7.3. The
metadata layer retries with exponential backoff up
to the configured maximum. When the retry budget
is exhausted, the metadata layer continues to
serve the stale cache and raises a `ReferenceError`
only when the consumer explicitly requests a fresh
download.

## 10.6 Rollback expectations

When a refresh fails after a partial success, the
metadata layer rolls back the cache to the previous
state. The roll-back is performed atomically: the
cache is not observed in a partial state.

---

# 11. Versioning Strategy

The versioning strategy declares how the metadata
layer tracks the version of each resource.

## 11.1 Metadata version

The metadata version is the canonical version of
the resource. The version is derived from the
upstream publication date and the resource's
identifier. The version is recorded on the
`MetadataCollection` (E24).

## 11.2 API version

The API version is the version of the UN Comtrade
API. The API version is recorded on the
`ComtradeResponse` (E22). The API version is not
tracked per resource; it is tracked per request.

## 11.3 Compatibility

A metadata resource is backward compatible when
the new version adds new fields, adds new values,
or adds new entities. A metadata resource is not
backward compatible when the new version removes
fields, removes values, removes entities, or
renames identifiers.

## 11.4 Change detection

A change is detected by comparing the cached
version with the upstream version. A difference
in the version is a change. The metadata layer
MAY also detect a change by comparing the SHA-256
of the cached payload with the SHA-256 of the
upstream payload.

## 11.5 Deprecation handling

A deprecated resource is preserved in the cache
until the cache lifetime expires. The metadata
layer does not refresh a deprecated resource
automatically. The metadata layer raises a
deprecation warning when a deprecated resource is
requested.

---

# 12. Error Handling

The error handling section declares the expected
behaviour of the metadata layer when an error
occurs.

## 12.1 Download failures

A download failure is a network error, an
authentication error, or a 5xx response. The
metadata layer retries with the documented
backoff. When the retry budget is exhausted, the
metadata layer raises a `ReferenceError`.

## 12.2 Validation failures

A validation failure is a missing required field,
an invalid value, a duplicate primary key, a
version mismatch, or a failed integrity check. The
metadata layer raises a `ReferenceError`. The
metadata layer does not retry a validation
failure; the consumer SHALL report the failure
to the maintainer.

## 12.3 Missing metadata

A missing metadata record is a `null` value for a
field that the consumer expected to be present.
The metadata layer raises a `ReferenceError` only
when the field is required by the canonical
model. The metadata layer does not raise a
`ReferenceError` when the field is optional.

## 12.4 Corrupt metadata

A corrupt metadata file is a file that fails to
parse or fails the integrity check. The metadata
layer deletes the corrupt file and re-downloads
the resource. The metadata layer raises a
`ReferenceError` when the re-download fails.

## 12.5 Version mismatch

A version mismatch is a difference between the
cached version and the upstream version. The
metadata layer re-downloads the resource. The
metadata layer raises a `ReferenceError` when the
re-download fails.

## 12.6 Partial updates

A partial update is a refresh that fails after
some records have been written. The metadata
layer rolls back the cache to the previous state.
The metadata layer raises a `ReferenceError` only
when the consumer explicitly requests a fresh
download.

---

# 13. Performance Considerations

The performance considerations section declares
the expected performance characteristics of the
metadata layer.

## 13.1 Expected metadata size

The expected sizes of the catalogues are recorded
in `004_API_RESEARCH.md` §3.1 and §10. The largest
catalogue is the combined HS list (8,262 entries).

## 13.2 Memory considerations

The memory consumption of the cache is bounded by
the catalogue size. The metadata layer MAY use a
per-resource maximum.

## 13.3 Startup cost

The startup cost of the metadata layer is the
cost of loading the persisted files. The cost is
bounded by the file size. The metadata layer
loads the files lazily; the first call to a
metadata method triggers the load of the
corresponding file.

## 13.4 Refresh cost

The refresh cost is the cost of re-downloading
and re-parsing the resource. The cost is bounded
by the upstream response size.

## 13.5 Search performance

The search performance is bounded by the catalogue
size. The metadata layer uses an in-memory index
for the search. The index is built on the first
search after a cache load and is invalidated on
cache invalidation.

---

# 14. Public SDK Integration

The public SDK integration section declares how
the metadata layer interacts with the SDK client
layer.

## 14.1 Metadata retrieval

The metadata layer is the implementation of the
M01–M18 methods of the SDK specification. The
metadata layer exposes a `MetadataClient` interface
that the SDK client layer dispatches to.

## 14.2 Metadata search

The metadata layer exposes a search interface
that the M10 method of the SDK specification uses.
The search interface is described in section 9 of
this document.

## 14.3 Trade request validation

The metadata layer is consulted by the validation
layer on every trade request. The validation
layer invokes the metadata layer to resolve every
code that appears in the request. The metadata
layer returns the canonical entity for each code.

## 14.4 Autocomplete

The metadata layer exposes a prefix-search
interface that a future autocomplete method
(OQ-SDK-005) will use. The prefix search is
described in section 9.5 of this document.

## 14.5 Relationship resolution

The metadata layer resolves the relationships
between entities. For example, the metadata layer
resolves the `partner2` of a trade record to the
`Country` entity. The resolution is performed by
the normalisation layer, not by the metadata
layer, but the metadata layer provides the lookup
interface.

---

# 15. Dependencies

The dependencies section declares the allowed and
prohibited dependencies of the metadata layer.

## 15.1 Allowed dependencies

- **Python standard library.** Required for
  dataclass representation, JSON serialisation,
  and file I/O.
- **Transport layer.** Required to issue HTTP
  requests to the upstream.
- **Storage layer.** Required to persist the cache.
- **Validation layer.** Required to validate the
  request parameters.
- **Configuration.** Required to read the cache
  location and the cache lifetime.
- **Logging seam.** Required to log the cache
  events.
- **Errors module.** Required to raise the
  documented exception types.

## 15.2 Prohibited dependencies

- **Trade layer.** The metadata layer SHALL NOT
  invoke the trade layer. The metadata layer
  provides the lookup interface; the trade layer
  invokes the metadata layer.
- **Export layer.** The metadata layer SHALL NOT
  invoke the export layer. The metadata layer
  returns a `MetadataCollection`; the export
  layer packages the result for the consumer.
- **Normalisation layer (for trade).** The
  metadata layer MAY use the normalisation layer
  to convert the upstream payload to the
  canonical model; the metadata layer SHALL NOT
  use the normalisation layer for trade data.
- **Pandas.** The metadata layer SHALL NOT depend
  on pandas. The metadata layer operates on
  collections of records, not on DataFrames.

## 15.3 Cross-layer rules

- The metadata layer MAY be invoked by the
  validation layer.
- The metadata layer MAY be invoked by the
  normalisation layer.
- The metadata layer MAY be invoked by the
  trade layer for code resolution.
- The metadata layer SHALL NOT invoke the trade
  layer.

---

# 16. Future Extensibility

The future extensibility section declares how
additional metadata types may be introduced
without breaking the architecture.

## 16.1 Additional reference tables

A new reference table is added by adding a new
resource to the metadata inventory (§2). The
new resource SHALL be documented with the same
level of detail as the existing resources. The
new resource is added in a minor version.

## 16.2 Additional fields

A new field is added by adding a new field to
the canonical entity. The new field SHALL be
nullable by default. The new field SHALL be
documented in the data model.

## 16.3 Additional classifications

A new classification system is added by adding a
new resource to the metadata inventory and a new
canonical entity to the data model. The new
classification is added in a minor version.

## 16.4 Additional editions

A new edition of an existing classification is
added by adding a new entry to the
`ClassificationEdition` resource. The new edition
is added in a minor version.

## 16.5 Deprecation

A deprecated resource is preserved in the cache
until the cache lifetime expires. The deprecation
is recorded in the changelog and the decisions
log. The deprecation period SHALL last at least
one minor release before the resource is removed.

---

# 17. Assumptions

The assumptions below are recorded for
traceability. An assumption that turns out to be
false is recorded in `DECISIONS.md` as a
correction and is propagated to the relevant
specification documents.

## 17.1 Verified assumptions

- The reference endpoints are public and do not
  require a key. Verified by live request.
- The list of references returns 28 entries.
  Verified.
- The reporters catalogue contains 255 entries.
  Verified.
- The partners catalogue contains 310 entries.
  Verified.
- The HS combined list contains 8,262 entries.
  Verified.
- The HS 2022 (H6) list contains 6,940 entries.
  Verified.
- The HS 2017 (H5) list contains 6,709 entries.
  Verified.
- The frequency list contains 3 entries. Verified.
- The trade flow list contains 10 entries.
  Verified.
- The modes of transport list contains 18 entries.
  Verified.
- The quantity units list contains 41 entries.
  Verified.
- The data items list contains 50 entries.
  Verified.

## 17.2 Inferred assumptions

- The reference catalogues are updated on a
  quarterly cycle. The cadence is documented but
  not verified.
- The HS revisions occur on a five-year cycle. The
  cadence is documented but not verified.
- The metadata cache lifetime of 7 days is a
  reasonable default for slow-changing resources.
  The default is not verified against the
  upstream.
- The metadata cache lifetime of 30 days is a
  reasonable default for static resources. The
  default is not verified against the upstream.
- The data availability endpoint URL is documented
  in the official `comtradeapicall` package. The
  URL is unverified by live request.
- The publication notes endpoint URL is documented
  in the official `comtradeapicall` package. The
  URL is documented but not exercised.

## 17.3 Local design decisions

- The metadata catalogue is loaded lazily on first
  use. The lazy load is a local design decision
  that minimises startup cost.
- The metadata catalogue is cached for a resource-
  specific lifetime. The lifetime is a local
  design decision.
- The metadata catalogue is persisted to the
  configured cache directory as a JSON file. The
  file format is a local design decision.
- The cache key is the resource identifier. The
  cache key is a local design decision.
- The `MetadataCollection` (E24) is the canonical
  handoff shape between the metadata layer and the
  SDK client layer. The handoff shape is a local
  design decision.
- The metadata layer exposes a `MetadataClient`
  interface to the SDK client layer. The
  `MetadataClient` interface is a local design
  decision; the implementation may collapse the
  metadata layer into the SDK client layer if the
  architecture permits it.

---

# 18. Open Questions

The questions below are recorded for future
resolution. Each question is described with the
impact and the suggested verification.

- **OQ-ML-001 (High).** What is the exact cache
  lifetime for each resource? **Impact.** The cache
  lifetime affects the freshness of the metadata
  and the frequency of upstream calls. **Suggested
  verification.** Run a monitoring experiment and
  observe the upstream publication cadence.

- **OQ-ML-002 (High).** What is the exact URL of
  the data availability endpoint (D1)? **Impact.**
  The metadata layer cannot expose the
  `get_data_availability` method without a URL.
  **Suggested verification.** Probe the official
  `comtradeapicall` source for the canonical URL.

- **OQ-ML-003 (Medium).** What is the response shape
  of the publication notes endpoint (U2)?
  **Impact.** The metadata layer cannot expose the
  `get_publication_notes` method without a response
  shape. **Suggested verification.** Exercise the
  publication notes endpoint with a valid key.

- **OQ-ML-004 (Medium).** Should the metadata layer
  expose a `DataItem` entity, or should the data
  items be exposed as a `MetadataCollection` of
  structured records? **Impact.** The data model
  does not currently define a `DataItem` entity.
  **Suggested verification.** Confirm with the
  consumer ergonomics.

- **OQ-ML-005 (Medium).** Should the metadata layer
  pre-load the entire catalogue at startup, or
  load each resource on first use? **Impact.** A
  pre-load is faster on first call but slower at
  startup. A lazy load is slower on first call but
  faster at startup. **Suggested verification.**
  Confirm with the consumer ergonomics.

- **OQ-ML-006 (Medium).** Should the metadata layer
  support a manual invalidation of the entire
  cache, or only per resource? **Impact.** A
  manual invalidation of the entire cache is
  simpler to expose. **Suggested verification.**
  Confirm with the consumer ergonomics.

- **OQ-ML-007 (Low).** Should the metadata layer
  expose a `get_recent_releases()` method that
  returns the recent changes to the catalogue?
  **Impact.** A recent-releases method would
  support change-data-capture workflows.
  **Suggested verification.** Confirm with the
  storage requirements.

- **OQ-ML-008 (Low).** Should the metadata layer
  support a custom cache backend (Redis, SQLite)
  through a documented extension point? **Impact.**
  A custom cache backend would enable shared
  caching across processes. **Suggested
  verification.** Confirm with the storage
  requirements.

- **OQ-ML-009 (Low).** Should the metadata layer
  expose a `validate_metadata()` method that
  validates the cache against the upstream?
  **Impact.** A validation method would support
  diagnostic workflows. **Suggested verification.**
  Confirm with the consumer ergonomics.

- **OQ-ML-010 (Low).** Should the metadata layer
  expose a `get_classification_tree(classification,
  edition)` method that returns the hierarchical
  tree of the classification? **Impact.** A tree
  method would support navigation workflows.
  **Suggested verification.** Confirm with the
  consumer ergonomics.

---

# End of document
