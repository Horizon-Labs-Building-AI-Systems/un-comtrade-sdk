# Implementation Baseline v1.0

| Field | Value |
| ----- | ----- |
| Document ID | 021 |
| Title | Implementation Baseline v1.0 |
| Version | 1.0 |
| Status | LIVE |
| Created | 2026-06-27T11:56:00Z |
| Last Updated | 2026-06-27T11:56:00Z |
| Author | Codex |
| Project | UN Comtrade Python SDK |
| Dependencies | All project documents |
| Supersedes | None |

---

## 1. Project Status

| Field | Value |
| ----- | ----- |
| Current Version | 0.1.0 (Documentation Phase complete) |
| Documentation Status | **COMPLETE** (21 documents in `docs/`; ~1.1 MB) |
| Architecture Status | **FROZEN** (36 ADRs, ADR-0001 through ADR-0036) |
| Verification Status | **COMPLETE** (4 empirical verification reports) |
| Implementation Status | **NOT STARTED** |
| MVP Scope | Synchronous Python client over `httpx`; 46 public methods; metadata + trade layers; DuckDB-first storage |

---

## 2. Source of Truth

**Project Governance**

- `docs/000_PROJECT_CHARTER.md`
- `docs/001_EXECUTION_PROTOCOL.md`
- `docs/002_CONTEXT.md`

**Architecture**

- `docs/003_ARCHITECTURE.md`
- `docs/DECISIONS.md` (ADRs)

**Specifications**

- `docs/004_API_RESEARCH.md`
- `docs/005_API_ENDPOINT_CATALOG.md`
- `docs/006_DATA_MODEL.md`
- `docs/007_SDK_SPECIFICATION.md`
- `docs/008_METADATA_LAYER_SPEC.md`
- `docs/009_TRADE_LAYER_SPEC.md`
- `docs/010_INFRASTRUCTURE_SPEC.md`
- `docs/011_ETL_SPECIFICATION.md`
- `docs/012_STORAGE_SPECIFICATION.md`
- `docs/013_TESTING_STANDARD.md`
- `docs/014_PACKAGING_SPECIFICATION.md`
- `docs/015_CODING_STANDARD.md`
- `docs/016_IMPLEMENTATION_ROADMAP.md`

**Tracking**

- `docs/CHANGELOG.md`
- `docs/TASK_LOG.md`
- `docs/PROJECT_CLARIFICATION_REGISTER.md`

**Verification Reports**

- `API_LIMITS_REPORT.md` (rate limits, EXT-001, EXT-002)
- `ENDPOINT_VERIFICATION.md` (D1/D2/D3 URLs, EXT-003/004/005)
- `SCHEMA_VERIFICATION.md` (response schema, EXT-006..009 partial)
- `FIELD_VERIFICATION.md` (`legacyEstimationFlag`, `aggrLevel`, `partner2Code`; EXT-010/011/012)

**Implementation**

- `docs/016_IMPLEMENTATION_ROADMAP.md` (10 phases)
- `docs/IMPLEMENTATION_BASELINE_v1.md` (this document — entry point)

---

## 3. Architecture Snapshot

The SDK is a 10-layer architecture with strict downward dependency.
Detail: `docs/003_ARCHITECTURE.md`.

| Layer | Module | Owns |
| ----- | ------ | ---- |
| Runtime | `un_comtrade.runtime` | configuration, transport, retry, timeout, cache, logging, errors |
| Client | `un_comtrade.client` | top-level `ComtradeClient` and its lifecycle |
| Metadata | `un_comtrade.metadata` | 17 reference catalogues; auto-init; case-insensitive search |
| Trade | `un_comtrade.trade` | unified annual + monthly model; hidden pagination; empty-collection semantics |
| Validation | `un_comtrade.validation` | client-side parameter checks before any upstream call |
| Normalisation | `un_comtrade.normalisation` | upstream-shape → canonical-model; isolated per ADR-0028 |
| Export | `un_comtrade.export` | canonical records → JSON / CSV / Parquet |
| Storage | `un_comtrade.storage` | DuckDB (default), Parquet (default export), JSON, CSV, optional PostgreSQL |
| Analytics | `un_comtrade.analytics` | derived fields; computed on read, never persisted |
| Application | `un_comtrade.cli` and `un_comtrade.__init__` | the public surface; CLI as `un-comtrade` console script |

**Runtime data flow:** Configuration → Transport → Client → (Metadata, Trade) → Normalisation → Export → Storage.

**Metadata flow:** Reference catalogue files (`/files/v1/app/reference/*.json`) → lazy fetch on first use → local cache in user cache directory → case-insensitive search.

**Trade flow:** Public preview endpoint (`/public/v1/preview/...`) or authenticated data endpoint (`/data/v1/get/...`) → response envelope (`count`, `data`, `elapsedTime`) → normalisation → `Decimal` monetary fields → canonical `TradeRecord` → storage or in-memory return.

**ETL pipeline:** 9 stages per `docs/011_ETL_SPECIFICATION.md`: validate, parse, normalise, deduplicate (latest-wins), enrich, partition, persist, verify, archive.

**Storage partition key:** `(reporter, year, frequency)` per ADR-0029.

---

## 4. Public SDK Surface

All 46 methods are defined in `docs/007_SDK_SPECIFICATION.md`.

### 4.1 Metadata (M01–M18)

`M01 get_countries`, `M02 get_country`, `M03 get_partners`, `M04 get_partner`,
`M05 get_classifications`, `M06 get_classification`, `M07 get_classification_editions`,
`M08 get_hs_codes`, `M09 get_hs_code`, `M10 search_hs`, `M11 get_trade_flows`,
`M12 get_transport_modes`, `M13 get_customs_procedures`, `M14 get_quantity_units`,
`M15 get_modes_of_supply`, `M16 get_frequencies`, `M17 get_data_items`, `M18 get_metadata`.

### 4.2 Trade (T01–T11)

`T01 get_exports`, `T02 get_imports`, `T03 get_trade`, `T04 get_trade_by_hs`,
`T05 get_world_trade`, `T06 get_trade_balance`, `T07 get_bilateral`,
`T08 get_trade_matrix`, `T09 get_monthly_exports`, `T10 get_monthly_imports`,
`T11 get_monthly_trade`.

### 4.3 Tariff-Line (F01–F02)

`F01 get_tariffline`, `F02 get_tariffline_by_hs`.

### 4.4 Preview (P01–P04)

`P01 preview_exports`, `P02 preview_imports`, `P03 preview_trade`,
`P04 preview_tariffline`.

### 4.5 Count (C01–C03)

`C01 count_exports`, `C02 count_imports`, `C03 count_trade`.

### 4.6 Async / Bulk (A01–A05)

`A01 submit_async_final_data`, `A02 check_async_request`,
`A03 download_async_request`, `A04 bulk_download_final_file`,
`A05 bulk_download_tariffline_file`.

### 4.7 Utility (U01–U03)

`U01 get_data_availability`, `U02 get_standard_unit_value`,
`U03 get_publication_notes`.

---

## 5. Frozen Decisions

36 ADRs are accepted. Full text in `docs/DECISIONS.md`.

| Category | ADR Range | Summary |
| -------- | --------- | ------- |
| Runtime | ADR-0001..0008 | Package name, layered architecture, snake_case, pagination, record caps, India code, reference catalogue, retry |
| SDK | ADR-0009..0015 | Conflict resolution, doc-first, preview casing, error hierarchy, line length, SemVer, API key |
| Metadata | ADR-0016..0019 | Phase transition, Python 3.11+, httpx, async deferred |
| Trade | ADR-0020..0024 | Stdlib JSON, public contract, retryable errors, timeout, caching |
| Data Model | ADR-0025..0028 | Logging, metadata invariants, trade semantics, canonical invariants |
| Infrastructure | ADR-0029..0032 | Storage, testing, packaging, documentation |
| Governance | ADR-0033..0036 | CI/CD, security, rate limit, daily cap |

---

## 6. Verified External API

Full detail in the four verification reports. Summary below.

| Aspect | Verdict | Report |
| ------ | ------- | ------ |
| Authentication | `subscription-key` query parameter; no API key on disk; SSL default-on | ADR-0034 |
| Metadata endpoints | 28 reference catalogue files at `/files/v1/app/reference/*.json` | `004_API_RESEARCH.md` §3 |
| Trade endpoints | Public preview at `/public/v1/preview/{type}/{freq}/{cl}`; auth at `/data/v1/get/{type}/{freq}/{cl}` | `004_API_RESEARCH.md` §3 |
| Rate limits | Token-bucket, ≈1 req/s refill, ≈2–3 burst, `Retry-After: 1` on 429 | `API_LIMITS_REPORT.md` §3, ADR-0035 |
| Daily cap | Free tier 50,000,000 records/day; per-call 500 (preview) / 250,000 (auth) | `API_LIMITS_REPORT.md` §4, ADR-0036 |
| Pagination | Page-less preview; split on `period` (ADR-0004); no offset / cursor / next-URL | `SCHEMA_VERIFICATION.md` §5 |
| Schema | 38 fields per `TradeRecord`; envelope `count`, `data`, `elapsedTime` | `SCHEMA_VERIFICATION.md` §3 |
| Nullable fields | `cifvalue` (37.8% null) and `fobvalue` (18.5% null) only | `SCHEMA_VERIFICATION.md` §4 |
| Field semantics | `aggrLevel` = HS hierarchy depth (0/2/4/6); `legacyEstimationFlag` ∈ {0,4,6}; `partner2Code` ignored on classic preview | `FIELD_VERIFICATION.md` §3–§5 |

**Remaining open external items:** 10 (in `PROJECT_CLARIFICATION_REGISTER.md` §15.2). All require either a subscription key or the upstream developer portal.

---

## 7. Implementation Order

Approved sequence in `docs/016_IMPLEMENTATION_ROADMAP.md`. Phase names only.

1. Project Skeleton
2. Configuration
3. Transport Layer
4. Authentication
5. Exceptions
6. Logging
7. Metadata Layer
8. Trade Layer
9. ETL
10. Storage
11. CLI
12. Testing
13. Release

---

## 8. Definition of Done

Any implementation task is complete when:

1. Specification implemented per the relevant document.
2. Unit tests written per `docs/013_TESTING_STANDARD.md`.
3. Public methods documented per `docs/015_CODING_STANDARD.md`.
4. `docs/CHANGELOG.md` updated with the change.
5. `docs/TASK_LOG.md` updated with the task entry.
6. `docs/002_CONTEXT.md` updated if project status changed.
7. `docs/DECISIONS.md` updated if a new architectural decision was made.
8. `pyproject.toml` updated if dependencies changed.
9. Existing tests pass; new tests pass; coverage of new code ≥ 80%.
10. Phase gate criteria from `016_IMPLEMENTATION_ROADMAP.md` satisfied.

---

## 9. Implementation Authorization

```text
Documentation
COMPLETE

Architecture
FROZEN

Verification
COMPLETE

Implementation
AUTHORIZED
```

---

*End of document.*