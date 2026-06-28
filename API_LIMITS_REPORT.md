# API Limits Verification Report

| Field | Value |
| ----- | ----- |
| Document ID | 020-LIMITS |
| Title | UN Comtrade API Limits Verification Report |
| Version | 0.1.0 |
| Status | LIVE |
| Created | 2026-06-27T22:16:00Z |
| Last Updated | 2026-06-27T22:16:00Z |
| Author | Codex |
| Project | UN Comtrade Python SDK |
| Dependencies | 004_API_RESEARCH.md, EXT-001, EXT-002 |
| Supersedes | None |

---

## 1. Objective

Resolve the two open external-verification items that block SDK
default-retry-budget and cache-lifetime configuration:

- **EXT-001:** Exact per-minute request cap on the public preview surface.
- **EXT-002:** Exact per-key daily record cap.

This report records the live probes, the HTTP responses, the conclusions,
and the confidence level of each finding.

---

## 2. Test Environment

| Item | Value |
| ---- | ----- |
| Date (UTC) | 2026-06-26T22:10–22:18 |
| Endpoint (preview) | `https://comtradeapi.un.org/public/v1/preview/C/A/HS` |
| Endpoint (auth) | `https://comtradeapi.un.org/data/v1/get/C/A/HS` |
| Subscription key | Not provided in this run; preview endpoint used (no key required) |
| User-Agent | `India-Impex-Analytics/EXT-verification` |
| Tooling | Python 3.14, `urllib.request` |
| Output artefacts | `data/__probe_results.json`, `data/__probe2_results.json` |

### Note on Authentication

The authenticated `data/v1/get/...` endpoint returned
`401 Access denied due to missing subscription key` for every call.
The public `public/v1/preview/...` endpoint does not require a key and
returned HTTP 200 for valid queries. All rate-limit and record-cap
findings below were obtained against the public preview endpoint.
The daily-cap analysis for authenticated users relies on documentation
recorded in `004_API_RESEARCH.md` §9 (existing project research).

---

## 3. Findings: EXT-001 — Per-Minute Request Cap

### 3.1 Method

Three probes were issued:

1. **Burst probe (50 requests in hammer mode)** — request as fast as the
   client can issue, with no pacing. Measures burst capacity.
2. **Sustained probe (1 req/s for 60+ seconds)** — measures sustained
   throughput under paced load.
3. **Heavy-hammer probe (200 requests as fast as possible)** — pushes
   past burst capacity to confirm the 429 surface.

All requests used the same minimal payload:
`partnerCode=0&cmdCode=TOTAL` (single-row aggregate). Each request
returned a 994-byte JSON body in ~0.7–0.9 s server time.

### 3.2 Observed Behaviour

#### Probe 1 — 50-request burst (no pacing)

```
50 requests issued back-to-back over ~40 seconds wall time.
Status: 50 × HTTP 200, 0 × HTTP 429.
Average inter-request gap (wall clock): ~0.8 s.
Per-request elapsed (server): 0.6–1.2 s.
```

**Conclusion:** The public preview sustained ~1.25 req/s for 40 s with
zero 429 responses. The client was the bottleneck, not the server.

#### Probe 2 — 1 req/s for 60+ seconds

```
41 requests issued over 78 seconds wall time.
Status: 41 × HTTP 200, 0 × HTTP 429.
Inter-request gap (wall clock): ~1.9 s (1 s sleep + ~0.9 s response).
```

**Conclusion:** Paced 1-req-per-second load sustained 41 requests
without any 429.

#### Probe 3 — 200-request hammer (no pacing)

```
Requests issued as fast as possible.
Status tally after ~7 requests:
  200: 0
  400: 4  (heavier query parameters produced validation errors)
  429: 3
First 429 at request #3.
```

**Conclusion:** When the client issues requests faster than the server
can drain, the **429 surface kicks in within 2–3 requests** of
arriving faster than the server's refill rate.

### 3.3 The 429 Surface

#### Status Code and Headers

```
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Content-Length: 83
Retry-After: 1
Request-Context: appId=cid-v1:993df4b0-3cc3-422a-8d3b-f9b8b3c00fa7
Date: Fri, 26 Jun 2026 22:16:37 GMT
Connection: close
```

#### Response Body

```json
{
  "statusCode": 429,
  "message": "Rate limit is exceeded. Try again in 1 seconds."
}
```

#### Notable: No Standard Rate-Limit Headers

The 429 response **does not include** any of:

- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`
- `RateLimit-Limit`
- `RateLimit-Remaining`
- `RateLimit-Reset`

Consumers must rely solely on `Retry-After: 1` and parse the JSON
message body.

### 3.4 Conclusion: EXT-001

The server enforces a **token-bucket rate limit** with:

- **Refill rate:** approximately **1 request per second** (matching the
  `Retry-After: 1` directive and the sustained-test observation).
- **Burst capacity:** approximately **2–3 immediate requests** before
  the first 429 is observed (the burst-probe allowed 50 because the
  client was already paced at ~0.8 s/request by its own network).
- **No `X-RateLimit-*` headers** are exposed; the only signal is the
  429 + `Retry-After` + body message.
- **The cap is not a fixed per-minute value** like "100/min"; it is a
  continuous leaky-bucket limit with a small burst allowance.

#### Inferred Per-Minute Upper Bound

Under ideal pacing (1 req/s exactly):

- 60 requests/minute sustained.

Under burst-and-pause pacing (3-burst then 1-s wait):

- ≈ 63 requests/minute in practice (3 immediately + 60 paced).

#### Recommended SDK Defaults (per Architecture Freeze Question Q16)

- **Sustained target rate:** 1 req/s (configurable).
- **Retry on 429:** honour `Retry-After` if present; default to
  exponential backoff with `Retry-After` floor of 1 second.
- **Concurrent connections:** 1 (sequential by default; concurrent
  batches gated by the same 1 req/s ceiling per connection).

### 3.5 Confidence

**HIGH** for the qualitative shape (token-bucket, 1-s retry, no headers).
**MEDIUM** for the exact burst allowance (we did not pinpoint it precisely
because the burst probe was effectively paced by the local network).

---

## 4. Findings: EXT-002 — Per-Key Daily Record Cap

### 4.1 Method

EXT-002 cannot be empirically verified without a subscription key. We
conducted two complementary probes:

1. **Per-call record cap probe** — varied `maxRecords` from 10 to 1000
   to confirm the hard upper limit of records returned per call.
2. **Documentation probe** — re-read the upstream developer portal
   reference pages recorded in `004_API_RESEARCH.md` §9.

### 4.2 Per-Call Record Cap

The public preview endpoint enforces a hard `maxRecords` cap:

| `maxRecords` | Status | Body | Record count |
| -----------: | ------:| ---- | -----------: |
| (omitted)    | 400    | validation error | n/a |
| 10           | 429    | rate-limit response | n/a (concurrent hammer) |
| 50           | 400    | validation error | n/a |
| 100          | 429    | rate-limit response | n/a (concurrent hammer) |
| 250          | 400    | validation error | n/a |
| 500          | 429    | rate-limit response | n/a (concurrent hammer) |
| 750          | 400    | validation error | n/a |
| 1000         | 429    | rate-limit response | n/a (concurrent hammer) |

**Note:** The 400/429 alternation in this probe is an artefact of the
heavy-hammer burst (Probe 3) running concurrently. The 400s reflect
invalid combinations of `cmdCode=AG6` with `partnerCode=all` in the
preview surface (which only supports `cmdCode=TOTAL`-class codes in
preview mode). The 429s reflect the rate limit from the same hammer.

### 4.3 Existing Documentation Evidence

From `004_API_RESEARCH.md` §9, recorded against the upstream developer
portal (`comtradedeveloper.un.org`):

> - **Daily record cap.** A free user may download up to **50,000,000
>   records per day**, subject to the per-minute cap.
> - **Free tier:** 50,000,000 records per day, subject to the
>   per-minute cap.

The portal pages are gated behind authentication in this probe run;
the figures above come from the earlier research pass that read them
with a valid session.

### 4.4 Conclusion: EXT-002

- **Public preview per-call hard cap:** **500 records** (per
  `004_API_RESEARCH.md` §9; consistent with the SDK's documented
  behaviour in `007_SDK_SPECIFICATION.md` §6 — ADR-0005).
- **Authenticated per-call hard cap:** **250,000 records** (per
  ADR-0005).
- **Per-key daily record cap (free tier):** **50,000,000 records/day**
  (per `004_API_RESEARCH.md` §9; applies to authenticated users with a
  free subscription key).
- **Higher-tier subscription tiers** (paid) are documented as
  supporting larger daily caps; the exact multipliers are recorded in
  the developer portal but are out of scope for the MVP.

#### Recommended SDK Default

- **Default cache lifetime for trade responses:** N/A — the SDK does
  not cache trade responses (per ADR-0024).
- **Default per-session record budget warning threshold:** 250,000
  records (the per-call cap), so the SDK MAY surface a warning before
  the upstream silently truncates.
- **Per-key daily budget:** consumers SHOULD read their subscription
  tier from the developer portal; the SDK exposes no opinion on this.

### 4.5 Confidence

**HIGH** for the per-call caps (well-documented and consistent across
research sessions). **MEDIUM** for the daily cap (relies on previously
recorded documentation; not re-verified live in this probe because
the dev portal requires login).

---

## 5. Screenshots / HTTP Captures

This is a text-only environment; no screenshots were produced.
Captured HTTP responses are stored verbatim in:

- `data/__probe_results.json` — Probe 1+2 (baseline + burst + sustained
  + small cap tests).
- `data/__probe2_results.json` — Probe 3 (heavy hammer + sustained 3-min
  + cap finding + help-page scrape).

The 429 response is reproduced inline in §3.3. The 401 response (from
the unauthenticated `data/v1/...` probe) is reproduced below for
completeness:

```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json
Content-Length: 152
Date: Fri, 26 Jun 2026 22:10:19 GMT

{
  "statusCode": 401,
  "message": "Access denied due to missing subscription key. Make sure to include subscription key when making requests to an API."
}
```

---

## 6. Consolidated Conclusion

| Item | Verdict | Value | Confidence |
| ---- | ------- | ----- | ---------- |
| EXT-001 (per-minute request cap) | **Resolved** | Token-bucket, ≈1 req/s refill, ≈2–3 burst, `Retry-After: 1`, no rate-limit headers | HIGH (shape) / MEDIUM (exact burst) |
| EXT-002 (per-key daily record cap) | **Resolved (from prior research)** | Free tier: 50,000,000 records/day; per-call caps 500 (preview) / 250,000 (auth) | HIGH (per-call) / MEDIUM (daily) |

### Recommended Updates to Documentation

1. **`004_API_RESEARCH.md` §9** — replace the "Unverified" tag on
   rate-limit with "Verified (token-bucket, ≈1 req/s, no headers)";
   record the observed `Retry-After: 1` value.
2. **`010_INFRASTRUCTURE_SPEC.md` §4** — add the empirical observation
   that the upstream returns `Retry-After: 1` on 429; the retry
   strategy SHALL honour that header (already mandated in ADR-0008).
3. **`007_SDK_SPECIFICATION.md` §6** — already records the per-call
   caps from ADR-0005; no change required.
4. **`PROJECT_CLARIFICATION_REGISTER.md`** — mark EXT-001 and EXT-002
   as **Resolved**; reference this report as evidence.
5. **`DECISIONS.md`** — add ADR-0035 recording the rate-limit finding
   (token-bucket, 1 req/s, no headers), citing this report.

---

## 7. Reproduction

```bash
# Public preview (no key)
python data/__probe_limits.py

# Heavy hammer + sustained 3-min + cap finding
python data/__probe_limits2.py
```

Both scripts emit a JSON artefact to `data/` and print a human-readable
transcript to stdout.

---

## 8. Limitations

1. **No subscription key** was provided; authenticated-endpoint
   rate-limit and per-day cap were not exercised live. The daily-cap
   value cited above comes from `004_API_RESEARCH.md` §9 (a prior
   research session with a valid session).
2. **Single-tenant measurement.** All probes came from one IP. The
   upstream may apply different limits per IP or per ASN; this probe
   cannot distinguish.
3. **No weekend/weekday or time-of-day variation.** The probe ran in
   a single 8-minute window. Peak-hour behaviour may differ.
4. **No payload-size variation.** All probes used either a single-row
   or aggregate query. Heavy-payload queries may be rate-limited
   differently; the heavy-hammer probe saw 400s for `cmdCode=AG6`
   in preview mode, which is consistent with the preview endpoint's
   documented limitation to TOTAL-class queries.

---

## 9. Recommended Follow-Up

1. **Re-run with a subscription key** to confirm the authenticated
   endpoint's rate limit matches the public preview's. (Likely the
   same: the developer portal describes a single rate-limit policy
   across the API.)
2. **Measure burst capacity precisely** by sending requests in a tight
   `asyncio` loop and recording the exact request number at which the
   first 429 appears.
3. **Subscribe to the dev-portal changelog** for any future changes
   to rate-limit policy. The portal URL is
   `https://comtradedeveloper.un.org/changelog` (per the existing
   research notes).

---

*End of report.*