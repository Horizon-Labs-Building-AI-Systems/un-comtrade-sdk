```
Document ID
007

Title
Public SDK Contract Specification

Version
0.1.0

Status
DRAFT

Created
2026-06-26T20:12:59Z

Last Updated
2026-06-26T20:12:59Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
006_DATA_MODEL.md

Supersedes
None
```

---

# 1. SDK Overview

## 1.1 SDK purpose

The UN Comtrade Python SDK is a typed, stable interface
to the United Nations Comtrade Database. The SDK exposes
the upstream API through a documented public surface
that abstracts the wire format, normalises the
response, and provides a consistent error contract.

The SDK is the only supported way to access the UN
Comtrade API from a Python application. Direct calls
to the upstream API from consumer code are out of
scope and are not supported by the SDK.

## 1.2 Intended users

The intended users of the SDK are:

- Data engineers integrating Comtrade data into ETL
  pipelines.
- Quantitative analysts and economists running
  reproducible analysis from Python.
- Application developers embedding Comtrade data into
  larger products.
- Researchers requiring a stable, citable access
  surface.

The SDK is not intended for non-technical end users,
for visual front-ends, or for any consumer who does
not need programmatic access.

## 1.3 Supported workflows

The SDK supports the following workflows out of the
box.

- Load and query the reference catalogue (reporters,
  partners, classifications, flows, transport modes,
  customs procedures, quantity units, modes of supply,
  data items).
- Retrieve annual or monthly trade data for a
  reporter, partner, period, flow, and commodity.
- Retrieve world totals for a reporter.
- Retrieve line-level tariffline data.
- Retrieve exports and imports separately.
- Retrieve trade balance data (exports and imports
  side by side).
- Retrieve bilateral data (reported and mirror).
- Retrieve the trade matrix (world export with
  estimates).
- Search the HS classification by code or by text.
- Count records before downloading them.
- Submit long-running async requests and poll for
  results.
- Download bulk files.

## 1.4 Public interface philosophy

The public interface of the SDK is governed by the
following commitments.

- The public interface is the documented set of
  methods, classes, parameters, return types, and
  exceptions.
- The public interface is stable within a major
  version.
- The public interface is minimal: the smallest set
  of methods that covers the supported workflows.
- The public interface is consistent: the parameter
  set of one method is consistent with the parameter
  set of every other method that shares a domain.
- The public interface is typed: every parameter and
  every return type declares a logical type from the
  data model.

## 1.5 Backward compatibility strategy

The SDK follows Semantic Versioning 2.0.0. The
backward compatibility policy is documented in
section 10.

---

# 2. Client Architecture

## 2.1 Primary entry point

The primary entry point of the SDK is a single class,
`ComtradeClient`. The class is the only object the
consumer instantiates directly. The class holds the
configuration, the authentication, the cache, and the
references to the lower layers of the architecture.

## 2.2 Construction

The constructor of `ComtradeClient` accepts a
configuration object. The configuration object is
immutable after construction.

The constructor does not perform network I/O. The
first network call occurs when the consumer invokes a
method on the client. The constructor MAY load the
cached reference catalogue from disk if caching is
enabled; this is the only I/O performed at
construction.

## 2.3 Configuration

The configuration object is an instance of a typed
class declared in section 8. The configuration object
exposes the documented configuration categories:
authentication, transport, caching, logging,
pagination, rate limiting, and recorded samples.

The configuration is bound at construction. A
configuration value is not mutated after construction
except through documented mutator methods on the
configuration object.

## 2.4 Authentication

The configuration object holds the subscription key.
The key is read from the construction argument, from
an environment variable, or from a configuration file.
The order of precedence is documented in section 8.

A consumer who instantiates a `ComtradeClient` without
a key can still use the public preview methods. A
consumer who instantiates a `ComtradeClient` with a
key can use every method. The methods that require a
key are documented in section 4.

## 2.5 Layer ownership

`ComtradeClient` is the public face of the SDK
client layer declared in `003_ARCHITECTURE.md` §5.2.
The class delegates to the metadata layer and the
trade layer. The lower layers are not exposed to the
consumer.

---

# 3. Public API Inventory

The public API inventory lists every method of the
`ComtradeClient` class. Each method is specified in
section 4. The methods are grouped into the categories
of section 5.

## 3.1 Metadata methods

- M01 `get_countries()`
- M02 `get_country(country_code)`
- M03 `get_partners()`
- M04 `get_partner(partner_code)`
- M05 `get_classifications()`
- M06 `get_classification(classification_code)`
- M07 `get_classification_editions(classification_code)`
- M08 `get_hs_codes(edition=None)`
- M09 `get_hs_code(commodity_code, edition=None)`
- M10 `search_hs(query, edition=None, limit=None)`
- M11 `get_trade_flows()`
- M12 `get_transport_modes()`
- M13 `get_customs_procedures()`
- M14 `get_quantity_units()`
- M15 `get_modes_of_supply()`
- M16 `get_frequencies()`
- M17 `get_data_items()`
- M18 `get_metadata(table_name)`

## 3.2 Trade retrieval methods — annual

- T01 `get_exports(reporter_code, partner_code=None, period, commodity_code=None, classification='HS', edition=None, breakdown_mode='classic', max_records=None)`
- T02 `get_imports(reporter_code, partner_code=None, period, commodity_code=None, classification='HS', edition=None, breakdown_mode='classic', max_records=None)`
- T03 `get_trade(reporter_code, flow_code, partner_code=None, period, commodity_code=None, classification='HS', edition=None, breakdown_mode='classic', max_records=None)`
- T04 `get_trade_by_hs(commodity_code, reporter_code, flow_code, partner_code=None, period, classification='HS', edition=None, breakdown_mode='classic', max_records=None)`
- T05 `get_world_trade(reporter_code, flow_code, period, commodity_code=None, classification='HS', edition=None, breakdown_mode='classic', max_records=None)`
- T06 `get_trade_balance(reporter_code, partner_code=None, period, commodity_code=None, classification='HS', edition=None, breakdown_mode='classic', max_records=None)`
- T07 `get_bilateral(reporter_code, flow_code, partner_code=None, period, commodity_code=None, classification='HS', edition=None, breakdown_mode='classic', max_records=None)`
- T08 `get_trade_matrix(period, flow_code, reporter_code, partner_code, commodity_code, classification=None, max_records=None)`

## 3.3 Trade retrieval methods — monthly

- T09 `get_monthly_exports(reporter_code, partner_code=None, period, commodity_code=None, classification='HS', edition=None, max_records=None)`
- T10 `get_monthly_imports(reporter_code, partner_code=None, period, commodity_code=None, classification='HS', edition=None, max_records=None)`
- T11 `get_monthly_trade(reporter_code, flow_code, partner_code=None, period, commodity_code=None, classification='HS', edition=None, max_records=None)`

## 3.4 Tariffline methods

- F01 `get_tariffline(reporter_code, flow_code, partner_code=None, period, commodity_code=None, classification='HS', edition=None, max_records=None)`
- F02 `get_tariffline_by_hs(commodity_code, reporter_code, flow_code, partner_code=None, period, classification='HS', edition=None, max_records=None)`

## 3.5 Preview methods (no key required)

- P01 `preview_exports(reporter_code, partner_code=None, period, commodity_code=None, classification='HS', edition=None, max_records=None)`
- P02 `preview_imports(reporter_code, partner_code=None, period, commodity_code=None, classification='HS', edition=None, max_records=None)`
- P03 `preview_trade(reporter_code, flow_code, partner_code=None, period, commodity_code=None, classification='HS', edition=None, max_records=None)`
- P04 `preview_tariffline(reporter_code, flow_code, partner_code=None, period, commodity_code=None, classification='HS', edition=None, max_records=None)`

## 3.6 Counting methods

- C01 `count_exports(reporter_code, partner_code=None, period, commodity_code=None, classification='HS', edition=None, breakdown_mode='classic')`
- C02 `count_imports(reporter_code, partner_code=None, period, commodity_code=None, classification='HS', edition=None, breakdown_mode='classic')`
- C03 `count_trade(reporter_code, flow_code, partner_code=None, period, commodity_code=None, classification='HS', edition=None, breakdown_mode='classic')`

## 3.7 Async and bulk methods

- A01 `submit_async_final_data(reporter_code, flow_code, partner_code=None, period, commodity_code=None, classification='HS', edition=None, breakdown_mode='classic')`
- A02 `check_async_request(request_id)`
- A03 `download_async_request(request_id, directory)`
- A04 `bulk_download_final_file(reporter_code, period, classification='HS', edition=None, directory=None, decompress=True)`
- A05 `bulk_download_tariffline_file(reporter_code, period, classification='HS', edition=None, directory=None, decompress=True)`

## 3.8 Utility methods

- U01 `get_data_availability(reporter_code=None, period, classification='HS', edition=None)`
- U02 `get_standard_unit_value(commodity_code, period, classification='HS', edition=None, flow_code=None, qty_unit_code=None)`
- U03 `get_publication_notes(period, reporter_code=None, classification='HS', edition=None, show_history=False)`

---

# 4. Method Specifications

The methods below are specified using the template of
this section. The full template is the contract; the
implementations SHALL conform to it.

---

## M01 — get_countries

### Method Name

`get_countries`

### Purpose

Return the catalogue of reporter countries.

### Description

Returns the list of every economy that has reported
trade data to the UN Comtrade database. The result
includes the current code, the historical code (if
any), the ISO codes, and the validity dates. The
result is cached and re-loaded on a documented
cadence.

### Parameters

| Name           | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| -------------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `include_expired` | boolean | no    | false   | true, false    | n/a        | When `true`, expired codes are included. When `false`, only current codes are included. |

### Return Type

A `MetadataCollection` of `Country` entities, as
defined in the data model. The collection is a
`Collection` of E01 Country entities.

### Behaviour

- The method returns a `MetadataCollection` of
  countries. The collection includes the union of
  current and expired countries when
  `include_expired=true`; only current countries
  otherwise.
- The method MAY serve the result from the cache.
  The cache lifetime is documented in section 8.
- The method is deterministic for a given cache
  state.
- An empty result is not possible: the catalogue is
  guaranteed to be non-empty.

### Exceptions

- `ConfigurationError` — raised when the
  configuration is invalid.
- `ReferenceError` — raised when the upstream
  reference endpoint is unreachable.
- `UpstreamError` — raised when the upstream returns
  a non-recoverable error.

### Side Effects

- Performs network I/O on cache miss.
- Reads cache on cache hit.
- Does not write to the cache for this method (the
  cache is populated by the metadata layer at
  startup).

### Performance Notes

- Typical latency: 0.10 to 0.40 seconds on cache
  miss.
- The method is fast on cache hit.
- The result is large (255 countries). The consumer
  SHALL filter the result after the call rather than
  before.

### Usage Notes

- Use this method to discover the available reporter
  codes.
- Use the `country_code` field as the input to the
  trade retrieval methods.

---

## M02 — get_country

### Method Name

`get_country`

### Purpose

Return a single country by its code.

### Description

Returns the Country entity that matches the given
code. The method is a convenience wrapper over
`get_countries()`.

### Parameters

| Name           | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| -------------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `country_code` | integer  | yes      | n/a     | ≥ 0            | non-negative | The code SHALL exist in the catalogue. |

### Return Type

A single `Country` entity (E01). Raises an exception
when the code is unknown.

### Behaviour

- The method returns a single Country entity.
- A code that is not in the catalogue raises a
  `ReferenceError`.

### Exceptions

- `ReferenceError` — raised when the code is not in
  the catalogue.
- `ValidationError` — raised when the code is
  malformed.

### Side Effects

- Performs network I/O on cache miss.
- Reads cache on cache hit.

### Performance Notes

- Fast on cache hit.
- 0.10 to 0.40 seconds on cache miss.

### Usage Notes

- Use this method to validate a code and to fetch
  the human-readable name.

---

## M03 — get_partners

### Method Name

`get_partners`

### Purpose

Return the catalogue of partner countries and areas.

### Description

Returns the list of every counterparty that can
appear in a trade record as a partner. The list
includes the special partner code `0` (World
aggregate).

### Parameters

| Name           | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| -------------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `include_groups` | boolean | no      | true    | true, false    | n/a        | When `true`, group aggregates are included. When `false`, only individual countries are included. |

### Return Type

A `MetadataCollection` of `Country` entities.

### Behaviour

- As M01, but for partners.

### Exceptions

- As M01.

### Side Effects

- As M01.

### Performance Notes

- Typical latency: 0.10 to 0.40 seconds on cache
  miss.
- 310 entries.

### Usage Notes

- Use this method to discover the available partner
  codes, including the World aggregate.

---

## M04 — get_partner

### Method Name

`get_partner`

### Purpose

Return a single partner by its code.

### Description

As M02, but for partners.

### Parameters

| Name           | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| -------------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `partner_code` | integer  | yes      | n/a     | ≥ 0            | non-negative | Special: `0` is the World aggregate. |

### Return Type

A single `Country` entity (E01).

### Behaviour

- As M02.

### Exceptions

- As M02.

### Side Effects

- As M02.

### Performance Notes

- As M02.

### Usage Notes

- The `partner_code=0` value is the World aggregate
  (see OQ-DM-005 — resolved here: the SDK exposes a
  constant `un_comtrade.PARTNER_WORLD = 0`).

---

## M05 — get_classifications

### Method Name

`get_classifications`

### Purpose

Return the catalogue of classification systems.

### Description

Returns the list of every classification system
supported by the upstream API (HS, SITC, BEC, EBOPS).

### Parameters

None.

### Return Type

A `MetadataCollection` of `Classification` entities
(E02).

### Behaviour

- As M01, but for classifications.

### Exceptions

- As M01.

### Side Effects

- As M01.

### Performance Notes

- As M01.

### Usage Notes

- Use this method to discover the supported
  classification systems.

---

## M06 — get_classification

### Method Name

`get_classification`

### Purpose

Return a single classification by its code.

### Description

As M02, but for classifications.

### Parameters

| Name                 | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| -------------------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `classification_code` | string | yes      | n/a     | non-empty      | n/a        | The code SHALL exist in the catalogue. |

### Return Type

A single `Classification` entity (E02).

### Behaviour

- As M02.

### Exceptions

- As M02.

### Side Effects

- As M02.

### Performance Notes

- As M02.

### Usage Notes

- Use this method to fetch the metadata of a
  specific classification.

---

## M07 — get_classification_editions

### Method Name

`get_classification_editions`

### Purpose

Return the editions of a classification.

### Description

Returns the list of every edition of the given
classification (e.g. HS 1992, HS 1996, ..., HS 2022
for the HS classification).

### Parameters

| Name                  | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| --------------------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `classification_code` | string   | yes      | n/a     | non-empty      | n/a        | The code SHALL exist in the catalogue. |

### Return Type

A `MetadataCollection` of `ClassificationEdition`
entities (E03).

### Behaviour

- As M01, but for editions.

### Exceptions

- As M01.

### Side Effects

- As M01.

### Performance Notes

- As M01.

### Usage Notes

- Use this method to enumerate the available
  editions of a classification.

---

## M08 — get_hs_codes

### Method Name

`get_hs_codes`

### Purpose

Return the HS classification codes for an edition.

### Description

Returns the list of every HS code in the given
edition. The default edition is the latest (HS 2022).

### Parameters

| Name      | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| --------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `edition` | string   | no       | `'H6'`  | `'H0'`..`'H6'`, `'HS'` | n/a | The edition SHALL be one of the documented values. |

### Return Type

A `MetadataCollection` of `CommodityCode` entities
(E04).

### Behaviour

- As M01, but for HS codes.
- The default edition is the latest published.

### Exceptions

- As M01, plus `ValidationError` for an unknown
  edition.

### Side Effects

- As M01.

### Performance Notes

- Typical latency: 0.20 to 0.80 seconds on cache
  miss.
- Up to 8,262 entries for the combined HS list.

### Usage Notes

- The combined HS list is the largest; the
  per-edition list is faster but smaller.

---

## M09 — get_hs_code

### Method Name

`get_hs_code`

### Purpose

Return a single HS code by its code and edition.

### Description

As M02, but for HS codes.

### Parameters

| Name            | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| --------------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `commodity_code` | string | yes      | n/a     | non-empty      | per classification | Length 2, 4, or 6 for HS. |
| `edition`       | string   | no       | `'H6'`  | `'H0'`..`'H6'`, `'HS'` | n/a | n/a |

### Return Type

A single `CommodityCode` entity (E04).

### Behaviour

- As M02.

### Exceptions

- As M02.

### Side Effects

- As M02.

### Performance Notes

- As M02.

### Usage Notes

- Use this method to validate an HS code and to
  fetch its description.

---

## M10 — search_hs

### Method Name

`search_hs`

### Purpose

Search the HS classification for codes matching a
text query.

### Description

Returns the HS codes whose description contains the
given text query. The match is case-insensitive and
substring-based.

### Parameters

| Name      | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| --------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `query`   | string   | yes      | n/a     | non-empty      | non-empty  | The query SHALL be at least 2 characters. |
| `edition` | string   | no       | `'H6'`  | `'H0'`..`'H6'`, `'HS'` | n/a | n/a |
| `limit`   | integer  | no       | 100     | 1..1000        | n/a        | The result SHALL NOT exceed `limit` records. |

### Return Type

A `MetadataCollection` of `CommodityCode` entities
(E04).

### Behaviour

- The method performs a case-insensitive substring
  search on the description field.
- The method is local when the catalogue is cached;
  the cache is loaded once.
- The result is deterministic for a given catalogue
  state.

### Exceptions

- `ValidationError` — raised when the query is too
  short or the edition is unknown.

### Side Effects

- May perform network I/O on cache miss.

### Performance Notes

- Fast on cache hit.
- The catalogue is loaded once and reused.

### Usage Notes

- The result is a `MetadataCollection`; the consumer
  can iterate over the result to find the desired
  code.

---

## M11 — get_trade_flows

### Method Name

`get_trade_flows`

### Purpose

Return the catalogue of trade flow codes.

### Description

As M01, but for trade flows.

### Parameters

None.

### Return Type

A `MetadataCollection` of `TradeFlow` entities
(E05).

### Behaviour

- As M01.

### Exceptions

- As M01.

### Side Effects

- As M01.

### Performance Notes

- As M01.

### Usage Notes

- Use this method to discover the available flow
  codes.

---

## M12 — get_transport_modes

### Method Name

`get_transport_modes`

### Purpose

Return the catalogue of mode of transport codes.

### Description

As M01, but for transport modes.

### Parameters

None.

### Return Type

A `MetadataCollection` of `TransportMode` entities
(E06).

### Behaviour

- As M01.

### Exceptions

- As M01.

### Side Effects

- As M01.

### Performance Notes

- As M01.

### Usage Notes

- Use this method to discover the available
  transport mode codes.

---

## M13 — get_customs_procedures

### Method Name

`get_customs_procedures`

### Purpose

Return the catalogue of customs procedure codes.

### Description

As M01, but for customs procedures.

### Parameters

None.

### Return Type

A `MetadataCollection` of `CustomsProcedure`
entities (E07).

### Behaviour

- As M01.

### Exceptions

- As M01.

### Side Effects

- As M01.

### Performance Notes

- As M01.

### Usage Notes

- Use this method to discover the available
  customs codes.

---

## M14 — get_quantity_units

### Method Name

`get_quantity_units`

### Purpose

Return the catalogue of quantity unit codes.

### Description

As M01, but for quantity units.

### Parameters

None.

### Return Type

A `MetadataCollection` of `QuantityUnit` entities
(E08).

### Behaviour

- As M01.

### Exceptions

- As M01.

### Side Effects

- As M01.

### Performance Notes

- As M01.

### Usage Notes

- Use this method to discover the available
  quantity unit codes.

---

## M15 — get_modes_of_supply

### Method Name

`get_modes_of_supply`

### Purpose

Return the catalogue of mode of supply codes (for
services).

### Description

As M01, but for modes of supply.

### Parameters

None.

### Return Type

A `MetadataCollection` of `ModeOfSupply` entities
(E11).

### Behaviour

- As M01.

### Exceptions

- As M01.

### Side Effects

- As M01.

### Performance Notes

- As M01.

### Usage Notes

- Only relevant to `type_code='S'` (services).

---

## M16 — get_frequencies

### Method Name

`get_frequencies`

### Purpose

Return the catalogue of frequency codes.

### Description

As M01, but for frequencies.

### Parameters

None.

### Return Type

A `MetadataCollection` of `Frequency` entities
(E09).

### Behaviour

- As M01.

### Exceptions

- As M01.

### Side Effects

- As M01.

### Performance Notes

- As M01.

### Usage Notes

- Use this method to discover the available
  frequency codes.

---

## M17 — get_data_items

### Method Name

`get_data_items`

### Purpose

Return the catalogue of data item (column) codes.

### Description

Returns the catalogue of data items used in trade
records. The catalogue is the source of truth for
the field-level documentation.

### Parameters

None.

### Return Type

A `MetadataCollection` of `DataItem` entities.

### Behaviour

- As M01.

### Exceptions

- As M01.

### Side Effects

- As M01.

### Performance Notes

- As M01.

### Usage Notes

- Use this method to drive a data dictionary.

---

## M18 — get_metadata

### Method Name

`get_metadata`

### Purpose

Return a generic metadata collection by table name.

### Description

A generic accessor for any of the reference
catalogues. The method is a thin wrapper over the
specialised accessors M01–M17.

### Parameters

| Name          | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| ------------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `table_name`  | string   | yes      | n/a     | documented     | n/a        | The table SHALL be one of the documented table names. |

### Return Type

A `MetadataCollection` of the corresponding entity.

### Behaviour

- The method dispatches to the specialised accessor
  based on `table_name`.

### Exceptions

- `ValidationError` — raised when the table name is
  unknown.

### Side Effects

- As M01.

### Performance Notes

- As M01.

### Usage Notes

- The method is a convenience for consumers that
  drive the catalogue from a configuration file.

---

## T01 — get_exports

### Method Name

`get_exports`

### Purpose

Return the annual exports of a reporter.

### Description

Returns the annual exports of the given reporter for
the given period, partner, and commodity. The default
classification is HS; the default edition is the
latest.

### Parameters

| Name            | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| --------------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `reporter_code` | integer  | yes      | n/a     | ≥ 0            | non-negative | The code SHALL be a valid current reporter. |
| `partner_code`  | integer  | no       | `None`  | ≥ 0            | non-negative | `0` is the World aggregate. |
| `period`        | string or array | yes | n/a   | `YYYY` or list of `YYYY` | per Frequency | Annual only; comma-separated for multiple years, up to 12. |
| `commodity_code` | string  | no       | `'TOTAL'` | documented or `'TOTAL'` | n/a | `TOTAL` selects every commodity. |
| `classification` | string  | no       | `'HS'`  | documented     | n/a        | n/a |
| `edition`       | string   | no       | `None`  | documented     | n/a        | The default is the latest edition. |
| `breakdown_mode` | string  | no       | `'classic'` | `'classic'`, `'plus'` | n/a | n/a |
| `max_records`   | integer  | no       | `None`  | 1..250000      | ≤ endpoint cap | n/a |

### Return Type

A `Response` (E22) wrapping a collection of
`TradeRecord` entities (E12).

### Behaviour

- The method issues a synchronous call to the
  authenticated final data endpoint.
- The default flow is `X` (export).
- The default period is the current year.
- The default partner is `None` (all partners).
- An empty result returns a `Response` with
  `count=0` and `records=[]`.

### Exceptions

- `AuthenticationError` — raised when the key is
  missing or invalid.
- `ValidationError` — raised when a parameter is
  malformed.
- `RateLimitError` — raised when the consumer has
  exceeded the rate limit. The SDK retries
  automatically with the documented backoff.
- `UpstreamError` — raised when the upstream returns
  a non-recoverable error.

### Side Effects

- Performs network I/O.
- Reads cache on cache hit.
- Writes cache on cache miss.

### Performance Notes

- Typical latency: 0.30 to 3.00 seconds.
- A 250,000-record call may take 5 to 30 seconds.

### Usage Notes

- The default classification is HS; the default
  edition is the latest.
- The result is a collection of `TradeRecord`
  entities; the consumer iterates over the result.

---

## T02 — get_imports

### Method Name

`get_imports`

### Purpose

Return the annual imports of a reporter.

### Description

As T01, but with `flow_code='M'`.

### Parameters

As T01, minus `flow_code` (implied).

### Return Type

A `Response` wrapping a collection of `TradeRecord`
entities.

### Behaviour

- As T01, but with `flow_code='M'`.

### Exceptions

- As T01.

### Side Effects

- As T01.

### Performance Notes

- As T01.

### Usage Notes

- As T01.

---

## T03 — get_trade

### Method Name

`get_trade`

### Purpose

Return the trade data of a reporter for a given flow.

### Description

The general-purpose method for retrieving trade data.
The flow code is required; the other parameters are
optional.

### Parameters

| Name            | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| --------------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `reporter_code` | integer  | yes      | n/a     | ≥ 0            | non-negative | n/a |
| `flow_code`     | string   | yes      | n/a     | documented     | n/a        | n/a |
| `partner_code`  | integer  | no       | `None`  | ≥ 0            | non-negative | n/a |
| `period`        | string or array | yes | n/a   | `YYYY` or list of `YYYY` | per Frequency | n/a |
| `commodity_code` | string  | no       | `'TOTAL'` | documented or `'TOTAL'` | n/a | n/a |
| `classification` | string  | no       | `'HS'`  | documented     | n/a        | n/a |
| `edition`       | string   | no       | `None`  | documented     | n/a        | n/a |
| `breakdown_mode` | string  | no       | `'classic'` | `'classic'`, `'plus'` | n/a | n/a |
| `max_records`   | integer  | no       | `None`  | 1..250000      | ≤ endpoint cap | n/a |

### Return Type

A `Response` wrapping a collection of `TradeRecord`
entities.

### Behaviour

- As T01, with an explicit flow code.

### Exceptions

- As T01, plus `ValidationError` for an unknown flow
  code.

### Side Effects

- As T01.

### Performance Notes

- As T01.

### Usage Notes

- This is the most general trade retrieval method.
  Use the specialised `get_exports` and `get_imports`
  when the flow is known.

---

## T04 — get_trade_by_hs

### Method Name

`get_trade_by_hs`

### Purpose

Return the trade data for a specific HS code.

### Description

The HS code is required; the other parameters are
optional.

### Parameters

| Name             | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| ---------------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `commodity_code` | string   | yes      | n/a     | documented     | per classification | n/a |
| `reporter_code`  | integer  | yes      | n/a     | ≥ 0            | non-negative | n/a |
| `flow_code`      | string   | yes      | n/a     | documented     | n/a        | n/a |
| `partner_code`   | integer  | no       | `None`  | ≥ 0            | non-negative | n/a |
| `period`         | string or array | yes | n/a   | `YYYY` or list of `YYYY` | per Frequency | n/a |
| `classification` | string   | no       | `'HS'`  | documented     | n/a        | n/a |
| `edition`        | string   | no       | `None`  | documented     | n/a        | n/a |
| `breakdown_mode` | string   | no       | `'classic'` | `'classic'`, `'plus'` | n/a | n/a |
| `max_records`    | integer  | no       | `None`  | 1..250000      | ≤ endpoint cap | n/a |

### Return Type

A `Response` wrapping a collection of `TradeRecord`
entities.

### Behaviour

- As T03, with an explicit commodity code.

### Exceptions

- As T03.

### Side Effects

- As T03.

### Performance Notes

- As T03.

### Usage Notes

- Use this method to retrieve the trade of a
  specific commodity.

---

## T05 — get_world_trade

### Method Name

`get_world_trade`

### Purpose

Return the world aggregate trade of a reporter.

### Description

Equivalent to `get_trade` with `partner_code=0`
(World).

### Parameters

| Name            | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| --------------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `reporter_code` | integer  | yes      | n/a     | ≥ 0            | non-negative | n/a |
| `flow_code`     | string   | yes      | n/a     | documented     | n/a        | n/a |
| `period`        | string or array | yes | n/a   | `YYYY` or list of `YYYY` | per Frequency | n/a |
| `commodity_code` | string  | no       | `'TOTAL'` | documented or `'TOTAL'` | n/a | n/a |
| `classification` | string  | no       | `'HS'`  | documented     | n/a        | n/a |
| `edition`       | string   | no       | `None`  | documented     | n/a        | n/a |
| `breakdown_mode` | string  | no       | `'classic'` | `'classic'`, `'plus'` | n/a | n/a |
| `max_records`   | integer  | no       | `None`  | 1..250000      | ≤ endpoint cap | n/a |

### Return Type

A `Response` wrapping a collection of `TradeRecord`
entities.

### Behaviour

- As T03, with `partner_code=0`.

### Exceptions

- As T03.

### Side Effects

- As T03.

### Performance Notes

- As T03.

### Usage Notes

- The result is a single record when
  `commodity_code='TOTAL'`.

---

## T06 — get_trade_balance

### Method Name

`get_trade_balance`

### Purpose

Return the trade balance of a reporter.

### Description

Returns exports and imports side by side for the same
query.

### Parameters

| Name            | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| --------------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `reporter_code` | integer  | yes      | n/a     | ≥ 0            | non-negative | n/a |
| `partner_code`  | integer  | no       | `None`  | ≥ 0            | non-negative | n/a |
| `period`        | string or array | yes | n/a   | `YYYY` or list of `YYYY` | per Frequency | n/a |
| `commodity_code` | string  | no       | `'TOTAL'` | documented or `'TOTAL'` | n/a | n/a |
| `classification` | string  | no       | `'HS'`  | documented     | n/a        | n/a |
| `edition`       | string   | no       | `None`  | documented     | n/a        | n/a |
| `breakdown_mode` | string  | no       | `'classic'` | `'classic'`, `'plus'` | n/a | n/a |
| `max_records`   | integer  | no       | `None`  | 1..250000      | ≤ endpoint cap | n/a |

### Return Type

A `Response` wrapping a collection of
`TradeBalanceRecord` entities (E14).

### Behaviour

- The method issues a call to the trade balance
  endpoint.
- The result is paired exports and imports.

### Exceptions

- As T01.

### Side Effects

- Performs network I/O.
- Reads and writes cache.

### Performance Notes

- As T01.

### Usage Notes

- The `balance_usd` field of the result is computed
  as `export_value_usd - import_value_usd`.

---

## T07 — get_bilateral

### Method Name

`get_bilateral`

### Purpose

Return the bilateral data of a reporter.

### Description

Returns reported and mirror values for the same
query.

### Parameters

| Name            | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| --------------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `reporter_code` | integer  | yes      | n/a     | ≥ 0            | non-negative | n/a |
| `flow_code`     | string   | yes      | n/a     | documented     | n/a        | n/a |
| `partner_code`  | integer  | no       | `None`  | ≥ 0            | non-negative | n/a |
| `period`        | string or array | yes | n/a   | `YYYY` or list of `YYYY` | per Frequency | n/a |
| `commodity_code` | string  | no       | `'TOTAL'` | documented or `'TOTAL'` | n/a | n/a |
| `classification` | string  | no       | `'HS'`  | documented     | n/a        | n/a |
| `edition`       | string   | no       | `None`  | documented     | n/a        | n/a |
| `breakdown_mode` | string  | no       | `'classic'` | `'classic'`, `'plus'` | n/a | n/a |
| `max_records`   | integer  | no       | `None`  | 1..250000      | ≤ endpoint cap | n/a |

### Return Type

A `Response` wrapping a collection of `BilateralRecord`
entities (E15).

### Behaviour

- The method issues a call to the bilateral endpoint.
- The result contains the reported and mirror values.

### Exceptions

- As T01.

### Side Effects

- As T01.

### Performance Notes

- As T01.

### Usage Notes

- The `asymmetry_usd` field of the result is computed
  as `reported_value_usd - mirror_value_usd`.

---

## T08 — get_trade_matrix

### Method Name

`get_trade_matrix`

### Purpose

Return the trade matrix (estimated world export).

### Description

Returns the trade matrix data, including the world
export matrix with estimates.

### Parameters

| Name            | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| --------------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `period`        | string or array | yes | n/a   | `YYYY` | per Frequency | n/a |
| `flow_code`     | string   | yes      | n/a     | documented     | n/a        | n/a |
| `reporter_code` | integer  | yes      | n/a     | ≥ 0            | non-negative | n/a |
| `partner_code`  | integer  | yes      | n/a     | ≥ 0            | non-negative | n/a |
| `commodity_code` | string  | yes      | n/a     | documented     | n/a        | n/a |
| `classification` | string  | no       | `None`  | documented     | n/a        | n/a |
| `max_records`   | integer  | no       | `None`  | 1..250000      | ≤ endpoint cap | n/a |

### Return Type

A `Response` wrapping a collection of `TradeRecord`
entities.

### Behaviour

- The method issues a call to the trade matrix
  endpoint.

### Exceptions

- As T01.

### Side Effects

- As T01.

### Performance Notes

- As T01.

### Usage Notes

- Use this method to retrieve the world export
  matrix with estimates.

---

## T09 — get_monthly_exports

### Method Name

`get_monthly_exports`

### Purpose

Return the monthly exports of a reporter.

### Description

As T01, but for monthly data. The period SHALL be
`YYYYMM` or a list of `YYYYMM` values.

### Parameters

As T01, with `period` constrained to `YYYYMM`.

### Return Type

A `Response` wrapping a collection of `TradeRecord`
entities.

### Behaviour

- As T01, with monthly frequency.

### Exceptions

- As T01.

### Side Effects

- As T01.

### Performance Notes

- As T01.

### Usage Notes

- The period SHALL be `YYYYMM` or a comma-separated
  list of `YYYYMM` values, up to 12.

---

## T10 — get_monthly_imports

### Method Name

`get_monthly_imports`

### Purpose

Return the monthly imports of a reporter.

### Description

As T09, but with `flow_code='M'`.

### Parameters

As T09, minus `flow_code` (implied).

### Return Type

A `Response` wrapping a collection of `TradeRecord`
entities.

### Behaviour

- As T09, with `flow_code='M'`.

### Exceptions

- As T09.

### Side Effects

- As T09.

### Performance Notes

- As T09.

### Usage Notes

- As T09.

---

## T11 — get_monthly_trade

### Method Name

`get_monthly_trade`

### Purpose

Return the monthly trade of a reporter for a given
flow.

### Description

As T03, but for monthly data.

### Parameters

As T03, with `period` constrained to `YYYYMM`.

### Return Type

A `Response` wrapping a collection of `TradeRecord`
entities.

### Behaviour

- As T03, with monthly frequency.

### Exceptions

- As T03.

### Side Effects

- As T03.

### Performance Notes

- As T03.

### Usage Notes

- As T09.

---

## F01 — get_tariffline

### Method Name

`get_tariffline`

### Purpose

Return the line-level tariffline trade of a reporter.

### Description

As T03, but for line-level tariffline data.

### Parameters

As T03, with `breakdown_mode` and `partner2_code`
removed (not applicable to tariffline data).

### Return Type

A `Response` wrapping a collection of
`TariffLineRecord` entities (E13).

### Behaviour

- As T03, but for line-level data.

### Exceptions

- As T03.

### Side Effects

- As T03.

### Performance Notes

- As T03, with longer typical latency.

### Usage Notes

- The result preserves the `line_id` field from the
  upstream.

---

## F02 — get_tariffline_by_hs

### Method Name

`get_tariffline_by_hs`

### Purpose

Return the line-level tariffline trade for a
specific HS code.

### Description

As T04, but for line-level tariffline data.

### Parameters

As T04, with `breakdown_mode` and `partner2_code`
removed.

### Return Type

A `Response` wrapping a collection of
`TariffLineRecord` entities.

### Behaviour

- As T04, but for line-level data.

### Exceptions

- As T04.

### Side Effects

- As T04.

### Performance Notes

- As T04.

### Usage Notes

- As F01.

---

## P01 — preview_exports

### Method Name

`preview_exports`

### Purpose

Return up to 500 annual exports of a reporter
without a key.

### Description

As T01, but using the public preview endpoint.

### Parameters

As T01, with `max_records` capped at 500.

### Return Type

A `Response` wrapping a collection of `TradeRecord`
entities.

### Behaviour

- The method issues a call to the public preview
  endpoint.
- The record cap is 500.
- The method is the only way to retrieve data
  without a key.

### Exceptions

- As T01, except `AuthenticationError` is not raised
  (the endpoint is public).

### Side Effects

- Performs network I/O.
- Reads and writes cache.

### Performance Notes

- Typical latency: 0.10 to 3.00 seconds.
- 500 records is the maximum per call.

### Usage Notes

- Use this method for ad-hoc queries and for
  first-look exploration.

---

## P02 — preview_imports

### Method Name

`preview_imports`

### Purpose

Return up to 500 annual imports of a reporter
without a key.

### Description

As P01, but with `flow_code='M'`.

### Parameters

As P01, minus `flow_code` (implied).

### Return Type

A `Response` wrapping a collection of `TradeRecord`
entities.

### Behaviour

- As P01, with `flow_code='M'`.

### Exceptions

- As P01.

### Side Effects

- As P01.

### Performance Notes

- As P01.

### Usage Notes

- As P01.

---

## P03 — preview_trade

### Method Name

`preview_trade`

### Purpose

Return up to 500 trade records of a reporter without
a key.

### Description

As T03, but using the public preview endpoint.

### Parameters

As T03, with `max_records` capped at 500.

### Return Type

A `Response` wrapping a collection of `TradeRecord`
entities.

### Behaviour

- As P01, with an explicit flow code.

### Exceptions

- As P01.

### Side Effects

- As P01.

### Performance Notes

- As P01.

### Usage Notes

- As P01.

---

## P04 — preview_tariffline

### Method Name

`preview_tariffline`

### Purpose

Return up to 500 tariffline trade records of a
reporter without a key.

### Description

As F01, but using the public preview endpoint.

### Parameters

As F01, with `max_records` capped at 500.

### Return Type

A `Response` wrapping a collection of
`TariffLineRecord` entities.

### Behaviour

- As F01, but using the public preview endpoint.

### Exceptions

- As F01, except `AuthenticationError` is not raised.

### Side Effects

- As F01.

### Performance Notes

- As F01.

### Usage Notes

- As F01.

---

## C01 — count_exports

### Method Name

`count_exports`

### Purpose

Return the number of export records matching a
query.

### Description

The method uses the `countOnly=true` parameter of
the upstream endpoint to return only the count.

### Parameters

As T01, except `max_records` is not applicable.

### Return Type

An integer count.

### Behaviour

- The method issues a call to the authenticated
  final data endpoint with `countOnly=true`.

### Exceptions

- As T01.

### Side Effects

- Performs network I/O.
- Reads and writes cache (the count is cached
  separately from the records).

### Performance Notes

- Fast; the response is small.

### Usage Notes

- Use this method to size a query before
  downloading the records.

---

## C02 — count_imports

### Method Name

`count_imports`

### Purpose

Return the number of import records matching a
query.

### Description

As C01, but with `flow_code='M'`.

### Parameters

As C01, minus `flow_code` (implied).

### Return Type

An integer count.

### Behaviour

- As C01, with `flow_code='M'`.

### Exceptions

- As C01.

### Side Effects

- As C01.

### Performance Notes

- As C01.

### Usage Notes

- As C01.

---

## C03 — count_trade

### Method Name

`count_trade`

### Purpose

Return the number of trade records matching a
query.

### Description

As C01, with an explicit flow code.

### Parameters

As T03, except `max_records` is not applicable.

### Return Type

An integer count.

### Behaviour

- As C01, with an explicit flow code.

### Exceptions

- As C01.

### Side Effects

- As C01.

### Performance Notes

- As C01.

### Usage Notes

- As C01.

---

## A01 — submit_async_final_data

### Method Name

`submit_async_final_data`

### Purpose

Submit a long-running data request and return a
handle.

### Description

The method submits an async request and returns a
handle. The handle is used to poll for status and
to download the result.

### Parameters

As T03.

### Return Type

An `AsyncRequestHandle` entity (E19).

### Behaviour

- The method issues a POST to the async submit
  endpoint.
- The handle is returned synchronously.
- The result is not returned by this method.

### Exceptions

- As T01.

### Side Effects

- Performs network I/O.
- Does not write to the cache.

### Performance Notes

- Submit latency: 0.30 to 1.00 seconds.

### Usage Notes

- The handle is the input to A02 and A03.

---

## A02 — check_async_request

### Method Name

`check_async_request`

### Purpose

Poll the status of an async request.

### Description

The method polls the async check endpoint and
returns the current status.

### Parameters

| Name         | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| ------------ | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `request_id` | string   | yes      | n/a     | non-empty      | n/a        | The handle SHALL be valid. |

### Return Type

An `AsyncRequestStatus` entity (E20).

### Behaviour

- The method issues a GET to the async check
  endpoint.

### Exceptions

- As T01.

### Side Effects

- Performs network I/O.
- Does not write to the cache.

### Performance Notes

- Poll latency: 0.10 to 0.30 seconds.

### Usage Notes

- The consumer polls periodically until the status
  is `Completed` or `Failed`.

---

## A03 — download_async_request

### Method Name

`download_async_request`

### Description

Download the result of an async request.

### Description

The method downloads the result to the configured
directory.

### Parameters

| Name         | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| ------------ | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `request_id` | string   | yes      | n/a     | non-empty      | n/a        | The handle SHALL be valid. |
| `directory`  | string   | yes      | n/a     | non-empty      | path       | The directory SHALL exist. |

### Return Type

The path to the downloaded file.

### Behaviour

- The method issues a GET to the async download
  endpoint.
- The result is written to the configured directory.

### Exceptions

- As T01, plus `ValidationError` for a non-existent
  directory.

### Side Effects

- Performs network I/O.
- Writes to the filesystem.

### Performance Notes

- Download latency depends on the result size.

### Usage Notes

- The result is a JSON file.

---

## A04 — bulk_download_final_file

### Method Name

`bulk_download_final_file`

### Purpose

Download the pre-built bulk data file for a
reporter and period.

### Description

The method downloads the bulk file to the configured
directory.

### Parameters

| Name            | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| --------------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `reporter_code` | integer  | yes      | n/a     | ≥ 0            | non-negative | n/a |
| `period`        | string   | yes      | n/a     | `YYYY` or `YYYYMM` | per Frequency | n/a |
| `classification` | string  | no       | `'HS'`  | documented     | n/a        | n/a |
| `edition`       | string   | no       | `None`  | documented     | n/a        | n/a |
| `directory`     | string   | no       | `None`  | path           | n/a        | The default is the configured cache directory. |
| `decompress`    | boolean  | no       | `True`  | true, false    | n/a        | When `True`, the file is decompressed. |

### Return Type

The path to the downloaded file.

### Behaviour

- The method issues a GET to the bulk download
  endpoint.
- The result is written to the configured directory.

### Exceptions

- As T01, plus `ValidationError` for a non-existent
  directory.

### Side Effects

- Performs network I/O.
- Writes to the filesystem.

### Performance Notes

- Download latency depends on the file size.
- Bulk files can be hundreds of megabytes.

### Usage Notes

- The file naming convention follows the
  `COMTRADE-FINAL-...` pattern documented in the
  upstream.

---

## A05 — bulk_download_tariffline_file

### Method Name

`bulk_download_tariffline_file`

### Purpose

Download the pre-built bulk tariffline file for a
reporter and period.

### Description

The method downloads the bulk tariffline file to
the configured directory.

### Parameters

As A04.

### Return Type

The path to the downloaded file.

### Behaviour

- As A04, but for tariffline data.

### Exceptions

- As A04.

### Side Effects

- As A04.

### Performance Notes

- As A04.

### Usage Notes

- The file naming convention follows the
  `COMTRADE-TARIFFLINE-...` pattern.

---

## U01 — get_data_availability

### Method Name

`get_data_availability`

### Purpose

Return the data availability for a combination of
reporter, period, and classification.

### Description

The method returns the data availability record(s)
for the given query.

### Parameters

| Name            | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| --------------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `reporter_code` | integer  | no       | `None`  | ≥ 0            | non-negative | n/a |
| `period`        | string   | yes      | n/a     | `YYYY` or `YYYYMM` | per Frequency | n/a |
| `classification` | string  | no       | `'HS'`  | documented     | n/a        | n/a |
| `edition`       | string   | no       | `None`  | documented     | n/a        | n/a |

### Return Type

A `Response` wrapping a collection of
`DataAvailabilityRecord` entities (E18).

### Behaviour

- The method issues a call to the data availability
  endpoint.

### Exceptions

- As T01.

### Side Effects

- Performs network I/O.
- Reads and writes cache.

### Performance Notes

- Fast; the response is small.

### Usage Notes

- Use this method to discover what data is
  currently available before issuing a large
  query.

---

## U02 — get_standard_unit_value

### Method Name

`get_standard_unit_value`

### Purpose

Return the reference Standard Unit Value for a
commodity.

### Description

The method returns the SUV record for the given
commodity and period.

### Parameters

| Name             | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| ---------------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `commodity_code` | string   | yes      | n/a     | documented     | per classification | n/a |
| `period`         | string   | yes      | n/a     | `YYYY`         | per Frequency | Annual only. |
| `classification` | string   | no       | `'HS'`  | documented     | n/a        | n/a |
| `edition`        | string   | no       | `None`  | documented     | n/a        | n/a |
| `flow_code`      | string   | no       | `None`  | documented     | n/a        | n/a |
| `qty_unit_code`  | integer  | no       | `8`     | documented     | n/a        | `8` is kilograms. |

### Return Type

A `Response` wrapping a collection of
`StandardUnitValue` entities (E16).

### Behaviour

- The method issues a call to the SUV endpoint.

### Exceptions

- As T01.

### Side Effects

- Performs network I/O.
- Reads and writes cache.

### Performance Notes

- Fast; the response is small.

### Usage Notes

- Use this method to detect price outliers in a
  trade record.

---

## U03 — get_publication_notes

### Method Name

`get_publication_notes`

### Purpose

Return the publication notes for a release.

### Description

The method returns the publication notes for the
given query.

### Parameters

| Name            | Datatype | Required | Default | Allowed Values | Validation | Constraints |
| --------------- | -------- | -------- | ------- | -------------- | ---------- | ----------- |
| `period`        | string   | yes      | n/a     | `YYYY` or `YYYYMM` | per Frequency | n/a |
| `reporter_code` | integer  | no       | `None`  | ≥ 0            | non-negative | n/a |
| `classification` | string  | no       | `'HS'`  | documented     | n/a        | n/a |
| `edition`       | string   | no       | `None`  | documented     | n/a        | n/a |
| `show_history`  | boolean  | no       | `False` | true, false    | n/a        | n/a |

### Return Type

A `Response` wrapping a collection of
`PublicationNote` entities (E17).

### Behaviour

- The method issues a call to the publication
  notes endpoint.

### Exceptions

- As T01.

### Side Effects

- Performs network I/O.
- Reads and writes cache.

### Performance Notes

- Fast; the response is small.

### Usage Notes

- Use this method to capture the publication
  version of a dataset.

---

# 5. Method Categories

The methods above are grouped into the categories
below. The category determines the layer ownership
and the typical use case.

## 5.1 Metadata

Methods that access the reference catalogue. M01–M18.
Layer ownership: metadata layer. Typical use case:
discovery and validation of codes.

## 5.2 Trade retrieval — annual

Methods that retrieve annual trade data. T01–T08.
Layer ownership: trade layer. Typical use case:
building a yearly dataset.

## 5.3 Trade retrieval — monthly

Methods that retrieve monthly trade data. T09–T11.
Layer ownership: trade layer. Typical use case:
building a monthly time series.

## 5.4 Tariffline

Methods that retrieve line-level data. F01–F02.
Layer ownership: trade layer. Typical use case:
line-level analysis.

## 5.5 Preview

Methods that use the public preview endpoint. P01–P04.
Layer ownership: trade layer. Typical use case:
ad-hoc queries and demos without a key.

## 5.6 Counting

Methods that return only the count. C01–C03. Layer
ownership: trade layer. Typical use case: query
sizing.

## 5.7 Async and bulk

Methods for long-running requests and bulk
downloads. A01–A05. Layer ownership: trade layer and
storage layer. Typical use case: large extracts.

## 5.8 Utility

Methods for data availability, SUV, and publication
notes. U01–U03. Layer ownership: trade layer.
Typical use case: provenance and data quality.

## 5.9 Administration

Reserved for future administrative methods (key
rotation, quota reporting). No public method in
this category at the date of this document.

---

# 6. Behavioural Contracts

The behavioural contracts below are the binding
contracts for every public method.

## 6.1 Input guarantees

- Every required parameter SHALL be provided.
- Every optional parameter SHALL be either omitted
  or set to a documented value.
- Every parameter SHALL satisfy the validation
  rules declared in section 4.
- The combination of parameters SHALL satisfy the
  cross-field dependencies declared in the data
  model.

## 6.2 Output guarantees

- The return type SHALL match the documented
  return type.
- The `Response` envelope SHALL contain every field
  declared in the data model.
- The records within the `Response` SHALL satisfy
  the validation rules of the corresponding entity.
- An empty result SHALL return a `Response` with
  `count=0` and `records=[]`.

## 6.3 Ordering guarantees

- The order of records within a `Response` is
  determined by the upstream API. The SDK SHALL NOT
  reorder the records.
- A consumer that requires a specific order SHALL
  sort the records after the call.

## 6.4 Determinism

- The output of a method is deterministic for a
  given input and a given cache state.
- The cache state is determined by the configuration
  and the upstream freshness.

## 6.5 Idempotency

- The metadata methods (M01–M18) are idempotent.
- The trade retrieval methods (T01–T11, F01–F02) are
  idempotent for a given cache state and a given
  upstream state.
- The counting methods (C01–C03) are idempotent.
- The async methods (A01–A03) are not idempotent
  across submissions; each submission creates a new
  handle.
- The bulk download methods (A04–A05) are not
  idempotent; each call may overwrite an existing
  file.

## 6.6 Consistency expectations

- The SDK SHALL NOT mix records from different
  upstream responses in a single `Response`.
- A cached `Response` SHALL be invalidated when the
  configuration declares that the cache lifetime has
  expired.

---

# 7. Error Contract

The error contract declares the public exception
hierarchy. The exception hierarchy is owned by the
`un_comtrade.errors` module declared in
`003_ARCHITECTURE.md` §9.2.

## 7.1 Base exception

`ComtradeError` is the base class of the public
exception hierarchy. Every public exception inherits
from `ComtradeError`.

## 7.2 Authentication error

`AuthenticationError` is raised when the
subscription key is missing, invalid, or expired.
Cause: HTTP 401. When raised: at any call to a
method that requires a key, when no key is
configured. Retry: no — the consumer SHALL provide a
valid key.

## 7.3 Rate limit error

`RateLimitError` is raised when the consumer has
exceeded the rate limit. Cause: HTTP 429. When
raised: at any call when the upstream has returned
429. Retry: yes, with the documented backoff; the
SDK retries automatically. The exception is raised
when the retry budget is exhausted.

## 7.4 Validation error

`ValidationError` is raised when a parameter is
malformed. Cause: invalid parameter value. When
raised: at any call when a parameter does not
satisfy the validation rules. Retry: no — the
consumer SHALL provide a valid parameter.

## 7.5 Reference error

`ReferenceError` is raised when a reference code is
unknown. Cause: a code that is not in the catalogue.
When raised: at any call that resolves a code. Retry:
no — the consumer SHALL provide a valid code.

## 7.6 Trade error

`TradeError` is raised when a trade query is
rejected by the upstream. Cause: HTTP 400 or
upstream-specific rejection. When raised: at any
trade retrieval method when the query is rejected.
Retry: depends on the upstream message; the
consumer SHALL consult the error message.

## 7.7 Network error

`NetworkError` is raised when the transport layer
fails to reach the upstream. Cause: network
failure, DNS failure, TLS failure. When raised: at
any call when the transport layer cannot complete
the request. Retry: yes, with the documented
backoff; the SDK retries automatically. The
exception is raised when the retry budget is
exhausted.

## 7.8 Timeout error

`TimeoutError` is raised when the transport layer
times out. Cause: request exceeds the configured
timeout. When raised: at any call when the transport
layer times out. Retry: yes, with the documented
backoff; the SDK retries automatically. The
exception is raised when the retry budget is
exhausted.

## 7.9 Upstream error

`UpstreamError` is raised when the upstream returns
a non-recoverable error. Cause: HTTP 5xx. When
raised: at any call when the upstream returns 5xx.
Retry: yes, with the documented backoff; the SDK
retries automatically. The exception is raised when
the retry budget is exhausted.

## 7.10 Endpoint not found error

`EndpointNotFoundError` is raised when the requested
URL is not a known endpoint. Cause: HTTP 404. When
raised: at any call when the upstream returns 404.
Retry: no — the consumer SHALL verify the endpoint.

## 7.11 Storage error

`StorageError` is raised when the storage layer
fails. Cause: filesystem error, permission error,
cache corruption. When raised: at any call that
writes to or reads from the cache. Retry: no — the
consumer SHALL verify the cache directory.

## 7.12 Configuration error

`ConfigurationError` is raised when the
configuration is invalid. Cause: missing key,
invalid timeout, invalid cache location. When
raised: at construction or at the first call that
uses the configuration. Retry: no — the consumer
SHALL provide a valid configuration.

## 7.13 Unknown error

`UnknownError` is raised when an unexpected
condition occurs. Cause: undocumented. When raised:
at any call when an unexpected condition is
detected. Retry: no — the consumer SHALL report the
error to the maintainer.

---

# 8. Configuration Contract

The configuration contract declares the configuration
surface of the SDK. The configuration is bound at
construction and is immutable after construction.

## 8.1 Authentication

- `subscription_key` (string, optional). The key
  issued by the developer portal. The order of
  precedence is: explicit construction argument,
  environment variable `UN_COMTRADE_KEY`,
  configuration file, default is `None` (no key).

## 8.2 Transport

- `timeout` (number, default 60). The request
  timeout in seconds.
- `proxy_url` (string, default `None`). An optional
  proxy URL.
- `max_retries` (integer, default 5). The maximum
  number of retries on transient errors.
- `initial_backoff_seconds` (number, default 1).
  The initial backoff in seconds.
- `backoff_multiplier` (number, default 2). The
  backoff multiplier.
- `backoff_cap_seconds` (number, default 60). The
  maximum backoff in seconds.

## 8.3 Caching

- `cache_enabled` (boolean, default `True`). Whether
  the cache is enabled.
- `cache_location` (string, default
  `~/.un_comtrade/cache`). The cache directory.
- `cache_lifetime_seconds` (number, default 86400).
  The cache lifetime in seconds (24 hours).
- `cache_metadata_lifetime_seconds` (number, default
  604800). The metadata cache lifetime in seconds
  (7 days).

## 8.4 Logging

- `log_level` (string, default `'WARNING'`). The log
  level (`'DEBUG'`, `'INFO'`, `'WARNING'`,
  `'ERROR'`, `'CRITICAL'`).
- `log_format` (string, default `'%(asctime)s
  %(levelname)s %(name)s %(message)s'`). The log
  format.
- `log_destination` (string, default `None`). The
  log destination. The default is the standard
  library's default handler.

## 8.5 Pagination

- `max_records_per_call` (integer, default
  250000). The maximum records per authenticated
  call.
- `preview_max_records_per_call` (integer, default
  500). The maximum records per preview call.

## 8.6 Rate limiting

- `requests_per_minute` (integer, default
  unverified). The configured requests-per-minute
  cap. The default is `None`; the SDK does not
  enforce a rate limit but documents the upstream
  cap.

## 8.7 Recorded samples

- `samples_directory` (string, default
  `~/.un_comtrade/samples`). The directory for
  recorded samples.
- `samples_retention_days` (integer, default 30).
  The retention period for recorded samples.

## 8.8 Construction

The configuration is passed to the constructor of
`ComtradeClient` as a typed object. The SDK SHALL
NOT read configuration from global state. The SDK
SHALL NOT mutate the configuration after
construction except through documented mutator
methods.

---

# 9. Output Contract

The output contract declares the supported output
formats of the SDK.

## 9.1 Canonical objects

The default output is the canonical model. Every
method returns an entity from the data model.

## 9.2 Response wrapper

A trade retrieval method returns a `Response`
entity (E22). The `Response` wraps a collection of
records and carries the elapsed time, the count, and
the error message.

## 9.3 Metadata collection

A metadata method returns a `MetadataCollection`
entity (E24). The collection wraps a typed array of
reference records.

## 9.4 Raw responses

The SDK SHALL NOT expose the raw upstream JSON
response. The canonical model is the only supported
output. The raw response is available through
`Response.upstream_url` for traceability.

## 9.5 DataFrame

A DataFrame handoff shape is a future consideration.
The SDK MAY expose an optional DataFrame output
through a documented parameter. The DataFrame output
is not in the MVP surface.

## 9.6 Serialisation

The SDK MAY expose a serialisation method that
returns a JSON string or a JSON file path. The
serialisation conforms to the data model
serialisation rules.

---

# 10. Compatibility Policy

The SDK follows Semantic Versioning 2.0.0. The
compatibility policy is normative.

## 10.1 Backward compatibility

A change is backward compatible if a consumer
that upgrades within a major version can continue
to use the SDK without modifying consumer code.

A change is backward compatible when:

- A new method is added.
- A new optional parameter with a default value is
  added to an existing method.
- A new value is added to an enumeration.
- A new entity is added.
- A new field is added to an existing entity, when
  the field is nullable.
- A new relationship is added between existing
  entities.
- The implementation of a method is changed
  without changing the documented behaviour.

## 10.2 Breaking changes

A change is a breaking change when:

- A documented public method is removed.
- A documented public method is renamed.
- A documented parameter is removed.
- A documented parameter is renamed.
- A documented parameter is made required (when it
  was previously optional).
- The documented return type is changed.
- A documented exception behaviour is changed.
- A documented default value of a parameter is
  changed such that a consumer who relied on the
  previous default observes different behaviour.
- A documented field of the canonical model is
  removed or renamed.
- The documented identity of an entity is changed.

## 10.3 Deprecation process

A documented public element may be marked deprecated
by:

1. Adding a deprecation note to the SDK
   specification.
2. Adding a deprecation warning to the runtime.
3. Adding a changelog entry.

The deprecation period SHALL last at least one minor
release before the element is removed in the next
major release. A deprecation note SHALL explain the
migration path.

## 10.4 Version guarantees

- Within a major version, the public interface is
  stable.
- A major version increment is reserved for breaking
  changes.
- A minor version increment is reserved for
  backward-compatible features.
- A patch version increment is reserved for
  backward-compatible corrections.

## 10.5 Semantic Versioning expectations

The SDK follows Semantic Versioning 2.0.0. The
version is encoded as `MAJOR.MINOR.PATCH`. A
pre-release version is encoded as
`MAJOR.MINOR.PATCH-IDENTIFIER`.

---

# 11. Extension Strategy

The SDK is extended by the rules below. Each
extension is recorded in the changelog and the
decisions log.

## 11.1 New methods

A new method is added in a minor version. The new
method SHALL be documented in this document with the
same level of detail as the existing methods. The
new method SHALL NOT change the behaviour of an
existing method.

## 11.2 New parameters

A new optional parameter with a default value is
added in a minor version. The new parameter SHALL
be documented in the method specification. The
new parameter SHALL NOT change the default
behaviour of the method.

## 11.3 New entities

A new entity is added in a minor version. The new
entity SHALL be documented in the data model. The
new entity SHALL NOT change the identity or the
behaviour of an existing entity.

## 11.4 New error types

A new error type is added in a minor version. The
new error type SHALL inherit from `ComtradeError`
or from a documented parent error. The new error
type SHALL be documented in section 7.

## 11.5 Backward compatibility

Every extension listed in this section preserves
backward compatibility within a major version. A
breaking change is reserved for a major version
increment and is recorded in `DECISIONS.md`.

---

# 12. Naming Conventions

The naming conventions below are the binding rules
for the public interface.

## 12.1 Method naming

- Method names use snake_case.
- Method names are imperative or descriptive: a
  method that returns a list of countries is named
  `get_countries`, not `countries` or `country_list`.
- Methods that perform a specific action on a
  resource are named `verb_resource`: `get_country`,
  `get_hs_code`, `search_hs`.
- Methods that return a count are prefixed with
  `count_`: `count_exports`.
- Methods that submit a request are prefixed with
  `submit_`: `submit_async_final_data`.
- Methods that check the status of a request are
  prefixed with `check_`: `check_async_request`.

## 12.2 Parameter naming

- Parameter names use snake_case.
- Parameter names are descriptive: `reporter_code`,
  not `r` or `rc`.
- Boolean parameters are prefixed with `is_`,
  `has_`, `include_`, or `show_`: `include_groups`,
  `show_history`.
- Default values are documented in the method
  specification.

## 12.3 Return object naming

- The return object is a `Response` (E22), a
  `MetadataCollection` (E24), or a primitive type.
- The return object SHALL NOT be a raw upstream
  JSON response.

## 12.4 Consistency rules

- The parameter set of a method SHALL be consistent
  with the parameter set of every other method that
  shares a domain.
- The return type of a method SHALL be consistent
  with the return type of every other method that
  shares a domain.
- The error behaviour of a method SHALL be
  consistent with the error behaviour of every
  other method that shares a domain.

## 12.5 Cross-references to the data model

- The canonical entity names from the data model
  are used in the return type descriptions.
- The canonical field names from the data model are
  used in the parameter descriptions.
- The canonical datatype names from the data model
  are used in the parameter type descriptions.

---

# 13. Future SDK Surface

The future SDK surface is the set of public methods
that MAY be added in a future version. The future
surface is documented for traceability; it is NOT
part of the MVP surface.

## 13.1 Async client

A separate async client class MAY be added in a
future version. The async client SHALL expose the
same public surface as `ComtradeClient`, with
`async` and `await` semantics on every method.

## 13.2 DataFrame output

A DataFrame output MAY be added as an optional
parameter on the trade retrieval methods. The
parameter is `as_dataframe=True`; the default is
`False`.

## 13.3 Streaming output

A streaming output MAY be added for very large
responses. The streaming output is a generator that
yields `Response` envelopes.

## 13.4 Plugin model

A plugin model MAY be added for storage engines,
exporters, and transport engines. The plugin model
is exposed through a documented extension point.

## 13.5 Multi-version support

The SDK MAY evolve to support multiple versions of
the upstream API simultaneously. The support is
expressed as a versioned client whose transport
layer selects the appropriate URL template.

## 13.6 Server-side components

The SDK SHALL NOT evolve to include server-side
components. The SDK is a client library. Server-side
components are the responsibility of separate
projects.

---

# 14. Assumptions

The assumptions below are recorded for traceability.
An assumption that turns out to be false is recorded
in `DECISIONS.md` as a correction and is propagated
to the relevant specification documents.

## 14.1 Verified assumptions

- The upstream response has four top-level keys
  (`elapsedTime`, `count`, `data`, `error`).
  Verified by live request.
- The reporter code for India is 699. Verified.
- The preview endpoint is capped at 500 records.
  Verified.
- The authenticated endpoint is capped at 250,000
  records. Verified.
- The 401 response body is structured.
  Verified.
- The CORS headers are not set. Verified.

## 14.2 Inferred assumptions

- The per-minute request cap on the public preview
  surface is unverified. The SDK does not enforce a
  rate limit by default; the default is to rely on
  the upstream.
- The `legacyEstimationFlag` integer values are
  documented in the upstream; the SDK preserves the
  integer.
- The `aggrLevel` semantics is documented in the
  upstream; the SDK preserves the integer.
- The data availability endpoint URL is documented
  in the official `comtradeapicall` package; the
  SDK exposes the method.
- The async delivery and bulk download endpoint
  URLs are documented in the official package; the
  SDK exposes the methods.

## 14.3 Local design decisions

- The public methods use snake_case parameter names.
  The wire format uses camelCase; the SDK normalises
  the casing.
- The default classification is HS; the default
  edition is the latest published.
- The default `commodity_code` is `'TOTAL'` (all
  products).
- The default `breakdown_mode` is `'classic'`.
- The default `max_records` is `None`; the SDK uses
  the endpoint cap.
- The default `partner_code` is `None`; the SDK
  uses all partners.
- The `partner_code=0` (World) is exposed as a
  constant `un_comtrade.PARTNER_WORLD = 0`.
- A `Response` with `count=0` is a successful empty
  result, not an error.
- The metadata collection is loaded on first use and
  cached for the metadata cache lifetime.

---

# 15. Open Questions

The questions below are recorded for future
resolution. Each question is described with the
impact and the suggested verification.

- **OQ-SDK-001 (Medium).** Should the SDK expose a
  `get_availability(reporter_code, period)` method
  that returns the count of records, instead of the
  current `U01` method? **Impact.** The current
  `U01` returns a collection; a count-only method
  would be simpler. **Suggested verification.** Confirm
  with the consumer ergonomics.

- **OQ-SDK-002 (Medium).** Should the async methods
  be on a separate client class, or on the same
  client? **Impact.** The current design puts them
  on the same client. A separate class would isolate
  the async lifecycle. **Suggested verification.**
  Confirm with the implementation ergonomics.

- **OQ-SDK-003 (Low).** Should the SDK expose a
  `get_trade_envelope(reporter_code, flow_code,
  period)` method that combines the `get_trade`,
  `get_trade_balance`, and `get_bilateral` methods
  into a single call? **Impact.** A single call
  would reduce the number of network round-trips.
  **Suggested verification.** Confirm with the
  analytics use case.

- **OQ-SDK-004 (Low).** Should the SDK expose a
  `get_metadata_diff(table_name, since)` method
  that returns the changes to a catalogue since a
  given timestamp? **Impact.** A diff method would
  support change-data-capture workflows. **Suggested
  verification.** Confirm with the storage
  requirements.

- **OQ-SDK-005 (Low).** Should the SDK expose a
  `validate_query(...)` method that validates a
  query without issuing it? **Impact.** A validation
  method would support pre-flight checks.
  **Suggested verification.** Confirm with the
  consumer ergonomics.

- **OQ-SDK-006 (Low).** Should the SDK expose a
  `get_recent_releases()` method that returns the
  recent data releases from the live update endpoint?
  **Impact.** A recent-releases method would
  support dashboard workflows. **Suggested
  verification.** Confirm with the analytics use
  case.

- **OQ-SDK-007 (Low).** Should the SDK expose
  constants for the special `flow_code` values
  (`un_comtrade.FLOW_EXPORT = 'X'`,
  `un_comtrade.FLOW_IMPORT = 'M'`)? **Impact.**
  Constants would reduce the risk of typos.
  **Suggested verification.** Confirm with the
  implementation ergonomics.

- **OQ-SDK-008 (Low).** Should the SDK expose
  constants for the classification codes
  (`un_comtrade.CLASSIFICATION_HS = 'HS'`,
  `un_comtrade.CLASSIFICATION_HS_2022 = 'H6'`)? **Impact.**
  Constants would reduce the risk of typos.
  **Suggested verification.** Confirm with the
  implementation ergonomics.

- **OQ-SDK-009 (Low).** Should the SDK expose an
  `__all__` list that documents the public
  surface? **Impact.** An `__all__` list would
  enable linters to detect unintended exports.
  **Suggested verification.** Confirm with the
  packaging specification.

- **OQ-SDK-010 (Low).** Should the SDK expose a
  `__version__` constant? **Impact.** A version
  constant would support runtime version checks.
  **Suggested verification.** Confirm with the
  packaging specification.

---

# End of document
