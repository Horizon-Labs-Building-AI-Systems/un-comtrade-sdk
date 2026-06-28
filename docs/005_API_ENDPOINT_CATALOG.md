```
Document ID
005

Title
API Endpoint Catalog

Version
0.1.0

Status
DRAFT

Created
2026-06-26T20:03:39Z

Last Updated
2026-06-26T20:03:39Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
004_API_RESEARCH.md

Supersedes
None
```

---

# Purpose

This document is the authoritative endpoint registry for
the UN Comtrade API as consumed by this project. Every
endpoint is recorded under the same template. The
document is a reference; it does not include narrative
discussion. Research discussion lives in
`004_API_RESEARCH.md`; this catalog reuses verified
information from that document and adds a structured
specification that is suitable as an implementation
reference.

# Classification

The endpoints documented in this catalog are classified
into the categories below. The classification determines
the order in which the endpoints appear.

- **Authentication.** The mechanism by which the
  consumer authenticates with the API.
- **Metadata.** The reference catalogue endpoints.
- **Trade.** The authenticated data endpoints.
- **Preview.** The unauthenticated data endpoints.
- **Tariff.** The line-level data endpoints.
- **Utility.** Tooling endpoints and the Standard Unit
  Value endpoint.
- **Administrative.** Endpoints for data availability,
  bulk download, async delivery, and publication
  metadata.
- **Deprecated.** Endpoints documented as deprecated.
  None at the date of this document.

# Future SDK Mapping

The endpoints documented in this catalog map to the
future SDK method names below. The mapping is normative
at the method-name level; the implementation is the
responsibility of the SDK specification and the
implementation tasks.

| Endpoint family  | Future SDK module        | Future SDK method (illustrative)      |
| ---------------- | ------------------------ | ------------------------------------- |
| Authentication   | `un_comtrade.client`     | `ComtradeClient(subscription_key=...)` |
| Reference        | `un_comtrade.metadata`   | `get_reporters`, `get_partners`, `get_classification`, `get_frequencies`, `get_trade_flows`, `get_quantity_units`, `get_modes_of_transport`, `get_customs_codes`, `get_data_items` |
| Preview          | `un_comtrade.trade`      | `preview_annual`, `preview_monthly`, `preview_final`, `preview_tariffline` |
| Trade            | `un_comtrade.trade`      | `get_annual`, `get_monthly`, `get_final`, `get_trade_matrix`, `get_trade_balance`, `get_bilateral` |
| Tariff           | `un_comtrade.trade`      | `get_tariffline_annual`, `get_tariffline_monthly` |
| Utility          | `un_comtrade.trade`      | `get_standard_unit_value`, `get_publication_notes` |
| Administrative   | `un_comtrade.trade`      | `get_data_availability`, `submit_async_request`, `check_async_request`, `download_async_request`, `bulk_download_final_file`, `bulk_download_tariffline_file` |

The future SDK method names are illustrative; the SDK
specification may refine them.

---

# Authentication

---

## A1 — Subscription Key Authentication

### HTTP Method

Not applicable. The authentication mechanism is a query
parameter or an HTTP header on every authenticated
endpoint.

### Endpoint Path

Not applicable. The mechanism is documented separately
from the endpoints that consume it.

### Base URL

- Authenticated data: `https://comtradeapi.un.org/data/v1`
- Authenticated tools: `https://comtradeapi.un.org/tools/v1`

### Category

Authentication.

### Purpose

Authenticates a consumer against the authenticated
endpoints of the UN Comtrade API. The mechanism is a
subscription key issued by the developer portal. The key
is a long opaque string. The key is sent on every
authenticated request either as a query parameter or as
an HTTP header.

### SDK Priority

Critical.

### Authentication

Not applicable — this entry documents the mechanism that
authenticates the other entries.

### Request Format

- Query parameter: `subscription-key=...`
- HTTP header: `Ocp-Apim-Subscription-Key: ...`

The query parameter form is the canonical form for the
SDK and is the form exercised by the official
`comtradeapicall` Python package.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| subscription-key | string | The key issued by the developer portal. | Any opaque string. | `AbCdEf1234567890` |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| Ocp-Apim-Subscription-Key | string | (none) | The same key, supplied as an HTTP header. | `AbCdEf1234567890` |

### Response

Not applicable. The authentication mechanism does not
return a response; it is consumed by the endpoints that
require it.

### Pagination

Not applicable.

### Rate Limiting

- **Known limits.** Daily record cap of 50,000,000
  records for the free tier.
- **Observed limits.** Unverified.
- **Per-minute cap.** Unverified.

### Typical Use Cases

- Authenticate every call to a data endpoint.
- Authenticate every call to a tools endpoint.
- Authenticate every call to an administrative endpoint.

### SDK Wrapper

The mechanism is consumed by the `ComtradeClient`
constructor of the `un_comtrade.client` module. The
constructor accepts the key as `subscription_key=`.

### Dependencies

- A valid subscription key from the developer portal.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 401 | The key is missing, invalid, or expired. | Provide a valid key. | No. |
| 429 | The consumer has exceeded the rate limit. | Wait and retry. | Yes, with backoff. |

### Performance Notes

- The key is sent on every request. The SDK SHALL avoid
  logging the full URL to prevent key leakage.

### Known Limitations

- The 401 response does not distinguish between a
  missing key, an invalid key, and an expired key. The
  SDK SHALL treat all three as the same exception.
- The key is sent in the URL; a consumer that logs the
  URL will leak the key.

### Verification Status

Verified.

### Documentation References

- `004_API_RESEARCH.md`, §2 and §7.2, §7.3.

---

# Metadata

The reference catalogue endpoints are documented below.
All reference endpoints are public and do not require
authentication. Every reference endpoint returns a
JSON object whose top-level key is `results` and whose
value is an array of records. The record shape depends
on the catalogue.

---

## M1 — List of References

### HTTP Method

GET.

### Endpoint Path

`/files/v1/app/reference/ListofReferences.json`

### Base URL

`https://comtradeapi.un.org`

### Category

Metadata.

### Purpose

Enumerates the available reference tables. Returns 28
entries that describe every other reference endpoint
documented in this catalog. The endpoint is static and
serves a small payload; the SDK uses it to discover the
catalogue and may also expose it to the consumer.

### SDK Priority

High.

### Authentication

Public.

### Request Format

- Path parameters: none.
- Query parameters: none.
- Headers: none.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| (none) | | | | |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| (none) | | | | |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** A JSON object with key `results`.
- **Top-level fields.** `results` (array of objects).
- **Nested objects.** Each entry has `category`,
  `variable`, `description`, `fileuri`.

### Pagination

Not supported.

### Rate Limiting

- **Known limits.** None published.
- **Observed limits.** None.
- The endpoint is static; no practical rate limit.

### Typical Use Cases

- Enumerate the reference tables.
- Discover the URL of a reference table.
- Build a UI that lists the reference tables.

### SDK Wrapper

- `un_comtrade.metadata.list_references()`

### Dependencies

None.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 404 | The reference file is missing. | Verify the URL. | No. |

### Performance Notes

- Typical latency: 0.05 to 0.30 seconds.
- The file is small and CDN-cached.

### Known Limitations

- The list is static; new reference tables require an
  upstream publication to appear.

### Verification Status

Verified.

### Documentation References

- `004_API_RESEARCH.md`, §3.1, §4.1, §10.
- `uncomtrade.org/docs/list-of-references-parameter-codes/`.

---

## M2 — Reporters

### HTTP Method

GET.

### Endpoint Path

`/files/v1/app/reference/Reporters.json`

### Base URL

`https://comtradeapi.un.org`

### Category

Metadata.

### Purpose

Enumerates the reporter countries and areas. Returns
255 entries that identify every economy that has
reported trade data. Each entry includes the current
reporter code, the historical code (if any), the ISO
codes, and the validity dates. India appears under both
`reporterCode=699` (current) and `reporterCode=356`
(historical, expired 1974-12-31).

### SDK Priority

High.

### Authentication

Public.

### Request Format

- Path parameters: none.
- Query parameters: none.
- Headers: none.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| (none) | | | | |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| (none) | | | | |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** A JSON object with key `results`.
- **Top-level fields.** `results` (array of objects).
- **Nested objects.** Each entry has `id`, `text`,
  `reporterCode`, `reporterDesc`, `reporterNote`,
  `reporterCodeIsoAlpha2`, `reporterCodeIsoAlpha3`,
  `entryEffectiveDate`, `entryExpiredDate`, `isGroup`.

### Pagination

Not supported.

### Rate Limiting

- **Known limits.** None published.
- **Observed limits.** None.

### Typical Use Cases

- Resolve a reporter identifier from the catalogue.
- Build a UI that lists the reporter countries.
- Validate a user-supplied reporter code.

### SDK Wrapper

- `un_comtrade.metadata.get_reporters()`

### Dependencies

None.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 404 | The reference file is missing. | Verify the URL. | No. |

### Performance Notes

- Typical latency: 0.10 to 0.40 seconds.
- The file is approximately 78 KB.

### Known Limitations

- The list mixes current and historical codes; the
  consumer SHALL filter by `entryExpiredDate` to obtain
  the current codes.

### Verification Status

Verified.

### Documentation References

- `004_API_RESEARCH.md`, §3.1, §4.2, §6.3, §10.
- `uncomtrade.org/docs/list-of-references-parameter-codes/`.

---

## M3 — Partner Areas

### HTTP Method

GET.

### Endpoint Path

`/files/v1/app/reference/partnerAreas.json`

### Base URL

`https://comtradeapi.un.org`

### Category

Metadata.

### Purpose

Enumerates the partner countries and areas. Returns 310
entries that identify every counterparty that can appear
in a trade record. The list includes the special
partner code `0` (World aggregate) and aggregate group
codes.

### SDK Priority

High.

### Authentication

Public.

### Request Format

- Path parameters: none.
- Query parameters: none.
- Headers: none.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| (none) | | | | |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| (none) | | | | |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** A JSON object with key `results`.
- **Top-level fields.** `results` (array of objects).
- **Nested objects.** Same shape as M2 reporters.

### Pagination

Not supported.

### Rate Limiting

- **Known limits.** None published.
- **Observed limits.** None.

### Typical Use Cases

- Resolve a partner identifier.
- Build a UI that lists the partner countries.
- Validate a user-supplied partner code.

### SDK Wrapper

- `un_comtrade.metadata.get_partners()`

### Dependencies

None.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 404 | The reference file is missing. | Verify the URL. | No. |

### Performance Notes

- Typical latency: 0.10 to 0.40 seconds.
- The file is approximately 93 KB.

### Known Limitations

None.

### Verification Status

Verified.

### Documentation References

- `004_API_RESEARCH.md`, §3.1, §4.3, §10.

---

## M4 — HS Combined Classification

### HTTP Method

GET.

### Endpoint Path

`/files/v1/app/reference/HS.json`

### Base URL

`https://comtradeapi.un.org`

### Category

Metadata.

### Purpose

Enumerates the harmonised system codes across every
edition. Returns 8,262 entries. The list is the largest
of the HS variants and is the canonical list when the
consumer does not pin a specific edition.

### SDK Priority

High.

### Authentication

Public.

### Request Format

- Path parameters: none.
- Query parameters: none.
- Headers: none.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| (none) | | | | |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| (none) | | | | |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** A JSON object with key `results`.
- **Top-level fields.** `results` (array of objects).
- **Nested objects.** Each entry has the standard HS
  fields, including the chapter, heading, and
  subheading.

### Pagination

Not supported.

### Rate Limiting

- **Known limits.** None published.
- **Observed limits.** None.

### Typical Use Cases

- Resolve an HS code to a description.
- Build a UI that lists the HS codes.

### SDK Wrapper

- `un_comtrade.metadata.get_classification('HS')`

### Dependencies

None.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 404 | The reference file is missing. | Verify the URL. | No. |

### Performance Notes

- Typical latency: 0.20 to 0.80 seconds.
- The file is approximately 2.0 MB.

### Known Limitations

- The combined list does not preserve the per-edition
  hierarchy; the consumer SHALL use the per-edition
  list when the edition matters.

### Verification Status

Verified.

### Documentation References

- `004_API_RESEARCH.md`, §3.1, §4.4, §10.

---

## M5 — HS Per-Edition Classification

### HTTP Method

GET.

### Endpoint Path

`/files/v1/app/reference/H{0,1,2,3,4,5,6}.json`

### Base URL

`https://comtradeapi.un.org`

### Category

Metadata.

### Purpose

Enumerates the harmonised system codes for a specific
edition. Returns between 6,000 and 7,000 entries per
edition. The editions are `H0` (HS 1992), `H1`
(HS 1996), `H2` (HS 2002), `H3` (HS 2007), `H4`
(HS 2012), `H5` (HS 2017), `H6` (HS 2022).

### SDK Priority

High.

### Authentication

Public.

### Request Format

- Path parameters: none.
- Query parameters: none.
- Headers: none.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| (none) | | | | |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| (none) | | | | |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** A JSON object with key `results`.
- **Top-level fields.** `results` (array of objects).
- **Nested objects.** Same shape as M4.

### Pagination

Not supported.

### Rate Limiting

- **Known limits.** None published.
- **Observed limits.** None.

### Typical Use Cases

- Resolve an HS code against a specific edition.
- Build a UI that lists the HS codes for a chosen
  edition.

### SDK Wrapper

- `un_comtrade.metadata.get_classification('H6')` (or
  any other edition).

### Dependencies

None.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 404 | The reference file is missing or the edition is unknown. | Verify the URL. | No. |

### Performance Notes

- Typical latency: 0.20 to 0.80 seconds.
- The file size is approximately 1.7 MB for HS 2022.

### Known Limitations

- The number of editions is fixed at 7; a new HS
  edition requires an upstream publication.

### Verification Status

Verified (H5, H6). Documented for the other editions.

### Documentation References

- `004_API_RESEARCH.md`, §3.1, §4.5, §10.

---

## M6 — SITC Classification

### HTTP Method

GET.

### Endpoint Path

`/files/v1/app/reference/S{1,2,3,4}.json` and
`/files/v1/app/reference/SS.json`

### Base URL

`https://comtradeapi.un.org`

### Category

Metadata.

### Purpose

Enumerates the Standard International Trade
Classification codes for a specific revision. Revisions
are `S1` (Rev.1), `S2` (Rev.2), `S3` (Rev.3), `S4`
(Rev.4). The combined list is `SS`.

### SDK Priority

Medium.

### Authentication

Public.

### Request Format

- Path parameters: none.
- Query parameters: none.
- Headers: none.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| (none) | | | | |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| (none) | | | | |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** A JSON object with key `results`.
- **Top-level fields.** `results` (array of objects).
- **Nested objects.** Each entry has the standard SITC
  fields.

### Pagination

Not supported.

### Rate Limiting

- **Known limits.** None published.
- **Observed limits.** None.

### Typical Use Cases

- Resolve an SITC code to a description.
- Build a UI that lists the SITC codes.

### SDK Wrapper

- `un_comtrade.metadata.get_classification('S4')` (or
  any other revision).

### Dependencies

None.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 404 | The reference file is missing. | Verify the URL. | No. |

### Performance Notes

- Typical latency: 0.10 to 0.30 seconds.
- File size is small.

### Known Limitations

None.

### Verification Status

Documented.

### Documentation References

- `004_API_RESEARCH.md`, §3.1, §4.6, §10.

---

## M7 — BEC Classification

### HTTP Method

GET.

### Endpoint Path

`/files/v1/app/reference/B4.json` and
`/files/v1/app/reference/B5.json`

### Base URL

`https://comtradeapi.un.org`

### Category

Metadata.

### Purpose

Enumerates the Broad Economic Categories for goods by
end-use. Revisions are `B4` (Rev.4) and `B5` (Rev.5).

### SDK Priority

Low.

### Authentication

Public.

### Request Format

- Path parameters: none.
- Query parameters: none.
- Headers: none.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| (none) | | | | |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| (none) | | | | |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** A JSON object with key `results`.
- **Top-level fields.** `results` (array of objects).
- **Nested objects.** Each entry has the standard BEC
  fields.

### Pagination

Not supported.

### Rate Limiting

- **Known limits.** None published.
- **Observed limits.** None.

### Typical Use Cases

- Resolve a BEC code to a description.
- Build a UI that lists the BEC categories.

### SDK Wrapper

- `un_comtrade.metadata.get_classification('B4')` (or
  any other revision).

### Dependencies

None.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 404 | The reference file is missing. | Verify the URL. | No. |

### Performance Notes

- Typical latency: 0.10 to 0.30 seconds.
- File size is small.

### Known Limitations

None.

### Verification Status

Documented.

### Documentation References

- `004_API_RESEARCH.md`, §3.1, §4.7, §10.

---

## M8 — EBOPS Classification

### HTTP Method

GET.

### Endpoint Path

`/files/v1/app/reference/EB02.json`,
`/files/v1/app/reference/EB10.json`,
`/files/v1/app/reference/EB10S.json`,
`/files/v1/app/reference/EB.json`

### Base URL

`https://comtradeapi.un.org`

### Category

Metadata.

### Purpose

Enumerates the Extended Balance of Payments Services
classifications. Variants are `EB02` (EBOPS 2002),
`EB10` (EBOPS 2010), `EB10S` (EBOPS 2010 SDMX), `EB`
(combined). Only relevant to `typeCode=S` (services).

### SDK Priority

Low.

### Authentication

Public.

### Request Format

- Path parameters: none.
- Query parameters: none.
- Headers: none.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| (none) | | | | |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| (none) | | | | |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** A JSON object with key `results`.
- **Top-level fields.** `results` (array of objects).
- **Nested objects.** Each entry has the standard
  EBOPS fields.

### Pagination

Not supported.

### Rate Limiting

- **Known limits.** None published.
- **Observed limits.** None.

### Typical Use Cases

- Resolve an EBOPS code to a description.

### SDK Wrapper

- `un_comtrade.metadata.get_classification('EB10')` (or
  any other variant).

### Dependencies

None.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 404 | The reference file is missing. | Verify the URL. | No. |

### Performance Notes

- Typical latency: 0.10 to 0.30 seconds.
- File size is small.

### Known Limitations

None.

### Verification Status

Documented.

### Documentation References

- `004_API_RESEARCH.md`, §3.1, §4.8, §10.

---

## M9 — Frequency

### HTTP Method

GET.

### Endpoint Path

`/files/v1/app/reference/Frequency.json`

### Base URL

`https://comtradeapi.un.org`

### Category

Metadata.

### Purpose

Enumerates the frequency codes used to identify the
time granularity of a query. Returns 3 entries: `A`
(annual), `M` (monthly), and a sentinel value for the
period aggregate.

### SDK Priority

High.

### Authentication

Public.

### Request Format

- Path parameters: none.
- Query parameters: none.
- Headers: none.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| (none) | | | | |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| (none) | | | | |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** A JSON object with key `results`.
- **Top-level fields.** `results` (array of objects).
- **Nested objects.** Each entry has the standard
  frequency fields.

### Pagination

Not supported.

### Rate Limiting

- **Known limits.** None published.
- **Observed limits.** None.

### Typical Use Cases

- Validate a user-supplied frequency code.
- Build a UI that lists the frequency options.

### SDK Wrapper

- `un_comtrade.metadata.get_frequencies()`

### Dependencies

None.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 404 | The reference file is missing. | Verify the URL. | No. |

### Performance Notes

- Typical latency: 0.05 to 0.20 seconds.
- File size is small (154 bytes).

### Known Limitations

None.

### Verification Status

Verified.

### Documentation References

- `004_API_RESEARCH.md`, §3.1, §4.9, §10.

---

## M10 — Trade Flows

### HTTP Method

GET.

### Endpoint Path

`/files/v1/app/reference/tradeRegimes.json`

### Base URL

`https://comtradeapi.un.org`

### Category

Metadata.

### Purpose

Enumerates the trade flow codes that identify the
direction of a trade. Returns 10 entries including
`M` (import), `X` (export), `RX` (re-export), `RM`
(re-import), and the `plus`-mode derived codes.

### SDK Priority

High.

### Authentication

Public.

### Request Format

- Path parameters: none.
- Query parameters: none.
- Headers: none.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| (none) | | | | |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| (none) | | | | |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** A JSON object with key `results`.
- **Top-level fields.** `results` (array of objects).
- **Nested objects.** Each entry has the standard
  trade flow fields.

### Pagination

Not supported.

### Rate Limiting

- **Known limits.** None published.
- **Observed limits.** None.

### Typical Use Cases

- Validate a user-supplied flow code.
- Build a UI that lists the flow options.

### SDK Wrapper

- `un_comtrade.metadata.get_trade_flows()`

### Dependencies

None.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 404 | The reference file is missing. | Verify the URL. | No. |

### Performance Notes

- Typical latency: 0.05 to 0.20 seconds.
- File size is small (658 bytes).

### Known Limitations

None.

### Verification Status

Verified.

### Documentation References

- `004_API_RESEARCH.md`, §3.1, §4.10, §10.

---

## M11 — Customs Procedure Codes

### HTTP Method

GET.

### Endpoint Path

`/files/v1/app/reference/CustomsCodes.json`

### Base URL

`https://comtradeapi.un.org`

### Category

Metadata.

### Purpose

Enumerates the customs procedure codes that identify
the customs treatment of a trade. `C00` is the total.

### SDK Priority

Medium.

### Authentication

Public.

### Request Format

- Path parameters: none.
- Query parameters: none.
- Headers: none.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| (none) | | | | |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| (none) | | | | |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** A JSON object with key `results`.
- **Top-level fields.** `results` (array of objects).
- **Nested objects.** Each entry has the standard
  customs code fields.

### Pagination

Not supported.

### Rate Limiting

- **Known limits.** None published.
- **Observed limits.** None.

### Typical Use Cases

- Validate a user-supplied customs code.

### SDK Wrapper

- `un_comtrade.metadata.get_customs_codes()`

### Dependencies

None.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 404 | The reference file is missing. | Verify the URL. | No. |

### Performance Notes

- Typical latency: 0.05 to 0.20 seconds.
- File size is small.

### Known Limitations

None.

### Verification Status

Documented.

### Documentation References

- `004_API_RESEARCH.md`, §3.1, §4.11, §10.

---

## M12 — Modes of Transport

### HTTP Method

GET.

### Endpoint Path

`/files/v1/app/reference/ModeOfTransportCodes.json`

### Base URL

`https://comtradeapi.un.org`

### Category

Metadata.

### Purpose

Enumerates the modes of transport codes. Returns 18
entries. The total is `0`.

### SDK Priority

Medium.

### Authentication

Public.

### Request Format

- Path parameters: none.
- Query parameters: none.
- Headers: none.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| (none) | | | | |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| (none) | | | | |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** A JSON object with key `results`.
- **Top-level fields.** `results` (array of objects).
- **Nested objects.** Each entry has the standard
  transport code fields.

### Pagination

Not supported.

### Rate Limiting

- **Known limits.** None published.
- **Observed limits.** None.

### Typical Use Cases

- Validate a user-supplied transport code.

### SDK Wrapper

- `un_comtrade.metadata.get_modes_of_transport()`

### Dependencies

None.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 404 | The reference file is missing. | Verify the URL. | No. |

### Performance Notes

- Typical latency: 0.05 to 0.20 seconds.
- File size is small (1.1 KB).

### Known Limitations

None.

### Verification Status

Verified.

### Documentation References

- `004_API_RESEARCH.md`, §3.1, §4.12, §10.

---

## M13 — Modes of Supply

### HTTP Method

GET.

### Endpoint Path

`/files/v1/app/reference/ModeOfSupply.json`

### Base URL

`https://comtradeapi.un.org`

### Category

Metadata.

### Purpose

Enumerates the modes of supply codes for services
trade. Only relevant to `typeCode=S`.

### SDK Priority

Low.

### Authentication

Public.

### Request Format

- Path parameters: none.
- Query parameters: none.
- Headers: none.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| (none) | | | | |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| (none) | | | | |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** A JSON object with key `results`.
- **Top-level fields.** `results` (array of objects).
- **Nested objects.** Each entry has the standard
  mode of supply fields.

### Pagination

Not supported.

### Rate Limiting

- **Known limits.** None published.
- **Observed limits.** None.

### Typical Use Cases

- Validate a user-supplied mode of supply code.

### SDK Wrapper

- `un_comtrade.metadata.get_modes_of_supply()`

### Dependencies

None.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 404 | The reference file is missing. | Verify the URL. | No. |

### Performance Notes

- Typical latency: 0.05 to 0.20 seconds.
- File size is small.

### Known Limitations

None.

### Verification Status

Documented.

### Documentation References

- `004_API_RESEARCH.md`, §3.1, §4.13, §10.

---

## M14 — Quantity Units

### HTTP Method

GET.

### Endpoint Path

`/files/v1/app/reference/QuantityUnits.json`

### Base URL

`https://comtradeapi.un.org`

### Category

Metadata.

### Purpose

Enumerates the quantity unit codes used in the
response payload. Returns 41 entries. The total is
encoded as `-1`.

### SDK Priority

Medium.

### Authentication

Public.

### Request Format

- Path parameters: none.
- Query parameters: none.
- Headers: none.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| (none) | | | | |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| (none) | | | | |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** A JSON object with key `results`.
- **Top-level fields.** `results` (array of objects).
- **Nested objects.** Each entry has the standard
  quantity unit fields.

### Pagination

Not supported.

### Rate Limiting

- **Known limits.** None published.
- **Observed limits.** None.

### Typical Use Cases

- Resolve a quantity unit code to an abbreviation.

### SDK Wrapper

- `un_comtrade.metadata.get_quantity_units()`

### Dependencies

None.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 404 | The reference file is missing. | Verify the URL. | No. |

### Performance Notes

- Typical latency: 0.05 to 0.20 seconds.
- File size is small (4.3 KB).

### Known Limitations

None.

### Verification Status

Verified.

### Documentation References

- `004_API_RESEARCH.md`, §3.1, §4.14, §10.

---

## M15 — Trade Data Items

### HTTP Method

GET.

### Endpoint Path

`/files/v1/app/reference/TradeDataItems.json`

### Base URL

`https://comtradeapi.un.org`

### Category

Metadata.

### Purpose

Enumerates the data item (column) catalogue used to
interpret every field of a trade record. Returns 50
entries. The catalogue is the source of truth for the
field-level documentation that the data model
specification refines.

### SDK Priority

High.

### Authentication

Public.

### Request Format

- Path parameters: none.
- Query parameters: none.
- Headers: none.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| (none) | | | | |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| (none) | | | | |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** A JSON object with key `results`.
- **Top-level fields.** `results` (array of objects).
- **Nested objects.** Each entry has the standard data
  item fields.

### Pagination

Not supported.

### Rate Limiting

- **Known limits.** None published.
- **Observed limits.** None.

### Typical Use Cases

- Interpret the column catalogue.
- Drive the data model specification.

### SDK Wrapper

- `un_comtrade.metadata.get_data_items()`

### Dependencies

None.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 404 | The reference file is missing. | Verify the URL. | No. |

### Performance Notes

- Typical latency: 0.10 to 0.30 seconds.
- File size is small (12.9 KB).

### Known Limitations

None.

### Verification Status

Verified.

### Documentation References

- `004_API_RESEARCH.md`, §3.1, §4.15, §10.

---

# Trade

The authenticated trade data endpoints are documented
below. Every trade endpoint requires a subscription key
and returns a JSON object whose top-level keys are
`elapsedTime`, `count`, `data`, and `error`. The `data`
array contains 0 to N records, each with the 47 fields
documented in `004_API_RESEARCH.md` §6.2.

---

## T1 — Authenticated Final Data

### HTTP Method

GET.

### Endpoint Path

`/data/v1/get/{typeCode}/{freqCode}/{clCode}`

### Base URL

`https://comtradeapi.un.org`

### Category

Trade.

### Purpose

Returns up to 250,000 final trade data records in a
single call. The endpoint is the primary authenticated
surface for trade data. It accepts the full parameter
set, including `subscription-key`, `reporterCode`,
`period`, `flowCode`, `cmdCode`, `partnerCode`,
`partner2Code`, `customsCode`, `motCode`, `maxRecords`,
`format`, `aggregateBy`, `breakdownMode`,
`countOnly`, `includeDesc`. The endpoint is
case-insensitive on `reporterCode` (camelCase).

### SDK Priority

Critical.

### Authentication

Subscription Key.

### Request Format

- Path parameters: `typeCode`, `freqCode`, `clCode`.
- Query parameters: documented in §5 of
  `004_API_RESEARCH.md`.
- Headers: optional `Ocp-Apim-Subscription-Key`.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| subscription-key | string | Subscription key. | opaque | `AbCdEf1234567890` |
| typeCode | string | Record type. | `C`, `S` | `C` |
| freqCode | string | Time granularity. | `A`, `M` | `A` |
| clCode | string | Product classification. | `HS`, `H0`–`H6`, `S1`–`S4`, `SS`, `B4`, `B5`, `EB02`, `EB10`, `EB10S`, `EB` | `HS` |
| reporterCode | string | Reporting country. | any value from M2 | `699` |
| period | string | Reference period. | `YYYY` or `YYYYMM`, comma-separated up to 12 values | `2022` |
| flowCode | string | Trade flow. | any value from M10 | `X` |
| cmdCode | string | Commodity code. | any value from the chosen classification, or `TOTAL` | `TOTAL` |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| partnerCode | string | none | Partner country. | `0`, `842` |
| partner2Code | string | none | Secondary partner. | `156` |
| customsCode | string | `C00` | Customs procedure code. | `C00` |
| motCode | string | `0` | Mode of transport. | `0` |
| maxRecords | integer | 250000 | Maximum records. | `250000` |
| format | string | `JSON` | Response format. | `JSON` |
| aggregateBy | string | none | Aggregation dimension. | `cmdCode` |
| breakdownMode | string | `classic` | Breakdown style. | `classic` |
| countOnly | boolean | `false` | Return only the count. | `false` |
| includeDesc | boolean | `true` | Include descriptions. | `true` |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** Top-level keys `elapsedTime`, `count`,
  `data`, `error`.
- **Top-level fields.** `elapsedTime` (string),
  `count` (integer), `data` (array), `error` (string).
- **Nested objects.** Each record has 47 fields
  documented in `004_API_RESEARCH.md` §6.2.

### Pagination

- **Supported.** Not supported via a documented
  continuation token.
- **Maximum page size.** 250,000.
- **Continuation tokens.** None.
- **Limits.** A larger result set SHALL be split across
  multiple calls by period, or SHALL use the async
  delivery (A1) or bulk download (A2).

### Rate Limiting

- **Known limits.** 50,000,000 records per day for the
  free tier; per-minute cap is unverified.
- **Observed limits.** Unverified.

### Typical Use Cases

- Retrieve a full year of a reporter's exports.
- Retrieve monthly data for a single commodity.
- Retrieve the world total for a reporter.

### SDK Wrapper

- `un_comtrade.trade.get_final(...)`
- `un_comtrade.trade.get_annual(...)`
- `un_comtrade.trade.get_monthly(...)`

### Dependencies

- A valid subscription key.
- The classification chosen in `clCode` SHALL have been
  loaded (M4–M8).

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 200 (count=0) | No records match the query. | Broaden the query. | No. |
| 401 | Key is missing or invalid. | Provide a valid key. | No. |
| 429 | Rate limit exceeded. | Wait and retry. | Yes, with backoff. |
| 5xx | Upstream failure. | Retry. | Yes, with backoff. |

### Performance Notes

- Typical latency: 0.30 to 3.00 seconds.
- A 250,000-record call may take 5 to 30 seconds
  depending on the query.
- Recommended SDK default timeout: 60 seconds.

### Known Limitations

- The record cap is 250,000 per call. Larger extracts
  require async delivery or bulk download.
- The endpoint is documented but not exercised in this
  research.

### Verification Status

Documented.

### Documentation References

- `004_API_RESEARCH.md`, §3.3, §4.18, §11.5.
- `uncomtrade.org/docs/data/`.

---

## T2 — Trade Matrix

### HTTP Method

GET.

### Endpoint Path

`/data/v1/getTradeMatrix/{typeCode}/{freqCode}/TM`

### Base URL

`https://comtradeapi.un.org`

### Category

Trade.

### Purpose

Returns trade matrix data — official trade values
complemented by estimates, including the harmonised
world export matrix. The `clCode` is fixed at `TM`.

### SDK Priority

Medium.

### Authentication

Subscription Key.

### Request Format

- Path parameters: `typeCode`, `freqCode`, `TM`.
- Query parameters: as T1.
- Headers: optional `Ocp-Apim-Subscription-Key`.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| subscription-key | string | Subscription key. | opaque | `AbCdEf1234567890` |
| typeCode | string | Record type. | `C`, `S` | `C` |
| freqCode | string | Time granularity. | `A`, `M` | `A` |
| period | string | Reference period. | `YYYY` or `YYYYMM` | `2022` |
| flowCode | string | Trade flow. | any value from M10 | `X` |
| cmdCode | string | Commodity code, may be `ag1`–`ag5` for SITC sections. | any value from the chosen classification, or `ag1` | `ag1` |
| reporterCode | string | Reporting country. | any value from M2 | `0` |
| partnerCode | string | Partner country. | any value from M3 | `0` |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| maxRecords | integer | 250000 | Maximum records. | `250000` |
| format | string | `JSON` | Response format. | `JSON` |
| aggregateBy | string | none | Aggregation dimension. | `cmdCode` |
| countOnly | boolean | `false` | Return only the count. | `false` |
| includeDesc | boolean | `true` | Include descriptions. | `true` |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** As T1.
- **Top-level fields.** As T1.
- **Nested objects.** As T1.

### Pagination

- **Supported.** Not supported.
- **Maximum page size.** 250,000.

### Rate Limiting

- **Known limits.** As T1.
- **Observed limits.** Unverified.

### Typical Use Cases

- Retrieve the world export matrix.
- Retrieve a one-digit SITC section across all
  reporters.

### SDK Wrapper

- `un_comtrade.trade.get_trade_matrix(...)`

### Dependencies

- A valid subscription key.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 401 | Key is missing or invalid. | Provide a valid key. | No. |
| 429 | Rate limit exceeded. | Wait and retry. | Yes, with backoff. |
| 5xx | Upstream failure. | Retry. | Yes, with backoff. |

### Performance Notes

- Typical latency: 0.50 to 5.00 seconds.
- A matrix call may return a large number of records.

### Known Limitations

- The endpoint is documented but not exercised in this
  research.

### Verification Status

Documented.

### Documentation References

- `004_API_RESEARCH.md`, §3.3, §4.20, §11.6.

---

## T3 — Trade Balance

### HTTP Method

GET.

### Endpoint Path

`/tools/v1/getTradeBalance/{typeCode}/{freqCode}/{clCode}`

### Base URL

`https://comtradeapi.un.org`

### Category

Trade.

### Purpose

Returns exports and imports laid out side by side for
the same query. The consumer receives both the export
record and the import record in a single response.

### SDK Priority

Medium.

### Authentication

Subscription Key.

### Request Format

- Path parameters: `typeCode`, `freqCode`, `clCode`.
- Query parameters: as T1, except `flowCode` is
  omitted (the endpoint produces both directions).
- Headers: optional `Ocp-Apim-Subscription-Key`.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| subscription-key | string | Subscription key. | opaque | `AbCdEf1234567890` |
| typeCode | string | Record type. | `C`, `S` | `C` |
| freqCode | string | Time granularity. | `A`, `M` | `A` |
| clCode | string | Product classification. | as T1 | `HS` |
| reporterCode | string | Reporting country. | any value from M2 | `699` |
| period | string | Reference period. | `YYYY` or `YYYYMM` | `2022` |
| cmdCode | string | Commodity code. | any value, or `TOTAL` | `TOTAL` |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| partnerCode | string | none | Partner country. | `0` |
| partner2Code | string | none | Secondary partner. | `156` |
| customsCode | string | `C00` | Customs procedure code. | `C00` |
| motCode | string | `0` | Mode of transport. | `0` |
| maxRecords | integer | 250000 | Maximum records. | `250000` |
| format | string | `JSON` | Response format. | `JSON` |
| breakdownMode | string | `classic` | Breakdown style. | `classic` |
| includeDesc | boolean | `true` | Include descriptions. | `true` |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** As T1.
- **Top-level fields.** As T1.
- **Nested objects.** Each record carries both the
  export and the import value for the same query.

### Pagination

- **Supported.** Not supported.
- **Maximum page size.** 250,000.

### Rate Limiting

- **Known limits.** As T1.
- **Observed limits.** Unverified.

### Typical Use Cases

- Compute the trade balance for a reporter in a
  single call.

### SDK Wrapper

- `un_comtrade.trade.get_trade_balance(...)`

### Dependencies

- A valid subscription key.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 401 | Key is missing or invalid. | Provide a valid key. | No. |
| 429 | Rate limit exceeded. | Wait and retry. | Yes, with backoff. |
| 5xx | Upstream failure. | Retry. | Yes, with backoff. |

### Performance Notes

- Typical latency: 0.50 to 3.00 seconds.

### Known Limitations

- The endpoint is documented but not exercised in this
  research.
- 401 verified for missing key; the body and shape of
  successful responses are documented.

### Verification Status

Verified (401 path). Documented for the rest.

### Documentation References

- `004_API_RESEARCH.md`, §3.4, §4.21, §11.6.

---

## T4 — Bilateral Data

### HTTP Method

GET.

### Endpoint Path

`/tools/v1/getBilateralData/{typeCode}/{freqCode}/{clCode}`

### Base URL

`https://comtradeapi.un.org`

### Category

Trade.

### Purpose

Returns reported data complemented by mirror partner
data. The consumer receives the value reported by the
reporter and the value reported by the partner; the two
values are reconciled in the response.

### SDK Priority

Low.

### Authentication

Subscription Key.

### Request Format

- Path parameters: `typeCode`, `freqCode`, `clCode`.
- Query parameters: as T1.
- Headers: optional `Ocp-Apim-Subscription-Key`.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| subscription-key | string | Subscription key. | opaque | `AbCdEf1234567890` |
| typeCode | string | Record type. | `C`, `S` | `C` |
| freqCode | string | Time granularity. | `A`, `M` | `A` |
| clCode | string | Product classification. | as T1 | `HS` |
| reporterCode | string | Reporting country. | any value from M2 | `699` |
| period | string | Reference period. | `YYYY` or `YYYYMM` | `2022` |
| cmdCode | string | Commodity code. | any value, or `TOTAL` | `TOTAL` |
| flowCode | string | Trade flow. | any value from M10 | `X` |
| partnerCode | string | Partner country. | any value from M3 | `0` |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| maxRecords | integer | 250000 | Maximum records. | `250000` |
| format | string | `JSON` | Response format. | `JSON` |
| includeDesc | boolean | `true` | Include descriptions. | `true` |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** As T1.
- **Top-level fields.** As T1.
- **Nested objects.** Each record carries both the
  reported value and the mirror value, with
  reconciliation metadata.

### Pagination

- **Supported.** Not supported.
- **Maximum page size.** 250,000.

### Rate Limiting

- **Known limits.** As T1.
- **Observed limits.** Unverified.

### Typical Use Cases

- Reconcile reported exports against mirror imports.
- Detect bilateral asymmetries.

### SDK Wrapper

- `un_comtrade.trade.get_bilateral(...)`

### Dependencies

- A valid subscription key.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 401 | Key is missing or invalid. | Provide a valid key. | No. |
| 429 | Rate limit exceeded. | Wait and retry. | Yes, with backoff. |
| 5xx | Upstream failure. | Retry. | Yes, with backoff. |

### Performance Notes

- Typical latency: 0.50 to 3.00 seconds.

### Known Limitations

- The endpoint is documented but not exercised in this
  research.
- 401 verified for missing key.

### Verification Status

Verified (401 path). Documented for the rest.

### Documentation References

- `004_API_RESEARCH.md`, §3.4, §4.22, §11.6.

---

# Preview

The public preview endpoints are documented below.
Every preview endpoint is unauthenticated, returns up to
500 records per call, and is case-sensitive on
`reportercode` (all lowercase).

---

## P1 — Public Preview, Final Data

### HTTP Method

GET.

### Endpoint Path

`/public/v1/preview/{typeCode}/{freqCode}/{clCode}`

### Base URL

`https://comtradeapi.un.org`

### Category

Preview.

### Purpose

Returns up to 500 final trade data records without a
key. The endpoint is the primary unauthenticated
surface for ad-hoc queries and for first-look
exploration. The endpoint uses the lowercase parameter
name `reportercode`; the casing is the documented quirk
of the preview surface.

### SDK Priority

High.

### Authentication

Public.

### Request Format

- Path parameters: `typeCode`, `freqCode`, `clCode`.
- Query parameters: as T1, but with `reportercode`
  (lowercase) and without `subscription-key`.
- Headers: none.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| typeCode | string | Record type. | `C`, `S` | `C` |
| freqCode | string | Time granularity. | `A`, `M` | `A` |
| clCode | string | Product classification. | as T1 | `HS` |
| reportercode | string | Reporting country (lowercase). | any value from M2 | `699` |
| period | string | Reference period. | `YYYY` or `YYYYMM`, up to 12 values | `2022` |
| flowCode | string | Trade flow. | any value from M10 | `X` |
| cmdCode | string | Commodity code. | any value, or `TOTAL` | `TOTAL` |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| partnerCode | string | none | Partner country. | `0`, `842` |
| partner2Code | string | none | Secondary partner. | `156` |
| customsCode | string | `C00` | Customs procedure code. | `C00` |
| motCode | string | `0` | Mode of transport. | `0` |
| maxRecords | integer | 500 | Maximum records. | `500` |
| format | string | `JSON` | Response format. | `JSON` |
| aggregateBy | string | none | Aggregation dimension. | `cmdCode` |
| breakdownMode | string | `classic` | Breakdown style. | `classic` |
| countOnly | boolean | `false` | Return only the count. | `false` |
| includeDesc | boolean | `true` | Include descriptions. | `true` |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** As T1.
- **Top-level fields.** As T1.
- **Nested objects.** As T1.

### Pagination

- **Supported.** Not supported.
- **Maximum page size.** 500.
- **Continuation tokens.** None.
- **Limits.** A larger result set SHALL be split across
  multiple period-bounded calls, or SHALL use the
  authenticated endpoint T1.

### Rate Limiting

- **Known limits.** Per-minute cap is unverified.
- **Observed limits.** Rapid requests may receive
  HTTP 429.

### Typical Use Cases

- Explore a dataset without registering.
- Quick look at a reporter's exports.
- Build an unauthenticated demo.

### SDK Wrapper

- `un_comtrade.trade.preview_final(...)`
- `un_comtrade.trade.preview_annual(...)`
- `un_comtrade.trade.preview_monthly(...)`

### Dependencies

None.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 200 (count=0) | No records match. | Broaden the query. | No. |
| 429 | Rate limit exceeded. | Wait and retry. | Yes, with backoff. |
| 5xx | Upstream failure. | Retry. | Yes, with backoff. |

### Performance Notes

- Typical latency: 0.10 to 3.00 seconds.
- A 500-record call typically completes in 1.0 to 3.0
  seconds.

### Known Limitations

- Case-sensitivity on `reportercode` (lowercase) is
  the documented quirk.
- 500-record cap.
- CORS is not supported; the endpoint SHALL NOT be
  called from a browser context.

### Verification Status

Verified.

### Documentation References

- `004_API_RESEARCH.md`, §3.2, §4.16, §11.1, §11.3.

---

## P2 — Public Preview, Tariffline Data

### HTTP Method

GET.

### Endpoint Path

`/public/v1/previewTariffline/{typeCode}/{freqCode}/{clCode}`

### Base URL

`https://comtradeapi.un.org`

### Category

Preview.

### Purpose

Returns up to 500 tariffline trade data records
without a key. The endpoint is the line-level
counterpart of P1 and provides finer-grained records
than the final data.

### SDK Priority

Medium.

### Authentication

Public.

### Request Format

- Path parameters: `typeCode`, `freqCode`, `clCode`.
- Query parameters: as P1.
- Headers: none.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| typeCode | string | Record type. | `C`, `S` | `C` |
| freqCode | string | Time granularity. | `A`, `M` | `A` |
| clCode | string | Product classification. | as T1 | `HS` |
| reportercode | string | Reporting country (lowercase). | any value from M2 | `699` |
| period | string | Reference period. | `YYYY` or `YYYYMM`, up to 12 values | `2022` |
| flowCode | string | Trade flow. | any value from M10 | `X` |
| cmdCode | string | Commodity code. | any value, or `TOTAL` | `TOTAL` |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| partnerCode | string | none | Partner country. | `0`, `842` |
| partner2Code | string | none | Secondary partner. | `156` |
| customsCode | string | `C00` | Customs procedure code. | `C00` |
| motCode | string | `0` | Mode of transport. | `0` |
| maxRecords | integer | 500 | Maximum records. | `500` |
| countOnly | boolean | `false` | Return only the count. | `false` |
| includeDesc | boolean | `true` | Include descriptions. | `true` |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** As T1.
- **Top-level fields.** As T1.
- **Nested objects.** Each record has the 47 fields
  of T1.

### Pagination

- **Supported.** Not supported.
- **Maximum page size.** 500.

### Rate Limiting

- **Known limits.** As P1.
- **Observed limits.** Unverified.

### Typical Use Cases

- Quick look at a reporter's tariffline data.
- Build an unauthenticated demo of line-level data.

### SDK Wrapper

- `un_comtrade.trade.preview_tariffline(...)`

### Dependencies

None.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 200 (count=0) | No records match. | Broaden the query. | No. |
| 429 | Rate limit exceeded. | Wait and retry. | Yes, with backoff. |
| 5xx | Upstream failure. | Retry. | Yes, with backoff. |

### Performance Notes

- Typical latency: 0.20 to 3.00 seconds.

### Known Limitations

- 500-record cap.
- CORS is not supported.

### Verification Status

Verified (URL structure and parameter set). A full
record has not been retrieved in this research.

### Documentation References

- `004_API_RESEARCH.md`, §3.2, §4.17, §11.1, §11.4.

---

# Tariff

---

## F1 — Authenticated Tariffline Data

### HTTP Method

GET.

### Endpoint Path

`/data/v1/getTariffline/{typeCode}/{freqCode}/{clCode}`

### Base URL

`https://comtradeapi.un.org`

### Category

Tariff.

### Purpose

Returns up to 250,000 tariffline trade data records
in a single call. The endpoint is the line-level
counterpart of T1 and provides finer-grained records
than the final data.

### SDK Priority

Medium.

### Authentication

Subscription Key.

### Request Format

- Path parameters: `typeCode`, `freqCode`, `clCode`.
- Query parameters: as T1, without `aggregateBy` and
  without `breakdownMode` (not applicable to
  tariffline data).
- Headers: optional `Ocp-Apim-Subscription-Key`.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| subscription-key | string | Subscription key. | opaque | `AbCdEf1234567890` |
| typeCode | string | Record type. | `C`, `S` | `C` |
| freqCode | string | Time granularity. | `A`, `M` | `A` |
| clCode | string | Product classification. | as T1 | `HS` |
| reporterCode | string | Reporting country. | any value from M2 | `699` |
| period | string | Reference period. | `YYYY` or `YYYYMM`, up to 12 values | `2022` |
| flowCode | string | Trade flow. | any value from M10 | `X` |
| cmdCode | string | Commodity code. | any value, or `TOTAL` | `TOTAL` |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| partnerCode | string | none | Partner country. | `0`, `842` |
| partner2Code | string | none | Secondary partner. | `156` |
| customsCode | string | `C00` | Customs procedure code. | `C00` |
| motCode | string | `0` | Mode of transport. | `0` |
| maxRecords | integer | 250000 | Maximum records. | `250000` |
| format | string | `JSON` | Response format. | `JSON` |
| countOnly | boolean | `false` | Return only the count. | `false` |
| includeDesc | boolean | `true` | Include descriptions. | `true` |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** As T1.
- **Top-level fields.** As T1.
- **Nested objects.** Each record has the 47 fields
  of T1.

### Pagination

- **Supported.** Not supported.
- **Maximum page size.** 250,000.

### Rate Limiting

- **Known limits.** As T1.
- **Observed limits.** Unverified.

### Typical Use Cases

- Retrieve a full year of a reporter's tariffline
  exports.
- Retrieve monthly tariffline data for a single
  commodity.

### SDK Wrapper

- `un_comtrade.trade.get_tariffline(...)`
- `un_comtrade.trade.get_tariffline_annual(...)`
- `un_comtrade.trade.get_tariffline_monthly(...)`

### Dependencies

- A valid subscription key.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 401 | Key is missing or invalid. | Provide a valid key. | No. |
| 429 | Rate limit exceeded. | Wait and retry. | Yes, with backoff. |
| 5xx | Upstream failure. | Retry. | Yes, with backoff. |

### Performance Notes

- Typical latency: 0.50 to 5.00 seconds.
- A 250,000-record call may take 5 to 30 seconds.

### Known Limitations

- The endpoint is documented but not exercised in this
  research.

### Verification Status

Documented.

### Documentation References

- `004_API_RESEARCH.md`, §3.3, §4.19, §11.1, §11.4.

---

# Utility

---

## U1 — Standard Unit Value

### HTTP Method

GET.

### Endpoint Path

Documented by `comtradeapicall`; not exercised in this
research.

### Base URL

`https://comtradeapi.un.org`

### Category

Utility.

### Purpose

Returns reference Standard Unit Value (SUV) and
range data for a commodity. The result is a
diagnostic value used to detect price outliers in a
trade record.

### SDK Priority

Low.

### Authentication

Subscription Key.

### Request Format

- Path parameters: documented by `comtradeapicall`.
- Query parameters: documented by `comtradeapicall`.
- Headers: optional `Ocp-Apim-Subscription-Key`.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| subscription-key | string | Subscription key. | opaque | `AbCdEf1234567890` |
| period | string | Reference period. | `YYYY` | `2022` |
| cmdCode | string | Commodity code. | any value from the chosen classification | `010391` |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| flowCode | string | none | Trade flow filter. | `X` |
| qtyUnitCode | integer | 8 | Quantity unit code. | `8` |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** Documented by `comtradeapicall`; not
  exercised in this research.
- **Top-level fields.** Documented.
- **Nested objects.** Documented.

### Pagination

- **Supported.** Not supported.

### Rate Limiting

- **Known limits.** As T1.
- **Observed limits.** Unverified.

### Typical Use Cases

- Detect price outliers in a trade record.
- Drive a data-quality dashboard.

### SDK Wrapper

- `un_comtrade.trade.get_standard_unit_value(...)`

### Dependencies

- A valid subscription key.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 401 | Key is missing or invalid. | Provide a valid key. | No. |
| 429 | Rate limit exceeded. | Wait and retry. | Yes, with backoff. |
| 5xx | Upstream failure. | Retry. | Yes, with backoff. |

### Performance Notes

- Typical latency: 0.30 to 1.00 seconds.

### Known Limitations

- The endpoint is documented but not exercised in this
  research.

### Verification Status

Documented.

### Documentation References

- `004_API_RESEARCH.md`, §3.5, §4.26.

---

## U2 — Publication Notes and Metadata

### HTTP Method

GET.

### Endpoint Path

Documented by `comtradeapicall`; not exercised in this
research.

### Base URL

`https://comtradeapi.un.org`

### Category

Utility.

### Purpose

Returns publication notes and per-release metadata.
The endpoint records the publication version of a
captured dataset and is used to tag stored data with
its provenance.

### SDK Priority

Medium.

### Authentication

Subscription Key.

### Request Format

- Path parameters: documented by `comtradeapicall`.
- Query parameters: documented by `comtradeapicall`.
- Headers: optional `Ocp-Apim-Subscription-Key`.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| subscription-key | string | Subscription key. | opaque | `AbCdEf1234567890` |
| typeCode | string | Record type. | `C`, `S` | `C` |
| freqCode | string | Time granularity. | `A`, `M` | `A` |
| clCode | string | Product classification. | as T1 | `HS` |
| period | string | Reference period. | `YYYY` or `YYYYMM` | `2022` |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| reporterCode | string | none | Reporting country. | `699` |
| showHistory | boolean | `false` | Return history. | `true` |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** Documented by `comtradeapicall`; not
  exercised in this research.

### Pagination

- **Supported.** Not supported.

### Rate Limiting

- **Known limits.** As T1.
- **Observed limits.** Unverified.

### Typical Use Cases

- Capture the publication version of a dataset.
- Drive a data-provenance dashboard.

### SDK Wrapper

- `un_comtrade.trade.get_publication_notes(...)`

### Dependencies

- A valid subscription key.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 401 | Key is missing or invalid. | Provide a valid key. | No. |
| 429 | Rate limit exceeded. | Wait and retry. | Yes, with backoff. |
| 5xx | Upstream failure. | Retry. | Yes, with backoff. |

### Performance Notes

- Typical latency: 0.30 to 1.00 seconds.

### Known Limitations

- The endpoint is documented but not exercised in this
  research.

### Verification Status

Documented.

### Documentation References

- `004_API_RESEARCH.md`, §3.5, §4.27.

---

# Administrative

The administrative endpoints are documented below.
Every administrative endpoint requires a subscription
key. The endpoints are designed for large extracts and
for capacity planning.

---

## D1 — Data Availability

### HTTP Method

GET.

### Endpoint Path

Documented by `comtradeapicall` as
`getFinalDataAvailability` and
`getTarifflineDataAvailability`. The exact URL is
unverified in this research.

### Base URL

`https://comtradeapi.un.org`

### Category

Administrative.

### Purpose

Enumerates the data currently available, by reporter
and period. Used to size a query before issuing it.

### SDK Priority

Medium.

### Authentication

Subscription Key.

### Request Format

- Path parameters: documented by `comtradeapicall`.
- Query parameters: documented by `comtradeapicall`.
- Headers: optional `Ocp-Apim-Subscription-Key`.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| subscription-key | string | Subscription key. | opaque | `AbCdEf1234567890` |
| typeCode | string | Record type. | `C`, `S` | `C` |
| freqCode | string | Time granularity. | `A`, `M` | `A` |
| clCode | string | Product classification. | as T1 | `HS` |
| period | string | Reference period. | `YYYY` or `YYYYMM` | `2022` |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| reporterCode | string | none | Reporting country. | `699` |
| publishedDateFrom | string | none | Filter by publication date. | `2024-01-01` |
| publishedDateTo | string | none | Filter by publication date. | `2024-12-31` |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** Documented by `comtradeapicall`; not
  exercised in this research.

### Pagination

- **Supported.** Not supported.

### Rate Limiting

- **Known limits.** As T1.
- **Observed limits.** Unverified.

### Typical Use Cases

- Discover what is currently available before issuing
  a large query.

### SDK Wrapper

- `un_comtrade.trade.get_data_availability(...)`

### Dependencies

- A valid subscription key.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 401 | Key is missing or invalid. | Provide a valid key. | No. |
| 404 | The endpoint URL is not known. | Verify the URL against the SDK specification. | No. |
| 429 | Rate limit exceeded. | Wait and retry. | Yes, with backoff. |
| 5xx | Upstream failure. | Retry. | Yes, with backoff. |

### Performance Notes

- Typical latency: 0.30 to 1.00 seconds.

### Known Limitations

- The URL path is **unverified** at the date of this
  document. The four URL patterns probed during the
  research all returned 404 without a key.
- The endpoint is exercised by the official
  `comtradeapicall` package; the URL pattern SHALL be
  verified before the SDK exposes it.

### Verification Status

Unverified.

### Documentation References

- `004_API_RESEARCH.md`, §3.5, §4.25.

---

## D2 — Async Submit, Status, and Download

### HTTP Method

GET (and POST for submit, per the official
`comtradeapicall` package).

### Endpoint Path

Documented by `comtradeapicall` as
`submitAsyncFinalDataRequest`,
`checkAsyncDataRequest`,
`downloadAsyncFinalDataRequest`, and corresponding
tariffline variants. The exact URLs are not exercised
in this research.

### Base URL

`https://comtradeapi.un.org`

### Category

Administrative.

### Purpose

Submits, polls, and downloads a long-running data
request that exceeds the 250,000-record cap of T1.
The cap of the async delivery is 2,500,000 records.
The submit call returns a handle; the poll call returns
the status; the download call returns the result.

### SDK Priority

Medium.

### Authentication

Subscription Key.

### Request Format

- Path parameters: documented by `comtradeapicall`.
- Query parameters: documented by `comtradeapicall`.
- Headers: optional `Ocp-Apim-Subscription-Key`.
- Request body: for the submit call only, the body
  contains the query parameters.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| subscription-key | string | Subscription key. | opaque | `AbCdEf1234567890` |
| (submit) | object | The query descriptor. | as T1 | n/a |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| (poll) batchId | string | none | The handle returned by the submit. | UUID |

### Response

- **Response Type.** Application/JSON.
- **Content Type.** `application/json`.
- **Structure.** Documented by `comtradeapicall`; not
  exercised in this research.
- **Top-level fields.** The submit response includes
  `requestId`; the poll response includes the status;
  the download response is a JSON file.

### Pagination

- **Supported.** Not supported.
- **Maximum page size.** 2,500,000 per async delivery.

### Rate Limiting

- **Known limits.** As T1.
- **Observed limits.** Unverified.

### Typical Use Cases

- Retrieve a multi-year, multi-reporter extract that
  exceeds 250,000 records.

### SDK Wrapper

- `un_comtrade.trade.submit_async_request(...)`
- `un_comtrade.trade.check_async_request(...)`
- `un_comtrade.trade.download_async_request(...)`

### Dependencies

- A valid subscription key.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 401 | Key is missing or invalid. | Provide a valid key. | No. |
| 429 | Rate limit exceeded. | Wait and retry. | Yes, with backoff. |
| 5xx | Upstream failure. | Retry. | Yes, with backoff. |

### Performance Notes

- Submit latency: 0.30 to 1.00 seconds.
- Poll latency: 0.10 to 0.30 seconds.
- Download latency depends on the result size.

### Known Limitations

- The endpoints are documented but not exercised in
  this research.

### Verification Status

Documented.

### Documentation References

- `004_API_RESEARCH.md`, §3.5, §4.23.

---

## D3 — Bulk Download

### HTTP Method

GET.

### Endpoint Path

Documented by `comtradeapicall` as
`bulkDownloadFinalFile` and corresponding variants.
The exact URLs are not exercised in this research.

### Base URL

`https://comtradeapi.un.org`

### Category

Administrative.

### Purpose

Downloads the pre-built bulk data files. The bulk
files are the most efficient way to load large volumes
of data. The download is to a directory configured by
the consumer.

### SDK Priority

Medium.

### Authentication

Subscription Key.

### Request Format

- Path parameters: documented by `comtradeapicall`.
- Query parameters: documented by `comtradeapicall`.
- Headers: optional `Ocp-Apim-Subscription-Key`.
- Request body: none.

### Required Parameters

| Name | Datatype | Description | Allowed Values | Example |
| ---- | -------- | ----------- | -------------- | ------- |
| subscription-key | string | Subscription key. | opaque | `AbCdEf1234567890` |
| typeCode | string | Record type. | `C`, `S` | `C` |
| freqCode | string | Time granularity. | `A`, `M` | `A` |
| clCode | string | Product classification. | as T1 | `HS` |
| period | string | Reference period. | `YYYY` or `YYYYMM` | `2022` |
| reporterCode | string | Reporting country. | any value from M2 | `699` |

### Optional Parameters

| Name | Datatype | Default | Description | Example |
| ---- | -------- | ------- | ----------- | ------- |
| publishedDateFrom | string | none | Filter by publication date. | `2024-01-01` |
| publishedDateTo | string | none | Filter by publication date. | `2024-12-31` |

### Response

- **Response Type.** Binary file.
- **Content Type.** `application/octet-stream` (or
  `application/zip` if compressed).
- **Structure.** A single file written to the
  configured directory.

### Pagination

- **Supported.** Not supported.

### Rate Limiting

- **Known limits.** As T1.
- **Observed limits.** Unverified.

### Typical Use Cases

- Load a year's worth of tariffline data for a
  reporter.
- Load the full history of a reporter's exports.

### SDK Wrapper

- `un_comtrade.trade.bulk_download_final_file(...)`
- `un_comtrade.trade.bulk_download_tariffline_file(...)`

### Dependencies

- A valid subscription key.
- A configured download directory.

### Error Responses

| HTTP Status | Meaning | Recovery | Retry |
| ----------- | ------- | -------- | ----- |
| 401 | Key is missing or invalid. | Provide a valid key. | No. |
| 404 | The bulk file is not available. | Verify the query. | No. |
| 429 | Rate limit exceeded. | Wait and retry. | Yes, with backoff. |
| 5xx | Upstream failure. | Retry. | Yes, with backoff. |

### Performance Notes

- Download latency depends on the file size. Bulk
  files can be hundreds of megabytes.

### Known Limitations

- The four URL patterns probed during the research
  returned 404 without a key. The URL pattern SHALL be
  verified before the SDK exposes it.

### Verification Status

Documented.

### Documentation References

- `004_API_RESEARCH.md`, §3.5, §4.24.

---

# Deprecated

No endpoints are marked as deprecated at the date of
this document. The section is reserved for future
deprecations.

---

# End of document
