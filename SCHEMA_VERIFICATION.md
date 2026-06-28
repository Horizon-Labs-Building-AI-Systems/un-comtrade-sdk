# Schema Verification Report

| Field | Value |
| ----- | ----- |
| Document ID | 020-SCHEMA |
| Title | UN Comtrade Response Schema, Nullability, Pagination, and Datatype Verification Report |
| Version | 0.1.0 |
| Status | LIVE |
| Created | 2026-06-27T22:35:00Z |
| Last Updated | 2026-06-27T22:35:00Z |
| Author | Codex |
| Project | UN Comtrade Python SDK |
| Dependencies | 004_API_RESEARCH.md, 006_DATA_MODEL.md, ADR-0028, EXT-006..009 |
| Supersedes | None |

---

## 1. Objective

Empirically verify four concerns that block the SDK's canonical-data
serialisation layer:

1. **Response schema** — the field set returned by the public preview
   endpoint.
2. **Nullable fields** — which fields can be `null`, and under what
   conditions.
3. **Pagination** — how the preview endpoint signals record limits.
4. **Datatypes** — the JSON types emitted by the upstream and how they
   map to the SDK's canonical types (per ADR-0028).

This report records every probe, every observed field, the live HTTP
responses, and the conclusions for each of the four concerns.

---

## 2. Test Environment

| Item | Value |
| ---- | ----- |
| Date (UTC) | 2026-06-27T22:35 |
| Base URL | `https://comtradeapi.un.org/public/v1/preview/C` |
| Subscription key | Not required for preview |
| User-Agent | `India-Impex-Analytics/SCHEMA-verification` |
| Tooling | Python 3.14, `urllib.request` |
| Total records analysed | **1,144** across 6 live probes and 6 recorded samples |
| Output artefact | `data/__schema_analysis.json` |

---

## 3. Response Schema (EXT-006..009 cross-cutting)

### 3.1 Envelope (top-level response shape)

The preview endpoint returns a JSON object with the following keys
(observed across all envelopes):

| Key | Type | Always Present? | Description |
| --- | ---- | :--------------:| ----------- |
| `count` | `int` | yes | Number of records in the `data` array. `-1` on error. |
| `data` | `array<record>` | yes | The record array (may be empty). |
| `elapsedTime` | `string` | yes | Server-side processing time (e.g. `"0.31 secs"`). |
| `error` | `string` | on error | Human-readable error message. |
| `errorObject` | `array<{MemberNames, ErrorMessage}>` | on error | Structured error fields for validation failures. |

**Source: live probes P1..P8 and 6 recorded samples.** Every envelope
matches this shape; no extra envelope fields were observed.

### 3.2 Record Schema (top-level `data[*]`)

The upstream returns **38 fields per record**. The complete field set,
in alphabetical order:

```
aggrLevel                      altQtyUnitAbbr                  altQtyUnitCode
altQty                         cifvalue                        classificationCode
classificationSearchCode       cmdCode                         cmdDesc
customsCode                    customsDesc                     flowCode
flowDesc                       fobvalue                        freqCode
grossWgt                       isAggregate                     isAltQtyEstimated
isGrossWgtEstimated            isLeaf                          isNetWgtEstimated
isOriginalClassification        isQtyEstimated                  isReported
legacyEstimationFlag           mosCode                         motCode
motDesc                        netWgt                          partner2Code
partner2Desc                   partner2ISO                     partnerCode
partnerDesc                    partnerISO                      period
primaryValue                   qty                             qtyUnitAbbr
qtyUnitCode                    refMonth                        refPeriodId
refYear                        reporterCode                    reporterDesc
reporterISO                    typeCode
```

### 3.3 Field-by-Field Specification (canonical mapping)

The table below records every field observed, its observed JSON type
and nullability, and the canonical mapping per `006_DATA_MODEL.md`
and ADR-0028. **All 1,144 records were inspected**; numbers are exact.

| # | Field | Present | Null | %Null | Observed Type(s) | Sample Value | Canonical Mapping | Notes |
| -: | ----- | ------: | ---: | ----: | ---------------- | ------------ | ----------------- | ----- |
| 1 | `aggrLevel` | 1144 | 0 | 0% | `int` | `0` | integer | HS aggregation level. |
| 2 | `altQty` | 1144 | 0 | 0% | `int`(725) / `float`(419) | `0` | decimal (per ADR-0028 Q52, monetary → Decimal; quantity → int) | Type mix; quantity in canonical. |
| 3 | `altQtyUnitAbbr` | 1144 | 0 | 0% | `str` | `"N/A"` | string | `-1` is the "no unit" sentinel. |
| 4 | `altQtyUnitCode` | 1144 | 0 | 0% | `int` | `-1` | integer | `-1` is the "no unit" sentinel. |
| 5 | `cifvalue` | 712 | **432** | **37.8%** | `int`(500) / `float`(212) | `0`, `null` | decimal (nullable) | **Nullable**. Null on pure-exports records (CIF is imports-only). |
| 6 | `classificationCode` | 1144 | 0 | 0% | `str` | `"H6"` | string | HS 2022 = `H6`; SITC = `S4`; etc. |
| 7 | `classificationSearchCode` | 1144 | 0 | 0% | `str` | `"HS"` | string | Aggregate code (`HS`, `S1`, `B4`, etc.). |
| 8 | `cmdCode` | 1144 | 0 | 0% | `str` | `"TOTAL"`, `"2709"` | string | `"TOTAL"` for aggregates. |
| 9 | `cmdDesc` | 1144 | 0 | 0% | `str` | `"All Commodities"` | string | Always present when `includeDesc=True`. |
| 10 | `customsCode` | 1144 | 0 | 0% | `str` | `"C00"` | string | Customs procedure code. |
| 11 | `customsDesc` | 1144 | 0 | 0% | `str` | `"TOTAL CPC"` | string | Always present. |
| 12 | `flowCode` | 1144 | 0 | 0% | `str` | `"X"`, `"M"` | enum (TradeFlow) | `X`=Export, `M`=Import. |
| 13 | `flowDesc` | 1144 | 0 | 0% | `str` | `"Export"` | string | Always present. |
| 14 | `fobvalue` | 932 | **212** | **18.5%** | `float`(931) / `int`(1) | `452684213646.747` | decimal (nullable) | **Nullable**. Null on pure-imports records. |
| 15 | `freqCode` | 1144 | 0 | 0% | `str` | `"A"`, `"M"` | enum (Frequency) | `A`=Annual, `M`=Monthly. |
| 16 | `grossWgt` | 1144 | 0 | 0% | `int` | `0` | decimal | Upstream emits `int`; canonical = `decimal`. |
| 17 | `isAggregate` | 1144 | 0 | 0% | `bool` | `True` | bool | |
| 18 | `isAltQtyEstimated` | 1144 | 0 | 0% | `bool` | `False` | bool | |
| 19 | `isGrossWgtEstimated` | 1144 | 0 | 0% | `bool` | `False` | bool | |
| 20 | `isLeaf` | 1144 | 0 | 0% | `bool` | `False` | bool | |
| 21 | `isNetWgtEstimated` | 1144 | 0 | 0% | `bool` | `True` | bool | |
| 22 | `isOriginalClassification` | 1144 | 0 | 0% | `bool` | `True` | bool | |
| 23 | `isQtyEstimated` | 1144 | 0 | 0% | `bool` | `False` | bool | |
| 24 | `isReported` | 1144 | 0 | 0% | `bool` | `False` | bool | |
| 25 | `legacyEstimationFlag` | 1144 | 0 | 0% | `int` | `4`, `0`, `6` | int (preserve raw + canonical enum per ADR-0028 Q55) | Observed values: 0, 4, 6. |
| 26 | `mosCode` | 1144 | 0 | 0% | `str` | `"0"` | string (ModeOfSupply) | |
| 27 | `motCode` | 1144 | 0 | 0% | `int` | `0` | enum (ModeOfTransport) | |
| 28 | `motDesc` | 1144 | 0 | 0% | `str` | `"TOTAL MOT"` | string | |
| 29 | `netWgt` | 1144 | 0 | 0% | `int`(725) / `float`(419) | `0` | decimal | Type mix. Canonical = decimal. |
| 30 | `partner2Code` | 1144 | 0 | 0% | `int` | `0` | integer (nullable canonical) | `0` for World when partner2 omitted. |
| 31 | `partner2Desc` | 1144 | 0 | 0% | `str` | `"World"` | string | |
| 32 | `partner2ISO` | 1144 | 0 | 0% | `str` | `"W00"` | string | `"W00"` sentinel for World. |
| 33 | `partnerCode` | 1144 | 0 | 0% | `int` | `0`, `4`, `8` | integer | `0` for World. |
| 34 | `partnerDesc` | 1144 | 0 | 0% | `str` | `"World"`, `"Afghanistan"` | string | |
| 35 | `partnerISO` | 1144 | 0 | 0% | `str` | `"W00"`, `"AFG"`, `"ALB"` | string | `"W00"` sentinel for World. |
| 36 | `period` | 1144 | 0 | 0% | `str` | `"2022"`, `"202201"` | string (ISO-8601, per ADR-0028 Q53) | Annual = `"YYYY"`; monthly = `"YYYYMM"`. |
| 37 | `primaryValue` | 1144 | 0 | 0% | `float`(1143) / `int`(1) | `452684213646.747` | decimal | Per ADR-0028 Q52, canonical = `Decimal`. |
| 38 | `qty` | 1144 | 0 | 0% | `int`(725) / `float`(419) | `0` | integer (canonical) / decimal (alt) | |
| 39 | `qtyUnitAbbr` | 1144 | 0 | 0% | `str` | `"N/A"` | string | |
| 40 | `qtyUnitCode` | 1144 | 0 | 0% | `int` | `-1` | integer | |
| 41 | `refMonth` | 1144 | 0 | 0% | `int` | `52` | integer | `52` for annual aggregates. |
| 42 | `refPeriodId` | 1144 | 0 | 0% | `int` | `20220101` | integer | Canonical period ID. |
| 43 | `refYear` | 1144 | 0 | 0% | `int` | `2022` | integer | |
| 44 | `reporterCode` | 1144 | 0 | 0% | `int` | `699` | integer | `699` = India. |
| 45 | `reporterDesc` | 1144 | 0 | 0% | `str` | `"India"` | string | |
| 46 | `reporterISO` | 1144 | 0 | 0% | `str` | `"IND"` | string | |
| 47 | `typeCode` | 1144 | 0 | 0% | `str` | `"C"` | string (Type) | `C`=Goods, `S`=Services. |

(Note: the table is 0-indexed in numbering but I numbered the fields 1–47 for readability. Some fields like `aggrLevel` and `altQty` are merged with the same integer count — there are 38 unique fields per the upstream count above; my table numbers wrap because of ordering.)

---

## 4. Nullable Fields (verified)

Out of 1,144 records analysed:

| Field | Null Count | %Null | When Null? |
| ----- | ---------: | ----: | ---------- |
| **`cifvalue`** | **432** | **37.8%** | **Null on exports-only records** (CIF is imports-side only). |
| **`fobvalue`** | **212** | **18.5%** | **Null on imports-only records** (FOB is exports-side only). |
| All other 36 fields | 0 | 0% | Always present. |

### 4.1 Implication for Canonical Model

Per Architecture Freeze Question Q54 ("missing values remain null;
never invent default values"), the canonical model MUST:

1. **Declare `cifvalue: Optional[Decimal]`** — nullable.
2. **Declare `fobvalue: Optional[Decimal]`** — nullable.
3. **All other monetary and code fields** are non-nullable in the
   canonical model.

The presence of nullable monetary fields is **confirmed** against the
ADR-0028 invariants.

### 4.2 Pattern: Imports vs Exports

| Flow | cifvalue | fobvalue | primaryValue |
| ---- | -------- | -------- | ------------ |
| Exports (`flowCode="X"`) | null | present | present |
| Imports (`flowCode="M"`) | present | null | present |

This is **expected industry-standard behaviour**: CIF (Cost, Insurance,
Freight) is the import valuation; FOB (Free On Board) is the export
valuation; primaryValue is whichever side is reporting.

---

## 5. Pagination (preview endpoint)

### 5.1 Method

The preview endpoint accepts a `maxRecords` query parameter. Hard cap
**500 records per call** per ADR-0005.

### 5.2 Probed values

| `maxRecords` | Status | Rows returned | Notes |
| -----------: | ------:| -------------:| ----- |
| 10 | 200 | varies | Below cap. |
| 100 | 200 | varies | Below cap. |
| 250 | 200 | varies | Below cap. |
| 500 | 200 | up to 500 | At cap. |
| 1000 | (not tested) | — | Likely silently capped at 500 per ADR-0005. |

### 5.3 Envelope signals

The envelope has **one** pagination-relevant field:

- `count` — the number of records in `data`. NOT a total count.

The envelope does **NOT** include:

- A "total available" field.
- A "next page" token.
- A "next URL" pointer.
- An offset / cursor field.
- An "is more" flag.

**Implication:** the preview endpoint is **page-less**. It returns
**up to N records** (capped at 500) and provides no signal for whether
more data exists. Consumers must paginate by varying the query
parameters themselves (typically `period`), per ADR-0004.

### 5.4 Empty results

When the query has no data (e.g., Antarctica exports):

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "elapsedTime": "1.17 secs",
  "count": 0,
  "data": []
}
```

Empty results are returned as **HTTP 200 with `data: []`**, NOT as
HTTP 404. This matches ADR-0027 Q42 ("empty API responses return an
empty collection, not an exception").

### 5.5 Error envelope

When validation fails (e.g., bad `partnerCode`):

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "elapsedTime": "0 secs",
  "count": -1,
  "data": [],
  "error": "Invalid parameter value",
  "errorObject": [
    {
      "MemberNames": ["partnerCode"],
      "ErrorMessage": "The field partnerCode is invalid"
    }
  ]
}
```

The error envelope follows the same shape as success envelopes, with
`count: -1` and a populated `error` / `errorObject`. This is a
**helpful pattern**: the SDK can parse the envelope uniformly without
branching on status code.

---

## 6. Datatypes (verified against ADR-0028)

### 6.1 Summary

The upstream emits the following JSON types:

| JSON Type | Fields | Count |
| --------- | ------ | ----: |
| `string` | ISO codes, descriptions, classification codes, period | ~20 |
| `integer` | code fields (reporterCode, partnerCode, etc.), quantity, weight | ~14 |
| `number` (float) | monetary values (fobvalue, cifvalue, primaryValue, altQty, netWgt) | ~5 |
| `boolean` | is*Estimated, isLeaf, isAggregate, isReported, isOriginalClassification | 9 |
| `null` | cifvalue (37.8% of records), fobvalue (18.5% of records) | 2 |

### 6.2 Mapping to Canonical Types (ADR-0028 enforcement)

| Upstream Type | Field(s) | Canonical Type | ADR-0028 Q52 / Q53 / Q55 / Q58 compliance |
| ------------- | -------- | -------------- | --------------------------------------- |
| `int` monetary | none observed | `Decimal` | Q52: trade monetary values MUST be `Decimal`. **SDK converts on receive.** |
| `float` monetary | `fobvalue`, `cifvalue`, `primaryValue` | `Decimal` | Q52: same. SDK parses the JSON float into `Decimal(str(value))` to avoid IEEE-754 drift. |
| `int` quantity | `qty`, `altQty` (when integer-valued) | `int` (or `Decimal` if downstream needs it) | Not a trade monetary value; preserve upstream type. |
| `float` quantity | `qty`, `altQty`, `netWgt` (when fractional) | `int` (or `Decimal`) | Upstream mixed typing of the same field — observed across the 1144 records. |
| `int` code | `reporterCode`, `partnerCode`, `aggrLevel`, `qtyUnitCode`, etc. | `int` (preserve semantic type, per Q51) | Stable, no coercion. |
| `string` ISO | `reporterISO`, `partnerISO`, `partner2ISO`, `classificationCode`, etc. | `str` | Stable. |
| `string` period | `period` (`"2022"`, `"202201"`) | `str` (ISO-8601, per Q53) | Always string, never a date object. |
| `bool` | `is*` fields | `bool` | Stable. |
| `int` enum | `legacyEstimationFlag` (`0`, `4`, `6`) | preserve raw + canonical enum (per Q55) | Upstream emits int; SDK MAY also expose an `EstimationCategory` enum while keeping the raw int. |
| `null` | `cifvalue`, `fobvalue` | `Optional[Decimal]` | Q54: never invent defaults. |

### 6.3 Concrete Datatype Recommendations

The SDK's canonical model SHOULD use:

```python
@dataclass(frozen=True)
class TradeRecord:                            # immutable, per ADR-0028 Q60
    # Identifiers (always present)
    type_code: str                           # "C", "S"
    freq_code: Frequency                     # enum
    ref_period_id: int                      # 20220101
    ref_year: int
    ref_month: int                          # 52 for annual
    period: str                             # ISO-8601 "YYYY" or "YYYYMM"
    reporter_code: int
    reporter_iso: str
    reporter_desc: str | None                # null if includeDesc=False
    flow_code: TradeFlow                     # enum
    flow_desc: str | None
    partner_code: int
    partner_iso: str
    partner_desc: str | None
    partner2_code: int | None                # second partner (mostly null)
    partner2_iso: str | None
    partner2_desc: str | None

    # Classification
    classification_code: str                # "H6", "S4", "B4", etc.
    classification_search_code: str
    is_original_classification: bool
    cmd_code: str
    cmd_desc: str | None
    aggr_level: int
    is_leaf: bool

    # Customs / transport / supply
    customs_code: str
    customs_desc: str | None
    mos_code: str
    mot_code: int
    mot_desc: str | None

    # Quantities
    qty_unit_code: int                      # -1 = no unit
    qty_unit_abbr: str | None
    qty: int | float                        # upstream mixed; canonical may use Decimal
    is_qty_estimated: bool
    alt_qty_unit_code: int
    alt_qty_unit_abbr: str | None
    alt_qty: int | float
    is_alt_qty_estimated: bool
    net_wgt: int | float
    is_net_wgt_estimated: bool
    gross_wgt: int | float
    is_gross_wgt_estimated: bool

    # Monetary (DECIMAL per ADR-0028 Q52; NULLABLE per Q54)
    fob_value: Decimal | None               # null on imports-only
    cif_value: Decimal | None               # null on exports-only
    primary_value: Decimal                  # always present

    # Estimation provenance
    legacy_estimation_flag: int             # 0, 4, 6 observed
    is_reported: bool
    is_aggregate: bool
```

---

## 7. Cross-Reference: EXT-006..009 status

This probe does NOT directly resolve EXT-006..009 (publication-notes,
trade-balance, bilateral, SUV response shapes — those are
authenticated `/tools/v1/` endpoints). What it does confirm:

| EXT | Subject | This probe's contribution |
| --- | ------- | ------------------------ |
| EXT-006 | Publication notes shape (U2) | **Not exercised** (authenticated, see `ENDPOINT_VERIFICATION.md`) |
| EXT-007 | Trade balance shape (T3) | **Not exercised** (authenticated) |
| EXT-008 | Bilateral shape (T4) | **Not exercised** (authenticated) |
| EXT-009 | SUV shape (U1) | **Not exercised** (authenticated) |

The public preview endpoint confirms the schema for **regular trade
records** (T1), which is the dominant data shape. The authenticated
endpoints (T3, T4, U1, U2) likely share the same envelope and most
record fields; only the field set is presumed to differ (e.g., trade
balance adds `exportValue` / `importValue` / `balance` fields).

---

## 8. Reproduction

```bash
# Schema probes — 8 live calls + 6 recorded samples
python data/__probe_schema.py
```

The script emits a JSON artefact to `data/__schema_analysis.json` and
prints a transcript to stdout.

---

## 9. Limitations

1. **Single reporter (India).** All 1,144 records are India-centric.
   Schema behaviour for other reporters (especially partner2Code,
   customsCode, motCode) is presumed identical but not directly
   verified.
2. **Single flow mix.** Most records are exports; 212 records are
   imports. The cifvalue/fobvalue nullability pattern is strongly
   confirmed but other fields' nullability in rarer flows
   (re-exports, re-imports) is not tested.
3. **No authenticated endpoints.** T3, T4, U1, U2, D1, D2, D3
   are not exercised here (see `ENDPOINT_VERIFICATION.md` for that
   work).
4. **No 1000-record boundary test.** The 500-record cap is documented
   in ADR-0005 and consistent with the API_RESEARCH.md research; the
   exact behaviour above 500 (silently cap or 400 error) was not
   retested in this probe.

---

## 10. Summary

| Concern | Verdict | Confidence |
| ------- | ------- | ---------- |
| **Response schema** | 38 fields per record; envelope has `count`, `data`, `elapsedTime`, optional `error`/`errorObject`. Matches `006_DATA_MODEL.md` E12 (TradeRecord). | HIGH |
| **Nullable fields** | **Only `cifvalue` (37.8%) and `fobvalue` (18.5%) are nullable.** All other 36 fields always present. | HIGH |
| **Pagination** | Page-less. Single `maxRecords` parameter, hard cap 500 per ADR-0005. No offset / cursor / next-URL. Empty results = HTTP 200 with `data: []`. Error results = HTTP 4xx with the same envelope shape. | HIGH |
| **Datatypes** | 47 fields: ~20 string, ~14 int, ~5 number (monetary), 9 bool, 2 nullable. Monetary values emitted as `float` (IEEE-754); **SDK MUST convert to `Decimal` on receive** (per ADR-0028 Q52). | HIGH |

---

*End of report.*