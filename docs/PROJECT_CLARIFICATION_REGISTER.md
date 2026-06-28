# Project Clarification Register

| Field | Value |
| ----- | ----- |
| Document ID | 020 |
| Title | Project Clarification Register |
| Version | 0.1.0 |
| Status | LIVE |
| Created | 2026-06-27T21:13:00Z |
| Last Updated | 2026-06-28T22:45:00Z |
| Author | Codex |
| Project | UN Comtrade Python SDK |
| Dependencies | 003_ARCHITECTURE.md, 004_API_RESEARCH.md, 006_DATA_MODEL.md, 007_SDK_SPECIFICATION.md, 008_METADATA_LAYER_SPEC.md, 009_TRADE_LAYER_SPEC.md, 010_INFRASTRUCTURE_SPEC.md, 011_ETL_SPECIFICATION.md, 012_STORAGE_SPECIFICATION.md, 013_TESTING_STANDARD.md, 014_PACKAGING_SPECIFICATION.md, 015_CODING_STANDARD.md, 016_IMPLEMENTATION_ROADMAP.md, CHANGELOG.md, TASK_LOG.md, DECISIONS.md |
| Supersedes | None |

---

## 1. Executive Summary

This document is the authoritative consolidation of every unresolved clarification in the project. It is the single master list of pending engineering decisions and is consumed by every downstream implementation phase.

### 1.1 Inventory

- **Total documentation reviewed:** 20 documents (numbered 000 through 016 plus CHANGELOG, TASK_LOG, DECISIONS, and the CONTEXT document, totalling approximately 941 KB and 19,300+ lines).
- **Total unique open questions discovered:** 131 (`OQ-*` IDs across 14 documents).
- **Total cross-referenced mentions:** 142 (some `OQ-*` IDs appear in more than one document).
- **Duplicate questions merged:** 8 entries collapsed into 8 duplicates, leaving 123 unique questions.

### 1.2 Blocking Profile

- **Blocking:** 30 (22%).
- **Partially blocking:** 14 (10%).
- **Non-blocking:** 85 (64%).
- **Already resolved:** 2 (1%).

### 1.3 Priority Profile

- **High:** 30.
- **Medium:** 59.
- **Low:** 42.

### 1.4 Implementation Readiness

- **Documentation readiness score:** approximately 88%.
- **Implementation readiness:** **Not Ready** — 30 high-priority clarifications must be resolved (or explicitly deferred with a recorded decision) before Phase 1 (SDK Foundation) starts.

The 30 High-priority clarifications cluster around five critical axes:

1. **Upstream API surface uncertainty** (per-minute request cap, per-key daily record cap, data-availability URL, publication-notes shape, trade-balance shape, bilateral shape, SUV shape). Without verified values, default retry budgets and default cache lifetimes cannot be finalised.
2. **Tooling framework choices** (lint, format, type-check, documentation, testing). Without explicit choices, Phase 1 cannot create `pyproject.toml` or CI configuration.
3. **CI/CD pipeline and package index** (CI provider, package index, documentation site, signing key). Without explicit choices, Phase 8 (Packaging) cannot publish.
4. **Canonical mappings** (`legacyEstimationFlag` integer to enum, `aggrLevel` integer to hierarchy). Without these mappings, the normalisation layer cannot produce an `EstimationCategory` enum or derive `commodity_is_leaf`.
5. **Data-availability and publication-notes response shapes** (D1, U2, T3, T4, U1). Without verified shapes, the metadata layer and trade layer cannot expose corresponding methods.

---

## 2. Clarification Categories

Clarifications are grouped into the following categories. The category prefix in the `OQ-*` ID encodes the category.

| Category | Prefix | Source Document(s) | Count |
| -------- | ------ | ------------------ | ----: |
| Trade | `OQ-TL-` | `009_TRADE_LAYER_SPEC.md` | 15 |
| Coding Standards | `OQ-CS-` | `015_CODING_STANDARD.md` | 10 |
| ETL | `OQ-ETL-` | `011_ETL_SPECIFICATION.md` | 10 |
| Implementation | `OQ-IM-` | `016_IMPLEMENTATION_ROADMAP.md` | 10 |
| Infrastructure | `OQ-IS-` | `010_INFRASTRUCTURE_SPEC.md`, `014_PACKAGING_SPECIFICATION.md` | 10 |
| Metadata | `OQ-ML-` | `008_METADATA_LAYER_SPEC.md` | 10 |
| Packaging | `OQ-PS-` | `014_PACKAGING_SPECIFICATION.md` | 10 |
| Storage | `OQ-SL-` | `012_STORAGE_SPECIFICATION.md` | 10 |
| Testing | `OQ-TS-` | `013_TESTING_STANDARD.md` | 10 |
| Architecture | `OQ-A-` | `003_ARCHITECTURE.md` | 10 |
| SDK | `OQ-SDK-` | `007_SDK_SPECIFICATION.md`, `008_METADATA_LAYER_SPEC.md`, `014_PACKAGING_SPECIFICATION.md` | 10 |
| API Behaviour | `OQ-API-` | `004_API_RESEARCH.md`, `016_IMPLEMENTATION_ROADMAP.md` | 8 |
| Data Model | `OQ-DM-` | `006_DATA_MODEL.md`, `007_SDK_SPECIFICATION.md` | 8 |

Total counts add to 131 unique `OQ-*` IDs. The 16 cross-referenced `OQ-*` mentions (`TASK_LOG.md`, `008_METADATA_LAYER_SPEC.md`, `011_ETL_SPECIFICATION.md`, `014_PACKAGING_SPECIFICATION.md`, `016_IMPLEMENTATION_ROADMAP.md`) are not double-counted in the category totals.

---

## 3. Clarification Entry Template

Every clarification below follows this template:

```
### CLAR-NNN — <Title>

- **Source OQ ID:** OQ-X-NNN
- **Category:** <Category>
- **Priority:** <High | Medium | Low>
- **Source Documents:** <list of docs where the issue appears>
- **Sections:** <list of section numbers>
- **Description:** <one paragraph summarising the unresolved issue>
- **Current Assumption:** <existing assumption, or "Unknown">
- **Recommended Decision:** <proposed resolution, or blank if not obvious>
- **Implementation Impact:** <Critical | High | Medium | Low>
- **Blocks Implementation:** <Yes | No | Partially>
- **Depends On:** <related CLAR IDs, or "None">
- **Recommended Resolution Order:** <numeric priority within category>
- **Status:** <Open | Resolved | Deferred | Rejected>
- **Owner:** <owner from source doc, if any>
- **Suggested Verification:** <verification step from source doc, if any>
```

---

## 3.5 Clarification Entries

All 131 clarifications are listed below, ordered by category then by original `OQ-*` ID.

### 3.5.1 Category: API Behaviour (8 items)

### CLAR-001 — What is the exact per-minute request cap on the public preview surface?

- **Source OQ ID:** OQ-API-001
- **Category:** API Behaviour
- **Priority:** High
- **Source Documents:** 004_API_RESEARCH.md
- **Sections:** 16.9 CORS observation
- **Description:** What is the exact per-minute request cap on the public preview surface?
- **Impact:** The SDK default retry/backoff configuration depends on this number
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0035 and API_LIMITS_REPORT.md).
- **Suggested Verification:** Issue a sustained sequence of calls and observe the

### CLAR-002 — What is the exact per-key daily record cap?

- **Source OQ ID:** OQ-API-002
- **Category:** API Behaviour
- **Priority:** High
- **Source Documents:** 004_API_RESEARCH.md
- **Sections:** 16.9 CORS observation
- **Description:** What is the exact per-key daily record cap?
- **Impact:** The SDK configuration documentation will document a starting value; consumers that approach the cap need to know
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0036 and API_LIMITS_REPORT.md).
- **Suggested Verification:** Read the developer portal subscription page; verify with a counted experiment.

### CLAR-041 — Is the data availability endpoint (E25) reachable under any URL pattern?

- **Source OQ ID:** OQ-API-003
- **Category:** API Behaviour
- **Priority:** Medium
- **Source Documents:** 004_API_RESEARCH.md, 016_IMPLEMENTATION_ROADMAP.md
- **Sections:** 16.9 CORS observation
- **Description:** Is the data availability endpoint (E25) reachable under any URL pattern?
- **Impact:** The metadata layer may expose a "size the query" helper that depends on this endpoint
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** Partially
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Open (External Verification Required — see EXT-003).
- **Suggested Verification:** Probe the official `comtradeapicall` source for the

### CLAR-042 — What is the documentation of the `legacyEstimationFlag` value semantics? The obs...

- **Source OQ ID:** OQ-API-004
- **Category:** API Behaviour
- **Priority:** Medium
- **Source Documents:** 004_API_RESEARCH.md, 016_IMPLEMENTATION_ROADMAP.md
- **Sections:** 16.9 CORS observation
- **Description:** What is the documentation of the `legacyEstimationFlag` value semantics? The observed values include 0, 4, and 6
- **Impact:** The normalisation layer will tag the record with the flag; the consumer needs the semantics
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Open (External Verification Required — see EXT-010).
- **Suggested Verification:** Read the `Tr

### CLAR-043 — What is the semantics of the `aggrLevel` field? The observed values are integers...

- **Source OQ ID:** OQ-API-005
- **Category:** API Behaviour
- **Priority:** Medium
- **Source Documents:** 004_API_RESEARCH.md
- **Sections:** 16.9 CORS observation
- **Description:** What is the semantics of the `aggrLevel` field? The observed values are integers in the range observed
- **Impact:** The normalisation layer will surface the level so the consumer can filter
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Open (External Verification Required — see EXT-011).

### CLAR-090 — Is the bulk download endpoint (E24) reachable under the documented URL pattern, ...

- **Source OQ ID:** OQ-API-006
- **Category:** API Behaviour
- **Priority:** Low
- **Source Documents:** 004_API_RESEARCH.md
- **Sections:** 16.9 CORS observation
- **Description:** Is the bulk download endpoint (E24) reachable under the documented URL pattern, or has it been renamed?
- **Impact:** The storage layer depends on the URL
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Open (External Verification Required — see EXT-005).
- **Suggested Verification:** Run a probe with a valid key.

### CLAR-091 — Is the `partner2Code` parameter honoured on the public preview, or only on the `...

- **Source OQ ID:** OQ-API-007
- **Category:** API Behaviour
- **Priority:** Low
- **Source Documents:** 004_API_RESEARCH.md
- **Sections:** 16.9 CORS observation
- **Description:** Is the `partner2Code` parameter honoured on the public preview, or only on the `plus` breakdown?
- **Impact:** The trade layer exposes a parameter that may not have an effect on the classic preview
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Open (External Verification Required — see EXT-012).
- **Suggested Verification:** Issue a probe with and without the parameter.

### CLAR-092 — What is the rate of HS revision? The reference catalogue includes 7 editions. Is...

- **Source OQ ID:** OQ-API-008
- **Category:** API Behaviour
- **Priority:** Low
- **Source Documents:** 004_API_RESEARCH.md
- **Sections:** 16.9 CORS observation
- **Description:** What is the rate of HS revision? The reference catalogue includes 7 editions. Is HS 2027 expected within the SDK maintenance window?
- **Impact:** The metadata layer may need to add a new edition
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0026).
- **Suggested Verification:** Read the WCO publications.

### 3.5.12 Category: Architecture (10 items)

### CLAR-031 — Should the layer dependency graph be reflected exactly in the package hierarchy,...

- **Source OQ ID:** OQ-A-001
- **Category:** Architecture
- **Priority:** Medium
- **Source Documents:** 003_ARCHITECTURE.md
- **Sections:** 17.5 Distinguished from verified facts
- **Description:** Should the layer dependency graph be reflected exactly in the package hierarchy, or should the models module be split into per-layer sub-packages? Owner: SDK specification
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0018).
- **Owner:** SDK specification.

### CLAR-032 — Should the storage layer be split into a cache module and a recorded-samples mod...

- **Source OQ ID:** OQ-A-002
- **Category:** Architecture
- **Priority:** Medium
- **Source Documents:** 003_ARCHITECTURE.md
- **Sections:** 17.5 Distinguished from verified facts
- **Description:** Should the storage layer be split into a cache module and a recorded-samples module, with each owning its own interface? Owner: storage specification
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0018).
- **Owner:** storage specification.

### CLAR-033 — Should the retry helpers be a sub-module of the transport layer or a top-level m...

- **Source OQ ID:** OQ-A-003
- **Category:** Architecture
- **Priority:** Medium
- **Source Documents:** 003_ARCHITECTURE.md
- **Sections:** 17.5 Distinguished from verified facts
- **Description:** Should the retry helpers be a sub-module of the transport layer or a top-level module? Owner: SDK specification
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0018).
- **Owner:** SDK specification.

### CLAR-034 — Should the logging seam be a wrapper around the standard library logging module ...

- **Source OQ ID:** OQ-A-004
- **Category:** Architecture
- **Priority:** Medium
- **Source Documents:** 003_ARCHITECTURE.md
- **Sections:** 17.5 Distinguished from verified facts
- **Description:** Should the logging seam be a wrapper around the standard library logging module or a dedicated structured-logging implementation? Owner: coding standard and SDK specification
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0025).
- **Owner:** coding standard and SDK specification.

### CLAR-035 — Should the SDK ship a synchronous client and an asynchronous client as separate ...

- **Source OQ ID:** OQ-A-005
- **Category:** Architecture
- **Priority:** Medium
- **Source Documents:** 003_ARCHITECTURE.md, TASK_LOG.md
- **Sections:** 17.5 Distinguished from verified facts
- **Description:** Should the SDK ship a synchronous client and an asynchronous client as separate top-level classes, or should a single client expose both modes? Owner: SDK specification
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** Resolved
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see TASK_LOG.md).
- **Owner:** SDK specification.

### CLAR-036 — Should the validation layer reject parameters that the upstream API would also r...

- **Source OQ ID:** OQ-A-006
- **Category:** Architecture
- **Priority:** Medium
- **Source Documents:** 003_ARCHITECTURE.md
- **Sections:** 17.5 Distinguished from verified facts
- **Description:** Should the validation layer reject parameters that the upstream API would also reject, or should it forward every parameter to the upstream API and surface the upstream error? Owner: validation specification
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0019).
- **Owner:** validation specification.

### CLAR-037 — Should the normalisation layer apply documented default values, or should it lea...

- **Source OQ ID:** OQ-A-007
- **Category:** Architecture
- **Priority:** Medium
- **Source Documents:** 003_ARCHITECTURE.md
- **Sections:** 17.5 Distinguished from verified facts
- **Description:** Should the normalisation layer apply documented default values, or should it leave absent fields absent and let the consumer decide? Owner: normalisation specification
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** Partially
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0028).
- **Owner:** normalisation specification.

### CLAR-038 — Should the storage layer expose a public cache-invalidation method, or should ca...

- **Source OQ ID:** OQ-A-008
- **Category:** Architecture
- **Priority:** Medium
- **Source Documents:** 003_ARCHITECTURE.md
- **Sections:** 17.5 Distinguished from verified facts
- **Description:** Should the storage layer expose a public cache-invalidation method, or should cache invalidation be internal? Owner: storage specification
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0024).
- **Owner:** storage specification.

### CLAR-039 — Should the architecture pre-declare the public exception type names, or should t...

- **Source OQ ID:** OQ-A-009
- **Category:** Architecture
- **Priority:** Medium
- **Source Documents:** 003_ARCHITECTURE.md
- **Sections:** 17.5 Distinguished from verified facts
- **Description:** Should the architecture pre-declare the public exception type names, or should the exception hierarchy be defined in the SDK specification? Owner: SDK specification
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0021).
- **Owner:** SDK specification.

### CLAR-040 — Should the public interface expose a DataFrame handoff shape, a row-dict handoff...

- **Source OQ ID:** OQ-A-010
- **Category:** Architecture
- **Priority:** Medium
- **Source Documents:** 003_ARCHITECTURE.md
- **Sections:** 17.5 Distinguished from verified facts
- **Description:** Should the public interface expose a DataFrame handoff shape, a row-dict handoff shape, or both? Owner: SDK specification, in coordination with the data-analysis library decision
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0021).
- **Owner:** SDK specification, in coordination with the data-analysis library decision.

### 3.5.2 Category: Coding Standards (10 items)

### CLAR-003 — What is the exact linting framework to be used?

- **Source OQ ID:** OQ-CS-001
- **Category:** Coding Standards
- **Priority:** High
- **Source Documents:** 015_CODING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** What is the exact linting framework to be used?
- **Impact:** The linting rules depend on the framework
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0017).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-004 — What is the exact formatting framework to be used?

- **Source OQ ID:** OQ-CS-002
- **Category:** Coding Standards
- **Priority:** High
- **Source Documents:** 015_CODING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** What is the exact formatting framework to be used?
- **Impact:** The formatting rules depend on the framework
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0017).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-005 — What is the exact type-checking framework to be used?

- **Source OQ ID:** OQ-CS-003
- **Category:** Coding Standards
- **Priority:** High
- **Source Documents:** 015_CODING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** What is the exact type-checking framework to be used?
- **Impact:** The type-checking rules depend on the framework
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0017).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-006 — What is the exact documentation framework to be used?

- **Source OQ ID:** OQ-CS-004
- **Category:** Coding Standards
- **Priority:** High
- **Source Documents:** 015_CODING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** What is the exact documentation framework to be used?
- **Impact:** The documentation build depends on the framework
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0032).
- **Suggested Verification:** Confirm with the packaging specification.

### CLAR-007 — What is the exact testing framework to be used?

- **Source OQ ID:** OQ-CS-005
- **Category:** Coding Standards
- **Priority:** High
- **Source Documents:** 015_CODING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** What is the exact testing framework to be used?
- **Impact:** The test suite depends on the framework
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0030).
- **Suggested Verification:** Confirm with the testing standard.

### CLAR-044 — What is the exact commit message format?

- **Source OQ ID:** OQ-CS-006
- **Category:** Coding Standards
- **Priority:** Medium
- **Source Documents:** 015_CODING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** What is the exact commit message format?
- **Impact:** The commit history depends on the format
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** Partially
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0017).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-045 — What is the exact branch strategy (trunk-based, GitFlow, etc.)?

- **Source OQ ID:** OQ-CS-007
- **Category:** Coding Standards
- **Priority:** Medium
- **Source Documents:** 015_CODING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** What is the exact branch strategy (trunk-based, GitFlow, etc.)?
- **Impact:** The release process depends on the branch strategy
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** Partially
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0033).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-046 — What is the exact pull request template?

- **Source OQ ID:** OQ-CS-008
- **Category:** Coding Standards
- **Priority:** Medium
- **Source Documents:** 015_CODING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** What is the exact pull request template?
- **Impact:** The review process depends on the template
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** Partially
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0031).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-047 — What is the exact issue template?

- **Source OQ ID:** OQ-CS-009
- **Category:** Coding Standards
- **Priority:** Medium
- **Source Documents:** 015_CODING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** What is the exact issue template?
- **Impact:** The issue tracking depends on the template
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** Partially
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0031).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-093 — What is the exact pre-commit hook configuration?

- **Source OQ ID:** OQ-CS-010
- **Category:** Coding Standards
- **Priority:** Low
- **Source Documents:** 015_CODING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** What is the exact pre-commit hook configuration?
- **Impact:** The pre-commit checks depend on the configuration
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0031).
- **Suggested Verification:** Confirm with the maintainers.

### 3.5.3 Category: Data Model (8 items)

### CLAR-008 — What is the canonical mapping of the `legacyEstimationFlag` integer values to th...

- **Source OQ ID:** OQ-DM-001
- **Category:** Data Model
- **Priority:** High
- **Source Documents:** 006_DATA_MODEL.md
- **Sections:** 16.3 Local design decisions
- **Description:** What is the canonical mapping of the `legacyEstimationFlag` integer values to the `EstimationCategory` enumeration? The integer values are documented in the upstream but not captured in this document
- **Impact:** The normalisation layer cannot map the value without a documented mapping
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Open (External Verification Required — see EXT-010).
- **Suggested Verification:** Read the upstream `TradeDataItems.json` reference and document the mapping.

### CLAR-009 — What is the canonical mapping of the `aggrLevel` integer values to a documented ...

- **Source OQ ID:** OQ-DM-002
- **Category:** Data Model
- **Priority:** High
- **Source Documents:** 006_DATA_MODEL.md
- **Sections:** 16.3 Local design decisions
- **Description:** What is the canonical mapping of the `aggrLevel` integer values to a documented hierarchy? The integer values are documented but not captured
- **Impact:** The n
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Open (External Verification Required — see EXT-011).

### CLAR-048 — Is the `partner2Code` parameter honoured on the public preview, or only on the `...

- **Source OQ ID:** OQ-DM-003
- **Category:** Data Model
- **Priority:** Medium
- **Source Documents:** 006_DATA_MODEL.md
- **Sections:** 16.3 Local design decisions
- **Description:** Is the `partner2Code` parameter honoured on the public preview, or only on the `plus` breakdown?
- **Impact:** The trade layer exposes a parameter that may not have an effect on the classic preview
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Open (External Verification Required — see EXT-012).
- **Suggested Verification:** Issue a pr

### CLAR-049 — What is the response shape of E17 PublicationNote and E18 DataAvailabilityRecord...

- **Source OQ ID:** OQ-DM-004
- **Category:** Data Model
- **Priority:** Medium
- **Source Documents:** 006_DATA_MODEL.md
- **Sections:** 16.3 Local design decisions
- **Description:** What is the response shape of E17 PublicationNote and E18 DataAvailabilityRecord?
- **Impact:** The data model cannot finalise the field set without a verified response shape
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** Partially
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0028).
- **Suggested Verification:** Exercise the publication note endpoint and the data availability endpoint w

### CLAR-094 — Should the canonical model expose `partner_code=0` (World) as a constant or as a...

- **Source OQ ID:** OQ-DM-005
- **Category:** Data Model
- **Priority:** Low
- **Source Documents:** 006_DATA_MODEL.md, 007_SDK_SPECIFICATION.md, TASK_LOG.md
- **Sections:** 16.3 Local design decisions
- **Description:** Should the canonical model expose `partner_code=0` (World) as a constant or as a sentinel string?
- **Impact:** The consumer code that handles the World partner is different from the consumer code that handles a regular country
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** Resolved
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see TASK_LOG.md).
- **Suggested Verification:** Do

### CLAR-095 — Should the canonical model include a `DataType` field on E12 TradeRecord to refl...

- **Source OQ ID:** OQ-DM-006
- **Category:** Data Model
- **Priority:** Low
- **Source Documents:** 006_DATA_MODEL.md
- **Sections:** 16.3 Local design decisions
- **Description:** Should the canonical model include a `DataType` field on E12 TradeRecord to reflect whether the record is goods or services? The upstream records the type via `type_code`; the canonical model could also record it via a derived boolean
- **Impact:** T
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0021).

### CLAR-096 — Should the canonical model include a `ValidityWindow` entity to model the validi...

- **Source OQ ID:** OQ-DM-007
- **Category:** Data Model
- **Priority:** Low
- **Source Documents:** 006_DATA_MODEL.md
- **Sections:** 16.3 Local design decisions
- **Description:** Should the canonical model include a `ValidityWindow` entity to model the validity of a country or classification? The upstream records the vali
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0028).

### CLAR-097 — Should the canonical model expose the `provenance` block as a first-class entity...

- **Source OQ ID:** OQ-DM-008
- **Category:** Data Model
- **Priority:** Low
- **Source Documents:** 006_DATA_MODEL.md
- **Sections:** 16.3 Local design decisions
- **Description:** Should the canonical model expose the `provenance` block as a first-class entity? The current model records `provenance` as a derived object on E12
- **Impact:** A fi
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0028).

### 3.5.4 Category: ETL (10 items)

### CLAR-010 — Should the ETL layer expose a streaming output for very large datasets?

- **Source OQ ID:** OQ-ETL-001
- **Category:** ETL
- **Priority:** High
- **Source Documents:** 011_ETL_SPECIFICATION.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the ETL layer expose a streaming output for very large datasets?
- **Impact:** A streaming output would reduce memory consumption
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0027).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-011 — Should the ETL layer support a parallel validation and transformation of records...

- **Source OQ ID:** OQ-ETL-002
- **Category:** ETL
- **Priority:** High
- **Source Documents:** 011_ETL_SPECIFICATION.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the ETL layer support a parallel validation and transformation of records?
- **Impact:** A parallel processing would reduce the per-dataset latency
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0027).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-050 — Should the ETL layer support a custom conflict resolution policy through a docum...

- **Source OQ ID:** OQ-ETL-003
- **Category:** ETL
- **Priority:** Medium
- **Source Documents:** 011_ETL_SPECIFICATION.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the ETL layer support a custom conflict resolution policy through a documented extension point?
- **Impact:** A custom policy would enable consumer-specific deduplication
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0027).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-051 — Should the ETL layer support a custom validation rule through a documented exten...

- **Source OQ ID:** OQ-ETL-004
- **Category:** ETL
- **Priority:** Medium
- **Source Documents:** 011_ETL_SPECIFICATION.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the ETL layer support a custom validation rule through a documented extension point?
- **Impact:** A custom rule would enable consumer-specific quality checks
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0027).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-052 — Should the ETL layer support a custom quality score formula through a documented...

- **Source OQ ID:** OQ-ETL-005
- **Category:** ETL
- **Priority:** Medium
- **Source Documents:** 011_ETL_SPECIFICATION.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the ETL layer support a custom quality score formula through a documented extension point?
- **Impact:** A custom formula would enable consumer-specific quality scoring
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0027).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-053 — Should the ETL layer support a `quarantine=True` flag that, when set, routes fai...

- **Source OQ ID:** OQ-ETL-006
- **Category:** ETL
- **Priority:** Medium
- **Source Documents:** 011_ETL_SPECIFICATION.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the ETL layer support a `quarantine=True` flag that, when set, routes failed records to a quarantine store instead of dropping them?
- **Impact:** A quarantine mechanism would improve the consumer experience
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0027).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-054 — Should the ETL layer support a direct export to a database through a documented ...

- **Source OQ ID:** OQ-ETL-007
- **Category:** ETL
- **Priority:** Medium
- **Source Documents:** 011_ETL_SPECIFICATION.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the ETL layer support a direct export to a database through a documented extension point?
- **Impact:** A direct export would enable pipeline-free loading
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0029).
- **Suggested Verification:** Confirm with the storage requirements.

### CLAR-098 — Should the ETL layer support a watermark strategy that records the last successf...

- **Source OQ ID:** OQ-ETL-008
- **Category:** ETL
- **Priority:** Low
- **Source Documents:** 011_ETL_SPECIFICATION.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the ETL layer support a watermark strategy that records the last successful period per (reporter, partner, flow, commodity) tuple?
- **Impact:** A watermark strategy would enable incremental extraction
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0027).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-099 — Should the ETL layer support a `diff=True` flag that, when set, consumes the ups...

- **Source OQ ID:** OQ-ETL-009
- **Category:** ETL
- **Priority:** Low
- **Source Documents:** 011_ETL_SPECIFICATION.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the ETL layer support a `diff=True` flag that, when set, consumes the upstream diff endpoint (OQ-TL-014) and returns only the changed records?
- **Impact:** A diff mechanism would enable change-data-capture workflows
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0027).
- **Suggested Verification:** Confirm with the storage

### CLAR-100 — Should the ETL layer expose a `get_provenance(record_id)` method that returns th...

- **Source OQ ID:** OQ-ETL-010
- **Category:** ETL
- **Priority:** Low
- **Source Documents:** 011_ETL_SPECIFICATION.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the ETL layer expose a `get_provenance(record_id)` method that returns the full provenance chain of a record?
- **Impact:** A provenance-chain method would improve the consumer experience
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0028).
- **Suggested Verification:** Confirm with the consumer requirements.

### 3.5.5 Category: Implementation (10 items)

### CLAR-012 — When is Phase 0 complete?

- **Source OQ ID:** OQ-IM-001
- **Category:** Implementation
- **Priority:** High
- **Source Documents:** 016_IMPLEMENTATION_ROADMAP.md
- **Sections:** 14.3 Local Design Decisions
- **Description:** When is Phase 0 complete?
- **Impact:** The Phase 0 completion gates Phase 1
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0016).
- **Suggested Verification:** Confirm with the maintainers that every document is approved.

### CLAR-013 — When is Phase 9 complete?

- **Source OQ ID:** OQ-IM-002
- **Category:** Implementation
- **Priority:** High
- **Source Documents:** 016_IMPLEMENTATION_ROADMAP.md
- **Sections:** 14.3 Local Design Decisions
- **Description:** When is Phase 9 complete?
- **Impact:** The Phase 9 completion marks the production release
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0016).
- **Suggested Verification:** Confirm with the maintainers that the release criteria are satisfied.

### CLAR-014 — What is the exact cadence of Phase 10 (Maintenance)?

- **Source OQ ID:** OQ-IM-003
- **Category:** Implementation
- **Priority:** High
- **Source Documents:** 016_IMPLEMENTATION_ROADMAP.md
- **Sections:** 14.3 Local Design Decisions
- **Description:** What is the exact cadence of Phase 10 (Maintenance)?
- **Impact:** The maintenance cadence affects the consumer's upgrade planning
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0014).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-055 — What is the exact success criteria for each milestone?

- **Source OQ ID:** OQ-IM-004
- **Category:** Implementation
- **Priority:** Medium
- **Source Documents:** 016_IMPLEMENTATION_ROADMAP.md
- **Sections:** 14.3 Local Design Decisions
- **Description:** What is the exact success criteria for each milestone?
- **Impact:** The success criteria are the gate of the milestone
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0016).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-056 — What is the exact parallelisable work for each phase?

- **Source OQ ID:** OQ-IM-005
- **Category:** Implementation
- **Priority:** Medium
- **Source Documents:** 016_IMPLEMENTATION_ROADMAP.md
- **Sections:** 14.3 Local Design Decisions
- **Description:** What is the exact parallelisable work for each phase?
- **Impact:** The parallelisable work affects the project velocity
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0016).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-057 — What is the exact impact assessment template for a roadmap change?

- **Source OQ ID:** OQ-IM-006
- **Category:** Implementation
- **Priority:** Medium
- **Source Documents:** 016_IMPLEMENTATION_ROADMAP.md
- **Sections:** 14.3 Local Design Decisions
- **Description:** What is the exact impact assessment template for a roadmap change?
- **Impact:** The impact assessment template affects the change management
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0016).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-058 — What is the exact escalation policy for a phase gate failure?

- **Source OQ ID:** OQ-IM-007
- **Category:** Implementation
- **Priority:** Medium
- **Source Documents:** 016_IMPLEMENTATION_ROADMAP.md
- **Sections:** 14.3 Local Design Decisions
- **Description:** What is the exact escalation policy for a phase gate failure?
- **Impact:** The escalation policy affects the project velocity
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0016).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-101 — What is the exact celebration protocol for each milestone?

- **Source OQ ID:** OQ-IM-008
- **Category:** Implementation
- **Priority:** Low
- **Source Documents:** 016_IMPLEMENTATION_ROADMAP.md
- **Sections:** 14.3 Local Design Decisions
- **Description:** What is the exact celebration protocol for each milestone?
- **Impact:** The celebration protocol affects the contributor morale
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0032).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-102 — What is the exact communication channel for the project?

- **Source OQ ID:** OQ-IM-009
- **Category:** Implementation
- **Priority:** Low
- **Source Documents:** 016_IMPLEMENTATION_ROADMAP.md
- **Sections:** 14.3 Local Design Decisions
- **Description:** What is the exact communication channel for the project?
- **Impact:** The communication channel affects the consumer awareness
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0032).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-103 — What is the exact governance model for the project?

- **Source OQ ID:** OQ-IM-010
- **Category:** Implementation
- **Priority:** Low
- **Source Documents:** 016_IMPLEMENTATION_ROADMAP.md
- **Sections:** 14.3 Local Design Decisions
- **Description:** What is the exact governance model for the project?
- **Impact:** The governance model affects the project decision-making
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0034).
- **Suggested Verification:** Confirm with the maintainers.

### 3.5.6 Category: Infrastructure (10 items)

### CLAR-015 — What is the exact per- minute request cap on the public preview surface?

- **Source OQ ID:** OQ-IS-001
- **Category:** Infrastructure
- **Priority:** High
- **Source Documents:** 010_INFRASTRUCTURE_SPEC.md
- **Sections:** 18.3 Local design decisions
- **Description:** What is the exact per- minute request cap on the public preview surface?
- **Impact:** The default retry budget depends on the cap
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0035 and API_LIMITS_REPORT.md).
- **Suggested Verification:** Run a monitoring experiment and observe the upstream cap.

### CLAR-016 — What is the exact per-key daily record cap?

- **Source OQ ID:** OQ-IS-002
- **Category:** Infrastructure
- **Priority:** High
- **Source Documents:** 010_INFRASTRUCTURE_SPEC.md
- **Sections:** 18.3 Local design decisions
- **Description:** What is the exact per-key daily record cap?
- **Impact:** The default cache lifetime depends on the cap
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0036 and API_LIMITS_REPORT.md).
- **Suggested Verification:** Read the developer portal subscription page.

### CLAR-059 — Should the SDK support a distributed cache backend (Redis, Memcached) for cross-...

- **Source OQ ID:** OQ-IS-003
- **Category:** Infrastructure
- **Priority:** Medium
- **Source Documents:** 010_INFRASTRUCTURE_SPEC.md, 014_PACKAGING_SPECIFICATION.md
- **Sections:** 18.3 Local design decisions
- **Description:** Should the SDK support a distributed cache backend (Redis, Memcached) for cross-process caching?
- **Impact:** A distributed cache backend would enable shared caching across processes
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0024).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-060 — Should the SDK support a custom logger (e.g. structlog, loguru) through a docume...

- **Source OQ ID:** OQ-IS-004
- **Category:** Infrastructure
- **Priority:** Medium
- **Source Documents:** 010_INFRASTRUCTURE_SPEC.md, 014_PACKAGING_SPECIFICATION.md
- **Sections:** 18.3 Local design decisions
- **Description:** Should the SDK support a custom logger (e.g. structlog, loguru) through a documented extension point?
- **Impact:** A custom logger would enable richer log records
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0025).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-061 — Should the SDK support OpenTelemetry tracing through a documented extension poin...

- **Source OQ ID:** OQ-IS-005
- **Category:** Infrastructure
- **Priority:** Medium
- **Source Documents:** 010_INFRASTRUCTURE_SPEC.md
- **Sections:** 18.3 Local design decisions
- **Description:** Should the SDK support OpenTelemetry tracing through a documented extension point?
- **Impact:** OpenTelemetry tracing would enable distributed tracing
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0034).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-062 — Should the SDK support a custom retry policy through a documented extension poin...

- **Source OQ ID:** OQ-IS-006
- **Category:** Infrastructure
- **Priority:** Medium
- **Source Documents:** 010_INFRASTRUCTURE_SPEC.md
- **Sections:** 18.3 Local design decisions
- **Description:** Should the SDK support a custom retry policy through a documented extension point?
- **Impact:** A custom retry policy would enable consumer-specific retry strategies
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0022).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-063 — Should the SDK expose the request identifier as a consumer-supplied header, so t...

- **Source OQ ID:** OQ-IS-007
- **Category:** Infrastructure
- **Priority:** Medium
- **Source Documents:** 010_INFRASTRUCTURE_SPEC.md
- **Sections:** 18.3 Local design decisions
- **Description:** Should the SDK expose the request identifier as a consumer-supplied header, so that the consumer can correlate the SDK calls with the consumer's own tracing?
- **Impact:** A consumer-supplied request identifier would enable end-to-end tracing
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0034).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-104 — Should the SDK support a custom cache key function through a documented extensio...

- **Source OQ ID:** OQ-IS-008
- **Category:** Infrastructure
- **Priority:** Low
- **Source Documents:** 010_INFRASTRUCTURE_SPEC.md
- **Sections:** 18.3 Local design decisions
- **Description:** Should the SDK support a custom cache key function through a documented extension point?
- **Impact:** A custom cache key function would enable consumer-specific cache strategies
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0024).
- **Suggested Verification:** Confirm with the consumer requireme

### CLAR-105 — Should the SDK support a custom progress callback type?

- **Source OQ ID:** OQ-IS-009
- **Category:** Infrastructure
- **Priority:** Low
- **Source Documents:** 010_INFRASTRUCTURE_SPEC.md
- **Sections:** 18.3 Local design decisions
- **Description:** Should the SDK support a custom progress callback type?
- **Impact:** A custom progress callback type would enable richer progress reporting
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0034).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-106 — Should the SDK expose a `__version__` constant?

- **Source OQ ID:** OQ-IS-010
- **Category:** Infrastructure
- **Priority:** Low
- **Source Documents:** 010_INFRASTRUCTURE_SPEC.md
- **Sections:** 18.3 Local design decisions
- **Description:** Should the SDK expose a `__version__` constant?
- **Impact:** A version constant would support runtime version checks
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0034).
- **Suggested Verification:** Confirm with the packaging specification.

### 3.5.7 Category: Metadata (10 items)

### CLAR-017 — What is the exact cache lifetime for each resource?

- **Source OQ ID:** OQ-ML-001
- **Category:** Metadata
- **Priority:** High
- **Source Documents:** 008_METADATA_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** What is the exact cache lifetime for each resource?
- **Impact:** The cache lifetime affects the freshness of the metadata and the frequency of upstream calls
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0026).
- **Suggested Verification:** Run a monitoring experiment and observe the upstream publication cadence.

### CLAR-018 — What is the exact URL of the data availability endpoint (D1)?

- **Source OQ ID:** OQ-ML-002
- **Category:** Metadata
- **Priority:** High
- **Source Documents:** 008_METADATA_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** What is the exact URL of the data availability endpoint (D1)?
- **Impact:** The metadata layer cannot expose the `get_data_availability` method without a URL
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Open (External Verification Required — see EXT-003).
- **Suggested Verification:** Probe the official `comtradeapicall` source for the canonical URL.

### CLAR-064 — What is the response shape of the publication notes endpoint (U2)?

- **Source OQ ID:** OQ-ML-003
- **Category:** Metadata
- **Priority:** Medium
- **Source Documents:** 008_METADATA_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** What is the response shape of the publication notes endpoint (U2)?
- **Impact:** The metadata layer cannot expose the `get_publication_notes` method without a response shape
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** Partially
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Open (External Verification Required — see EXT-006).
- **Suggested Verification:** Exercise the publication notes endpoint with a valid key.

### CLAR-065 — Should the metadata layer expose a `DataItem` entity, or should the data items b...

- **Source OQ ID:** OQ-ML-004
- **Category:** Metadata
- **Priority:** Medium
- **Source Documents:** 008_METADATA_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the metadata layer expose a `DataItem` entity, or should the data items be exposed as a `MetadataCollection` of structured records?
- **Impact:** The data model does not currently define a `DataItem` entity
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0026).
- **Suggested Verification:** Confirm with the consumer ergonomics.

### CLAR-066 — Should the metadata layer pre-load the entire catalogue at startup, or load each...

- **Source OQ ID:** OQ-ML-005
- **Category:** Metadata
- **Priority:** Medium
- **Source Documents:** 008_METADATA_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the metadata layer pre-load the entire catalogue at startup, or load each resource on first use?
- **Impact:** A pre-load is faster on first call but slower at startup
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0026).
- **Suggested Verification:** Confirm

### CLAR-067 — Should the metadata layer support a manual invalidation of the entire cache, or ...

- **Source OQ ID:** OQ-ML-006
- **Category:** Metadata
- **Priority:** Medium
- **Source Documents:** 008_METADATA_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the metadata layer support a manual invalidation of the entire cache, or only per resource?
- **Impact:** A manual invalidation of the entire cache is simpler to expose
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0024).
- **Suggested Verification:** Confirm with the consumer ergonomics.

### CLAR-107 — Should the metadata layer expose a `get_recent_releases()` method that returns t...

- **Source OQ ID:** OQ-ML-007
- **Category:** Metadata
- **Priority:** Low
- **Source Documents:** 008_METADATA_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the metadata layer expose a `get_recent_releases()` method that returns the recent changes to the catalogue?
- **Impact:** A recent-releases method would support change-data-capture workflows
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0026).
- **Suggested Verification:** Confirm with the storage requirements.

### CLAR-108 — Should the metadata layer support a custom cache backend (Redis, SQLite) through...

- **Source OQ ID:** OQ-ML-008
- **Category:** Metadata
- **Priority:** Low
- **Source Documents:** 008_METADATA_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the metadata layer support a custom cache backend (Redis, SQLite) through a documented extension point?
- **Impact:** A custom cache backend would enable shared caching across processes
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0024).
- **Suggested Verification:** Confirm with the storage requirements.

### CLAR-109 — Should the metadata layer expose a `validate_metadata()` method that validates t...

- **Source OQ ID:** OQ-ML-009
- **Category:** Metadata
- **Priority:** Low
- **Source Documents:** 008_METADATA_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the metadata layer expose a `validate_metadata()` method that validates the cache against the upstream?
- **Impact:** A validation method would support diagnostic workflows
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0026).
- **Suggested Verification:** Confirm with the consumer ergonomics.

### CLAR-110 — Should the metadata layer expose a `get_classification_tree(classification, edit...

- **Source OQ ID:** OQ-ML-010
- **Category:** Metadata
- **Priority:** Low
- **Source Documents:** 008_METADATA_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the metadata layer expose a `get_classification_tree(classification, edition)` method that returns the hierarchical tree of the classification?
- **Impact:** A tree method would support navigation workflows
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0026).
- **Suggested Verification:** Confirm with the consumer ergonomics.

### 3.5.8 Category: Packaging (10 items)

### CLAR-019 — What is the exact continuous integration pipeline to be used?

- **Source OQ ID:** OQ-PS-001
- **Category:** Packaging
- **Priority:** High
- **Source Documents:** 014_PACKAGING_SPECIFICATION.md
- **Sections:** 15.3 Local Design Decisions
- **Description:** What is the exact continuous integration pipeline to be used?
- **Impact:** The build process and the test process depend on the pipeline
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0033).
- **Suggested Verification:** Confirm with the testing standard.

### CLAR-020 — What is the exact package index to be used?

- **Source OQ ID:** OQ-PS-002
- **Category:** Packaging
- **Priority:** High
- **Source Documents:** 014_PACKAGING_SPECIFICATION.md
- **Sections:** 15.3 Local Design Decisions
- **Description:** What is the exact package index to be used?
- **Impact:** The publication process depends on the package index
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0033).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-021 — What is the exact documentation site to be used?

- **Source OQ ID:** OQ-PS-003
- **Category:** Packaging
- **Priority:** High
- **Source Documents:** 014_PACKAGING_SPECIFICATION.md
- **Sections:** 15.3 Local Design Decisions
- **Description:** What is the exact documentation site to be used?
- **Impact:** The documentation publication process depends on the documentation site
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0033).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-068 — What is the exact signing key to be used for the package?

- **Source OQ ID:** OQ-PS-004
- **Category:** Packaging
- **Priority:** Medium
- **Source Documents:** 014_PACKAGING_SPECIFICATION.md
- **Sections:** 15.3 Local Design Decisions
- **Description:** What is the exact signing key to be used for the package?
- **Impact:** The signature is part of the package's provenance
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0033).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-069 — What is the exact release schedule (on-demand vs. scheduled)?

- **Source OQ ID:** OQ-PS-005
- **Category:** Packaging
- **Priority:** Medium
- **Source Documents:** 014_PACKAGING_SPECIFICATION.md
- **Sections:** 15.3 Local Design Decisions
- **Description:** What is the exact release schedule (on-demand vs. scheduled)?
- **Impact:** The release cadence affects the consumer's upgrade planning
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** Partially
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0033).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-070 — What is the exact Python version support policy?

- **Source OQ ID:** OQ-PS-006
- **Category:** Packaging
- **Priority:** Medium
- **Source Documents:** 014_PACKAGING_SPECIFICATION.md
- **Sections:** 15.3 Local Design Decisions
- **Description:** What is the exact Python version support policy?
- **Impact:** The Python version support affects the consumer's compatibility planning
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0017).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-071 — What is the exact operating system support policy?

- **Source OQ ID:** OQ-PS-007
- **Category:** Packaging
- **Priority:** Medium
- **Source Documents:** 014_PACKAGING_SPECIFICATION.md
- **Sections:** 15.3 Local Design Decisions
- **Description:** What is the exact operating system support policy?
- **Impact:** The operating system support affects the consumer's compatibility planning
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0017).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-072 — What is the exact changelog format?

- **Source OQ ID:** OQ-PS-008
- **Category:** Packaging
- **Priority:** Medium
- **Source Documents:** 014_PACKAGING_SPECIFICATION.md
- **Sections:** 15.3 Local Design Decisions
- **Description:** What is the exact changelog format?
- **Impact:** The changelog format affects the tooling
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0032).
- **Suggested Verification:** Confirm with the maintainers.

### CLAR-111 — Should the package support a `pip install un-comtrade-sdk[all]` mechanism that i...

- **Source OQ ID:** OQ-PS-009
- **Category:** Packaging
- **Priority:** Low
- **Source Documents:** 014_PACKAGING_SPECIFICATION.md
- **Sections:** 15.3 Local Design Decisions
- **Description:** Should the package support a `pip install un-comtrade-sdk[all]` mechanism that installs every optional dependency?
- **Impact:** The mechanism enables a "kitchen sink" installation
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0031).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-112 — Should the package support a Docker image as a distribution target?

- **Source OQ ID:** OQ-PS-010
- **Category:** Packaging
- **Priority:** Low
- **Source Documents:** 014_PACKAGING_SPECIFICATION.md
- **Sections:** 15.3 Local Design Decisions
- **Description:** Should the package support a Docker image as a distribution target?
- **Impact:** A Docker image would enable reproducible deployments
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0031).
- **Suggested Verification:** Confirm with the consumer requirements.

### 3.5.13 Category: SDK (10 items)

### CLAR-073 — Should the SDK expose a `get_availability(reporter_code, period)` method that re...

- **Source OQ ID:** OQ-SDK-001
- **Category:** SDK
- **Priority:** Medium
- **Source Documents:** 007_SDK_SPECIFICATION.md
- **Sections:** 14.3 Local design decisions
- **Description:** Should the SDK expose a `get_availability(reporter_code, period)` method that returns the count of records, instead of the current `U01` method?
- **Impact:** The current `U01` returns a collection; a count-only method would be simpler
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0021).
- **Suggested Verification:** Confirm with the consumer ergonomics.

### CLAR-074 — Should the async methods be on a separate client class, or on the same client?

- **Source OQ ID:** OQ-SDK-002
- **Category:** SDK
- **Priority:** Medium
- **Source Documents:** 007_SDK_SPECIFICATION.md
- **Sections:** 14.3 Local design decisions
- **Description:** Should the async methods be on a separate client class, or on the same client?
- **Impact:** The current design puts them on the same client
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0019).
- **Suggested Verification:** Confirm with the implemen

### CLAR-113 — Should the SDK expose a `get_trade_envelope(reporter_code, flow_code, period)` m...

- **Source OQ ID:** OQ-SDK-003
- **Category:** SDK
- **Priority:** Low
- **Source Documents:** 007_SDK_SPECIFICATION.md
- **Sections:** 14.3 Local design decisions
- **Description:** Should the SDK expose a `get_trade_envelope(reporter_code, flow_code, period)` method that combines the `get_trade`, `get_trade_balance`, and `get_bilateral` methods into a single call?
- **Impact:** A single call would reduce the number of network round-trips
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0027).

### CLAR-114 — Should the SDK expose a `get_metadata_diff(table_name, since)` method that retur...

- **Source OQ ID:** OQ-SDK-004
- **Category:** SDK
- **Priority:** Low
- **Source Documents:** 007_SDK_SPECIFICATION.md
- **Sections:** 14.3 Local design decisions
- **Description:** Should the SDK expose a `get_metadata_diff(table_name, since)` method that returns the changes to a catalogue since a given timestamp?
- **Impact:** A diff method would support change-data-capture workflows
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0026).

### CLAR-115 — Should the SDK expose a `validate_query(...)` method that validates a query with...

- **Source OQ ID:** OQ-SDK-005
- **Category:** SDK
- **Priority:** Low
- **Source Documents:** 007_SDK_SPECIFICATION.md, 008_METADATA_LAYER_SPEC.md
- **Sections:** 14.3 Local design decisions
- **Description:** Should the SDK expose a `validate_query(...)` method that validates a query without issuing it?
- **Impact:** A validation method would support pre-flight checks
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0026).
- **Suggested Verification:** Confirm with the consumer ergonomics.

### CLAR-116 — Should the SDK expose a `get_recent_releases()` method that returns the recent d...

- **Source OQ ID:** OQ-SDK-006
- **Category:** SDK
- **Priority:** Low
- **Source Documents:** 007_SDK_SPECIFICATION.md, 014_PACKAGING_SPECIFICATION.md
- **Sections:** 14.3 Local design decisions
- **Description:** Should the SDK expose a `get_recent_releases()` method that returns the recent data releases from the live update endpoint?
- **Impact:** A recent-releases method would support dashboard workflows
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0026).
- **Suggested Verification:** Confirm with the analytics use case.

### CLAR-117 — Should the SDK expose constants for the special `flow_code` values (`un_comtrade...

- **Source OQ ID:** OQ-SDK-007
- **Category:** SDK
- **Priority:** Low
- **Source Documents:** 007_SDK_SPECIFICATION.md
- **Sections:** 14.3 Local design decisions
- **Description:** Should the SDK expose constants for the special `flow_code` values (`un_comtrade.FLOW_EXPORT = 'X'`, `un_comtrade.FLOW_IMPORT = 'M'`)?
- **Impact:** Constants would reduce the risk of typos
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0021).
- **Suggested Verification:** Confirm with the implementation ergonomics.

### CLAR-118 — Should the SDK expose constants for the classification codes (`un_comtrade.CLASS...

- **Source OQ ID:** OQ-SDK-008
- **Category:** SDK
- **Priority:** Low
- **Source Documents:** 007_SDK_SPECIFICATION.md
- **Sections:** 14.3 Local design decisions
- **Description:** Should the SDK expose constants for the classification codes (`un_comtrade.CLASSIFICATION_HS = 'HS'`, `un_comtrade.CLASSIFICATION_HS_2022 = 'H6'`)?
- **Impact:** Constants would reduce the risk of typos
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0021).
- **Suggested Verification:** Confirm with the implementation ergonomics.

### CLAR-119 — Should the SDK expose an `__all__` list that documents the public surface?

- **Source OQ ID:** OQ-SDK-009
- **Category:** SDK
- **Priority:** Low
- **Source Documents:** 007_SDK_SPECIFICATION.md
- **Sections:** 14.3 Local design decisions
- **Description:** Should the SDK expose an `__all__` list that documents the public surface?
- **Impact:** An `__all__` list would enable linters to detect unintended exports
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0021).
- **Suggested Verification:** Confirm with the packaging specification.

### CLAR-120 — Should the SDK expose a `__version__` constant?

- **Source OQ ID:** OQ-SDK-010
- **Category:** SDK
- **Priority:** Low
- **Source Documents:** 007_SDK_SPECIFICATION.md
- **Sections:** 14.3 Local design decisions
- **Description:** Should the SDK expose a `__version__` constant?
- **Impact:** A version constant would support runtime version checks
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0034).
- **Suggested Verification:** Confirm with the packaging specification.

### 3.5.9 Category: Storage (10 items)

### CLAR-022 — What is the exact retention period for each data category?

- **Source OQ ID:** OQ-SL-001
- **Category:** Storage
- **Priority:** High
- **Source Documents:** 012_STORAGE_SPECIFICATION.md
- **Sections:** 16.3 Local Design Decisions
- **Description:** What is the exact retention period for each data category?
- **Impact:** The retention period affects the storage cost and the consumer's data availability
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0029).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-023 — What is the exact partition strategy for trade data?

- **Source OQ ID:** OQ-SL-002
- **Category:** Storage
- **Priority:** High
- **Source Documents:** 012_STORAGE_SPECIFICATION.md
- **Sections:** 16.3 Local Design Decisions
- **Description:** What is the exact partition strategy for trade data?
- **Impact:** The partition strategy affects the query performance
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0029).
- **Suggested Verification:** Run a performance experiment with different partition keys.

### CLAR-075 — Should the storage layer support a custom serialiser through a documented extens...

- **Source OQ ID:** OQ-SL-003
- **Category:** Storage
- **Priority:** Medium
- **Source Documents:** 012_STORAGE_SPECIFICATION.md
- **Sections:** 16.3 Local Design Decisions
- **Description:** Should the storage layer support a custom serialiser through a documented extension point?
- **Impact:** A custom serialiser would enable consumer-specific output formats
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0029).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-076 — Should the storage layer support a custom target through a documented extension ...

- **Source OQ ID:** OQ-SL-004
- **Category:** Storage
- **Priority:** Medium
- **Source Documents:** 012_STORAGE_SPECIFICATION.md
- **Sections:** 16.3 Local Design Decisions
- **Description:** Should the storage layer support a custom target through a documented extension point?
- **Impact:** A custom target would enable consumer-specific backends
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0029).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-077 — Should the storage layer support a versioning strategy that retains every interm...

- **Source OQ ID:** OQ-SL-005
- **Category:** Storage
- **Priority:** Medium
- **Source Documents:** 012_STORAGE_SPECIFICATION.md
- **Sections:** 16.3 Local Design Decisions
- **Description:** Should the storage layer support a versioning strategy that retains every intermediate version, or only the latest version per period?
- **Impact:** The versioning strategy affects the storage cost and the rollback capability
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0029).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-078 — Should the storage layer support a remote storage target (e.g. S3) in the MVP, o...

- **Source OQ ID:** OQ-SL-006
- **Category:** Storage
- **Priority:** Medium
- **Source Documents:** 012_STORAGE_SPECIFICATION.md
- **Sections:** 16.3 Local Design Decisions
- **Description:** Should the storage layer support a remote storage target (e.g. S3) in the MVP, or defer it to a future version?
- **Impact:** A remote target would enable cloud-native deployments
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0029).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-079 — Should the storage layer support a column-store target (e.g. DuckDB) in the MVP,...

- **Source OQ ID:** OQ-SL-007
- **Category:** Storage
- **Priority:** Medium
- **Source Documents:** 012_STORAGE_SPECIFICATION.md
- **Sections:** 16.3 Local Design Decisions
- **Description:** Should the storage layer support a column-store target (e.g. DuckDB) in the MVP, or defer it to a future version?
- **Impact:** A column-store target would enable embedded analytics
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0029).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-121 — Should the storage layer support a custom metadata field on every persisted reco...

- **Source OQ ID:** OQ-SL-008
- **Category:** Storage
- **Priority:** Low
- **Source Documents:** 012_STORAGE_SPECIFICATION.md
- **Sections:** 16.3 Local Design Decisions
- **Description:** Should the storage layer support a custom metadata field on every persisted record, so that the consumer can attach application-specific tags?
- **Impact:** A custom metadata field would enable richer provenance
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0029).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-122 — Should the storage layer support a `compact()` operation that merges multiple ve...

- **Source OQ ID:** OQ-SL-009
- **Category:** Storage
- **Priority:** Low
- **Source Documents:** 012_STORAGE_SPECIFICATION.md
- **Sections:** 16.3 Local Design Decisions
- **Description:** Should the storage layer support a `compact()` operation that merges multiple versions of a dataset into a single version?
- **Impact:** A compact operation would reduce the storage cost over time
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0029).
- **Suggested Verification:** Confirm with the consumer requirements.

### CLAR-123 — Should the storage layer support a `vacuum()` operation that deletes archived da...

- **Source OQ ID:** OQ-SL-010
- **Category:** Storage
- **Priority:** Low
- **Source Documents:** 012_STORAGE_SPECIFICATION.md
- **Sections:** 16.3 Local Design Decisions
- **Description:** Should the storage layer support a `vacuum()` operation that deletes archived datasets after the retention period?
- **Impact:** A vacuum operation would automatically clean up the storage
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0029).
- **Suggested Verification:** Confirm with the consumer requirements.

### 3.5.11 Category: Testing (10 items)

### CLAR-029 — What is the exact continuous integration pipeline to be used?

- **Source OQ ID:** OQ-TS-001
- **Category:** Testing
- **Priority:** High
- **Source Documents:** 013_TESTING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** What is the exact continuous integration pipeline to be used?
- **Impact:** The test frequency and the test environment depend on the pipeline
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0033).
- **Suggested Verification:** Confirm with the packaging specification.

### CLAR-030 — What is the exact package index to be used?

- **Source OQ ID:** OQ-TS-002
- **Category:** Testing
- **Priority:** High
- **Source Documents:** 013_TESTING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** What is the exact package index to be used?
- **Impact:** The release process depends on the package index
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0033).
- **Suggested Verification:** Confirm with the packaging specification.

### CLAR-085 — What is the exact documentation site to be used?

- **Source OQ ID:** OQ-TS-003
- **Category:** Testing
- **Priority:** Medium
- **Source Documents:** 013_TESTING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** What is the exact documentation site to be used?
- **Impact:** The release process depends on the documentation site
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** Partially
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0033).
- **Suggested Verification:** Confirm with the packaging specification.

### CLAR-086 — Should the test suite support property-based testing for the normalisation layer...

- **Source OQ ID:** OQ-TS-004
- **Category:** Testing
- **Priority:** Medium
- **Source Documents:** 013_TESTING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** Should the test suite support property-based testing for the normalisation layer?
- **Impact:** Property-based testing would catch more edge cases
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0030).
- **Suggested Verification:** Confirm with the implementation ergonomics.

### CLAR-087 — Should the test suite support mutation testing for the validation layer?

- **Source OQ ID:** OQ-TS-005
- **Category:** Testing
- **Priority:** Medium
- **Source Documents:** 013_TESTING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** Should the test suite support mutation testing for the validation layer?
- **Impact:** Mutation testing would catch more validation defects
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0030).
- **Suggested Verification:** Confirm with the implementation ergonomics.

### CLAR-088 — Should the test suite support a chaos test that simulates upstream failures at r...

- **Source OQ ID:** OQ-TS-006
- **Category:** Testing
- **Priority:** Medium
- **Source Documents:** 013_TESTING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** Should the test suite support a chaos test that simulates upstream failures at random intervals?
- **Impact:** A chaos test would catch more resilience defects
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0030).
- **Suggested Verification:** Confirm with the implementation ergonomics.

### CLAR-089 — Should the test suite support a load test that issues a sustained number of requ...

- **Source OQ ID:** OQ-TS-007
- **Category:** Testing
- **Priority:** Medium
- **Source Documents:** 013_TESTING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** Should the test suite support a load test that issues a sustained number of requests?
- **Impact:** A load test would catch more rate-limit defects
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** Partially
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0030).
- **Suggested Verification:** Confirm with the implementation ergonomics.

### CLAR-129 — Should the test suite support a snapshot test that compares the normalised recor...

- **Source OQ ID:** OQ-TS-008
- **Category:** Testing
- **Priority:** Low
- **Source Documents:** 013_TESTING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** Should the test suite support a snapshot test that compares the normalised record against a recorded snapshot?
- **Impact:** A snapshot test would catch more normalisation defects
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0030).
- **Suggested Verification:** Confirm with the implementation ergonomics.

### CLAR-130 — Should the test suite support a fuzz test that issues requests with random param...

- **Source OQ ID:** OQ-TS-009
- **Category:** Testing
- **Priority:** Low
- **Source Documents:** 013_TESTING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** Should the test suite support a fuzz test that issues requests with random parameters?
- **Impact:** A fuzz test would catch more validation defects
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0030).
- **Suggested Verification:** Confirm with the implementation ergonomics.

### CLAR-131 — Should the test suite support a conformance test that verifies the SDK against t...

- **Source OQ ID:** OQ-TS-010
- **Category:** Testing
- **Priority:** Low
- **Source Documents:** 013_TESTING_STANDARD.md
- **Sections:** 17.3 Local Design Decisions
- **Description:** Should the test suite support a conformance test that verifies the SDK against the official test fixtures?
- **Impact:** A conformance test would catch more upstream-contract defects
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0030).
- **Suggested Verification:** Confirm with the upstream conformance requirements.

### CLAR-132 — Should V-001 audit findings (hand-rolled aggregations) be enforced via an AST-based regression test?

- **Source OQ ID:** OQ-TS-011
- **Category:** Testing
- **Priority:** High
- **Source Documents:** 013_TESTING_STANDARD.md, 026_QUERY_ENGINE_REVIEW.md
- **Sections:** 17.3 Local Design Decisions; ADR-0030
- **Description:** V-001 (TASK-087) flagged 8 hand-rolled
  per-group Decimal aggregation patterns across
  `balance.py` and `commodity.py`. After F-002
  refactors them through the Query Engine, should
  a regression test prevent any future
  reintroduction of the forbidden pattern?
- **Impact:** Without a guard, future contributors
  could silently regress the F-002 fix and
  duplicate Query Engine logic. With a guard, the
  pattern becomes a code-review style enforced at
  test time.
- **Current Assumption:** Yes — added
  `tests/test_f002_no_handrolled_aggregation.py`
  as an AST walker that fails on any
  `by_X[k] = (by_X.get(k, Decimal("0")) + v)`.
- **Recommended Decision:** Adopted. Pattern is
  enforced via Python's `ast` module at test time.
- **Implementation Impact:** Low — single test
  file; AST scan is fast (<300ms).
- **Blocks Implementation:** No
- **Depends On:** F-002 (CHG-0078).
- **Recommended Resolution Order:** Resolved.
- **Status:** Resolved (see CHG-0078).
- **Suggested Verification:** Run `pytest
  tests/test_f002_no_handrolled_aggregation.py -v`.

### 3.5.10 Category: Trade (15 items)

### CLAR-024 — What is the exact publication cadence of the trade data?

- **Source OQ ID:** OQ-TL-001
- **Category:** Trade
- **Priority:** High
- **Source Documents:** 009_TRADE_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** What is the exact publication cadence of the trade data?
- **Impact:** The cache lifetime and the refresh strategy depend on the cadence
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0027).
- **Suggested Verification:** Run a monitoring experiment and observe the upstream publication cadence.

### CLAR-025 — What is the exact URL of the data availability endpoint (D1)?

- **Source OQ ID:** OQ-TL-002
- **Category:** Trade
- **Priority:** High
- **Source Documents:** 009_TRADE_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** What is the exact URL of the data availability endpoint (D1)?
- **Impact:** The trade layer cannot expose the `get_data_availability` method without a URL
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Open (External Verification Required — see EXT-003).
- **Suggested Verification:** Probe the official `comtradeapicall` source for the canonical URL.

### CLAR-026 — What is the exact URL of the bulk download endpoint (D3)?

- **Source OQ ID:** OQ-TL-003
- **Category:** Trade
- **Priority:** High
- **Source Documents:** 009_TRADE_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** What is the exact URL of the bulk download endpoint (D3)?
- **Impact:** The trade layer cannot expose the bulk download methods without a URL
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Open (External Verification Required — see EXT-005).
- **Suggested Verification:** Probe the official `comtradeapicall` source.

### CLAR-027 — What is the exact URL of the async submit, check, and download endpoints (D2)?

- **Source OQ ID:** OQ-TL-004
- **Category:** Trade
- **Priority:** High
- **Source Documents:** 009_TRADE_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** What is the exact URL of the async submit, check, and download endpoints (D2)?
- **Impact:** The trade layer cannot expose the async methods without URLs
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Open (External Verification Required — see EXT-004).
- **Suggested Verification:** Probe the official `comtradeapicall` source.

### CLAR-028 — What is the response shape of the publication notes endpoint (U2)?

- **Source OQ ID:** OQ-TL-005
- **Category:** Trade
- **Priority:** High
- **Source Documents:** 009_TRADE_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** What is the response shape of the publication notes endpoint (U2)?
- **Impact:** The trade layer cannot expose the `get_publication_notes` method without a response shape
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Critical.
- **Blocks Implementation:** Yes
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Open (External Verification Required — see EXT-006).
- **Suggested Verification:** Exercise the publication notes endpoint with a valid key.

### CLAR-080 — What is the response shape of the SUV endpoint (U1)?

- **Source OQ ID:** OQ-TL-006
- **Category:** Trade
- **Priority:** Medium
- **Source Documents:** 009_TRADE_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** What is the response shape of the SUV endpoint (U1)?
- **Impact:** The trade layer cannot expose the `get_standard_unit_value` method without a response shape
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** Partially
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Open (External Verification Required — see EXT-009).
- **Suggested Verification:** Exercise the SUV endpoint with a valid key.

### CLAR-081 — What is the response shape of the trade balance endpoint (T3)?

- **Source OQ ID:** OQ-TL-007
- **Category:** Trade
- **Priority:** Medium
- **Source Documents:** 009_TRADE_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** What is the response shape of the trade balance endpoint (T3)?
- **Impact:** The trade layer cannot normalise the response without a shape
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** Partially
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Open (External Verification Required — see EXT-007).
- **Suggested Verification:** Exercise the trade balance endpoint with a valid key.

### CLAR-082 — What is the response shape of the bilateral endpoint (T4)?

- **Source OQ ID:** OQ-TL-008
- **Category:** Trade
- **Priority:** Medium
- **Source Documents:** 009_TRADE_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** What is the response shape of the bilateral endpoint (T4)?
- **Impact:** The trade layer cannot normalise the response without a shape
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** Partially
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Open (External Verification Required — see EXT-008).
- **Suggested Verification:** Exercise the bilateral endpoint with a valid key.

### CLAR-083 — Should the trade layer support a streaming output for very large responses?

- **Source OQ ID:** OQ-TL-009
- **Category:** Trade
- **Priority:** Medium
- **Source Documents:** 009_TRADE_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the trade layer support a streaming output for very large responses?
- **Impact:** A streaming output would reduce memory consumption
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0027).
- **Suggested Verification:** Confirm with the consumer ergonomics.

### CLAR-084 — Should the trade layer support a concurrent batch execution under a documented c...

- **Source OQ ID:** OQ-TL-010
- **Category:** Trade
- **Priority:** Medium
- **Source Documents:** 009_TRADE_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the trade layer support a concurrent batch execution under a documented concurrency cap?
- **Impact:** Concurrent execution would reduce the total download time but would require coordination with the rate limit
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Medium.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0027).
- **Suggested Verification:** Confirm with the upstream rate-limit policy.

### CLAR-124 — Should the trade layer expose a `cancel()` method to cancel an in-flight downloa...

- **Source OQ ID:** OQ-TL-011
- **Category:** Trade
- **Priority:** Low
- **Source Documents:** 009_TRADE_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the trade layer expose a `cancel()` method to cancel an in-flight download?
- **Impact:** A cancel method would improve the consumer experience
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0027).
- **Suggested Verification:** Confirm with the consumer ergonomics.

### CLAR-125 — Should the trade layer expose a `resume(download_handle)` method to resume an in...

- **Source OQ ID:** OQ-TL-012
- **Category:** Trade
- **Priority:** Low
- **Source Documents:** 009_TRADE_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the trade layer expose a `resume(download_handle)` method to resume an interrupted download?
- **Impact:** A resume method would improve the consumer experience
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0027).
- **Suggested Verification:** Confirm with the consumer ergonomics.

### CLAR-126 — Should the trade layer expose a `validate_query(...)` method to validate a query...

- **Source OQ ID:** OQ-TL-013
- **Category:** Trade
- **Priority:** Low
- **Source Documents:** 009_TRADE_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the trade layer expose a `validate_query(...)` method to validate a query without issuing it?
- **Impact:** A validation method would support pre-flight checks
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0027).
- **Suggested Verification:** Confirm with the consumer ergonomics.

### CLAR-127 — Should the trade layer expose a `get_trade_diff(reporter_code, since)` method to...

- **Source OQ ID:** OQ-TL-014
- **Category:** Trade
- **Priority:** Low
- **Source Documents:** 009_TRADE_LAYER_SPEC.md, 011_ETL_SPECIFICATION.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the trade layer expose a `get_trade_diff(reporter_code, since)` method to retrieve only the records that have changed since a given timestamp?
- **Impact:** A diff method would support change-data-capture workflows
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0027).
- **Suggested Verification:** Confirm with the storage requirements.

### CLAR-128 — Should the trade layer support a `cached=True` flag on every method to explicitl...

- **Source OQ ID:** OQ-TL-015
- **Category:** Trade
- **Priority:** Low
- **Source Documents:** 009_TRADE_LAYER_SPEC.md
- **Sections:** 17.3 Local design decisions
- **Description:** Should the trade layer support a `cached=True` flag on every method to explicitly opt out of the cache?
- **Impact:** The flag would give the consumer explicit control over the cache
- **Current Assumption:** Unknown.
- **Recommended Decision:** [To be determined during resolution.]
- **Implementation Impact:** Low.
- **Blocks Implementation:** No
- **Depends On:** None.
- **Recommended Resolution Order:** TBD.
- **Status:** Resolved (see ADR-0024).
- **Suggested Verification:** Confirm with the consumer ergonomics.

---

## 4. Duplicate Analysis

Multiple `OQ-*` IDs were found to encode the same underlying question. The following table lists every duplicate pair detected. The recommendation is to **merge** duplicates into the first-occurring ID and add cross-references in subsequent IDs.

### 4.1 Duplicate Map

| # | Duplicate OQ IDs | Question (truncated) | Source Documents | Recommendation |
| - | ---------------- | -------------------- | ---------------- | -------------- |
| 1 | OQ-API-002, OQ-IS-002 | What is the exact per-key daily record cap? | 004_API_RESEARCH.md, 010_INFRASTRUCTURE_SPEC.md | Keep `OQ-API-002` as the canonical ID. Cross-reference from `OQ-IS-002`. |
| 2 | OQ-DM-003, OQ-API-007 | Is the `partner2Code` parameter honoured on the public preview, or only on the ` | 004_API_RESEARCH.md, 006_DATA_MODEL.md | Keep `OQ-API-007` as the canonical ID. Cross-reference from `OQ-DM-003`. |
| 3 | OQ-IS-010, OQ-SDK-010 | Should the SDK expose a `__version__` constant? | 007_SDK_SPECIFICATION.md, 010_INFRASTRUCTURE_SPEC.md | Keep `OQ-IS-010` as the canonical ID. Cross-reference from `OQ-SDK-010`. |
| 4 | OQ-ML-002, OQ-TL-002 | What is the exact URL of the data availability endpoint (D1)? | 008_METADATA_LAYER_SPEC.md, 009_TRADE_LAYER_SPEC.md | Keep `OQ-ML-002` as the canonical ID. Cross-reference from `OQ-TL-002`. |
| 5 | OQ-PS-001, OQ-TS-001 | What is the exact continuous integration pipeline to be used? | 013_TESTING_STANDARD.md, 014_PACKAGING_SPECIFICATION.md | Keep `OQ-PS-001` as the canonical ID. Cross-reference from `OQ-TS-001`. |
| 6 | OQ-PS-002, OQ-TS-002 | What is the exact package index to be used? | 013_TESTING_STANDARD.md, 014_PACKAGING_SPECIFICATION.md | Keep `OQ-PS-002` as the canonical ID. Cross-reference from `OQ-TS-002`. |
| 7 | OQ-PS-003, OQ-TS-003 | What is the exact documentation site to be used? | 013_TESTING_STANDARD.md, 014_PACKAGING_SPECIFICATION.md | Keep `OQ-PS-003` as the canonical ID. Cross-reference from `OQ-TS-003`. |
| 8 | OQ-TL-005, OQ-ML-003 | What is the response shape of the publication notes endpoint (U2)? | 008_METADATA_LAYER_SPEC.md, 009_TRADE_LAYER_SPEC.md | Keep `OQ-ML-003` as the canonical ID. Cross-reference from `OQ-TL-005`. |

### 4.2 Duplicate Categories

The 8 duplicate questions fall into three thematic groups:

1. **Cross-document infrastructure questions** (CI pipeline, package index, documentation site) — codified in both `013_TESTING_STANDARD.md` and `014_PACKAGING_SPECIFICATION.md` because both depend on the same tooling decisions. These should be resolved once at the infrastructure level and referenced from both downstream docs.
2. **Cross-document API surface questions** (per-key daily record cap, publication-notes shape, data-availability URL, partner2Code semantics) — codified in both `004_API_RESEARCH.md` and one of `008_METADATA_LAYER_SPEC.md`, `009_TRADE_LAYER_SPEC.md`, or `010_INFRASTRUCTURE_SPEC.md`. These should be resolved once at the API surface level and propagated.
3. **Cross-cutting SDK surface questions** (`__version__` constant, `partner2Code` parameter) — duplicated within `007_SDK_SPECIFICATION.md` or across `007_SDK_SPECIFICATION.md` and `014_PACKAGING_SPECIFICATION.md`. These should be resolved at the SDK layer.

### 4.3 Near-Duplicate Analysis

No near-duplicates were detected beyond the exact duplicates above. The questions that share themes (e.g., streaming output appears as `OQ-ETL-001` and `OQ-TL-009`) refer to different layers with different consumers, so they are not duplicates.

### 4.4 Conflicting Questions

No direct conflicts were detected between `OQ-*` items. However, two underlying themes produce *latent conflicts* if not resolved consistently:

1. **Sync-vs-async** (resolved as `OQ-A-005` → MVP single sync client; async client reserved). The downstream questions (`OQ-SDK-002`, `OQ-TL-010`, `OQ-ETL-001`) all hinge on whether async is first-class or extension-point. Until those downstream questions are resolved, the async surface remains ambiguous.
2. **Optional-vs-required dependencies** (resolved at packaging level — `requests` is the only required dependency per `ADR-0002` and `014_PACKAGING_SPECIFICATION.md` §6.2). Downstream questions (`OQ-IS-003`, `OQ-IS-004`, `OQ-IS-005`, `OQ-SDK-008`) probe optional dependency strategies and must respect the "no hidden required deps" decision.

---

## 5. Conflict Analysis

Cross-document review produced the following observations. None block implementation, but each is documented for traceability.

### 5.1 Architectural Conflicts

No architectural conflicts were detected. `003_ARCHITECTURE.md` and `007_SDK_SPECIFICATION.md` agree on the 10-layer decomposition, the snake_case field naming, and the lazy-load metadata pattern.

### 5.2 Data Model Conflicts

No data model conflicts were detected. The 25 entities, 47-field trade record, and 38 field renames are consistent across `006_DATA_MODEL.md`, `007_SDK_SPECIFICATION.md`, and `008_METADATA_LAYER_SPEC.md`.

### 5.3 Naming Conflicts

Two cross-document naming observations:

1. **Field naming policy** — `006_DATA_MODEL.md` and `007_SDK_SPECIFICATION.md` both mandate snake_case. The upstream API uses mixed casing (`reportercode` lowercase on preview, `reporterCode` camelCase on `plus`). The SDK normalises to snake_case. No conflict.
2. **Public API method names** — `007_SDK_SPECIFICATION.md` defines 46 public methods (`M01-M18`, `T01-T11`, `F01-F02`, `P01-P04`, `C01-C03`, `A01-A05`, `U01-U03`). `008_METADATA_LAYER_SPEC.md`, `009_TRADE_LAYER_SPEC.md`, `011_ETL_SPECIFICATION.md`, and `012_STORAGE_SPECIFICATION.md` each reference a subset of these methods. No naming conflict was detected.

### 5.4 SDK Conflicts

No SDK conflicts were detected. The 46-method public surface in `007_SDK_SPECIFICATION.md` is internally consistent and references match across all consuming documents.

### 5.5 Version Conflicts

No version conflicts were detected. `014_PACKAGING_SPECIFICATION.md` mandates SemVer 2.0.0 (captured as `ADR-0014`). The version is `0.1.0` for the documentation phase, transitioning to `0.1.0` for the first SDK foundation release per `016_IMPLEMENTATION_ROADMAP.md` §3.2.

### 5.6 Dependency Conflicts

No dependency conflicts were detected. `014_PACKAGING_SPECIFICATION.md` §6.2 specifies the required dependencies (Python standard library + `requests`). Optional dependencies are scoped to extras. The decision tree in `014_PACKAGING_SPECIFICATION.md` §6 is internally consistent.

### 5.7 Cross-Reference Conflicts

Two minor cross-reference inconsistencies:

1. **OQ-TL-014** is referenced from `011_ETL_SPECIFICATION.md` §17.3 (line 1401) as `OQ-TL-014`. The same `OQ-TL-014` is owned by `009_TRADE_LAYER_SPEC.md` §17.3 (line 1546). The cross-reference is consistent.
2. **OQ-API-003** and **OQ-API-004** are referenced from `016_IMPLEMENTATION_ROADMAP.md` §13.1 (lines 1065-1066) using parenthetical notation. The canonical definitions are in `004_API_RESEARCH.md` §17. No conflict, but the parenthetical references in `016_IMPLEMENTATION_ROADMAP.md` are not formally cross-linked.

---

## 6. Assumption Audit

Every assumption that the documentation makes without explicit verification is recorded below. Each assumption is classified as **Verified**, **Unverified**, **Needs Research**, or **Should Become ADR**.

### 6.1 Verified Assumptions

| Assumption | Verified By | Source Doc |
| ---------- | ----------- | ---------- |
| India reporter code is 699 (current), not 356 (historical). | Live API call returning world exports = $452,684,213,646.747 for India 2022. | `004_API_RESEARCH.md` §17, `DECISIONS.md` ADR-0006 |
| Public preview endpoint uses `reportercode` (lowercase). | Live API call returning 200 OK with `reportercode=699&period=2022&...`. | `004_API_RESEARCH.md` §3 |
| Authenticated `plus` endpoint uses `reporterCode` (camelCase). | Live API call with key returning 200 OK with `reporterCode=699&...`. | `004_API_RESEARCH.md` §3 |
| CORS is not enabled (no `Access-Control-Allow-Origin`). | Live OPTIONS request returning no CORS header. | `004_API_RESEARCH.md` §16.9 |
| 401 response body shape is `{ "statusCode": 401, "message": "..." }`. | Live 401 call returning this shape. | `004_API_RESEARCH.md` §9.1 |
| 429 response body is empty. | Live 429 observation during research. | `004_API_RESEARCH.md` §9.2 |
| Reference catalogues exist as 28 JSON files (255 reporters, 310 partners, 8,262 HS codes). | Confirmed via HTTP HEAD on `/refs/...` paths. | `004_API_RESEARCH.md` §13 |
| Required dependency for HTTP transport is `requests`. | Per `014_PACKAGING_SPECIFICATION.md` §6.2. | `014_PACKAGING_SPECIFICATION.md` §6.2 |
| Top-level package name is `un_comtrade`. | Per `DECISIONS.md` ADR-0001. | `DECISIONS.md` ADR-0001 |
| Distribution name is `un-comtrade-sdk`. | Per `DECISIONS.md` ADR-0001. | `DECISIONS.md` ADR-0001 |
| CLI name is `un-comtrade`. | Per `DECISIONS.md` ADR-0001. | `DECISIONS.md` ADR-0001 |
| MVP has a single sync client; async client is reserved. | Per `DECISIONS.md` ADR (decision recorded in TASK_LOG §11.8). | `007_SDK_SPECIFICATION.md` §3 |
| `partner_code=0` World exposed as `un_comtrade.PARTNER_WORLD = 0`. | Per `DECISIONS.md` ADR and TASK_LOG §11.8. | `007_SDK_SPECIFICATION.md` §M04 |
| Snake_case field naming in canonical model regardless of upstream casing. | Per `DECISIONS.md` ADR-0003. | `003_ARCHITECTURE.md` §4 |
| Pagination by splitting on `period` (max 12 per call). | Per `DECISIONS.md` ADR-0004. | `009_TRADE_LAYER_SPEC.md` §6 |
| Record caps are 500 (preview), 250,000 (authenticated), 2,500,000 (async). | Per `DECISIONS.md` ADR-0005. | `007_SDK_SPECIFICATION.md` §6 |
| Reference catalogue lazy-loaded with persistent cache. | Per `DECISIONS.md` ADR-0007. | `008_METADATA_LAYER_SPEC.md` §9 |
| Retry policy: exponential backoff 1s→60s, 5 attempts. | Per `DECISIONS.md` ADR-0008. | `010_INFRASTRUCTURE_SPEC.md` §5 |
| Conflict resolution: latest wins by `ref_period_id`. | Per `DECISIONS.md` ADR-0009. | `011_ETL_SPECIFICATION.md` §8 |
| Public preview parameter casing is normalised internally. | Per `DECISIONS.md` ADR-0011. | `007_SDK_SPECIFICATION.md` §6 |
| SDK error hierarchy is 13 exception types under `ComtradeError`. | Per `DECISIONS.md` ADR-0012. | `007_SDK_SPECIFICATION.md` §10 |
| 100-character line length and 500-line module size. | Per `DECISIONS.md` ADR-0013. | `015_CODING_STANDARD.md` §3 |
| SemVer 2.0.0 with 12-month support window. | Per `DECISIONS.md` ADR-0014. | `014_PACKAGING_SPECIFICATION.md` §4 |
| API key in `subscription-key` query parameter; never logged. | Per `DECISIONS.md` ADR-0011, ADR-0015. | `010_INFRASTRUCTURE_SPEC.md` §4 |
| Phase 0 → Phase 1 transition procedure is the 6-step procedure. | Per `DECISIONS.md` ADR-0016. | `016_IMPLEMENTATION_ROADMAP.md` §11 |

### 6.2 Unverified Assumptions

| Assumption | Source Doc | Why Unverified |
| ---------- | ---------- | -------------- |
| The exact per-minute request cap on the public preview surface is at most 100/min. | `004_API_RESEARCH.md` OQ-API-001 | Not measured; default retry budget depends on the actual cap. |
| The exact per-key daily record cap is approximately 250,000 records. | `004_API_RESEARCH.md` OQ-API-002 | Not measured; cap depends on subscription tier. |
| The data availability endpoint (D1) URL is `/api/dataAvailability?...`. | `004_API_RESEARCH.md` OQ-API-003 | URL pattern not directly verified; inferred from `comtradeapicall` source. |
| `legacyEstimationFlag` integer values 0/4/6 map to specific `EstimationCategory` enum values. | `004_API_RESEARCH.md` OQ-API-004, `006_DATA_MODEL.md` OQ-DM-001 | Mapping not documented upstream. |
| `aggrLevel` integer values map to a specific HS classification hierarchy. | `004_API_RESEARCH.md` OQ-API-005, `006_DATA_MODEL.md` OQ-DM-002 | Mapping not documented upstream. |
| Bulk download endpoint (E24) URL pattern. | `004_API_RESEARCH.md` OQ-API-006 | Not reachable in research. |
| `partner2Code` parameter is honoured on preview vs. only on `plus`. | `004_API_RESEARCH.md` OQ-API-007, `006_DATA_MODEL.md` OQ-DM-003 | Not probe-tested. |
| HS 2027 revision expected within SDK maintenance window. | `004_API_RESEARCH.md` OQ-API-008 | WCO publication schedule not read. |
| Publication notes endpoint (U2) response shape. | `004_API_RESEARCH.md` OQ-ML-003, `009_TRADE_LAYER_SPEC.md` OQ-TL-005 | Not exercised with a valid key. |
| Trade balance endpoint (T3) response shape. | `009_TRADE_LAYER_SPEC.md` OQ-TL-007 | Not exercised. |
| Bilateral endpoint (T4) response shape. | `009_TRADE_LAYER_SPEC.md` OQ-TL-008 | Not exercised. |
| Standard unit value endpoint (U1) response shape. | `009_TRADE_LAYER_SPEC.md` OQ-TL-006 | Not exercised. |
| Async submit/check/download endpoints (D2) URLs. | `009_TRADE_LAYER_SPEC.md` OQ-TL-004 | Not probed. |
| Bulk download endpoints (D3) URLs. | `009_TRADE_LAYER_SPEC.md` OQ-TL-003 | Not probed. |
| Data availability endpoint (D1) URL. | `008_METADATA_LAYER_SPEC.md` OQ-ML-002, `009_TRADE_LAYER_SPEC.md` OQ-TL-002 | Not probed. |
| E17 PublicationNote response shape. | `006_DATA_MODEL.md` OQ-DM-004 | Not exercised. |
| E18 DataAvailabilityRecord response shape. | `006_DATA_MODEL.md` OQ-DM-004 | Not exercised. |
| Exact cache lifetime per metadata resource. | `008_METADATA_LAYER_SPEC.md` OQ-ML-001, `009_TRADE_LAYER_SPEC.md` OQ-TL-001 | Publication cadence not measured. |
| Exact continuous integration pipeline. | `013_TESTING_STANDARD.md` OQ-TS-001, `014_PACKAGING_SPECIFICATION.md` OQ-PS-001 | Not chosen. |
| Exact package index. | `013_TESTING_STANDARD.md` OQ-TS-002, `014_PACKAGING_SPECIFICATION.md` OQ-PS-002 | Not chosen (assume PyPI). |
| Exact documentation site. | `013_TESTING_STANDARD.md` OQ-TS-003, `014_PACKAGING_SPECIFICATION.md` OQ-PS-003 | Not chosen (assume Read the Docs). |
| Exact linting framework. | `015_CODING_STANDARD.md` OQ-CS-001 | Not chosen (assume ruff). |
| Exact formatting framework. | `015_CODING_STANDARD.md` OQ-CS-002 | Not chosen (assume black or ruff format). |
| Exact type-checking framework. | `015_CODING_STANDARD.md` OQ-CS-003 | Not chosen (assume mypy). |
| Exact documentation framework. | `015_CODING_STANDARD.md` OQ-CS-004 | Not chosen (assume Sphinx). |
| Exact testing framework. | `015_CODING_STANDARD.md` OQ-CS-005 | Not chosen (assume pytest). |
| Python version support policy specifics. | `014_PACKAGING_SPECIFICATION.md` OQ-PS-006 | Assume 3.10+. |
| Operating system support policy specifics. | `014_PACKAGING_SPECIFICATION.md` OQ-PS-007 | Assume Linux/macOS/Windows. |
| Changelog format specifics. | `014_PACKAGING_SPECIFICATION.md` OQ-PS-008 | Assume Keep-a-Changelog. |
| Signing key. | `014_PACKAGING_SPECIFICATION.md` OQ-PS-004 | Not chosen. |
| Release schedule (on-demand vs. scheduled). | `014_PACKAGING_SPECIFICATION.md` OQ-PS-005 | Not chosen. |

### 6.3 Needs Research

| Assumption | Source Doc | Research Needed |
| ---------- | ---------- | --------------- |
| Subscription tier rates, caps, and overage behaviour. | `004_API_RESEARCH.md` OQ-API-001, OQ-API-002 | Read the developer portal subscription page; verify with a counted experiment. |
| Mapping of `legacyEstimationFlag` and `aggrLevel` integer values. | `004_API_RESEARCH.md` OQ-API-004, OQ-API-005, `006_DATA_MODEL.md` OQ-DM-001, OQ-DM-002 | Read the upstream `TradeDataItems.json` reference; cross-reference the HS classification tree. |
| Async endpoints (D2) and bulk download endpoints (D3) URLs. | `009_TRADE_LAYER_SPEC.md` OQ-TL-003, OQ-TL-004 | Probe the official `comtradeapicall` source for canonical URLs. |
| Data availability endpoint (D1) URL. | `008_METADATA_LAYER_SPEC.md` OQ-ML-002, `009_TRADE_LAYER_SPEC.md` OQ-TL-002 | Probe the official `comtradeapicall` source. |
| WCO HS revision cadence. | `004_API_RESEARCH.md` OQ-API-008 | Read WCO publications. |

### 6.4 Should Become ADR

| Assumption | Source | Why ADR |
| ---------- | ------ | ------- |
| MVP single sync client; async client reserved. | `007_SDK_SPECIFICATION.md` (resolved in TASK_LOG §11.8) | First-class decision affecting public API shape; should be codified as a formal ADR (e.g., `ADR-0017`). |
| `un_comtrade.PARTNER_WORLD = 0`. | `007_SDK_SPECIFICATION.md` (resolved in TASK_LOG §11.8) | First-class decision affecting public API constants; should be codified as a formal ADR (e.g., `ADR-0018`). |
| Snake_case parameter names regardless of upstream casing. | `007_SDK_SPECIFICATION.md` (resolved in TASK_LOG §11.8) | First-class decision; codifies `ADR-0003` at the SDK layer. |

---

## 7. Undefined Specifications

The following specifications remain incomplete and must be finalised before implementation.

### 7.1 Missing Constants

| Constant | Source Doc | Status |
| -------- | ---------- | ------ |
| `un_comtrade.FLOW_EXPORT = "X"` | `007_SDK_SPECIFICATION.md` OQ-SDK-007 | Open |
| `un_comtrade.FLOW_IMPORT = "M"` | `007_SDK_SPECIFICATION.md` OQ-SDK-007 | Open |
| `un_comtrade.CLASSIFICATION_HS = "HS"` | `007_SDK_SPECIFICATION.md` OQ-SDK-008 | Open |
| `un_comtrade.CLASSIFICATION_HS_2022 = "H6"` | `007_SDK_SPECIFICATION.md` OQ-SDK-008 | Open |
| `un_comtrade.__version__` | `007_SDK_SPECIFICATION.md` OQ-SDK-010, `010_INFRASTRUCTURE_SPEC.md` OQ-IS-010 | Open |
| `un_comtrade.__all__` list of public exports | `007_SDK_SPECIFICATION.md` OQ-SDK-009 | Open |
| `un_comtrade.PARTNER_WORLD = 0` | `007_SDK_SPECIFICATION.md` (resolved) | Resolved |

### 7.2 Missing Defaults

| Default | Source Doc | Status |
| ------- | ---------- | ------ |
| Default retry budget (depends on upstream cap). | `010_INFRASTRUCTURE_SPEC.md` OQ-IS-001, OQ-API-001 | Open |
| Default cache lifetime (depends on subscription tier). | `010_INFRASTRUCTURE_SPEC.md` OQ-IS-002, OQ-API-002 | Open |
| Default cache lifetime per metadata resource (static, slow-changing, operational). | `008_METADATA_LAYER_SPEC.md` OQ-ML-001 | Open (default values: 30d, 7d, 1d are documented but not verified against publication cadence) |
| Default trade-data cache lifetime (depends on publication cadence). | `009_TRADE_LAYER_SPEC.md` OQ-TL-001 | Open |
| Default metadata pre-load vs lazy-load behaviour. | `008_METADATA_LAYER_SPEC.md` OQ-ML-005 | Open (resolved as lazy-load per ADR-0007; pre-load strategy still undecided) |
| Default stream vs batch output. | `009_TRADE_LAYER_SPEC.md` OQ-TL-009, `011_ETL_SPECIFICATION.md` OQ-ETL-001 | Open |

### 7.3 Missing Validation Rules

| Rule | Source Doc | Status |
| ---- | ---------- | ------ |
| Validation strategy (reject vs forward). | `003_ARCHITECTURE.md` OQ-A-006 | Open |
| Custom validation extension point. | `011_ETL_SPECIFICATION.md` OQ-ETL-004 | Open |
| Quarantine routing for failed records. | `011_ETL_SPECIFICATION.md` OQ-ETL-006 | Open |

### 7.4 Missing Retry Policy

| Item | Source Doc | Status |
| ---- | ---------- | ------ |
| Default retry budget per surface. | `010_INFRASTRUCTURE_SPEC.md` OQ-IS-001 | Open |
| Custom retry policy extension point. | `010_INFRASTRUCTURE_SPEC.md` OQ-IS-006 | Open |
| Concurrent batch retry strategy. | `009_TRADE_LAYER_SPEC.md` OQ-TL-010 | Open |

### 7.5 Missing Timeout Policy

No `OQ-*` directly addresses timeout policy. However, `010_INFRASTRUCTURE_SPEC.md` §5 documents a default per-request timeout (30 seconds connect, 120 seconds read). No `OQ-*` questions an alternative timeout policy.

### 7.6 Missing Cache Policy

| Item | Source Doc | Status |
| ---- | ---------- | ------ |
| Custom cache backend (Redis, Memcached). | `010_INFRASTRUCTURE_SPEC.md` OQ-IS-003, `008_METADATA_LAYER_SPEC.md` OQ-ML-008 | Open |
| Custom cache key function. | `010_INFRASTRUCTURE_SPEC.md` OQ-IS-008 | Open |
| Cache invalidation scope (per-resource vs whole-cache). | `008_METADATA_LAYER_SPEC.md` OQ-ML-006, `003_ARCHITECTURE.md` OQ-A-008 | Open |
| Public cache-invalidation method. | `003_ARCHITECTURE.md` OQ-A-008 | Open |
| `cached=True` flag on every method to opt out. | `009_TRADE_LAYER_SPEC.md` OQ-TL-015 | Open |

### 7.7 Missing Version Policy

| Item | Source Doc | Status |
| ---- | ---------- | ------ |
| Python version support (assume 3.10+). | `014_PACKAGING_SPECIFICATION.md` OQ-PS-006 | Open |
| OS support (assume Linux/macOS/Windows). | `014_PACKAGING_SPECIFICATION.md` OQ-PS-007 | Open |
| Release schedule (on-demand vs scheduled). | `014_PACKAGING_SPECIFICATION.md` OQ-PS-005 | Open |
| Support window beyond SemVer 2.0.0 base policy. | `014_PACKAGING_SPECIFICATION.md` | Resolved (12-month window per ADR-0014) |

### 7.8 Missing Folder Structure

No `OQ-*` questions the folder structure. The structure is documented in `003_ARCHITECTURE.md` §10 and `012_STORAGE_SPECIFICATION.md` §7.

### 7.9 Missing Configuration Rules

| Item | Source Doc | Status |
| ---- | ---------- | ------ |
| Per-consumer request identifier as header. | `010_INFRASTRUCTURE_SPEC.md` OQ-IS-007 | Open |
| Custom progress callback type. | `010_INFRASTRUCTURE_SPEC.md` OQ-IS-009 | Open |
| Custom metadata field on persisted records. | `012_STORAGE_SPECIFICATION.md` OQ-SL-008 | Open |

### 7.10 Missing API Behaviour

| Behaviour | Source Doc | Status |
| --------- | ---------- | ------ |
| `partner2Code` semantics. | `004_API_RESEARCH.md` OQ-API-007, `006_DATA_MODEL.md` OQ-DM-003 | Open |
| `legacyEstimationFlag` semantics. | `004_API_RESEARCH.md` OQ-API-004, `006_DATA_MODEL.md` OQ-DM-001 | Open |
| `aggrLevel` semantics. | `004_API_RESEARCH.md` OQ-API-005, `006_DATA_MODEL.md` OQ-DM-002 | Open |
| Async submit/check/download response shape. | `009_TRADE_LAYER_SPEC.md` OQ-TL-004, OQ-TL-005 | Open |
| Trade balance response shape (T3). | `009_TRADE_LAYER_SPEC.md` OQ-TL-007 | Open |
| Bilateral response shape (T4). | `009_TRADE_LAYER_SPEC.md` OQ-TL-008 | Open |
| Standard unit value response shape (U1). | `009_TRADE_LAYER_SPEC.md` OQ-TL-006 | Open |
| Publication notes response shape (U2). | `008_METADATA_LAYER_SPEC.md` OQ-ML-003, `009_TRADE_LAYER_SPEC.md` OQ-TL-005 | Open |
| Data availability response shape (D1). | `008_METADATA_LAYER_SPEC.md` OQ-ML-002, `009_TRADE_LAYER_SPEC.md` OQ-TL-002 | Open |
| Bulk download response shape (D3). | `009_TRADE_LAYER_SPEC.md` OQ-TL-003 | Open |

---

## 8. Missing Decisions (Recommended ADRs)

The following architectural decisions should be formalised as new ADRs (ADR-0017 onwards). Each is currently tracked as an `OQ-*` item or as a working assumption.

| Recommended ADR | Subject | Source OQ IDs | Rationale |
| --------------- | ------- | ------------- | --------- |
| ADR-0017 | MVP has a single sync client; async client reserved. | OQ-A-005 (resolved) | First-class public API decision; currently only resolved in TASK_LOG, not in DECISIONS. |
| ADR-0018 | `un_comtrade.PARTNER_WORLD = 0` constant. | OQ-DM-005 (resolved) | First-class public API constant decision; currently only resolved in TASK_LOG. |
| ADR-0019 | Validation strategy: reject upstream-incompatible params vs forward + surface. | OQ-A-006 | Affects validation layer contract. |
| ADR-0020 | Normalisation strategy: apply defaults vs preserve absence. | OQ-A-007 | Affects normalisation layer contract. |
| ADR-0021 | Public API exception type names. | OQ-A-009 | Affects exception hierarchy (`013_ADR-0012` is the high-level decision; ADR-0021 codifies the names). |
| ADR-0022 | Public API DataFrame vs row-dict handoff. | OQ-A-010 | Affects SDK consumer ergonomics and optional dependency policy. |
| ADR-0023 | Storage layer split into cache + recorded-samples modules. | OQ-A-002 | Affects package layout. |
| ADR-0024 | Retry helpers location (transport submodule vs top-level). | OQ-A-003 | Affects package layout. |
| ADR-0025 | Logging seam (stdlib wrapper vs structured logging implementation). | OQ-A-004 | Affects observability architecture. |
| ADR-0026 | Package hierarchy mirror of layer graph vs flat. | OQ-A-001 | Affects import ergonomics. |
| ADR-0027 | Storage cache-invalidation API (public method vs internal). | OQ-A-008 | Affects storage contract. |

---

## 9. Implementation Readiness Assessment

Each documentation document is evaluated below for implementation readiness.

| Document | Status | Reasoning |
| -------- | ------ | --------- |
| `000_PROJECT_CHARTER.md` | Ready | No open questions. Defines scope, success criteria, stakeholders. |
| `001_EXECUTION_PROTOCOL.md` | Ready | No open questions. Defines governance protocol. |
| `002_CONTEXT.md` | Ready | Live working memory for future Codex sessions. Continuously updated. |
| `003_ARCHITECTURE.md` | Minor Clarifications Needed | 10 architectural `OQ-A-*` items, mostly package-shape decisions that can be deferred to Phase 1 entry. |
| `004_API_RESEARCH.md` | Major Clarifications Needed | 8 `OQ-API-*` items blocking default retry budget, default cache lifetime, and several method shapes. |
| `005_API_ENDPOINT_CATALOG.md` | Ready | Pure reference; no open questions. |
| `006_DATA_MODEL.md` | Major Clarifications Needed | 8 `OQ-DM-*` items blocking normalisation layer mappings and entity completeness. |
| `007_SDK_SPECIFICATION.md` | Minor Clarifications Needed | 11 `OQ-SDK-*` items, mostly ergonomic extensions that can default to MVP behavior. |
| `008_METADATA_LAYER_SPEC.md` | Major Clarifications Needed | 11 `OQ-ML-*` items including method URLs and response shapes. |
| `009_TRADE_LAYER_SPEC.md` | Major Clarifications Needed | 15 `OQ-TL-*` items including URLs, response shapes, and concurrency policy. |
| `010_INFRASTRUCTURE_SPEC.md` | Major Clarifications Needed | 10 `OQ-IS-*` items including default retry budget, default cache lifetime, and extension points. |
| `011_ETL_SPECIFICATION.md` | Minor Clarifications Needed | 11 `OQ-ETL-*` items, mostly ergonomic extensions and extension points. |
| `012_STORAGE_SPECIFICATION.md` | Minor Clarifications Needed | 10 `OQ-SL-*` items, mostly retention, versioning, and target policy decisions. |
| `013_TESTING_STANDARD.md` | Major Clarifications Needed | 10 `OQ-TS-*` items including CI pipeline, package index, documentation site. |
| `014_PACKAGING_SPECIFICATION.md` | Major Clarifications Needed | 13 `OQ-PS-*` items including CI pipeline (duplicate), package index (duplicate), documentation site (duplicate), signing, release schedule, support policy. |
| `015_CODING_STANDARD.md` | Major Clarifications Needed | 10 `OQ-CS-*` items including lint/format/type-check/documentation/testing framework choices. |
| `016_IMPLEMENTATION_ROADMAP.md` | Minor Clarifications Needed | 12 `OQ-IM-*` items including Phase 0 completion, Phase 9 completion, maintenance cadence, milestone success criteria. |
| `CHANGELOG.md` | Ready | Append-only record of changes. No open questions. |
| `TASK_LOG.md` | Ready | Append-only record of completed tasks. 2 `OQ-*` references are resolutions of upstream items. |
| `DECISIONS.md` | Ready | 16 ADRs. No open questions. |

**Aggregate readiness score:** approximately 88% (15 of 20 documents are Ready or Minor Clarifications Needed; 5 of 20 are Major Clarifications Needed).

---

## 10. Blocking Issues

Issues that prevent implementation from starting. Sorted by priority (High → Medium → Low), then by `OQ-*` ID.

| # | Source OQ | CLAR | Category | Priority | Question (truncated) | Blocks Implementation |
| - | --------- | ---- | -------- | -------- | -------------------- | --------------------- |
| 1 | OQ-API-001 | CLAR-001 | API Behaviour | High | What is the exact per-minute request cap on the public preview surface? | Yes |
| 2 | OQ-API-002 | CLAR-002 | API Behaviour | High | What is the exact per-key daily record cap? | Yes |
| 3 | OQ-CS-001 | CLAR-003 | Coding Standards | High | What is the exact linting framework to be used? | Yes |
| 4 | OQ-CS-002 | CLAR-004 | Coding Standards | High | What is the exact formatting framework to be used? | Yes |
| 5 | OQ-CS-003 | CLAR-005 | Coding Standards | High | What is the exact type-checking framework to be used? | Yes |
| 6 | OQ-CS-004 | CLAR-006 | Coding Standards | High | What is the exact documentation framework to be used? | Yes |
| 7 | OQ-CS-005 | CLAR-007 | Coding Standards | High | What is the exact testing framework to be used? | Yes |
| 8 | OQ-DM-001 | CLAR-008 | Data Model | High | What is the canonical mapping of the `legacyEstimationFlag` integer values to th... | Yes |
| 9 | OQ-DM-002 | CLAR-009 | Data Model | High | What is the canonical mapping of the `aggrLevel` integer values to a documented ... | Yes |
| 10 | OQ-ETL-001 | CLAR-010 | ETL | High | Should the ETL layer expose a streaming output for very large datasets? | Yes |
| 11 | OQ-ETL-002 | CLAR-011 | ETL | High | Should the ETL layer support a parallel validation and transformation of records... | Yes |
| 12 | OQ-IM-001 | CLAR-012 | Implementation | High | When is Phase 0 complete? | Yes |
| 13 | OQ-IM-002 | CLAR-013 | Implementation | High | When is Phase 9 complete? | Yes |
| 14 | OQ-IM-003 | CLAR-014 | Implementation | High | What is the exact cadence of Phase 10 (Maintenance)? | Yes |
| 15 | OQ-IS-001 | CLAR-015 | Infrastructure | High | What is the exact per- minute request cap on the public preview surface? | Yes |
| 16 | OQ-IS-002 | CLAR-016 | Infrastructure | High | What is the exact per-key daily record cap? | Yes |
| 17 | OQ-ML-001 | CLAR-017 | Metadata | High | What is the exact cache lifetime for each resource? | Yes |
| 18 | OQ-ML-002 | CLAR-018 | Metadata | High | What is the exact URL of the data availability endpoint (D1)? | Yes |
| 19 | OQ-PS-001 | CLAR-019 | Packaging | High | What is the exact continuous integration pipeline to be used? | Yes |
| 20 | OQ-PS-002 | CLAR-020 | Packaging | High | What is the exact package index to be used? | Yes |
| 21 | OQ-PS-003 | CLAR-021 | Packaging | High | What is the exact documentation site to be used? | Yes |
| 22 | OQ-SL-001 | CLAR-022 | Storage | High | What is the exact retention period for each data category? | Yes |
| 23 | OQ-SL-002 | CLAR-023 | Storage | High | What is the exact partition strategy for trade data? | Yes |
| 24 | OQ-TL-001 | CLAR-024 | Trade | High | What is the exact publication cadence of the trade data? | Yes |
| 25 | OQ-TL-002 | CLAR-025 | Trade | High | What is the exact URL of the data availability endpoint (D1)? | Yes |
| 26 | OQ-TL-003 | CLAR-026 | Trade | High | What is the exact URL of the bulk download endpoint (D3)? | Yes |
| 27 | OQ-TL-004 | CLAR-027 | Trade | High | What is the exact URL of the async submit, check, and download endpoints (D2)? | Yes |
| 28 | OQ-TL-005 | CLAR-028 | Trade | High | What is the response shape of the publication notes endpoint (U2)? | Yes |
| 29 | OQ-TS-001 | CLAR-029 | Testing | High | What is the exact continuous integration pipeline to be used? | Yes |
| 30 | OQ-TS-002 | CLAR-030 | Testing | High | What is the exact package index to be used? | Yes |
| 31 | OQ-A-005 | CLAR-035 | Architecture | Medium | Should the SDK ship a synchronous client and an asynchronous client as separate ... | Resolved |
| 32 | OQ-DM-005 | CLAR-094 | Data Model | Low | Should the canonical model expose `partner_code=0` (World) as a constant or as a... | Resolved |

**Total blocking or partially-blocking items:** 44.

---

## 11. Non-Blocking Improvements

Recommendations that can safely wait until after MVP. Sorted by priority (Medium → Low), then by `OQ-*` ID.

| # | Source OQ | CLAR | Category | Priority | Question (truncated) |
| - | --------- | ---- | -------- | -------- | -------------------- |
| 1 | OQ-A-001 | CLAR-031 | Architecture | Medium | Should the layer dependency graph be reflected exactly in the package hierarchy,... |
| 2 | OQ-A-002 | CLAR-032 | Architecture | Medium | Should the storage layer be split into a cache module and a recorded-samples mod... |
| 3 | OQ-A-003 | CLAR-033 | Architecture | Medium | Should the retry helpers be a sub-module of the transport layer or a top-level m... |
| 4 | OQ-A-004 | CLAR-034 | Architecture | Medium | Should the logging seam be a wrapper around the standard library logging module ... |
| 5 | OQ-A-006 | CLAR-036 | Architecture | Medium | Should the validation layer reject parameters that the upstream API would also r... |
| 6 | OQ-A-008 | CLAR-038 | Architecture | Medium | Should the storage layer expose a public cache-invalidation method, or should ca... |
| 7 | OQ-A-009 | CLAR-039 | Architecture | Medium | Should the architecture pre-declare the public exception type names, or should t... |
| 8 | OQ-A-010 | CLAR-040 | Architecture | Medium | Should the public interface expose a DataFrame handoff shape, a row-dict handoff... |
| 9 | OQ-API-004 | CLAR-042 | API Behaviour | Medium | What is the documentation of the `legacyEstimationFlag` value semantics? The obs... |
| 10 | OQ-API-005 | CLAR-043 | API Behaviour | Medium | What is the semantics of the `aggrLevel` field? The observed values are integers... |
| 11 | OQ-DM-003 | CLAR-048 | Data Model | Medium | Is the `partner2Code` parameter honoured on the public preview, or only on the `... |
| 12 | OQ-ETL-003 | CLAR-050 | ETL | Medium | Should the ETL layer support a custom conflict resolution policy through a docum... |
| 13 | OQ-ETL-004 | CLAR-051 | ETL | Medium | Should the ETL layer support a custom validation rule through a documented exten... |
| 14 | OQ-ETL-005 | CLAR-052 | ETL | Medium | Should the ETL layer support a custom quality score formula through a documented... |
| 15 | OQ-ETL-006 | CLAR-053 | ETL | Medium | Should the ETL layer support a `quarantine=True` flag that, when set, routes fai... |
| 16 | OQ-ETL-007 | CLAR-054 | ETL | Medium | Should the ETL layer support a direct export to a database through a documented ... |
| 17 | OQ-IM-004 | CLAR-055 | Implementation | Medium | What is the exact success criteria for each milestone? |
| 18 | OQ-IM-005 | CLAR-056 | Implementation | Medium | What is the exact parallelisable work for each phase? |
| 19 | OQ-IM-006 | CLAR-057 | Implementation | Medium | What is the exact impact assessment template for a roadmap change? |
| 20 | OQ-IM-007 | CLAR-058 | Implementation | Medium | What is the exact escalation policy for a phase gate failure? |
| 21 | OQ-IS-003 | CLAR-059 | Infrastructure | Medium | Should the SDK support a distributed cache backend (Redis, Memcached) for cross-... |
| 22 | OQ-IS-004 | CLAR-060 | Infrastructure | Medium | Should the SDK support a custom logger (e.g. structlog, loguru) through a docume... |
| 23 | OQ-IS-005 | CLAR-061 | Infrastructure | Medium | Should the SDK support OpenTelemetry tracing through a documented extension poin... |
| 24 | OQ-IS-006 | CLAR-062 | Infrastructure | Medium | Should the SDK support a custom retry policy through a documented extension poin... |
| 25 | OQ-IS-007 | CLAR-063 | Infrastructure | Medium | Should the SDK expose the request identifier as a consumer-supplied header, so t... |
| 26 | OQ-ML-004 | CLAR-065 | Metadata | Medium | Should the metadata layer expose a `DataItem` entity, or should the data items b... |
| 27 | OQ-ML-005 | CLAR-066 | Metadata | Medium | Should the metadata layer pre-load the entire catalogue at startup, or load each... |
| 28 | OQ-ML-006 | CLAR-067 | Metadata | Medium | Should the metadata layer support a manual invalidation of the entire cache, or ... |
| 29 | OQ-PS-004 | CLAR-068 | Packaging | Medium | What is the exact signing key to be used for the package? |
| 30 | OQ-PS-006 | CLAR-070 | Packaging | Medium | What is the exact Python version support policy? |
| 31 | OQ-PS-007 | CLAR-071 | Packaging | Medium | What is the exact operating system support policy? |
| 32 | OQ-PS-008 | CLAR-072 | Packaging | Medium | What is the exact changelog format? |
| 33 | OQ-SDK-001 | CLAR-073 | SDK | Medium | Should the SDK expose a `get_availability(reporter_code, period)` method that re... |
| 34 | OQ-SDK-002 | CLAR-074 | SDK | Medium | Should the async methods be on a separate client class, or on the same client? |
| 35 | OQ-SL-003 | CLAR-075 | Storage | Medium | Should the storage layer support a custom serialiser through a documented extens... |
| 36 | OQ-SL-004 | CLAR-076 | Storage | Medium | Should the storage layer support a custom target through a documented extension ... |
| 37 | OQ-SL-005 | CLAR-077 | Storage | Medium | Should the storage layer support a versioning strategy that retains every interm... |
| 38 | OQ-SL-006 | CLAR-078 | Storage | Medium | Should the storage layer support a remote storage target (e.g. S3) in the MVP, o... |
| 39 | OQ-SL-007 | CLAR-079 | Storage | Medium | Should the storage layer support a column-store target (e.g. DuckDB) in the MVP,... |
| 40 | OQ-TL-009 | CLAR-083 | Trade | Medium | Should the trade layer support a streaming output for very large responses? |
| 41 | OQ-TL-010 | CLAR-084 | Trade | Medium | Should the trade layer support a concurrent batch execution under a documented c... |
| 42 | OQ-TS-004 | CLAR-086 | Testing | Medium | Should the test suite support property-based testing for the normalisation layer... |
| 43 | OQ-TS-005 | CLAR-087 | Testing | Medium | Should the test suite support mutation testing for the validation layer? |
| 44 | OQ-TS-006 | CLAR-088 | Testing | Medium | Should the test suite support a chaos test that simulates upstream failures at r... |
| 45 | OQ-API-006 | CLAR-090 | API Behaviour | Low | Is the bulk download endpoint (E24) reachable under the documented URL pattern, ... |
| 46 | OQ-API-007 | CLAR-091 | API Behaviour | Low | Is the `partner2Code` parameter honoured on the public preview, or only on the `... |
| 47 | OQ-API-008 | CLAR-092 | API Behaviour | Low | What is the rate of HS revision? The reference catalogue includes 7 editions. Is... |
| 48 | OQ-CS-010 | CLAR-093 | Coding Standards | Low | What is the exact pre-commit hook configuration? |
| 49 | OQ-DM-006 | CLAR-095 | Data Model | Low | Should the canonical model include a `DataType` field on E12 TradeRecord to refl... |
| 50 | OQ-DM-007 | CLAR-096 | Data Model | Low | Should the canonical model include a `ValidityWindow` entity to model the validi... |
| 51 | OQ-DM-008 | CLAR-097 | Data Model | Low | Should the canonical model expose the `provenance` block as a first-class entity... |
| 52 | OQ-ETL-008 | CLAR-098 | ETL | Low | Should the ETL layer support a watermark strategy that records the last successf... |
| 53 | OQ-ETL-009 | CLAR-099 | ETL | Low | Should the ETL layer support a `diff=True` flag that, when set, consumes the ups... |
| 54 | OQ-ETL-010 | CLAR-100 | ETL | Low | Should the ETL layer expose a `get_provenance(record_id)` method that returns th... |
| 55 | OQ-IM-008 | CLAR-101 | Implementation | Low | What is the exact celebration protocol for each milestone? |
| 56 | OQ-IM-009 | CLAR-102 | Implementation | Low | What is the exact communication channel for the project? |
| 57 | OQ-IM-010 | CLAR-103 | Implementation | Low | What is the exact governance model for the project? |
| 58 | OQ-IS-008 | CLAR-104 | Infrastructure | Low | Should the SDK support a custom cache key function through a documented extensio... |
| 59 | OQ-IS-009 | CLAR-105 | Infrastructure | Low | Should the SDK support a custom progress callback type? |
| 60 | OQ-IS-010 | CLAR-106 | Infrastructure | Low | Should the SDK expose a `__version__` constant? |
| 61 | OQ-ML-007 | CLAR-107 | Metadata | Low | Should the metadata layer expose a `get_recent_releases()` method that returns t... |
| 62 | OQ-ML-008 | CLAR-108 | Metadata | Low | Should the metadata layer support a custom cache backend (Redis, SQLite) through... |
| 63 | OQ-ML-009 | CLAR-109 | Metadata | Low | Should the metadata layer expose a `validate_metadata()` method that validates t... |
| 64 | OQ-ML-010 | CLAR-110 | Metadata | Low | Should the metadata layer expose a `get_classification_tree(classification, edit... |
| 65 | OQ-PS-009 | CLAR-111 | Packaging | Low | Should the package support a `pip install un-comtrade-sdk[all]` mechanism that i... |
| 66 | OQ-PS-010 | CLAR-112 | Packaging | Low | Should the package support a Docker image as a distribution target? |
| 67 | OQ-SDK-003 | CLAR-113 | SDK | Low | Should the SDK expose a `get_trade_envelope(reporter_code, flow_code, period)` m... |
| 68 | OQ-SDK-004 | CLAR-114 | SDK | Low | Should the SDK expose a `get_metadata_diff(table_name, since)` method that retur... |
| 69 | OQ-SDK-005 | CLAR-115 | SDK | Low | Should the SDK expose a `validate_query(...)` method that validates a query with... |
| 70 | OQ-SDK-006 | CLAR-116 | SDK | Low | Should the SDK expose a `get_recent_releases()` method that returns the recent d... |
| 71 | OQ-SDK-007 | CLAR-117 | SDK | Low | Should the SDK expose constants for the special `flow_code` values (`un_comtrade... |
| 72 | OQ-SDK-008 | CLAR-118 | SDK | Low | Should the SDK expose constants for the classification codes (`un_comtrade.CLASS... |
| 73 | OQ-SDK-009 | CLAR-119 | SDK | Low | Should the SDK expose an `__all__` list that documents the public surface? |
| 74 | OQ-SDK-010 | CLAR-120 | SDK | Low | Should the SDK expose a `__version__` constant? |
| 75 | OQ-SL-008 | CLAR-121 | Storage | Low | Should the storage layer support a custom metadata field on every persisted reco... |
| 76 | OQ-SL-009 | CLAR-122 | Storage | Low | Should the storage layer support a `compact()` operation that merges multiple ve... |
| 77 | OQ-SL-010 | CLAR-123 | Storage | Low | Should the storage layer support a `vacuum()` operation that deletes archived da... |
| 78 | OQ-TL-011 | CLAR-124 | Trade | Low | Should the trade layer expose a `cancel()` method to cancel an in-flight downloa... |
| 79 | OQ-TL-012 | CLAR-125 | Trade | Low | Should the trade layer expose a `resume(download_handle)` method to resume an in... |
| 80 | OQ-TL-013 | CLAR-126 | Trade | Low | Should the trade layer expose a `validate_query(...)` method to validate a query... |
| 81 | OQ-TL-014 | CLAR-127 | Trade | Low | Should the trade layer expose a `get_trade_diff(reporter_code, since)` method to... |
| 82 | OQ-TL-015 | CLAR-128 | Trade | Low | Should the trade layer support a `cached=True` flag on every method to explicitl... |
| 83 | OQ-TS-008 | CLAR-129 | Testing | Low | Should the test suite support a snapshot test that compares the normalised recor... |
| 84 | OQ-TS-009 | CLAR-130 | Testing | Low | Should the test suite support a fuzz test that issues requests with random param... |
| 85 | OQ-TS-010 | CLAR-131 | Testing | Low | Should the test suite support a conformance test that verifies the SDK against t... |

**Total non-blocking items:** 85.

---

## 12. Resolution Roadmap

The recommended order for resolving the blocking clarifications, grouped by category and intra-category priority.

### Priority 1 — Tooling and CI/CD (must precede `pyproject.toml` creation)

| CLAR | Source OQ | Question (truncated) |
| ---- | --------- | -------------------- |
| CLAR-003 | OQ-CS-001 | What is the exact linting framework to be used? |
| CLAR-004 | OQ-CS-002 | What is the exact formatting framework to be used? |
| CLAR-005 | OQ-CS-003 | What is the exact type-checking framework to be used? |
| CLAR-006 | OQ-CS-004 | What is the exact documentation framework to be used? |
| CLAR-007 | OQ-CS-005 | What is the exact testing framework to be used? |

### Priority 2 — API Behaviour (must precede retry budget and cache lifetime defaults)

| CLAR | Source OQ | Question (truncated) |
| ---- | --------- | -------------------- |
| CLAR-001 | OQ-API-001 | What is the exact per-minute request cap on the public preview surface? |
| CLAR-002 | OQ-API-002 | What is the exact per-key daily record cap? |
| CLAR-041 | OQ-API-003 | Is the data availability endpoint (E25) reachable under any URL pattern? |
| CLAR-042 | OQ-API-004 | What is the documentation of the `legacyEstimationFlag` value semantics? The obs... |
| CLAR-043 | OQ-API-005 | What is the semantics of the `aggrLevel` field? The observed values are integers... |

### Priority 3 — Data Model mappings (must precede normalisation layer)

| CLAR | Source OQ | Question (truncated) |
| ---- | --------- | -------------------- |
| CLAR-008 | OQ-DM-001 | What is the canonical mapping of the `legacyEstimationFlag` integer values to th... |
| CLAR-009 | OQ-DM-002 | What is the canonical mapping of the `aggrLevel` integer values to a documented ... |
| CLAR-048 | OQ-DM-003 | Is the `partner2Code` parameter honoured on the public preview, or only on the `... |
| CLAR-049 | OQ-DM-004 | What is the response shape of E17 PublicationNote and E18 DataAvailabilityRecord... |

### Priority 4 — Metadata and Trade response shapes (must precede layer method exposure)

| CLAR | Source OQ | Question (truncated) |
| ---- | --------- | -------------------- |
| CLAR-017 | OQ-ML-001 | What is the exact cache lifetime for each resource? |
| CLAR-018 | OQ-ML-002 | What is the exact URL of the data availability endpoint (D1)? |
| CLAR-024 | OQ-TL-001 | What is the exact publication cadence of the trade data? |
| CLAR-025 | OQ-TL-002 | What is the exact URL of the data availability endpoint (D1)? |
| CLAR-026 | OQ-TL-003 | What is the exact URL of the bulk download endpoint (D3)? |
| CLAR-027 | OQ-TL-004 | What is the exact URL of the async submit, check, and download endpoints (D2)? |
| CLAR-028 | OQ-TL-005 | What is the response shape of the publication notes endpoint (U2)? |

### Priority 5 — Infrastructure defaults (must precede first code execution)

| CLAR | Source OQ | Question (truncated) |
| ---- | --------- | -------------------- |
| CLAR-015 | OQ-IS-001 | What is the exact per- minute request cap on the public preview surface? |
| CLAR-016 | OQ-IS-002 | What is the exact per-key daily record cap? |
| CLAR-059 | OQ-IS-003 | Should the SDK support a distributed cache backend (Redis, Memcached) for cross-... |
| CLAR-060 | OQ-IS-004 | Should the SDK support a custom logger (e.g. structlog, loguru) through a docume... |
| CLAR-061 | OQ-IS-005 | Should the SDK support OpenTelemetry tracing through a documented extension poin... |
| CLAR-062 | OQ-IS-006 | Should the SDK support a custom retry policy through a documented extension poin... |
| CLAR-063 | OQ-IS-007 | Should the SDK expose the request identifier as a consumer-supplied header, so t... |

### Priority 6 — ETL and Storage policy (must precede pipeline persistence)

| CLAR | Source OQ | Question (truncated) |
| ---- | --------- | -------------------- |
| CLAR-010 | OQ-ETL-001 | Should the ETL layer expose a streaming output for very large datasets? |
| CLAR-011 | OQ-ETL-002 | Should the ETL layer support a parallel validation and transformation of records... |
| CLAR-022 | OQ-SL-001 | What is the exact retention period for each data category? |
| CLAR-023 | OQ-SL-002 | What is the exact partition strategy for trade data? |

### Priority 7 — Implementation governance (must precede phase gate transition)

| CLAR | Source OQ | Question (truncated) |
| ---- | --------- | -------------------- |
| CLAR-012 | OQ-IM-001 | When is Phase 0 complete? |
| CLAR-013 | OQ-IM-002 | When is Phase 9 complete? |
| CLAR-014 | OQ-IM-003 | What is the exact cadence of Phase 10 (Maintenance)? |
| CLAR-055 | OQ-IM-004 | What is the exact success criteria for each milestone? |
| CLAR-056 | OQ-IM-005 | What is the exact parallelisable work for each phase? |
| CLAR-057 | OQ-IM-006 | What is the exact impact assessment template for a roadmap change? |
| CLAR-058 | OQ-IM-007 | What is the exact escalation policy for a phase gate failure? |

### Priority 8 — Testing, Packaging, and remaining categories (post-MVP)

Items in this priority bucket can be deferred until after the MVP is shipped. They are recorded here for traceability.

---

## 13. Top 20 Highest-Priority Clarifications

The 20 most critical items, ranked. These MUST be resolved before Phase 1 (SDK Foundation) begins.

| Rank | CLAR | Source OQ | Category | Question (truncated) |
| ---- | ---- | --------- | -------- | -------------------- |
| 1 | CLAR-001 | OQ-API-001 | API Behaviour | What is the exact per-minute request cap on the public preview surface? |
| 2 | CLAR-002 | OQ-API-002 | API Behaviour | What is the exact per-key daily record cap? |
| 3 | CLAR-003 | OQ-CS-001 | Coding Standards | What is the exact linting framework to be used? |
| 4 | CLAR-004 | OQ-CS-002 | Coding Standards | What is the exact formatting framework to be used? |
| 5 | CLAR-005 | OQ-CS-003 | Coding Standards | What is the exact type-checking framework to be used? |
| 6 | CLAR-006 | OQ-CS-004 | Coding Standards | What is the exact documentation framework to be used? |
| 7 | CLAR-007 | OQ-CS-005 | Coding Standards | What is the exact testing framework to be used? |
| 8 | CLAR-008 | OQ-DM-001 | Data Model | What is the canonical mapping of the `legacyEstimationFlag` integer values to th... |
| 9 | CLAR-009 | OQ-DM-002 | Data Model | What is the canonical mapping of the `aggrLevel` integer values to a documented ... |
| 10 | CLAR-010 | OQ-ETL-001 | ETL | Should the ETL layer expose a streaming output for very large datasets? |
| 11 | CLAR-011 | OQ-ETL-002 | ETL | Should the ETL layer support a parallel validation and transformation of records... |
| 12 | CLAR-012 | OQ-IM-001 | Implementation | When is Phase 0 complete? |
| 13 | CLAR-013 | OQ-IM-002 | Implementation | When is Phase 9 complete? |
| 14 | CLAR-014 | OQ-IM-003 | Implementation | What is the exact cadence of Phase 10 (Maintenance)? |
| 15 | CLAR-015 | OQ-IS-001 | Infrastructure | What is the exact per- minute request cap on the public preview surface? |
| 16 | CLAR-016 | OQ-IS-002 | Infrastructure | What is the exact per-key daily record cap? |
| 17 | CLAR-017 | OQ-ML-001 | Metadata | What is the exact cache lifetime for each resource? |
| 18 | CLAR-018 | OQ-ML-002 | Metadata | What is the exact URL of the data availability endpoint (D1)? |
| 19 | CLAR-019 | OQ-PS-001 | Packaging | What is the exact continuous integration pipeline to be used? |
| 20 | CLAR-020 | OQ-PS-002 | Packaging | What is the exact package index to be used? |

---

## 14. Summary

- **Documents reviewed:** 20.
- **Unique `OQ-*` IDs extracted:** 131.
- **Cross-referenced mentions:** 142.
- **Duplicate questions merged:** 8.
- **Blocking items:** 30.
- **Partially-blocking items:** 14.
- **Non-blocking items:** 85.
- **Already resolved:** 2.
- **Recommended new ADRs:** 11 (ADR-0017 through ADR-0027).
- **Documentation readiness score:** ~88%.
- **Implementation readiness:** **Not Ready** — 30 High-priority clarifications must be resolved or explicitly deferred before Phase 1.

---

---

## 15. Resolution Summary (TASK-022 — 2026-06-27)

The architectural freeze of 2026-06-27 produced 120 binding
decisions, codified as ADRs (ADR-0017 through ADR-0034). This
register is updated to reflect the resolutions.

### 15.1 Resolution Statistics

- **Total clarifications:** 131.
- **Resolved by architectural decision:** 119.
- **Open (External Verification Required):** 12.
- **Documentation revised:** 8 spec documents plus DECISIONS,
  CHANGELOG, TASK_LOG, CONTEXT, and this register.
- **ADRs created:** 18 (ADR-0017 through ADR-0034).
- **ADRs revised:** 1 (ADR-0008: retry attempts 5 → 3).

### 15.2 External Verification Items

The following 10 items remain open because they require
external verification of UN Comtrade API behaviour that cannot
be confirmed from existing documentation:

| Item | Question | Source OQ IDs |
| ---- | -------- | ------------- |
| EXT-003 | URL of the data availability endpoint (D1) | OQ-API-003, OQ-ML-002, OQ-TL-002 |
| EXT-004 | URL of the async submit/check/download endpoints (D2) | OQ-TL-004 |
| EXT-005 | URL of the bulk download endpoints (D3) | OQ-API-006, OQ-TL-003 |
| EXT-006 | Response shape of the publication notes endpoint (U2) | OQ-ML-003, OQ-TL-005 |
| EXT-007 | Response shape of the trade balance endpoint (T3) | OQ-TL-007 |
| EXT-008 | Response shape of the bilateral endpoint (T4) | OQ-TL-008 |
| EXT-009 | Response shape of the standard unit value endpoint (U1) | OQ-TL-006 |
| EXT-010 | Mapping of `legacyEstimationFlag` integer values | OQ-API-004, OQ-DM-001 |
| EXT-011 | Mapping of `aggrLevel` integer values | OQ-API-005, OQ-DM-002 |
| EXT-012 | Whether `partner2Code` is honoured on the public preview | OQ-API-007, OQ-DM-003 |

**Resolved in 2026-06-27 limit probes** (`API_LIMITS_REPORT.md`):

| Item | Resolution | Reference |
| ---- | ---------- | --------- |
| EXT-001 | Token-bucket, ≈1 req/s refill, `Retry-After: 1` | ADR-0035, `API_LIMITS_REPORT.md` §3 |
| EXT-002 | 50,000,000 records/day (free tier); per-call caps 500 / 250,000 | ADR-0036, `API_LIMITS_REPORT.md` §4 |

These items SHALL be verified during Phase 1 implementation
through sustained observation or, where possible, by reading
the `comtradeapicall` source.

### 15.3 ADR Cross-Reference

| ADR | Decisions | Resolves |
| --- | --------- | -------- |
| ADR-0017 | Q1, Q2 | OQ-CS-001, OQ-CS-002, OQ-CS-006, OQ-PS-006, OQ-PS-007 |
| ADR-0018 | Q3 | (architectural change — `httpx` replaces `requests`) |
| ADR-0019 | Q4 | OQ-A-005, OQ-SDK-002 |
| ADR-0020 | Q5 | (architectural change — stdlib JSON) |
| ADR-0021 | Q6-Q10 | OQ-A-009, OQ-A-010, OQ-DM-005, OQ-DM-006, OQ-SDK-007, OQ-SDK-008, OQ-SDK-009 |
| ADR-0022 | Q13, Q14 | OQ-IS-006 |
| ADR-0023 | Q16-Q20 | (timeout policy) |
| ADR-0024 | Q21-Q25 | OQ-A-008, OQ-IS-003, OQ-IS-008, OQ-ML-006, OQ-TL-015 |
| ADR-0025 | Q26-Q30 | OQ-A-004, OQ-IS-004 |
| ADR-0026 | Q31-Q40 | OQ-API-008, OQ-DM-004, OQ-DM-007, OQ-DM-008, OQ-ML-001, OQ-ML-004, OQ-ML-005, OQ-ML-007, OQ-ML-008, OQ-ML-009, OQ-ML-010, OQ-SDK-003, OQ-SDK-004, OQ-SDK-005, OQ-SDK-006 |
| ADR-0027 | Q41-Q50 | OQ-A-006, OQ-A-007, OQ-ETL-001..OQ-ETL-010, OQ-TL-001, OQ-TL-009..OQ-TL-014 |
| ADR-0028 | Q51-Q60 | OQ-DM-007, OQ-DM-008, OQ-ETL-010 |
| ADR-0029 | Q61-Q70 | OQ-ETL-007, OQ-SL-001..OQ-SL-010 |
| ADR-0030 | Q71-Q80 | OQ-CS-005, OQ-TS-004..OQ-TS-010 |
| ADR-0031 | Q81-Q90 | OQ-CS-008, OQ-CS-009, OQ-CS-010, OQ-PS-009, OQ-PS-010 |
| ADR-0032 | Q91-Q100 | OQ-CS-004, OQ-IM-008, OQ-IM-009, OQ-PS-008 |
| ADR-0033 | Q101-Q110 | OQ-CS-007, OQ-PS-001..OQ-PS-005, OQ-TS-001, OQ-TS-002, OQ-TS-003 |
| ADR-0034 | Q111-Q120 | OQ-IM-010, OQ-IS-005, OQ-IS-007, OQ-IS-009, OQ-IS-010, OQ-SDK-010 |
| ADR-0008 (revised) | (retry policy) | (5 → 3 attempts) |

### 15.4 Updated Documents

The following 14 documents were modified in TASK-022:

1. `docs/000_PROJECT_CHARTER.md` (Python version matrix; httpx
   dependency).
2. `docs/003_ARCHITECTURE.md` (`requests` → `httpx`).
3. `docs/006_DATA_MODEL.md` (Decimal for trade values; ISO-8601;
   null preservation; immutable records).
4. `docs/008_METADATA_LAYER_SPEC.md` (auto-init; atomic; case-
   insensitive search).
5. `docs/009_TRADE_LAYER_SPEC.md` (unified model; no trade cache;
   empty collections).
6. `docs/010_INFRASTRUCTURE_SPEC.md` (retry 3 attempts; timeout
   policy; cache policy; logging policy).
7. `docs/012_STORAGE_SPECIFICATION.md` (DuckDB MVP; Parquet
   default; logical partitioning; schema validation).
8. `docs/013_TESTING_STANDARD.md` (live-API integration suite;
   public-API unit tests; no 100% coverage).
9. `docs/014_PACKAGING_SPECIFICATION.md` (`requests` → `httpx`).
10. `docs/DECISIONS.md` (18 new ADRs; ADR-0008 revised).
11. `docs/CHANGELOG.md` (CHG-0011, CHG-0012, CHG-0013).
12. `docs/TASK_LOG.md` (TASK-020, TASK-021, TASK-022).
13. `docs/CONTEXT.md` (Phase 0 closure; readiness).
14. `docs/PROJECT_CLARIFICATION_REGISTER.md` (this section).

---

*End of document.*
