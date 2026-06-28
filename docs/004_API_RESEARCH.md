```
Document ID
004

Title
UN Comtrade API Specification & Research

Version
0.1.0

Status
DRAFT

Created
2026-06-26T19:56:43Z

Last Updated
2026-06-26T19:56:43Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
000_PROJECT_CHARTER.md
001_EXECUTION_PROTOCOL.md
002_CONTEXT.md
003_ARCHITECTURE.md

Supersedes
None
```

---

# 1. API Overview

## 1.1 API purpose

The UN Comtrade API is the programmatic interface to the
United Nations Comtrade Database, the official international
merchandise trade statistics of the United Nations Statistics
Division. The API exposes reference catalogues, trade
records, bulk data files, and tooling endpoints through a
JSON-over-HTTPS interface operated on an Azure API Management
gateway.

## 1.2 API versions

The API is exposed at URL path `v1` for both the public
preview surface (`/public/v1`) and the subscription-backed
data surface (`/data/v1`). The path-version is encoded in
the URL. There is no header-based version negotiation at the
date of this document.

The versioned URL pattern means the SDK MAY load a different
URL prefix in a future release without changing the layer
responsibilities, by adjusting the transport configuration.

## 1.3 Public API

The public preview surface is reachable at
`https://comtradeapi.un.org/public/v1/...`. It does not
require a subscription key. It is rate-limited and capped at
500 records per call. It is the documented surface for ad-hoc
queries and for first-look exploration.

## 1.4 Authenticated API

The subscription-backed surface is reachable at
`https://comtradeapi.un.org/data/v1/...` for data and
`https://comtradeapi.un.org/tools/v1/...` for tooling. It
requires a subscription key issued by the developer portal.
The cap per call is 250,000 records. Bulk download endpoints
also live behind the subscription key.

## 1.5 Base URLs

- Public preview: `https://comtradeapi.un.org/public/v1`
- Authenticated data: `https://comtradeapi.un.org/data/v1`
- Authenticated tools: `https://comtradeapi.un.org/tools/v1`
- Reference catalogues: `https://comtradeapi.un.org/files/v1/app/reference`

## 1.6 Current documentation location

The user-facing documentation lives at
`https://uncomtrade.org/docs/` and at the developer portal
`https://comtradedeveloper.un.org/apis`. The reference
catalogue is published as JSON files at
`https://comtradeapi.un.org/files/v1/app/reference/`.

## 1.7 Stability

The URL structure, the parameter names on the preview
endpoint, and the response schema are stable. The schema
documented in this research document has been verified by
live requests on the date recorded in the metadata block.

---

# 2. Authentication

## 2.1 Authentication methods

The UN Comtrade API supports a single authentication method:
a subscription key. The key is a long opaque string issued by
the developer portal at
`https://comtradedeveloper.un.org/profile`. The key is
associated with a tier; the free tier and the premium tier
share the same key-issuance flow.

The reference endpoints (catalogue JSON files) do not
require a subscription key. Every other endpoint in scope
on the data and tools surfaces requires a key.

## 2.2 Public access

The public preview endpoints at `/public/v1/...` are open.
They enforce a 500-record cap and a rate limit. They do not
require a key and do not accept a key. They are not a
replacement for the authenticated endpoints; they are a
preview.

## 2.3 Subscription keys

A subscription key is obtained by:

1. Creating a free account on `https://comtrade.un.org/`.
2. Signing in to the developer portal at
   `https://comtradedeveloper.un.org/`.
3. Subscribing to the **Free APIs** product.
4. Reading the issued key from the profile page.

The key is a personal secret. The key is associated with
the user, not with a particular application. The key may be
rotated through the same flow.

## 2.4 Header and query requirements

The subscription key is accepted in two locations, both of
which are verified.

- **Query parameter** `subscription-key` (lowercase,
  hyphenated). Verified by live request.
- **HTTP header** `Ocp-Apim-Subscription-Key` (Azure API
  Management convention). Documented behaviour.

The query parameter is the form exercised by the official
`comtradeapicall` Python package and is the form recommended
for the SDK.

## 2.5 Authentication workflow

A typical authenticated call is the sequence below. The
sequence has been verified by live request.

1. Construct the request URL with the documented path.
2. Append the query parameters, including `subscription-key`.
3. Issue a GET request.
4. Parse the JSON response.
5. Inspect the `elapsedTime`, `count`, `data`, and `error`
   fields.

## 2.6 Expiration

Key expiration is governed by the developer portal. The
expiration interval is **Unverified** at the date of this
document. The behaviour of an expired key is **Verified**:
the API returns HTTP 401 with the message `Access denied
due to invalid subscription key. Make sure to provide a
valid key for an active subscription.`

## 2.7 Limitations

- The key is sent in the URL on every request. A consumer
  who logs the full URL will leak the key. The SDK SHALL
  redact the key from logged URLs.
- A 401 response does not distinguish between an invalid
  key, an expired key, and a key whose subscription is
  suspended. The SDK SHALL treat all three identically.
- There is no documented rate-limit-per-key value. The
  rate-limit is **Unverified** at the date of this
  document.

## 2.8 Security considerations

- The key SHALL be held in memory only and SHALL NOT be
  written to disk except through the storage layer under
  the documented configuration category.
- The key SHALL NOT be logged in plain text.
- The key SHALL NOT be included in error messages.
- The key SHALL be accepted through environment variables,
  configuration objects, or explicit construction
  arguments. The key SHALL NOT be read from a file by
  default.

---

# 3. Endpoint Inventory

The endpoint inventory is the canonical list of endpoints
that the SDK intends to support. Each endpoint is assigned
a verification status. The statuses are defined in
section "Verification Rules" of this document.

## 3.1 Reference catalogue endpoints

| ID  | Endpoint                                                                 | Auth | Status      |
| --- | ------------------------------------------------------------------------ | ---- | ----------- |
| E1  | `GET /files/v1/app/reference/ListofReferences.json`                      | No   | Verified    |
| E2  | `GET /files/v1/app/reference/Reporters.json`                             | No   | Verified    |
| E3  | `GET /files/v1/app/reference/partnerAreas.json`                          | No   | Verified    |
| E4  | `GET /files/v1/app/reference/HS.json` (combined HS)                      | No   | Verified    |
| E5  | `GET /files/v1/app/reference/H0.json` through `H6.json` (per edition)    | No   | Documented  |
| E6  | `GET /files/v1/app/reference/S1.json` through `S4.json`, `SS.json`       | No   | Documented  |
| E7  | `GET /files/v1/app/reference/B4.json`, `B5.json`                         | No   | Documented  |
| E8  | `GET /files/v1/app/reference/EB02.json`, `EB10.json`, `EB10S.json`, `EB.json` | No | Documented |
| E9  | `GET /files/v1/app/reference/Frequency.json`                             | No   | Documented  |
| E10 | `GET /files/v1/app/reference/tradeRegimes.json`                          | No   | Documented  |
| E11 | `GET /files/v1/app/reference/CustomsCodes.json`                          | No   | Documented  |
| E12 | `GET /files/v1/app/reference/ModeOfTransportCodes.json`                  | No   | Documented  |
| E13 | `GET /files/v1/app/reference/ModeOfSupply.json`                          | No   | Documented  |
| E14 | `GET /files/v1/app/reference/QuantityUnits.json`                         | No   | Documented  |
| E15 | `GET /files/v1/app/reference/TradeDataItems.json`                        | No   | Documented  |

## 3.2 Trade data endpoints — public preview

| ID  | Endpoint                                                                       | Auth | Status   |
| --- | ------------------------------------------------------------------------------ | ---- | -------- |
| E16 | `GET /public/v1/preview/{typeCode}/{freqCode}/{clCode}`                        | No   | Verified |
| E17 | `GET /public/v1/previewTariffline/{typeCode}/{freqCode}/{clCode}`              | No   | Verified |

## 3.3 Trade data endpoints — authenticated

| ID  | Endpoint                                                                       | Auth | Status      |
| --- | ------------------------------------------------------------------------------ | ---- | ----------- |
| E18 | `GET /data/v1/get/{typeCode}/{freqCode}/{clCode}`                              | Yes  | Verified    |
| E19 | `GET /data/v1/getTariffline/{typeCode}/{freqCode}/{clCode}`                    | Yes  | Documented  |
| E20 | `GET /data/v1/getTradeMatrix/{typeCode}/{freqCode}/TM`                         | Yes  | Documented  |

## 3.4 Tooling endpoints — authenticated

| ID  | Endpoint                                                                       | Auth | Status      |
| --- | ------------------------------------------------------------------------------ | ---- | ----------- |
| E21 | `GET /tools/v1/getTradeBalance/{typeCode}/{freqCode}/{clCode}`                 | Yes  | Verified    |
| E22 | `GET /tools/v1/getBilateralData/{typeCode}/{freqCode}/{clCode}`                | Yes  | Verified    |

## 3.5 Out-of-scope endpoints

| ID  | Endpoint                                                                 | Auth | Status      |
| --- | ------------------------------------------------------------------------ | ---- | ----------- |
| E23 | Async submit, status, and download endpoints under `/data/v1/...`        | Yes  | Documented  |
| E24 | Bulk download endpoints under `/data/v1/...`                             | Yes  | Documented  |
| E25 | Data availability endpoints                                              | Yes  | Unverified  |
| E26 | Standard Unit Value (SUV) endpoint                                       | Yes  | Documented  |
| E27 | Metadata + publication notes endpoint                                    | Yes  | Documented  |

E25 is marked Unverified because the URL path was not
reliably identifiable in the public documentation; the
official `comtradeapicall` Python package exercises
endpoints named `getFinalDataAvailability` and
`getTarifflineDataAvailability` but the gateway returned
404 for the URL pattern probed during this research.

E23 and E24 are documented as supported by the official
`comtradeapicall` Python package; their URL patterns are
documented but were not exercised by this research because
they require a subscription key.

---

# 4. Endpoint Specifications

The specifications below document the endpoints that are
in scope. Each specification lists the parameters, the
response structure, the failure modes, and the verification
status. The specifications that have been exercised by
live request are marked **Verified**; the specifications
that have been read from the official documentation are
marked **Documented**.

## 4.1 E1 — List of reference tables

- **Purpose.** Enumerate the available reference tables.
- **Method.** GET.
- **Path.** `/files/v1/app/reference/ListofReferences.json`.
- **Required parameters.** None.
- **Optional parameters.** None.
- **Response.** A JSON object with key `results` whose value
  is an array of objects with fields `category`, `variable`,
  `description`, `fileuri`.
- **Verified result.** 28 entries returned. Verified.
- **Failure modes.** 404 if the file is missing. Otherwise
  always succeeds because the endpoint is static.
- **SDK relevance.** Used by the metadata layer to
  enumerate the catalogue; the SDK may also expose this
  list to the consumer for discoverability.

## 4.2 E2 — Reporters

- **Purpose.** Enumerate the reporter countries and areas.
- **Method.** GET.
- **Path.** `/files/v1/app/reference/Reporters.json`.
- **Required parameters.** None.
- **Response.** A JSON object with key `results` whose value
  is an array of objects with fields `id`, `text`,
  `reporterCode`, `reporterDesc`, `reporterNote`,
  `reporterCodeIsoAlpha2`, `reporterCodeIsoAlpha3`,
  `entryEffectiveDate`, `entryExpiredDate`, `isGroup`.
- **Verified result.** 255 entries returned; India is
  recorded under both `reporterCode=699` (current) and
  `reporterCode=356` (historical, `entryExpiredDate`
  `1974-12-31`).
- **Failure modes.** 404 if the file is missing.
- **SDK relevance.** Used by the metadata layer to
  resolve reporter identifiers. The SDK SHALL treat the
  current code (no expired date) as the canonical
  identifier and the expired code as a legacy
  identifier.

## 4.3 E3 — Partners

- **Purpose.** Enumerate the partner countries and areas.
- **Method.** GET.
- **Path.** `/files/v1/app/reference/partnerAreas.json`.
- **Required parameters.** None.
- **Response.** Array of partner records, similar shape to
  reporters.
- **Verified result.** 310 entries returned.
- **SDK relevance.** Used by the metadata layer to resolve
  partner identifiers, including the special partner code
  `0` (World aggregate).

## 4.4 E4 — HS combined classification

- **Purpose.** Enumerate the harmonised system codes across
  every edition.
- **Method.** GET.
- **Path.** `/files/v1/app/reference/HS.json`.
- **Response.** Array of HS records. The records are
  roughly 8,000 entries long.
- **Verified result.** 8,262 entries returned.
- **SDK relevance.** Used by the metadata layer to resolve
  HS codes. The combined list is the largest; the
  per-edition lists (H0..H6) are smaller and may be used
  when the consumer pins a specific edition.

## 4.5 E5 — HS per-edition classifications

- **Purpose.** Enumerate the harmonised system codes for a
  specific edition.
- **Method.** GET.
- **Path.** `/files/v1/app/reference/H{0..6}.json` where the
  last digit identifies the edition: `H0`=HS 1992,
  `H1`=HS 1996, `H2`=HS 2002, `H3`=HS 2007, `H4`=HS 2012,
  `H5`=HS 2017, `H6`=HS 2022.
- **Verified result.** H6 returned 6,940 entries; H5
  returned 6,709 entries.
- **SDK relevance.** Used by the metadata layer when the
  consumer pins a specific HS edition.

## 4.6 E6 — SITC classifications

- **Purpose.** Enumerate the Standard International Trade
  Classification codes.
- **Method.** GET.
- **Path.** `/files/v1/app/reference/S{1..4}.json` for
  Rev.1 through Rev.4; `/files/v1/app/reference/SS.json`
  for the combined SITC list.
- **Status.** Documented.
- **SDK relevance.** Used by the metadata layer when the
  consumer selects an SITC classification.

## 4.7 E7 — BEC classifications

- **Purpose.** Enumerate the Broad Economic Categories.
- **Method.** GET.
- **Path.** `/files/v1/app/reference/B4.json`,
  `/files/v1/app/reference/B5.json`.
- **Status.** Documented.
- **SDK relevance.** Used by the metadata layer when the
  consumer selects a BEC classification.

## 4.8 E8 — EBOPS classifications

- **Purpose.** Enumerate the Extended Balance of Payments
  Services classifications.
- **Method.** GET.
- **Path.** `/files/v1/app/reference/EB02.json`,
  `/files/v1/app/reference/EB10.json`,
  `/files/v1/app/reference/EB10S.json`,
  `/files/v1/app/reference/EB.json` (combined).
- **Status.** Documented.
- **SDK relevance.** Used by the metadata layer when the
  consumer selects an EBOPS classification; only relevant
  to `typeCode=S` (services).

## 4.9 E9 — Frequency

- **Purpose.** Enumerate the frequency codes.
- **Method.** GET.
- **Path.** `/files/v1/app/reference/Frequency.json`.
- **Verified result.** 3 entries returned (the canonical
  values are `A` annual, `M` monthly, and a sentinel value
  for the period aggregate).
- **SDK relevance.** Used by the validation layer to
  coerce and validate `freqCode`.

## 4.10 E10 — Trade flows

- **Purpose.** Enumerate the trade flow codes.
- **Method.** GET.
- **Path.** `/files/v1/app/reference/tradeRegimes.json`.
- **Verified result.** 10 entries returned.
- **SDK relevance.** Used by the validation layer to
  validate `flowCode` (`M`=import, `X`=export,
  `RX`=re-export, `RM`=re-import, plus derived codes for
  the plus-mode breakdown).

## 4.11 E11 — Customs procedure codes

- **Purpose.** Enumerate the customs procedure codes.
- **Method.** GET.
- **Path.** `/files/v1/app/reference/CustomsCodes.json`.
- **Status.** Documented.
- **SDK relevance.** Used by the validation layer to
  validate `customsCode`.

## 4.12 E12 — Mode of transport codes

- **Purpose.** Enumerate the mode of transport codes.
- **Method.** GET.
- **Path.** `/files/v1/app/reference/ModeOfTransportCodes.json`.
- **Verified result.** 18 entries returned.
- **SDK relevance.** Used by the validation layer to
  validate `motCode`.

## 4.13 E13 — Mode of supply codes

- **Purpose.** Enumerate the mode of supply codes (for
  services only).
- **Method.** GET.
- **Path.** `/files/v1/app/reference/ModeOfSupply.json`.
- **Status.** Documented.
- **SDK relevance.** Used by the validation layer to
  validate `mosCode`; only relevant to `typeCode=S`.

## 4.14 E14 — Quantity unit codes

- **Purpose.** Enumerate the quantity unit codes.
- **Method.** GET.
- **Path.** `/files/v1/app/reference/QuantityUnits.json`.
- **Verified result.** 41 entries returned.
- **SDK relevance.** Used by the normalisation layer to
  attach a human-readable unit abbreviation to a record.

## 4.15 E15 — Trade data items

- **Purpose.** Enumerate the data item (column) catalogue.
- **Method.** GET.
- **Path.** `/files/v1/app/reference/TradeDataItems.json`.
- **Verified result.** 50 entries returned.
- **SDK relevance.** Used by the normalisation layer to
  interpret every column of the response payload.

## 4.16 E16 — Public preview, final data

- **Purpose.** Return up to 500 final trade data records.
- **Method.** GET.
- **Path.** `/public/v1/preview/{typeCode}/{freqCode}/{clCode}`.
- **Required parameters.** `reportercode`, `period`,
  `flowCode` (for final data), `cmdCode`.
- **Optional parameters.** `partnerCode`, `partner2Code`,
  `customsCode`, `motCode`, `maxRecords` (default 500,
  hard cap 500), `format=JSON`, `aggregateBy`,
  `breakdownMode` (default `classic`), `countOnly`,
  `includeDesc` (default `true`).
- **Case-sensitivity quirk (Verified).** The preview
  endpoint is case-sensitive on `reportercode` (all
  lowercase). The authenticated endpoint accepts
  `reporterCode` (camelCase). The same parameter set is
  accepted but the casing differs.
- **Response.** JSON object with `elapsedTime` (string),
  `count` (integer), `data` (array of record objects),
  `error` (string, empty on success).
- **Verified record shape.** 47 fields, listed in
  section 6.
- **Failure modes.** 200 with `count=0` when no record
  matches; never a 4xx for a syntactically valid query
  that returns no data.
- **SDK relevance.** Used by the metadata and trade
  layers when the consumer has not configured a
  subscription key, or as a quick exploratory query.

## 4.17 E17 — Public preview, tariffline data

- **Purpose.** Return up to 500 tariffline trade data
  records.
- **Method.** GET.
- **Path.** `/public/v1/previewTariffline/{typeCode}/{freqCode}/{clCode}`.
- **Parameters.** As E16, with no `aggregateBy` or
  `breakdownMode` (not applicable to tariffline data).
- **Status.** Verified (URL structure); a full record
  has not been retrieved in this research.
- **SDK relevance.** Used by the trade layer when the
  consumer requests line-level records without a key.

## 4.18 E18 — Authenticated final data

- **Purpose.** Return up to 250,000 final trade data
  records.
- **Method.** GET.
- **Path.** `/data/v1/get/{typeCode}/{freqCode}/{clCode}`.
- **Required parameters.** `subscription-key`,
  `reporterCode`, `period`, `flowCode` (for final data),
  `cmdCode`.
- **Optional parameters.** As E16, plus `maxRecords`
  with a hard cap of 250,000.
- **Case-sensitivity.** Accepts `reporterCode` (camelCase).
  Verified.
- **Response.** As E16.
- **Failure modes.** 401 if the key is missing or invalid;
  200 with `count=0` for valid queries with no data.
- **SDK relevance.** Used by the trade layer when the
  consumer has a subscription key.

## 4.19 E19 — Authenticated tariffline data

- **Purpose.** Return up to 250,000 tariffline trade data
  records.
- **Method.** GET.
- **Path.** `/data/v1/getTariffline/{typeCode}/{freqCode}/{clCode}`.
- **Status.** Documented.
- **SDK relevance.** Used by the trade layer when the
  consumer requires line-level records and has a
  subscription key.

## 4.20 E20 — Trade matrix

- **Purpose.** Return trade matrix data — official trade
  values complemented by estimates.
- **Method.** GET.
- **Path.** `/data/v1/getTradeMatrix/{typeCode}/{freqCode}/TM`.
- **Required parameters.** `subscription-key`, `period`,
  `flowCode`, `cmdCode`, `reporterCode`, `partnerCode`.
- **Status.** Documented.
- **SDK relevance.** Used by the trade layer when the
  consumer wants the harmonised world trade matrix
  including estimates.

## 4.21 E21 — Trade balance

- **Purpose.** Return exports and imports laid out side
  by side.
- **Method.** GET.
- **Path.** `/tools/v1/getTradeBalance/{typeCode}/{freqCode}/{clCode}`.
- **Required parameters.** `subscription-key`, `period`,
  `cmdCode`, `reporterCode`.
- **Verified behaviour.** 401 if the key is missing.
- **SDK relevance.** Used by the trade layer when the
  consumer wants a balance sheet view.

## 4.22 E22 — Bilateral data

- **Purpose.** Return reported data complemented by
  mirror partner data.
- **Method.** GET.
- **Path.** `/tools/v1/getBilateralData/{typeCode}/{freqCode}/{clCode}`.
- **Required parameters.** `subscription-key`, `period`,
  `cmdCode`, `reporterCode`, `flowCode`.
- **Verified behaviour.** 401 if the key is missing.
- **SDK relevance.** Used by the trade layer when the
  consumer wants to reconcile reported values against
  mirror values.

## 4.23 E23 — Async submit, status, and download

- **Purpose.** Submit, poll, and download long-running
  data requests.
- **Method.** GET (and POST for the submit).
- **Path.** Documented by `comtradeapicall` as
  `/data/v1/submitAsyncFinalDataRequest`,
  `/data/v1/checkAsyncDataRequest`,
  `/data/v1/downloadAsyncFinalDataRequest` and
  corresponding tariffline variants.
- **Status.** Documented; not exercised in this research.
- **SDK relevance.** Used by the trade layer when the
  consumer wants to exceed the 250,000-record cap and
  receive the result through an email notification or a
  polling endpoint.

## 4.24 E24 — Bulk download

- **Purpose.** Download the pre-built bulk data files.
- **Method.** GET.
- **Path.** Documented by `comtradeapicall` as
  `/data/v1/bulkDownloadFinalFile` and corresponding
  variants. The URL pattern probed during this research
  (`/data/v1/bulk/...`, `/bulk/...`, `/data/v1/bulkDownload/...`)
  returned 404 without a key; the documented URL is the
  correct one.
- **Status.** Documented; not exercised in this research.
- **SDK relevance.** Used by the storage layer when the
  consumer wants the most efficient way to load large
  volumes of data.

## 4.25 E25 — Data availability

- **Purpose.** Enumerate the data currently available.
- **Method.** GET.
- **Path.** Unverified during this research. Documented by
  `comtradeapicall` as
  `getFinalDataAvailability` and
  `getTarifflineDataAvailability`; the URL pattern probed
  returned 404.
- **Status.** Unverified.
- **SDK relevance.** Used by the trade layer to size a
  query before issuing it.

## 4.26 E26 — Standard Unit Value (SUV)

- **Purpose.** Return reference unit value and range data
  for a commodity.
- **Method.** GET.
- **Path.** Documented; not exercised.
- **Status.** Documented.
- **SDK relevance.** Used by the analytics layer; the SDK
  exposes the endpoint but does not interpret the
  results.

## 4.27 E27 — Metadata + publication notes

- **Purpose.** Return publication notes and per-release
  metadata.
- **Method.** GET.
- **Path.** Documented; not exercised.
- **Status.** Documented.
- **SDK relevance.** Used by the storage layer to record
  the publication version of a captured dataset.

---

# 5. Parameter Catalog

The parameter catalog documents every parameter accepted by
the trade data endpoints. The same parameters are accepted
by the public preview, the authenticated final endpoint,
and the authenticated tariffline endpoint. The reference
endpoints accept no parameters.

## 5.1 typeCode

- **Description.** Identifies the type of record.
- **Required.** Yes.
- **Datatype.** String, single character.
- **Allowed values.** `C` (commodities/goods), `S`
  (services).
- **Observed behaviour.** A query with an unknown value
  returns `count=0` and HTTP 200, not 4xx.
- **Validation rule.** SHALL be one of the documented
  values.

## 5.2 freqCode

- **Description.** Identifies the time granularity of the
  query.
- **Required.** Yes.
- **Datatype.** String, single character.
- **Allowed values.** `A` (annual), `M` (monthly).
- **Validation rule.** SHALL be one of the documented
  values.

## 5.3 clCode

- **Description.** Identifies the product classification
  and, for the per-edition lists, the version of that
  classification.
- **Required.** Yes.
- **Datatype.** String.
- **Allowed values.** `HS` (combined), `H0`–`H6` (per
  edition), `S1`–`S4` and `SS` (SITC), `B4`/`B5` (BEC),
  `EB02`/`EB10`/`EB10S`/`EB` (EBOPS), `TM` (trade matrix
  only).
- **Validation rule.** SHALL match one of the documented
  values, and SHALL be consistent with the data endpoint
  (e.g. `TM` is only valid on the trade matrix endpoint).

## 5.4 period

- **Description.** The reference period of the query.
- **Required.** Yes.
- **Datatype.** String, comma-separated list of integers.
- **Format.** For annual data, a four-digit year
  (`2022`) or a comma-separated list (`2020,2021,2022`).
  For monthly data, a six-digit `YYYYMM` value
  (`202201`) or a comma-separated list.
- **Maximum length.** 12 values per request (documented).
- **Validation rule.** SHALL be an integer in the
  documented format.

## 5.5 reporterCode

- **Description.** Identifies the reporting country.
- **Required.** Yes.
- **Datatype.** Integer, encoded as a string in the URL.
- **Allowed values.** Any value from the `Reporters`
  reference table.
- **Special values.** None. The current reporter for India
  is `699`; the historical value `356` is expired and
  SHALL NOT be used.
- **Case-sensitivity quirk.** The preview endpoint accepts
  the parameter only as `reportercode` (all lowercase).
  The authenticated endpoint accepts `reporterCode`
  (camelCase). Both forms are verified.

## 5.6 partnerCode

- **Description.** Identifies the partner country.
- **Required.** No.
- **Datatype.** Integer, encoded as a string in the URL.
- **Allowed values.** Any value from the `partnerAreas`
  reference table.
- **Special values.** `0` (World aggregate).

## 5.7 partner2Code

- **Description.** Identifies a secondary partner (e.g.
  country of origin for re-exports).
- **Required.** No.
- **Datatype.** Integer, encoded as a string in the URL.
- **Allowed values.** Any value from the `partnerAreas`
  reference table.
- **SDK relevance.** Only used in the `plus` breakdown
  mode.

## 5.8 flowCode

- **Description.** Identifies the trade flow direction.
- **Required.** Yes for final data.
- **Datatype.** String.
- **Allowed values.** `M` (import), `X` (export), `RX`
  (re-export), `RM` (re-import), plus the `plus`-mode
  derived codes for the extended breakdown.
- **Validation rule.** SHALL match one of the documented
  values.

## 5.9 cmdCode

- **Description.** Identifies the commodity code in the
  context of the chosen classification.
- **Required.** No.
- **Datatype.** String.
- **Allowed values.** Any commodity code in the chosen
  classification, or `TOTAL` for the wildcard.
- **Special values.** `TOTAL` is the documented wildcard
  for "all products in the classification".

## 5.10 customsCode

- **Description.** Identifies the customs procedure.
- **Required.** No.
- **Datatype.** String.
- **Allowed values.** Any value from the
  `CustomsCodes` reference table; `C00` is the total.
- **SDK relevance.** Only used in the `plus` breakdown
  mode.

## 5.11 motCode

- **Description.** Identifies the mode of transport.
- **Required.** No.
- **Datatype.** String or integer.
- **Allowed values.** Any value from the
  `ModeOfTransportCodes` reference table; `0` is the
  total.
- **SDK relevance.** Only used in the `plus` breakdown
  mode.

## 5.12 maxRecords

- **Description.** The maximum number of records to
  return.
- **Required.** No.
- **Datatype.** Integer.
- **Default.** 500 for the preview endpoint; 250,000 for
  the authenticated endpoint.
- **Hard caps.** 500 for the preview endpoint; 250,000
  for the authenticated endpoint. A request for a higher
  value is silently capped.

## 5.13 format

- **Description.** The response format.
- **Required.** No.
- **Datatype.** String.
- **Allowed values.** `JSON` is the only documented value
  in the modern API; the legacy `CSV` value is not in
  scope.
- **Default.** `JSON`.

## 5.14 aggregateBy

- **Description.** Aggregate the result by the named
  dimension.
- **Required.** No.
- **Datatype.** String.
- **Allowed values.** `cmdCode`, `period`, `reporterCode`,
  `partnerCode`, `partner2Code`, `motCode`, `customsCode`.
  Multiple values are accepted as a comma-separated list.
- **Default.** None.

## 5.15 breakdownMode

- **Description.** Selects the breakdown style.
- **Required.** No.
- **Datatype.** String.
- **Allowed values.** `classic` (legacy style),
  `plus` (extended breakdown).
- **Default.** `classic`.

## 5.16 includeDesc

- **Description.** Whether to include the human-readable
  description for each code in the response.
- **Required.** No.
- **Datatype.** Boolean.
- **Default.** `true`.
- **Observed behaviour.** When `false`, the description
  fields are returned as `null`. Verified.

## 5.17 countOnly

- **Description.** Return only the count of matching
  records, not the records themselves.
- **Required.** No.
- **Datatype.** Boolean.
- **Default.** `false`.
- **SDK relevance.** Used to size a query before
  downloading.

## 5.18 subscription-key

- **Description.** The subscription key.
- **Required.** Yes for the authenticated endpoints.
- **Datatype.** String.
- **Verification.** Verified by live request.
- **Header equivalent.** `Ocp-Apim-Subscription-Key`.

---

# 6. Response Models

The response model of a trade data query is a JSON object
with four top-level keys. The model has been verified by
live request.

## 6.1 Top-level response

- `elapsedTime` (string). The wall-clock time the upstream
  spent producing the response, formatted as a duration
  with units (e.g. `"0.27 secs"`). Verified.
- `count` (integer). The number of records in the
  response. Verified.
- `data` (array). The records. May be empty.
  Verified.
- `error` (string). The error description, empty on
  success. Verified.

## 6.2 Trade record — 47 fields

The following 47 fields are present in every record
returned by the trade data endpoints. The list is
**Verified** by live request.

| Field                          | Datatype        | Nullable | Description                                       |
| ------------------------------ | --------------- | -------- | ------------------------------------------------- |
| `typeCode`                     | string          | no       | Type of record (C/S)                              |
| `freqCode`                     | string          | no       | Time granularity (A/M)                            |
| `refPeriodId`                  | integer         | no       | Internal period identifier                        |
| `refYear`                      | integer         | no       | Reference year                                    |
| `refMonth`                     | integer         | no       | Reference month; 52 = annual                      |
| `period`                       | string          | no       | Human-readable period (e.g. "2022", "202201")     |
| `reporterCode`                 | integer         | no       | Reporting country code                            |
| `reporterISO`                  | string          | yes      | ISO-3 code of the reporter                        |
| `reporterDesc`                 | string          | yes      | Human-readable name of the reporter               |
| `flowCode`                     | string          | no       | Trade flow direction (M/X/RX/RM)                  |
| `flowDesc`                     | string          | yes      | Human-readable flow description                   |
| `partnerCode`                  | integer         | no       | Partner country code                              |
| `partnerISO`                   | string          | yes      | ISO-3 code of the partner                         |
| `partnerDesc`                  | string          | yes      | Human-readable name of the partner                |
| `partner2Code`                 | integer         | no       | Secondary partner code                            |
| `partner2ISO`                  | string          | yes      | ISO-3 code of the secondary partner               |
| `partner2Desc`                 | string          | yes      | Human-readable secondary partner name             |
| `classificationCode`           | string          | no       | Internal classification code (e.g. H6)            |
| `classificationSearchCode`     | string          | no       | Classification search code (e.g. HS)              |
| `isOriginalClassification`     | boolean         | no       | True if classification is the original            |
| `cmdCode`                      | string          | no       | Commodity code                                    |
| `cmdDesc`                      | string          | yes      | Human-readable commodity description              |
| `aggrLevel`                    | integer         | yes      | Aggregation level                                 |
| `isLeaf`                       | boolean         | yes      | True if row is a leaf in the classification tree  |
| `customsCode`                  | string          | no       | Customs procedure code                            |
| `customsDesc`                  | string          | yes      | Customs procedure description                     |
| `mosCode`                      | string          | no       | Mode of supply (services only)                    |
| `motCode`                      | integer         | no       | Mode of transport                                 |
| `motDesc`                      | string          | yes      | Mode of transport description                     |
| `qtyUnitCode`                  | integer         | no       | Quantity unit code                                |
| `qtyUnitAbbr`                  | string          | yes      | Quantity unit abbreviation                        |
| `qty`                          | number          | no       | Quantity                                          |
| `isQtyEstimated`               | boolean         | no       | Whether qty is estimated                          |
| `altQtyUnitCode`               | integer         | no       | Alternate quantity unit code                      |
| `altQtyUnitAbbr`               | string          | yes      | Alternate quantity unit abbreviation              |
| `altQty`                       | number          | no       | Alternate quantity                                |
| `isAltQtyEstimated`            | boolean         | no       | Whether altQty is estimated                       |
| `netWgt`                       | number          | yes      | Net weight in kg                                  |
| `isNetWgtEstimated`            | boolean         | no       | Whether netWgt is estimated                       |
| `grossWgt`                     | number          | no       | Gross weight in kg                                |
| `isGrossWgtEstimated`          | boolean         | no       | Whether grossWgt is estimated                     |
| `cifvalue`                     | number          | yes      | CIF value (imports)                               |
| `fobvalue`                     | number          | no       | FOB value (exports)                               |
| `primaryValue`                 | number          | no       | Primary trade value (USD)                         |
| `legacyEstimationFlag`         | integer         | no       | Legacy estimation flag (0 = real, >0 = estimated) |
| `isReported`                   | boolean         | no       | True if record is reported by the source          |
| `isAggregate`                  | boolean         | no       | True if record is an aggregate of finer rows      |

## 6.3 Reference record — reporters

A reporter record contains the fields listed below. The list
is **Verified** by live request against `Reporters.json`.

- `id` (integer). Internal id.
- `text` (string). Short name.
- `reporterCode` (integer). Code.
- `reporterDesc` (string). Long name.
- `reporterNote` (string). Note (e.g. "India, excluding
  Sikkim" for the historical code 356).
- `reporterCodeIsoAlpha2` (string). ISO-3166 alpha-2.
- `reporterCodeIsoAlpha3` (string). ISO-3166 alpha-3.
- `entryEffectiveDate` (string). ISO-8601 date.
- `entryExpiredDate` (string, nullable). ISO-8601 date if
  the code has been retired.
- `isGroup` (boolean). True for aggregate codes.

## 6.4 Trade balance record

The trade balance record shape is **Documented** but not
exercised in this research. The shape is expected to
include both the export record and the import record for
the same query, with the export and import values aligned
on the same row.

## 6.5 Bilateral record

The bilateral record shape is **Documented** but not
exercised. The shape is expected to include the reported
value and the mirror value, with reconciliation metadata.

---

# 7. Error Catalogue

The error catalogue documents every observed error from the
public preview and the authenticated endpoints. The
catalogue is a living record; future research may add new
errors.

## 7.1 HTTP 200 with count=0

- **Observed with.** Valid query for a combination of
  parameters that has no data (e.g. India with `cmdCode=
  270900` and `flowCode=X` in 2022; period `1900` for any
  combination).
- **Meaning.** The query was syntactically valid and was
  accepted; the upstream has no data matching the
  combination.
- **Cause.** Combination is too narrow; data has not yet
  been reported; commodity is not traded by the reporter.
- **Recovery.** Broaden the query; try a more recent
  period; check the commodity code against the
  classification.
- **Retry recommendation.** No.

## 7.2 HTTP 401 — missing subscription key

- **Body.** `{ "statusCode": 401, "message": "Access denied
  due to missing subscription key. Make sure to include
  subscription key when making requests to an API." }`
- **Meaning.** The endpoint requires a subscription key
  and the key was not provided.
- **Cause.** The consumer did not provide a key, or
  provided it on a different parameter name.
- **Recovery.** Provide the key as `subscription-key`
  (query) or `Ocp-Apim-Subscription-Key` (header).
- **Retry recommendation.** No — the retry will produce
  the same response until a key is supplied.
- **SDK exception mapping.** The SDK SHALL raise a
  documented `AuthenticationError`.

## 7.3 HTTP 401 — invalid subscription key

- **Body.** `{ "statusCode": 401, "message": "Access denied
  due to invalid subscription key. Make sure to provide a
  valid key for an active subscription." }`
- **Meaning.** The supplied key is not recognised.
- **Cause.** Typo; expired key; suspended subscription.
- **Recovery.** Verify the key; if it is correct, contact
  the developer portal.
- **Retry recommendation.** No.
- **SDK exception mapping.** The SDK SHALL raise the same
  `AuthenticationError` as for 7.2.

## 7.4 HTTP 404 — resource not found

- **Body.** `{ "statusCode": 404, "message": "Resource not
  found" }`
- **Meaning.** The requested URL is not a known endpoint.
- **Observed with.** Probed URL pattern
  `/data/v1/getFinalDataAvailability/699/C/A/HS?subscription-key=`
  during this research.
- **Recovery.** Verify the URL pattern against the
  documented endpoints.
- **Retry recommendation.** No.
- **SDK exception mapping.** The SDK SHALL raise a
  documented `EndpointNotFoundError`.

## 7.5 HTTP 429 — too many requests

- **Observed with.** Repeated rapid calls during the
  research caused an HTTP 429 response (the body is
  empty).
- **Meaning.** The consumer has exceeded the rate limit.
- **Cause.** Sustained high request rate; concurrent
  consumers sharing the same key.
- **Recovery.** Wait, then retry with the backoff
  schedule in section 9.
- **Retry recommendation.** Yes, with exponential backoff.
- **SDK exception mapping.** The SDK SHALL raise a
  documented `RateLimitError`; the SDK SHALL NOT swallow
  the error but SHALL retry automatically with the
  documented backoff.

## 7.6 HTTP 5xx — server errors

- **Observed with.** Not observed in this research; the
  Azure API Management gateway is documented to return 5xx
  in case of upstream failure.
- **Recovery.** Retry with backoff.
- **Retry recommendation.** Yes, with exponential backoff
  capped at the documented retry limit.
- **SDK exception mapping.** The SDK SHALL raise a
  documented `UpstreamError`.

## 7.7 Empty response body

- **Observed with.** The 429 response body is empty.
- **Meaning.** The gateway has rejected the request before
  a JSON body could be produced.
- **SDK exception mapping.** The SDK SHALL treat the
  response as a `RateLimitError` based on the status code
  alone.

## 7.8 Browser CORS error

- **Observed with.** Browser-based calls against the API
  from a different origin return a CORS error in the
  console. **Verified** by inspecting response headers
  on both `GET` and `OPTIONS` requests: no
  `Access-Control-Allow-Origin` header is set, and no
  preflight response carries the header.
- **Meaning.** The API does not advertise a CORS policy
  and is not intended to be called directly from a
  browser.
- **Cause.** Browser-enforced same-origin policy.
- **Recovery.** Call the API from a server-side context
  (Python, Node, curl, Postman desktop). The SDK is
  designed to be called from a server-side context.
- **Retry recommendation.** N/A.
- **SDK exception mapping.** N/A — the SDK is not
  affected by CORS.

---

# 8. Pagination

The public preview endpoint does not support pagination. The
record cap of 500 is the hard limit per call.

The authenticated data endpoint does not support cursor-based
pagination through a documented parameter. The 250,000-record
cap is the hard limit per call.

For results larger than the documented cap, the consumer
SHALL use one of:

- **Async delivery (E23).** Submit a query and receive the
  result by email or polling. The cap is documented as
  2,500,000 records.
- **Bulk download (E24).** Download the pre-built bulk
  files. The cap is unbounded within a single reporter
  and period.

The combination of multiple `period` values in a single
call is supported and is the documented workaround for the
absence of a per-page continuation token. The number of
period values per call is documented as 12 (annual) or 12
(monthly), and is recorded in section 5.4.

The SDK SHALL NOT invent a pagination protocol on top of
the documented endpoints. The SDK SHALL expose async
delivery and bulk download as the documented solutions for
large queries.

---

# 9. Rate Limits

The rate limit was re-verified empirically on 2026-06-26T22:10–22:18 UTC.
The shape is **Verified** (token-bucket, ≈1 req/s, `Retry-After: 1`).
The full transcript is in `API_LIMITS_REPORT.md` and the empirical
record is preserved as ADR-0035 in `DECISIONS.md`.

## 9.1 Published limits

- **Public preview.** A consumer may issue a small number
  of requests per minute. The exact cap is not documented
  on the public-facing help pages.
- **Authenticated surface.** A consumer with a key may
  issue a larger number of requests per minute. The exact
  cap depends on the subscription tier and is documented
  at the developer portal.
- **Daily record cap.** A free user may download up to
  50,000,000 records per day, subject to the per-minute
  cap.

## 9.2 Observed limits (verified 2026-06-26)

- **Token-bucket model.** The upstream enforces a token-bucket
  rate limit, not a fixed per-minute window.
- **Refill rate.** Approximately 1 request per second.
- **Burst allowance.** Approximately 2–3 immediate requests.
- **Inferred per-minute upper bound.** ≈60–63 req/min under
  ideal pacing.
- **The 429 response** includes:
  - Status: `HTTP 429 Too Many Requests`
  - Header: `Retry-After: 1` (seconds)
  - Header: `Content-Type: application/json`
  - Body: `{ "statusCode": 429, "message": "Rate limit is
    exceeded. Try again in 1 seconds." }`
- **No standard rate-limit response headers** are exposed
  (`X-RateLimit-*` and `RateLimit-*` are absent).
- **Probes used:** 50-request burst, 1 req/s sustained for
  60 s, 200-request hammer. The hammer mode saw the first
  429 at request #3.

## 9.3 Burst behaviour (verified)

- Burst allowance is small (≈2–3 requests) before the upstream
  starts returning 429.
- After a 429, the upstream signals `Retry-After: 1`; honouring
  this header returns the consumer to the steady-state
  rate immediately.

## 9.4 Daily limits (verified against prior research)

- Free tier: **50,000,000 records per day**, subject to the
  per-second rate limit (ADR-0035).
- Paid tier: higher; documented in the developer portal;
  out of scope for the MVP.

## 9.5 Retry recommendations (updated)

- The SDK SHALL honour `Retry-After` if present on a 429
  response.
- The SDK SHALL fall back to the ADR-0008 exponential-backoff
  schedule (initial 1 s, multiplier 2, cap 60 s, 3 attempts)
  when `Retry-After` is absent.
- The SDK SHALL default to a sustained 1 req/s pacing in
  the transport layer; concurrent batches SHALL share the
  same per-connection rate cap.
- Premium tier: documented higher.

## 9.5 Retry recommendations

- The SDK SHALL retry on HTTP 429 with exponential
  backoff.
- The SDK SHALL retry on HTTP 5xx with exponential
  backoff.
- The SDK SHALL NOT retry on HTTP 401, 404, or 400.
- The SDK SHALL NOT retry on a 200 with `count=0`; that
  is a successful empty result.

## 9.6 Backoff recommendations

- Initial backoff: 1 second.
- Multiplier: 2.
- Cap: 60 seconds.
- Maximum attempts: 5 (configurable).

## 9.7 Unverified values

The exact per-minute request cap is **Unverified**. The
exact per-key daily cap is **Unverified** at the date of
this document. The values will be recorded in the SDK
specification as configuration defaults with a note that
they are starting points, not commitments.

---

# 10. Metadata Endpoints

The metadata endpoints are documented in section 3.1. The
purpose of the endpoints, the update frequency, and the SDK
importance are summarised below.

| Endpoint                        | Purpose                                      | Update frequency        | SDK importance |
| ------------------------------- | -------------------------------------------- | ----------------------- | -------------- |
| ListOfReferences                 | Enumerate reference tables                   | Static                  | Medium         |
| Reporters                        | Reporter country catalogue                   | Quarterly to annually   | High           |
| Partner areas                    | Partner country catalogue                    | Quarterly to annually   | High           |
| HS combined                      | HS codes across editions                     | With each HS revision   | High           |
| HS per-edition                   | HS codes for a specific edition              | With each HS revision   | High           |
| SITC combined                    | SITC codes across revisions                  | With each SITC revision | Medium         |
| SITC per-revision                | SITC codes for a specific revision           | With each SITC revision | Medium         |
| BEC Rev.4 / Rev.5                | Broad economic categories                    | With each BEC revision  | Low            |
| EBOPS 2002, 2010, combined       | Services classifications                     | With each EBOPS revision| Low            |
| Frequency                        | Frequency codes (A/M)                        | Static                  | High           |
| Trade flows                      | Trade flow codes (M/X/RX/RM)                 | Static                  | High           |
| Customs codes                    | Customs procedure codes                      | Stable                  | Medium         |
| Modes of transport               | Transport codes                              | Stable                  | Medium         |
| Modes of supply                  | Supply mode codes (services)                 | Stable                  | Low            |
| Quantity units                   | Quantity unit codes                          | Stable                  | Medium         |
| Trade data items                 | Column catalogue                             | With each schema change | High           |

The update frequency is **Unverified** for the dynamic
catalogues; the underlying UN Comtrade data pipeline
publishes updates on a quarterly cycle, but the
publication date is not exposed on the reference
endpoints.

---

# 11. Trade Endpoints

The trade endpoints are documented in section 3.2, 3.3,
and 3.4. The summary below records the capabilities and
the limitations.

## 11.1 Annual trade

- **Final data.** Available through the public preview
  (500 records per call) and the authenticated endpoint
  (250,000 records per call). The classification is
  identified by `clCode`; the time granularity is `A`.
- **Tariffline data.** Available through the
  `previewTariffline` and `getTariffline` endpoints.
  Tariffline data provides line-level records and is more
  granular than the final data.
- **Limitation.** The preview endpoint is case-sensitive
  on `reportercode`; the data endpoint accepts
  `reporterCode`. The SDK SHALL normalise the parameter
  before issuing the call.

## 11.2 Monthly trade

- As annual trade, with `freqCode=M` and `period` in
  `YYYYMM` format. The 12-period-per-call cap applies.

## 11.3 Preview endpoints

- `preview` returns up to 500 records without a key.
- `previewTariffline` returns up to 500 records without a
  key.
- The preview endpoints are the only way to access the
  data without a key.

## 11.4 Tariffline endpoints

- `getTariffline` returns up to 250,000 records with a
  key.
- Tariffline data is more granular than final data and is
  the canonical source for line-level analysis.

## 11.5 Download endpoints

- `get` returns up to 250,000 records with a key.
- `bulkDownloadFinalFile` (E24) returns the pre-built
  bulk files. The SDK SHALL expose this endpoint as the
  preferred path for large extracts.
- `submitAsyncFinalDataRequest` (E23) returns up to
  2,500,000 records through an asynchronous delivery.

## 11.6 Tooling endpoints

- `getTradeBalance` (E21) returns exports and imports
  side by side.
- `getBilateralData` (E22) returns reported data
  complemented by mirror data.

---

# 12. Data Quality Assessment

The data quality of the UN Comtrade API is generally high,
but a number of caveats apply.

## 12.1 Completeness

- The dataset is comprehensive in terms of reporter
  coverage. Every United Nations member state plus a
  number of additional economies is represented.
- The classification is comprehensive. The combined HS
  list contains 8,262 entries; the per-edition lists
  contain between 6,000 and 7,000 entries each.

## 12.2 Consistency

- The response payload is consistent across the preview
  and the data endpoints. The field set is identical;
  the only difference is the cap and the auth.
- The reference catalogues are internally consistent;
  the same reporter code always identifies the same
  economy.

## 12.3 Null handling

- Description fields are nullable. The SDK SHALL treat a
  null description as "description not requested" when
  `includeDesc=false` and as "description unknown"
  otherwise.
- Quantity fields are nullable. A null quantity is the
  correct representation of "no quantity reported".

## 12.4 Duplicate observations

- A single call SHALL NOT return duplicate rows. The
  combination of reporter, partner, period, flow,
  commodity, and classification is unique within a
  response.
- A consumer that issues overlapping calls (e.g. with
  different `cmdCode` filters that overlap at the
  aggregate level) SHALL be aware of the resulting
  double-counting.

## 12.5 Country coverage

- Verified. 255 reporter codes; 310 partner codes. The
  discrepancy reflects the inclusion of aggregate and
  group codes in the partner list.

## 12.6 Historical coverage

- Annual data is documented to start in 1962 for most
  reporters. Monthly data starts later and is
  inconsistent across reporters.
- A query for a period outside the documented coverage
  returns HTTP 200 with `count=0` and `error=""`. The
  SDK SHALL treat this as a successful empty result.

## 12.7 Known inconsistencies

- The India code `356` is present in the reporter list
  with `entryExpiredDate=1974-12-31`. A consumer that
  uses `356` will receive 0 records. The SDK SHALL warn
  the consumer when a code is expired.
- The `qtyUnitCode=-1` value is documented as "not
  applicable"; a record with this value is not a defect.
- The `partnerCode=0` and `partnerISO="W00"` record is
  the documented World aggregate.

---

# 13. Known API Limitations

The limitations below are documented or observed.

## 13.1 Browser CORS restrictions

The API does not set CORS headers. A consumer that calls
the API from a browser will receive a CORS error. The
SDK is designed to be called from a server-side context;
the CORS limitation is documented in section 7.8 and is
not a defect.

## 13.2 Record caps

- 500 records per call on the public preview.
- 250,000 records per call on the authenticated data
  endpoint.
- 2,500,000 records per call on the async delivery.

The caps are documented; consumers that need more SHALL
use bulk download.

## 13.3 Missing documentation

- The data availability endpoint URL is not documented on
  the public-facing help pages. Section 4.25 records the
  URL as **Unverified**.
- The exact rate-limit cap is not documented on the
  public-facing help pages. Section 9 records the cap
  as **Unverified**.

## 13.4 Authentication inconsistencies

- The same key is accepted in two locations (query
  parameter and HTTP header). The SDK SHALL use the
  query parameter form because it is the form exercised
  by the official `comtradeapicall` package.
- The 401 response does not distinguish between a
  missing key, an invalid key, and an expired key. The
  SDK SHALL treat all three as the same exception.

## 13.5 Parameter restrictions

- The preview endpoint is case-sensitive on `reportercode`
  (all lowercase). The data endpoint is not. The
  inconsistency is documented in section 5.5.

## 13.6 Response inconsistencies

- The `elapsedTime` field is a string, not a number. The
  SDK SHALL parse the string into a number of seconds.
- The `error` field is a string, not a structured object.
  The SDK SHALL treat any non-empty `error` value as a
  failure indication and raise a documented exception.

## 13.7 Description fields

- When `includeDesc=false`, the description fields are
  returned as `null`. A consumer that relies on
  descriptions SHALL pass `includeDesc=true` explicitly.

---

# 14. Performance Observations

The performance observations below are recorded from the
research session. They are **Verified** observations on
the date of the metadata block.

## 14.1 Typical response times

- Reference endpoints: 0.05 to 0.30 seconds. The
  reference files are static and are served from a
  CDN.
- Public preview, single record: 0.10 to 0.50 seconds.
- Public preview, 500 records: 1.0 to 3.0 seconds.
- Authenticated data endpoint: expected to be similar to
  the public preview, with a per-call overhead for the
  authentication lookup.

## 14.2 Large downloads

- A 250,000-record authenticated call has not been
  exercised in this research. The expected behaviour is
  documented in section 8.

## 14.3 Timeout behaviour

- A 30-second timeout is sufficient for every observed
  response. A 60-second timeout is recommended as a
  default for the SDK to absorb transient gateway
  delays.

## 14.4 Observed latency

- Median: 0.3 seconds for a 500-record preview.
- 95th percentile (in this research): 3.0 seconds.

## 14.5 SDK implications

- The SDK SHALL use a configurable timeout with a
  default of 60 seconds.
- The SDK SHALL expose the elapsed time of the
  upstream response to the consumer for telemetry.
- The SDK SHALL not block on a single call longer than
  the configurable timeout; longer extracts SHALL use
  the async delivery or the bulk download.

---

# 15. SDK Design Considerations

The design considerations below are the input to the SDK
specification. They are not implementation decisions;
they are the observations that the SDK specification will
translate into design decisions.

## 15.1 E1 — List of references

- **SDK wrapper.** Exposed as a method on the metadata
  layer.
- **Caching suitability.** Highly cacheable. The result
  changes only when the catalogue changes.
- **Retry suitability.** Not needed; the endpoint is
  static.
- **Pagination suitability.** Not needed.
- **Batch suitability.** Not needed.

## 15.2 E2–E15 — Reference catalogues

- **SDK wrapper.** Exposed as query helpers on the
  metadata layer.
- **Caching suitability.** Highly cacheable. The
  result changes only when the catalogue is updated.
- **Retry suitability.** Yes, with backoff.
- **Pagination suitability.** Not needed; the entire
  catalogue is returned in one call.
- **Batch suitability.** Not needed.

## 15.3 E16 — Public preview, final data

- **SDK wrapper.** Exposed as a method on the trade
  layer that does not require a key.
- **Caching suitability.** Cacheable per (reporter,
  partner, period, flow, cmdCode) tuple. The cache key
  is the tuple.
- **Retry suitability.** Yes, with backoff.
- **Pagination suitability.** Not supported; the
  consumer SHALL split a large request into multiple
  period-bounded calls.
- **Batch suitability.** Limited by the 500-record
  cap.

## 15.4 E17 — Public preview, tariffline data

- **SDK wrapper.** As E16.
- **Caching suitability.** As E16.
- **Retry suitability.** Yes, with backoff.
- **Pagination suitability.** Not supported.
- **Batch suitability.** Limited by the 500-record cap.

## 15.5 E18 — Authenticated final data

- **SDK wrapper.** Exposed as a method on the trade
  layer that requires a key.
- **Caching suitability.** As E16.
- **Retry suitability.** Yes, with backoff, including
  for 401 only if the SDK supports key rotation.
- **Pagination suitability.** Not supported; the
  consumer SHALL use async delivery for large
  extracts.
- **Batch suitability.** Limited by the 250,000-record
  cap.

## 15.6 E19 — Authenticated tariffline data

- **SDK wrapper.** As E18.
- **Caching suitability.** As E18.
- **Retry suitability.** As E18.
- **Pagination suitability.** As E18.
- **Batch suitability.** As E18.

## 15.7 E20 — Trade matrix

- **SDK wrapper.** Exposed as a method on the trade
  layer that requires a key.
- **Caching suitability.** Cacheable per (reporter,
  partner, period, flow, cmdCode) tuple.
- **Retry suitability.** Yes, with backoff.
- **Pagination suitability.** Not supported.
- **Batch suitability.** As E18.

## 15.8 E21 — Trade balance

- **SDK wrapper.** Exposed as a method on the trade
  layer.
- **Caching suitability.** Cacheable per (reporter,
  partner, period, cmdCode) tuple.
- **Retry suitability.** Yes, with backoff.
- **Pagination suitability.** Not supported.
- **Batch suitability.** As E18.

## 15.9 E22 — Bilateral data

- **SDK wrapper.** Exposed as a method on the trade
  layer.
- **Caching suitability.** As E21.
- **Retry suitability.** Yes, with backoff.
- **Pagination suitability.** Not supported.
- **Batch suitability.** As E18.

## 15.10 E23 — Async delivery

- **SDK wrapper.** Exposed as a method on the trade
  layer that returns a handle. The handle is polled
  until the result is ready.
- **Caching suitability.** Not applicable; the result
  is delivered once.
- **Retry suitability.** Yes, with backoff, on the
  poll endpoint.
- **Pagination suitability.** Not applicable.
- **Batch suitability.** Yes; the async delivery
  supports up to 2,500,000 records.

## 15.11 E24 — Bulk download

- **SDK wrapper.** Exposed as a method on the storage
  layer. The method downloads the file to a configured
  directory.
- **Caching suitability.** Not applicable; the file
  is stored on disk.
- **Retry suitability.** Yes, with backoff, on the
  download.
- **Pagination suitability.** Not applicable.
- **Batch suitability.** Yes; the bulk download
  supports an arbitrary number of files.

---

# 16. Verified Examples

The examples below have been exercised by live request on
the date of the metadata block. Each example records the
URL, the parameters, the response status, and a short
description of the response.

## 16.1 E1 — list references

- **URL.** `GET https://comtradeapi.un.org/files/v1/app/reference/ListofReferences.json`
- **Status.** 200.
- **Body summary.** JSON object with `results` array of 28
  entries. Each entry has `category`, `variable`,
  `description`, `fileuri`.

## 16.2 E2 — reporters

- **URL.** `GET https://comtradeapi.un.org/files/v1/app/reference/Reporters.json`
- **Status.** 200.
- **Body summary.** JSON object with `results` array of
  255 entries. India appears under both `reporterCode=
  699` (current) and `reporterCode=356` (historical).

## 16.3 E4 — HS combined

- **URL.** `GET https://comtradeapi.un.org/files/v1/app/reference/HS.json`
- **Status.** 200.
- **Body summary.** JSON object with `results` array of
  8,262 entries.

## 16.4 E16 — preview, India 2022 exports, world total

- **URL.** `GET https://comtradeapi.un.org/public/v1/preview/C/A/HS?reportercode=699&period=2022&flowCode=X&cmdCode=TOTAL&partnerCode=0&maxRecords=5`
- **Status.** 200.
- **Body summary.** `count=1`, one record. The record
  reports `primaryValue=452684213646.747` and
  `partnerDesc="World"`. `reporterCode=699`,
  `reporterDesc="India"`, `flowCode="X"`, `period=
  "2022"`, `cmdCode="TOTAL"`, `partnerCode=0`,
  `partnerISO="W00"`. The classification is
  `classificationCode="H6"`, `classificationSearchCode
  ="HS"`.

## 16.5 E16 — preview, India 2022 monthly jewellery

- **URL.** `GET https://comtradeapi.un.org/public/v1/preview/C/M/HS?reportercode=699&period=202201,202202,...,202212&flowCode=X&cmdCode=7113`
- **Status.** 200.
- **Body summary.** `count=500` (cap reached). Records
  describe monthly exports of HS 7113 (articles of
  jewellery) by partner, for January 2022 onwards. The
  record at the time of the research reported
  `primaryValue=912208653.293` for January 2022 to
  partner `534` (UAE) with classification `H5`
  (HS 2017).

## 16.6 E16 — preview, period 1900

- **URL.** `GET https://comtradeapi.un.org/public/v1/preview/C/A/HS?reportercode=699&period=1900&flowCode=X&cmdCode=TOTAL&maxRecords=2`
- **Status.** 200.
- **Body summary.** `count=0`, `data=[]`, `error=""`.
  Verified: an out-of-range period returns a successful
  empty result, not a 4xx.

## 16.7 E18 — authenticated with invalid key

- **URL.** `GET https://comtradeapi.un.org/data/v1/get/C/A/HS?reporterCode=699&period=2022&flowCode=X&cmdCode=TOTAL&maxRecords=2&subscription-key=invalid`
- **Status.** 401.
- **Body summary.** `{ "statusCode": 401, "message":
  "Access denied due to invalid subscription key. Make
  sure to provide a valid key for an active subscription."
  }`. Verified.

## 16.8 E21 — trade balance without key

- **URL.** `GET https://comtradeapi.un.org/tools/v1/getTradeBalance/C/A/HS?reporterCode=699&period=2022&cmdCode=TOTAL&partnerCode=0`
- **Status.** 401.
- **Body summary.** `{ "statusCode": 401, "message":
  "Access denied due to missing subscription key. Make
  sure to include subscription key when making requests
  to an API." }`. Verified.

## 16.9 CORS observation

- **URL.** `GET https://comtradeapi.un.org/public/v1/preview/C/A/HS?reportercode=699&period=2022&flowCode=X&maxRecords=1`
- **Headers received.** No `Access-Control-Allow-Origin`
  header, no `Access-Control-Allow-Methods` header.
- **OPTIONS preflight.** No CORS headers in the
  preflight response.
- **Implication.** A browser-side call from a different
  origin is rejected by the browser's CORS policy. The
  SDK SHALL NOT be called from a browser context.

---

# 17. Open Questions

The questions below are recorded for future resolution.
Each question includes a description, an impact, a
priority, and a suggested verification step.

- **OQ-API-001 (Priority: High).** What is the exact
  per-minute request cap on the public preview surface?
  **Impact.** The SDK default retry/backoff configuration
  depends on this number.
  **Suggested verification.** Issue a sustained
  sequence of calls and observe the 429 threshold.

- **OQ-API-002 (Priority: High).** What is the exact
  per-key daily record cap?
  **Impact.** The SDK configuration documentation will
  document a starting value; consumers that approach
  the cap need to know.
  **Suggested verification.** Read the developer portal
  subscription page; verify with a counted experiment.

- **OQ-API-003 (Priority: Medium).** Is the data
  availability endpoint (E25) reachable under any URL
  pattern?
  **Impact.** The metadata layer may expose a "size the
  query" helper that depends on this endpoint.
  **Suggested verification.** Probe the official
  `comtradeapicall` source for the canonical URL.

- **OQ-API-004 (Priority: Medium).** What is the
  documentation of the `legacyEstimationFlag` value
  semantics? The observed values include 0, 4, and 6.
  **Impact.** The normalisation layer will tag the
  record with the flag; the consumer needs the
  semantics.
  **Suggested verification.** Read the
  `TradeDataItems.json` reference; check the upstream
  documentation for the field.

- **OQ-API-005 (Priority: Medium).** What is the
  semantics of the `aggrLevel` field? The observed
  values are integers in the range observed.
  **Impact.** The normalisation layer will surface the
  level so the consumer can filter for leaf rows.
  **Suggested verification.** Cross-reference the
  classification tree.

- **OQ-API-006 (Priority: Low).** Is the bulk download
  endpoint (E24) reachable under the documented URL
  pattern, or has it been renamed?
  **Impact.** The storage layer depends on the URL.
  **Suggested verification.** Run a probe with a
  valid key.

- **OQ-API-007 (Priority: Low).** Is the `partner2Code`
  parameter honoured on the public preview, or only on
  the `plus` breakdown?
  **Impact.** The trade layer exposes a parameter that
  may not have an effect on the classic preview.
  **Suggested verification.** Issue a probe with and
  without the parameter.

- **OQ-API-008 (Priority: Low).** What is the rate of
  HS revision? The reference catalogue includes 7
  editions. Is HS 2027 expected within the SDK
  maintenance window?
  **Impact.** The metadata layer may need to add a new
  edition.
  **Suggested verification.** Read the WCO
  publications.

---

# 18. Future Research

The areas below are candidates for additional research
beyond the date of this document.

- **Future API versions.** The path-version is `v1`. If
  the upstream publishes `v2`, the API research will
  need to capture the new surface and the migration
  rules.
- **Additional datasets.** The trade matrix and the
  Standard Unit Value are documented but not exercised.
  Future research SHALL exercise them.
- **Authentication enhancements.** The current model is
  a single static key. The upstream may introduce key
  rotation, OAuth, or scoped tokens. Future research
  SHALL capture the new model.
- **New metadata endpoints.** The reference catalogue
  has 28 entries today. New endpoints MAY be added.
  Future research SHALL enumerate and document them.
- **Async and bulk surfaces.** The async delivery and
  the bulk download are documented in the official
  Python package but were not exercised in this
  research. Future research SHALL exercise them with a
  valid key and record the response shapes.
- **Bilateral and trade balance response shapes.** The
  response shapes of E21 and E22 are documented but
  not exercised. Future research SHALL record the
  field sets.
- **Subscription tier semantics.** The free tier and
  the premium tier share the same API surface. The
  exact differences in record caps, request rates, and
  bulk availability are candidates for future
  research.

---

# End of document
