```
Document ID
009

Title
Trade Retrieval & Processing Layer Specification

Version
0.1.0

Status
DRAFT

Created
2026-06-26T20:22:04Z

Last Updated
2026-06-26T20:22:04Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
008_METADATA_LAYER_SPEC.md

Supersedes
None
```

---

# 1. Trade Layer Overview

## 1.1 Purpose

The Trade Retrieval & Processing Layer (the trade
layer) is the lower layer of the SDK that is
responsible for every interaction with the trade
datasets of the UN Comtrade database. The trade layer
composes a query, dispatches the query to the upstream
endpoint, validates the response, normalises the
response into the canonical model, paginates the
response when necessary, retries on transient failure,
and returns a `Response` (E22) to the SDK client layer.

The trade layer is the canonical owner of every trade
artefact in the SDK. No other layer duplicates the
trade logic. No other layer performs network I/O
against the trade endpoints.

## 1.2 Responsibilities

The trade layer is responsible for:

- Composing a query from the SDK client request.
- Validating the query against the upstream schema.
- Resolving every code in the query through the
  metadata layer.
- Selecting the appropriate upstream endpoint based
  on the query.
- Dispatching the query to the transport layer.
- Validating the upstream response.
- Normalising the upstream response into the
  canonical model.
- Paginating the response when the result exceeds
  the per-call cap.
- Retrying on transient failure.
- Returning a `Response` to the SDK client layer.
- Caching the response through the storage layer.

## 1.3 Position within architecture

The trade layer is the L4 layer declared in
`003_ARCHITECTURE.md` §4. The layer is owned by the
`un_comtrade.trade` module. The layer is invoked by
the SDK client layer (L2) on every trade retrieval
method. The layer depends on the transport layer (L1)
for network I/O, on the validation layer (L5) for
parameter validation, on the normalisation layer (L6)
for response coercion, on the metadata layer (L3) for
code resolution, on the export layer (L7) for response
packaging, and on the storage layer (L8) for caching.

## 1.4 Relationship to Metadata Layer

The trade layer is the primary consumer of the
metadata layer. The trade layer invokes the metadata
layer to resolve every code that appears in the
request and every code that appears in the response.
The trade layer does not perform code resolution
locally; the metadata layer is the canonical owner of
the resolution.

The trade layer also relies on the metadata layer for
the validation of the request parameters. The
validation layer consults the metadata layer to
verify that a code exists and is current.

## 1.5 Relationship to SDK Client

The trade layer is invoked by the SDK client layer.
The SDK client layer exposes the public methods T01
through T11, F01 through F02, P01 through P04, C01
through C03, A01 through A05, and U01 through U03 of
the SDK specification. The SDK client layer delegates
every call to the trade layer.

The trade layer does not expose its public surface
directly. The SDK client layer is the only entry
point to the trade layer from the consumer.

---

# 2. Supported Trade Datasets

The trade layer supports the datasets below. Each
dataset is documented with its purpose, its source
endpoint, its granularity, its frequency, its typical
usage, and its SDK priority.

## 2.1 Dataset D01 — Annual Final Data

- **Purpose.** Annual aggregate trade data per
  reporter, partner, period, flow, and commodity.
- **Source endpoint.** T1 of
  `005_API_ENDPOINT_CATALOG.md` —
  `GET /data/v1/get/C/A/HS`.
- **Granularity.** Aggregate at the chosen
  classification level.
- **Frequency.** Annual.
- **Typical usage.** Build a yearly dataset of a
  reporter's trade with one or more partners.
- **SDK priority.** Critical.

## 2.2 Dataset D02 — Monthly Final Data

- **Purpose.** Monthly aggregate trade data per
  reporter, partner, period, flow, and commodity.
- **Source endpoint.** T1 of the catalog, with
  `freqCode='M'`.
- **Granularity.** Aggregate at the chosen
  classification level.
- **Frequency.** Monthly.
- **Typical usage.** Build a monthly time series of a
  reporter's trade.
- **SDK priority.** Critical.

## 2.3 Dataset D03 — Annual Tariffline Data

- **Purpose.** Annual line-level trade data per
  reporter, partner, period, flow, and commodity.
- **Source endpoint.** F1 of the catalog —
  `GET /data/v1/getTariffline/C/A/HS`.
- **Granularity.** Line level.
- **Frequency.** Annual.
- **Typical usage.** Line-level analysis, unit value
  computation, outlier detection.
- **SDK priority.** Medium.

## 2.4 Dataset D04 — Monthly Tariffline Data

- **Purpose.** Monthly line-level trade data.
- **Source endpoint.** F1 of the catalog, with
  `freqCode='M'`.
- **Granularity.** Line level.
- **Frequency.** Monthly.
- **Typical usage.** Monthly line-level analysis.
- **SDK priority.** Medium.

## 2.5 Dataset D05 — Trade Matrix

- **Purpose.** Trade matrix data, including the
  harmonised world export matrix with estimates.
- **Source endpoint.** T2 of the catalog —
  `GET /data/v1/getTradeMatrix/C/A/TM`.
- **Granularity.** Aggregate at the chosen
  classification level.
- **Frequency.** Annual.
- **Typical usage.** World export analysis, world
  trade matrix.
- **SDK priority.** Medium.

## 2.6 Dataset D06 — Trade Balance

- **Purpose.** Exports and imports laid out side by
  side for the same query.
- **Source endpoint.** T3 of the catalog —
  `GET /tools/v1/getTradeBalance/C/A/HS`.
- **Granularity.** Aggregate at the chosen
  classification level.
- **Frequency.** Annual or monthly.
- **Typical usage.** Compute the trade balance of a
  reporter in a single call.
- **SDK priority.** Medium.

## 2.7 Dataset D07 — Bilateral Data

- **Purpose.** Reported and mirror values for the
  same query.
- **Source endpoint.** T4 of the catalog —
  `GET /tools/v1/getBilateralData/C/A/HS`.
- **Granularity.** Aggregate at the chosen
  classification level.
- **Frequency.** Annual or monthly.
- **Typical usage.** Reconcile reported values against
  mirror values, detect bilateral asymmetries.
- **SDK priority.** Low.

## 2.8 Dataset D08 — Standard Unit Value

- **Purpose.** Reference Standard Unit Value and
  range data for a commodity.
- **Source endpoint.** U1 of the catalog — the
  URL is documented in the official
  `comtradeapicall` package.
- **Granularity.** Reference value.
- **Frequency.** Annual.
- **Typical usage.** Detect price outliers in a
  trade record.
- **SDK priority.** Low.

## 2.9 Dataset D09 — Public Preview, Annual Final

- **Purpose.** Annual aggregate trade data without a
  subscription key.
- **Source endpoint.** P1 of the catalog —
  `GET /public/v1/preview/C/A/HS`.
- **Granularity.** Aggregate at the chosen
  classification level.
- **Frequency.** Annual.
- **Record cap.** 500.
- **Typical usage.** Ad-hoc queries and demos without
  a key.
- **SDK priority.** High.

## 2.10 Dataset D10 — Public Preview, Monthly Final

- **Purpose.** Monthly aggregate trade data without a
  subscription key.
- **Source endpoint.** P1 of the catalog, with
  `freqCode='M'`.
- **Granularity.** Aggregate at the chosen
  classification level.
- **Frequency.** Monthly.
- **Record cap.** 500.
- **Typical usage.** Ad-hoc monthly queries without a
  key.
- **SDK priority.** High.

## 2.11 Dataset D11 — Public Preview, Annual Tariffline

- **Purpose.** Annual line-level trade data without
  a key.
- **Source endpoint.** P2 of the catalog —
  `GET /public/v1/previewTariffline/C/A/HS`.
- **Granularity.** Line level.
- **Frequency.** Annual.
- **Record cap.** 500.
- **Typical usage.** Ad-hoc line-level queries
  without a key.
- **SDK priority.** Medium.

## 2.12 Dataset D12 — Data Availability

- **Purpose.** Enumerate the data currently
  available.
- **Source endpoint.** D1 of the catalog — the URL
  is unverified.
- **Granularity.** Aggregate count per reporter,
  period, and classification.
- **Frequency.** Per upstream update.
- **Typical usage.** Size a query before issuing it.
- **SDK priority.** Medium.

## 2.13 Dataset D13 — Publication Notes

- **Purpose.** Publication notes and per-release
  metadata.
- **Source endpoint.** U2 of the catalog — the URL
  is documented but not exercised.
- **Granularity.** Per release.
- **Frequency.** Per upstream update.
- **Typical usage.** Capture the publication version
  of a dataset.
- **SDK priority.** Medium.

## 2.14 Summary

| ID    | Dataset                              | Endpoint | Priority |
| ----- | ------------------------------------ | -------- | -------- |
| D01   | Annual Final Data                    | T1       | Critical |
| D02   | Monthly Final Data                   | T1       | Critical |
| D03   | Annual Tariffline Data               | F1       | Medium   |
| D04   | Monthly Tariffline Data              | F1       | Medium   |
| D05   | Trade Matrix                         | T2       | Medium   |
| D06   | Trade Balance                        | T3       | Medium   |
| D07   | Bilateral Data                       | T4       | Low      |
| D08   | Standard Unit Value                  | U1       | Low      |
| D09   | Public Preview, Annual Final         | P1       | High     |
| D10   | Public Preview, Monthly Final        | P1       | High     |
| D11   | Public Preview, Annual Tariffline    | P2       | Medium   |
| D12   | Data Availability                    | D1       | Medium   |
| D13   | Publication Notes                    | U2       | Medium   |

---

# 3. Retrieval Modes

The trade layer supports the retrieval modes below.
A retrieval mode is a high-level workflow that
combines one or more query dimensions and one or
more pagination steps to produce a complete result.

## 3.1 Single Request

- **Purpose.** Issue a single query and return the
  result.
- **Scope.** A single upstream call.
- **Expected behaviour.** The trade layer issues the
  call, validates the response, normalises the
  response, and returns a `Response`.
- **Constraints.** The result is bounded by the
  per-call cap of the dataset.

## 3.2 Batch Retrieval

- **Purpose.** Issue a sequence of related queries
  and aggregate the result.
- **Scope.** Multiple upstream calls.
- **Expected behaviour.** The trade layer issues the
  calls sequentially, validates each response,
  normalises each response, and aggregates the
  results into a single `Response`.
- **Constraints.** The batch is bounded by the
  consumer's configuration. A batch SHALL NOT exceed
  the documented limits (12 periods per call, 250K
  records per call).

## 3.3 Country Download

- **Purpose.** Download every trade record of a
  reporter for a given period.
- **Scope.** Multiple upstream calls, typically
  across periods and partners.
- **Expected behaviour.** The trade layer issues the
  calls in a documented order, aggregates the
  results, and returns a `Response`.
- **Constraints.** The download is bounded by the
  consumer's configuration. A download that exceeds
  the configured maximum SHALL be aborted and a
  `DownloadInterrupted` exception raised.

## 3.4 HS Code Download

- **Purpose.** Download every trade record of an HS
  code across all reporters.
- **Scope.** Multiple upstream calls, one per
  reporter.
- **Expected behaviour.** The trade layer issues the
  calls in a documented order, aggregates the
  results, and returns a `Response`.
- **Constraints.** The download is bounded by the
  configured maximum. A download that exceeds the
  maximum SHALL be aborted.

## 3.5 World Download

- **Purpose.** Download every trade record of a
  reporter with the World aggregate as the partner.
- **Scope.** A single upstream call per period.
- **Expected behaviour.** The trade layer issues the
  call with `partnerCode=0`, validates the response,
  normalises the response, and returns a `Response`.
- **Constraints.** The result is bounded by the
  per-call cap.

## 3.6 Multi-Year Download

- **Purpose.** Download every trade record of a
  reporter across multiple years.
- **Scope.** Multiple upstream calls, one per period
  (up to 12 per call, then a new call).
- **Expected behaviour.** The trade layer issues the
  calls in chronological order, aggregates the
  results, and returns a `Response`.
- **Constraints.** The result is bounded by the
  per-call cap. The trade layer SHALL split the
  download into multiple calls when the per-call cap
  is reached.

## 3.7 Future Incremental Download

- **Purpose.** Download only the records that have
  changed since a given timestamp.
- **Scope.** Multiple upstream calls, filtered by
  publication date.
- **Expected behaviour.** The trade layer filters the
  query by the `publishedDateFrom` parameter and
  returns the changed records.
- **Status.** Reserved for the future. The
  `publishedDateFrom` parameter is documented in the
  catalog (D1) but the endpoint URL is unverified.

---

# 4. Query Strategy

The query strategy declares the query dimensions
supported by the trade layer. Every query is a
combination of dimensions. Every dimension is
validated against the canonical model and against
the upstream schema.

## 4.1 Reporter

- **Validation.** The reporter code SHALL exist in
  the reporters catalogue and SHALL NOT be expired.
- **Composition.** The reporter code is required on
  every query that targets a specific reporter. The
  reporter code may be omitted from a query that
  targets the world aggregate.

## 4.2 Partner

- **Validation.** The partner code SHALL exist in
  the partners catalogue. A partner code of `0`
  selects the World aggregate.
- **Composition.** The partner code is optional. When
  omitted, the upstream returns every partner.

## 4.3 Period

- **Validation.** The period SHALL match the
  frequency format. For annual, `YYYY`. For monthly,
  `YYYYMM`. A list of periods SHALL contain at most
  12 values.
- **Composition.** The period is required. Multiple
  periods are comma-separated.

## 4.4 HS Code

- **Validation.** The HS code SHALL exist in the
  chosen classification edition. The wildcard
  `TOTAL` selects every code.
- **Composition.** The HS code is optional. The
  default is `TOTAL`.

## 4.5 Trade Flow

- **Validation.** The flow code SHALL exist in the
  trade flows catalogue.
- **Composition.** The flow code is required for
  final data. The flow code is not applicable to
  the trade balance dataset.

## 4.6 Classification

- **Validation.** The classification code SHALL be
  one of the documented values.
- **Composition.** The classification code is
  required. The default is `HS`.

## 4.7 Frequency

- **Validation.** The frequency code SHALL be one of
  the documented values (`A` or `M`).
- **Composition.** The frequency code is part of the
  URL path. The frequency code is required.

## 4.8 Edition

- **Validation.** The edition SHALL be one of the
  documented values for the chosen classification.
- **Composition.** The edition is optional. The
  default is the latest published edition.

## 4.9 Partner 2

- **Validation.** The partner2 code SHALL exist in
  the partners catalogue. Only applicable in the
  `plus` breakdown mode.
- **Composition.** The partner2 code is optional.

## 4.10 Customs Procedure

- **Validation.** The customs code SHALL exist in the
  customs catalogue.
- **Composition.** The customs code is optional. The
  default is `C00`.

## 4.11 Mode of Transport

- **Validation.** The mot code SHALL exist in the
  transport catalogue.
- **Composition.** The mot code is optional. The
  default is `0`.

## 4.12 Mode of Supply

- **Validation.** The mos code SHALL exist in the
  supply catalogue. Only applicable to `typeCode='S'`.
- **Composition.** The mos code is optional. The
  default is `0`.

## 4.13 Maximum Records

- **Validation.** The maximum records SHALL be a
  positive integer. The maximum records SHALL NOT
  exceed the per-call cap of the dataset.
- **Composition.** The maximum records is optional.
  The default is the per-call cap.

## 4.14 Breakdown Mode

- **Validation.** The breakdown mode SHALL be one of
  the documented values (`classic` or `plus`).
- **Composition.** The breakdown mode is optional.
  The default is `classic`.

## 4.15 Aggregate By

- **Validation.** The aggregate-by dimension SHALL
  be one of the documented values.
- **Composition.** The aggregate-by dimension is
  optional. Multiple dimensions are accepted as a
  comma-separated list.

## 4.16 Include Description

- **Validation.** The include-description flag SHALL
  be a boolean.
- **Composition.** The include-description flag is
  optional. The default is `true`.

## 4.17 Count Only

- **Validation.** The count-only flag SHALL be a
  boolean.
- **Composition.** The count-only flag is optional.
  The default is `false`.

## 4.18 Query Composition Rules

- The combination of dimensions SHALL be valid
  against the upstream schema.
- The combination of dimensions SHALL be valid
  against the canonical model.
- A query that targets a partner SHALL specify a
  reporter, except for queries that target the
  world aggregate.
- A query that targets a period SHALL specify a
  frequency.
- A query that targets a tariffline dataset SHALL
  NOT specify a `breakdownMode` or a `partner2Code`.

---

# 5. Pagination Strategy

The pagination strategy declares how the trade layer
paginates a result that exceeds the per-call cap of a
dataset. The strategy is the only pagination strategy
supported by the upstream API.

## 5.1 Pagination mechanism

The upstream API does not support a documented
pagination protocol. The pagination strategy is to
split a query into multiple queries, each bounded by
the per-call cap, and to aggregate the responses into
a single `Response`.

The split dimension is the `period` dimension. The
trade layer splits a multi-year query into multiple
single-year queries, each containing at most 12
periods.

## 5.2 Continuation tokens

The upstream API does not expose a continuation
token. The trade layer does not invent a continuation
token.

## 5.3 Maximum records

The maximum records per call is:

- 500 for the public preview datasets (D09, D10,
  D11).
- 250,000 for the authenticated datasets (D01–D08,
  D12, D13).
- 2,500,000 for the async delivery datasets.

The trade layer enforces the maximum records cap on
every call.

## 5.4 Page traversal

The trade layer traverses the pages in chronological
order. For annual data, the pages are traversed by
year. For monthly data, the pages are traversed by
year-month.

## 5.5 Partial page handling

A partial page is a response where the number of
records is less than the per-call cap. A partial
page is the last page of the result.

The trade layer detects the last page by comparing
the actual record count to the per-call cap. A
partial page terminates the pagination.

## 5.6 Completion detection

The trade layer declares the pagination complete
when one of the following conditions is met:

- The last page is partial.
- The consumer-supplied period list is exhausted.
- The consumer cancels the pagination.
- A non-retryable error is encountered.

## 5.7 SDK responsibilities

The SDK is responsible for:

- Setting the maximum records.
- Setting the period list.
- Handling the `Response` returned by the trade
  layer.
- Handling the exceptions raised by the trade
  layer.

The trade layer is responsible for:

- Splitting the query into pages.
- Issuing the pages in order.
- Aggregating the responses into a single
  `Response`.
- Detecting the last page.

## 5.8 Unknown behaviour

The behaviour of the upstream API when a query
returns more than 250,000 records in a single call
is **unverified**. The trade layer assumes that the
upstream truncates the response at the cap and does
not return a pagination indicator.

---

# 6. Batch Processing Strategy

The batch processing strategy declares how the trade
layer processes a batch of related queries.

## 6.1 Batch construction

A batch is constructed from the consumer's request.
The consumer specifies the batch dimensions (e.g. a
list of years, a list of HS codes). The trade layer
constructs the per-page queries from the batch
dimensions.

## 6.2 Sequential vs logical batching

The trade layer executes a batch sequentially. The
upstream API does not support concurrent calls from a
single consumer without rate limiting.

A logical batch is a batch that is constructed
programmatically by the consumer and executed one
query at a time. A logical batch is the only batch
type supported by the trade layer in the MVP.

## 6.3 Failure handling

A failure on a single page is handled by the retry
policy (§9). When the retry budget is exhausted, the
trade layer raises a `TradeError` and aborts the
batch.

A partial success (some pages succeeded, some
failed) is treated as a batch failure. The trade
layer does not return a partial `Response`.

## 6.4 Partial completion

The trade layer SHALL NOT return a partial
`Response`. A batch is either complete or it is
aborted.

## 6.5 Progress reporting

The trade layer reports progress through a
documented callback. The callback is invoked after
each page is processed. The callback receives the
page number, the page count, and the cumulative
record count.

## 6.6 Batch limits

A batch SHALL NOT exceed the documented limits:

- 12 periods per call.
- 250,000 records per call.
- 12 pages per batch in the MVP (a batch that would
  exceed 12 pages is aborted and the consumer is
  asked to reduce the scope).

## 6.7 Batch validation

The trade layer validates the batch dimensions
before the batch is executed. A validation failure
is raised as a `ValidationError`.

---

# 7. Download Strategy

The download strategy declares how the trade layer
downloads large datasets. The strategy is a higher-
level orchestration of the batch processing strategy.

## 7.1 Country Trade Download

- **Purpose.** Download every trade record of a
  reporter for a given period.
- **Workflow.** Iterate over partners and periods.
  For each combination, issue a query and aggregate
  the results.
- **Expected output.** A `Response` (E22) wrapping
  the aggregated `TradeRecord` entities.
- **Failure behaviour.** A failure on any combination
  aborts the download. The trade layer raises a
  `DownloadInterrupted` exception.
- **Completion criteria.** Every combination of
  partner and period has been processed.

## 7.2 World Trade Download

- **Purpose.** Download every trade record of a
  reporter with the World aggregate as the partner.
- **Workflow.** Iterate over periods. For each
  period, issue a query with `partnerCode=0` and
  aggregate the results.
- **Expected output.** A `Response` (E22) wrapping
  the aggregated `TradeRecord` entities.
- **Failure behaviour.** A failure on any period
  aborts the download.
- **Completion criteria.** Every period has been
  processed.

## 7.3 HS Code Dataset Download

- **Purpose.** Download every trade record of an HS
  code across all reporters.
- **Workflow.** Iterate over reporters. For each
  reporter, issue a query for the given HS code and
  aggregate the results.
- **Expected output.** A `Response` (E22) wrapping
  the aggregated `TradeRecord` entities.
- **Failure behaviour.** A failure on any reporter
  aborts the download.
- **Completion criteria.** Every reporter has been
  processed.

## 7.4 Multi-Year Dataset Download

- **Purpose.** Download every trade record of a
  reporter across multiple years.
- **Workflow.** Iterate over years. For each year,
  issue a query and aggregate the results.
- **Expected output.** A `Response` (E22) wrapping
  the aggregated `TradeRecord` entities.
- **Failure behaviour.** A failure on any year aborts
  the download.
- **Completion criteria.** Every year has been
  processed.

## 7.5 Multi-Partner Dataset Download

- **Purpose.** Download every trade record of a
  reporter with a list of partners.
- **Workflow.** Iterate over the partner list. For
  each partner, issue a query and aggregate the
  results.
- **Expected output.** A `Response` (E22) wrapping
  the aggregated `TradeRecord` entities.
- **Failure behaviour.** A failure on any partner
  aborts the download.
- **Completion criteria.** Every partner has been
  processed.

## 7.6 Bulk File Download

- **Purpose.** Download the pre-built bulk files for
  a reporter and a period.
- **Workflow.** Issue a GET to the bulk download
  endpoint. Save the file to the configured
  directory. Optionally decompress the file.
- **Expected output.** A file path.
- **Failure behaviour.** A failure raises a
  `DownloadInterrupted` exception. The partially
  downloaded file is deleted.
- **Completion criteria.** The file is fully
  downloaded and the integrity check passes.

## 7.7 Async Delivery

- **Purpose.** Submit, poll, and download a long-
  running data request.
- **Workflow.** Submit the request to the async
  submit endpoint. Poll the async check endpoint
  until the status is `Completed` or `Failed`.
  Download the result from the async download
  endpoint.
- **Expected output.** A file path.
- **Failure behaviour.** A failure on submit raises
  a `TradeError`. A failure on poll raises a
  `TradeError` and the consumer can retry the poll.
  A failure on download raises a
  `DownloadInterrupted` exception.
- **Completion criteria.** The result is downloaded
  and the integrity check passes.

---

# 8. Validation Strategy

The validation strategy declares the rules that the
trade layer applies to a request and a response.

## 8.1 Parameter validation

The trade layer validates every parameter of the
request against the validation rules declared in
the data model (`006_DATA_MODEL.md` §11) and against
the upstream schema. A failed validation raises a
`ValidationError`.

## 8.2 Response validation

The trade layer validates the response envelope
before processing the records. The envelope SHALL
contain the four documented top-level keys. A missing
top-level key is a `TradeError`. A non-numeric
`count` is a `TradeError`. A non-array `data` is a
`TradeError`.

## 8.3 Trade record validation

The trade layer validates every record against the
canonical model. A record that does not satisfy the
canonical model is dropped from the result. The
trade layer records the dropped records in a
documented `warnings` field of the `Response`.

## 8.4 Duplicate handling

The trade layer validates that the primary key of
every record in the response is unique within the
response. A duplicate primary key is dropped from
the result. The trade layer records the dropped
records in the `warnings` field.

## 8.5 Missing values

The trade layer preserves missing values as `null`
in the canonical record. The trade layer SHALL NOT
infer a default value for a missing value.

## 8.6 Unexpected fields

The trade layer ignores unexpected fields in the
response. The unexpected fields are not propagated
to the canonical record. The trade layer MAY log
the unexpected fields as a warning.

## 8.7 Schema evolution

The trade layer SHALL tolerate schema evolution
within the documented field set. A new field in the
upstream schema is preserved in the canonical
record only if the field is declared in the data
model. A new field that is not declared in the data
model is ignored and MAY be logged as a warning.

A removed field in the upstream schema is preserved
in the canonical record as `null`. The trade layer
does not raise an error on a missing field.

A changed datatype in the upstream schema is
recorded as a `TradeError`. The trade layer does
not coerce a changed datatype.

---

# 9. Retry Strategy

The retry strategy declares the retry behaviour of
the trade layer. The retry strategy is the same as
the retry behaviour declared in
`007_SDK_SPECIFICATION.md` §7.3 and §8.2.

## 9.1 Retryable failures

The trade layer retries on the following failures:

- HTTP 429 (rate limit).
- HTTP 5xx (server errors).
- Network failure.
- DNS failure.
- TLS failure.
- Request timeout.
- Connection reset.

## 9.2 Non-retryable failures

The trade layer does not retry on the following
failures:

- HTTP 400 (bad request).
- HTTP 401 (unauthenticated).
- HTTP 403 (forbidden).
- HTTP 404 (not found).
- HTTP 422 (unprocessable entity).
- Validation error.
- Configuration error.

## 9.3 Timeouts

A request that exceeds the configured timeout is
retried. The default timeout is 60 seconds. The
trade layer exposes a configuration parameter to
override the default.

## 9.4 Server errors

An HTTP 5xx response is retried. The trade layer
records the response status in the retry log.

## 9.5 Rate limiting

An HTTP 429 response is retried. The trade layer
honours the `Retry-After` header if it is present.
When the header is absent, the trade layer uses the
documented backoff schedule.

## 9.6 Network failures

A network failure is retried. The trade layer
records the network error in the retry log.

## 9.7 Maximum retry concepts

The trade layer exposes a configuration parameter
`max_retries` with a default of 5. The parameter is
the maximum number of retry attempts. A retry budget
of 0 disables retries.

## 9.8 Backoff expectations

The backoff schedule is:

- Initial backoff: 1 second.
- Multiplier: 2.
- Cap: 60 seconds.
- Maximum attempts: 5 (configurable).

The backoff is applied to every retry. The first
retry is after 1 second, the second after 2 seconds,
the third after 4 seconds, the fourth after 8
seconds, and the fifth after 16 seconds.

The total maximum wait time across 5 retries is
approximately 31 seconds.

---

# 10. Error Handling

The error handling section declares the expected
behaviour of the trade layer when an error occurs.
The exceptions are the same as the exceptions
declared in `007_SDK_SPECIFICATION.md` §7.

## 10.1 Authentication error

`AuthenticationError` is raised when the subscription
key is missing, invalid, or expired. The trade layer
does not retry an authentication error. The consumer
SHALL provide a valid key.

## 10.2 Invalid parameters

`ValidationError` is raised when a parameter is
malformed. The trade layer does not retry a
validation error. The consumer SHALL provide valid
parameters.

## 10.3 Empty results

A 200 response with `count=0` is not an error. The
trade layer returns a `Response` with `count=0` and
`records=[]`. The empty result is not raised as an
exception.

## 10.4 Pagination failures

A pagination failure raises a `TradeError`. The
trade layer does not return a partial `Response`.

## 10.5 Download interruption

A download interruption raises a
`DownloadInterrupted` exception. The partially
downloaded file is deleted.

## 10.6 Corrupt responses

A corrupt response (a response that fails the
validation rules of section 8) raises a
`TradeError`. The trade layer does not retry a
corrupt response.

## 10.7 Partial responses

A partial response (a response that returns fewer
records than the per-call cap but is not the last
page) raises a `TradeError`. The trade layer does
not retry a partial response; the partial response
is an upstream defect.

## 10.8 Recovery expectations

The trade layer recovers from transient failures
through the retry strategy (§9). The trade layer
recovers from configuration errors only by
re-construction of the SDK. The trade layer
recovers from authentication errors only by
provisioning a new key.

---

# 11. Progress Tracking

The progress tracking section declares the
conceptual progress reporting of the trade layer.

## 11.1 Single request

A single request is a single call. Progress is
reported as 0% before the call, 50% during the call,
and 100% after the call. The progress is reported
through the documented callback.

## 11.2 Batch download

A batch download reports progress after each page.
The progress is the ratio of pages processed to
pages in the batch. The progress is reported through
the documented callback.

## 11.3 Large dataset download

A large dataset download reports progress after each
combination of dimensions. The progress is the ratio
of combinations processed to combinations in the
download.

## 11.4 Resume after interruption

A download interruption is recoverable. The consumer
SHALL record the last successful combination and
SHALL resume the download from the next combination.

## 11.5 Cancellation behaviour

A download cancellation is supported. The consumer
SHALL cancel the download through the documented
callback. The trade layer SHALL abort the download
at the next page boundary.

---

# 12. Performance Considerations

The performance considerations section declares the
expected performance characteristics of the trade
layer.

## 12.1 Large datasets

A large dataset is a dataset that exceeds 250,000
records. The trade layer processes a large dataset
through the batch processing strategy. The total
latency is the sum of the per-page latencies plus
the backoff time.

## 12.2 Memory considerations

The memory consumption of the trade layer is
bounded by the per-call cap. The trade layer does
not load the entire result into memory before
returning; the trade layer returns the result as
the pages are processed.

## 12.3 Network efficiency

The trade layer issues one request at a time. The
upstream API does not support concurrent requests
from a single consumer. The network efficiency is
therefore limited by the upstream rate limit and by
the per-call cap.

## 12.4 Expected response sizes

The expected response sizes are:

- 500 records for the public preview datasets.
- 250,000 records for the authenticated datasets.
- Up to 2,500,000 records for the async delivery.

The trade layer does not bound the response size
beyond the per-call cap.

## 12.5 Download duration

A bulk file download can take from a few seconds to
several minutes, depending on the file size. The
trade layer exposes a progress callback so that the
consumer can monitor the download.

---

# 13. Integration with Metadata Layer

The integration with the metadata layer declares
how the trade layer uses the metadata layer.

## 13.1 Metadata validation before requests

The trade layer invokes the metadata layer to
validate every code in the request. A code that
does not exist in the catalogue raises a
`ReferenceError`. A code that is expired raises a
`ReferenceError`. A code that is a group aggregate
is permitted only as a partner.

## 13.2 Lookup dependencies

The trade layer invokes the metadata layer to
resolve:

- The reporter code (E01) — at request time.
- The partner code (E01) — at request time.
- The partner2 code (E01) — at request time.
- The classification code (E02) — at request time.
- The edition (E03) — at request time.
- The commodity code (E04) — at request time.
- The flow code (E05) — at request time.
- The customs code (E07) — at request time.
- The mot code (E06) — at request time.
- The mos code (E11) — at request time.
- The frequency code (E09) — at request time.
- The quantity unit code (E08) — at response time.

## 13.3 Identifier resolution

The trade layer accepts a code as a string or as an
integer. The trade layer resolves the code through
the metadata layer when the code is a string. The
trade layer uses the code directly when the code is
an integer.

## 13.4 Relationship handling

The trade layer does not maintain a local cache of
the relationships. The trade layer relies on the
metadata layer for every relationship. A change in
the metadata catalogue is reflected in the trade
layer on the next call.

---

# 14. Integration with Public SDK

The integration with the public SDK declares how
the trade layer supports the public methods of the
SDK specification. The methods are described in
detail in `007_SDK_SPECIFICATION.md` §4.

## 14.1 get_exports

`get_exports` is implemented by the trade layer as
a single request against D01 (Annual Final Data)
with `flowCode='X'`.

## 14.2 get_imports

`get_imports` is implemented by the trade layer as
a single request against D01 (Annual Final Data)
with `flowCode='M'`.

## 14.3 get_trade

`get_trade` is implemented by the trade layer as a
single request against D01 or D02, depending on the
frequency. The flow code is the consumer-supplied
flow code.

## 14.4 download_country_trade

`download_country_trade` is implemented by the trade
layer as a Country Trade Download (D01/D02) over
every partner and every period.

## 14.5 download_world_trade

`download_world_trade` is implemented by the trade
layer as a World Trade Download (D01/D02) with
`partnerCode=0`.

## 14.6 get_trade_by_hs

`get_trade_by_hs` is implemented by the trade layer
as a single request against D01 or D02 with the
HS code as the consumer-supplied commodity code.

## 14.7 get_world_trade

`get_world_trade` is implemented by the trade layer
as a single request against D01 or D02 with
`partnerCode=0` and the consumer-supplied
dimensions.

---

# 15. Trade Data Lifecycle

The trade data lifecycle describes the path that a
trade query follows from request to response. The
lifecycle is the same for every dataset.

```
Request
    |
    v
Validation
    |
    v
Retrieval
    |
    v
Response Validation
    |
    v
Normalization
    |
    v
Canonical Trade Records
    |
    v
SDK Response
```

## 15.1 Request

The request is received from the SDK client layer.
The request carries the consumer's parameters and
the configuration.

## 15.2 Validation

The validation is performed by the validation layer.
The validation rules are declared in the data model
(`006_DATA_MODEL.md` §11) and in the SDK
specification (`007_SDK_SPECIFICATION.md` §4).

The validation layer invokes the metadata layer to
resolve every code in the request.

## 15.3 Retrieval

The retrieval is performed by the trade layer. The
trade layer issues the request to the transport
layer, which issues the HTTP call to the upstream
endpoint.

The trade layer paginates the result when the
per-call cap is reached.

## 15.4 Response Validation

The response validation is performed by the trade
layer. The validation rules are declared in section
8 of this document.

## 15.5 Normalization

The normalisation is performed by the normalisation
layer. The normalisation rules are declared in
`006_DATA_MODEL.md` §13.

## 15.6 Canonical Trade Records

The canonical trade records are the output of the
normalisation layer. The records are
`TradeRecord` entities (E12), `TariffLineRecord`
entities (E13), `TradeBalanceRecord` entities
(E14), `BilateralRecord` entities (E15), or
`StandardUnitValue` entities (E16), depending on
the dataset.

## 15.7 SDK Response

The canonical trade records are packaged into a
`Response` (E22) by the export layer. The
`Response` carries the elapsed time, the count,
the records, and the error message.

The `Response` is returned to the SDK client
layer, which returns it to the consumer.

---

# 16. Future Extensibility

The future extensibility section declares how
additional datasets and retrieval modes can be
introduced without breaking the architecture.

## 16.1 Additional datasets

A new dataset is added by adding a new endpoint to
the catalog and a new dispatch in the trade layer.
The new dataset SHALL be documented with the same
level of detail as the existing datasets. The new
dataset is added in a minor version.

## 16.2 Additional retrieval modes

A new retrieval mode is added by adding a new
workflow to the trade layer. The new workflow SHALL
be documented in section 3 of this document. The
new workflow is added in a minor version.

## 16.3 Additional dimensions

A new query dimension is added by adding a new
parameter to the request and a new dispatch in the
trade layer. The new dimension SHALL be documented
in section 4 of this document. The new dimension
is added in a minor version.

## 16.4 New classifications

A new classification is added by adding a new
endpoint to the metadata layer and a new dispatch
in the trade layer. The new classification is
documented in the metadata layer specification.

## 16.5 Deprecation

A deprecated dataset, mode, or dimension is
preserved in the SDK until the deprecation period
expires. The deprecation is recorded in the
changelog and the decisions log.

---

# 17. Assumptions

The assumptions below are recorded for traceability.
An assumption that turns out to be false is
recorded in `DECISIONS.md` as a correction and is
propagated to the relevant specification documents.

## 17.1 Verified assumptions

- The trade data endpoint returns 47 fields per
  record. Verified by live request.
- The reporter code for India is 699. Verified.
- The preview endpoint is capped at 500 records.
  Verified.
- The authenticated endpoint is capped at 250,000
  records. Verified.
- The 401 response body is structured. Verified.
- The CORS headers are not set. Verified.
- The CORS limitation does not affect server-side
  use. Verified.

## 17.2 Inferred assumptions

- The 12-period-per-call limit is a documented
  limitation; the trade layer uses the limit as the
  page boundary.
- The 250,000-record cap is a hard cap; the trade
  layer uses the cap as the per-call boundary.
- The upstream truncates a response that exceeds
  the per-call cap. The trade layer treats a
  truncated response as a successful response and
  paginates by period to avoid truncation.
- The `partner2Code` parameter is honoured on the
  public preview only in the `plus` breakdown mode.
- The `legacyEstimationFlag` integer values are
  documented in the upstream; the trade layer
  preserves the integer.
- The `aggrLevel` semantics is documented in the
  upstream; the trade layer preserves the integer.
- The data availability endpoint URL is documented
  in the official `comtradeapicall` package; the
  trade layer exposes the method.
- The async delivery endpoint URL is documented in
  the official `comtradeapicall` package; the trade
  layer exposes the method.
- The bulk download endpoint URL is documented in
  the official `comtradeapicall` package; the trade
  layer exposes the method.

## 17.3 Local design decisions

- The pagination strategy is split-by-period; the
  trade layer does not invent a continuation token.
- The batch processing is sequential; the trade
  layer does not issue concurrent requests.
- The partial response is treated as an error; the
  trade layer does not return a partial `Response`.
- The retry strategy is shared with the metadata
  layer; the trade layer does not define a
  separate retry policy.
- **The trade layer does NOT maintain a response
  cache.** Trade responses are NOT cached by the
  SDK (per Architecture Freeze Question Q22). The
  metadata layer's catalogue cache remains.
  Optional response caching is reserved for a
  future version.
- The default timeout is 30 seconds; the trade
  layer does not impose a different timeout.
- The default maximum records per call is 250,000
  for the authenticated datasets and 500 for the
  preview datasets; the trade layer does not impose
  a different cap.

---

# 18. Open Questions

The questions below are recorded for future
resolution. Each question is described with the
impact and the suggested verification.

- **OQ-TL-001 (High).** What is the exact
  publication cadence of the trade data? **Impact.**
  The cache lifetime and the refresh strategy
  depend on the cadence. **Suggested verification.**
  Run a monitoring experiment and observe the
  upstream publication cadence.

- **OQ-TL-002 (High).** What is the exact URL of
  the data availability endpoint (D1)? **Impact.**
  The trade layer cannot expose the
  `get_data_availability` method without a URL.
  **Suggested verification.** Probe the official
  `comtradeapicall` source for the canonical URL.

- **OQ-TL-003 (High).** What is the exact URL of
  the bulk download endpoint (D3)? **Impact.** The
  trade layer cannot expose the bulk download
  methods without a URL. **Suggested verification.**
  Probe the official `comtradeapicall` source.

- **OQ-TL-004 (High).** What is the exact URL of
  the async submit, check, and download endpoints
  (D2)? **Impact.** The trade layer cannot expose
  the async methods without URLs. **Suggested
  verification.** Probe the official
  `comtradeapicall` source.

- **OQ-TL-005 (High).** What is the response shape
  of the publication notes endpoint (U2)?
  **Impact.** The trade layer cannot expose the
  `get_publication_notes` method without a
  response shape. **Suggested verification.**
  Exercise the publication notes endpoint with a
  valid key.

- **OQ-TL-006 (Medium).** What is the response shape
  of the SUV endpoint (U1)? **Impact.** The trade
  layer cannot expose the `get_standard_unit_value`
  method without a response shape. **Suggested
  verification.** Exercise the SUV endpoint with a
  valid key.

- **OQ-TL-007 (Medium).** What is the response shape
  of the trade balance endpoint (T3)? **Impact.**
  The trade layer cannot normalise the response
  without a shape. **Suggested verification.**
  Exercise the trade balance endpoint with a valid
  key.

- **OQ-TL-008 (Medium).** What is the response shape
  of the bilateral endpoint (T4)? **Impact.** The
  trade layer cannot normalise the response without
  a shape. **Suggested verification.** Exercise the
  bilateral endpoint with a valid key.

- **OQ-TL-009 (Medium).** Should the trade layer
  support a streaming output for very large
  responses? **Impact.** A streaming output would
  reduce memory consumption. **Suggested
  verification.** Confirm with the consumer
  ergonomics.

- **OQ-TL-010 (Medium).** Should the trade layer
  support a concurrent batch execution under a
  documented concurrency cap? **Impact.**
  Concurrent execution would reduce the total
  download time but would require coordination with
  the rate limit. **Suggested verification.**
  Confirm with the upstream rate-limit policy.

- **OQ-TL-011 (Low).** Should the trade layer
  expose a `cancel()` method to cancel an in-flight
  download? **Impact.** A cancel method would
  improve the consumer experience. **Suggested
  verification.** Confirm with the consumer
  ergonomics.

- **OQ-TL-012 (Low).** Should the trade layer
  expose a `resume(download_handle)` method to
  resume an interrupted download? **Impact.** A
  resume method would improve the consumer
  experience. **Suggested verification.** Confirm
  with the consumer ergonomics.

- **OQ-TL-013 (Low).** Should the trade layer
  expose a `validate_query(...)` method to
  validate a query without issuing it? **Impact.**
  A validation method would support pre-flight
  checks. **Suggested verification.** Confirm with
  the consumer ergonomics.

- **OQ-TL-014 (Low).** Should the trade layer
  expose a `get_trade_diff(reporter_code, since)`
  method to retrieve only the records that have
  changed since a given timestamp? **Impact.** A
  diff method would support change-data-capture
  workflows. **Suggested verification.** Confirm
  with the storage requirements.

- **OQ-TL-015 (Low).** Should the trade layer
  support a `cached=True` flag on every method to
  explicitly opt out of the cache? **Impact.** The
  flag would give the consumer explicit control
  over the cache. **Suggested verification.**
  Confirm with the consumer ergonomics.

---

# End of document
