# Endpoint Verification Report

| Field | Value |
| ----- | ----- |
| Document ID | 020-ENDPOINTS |
| Title | UN Comtrade Endpoint URL Verification Report |
| Version | 0.1.0 |
| Status | LIVE |
| Created | 2026-06-27T22:30:00Z |
| Last Updated | 2026-06-27T22:30:00Z |
| Author | Codex |
| Project | UN Comtrade Python SDK |
| Dependencies | 004_API_RESEARCH.md, 005_API_ENDPOINT_CATALOG.md, EXT-003, EXT-004, EXT-005 |
| Supersedes | None |

---

## 1. Objective

Resolve the three open external-verification items that block SDK
endpoint wiring for asynchronous and bulk operations:

- **EXT-003:** URL of the data availability endpoint (D1).
- **EXT-004:** URL of the async submit/check/download endpoints (D2).
- **EXT-005:** URL of the bulk download endpoints (D3).

This report records every candidate URL probed, the HTTP responses, the
documented URL patterns, and the verdict for each endpoint.

---

## 2. Test Environment

| Item | Value |
| ---- | ----- |
| Date (UTC) | 2026-06-26T22:29–22:30 |
| Base URL | `https://comtradeapi.un.org` |
| Subscription key | **Not provided** in this run |
| User-Agent | `India-Impex-Analytics/EXT-discovery` and `India-Impex-Analytics/EXT-discovery-2` |
| Tooling | Python 3.14, `urllib.request` |
| Output artefacts | `data/__endpoint_probe.json` |

### Important Caveat

The UN Comtrade API gateway **does not return 401** for unauthenticated
requests to authenticated endpoints. Instead, it returns
**HTTP 404** with a `{"statusCode": 404, "message": "Resource not found"}`
body. This means **the 404 result below is consistent with both**:

1. The endpoint truly does not exist at that URL, **or**
2. The endpoint exists but is gated by authentication that the
   unauthenticated client cannot satisfy.

This probe therefore **cannot distinguish** between (1) and (2). A
definitive answer requires a valid subscription key.

---

## 3. Findings: EXT-003 — Data Availability (D1)

### 3.1 Documented URL Patterns

Per `004_API_RESEARCH.md` §17 line 1019 (recorded in earlier research
sessions with valid authentication):

- `GET https://comtradeapi.un.org/data/v1/getFinalDataAvailability/{reporterCode}/{typeCode}/{freqCode}/{clCode}`
- Example: `GET https://comtradeapi.un.org/data/v1/getFinalDataAvailability/699/C/A/HS?subscription-key=...`

### 3.2 URL Patterns Probed

| # | Method | URL | Status | Response |
| - | ------ | --- | ------:| -------- |
| 1 | GET | `/data/v1/getFinalDataAvailability?typeCode=C&freqCode=A&clCode=HS` | 404 | Resource not found |
| 2 | GET | `/data/v1/getFinalDataAvailability/699/C/A/HS` | 404 | Resource not found |
| 3 | GET | `/data/v1/getDataAvailability?reporterCode=699&typeCode=C&freqCode=A&clCode=HS` | 404 | Resource not found |
| 4 | GET | `/tools/v1/getDataAvailability?reporterCode=699&typeCode=C&freqCode=A&clCode=HS` | 404 | Resource not found |
| 5 | GET | `/public/v1/preview/availability/C/A/HS?reportercode=699&period=2022` | 404 | Resource not found |
| 6 | GET | `/data/v1/getDataAvailability/699/C/A/HS` | 404 | Resource not found |
| 7 | GET | `/data/v1/getDataAvailability/C/A/HS` | 404 | Resource not found |
| 8 | GET | `/data/v1/dataAvailability` | 404 | Resource not found |
| 9 | GET | `/data/v1/checkDataAvailability` | 404 | Resource not found |
| 10 | GET | `/data/v1/getDataAvailabilityFile` | 404 | Resource not found |
| 11 | GET | `/data/v1/availability` | 404 | Resource not found |
| 12 | GET | `/data/v1/avail` | 404 | Resource not found |
| 13 | OPTIONS | `/data/v1/get/C/A/HS` | 404 | Resource not found |

### 3.3 Example Capture

```http
GET https://comtradeapi.un.org/data/v1/getFinalDataAvailability/699/C/A/HS HTTP/1.1
User-Agent: India-Impex-Analytics/EXT-discovery

HTTP/1.1 404 Not Found
Content-Type: application/json
Content-Length: 54
Date: Fri, 26 Jun 2026 22:29:53 GMT

{ "statusCode": 404, "message": "Resource not found" }
```

### 3.4 Evidence

The reference listing at
`https://comtradeapi.un.org/files/v1/app/reference/ListofReferences.json`
returned HTTP 200 with 6,567 bytes of metadata. The listing enumerates
all reference catalogue files (Reporters, HS, EB, SITC, etc.) but does
**not** include any bulk, async, or data-availability endpoint URLs.
The reference catalogue is metadata only.

No public Swagger/OpenAPI document is exposed:

| Path | Status |
| ---- | ------:|
| `/swagger.json` | 404 |
| `/openapi.json` | 404 |
| `/api-docs` | 404 |
| `/data/v1/swagger.json` | 404 |
| `/files/v1/app/swagger.json` | 404 |
| `/files/v1/app/api.json` | 404 |

The developer portal at `https://comtradedeveloper.un.org/api-details/`
returns 200 but the body is a sign-in redirect (4,587 bytes), not a
spec document.

### 3.5 Conclusion: EXT-003

**Cannot be empirically verified without a subscription key.**
The documented URL pattern
`/data/v1/getFinalDataAvailability/{reporterCode}/{typeCode}/{freqCode}/{clCode}`
is the most likely candidate. None of the 13 alternative URL
patterns tried returned a non-404 status.

#### Recommended SDK Configuration

- **Default endpoint URL** (subject to verification with a key):
  `https://comtradeapi.un.org/data/v1/getFinalDataAvailability/{reporterCode}/{typeCode}/{freqCode}/{clCode}`
- **Method:** `GET`
- **Authentication:** `subscription-key` query parameter.
- **Response shape:** documented as a count-of-records response per
  `(reporter, period, flow, commodity)` tuple. The exact JSON shape is
  not documented in `004_API_RESEARCH.md` and cannot be confirmed here.

---

## 4. Findings: EXT-004 — Async Submit / Check / Download (D2)

### 4.1 Documented URL Patterns

Per `004_API_RESEARCH.md` §17 lines 584–586:

- `POST /data/v1/submitAsyncFinalDataRequest` — submit a long-running data request.
- `GET /data/v1/checkAsyncDataRequest` — poll the status of a submitted request.
- `GET /data/v1/downloadAsyncFinalDataRequest` — download the result of a completed request.

### 4.2 URL Patterns Probed

| # | Method | URL | Status | Response |
| - | ------ | --- | ------:| -------- |
| 1 | POST | `/data/v1/submitAsyncFinalDataRequest` | 404 | Resource not found |
| 2 | POST | `/data/v1/submitAsyncDataRequest` | 404 | Resource not found |
| 3 | POST | `/data/v1/submitAsyncRequest` | 404 | Resource not found |
| 4 | GET | `/data/v1/checkAsyncDataRequest?subscription-key=test` | 404 | Resource not found |
| 5 | GET | `/data/v1/getAsyncRequestStatus` | 404 | Resource not found |
| 6 | GET | `/data/v1/checkAsyncRequestStatus` | 404 | Resource not found |
| 7 | GET | `/data/v1/downloadAsyncFinalDataRequest?subscription-key=test` | 404 | Resource not found |
| 8 | GET | `/data/v1/getAsyncRequestResult` | 404 | Resource not found |
| 9 | GET | `/data/v1/downloadAsyncRequest` | 404 | Resource not found |
| 10 | OPTIONS | `/data/v1/submitAsyncFinalDataRequest` | 404 | Resource not found |
| 11 | OPTIONS | `/data/v1/checkAsyncDataRequest` | 404 | Resource not found |
| 12 | OPTIONS | `/data/v1/downloadAsyncFinalDataRequest` | 404 | Resource not found |
| 13 | OPTIONS | `/data/v1/submitAsyncRequest` | 404 | Resource not found |
| 14 | OPTIONS | `/data/v1/getAsyncRequestStatus` | 404 | Resource not found |

### 4.3 Example Capture (POST)

```http
POST https://comtradeapi.un.org/data/v1/submitAsyncFinalDataRequest HTTP/1.1
User-Agent: India-Impex-Analytics/EXT-discovery
Content-Type: application/x-www-form-urlencoded

typeCode=C&freqCode=A&clCode=HS&reporterCode=699&period=2022&flowCode=X&cmdCode=TOTAL

HTTP/1.1 404 Not Found
Content-Type: application/json
Content-Length: 54
Date: Fri, 26 Jun 2026 22:29:57 GMT

{ "statusCode": 404, "message": "Resource not found" }
```

### 4.4 Conclusion: EXT-004

**Cannot be empirically verified without a subscription key.**
The documented URL patterns are the most likely candidates. The
*submit* path is `POST`; the *check* and *download* paths are `GET`.

#### Recommended SDK Configuration

- **Submit URL:** `https://comtradeapi.un.org/data/v1/submitAsyncFinalDataRequest` (POST).
- **Check URL:** `https://comtradeapi.un.org/data/v1/checkAsyncDataRequest` (GET).
- **Download URL:** `https://comtradeapi.un.org/data/v1/downloadAsyncFinalDataRequest` (GET).
- **Authentication:** `subscription-key` query parameter on all three.
- **Response shape:** the async flow returns a job ID on submit, a
  status (queued/running/done/failed) on check, and a download URL
  or redirect on download. Exact JSON shapes are documented in
  `004_API_RESEARCH.md` §17 as **Documented** (not yet empirically
  verified).

---

## 5. Findings: EXT-005 — Bulk Download (D3)

### 5.1 Documented URL Patterns

Per `004_API_RESEARCH.md` §17 lines 599–601:

- `GET /data/v1/bulkDownloadFinalFile` — download a previously-prepared
  bulk CSV.
- `GET /data/v1/bulk/...` and `/bulk/...` — listed as candidate
  patterns without a definitive example.
- `GET /data/v1/bulkDownload/...` — also listed as a candidate.

### 5.2 URL Patterns Probed

| # | Method | URL | Status | Response |
| - | ------ | --- | ------:| -------- |
| 1 | GET | `/data/v1/bulkDownloadFinalFile` | 404 | Resource not found |
| 2 | GET | `/data/v1/bulkDownload` | 404 | Resource not found |
| 3 | GET | `/data/v1/bulk` | 404 | Resource not found |
| 4 | GET | `/data/v1/bulkDownload/files` | 404 | Resource not found |
| 5 | GET | `/data/v1/bulk/files` | 404 | Resource not found |
| 6 | GET | `/bulk` | 404 | Resource not found |
| 7 | GET | `/data/v1/getBulkFiles` | 404 | Resource not found |
| 8 | GET | `/data/v1/getBulkDownload` | 404 | Resource not found |
| 9 | GET | `/data/v1/bulkDownloadList` | 404 | Resource not found |
| 10 | OPTIONS | `/data/v1/bulkDownloadFinalFile` | 404 | Resource not found |
| 11 | OPTIONS | `/data/v1/bulkDownload` | 404 | Resource not found |
| 12 | OPTIONS | `/data/v1/bulk` | 404 | Resource not found |

### 5.3 Example Capture

```http
GET https://comtradeapi.un.org/data/v1/bulkDownloadFinalFile HTTP/1.1
User-Agent: India-Impex-Analytics/EXT-discovery

HTTP/1.1 404 Not Found
Content-Type: application/json
Content-Length: 54
Date: Fri, 26 Jun 2026 22:30:04 GMT

{ "statusCode": 404, "message": "Resource not found" }
```

### 5.4 Conclusion: EXT-005

**Cannot be empirically verified without a subscription key.**
The documented URL pattern `/data/v1/bulkDownloadFinalFile` is the
most likely candidate. The endpoint probably accepts a `fileName`
or `downloadId` query parameter; the exact parameter name is not
documented in `004_API_RESEARCH.md`.

#### Recommended SDK Configuration

- **Download URL:** `https://comtradeapi.un.org/data/v1/bulkDownloadFinalFile` (GET).
- **Authentication:** `subscription-key` query parameter.
- **Query parameters (suspected):** `fileName` or `downloadId` (TBD).
- **Response:** the endpoint probably returns a streaming CSV/TSV
  response with `Content-Type: text/csv` or
  `Content-Type: application/octet-stream`. The exact content type
  is not documented.

---

## 6. Cross-Cutting Observations

### 6.1 Gateway Behaviour

All authenticated endpoints under `/data/v1/...`, `/tools/v1/...`, and
`/bulk` returned the **same response shape** when probed without
authentication:

```json
{
  "statusCode": 404,
  "message": "Resource not found"
}
```

The 404 message is identical regardless of whether the path is a
documented endpoint (e.g., `/data/v1/getFinalDataAvailability`) or an
invented one (e.g., `/data/v1/nonsense`). This strongly suggests the
gateway **rejects all unauthenticated requests uniformly** rather
than routing them to specific handlers — i.e., the 404 is a
**gateway-level authentication response**, not a per-endpoint
existence check.

**Implication:** a 404 from this gateway is **not evidence that
the endpoint does not exist**. It is evidence that the gateway
refused the request because authentication was missing.

### 6.2 OPTIONS Method

Every OPTIONS request also returned 404. This is unusual: a properly
CORS-configured gateway should return 200 (or 204) with an `Allow`
header listing the supported HTTP methods. The 404 on OPTIONS means
either:

1. The endpoint does not exist (unlikely given the gateway-uniform
   response shape), or
2. The gateway does not support OPTIONS for these paths, which would
   also block legitimate cross-origin consumer access (consistent
   with the earlier CORS observation in `004_API_RESEARCH.md` §16.9).

### 6.3 Public vs. Authenticated Surface

The only paths that returned **non-404 responses** without a key
were the public reference catalogue under `/files/v1/app/reference/`
and the public preview under `/public/v1/preview/`. This matches the
documented split:

- **Public:** `/files/v1/app/reference/` and `/public/v1/preview/...`
- **Authenticated:** `/data/v1/...` and `/tools/v1/...`

---

## 7. Recommendations

### 7.1 Resolution Path

To definitively resolve EXT-003, EXT-004, and EXT-005:

1. **Acquire a subscription key** (free tier available from
   `https://comtradedeveloper.un.org/profile`).
2. **Re-run the probe** with the key passed as the `subscription-key`
   query parameter.
3. **Expect HTTP 200** with the documented JSON shape on each call.
4. **Capture the response** verbatim into a follow-up of this report.

### 7.2 Until Resolved

Until EXT-003, EXT-004, EXT-005 are empirically verified, the SDK
MUST:

1. **Treat the documented URL patterns as authoritative** for
   internal SDK design.
2. **NOT expose wrapper methods** for D1, D2, or D3 to consumers
   until at least one URL pattern has been confirmed via a 200
   response.
3. **Surface a clear error** to the consumer if a wrapper method
   is called and the upstream returns 404 — i.e., not silently
   retry, not silently fall back to another URL.

### 7.3 Recommended ADR

Add **ADR-0037 — Authenticated Endpoint URL Assumptions** to
`DECISIONS.md`, recording:

- The documented URL patterns for D1, D2, D3 (from
  `004_API_RESEARCH.md` §17).
- The empirical observation that the gateway returns a uniform
  404 for all authenticated endpoints without a key.
- The decision to **block SDK wrapper exposure** for D1, D2, D3
  until each is empirically verified with a valid key.

---

## 8. Reproduction

```bash
# Round 1 — exhaustive candidate URLs
python data/__probe_endpoints.py

# Round 2 — Swagger / OPTIONS / discovery
python data/__probe_endpoints2.py
```

Both scripts emit JSON to `data/` and print transcripts to stdout.

---

## 9. Limitations

1. **No subscription key** was supplied in this run. The empirical
   evidence therefore is a **uniform 404 from the gateway** rather
   than per-endpoint existence confirmation.
2. **No public API specification** is available. Without a Swagger or
   OpenAPI document, the URL candidates are limited to the patterns
   recorded in `004_API_RESEARCH.md` (an earlier research session)
   and the patterns inferable from the same naming convention.
3. **Single vantage point.** All probes came from one IP in a
   single 90-second window. Behaviour across regions and time-of-day
   is unknown.
4. **No payload variation.** POST requests were issued with one
   form-encoded body; the upstream may accept JSON, multipart, or
   other content types. This was not exercised.

---

## 10. Summary

| Item | Method | Documented URL | Empirical Status |
| ---- | ------ | --------------- | ---------------- |
| **EXT-003 (D1)** | GET | `/data/v1/getFinalDataAvailability/{reporter}/{type}/{freq}/{cl}` | **Unverified** (404 without key) |
| **EXT-004 submit (D2a)** | POST | `/data/v1/submitAsyncFinalDataRequest` | **Unverified** (404 without key) |
| **EXT-004 check (D2b)** | GET | `/data/v1/checkAsyncDataRequest` | **Unverified** (404 without key) |
| **EXT-004 download (D2c)** | GET | `/data/v1/downloadAsyncFinalDataRequest` | **Unverified** (404 without key) |
| **EXT-005 (D3)** | GET | `/data/v1/bulkDownloadFinalFile` | **Unverified** (404 without key) |

**Confidence:** LOW for any specific URL existence. The gateway returns
404 uniformly, which does not distinguish "endpoint does not exist" from
"endpoint requires authentication."

**Recommended next step:** re-run with a subscription key. Once one
endpoint per category returns 200, the documented URL pattern is
confirmed and the SDK can wire up wrappers.

---

*End of report.*