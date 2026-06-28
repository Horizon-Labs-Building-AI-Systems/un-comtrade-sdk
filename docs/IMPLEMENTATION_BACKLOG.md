# Implementation Backlog

| Field | Value |
| ----- | ----- |
| Document ID | 022 |
| Title | Implementation Backlog |
| Version | 1.0 |
| Status | LIVE |
| Created | 2026-06-27T12:00:00Z |
| Last Updated | 2026-06-27T12:00:00Z |
| Author | Codex |
| Project | UN Comtrade Python SDK |
| Dependencies | IMPLEMENTATION_BASELINE_v1.md, IMPLEMENTATION_ROADMAP.md, DECISIONS.md |
| Supersedes | None |

---

## Phase 1 — SDK Foundation

**Tasks:** 20

### T-001: Create `pyproject.toml` with `httpx` requirement and Python 3.11+ support

- **Task ID:** T-001
- **Title:** Create `pyproject.toml` with `httpx` requirement and Python 3.11+ support
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** —
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0017, ADR-0018, ADR-0031
- **Expected Output:** `pyproject.toml` declaring `httpx` dependency, `requires-python = ">=3.11"`, project metadata.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-002: Create `un_comtrade/__init__.py` package skeleton

- **Task ID:** T-002
- **Title:** Create `un_comtrade/__init__.py` package skeleton
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** T-001
- **Primary Specification:** 003_ARCHITECTURE.md
- **Primary ADR:** ADR-0001
- **Expected Output:** `un_comtrade/__init__.py` exposing the public API surface.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-003: Create `un_comtrade/__version__.py` with `__version__` string

- **Task ID:** T-003
- **Title:** Create `un_comtrade/__version__.py` with `__version__` string
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** T-001
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0034
- **Expected Output:** `__version__` constant readable via `un_comtrade.__version__`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-004: Define the 13-exception hierarchy under `ComtradeError`

- **Task ID:** T-004
- **Title:** Define the 13-exception hierarchy under `ComtradeError`
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** T-002
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0012
- **Expected Output:** `un_comtrade/exceptions.py` with 13 typed exception classes.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-005: Define the configuration dataclass

- **Task ID:** T-005
- **Title:** Define the configuration dataclass
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** T-002
- **Primary Specification:** 010_INFRASTRUCTURE_SPEC.md
- **Primary ADR:** ADR-0023
- **Expected Output:** `un_comtrade/config.py` with typed configuration slots.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-006: Implement configuration loading from environment variables

- **Task ID:** T-006
- **Title:** Implement configuration loading from environment variables
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** T-005
- **Primary Specification:** 010_INFRASTRUCTURE_SPEC.md
- **Primary ADR:** ADR-0034
- **Expected Output:** Configuration values populated from `UN_COMTRADE_API_KEY`, `UN_COMTRADE_CACHE_DIR`, etc.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-007: Implement `httpx` synchronous HTTP client factory

- **Task ID:** T-007
- **Title:** Implement `httpx` synchronous HTTP client factory
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** T-005
- **Primary Specification:** 003_ARCHITECTURE.md
- **Primary ADR:** ADR-0018
- **Expected Output:** `un_comtrade/runtime/transport.py` creating a configured `httpx.Client`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-008: Implement the synchronous request method on the transport

- **Task ID:** T-008
- **Title:** Implement the synchronous request method on the transport
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** T-007
- **Primary Specification:** 010_INFRASTRUCTURE_SPEC.md
- **Primary ADR:** ADR-0018
- **Expected Output:** `transport.request(method, url, **kwargs)` returning a `Response`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-009: Implement subscription-key authentication injection

- **Task ID:** T-009
- **Title:** Implement subscription-key authentication injection
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** T-008
- **Primary Specification:** 010_INFRASTRUCTURE_SPEC.md
- **Primary ADR:** ADR-0034
- **Expected Output:** Authentication layer that injects `subscription-key` per call.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-010: Implement retry middleware (3 attempts, exponential backoff)

- **Task ID:** T-010
- **Title:** Implement retry middleware (3 attempts, exponential backoff)
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** T-008
- **Primary Specification:** 010_INFRASTRUCTURE_SPEC.md
- **Primary ADR:** ADR-0008, ADR-0022
- **Expected Output:** `un_comtrade/runtime/retry.py` honouring `Retry-After` and ADR-0008 backoff.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-011: Implement the three-category timeout policy

- **Task ID:** T-011
- **Title:** Implement the three-category timeout policy
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** T-007
- **Primary Specification:** 010_INFRASTRUCTURE_SPEC.md
- **Primary ADR:** ADR-0023
- **Expected Output:** Timeout module with 30s request, 15s metadata, 300s download defaults.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-012: Implement the stdlib logging seam

- **Task ID:** T-012
- **Title:** Implement the stdlib logging seam
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** T-002
- **Primary Specification:** 010_INFRASTRUCTURE_SPEC.md
- **Primary ADR:** ADR-0025
- **Expected Output:** `un_comtrade/runtime/logging.py` with WARNING default and API-key redaction.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-013: Implement the metadata cache skeleton

- **Task ID:** T-013
- **Title:** Implement the metadata cache skeleton
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** T-012
- **Primary Specification:** 008_METADATA_LAYER_SPEC.md
- **Primary ADR:** ADR-0024, ADR-0026
- **Expected Output:** `un_comtrade/runtime/cache.py` with persistent JSON cache and 30d default.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-014: Create the `ComtradeClient` class skeleton

- **Task ID:** T-014
- **Title:** Create the `ComtradeClient` class skeleton
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** T-002
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0019
- **Expected Output:** `un_comtrade/client.py` with constructor accepting configuration.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-015: Wire `ComtradeClient` constructor and shutdown lifecycle

- **Task ID:** T-015
- **Title:** Wire `ComtradeClient` constructor and shutdown lifecycle
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** T-014
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0019
- **Expected Output:** `ComtradeClient.__init__` and `__enter__` / `__exit__` complete.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-016: Define `un_comtrade.types` common type aliases

- **Task ID:** T-016
- **Title:** Define `un_comtrade.types` common type aliases
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** T-002
- **Primary Specification:** 006_DATA_MODEL.md
- **Primary ADR:** ADR-0028
- **Expected Output:** Common type aliases used across the SDK.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-017: Define `un_comtrade.units` monetary and quantity unit enums

- **Task ID:** T-017
- **Title:** Define `un_comtrade.units` monetary and quantity unit enums
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** T-016
- **Primary Specification:** 006_DATA_MODEL.md
- **Primary ADR:** ADR-0028
- **Expected Output:** Monetary and quantity unit enums exposed by the SDK.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-018: Define `un_comtrade.constants` for partner-code sentinels

- **Task ID:** T-018
- **Title:** Define `un_comtrade.constants` for partner-code sentinels
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** T-016
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0021
- **Expected Output:** Constants like `PARTNER_WORLD = 0`, `FLOW_EXPORT = "X"` etc.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-019: Implement first smoke test that instantiates `ComtradeClient`

- **Task ID:** T-019
- **Title:** Implement first smoke test that instantiates `ComtradeClient`
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** T-015
- **Primary Specification:** 016_IMPLEMENTATION_ROADMAP.md
- **Primary ADR:** ADR-0016
- **Expected Output:** `tests/test_smoke.py` instantiating `ComtradeClient` and exiting cleanly.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-020: Implement the SDK CLI module skeleton `un_comtrade.cli`

- **Task ID:** T-020
- **Title:** Implement the SDK CLI module skeleton `un_comtrade.cli`
- **Phase:** Phase 1 — SDK Foundation
- **Depends On:** T-002
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0031
- **Expected Output:** `un_comtrade/cli/__init__.py` exposing a `main()` entry point.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

---

## Phase 2 — Metadata Layer

**Tasks:** 24

### T-021: Define canonical entity E01 Country

- **Task ID:** T-021
- **Title:** Define canonical entity E01 Country
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-016
- **Primary Specification:** 006_DATA_MODEL.md
- **Primary ADR:** ADR-0028
- **Expected Output:** Frozen dataclass for `Country` with code, iso3, name, validity window.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-022: Define canonical entity E02 Classification and E03 Edition

- **Task ID:** T-022
- **Title:** Define canonical entity E02 Classification and E03 Edition
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-021
- **Primary Specification:** 006_DATA_MODEL.md
- **Primary ADR:** ADR-0028
- **Expected Output:** Frozen dataclasses for `Classification` and `ClassificationEdition`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-023: Define canonical entity E04 CommodityCode

- **Task ID:** T-023
- **Title:** Define canonical entity E04 CommodityCode
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-021
- **Primary Specification:** 006_DATA_MODEL.md
- **Primary ADR:** ADR-0028
- **Expected Output:** Frozen dataclass for `CommodityCode` with code, description, aggr_level, is_leaf.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-024: Define canonical entities E05 TradeFlow and E06 TransportMode

- **Task ID:** T-024
- **Title:** Define canonical entities E05 TradeFlow and E06 TransportMode
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-021
- **Primary Specification:** 006_DATA_MODEL.md
- **Primary ADR:** ADR-0028
- **Expected Output:** Frozen dataclasses with canonical enums.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-025: Define canonical entities E07 CustomsProcedure, E08 QuantityUnit

- **Task ID:** T-025
- **Title:** Define canonical entities E07 CustomsProcedure, E08 QuantityUnit
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-021
- **Primary Specification:** 006_DATA_MODEL.md
- **Primary ADR:** ADR-0028
- **Expected Output:** Frozen dataclasses for customs procedures and quantity units.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-026: Define canonical entities E09 Frequency and E10 Period

- **Task ID:** T-026
- **Title:** Define canonical entities E09 Frequency and E10 Period
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-021
- **Primary Specification:** 006_DATA_MODEL.md
- **Primary ADR:** ADR-0028
- **Expected Output:** Frozen dataclasses with frequency enum and ISO-8601 period strings.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-027: Define canonical entity E11 ModeOfSupply

- **Task ID:** T-027
- **Title:** Define canonical entity E11 ModeOfSupply
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-021
- **Primary Specification:** 006_DATA_MODEL.md
- **Primary ADR:** ADR-0028
- **Expected Output:** Frozen dataclass for mode of supply codes.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-028: Implement the metadata API client

- **Task ID:** T-028
- **Title:** Implement the metadata API client
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-008
- **Primary Specification:** 008_METADATA_LAYER_SPEC.md
- **Primary ADR:** ADR-0026
- **Expected Output:** `un_comtrade/metadata/api.py` calling `/files/v1/app/reference/...`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-029: Implement the metadata cache loader and saver

- **Task ID:** T-029
- **Title:** Implement the metadata cache loader and saver
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-013
- **Primary Specification:** 008_METADATA_LAYER_SPEC.md
- **Primary ADR:** ADR-0024, ADR-0026
- **Expected Output:** Atomic load and save of cached reference files.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-030: Implement the metadata auto-init on first use

- **Task ID:** T-030
- **Title:** Implement the metadata auto-init on first use
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-029
- **Primary Specification:** 008_METADATA_LAYER_SPEC.md
- **Primary ADR:** ADR-0026
- **Expected Output:** First call to a metadata method triggers lazy fetch.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-031: Implement `M01 get_countries`

- **Task ID:** T-031
- **Title:** Implement `M01 get_countries`
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-030
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0026
- **Expected Output:** Returns list of canonical `Country` entities.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-032: Implement `M02 get_country`

- **Task ID:** T-032
- **Title:** Implement `M02 get_country`
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-031
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0026
- **Expected Output:** Single `Country` lookup by reporter code.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-033: Implement `M03 get_partners` and `M04 get_partner`

- **Task ID:** T-033
- **Title:** Implement `M03 get_partners` and `M04 get_partner`
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-031
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0026
- **Expected Output:** Partner country and partner-by-code methods.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-034: Implement `M05 get_classifications` and `M06 get_classification`

- **Task ID:** T-034
- **Title:** Implement `M05 get_classifications` and `M06 get_classification`
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-031
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0026
- **Expected Output:** Classification list and single-classification methods.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-035: Implement `M07 get_classification_editions`

- **Task ID:** T-035
- **Title:** Implement `M07 get_classification_editions`
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-034
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0026
- **Expected Output:** Returns list of `ClassificationEdition`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-036: Implement `M08 get_hs_codes` and `M09 get_hs_code`

- **Task ID:** T-036
- **Title:** Implement `M08 get_hs_codes` and `M09 get_hs_code`
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-034
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0026
- **Expected Output:** HS codes list and HS-code-by-code methods.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-037: Implement `M10 search_hs` (case-insensitive prefix search)

- **Task ID:** T-037
- **Title:** Implement `M10 search_hs` (case-insensitive prefix search)
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-036
- **Primary Specification:** 008_METADATA_LAYER_SPEC.md
- **Primary ADR:** ADR-0026
- **Expected Output:** Search HS codes by case-insensitive prefix.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-038: Implement `M11 get_trade_flows`

- **Task ID:** T-038
- **Title:** Implement `M11 get_trade_flows`
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-031
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0026
- **Expected Output:** Returns list of `TradeFlow`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-039: Implement `M12 get_transport_modes` and `M13 get_customs_procedures`

- **Task ID:** T-039
- **Title:** Implement `M12 get_transport_modes` and `M13 get_customs_procedures`
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-031
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0026
- **Expected Output:** Transport-mode and customs-procedure lookups.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-040: Implement `M14 get_quantity_units`, `M15 get_modes_of_supply`

- **Task ID:** T-040
- **Title:** Implement `M14 get_quantity_units`, `M15 get_modes_of_supply`
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-031
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0026
- **Expected Output:** Quantity units and mode-of-supply lookups.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-041: Implement `M16 get_frequencies`

- **Task ID:** T-041
- **Title:** Implement `M16 get_frequencies`
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-031
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0026
- **Expected Output:** Returns list of `Frequency`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-042: Implement `M17 get_data_items`

- **Task ID:** T-042
- **Title:** Implement `M17 get_data_items`
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-031
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0026
- **Expected Output:** Returns the upstream data-items catalogue.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-043: Implement `M18 get_metadata` (umbrella metadata call)

- **Task ID:** T-043
- **Title:** Implement `M18 get_metadata` (umbrella metadata call)
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-031
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0026
- **Expected Output:** Bulk metadata fetcher returning a `MetadataCollection`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-044: Implement `refresh_metadata()` method on the metadata layer

- **Task ID:** T-044
- **Title:** Implement `refresh_metadata()` method on the metadata layer
- **Phase:** Phase 2 — Metadata Layer
- **Depends On:** T-029
- **Primary Specification:** 008_METADATA_LAYER_SPEC.md
- **Primary ADR:** ADR-0026
- **Expected Output:** Force a cache refresh and re-download catalogues.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

---

## Phase 3 — Trade Layer

**Tasks:** 20

### T-045: Define canonical entity E12 TradeRecord (38 fields + Decimal)

- **Task ID:** T-045
- **Title:** Define canonical entity E12 TradeRecord (38 fields + Decimal)
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-016
- **Primary Specification:** 006_DATA_MODEL.md
- **Primary ADR:** ADR-0028
- **Expected Output:** Frozen dataclass with all canonical fields per `SCHEMA_VERIFICATION.md`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-046: Define canonical entity E13 TariffLineRecord

- **Task ID:** T-046
- **Title:** Define canonical entity E13 TariffLineRecord
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-045
- **Primary Specification:** 006_DATA_MODEL.md
- **Primary ADR:** ADR-0028
- **Expected Output:** Frozen dataclass for tariff-line records.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-047: Implement the trade API client (authenticated + preview)

- **Task ID:** T-047
- **Title:** Implement the trade API client (authenticated + preview)
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-008
- **Primary Specification:** 009_TRADE_LAYER_SPEC.md
- **Primary ADR:** ADR-0027
- **Expected Output:** `un_comtrade/trade/api.py` calling `/data/v1/get/...` and `/public/v1/preview/...`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-048: Implement `T01 get_exports`

- **Task ID:** T-048
- **Title:** Implement `T01 get_exports`
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-047
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Returns iterable of `TradeRecord` for export flow.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-049: Implement `T02 get_imports`

- **Task ID:** T-049
- **Title:** Implement `T02 get_imports`
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-047
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Returns iterable of `TradeRecord` for import flow.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-050: Implement `T03 get_trade` (auto-detect flow)

- **Task ID:** T-050
- **Title:** Implement `T03 get_trade` (auto-detect flow)
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-048
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Returns iterable of `TradeRecord` for the requested flow code.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-051: Implement `T04 get_trade_by_hs`

- **Task ID:** T-051
- **Title:** Implement `T04 get_trade_by_hs`
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-048
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Returns trade filtered to a specific HS code.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-052: Implement `T05 get_world_trade`

- **Task ID:** T-052
- **Title:** Implement `T05 get_world_trade`
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-048
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Returns trade aggregated to the World partner.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-053: Implement `T06 get_trade_balance`

- **Task ID:** T-053
- **Title:** Implement `T06 get_trade_balance`
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-047
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Returns a `TradeBalanceRecord`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-054: Implement `T07 get_bilateral`

- **Task ID:** T-054
- **Title:** Implement `T07 get_bilateral`
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-047
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Returns a `BilateralRecord`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-055: Implement `T08 get_trade_matrix`

- **Task ID:** T-055
- **Title:** Implement `T08 get_trade_matrix`
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-047
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Returns a `TradeMatrixRecord`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-056: Implement `T09 get_monthly_exports`

- **Task ID:** T-056
- **Title:** Implement `T09 get_monthly_exports`
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-048
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Monthly export trade iterable.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-057: Implement `T10 get_monthly_imports`

- **Task ID:** T-057
- **Title:** Implement `T10 get_monthly_imports`
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-048
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Monthly import trade iterable.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-058: Implement `T11 get_monthly_trade`

- **Task ID:** T-058
- **Title:** Implement `T11 get_monthly_trade`
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-050
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Monthly trade with auto-detected flow.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-059: Implement `F01 get_tariffline`

- **Task ID:** T-059
- **Title:** Implement `F01 get_tariffline`
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-046
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Returns tariff-line iterable.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-060: Implement `F02 get_tariffline_by_hs`

- **Task ID:** T-060
- **Title:** Implement `F02 get_tariffline_by_hs`
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-059
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Tariff-line iterable filtered to a specific HS code.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-061: Implement hidden pagination (split on period)

- **Task ID:** T-061
- **Title:** Implement hidden pagination (split on period)
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-047
- **Primary Specification:** 009_TRADE_LAYER_SPEC.md
- **Primary ADR:** ADR-0004, ADR-0027
- **Expected Output:** Consumer-facing iterators that transparently paginate by `period`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-062: Implement empty-collection semantics for upstream 0-row responses

- **Task ID:** T-062
- **Title:** Implement empty-collection semantics for upstream 0-row responses
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-061
- **Primary Specification:** 009_TRADE_LAYER_SPEC.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Empty results return an empty collection, not an exception.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-063: Implement concurrent batch execution with configurable cap

- **Task ID:** T-063
- **Title:** Implement concurrent batch execution with configurable cap
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-061
- **Primary Specification:** 009_TRADE_LAYER_SPEC.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Batch downloads continue on failure and report success/failure summary.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-064: Implement trade deduplication (latest-wins by `ref_period_id`)

- **Task ID:** T-064
- **Title:** Implement trade deduplication (latest-wins by `ref_period_id`)
- **Phase:** Phase 3 — Trade Layer
- **Depends On:** T-045
- **Primary Specification:** 011_ETL_SPECIFICATION.md
- **Primary ADR:** ADR-0009
- **Expected Output:** Duplicate records deduplicated in the canonical collection.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

---

## Phase 4 — Validation, Normalisation, Export

**Tasks:** 11

### T-065: Define canonical entities E21 Request, E22 Response, E23 ErrorResponse

- **Task ID:** T-065
- **Title:** Define canonical entities E21 Request, E22 Response, E23 ErrorResponse
- **Phase:** Phase 4 — Validation, Normalisation, Export
- **Depends On:** T-016
- **Primary Specification:** 006_DATA_MODEL.md
- **Primary ADR:** ADR-0028
- **Expected Output:** Frozen dataclasses for the request / response envelope.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-066: Define canonical entities E24 MetadataCollection, E25 Pagination

- **Task ID:** T-066
- **Title:** Define canonical entities E24 MetadataCollection, E25 Pagination
- **Phase:** Phase 4 — Validation, Normalisation, Export
- **Depends On:** T-021
- **Primary Specification:** 006_DATA_MODEL.md
- **Primary ADR:** ADR-0028
- **Expected Output:** Frozen dataclasses for the metadata collection and pagination shapes.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-067: Implement client-side validation layer

- **Task ID:** T-067
- **Title:** Implement client-side validation layer
- **Phase:** Phase 4 — Validation, Normalisation, Export
- **Depends On:** T-005
- **Primary Specification:** 003_ARCHITECTURE.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Parameter validation before any upstream call.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-068: Implement upstream-to-canonical normaliser (skeleton)

- **Task ID:** T-068
- **Title:** Implement upstream-to-canonical normaliser (skeleton)
- **Phase:** Phase 4 — Validation, Normalisation, Export
- **Depends On:** T-045
- **Primary Specification:** 006_DATA_MODEL.md
- **Primary ADR:** ADR-0028
- **Expected Output:** `un_comtrade/normalisation/parser.py` turning upstream JSON into canonical entities.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-069: Implement `Decimal(str(value))` conversion for monetary fields

- **Task ID:** T-069
- **Title:** Implement `Decimal(str(value))` conversion for monetary fields
- **Phase:** Phase 4 — Validation, Normalisation, Export
- **Depends On:** T-068
- **Primary Specification:** 006_DATA_MODEL.md
- **Primary ADR:** ADR-0028
- **Expected Output:** All monetary fields normalised to `Decimal`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-070: Implement `legacyEstimationFlag` → `EstimationCategory` mapping

- **Task ID:** T-070
- **Title:** Implement `legacyEstimationFlag` → `EstimationCategory` mapping
- **Phase:** Phase 4 — Validation, Normalisation, Export
- **Depends On:** T-068
- **Primary Specification:** FIELD_VERIFICATION.md
- **Primary ADR:** ADR-0028
- **Expected Output:** Enum mapping per `FIELD_VERIFICATION.md` §3.5; preserves raw value.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-071: Implement `aggrLevel` → `AggrLevelCategory` mapping

- **Task ID:** T-071
- **Title:** Implement `aggrLevel` → `AggrLevelCategory` mapping
- **Phase:** Phase 4 — Validation, Normalisation, Export
- **Depends On:** T-068
- **Primary Specification:** FIELD_VERIFICATION.md
- **Primary ADR:** ADR-0028
- **Expected Output:** Mapping per `FIELD_VERIFICATION.md` §4.5.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-072: Implement `partner2Code` handling (preserve raw, document classic-mode ignore)

- **Task ID:** T-072
- **Title:** Implement `partner2Code` handling (preserve raw, document classic-mode ignore)
- **Phase:** Phase 4 — Validation, Normalisation, Export
- **Depends On:** T-068
- **Primary Specification:** FIELD_VERIFICATION.md
- **Primary ADR:** ADR-0028
- **Expected Output:** Canonical field preserved verbatim; SDK documents classic-mode behaviour.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-073: Implement JSON export to local file

- **Task ID:** T-073
- **Title:** Implement JSON export to local file
- **Phase:** Phase 4 — Validation, Normalisation, Export
- **Depends On:** T-068
- **Primary Specification:** 012_STORAGE_SPECIFICATION.md
- **Primary ADR:** ADR-0029
- **Expected Output:** `un_comtrade/export/json.py` writes canonical records as JSON.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-074: Implement CSV export to local file

- **Task ID:** T-074
- **Title:** Implement CSV export to local file
- **Phase:** Phase 4 — Validation, Normalisation, Export
- **Depends On:** T-073
- **Primary Specification:** 012_STORAGE_SPECIFICATION.md
- **Primary ADR:** ADR-0029
- **Expected Output:** `un_comtrade/export/csv.py` writes canonical records as CSV.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-075: Implement Parquet export to local file

- **Task ID:** T-075
- **Title:** Implement Parquet export to local file
- **Phase:** Phase 4 — Validation, Normalisation, Export
- **Depends On:** T-073
- **Primary Specification:** 012_STORAGE_SPECIFICATION.md
- **Primary ADR:** ADR-0029
- **Expected Output:** `un_comtrade/export/parquet.py` writes canonical records as Parquet.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

---

## Phase 5 — Infrastructure

**Tasks:** 6

### T-076: Refine retry middleware with configurable budget

- **Task ID:** T-076
- **Title:** Refine retry middleware with configurable budget
- **Phase:** Phase 5 — Infrastructure
- **Depends On:** T-010
- **Primary Specification:** 010_INFRASTRUCTURE_SPEC.md
- **Primary ADR:** ADR-0008, ADR-0022
- **Expected Output:** Retry budget configurable via the SDK configuration.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-077: Refine the timeout module with per-category defaults

- **Task ID:** T-077
- **Title:** Refine the timeout module with per-category defaults
- **Phase:** Phase 5 — Infrastructure
- **Depends On:** T-011
- **Primary Specification:** 010_INFRASTRUCTURE_SPEC.md
- **Primary ADR:** ADR-0023
- **Expected Output:** 30s request, 15s metadata, 300s download defaults configurable.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-078: Refine logging with WARNING default and API-key redaction

- **Task ID:** T-078
- **Title:** Refine logging with WARNING default and API-key redaction
- **Phase:** Phase 5 — Infrastructure
- **Depends On:** T-012
- **Primary Specification:** 010_INFRASTRUCTURE_SPEC.md
- **Primary ADR:** ADR-0025
- **Expected Output:** Log records redact `subscription-key` and other secrets.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-079: Refine metadata cache with user cache directory

- **Task ID:** T-079
- **Title:** Refine metadata cache with user cache directory
- **Phase:** Phase 5 — Infrastructure
- **Depends On:** T-013
- **Primary Specification:** 010_INFRASTRUCTURE_SPEC.md
- **Primary ADR:** ADR-0024
- **Expected Output:** Cache lives under the platform user cache directory (XDG / macOS / Windows).
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-080: Implement progress callback for long-running operations

- **Task ID:** T-080
- **Title:** Implement progress callback for long-running operations
- **Phase:** Phase 5 — Infrastructure
- **Depends On:** T-008
- **Primary Specification:** 010_INFRASTRUCTURE_SPEC.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Caller-supplied progress callback invoked during pagination.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-081: Implement resumable download skeleton (design only)

- **Task ID:** T-081
- **Title:** Implement resumable download skeleton (design only)
- **Phase:** Phase 5 — Infrastructure
- **Depends On:** T-061
- **Primary Specification:** 009_TRADE_LAYER_SPEC.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Design seam for future resumability; implementation deferred.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

---

## Phase 6 — Storage Layer

**Tasks:** 19

### T-082: Define canonical entities E14–E16 (TradeBalance, Bilateral, SUV)

- **Task ID:** T-082
- **Title:** Define canonical entities E14–E16 (TradeBalance, Bilateral, SUV)
- **Phase:** Phase 6 — Storage Layer
- **Depends On:** T-045
- **Primary Specification:** 006_DATA_MODEL.md
- **Primary ADR:** ADR-0028
- **Expected Output:** Frozen dataclasses for trade-balance, bilateral, and standard-unit-value.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-083: Define canonical entities E17–E18 (PublicationNote, DataAvailability)

- **Task ID:** T-083
- **Title:** Define canonical entities E17–E18 (PublicationNote, DataAvailability)
- **Phase:** Phase 6 — Storage Layer
- **Depends On:** T-045
- **Primary Specification:** 006_DATA_MODEL.md
- **Primary ADR:** ADR-0028
- **Expected Output:** Frozen dataclasses for publication notes and data availability.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-084: Define canonical entities E19–E20 (AsyncRequestHandle, AsyncRequestStatus)

- **Task ID:** T-084
- **Title:** Define canonical entities E19–E20 (AsyncRequestHandle, AsyncRequestStatus)
- **Phase:** Phase 6 — Storage Layer
- **Depends On:** T-045
- **Primary Specification:** 006_DATA_MODEL.md
- **Primary ADR:** ADR-0028
- **Expected Output:** Frozen dataclasses for the async lifecycle.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-085: Implement the storage adapter common interface

- **Task ID:** T-085
- **Title:** Implement the storage adapter common interface
- **Phase:** Phase 6 — Storage Layer
- **Depends On:** T-002
- **Primary Specification:** 012_STORAGE_SPECIFICATION.md
- **Primary ADR:** ADR-0029
- **Expected Output:** `un_comtrade/storage/base.py` exposing the common adapter API.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-086: Implement the DuckDB adapter (default analytical backend)

- **Task ID:** T-086
- **Title:** Implement the DuckDB adapter (default analytical backend)
- **Phase:** Phase 6 — Storage Layer
- **Depends On:** T-085
- **Primary Specification:** 012_STORAGE_SPECIFICATION.md
- **Primary ADR:** ADR-0029
- **Expected Output:** `un_comtrade/storage/duckdb.py` writing to a DuckDB database.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-087: Implement the Parquet adapter

- **Task ID:** T-087
- **Title:** Implement the Parquet adapter
- **Phase:** Phase 6 — Storage Layer
- **Depends On:** T-085
- **Primary Specification:** 012_STORAGE_SPECIFICATION.md
- **Primary ADR:** ADR-0029
- **Expected Output:** `un_comtrade/storage/parquet.py` writing Parquet files.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-088: Implement the JSON adapter

- **Task ID:** T-088
- **Title:** Implement the JSON adapter
- **Phase:** Phase 6 — Storage Layer
- **Depends On:** T-085
- **Primary Specification:** 012_STORAGE_SPECIFICATION.md
- **Primary ADR:** ADR-0029
- **Expected Output:** `un_comtrade/storage/json.py` writing JSON files.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-089: Implement the CSV adapter

- **Task ID:** T-089
- **Title:** Implement the CSV adapter
- **Phase:** Phase 6 — Storage Layer
- **Depends On:** T-085
- **Primary Specification:** 012_STORAGE_SPECIFICATION.md
- **Primary ADR:** ADR-0029
- **Expected Output:** `un_comtrade/storage/csv.py` writing CSV files.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-090: Implement logical partitioning by (reporter, year, frequency)

- **Task ID:** T-090
- **Title:** Implement logical partitioning by (reporter, year, frequency)
- **Phase:** Phase 6 — Storage Layer
- **Depends On:** T-085
- **Primary Specification:** 012_STORAGE_SPECIFICATION.md
- **Primary ADR:** ADR-0029
- **Expected Output:** Partition key derived from each canonical record.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-091: Implement schema validation before writing

- **Task ID:** T-091
- **Title:** Implement schema validation before writing
- **Phase:** Phase 6 — Storage Layer
- **Depends On:** T-090
- **Primary Specification:** 012_STORAGE_SPECIFICATION.md
- **Primary ADR:** ADR-0029
- **Expected Output:** Adapter rejects records that do not match the canonical schema.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-092: Implement `P01-P04 preview_*` public methods

- **Task ID:** T-092
- **Title:** Implement `P01-P04 preview_*` public methods
- **Phase:** Phase 6 — Storage Layer
- **Depends On:** T-047
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Public-preview methods for unauthenticated queries.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-093: Implement `C01-C03 count_*` public methods

- **Task ID:** T-093
- **Title:** Implement `C01-C03 count_*` public methods
- **Phase:** Phase 6 — Storage Layer
- **Depends On:** T-047
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Count-only methods returning record counts.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-094: Implement `U01 get_data_availability`

- **Task ID:** T-094
- **Title:** Implement `U01 get_data_availability`
- **Phase:** Phase 6 — Storage Layer
- **Depends On:** T-084
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Wrapper for the upstream data-availability endpoint.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-095: Implement `U02 get_standard_unit_value`

- **Task ID:** T-095
- **Title:** Implement `U02 get_standard_unit_value`
- **Phase:** Phase 6 — Storage Layer
- **Depends On:** T-082
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Wrapper for the SUV endpoint.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-096: Implement `U03 get_publication_notes`

- **Task ID:** T-096
- **Title:** Implement `U03 get_publication_notes`
- **Phase:** Phase 6 — Storage Layer
- **Depends On:** T-083
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Wrapper for the publication-notes endpoint.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-097: Implement `A01 submit_async_final_data`

- **Task ID:** T-097
- **Title:** Implement `A01 submit_async_final_data`
- **Phase:** Phase 6 — Storage Layer
- **Depends On:** T-084
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Submit an async data request.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-098: Implement `A02 check_async_request`

- **Task ID:** T-098
- **Title:** Implement `A02 check_async_request`
- **Phase:** Phase 6 — Storage Layer
- **Depends On:** T-084
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Poll an async request status.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-099: Implement `A03 download_async_request`

- **Task ID:** T-099
- **Title:** Implement `A03 download_async_request`
- **Phase:** Phase 6 — Storage Layer
- **Depends On:** T-084
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Download the completed async result.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-100: Implement `A04 bulk_download_final_file` and `A05 bulk_download_tariffline_file`

- **Task ID:** T-100
- **Title:** Implement `A04 bulk_download_final_file` and `A05 bulk_download_tariffline_file`
- **Phase:** Phase 6 — Storage Layer
- **Depends On:** T-085
- **Primary Specification:** 007_SDK_SPECIFICATION.md
- **Primary ADR:** ADR-0027
- **Expected Output:** Wrappers for the bulk-download endpoints.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

---

## Phase 7 — Testing & Validation

**Tasks:** 14

### T-101: Set up `pytest` test framework

- **Task ID:** T-101
- **Title:** Set up `pytest` test framework
- **Phase:** Phase 7 — Testing & Validation
- **Depends On:** T-019
- **Primary Specification:** 013_TESTING_STANDARD.md
- **Primary ADR:** ADR-0030
- **Expected Output:** `tests/` directory with `pytest` configuration and the first passing test.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-102: Implement unit-test scaffolding for M01–M09

- **Task ID:** T-102
- **Title:** Implement unit-test scaffolding for M01–M09
- **Phase:** Phase 7 — Testing & Validation
- **Depends On:** T-101
- **Primary Specification:** 013_TESTING_STANDARD.md
- **Primary ADR:** ADR-0030
- **Expected Output:** Unit tests for each metadata method using recorded fixtures.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-103: Implement unit-test scaffolding for M10–M18

- **Task ID:** T-103
- **Title:** Implement unit-test scaffolding for M10–M18
- **Phase:** Phase 7 — Testing & Validation
- **Depends On:** T-102
- **Primary Specification:** 013_TESTING_STANDARD.md
- **Primary ADR:** ADR-0030
- **Expected Output:** Unit tests for case-insensitive search and remaining metadata methods.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-104: Implement unit-test scaffolding for T01–T11

- **Task ID:** T-104
- **Title:** Implement unit-test scaffolding for T01–T11
- **Phase:** Phase 7 — Testing & Validation
- **Depends On:** T-101
- **Primary Specification:** 013_TESTING_STANDARD.md
- **Primary ADR:** ADR-0030
- **Expected Output:** Unit tests for each trade method using recorded fixtures.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-105: Implement unit-test scaffolding for F01, F02

- **Task ID:** T-105
- **Title:** Implement unit-test scaffolding for F01, F02
- **Phase:** Phase 7 — Testing & Validation
- **Depends On:** T-104
- **Primary Specification:** 013_TESTING_STANDARD.md
- **Primary ADR:** ADR-0030
- **Expected Output:** Unit tests for the tariff-line methods.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-106: Implement unit-test scaffolding for P01–P04, C01–C03, U01–U03

- **Task ID:** T-106
- **Title:** Implement unit-test scaffolding for P01–P04, C01–C03, U01–U03
- **Phase:** Phase 7 — Testing & Validation
- **Depends On:** T-104
- **Primary Specification:** 013_TESTING_STANDARD.md
- **Primary ADR:** ADR-0030
- **Expected Output:** Unit tests for preview, count, and utility methods.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-107: Implement unit-test scaffolding for A01–A05

- **Task ID:** T-107
- **Title:** Implement unit-test scaffolding for A01–A05
- **Phase:** Phase 7 — Testing & Validation
- **Depends On:** T-104
- **Primary Specification:** 013_TESTING_STANDARD.md
- **Primary ADR:** ADR-0030
- **Expected Output:** Unit tests for the async and bulk methods.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-108: Implement the dedicated live-API integration test suite

- **Task ID:** T-108
- **Title:** Implement the dedicated live-API integration test suite
- **Phase:** Phase 7 — Testing & Validation
- **Depends On:** T-101
- **Primary Specification:** 013_TESTING_STANDARD.md
- **Primary ADR:** ADR-0030
- **Expected Output:** `tests/integration/` running against the live upstream with a key.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-109: Implement the API contract test suite

- **Task ID:** T-109
- **Title:** Implement the API contract test suite
- **Phase:** Phase 7 — Testing & Validation
- **Depends On:** T-101
- **Primary Specification:** 013_TESTING_STANDARD.md
- **Primary ADR:** ADR-0030
- **Expected Output:** Contract tests detecting upstream schema changes.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-110: Implement the regression test suite

- **Task ID:** T-110
- **Title:** Implement the regression test suite
- **Phase:** Phase 7 — Testing & Validation
- **Depends On:** T-101
- **Primary Specification:** 013_TESTING_STANDARD.md
- **Primary ADR:** ADR-0030
- **Expected Output:** Recorded regression tests for stable behaviour.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-111: Implement versioned mock fixtures

- **Task ID:** T-111
- **Title:** Implement versioned mock fixtures
- **Phase:** Phase 7 — Testing & Validation
- **Depends On:** T-101
- **Primary Specification:** 013_TESTING_STANDARD.md
- **Primary ADR:** ADR-0030
- **Expected Output:** Mock fixtures tied to API versions.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-112: Implement documentation example tests

- **Task ID:** T-112
- **Title:** Implement documentation example tests
- **Phase:** Phase 7 — Testing & Validation
- **Depends On:** T-101
- **Primary Specification:** 013_TESTING_STANDARD.md
- **Primary ADR:** ADR-0030
- **Expected Output:** Tests that execute every documentation example end-to-end.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-113: Set up CI pipeline configuration

- **Task ID:** T-113
- **Title:** Set up CI pipeline configuration
- **Phase:** Phase 7 — Testing & Validation
- **Depends On:** T-101
- **Primary Specification:** 013_TESTING_STANDARD.md
- **Primary ADR:** ADR-0033
- **Expected Output:** CI configuration running unit + contract + regression tests on every PR.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-114: Implement coverage reporting

- **Task ID:** T-114
- **Title:** Implement coverage reporting
- **Phase:** Phase 7 — Testing & Validation
- **Depends On:** T-101
- **Primary Specification:** 013_TESTING_STANDARD.md
- **Primary ADR:** ADR-0030
- **Expected Output:** Coverage report above 80% of public interfaces; not 100%.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

---

## Phase 8 — Packaging & Distribution

**Tasks:** 11

### T-115: Finalise `pyproject.toml` with all project metadata

- **Task ID:** T-115
- **Title:** Finalise `pyproject.toml` with all project metadata
- **Phase:** Phase 8 — Packaging & Distribution
- **Depends On:** T-001
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0031
- **Expected Output:** `pyproject.toml` complete with name, version, authors, classifiers, etc.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-116: Define optional extras (`[duckdb]`, `[parquet]`, `[postgres]`, `[cli]`)

- **Task ID:** T-116
- **Title:** Define optional extras (`[duckdb]`, `[parquet]`, `[postgres]`, `[cli]`)
- **Phase:** Phase 8 — Packaging & Distribution
- **Depends On:** T-115
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0031
- **Expected Output:** Extras entry points in `pyproject.toml`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-117: Implement the `un-comtrade` console script entry

- **Task ID:** T-117
- **Title:** Implement the `un-comtrade` console script entry
- **Phase:** Phase 8 — Packaging & Distribution
- **Depends On:** T-086
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0031
- **Expected Output:** Console script registered in `pyproject.toml` calling `un_comtrade.cli.main`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-118: Implement CLI command skeleton (`un-comtrade`)

- **Task ID:** T-118
- **Title:** Implement CLI command skeleton (`un-comtrade`)
- **Phase:** Phase 8 — Packaging & Distribution
- **Depends On:** T-117
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0031
- **Expected Output:** Argument parser with sub-commands for high-value operations.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-119: Implement CLI command `version`

- **Task ID:** T-119
- **Title:** Implement CLI command `version`
- **Phase:** Phase 8 — Packaging & Distribution
- **Depends On:** T-118
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0031
- **Expected Output:** Prints the SDK version.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-120: Implement CLI command `countries`

- **Task ID:** T-120
- **Title:** Implement CLI command `countries`
- **Phase:** Phase 8 — Packaging & Distribution
- **Depends On:** T-118
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0031
- **Expected Output:** Lists reporter countries in human-readable form.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-121: Implement CLI command `preview-exports`

- **Task ID:** T-121
- **Title:** Implement CLI command `preview-exports`
- **Phase:** Phase 8 — Packaging & Distribution
- **Depends On:** T-118
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0031
- **Expected Output:** Issues a public-preview exports query and prints results.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-122: Implement CLI command `dump` (export a query to a file)

- **Task ID:** T-122
- **Title:** Implement CLI command `dump` (export a query to a file)
- **Phase:** Phase 8 — Packaging & Distribution
- **Depends On:** T-118
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0031
- **Expected Output:** Materialises a query result to JSON / CSV / Parquet.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-123: Configure wheel + sdist build

- **Task ID:** T-123
- **Title:** Configure wheel + sdist build
- **Phase:** Phase 8 — Packaging & Distribution
- **Depends On:** T-115
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0031
- **Expected Output:** Build artefacts in `dist/`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-124: Configure PyPI publishing workflow

- **Task ID:** T-124
- **Title:** Configure PyPI publishing workflow
- **Phase:** Phase 8 — Packaging & Distribution
- **Depends On:** T-123
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0031
- **Expected Output:** Workflow for publishing to PyPI from tagged releases.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-125: Generate release notes from the changelog

- **Task ID:** T-125
- **Title:** Generate release notes from the changelog
- **Phase:** Phase 8 — Packaging & Distribution
- **Depends On:** T-123
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0031
- **Expected Output:** Script that extracts release notes from `docs/CHANGELOG.md`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

---

## Phase 9 — Production Release

**Tasks:** 6

### T-126: Run full RC test execution

- **Task ID:** T-126
- **Title:** Run full RC test execution
- **Phase:** Phase 9 — Production Release
- **Depends On:** T-114
- **Primary Specification:** 013_TESTING_STANDARD.md
- **Primary ADR:** ADR-0030
- **Expected Output:** All unit, contract, regression, integration tests pass.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-127: Generate release artefacts (wheel + sdist)

- **Task ID:** T-127
- **Title:** Generate release artefacts (wheel + sdist)
- **Phase:** Phase 9 — Production Release
- **Depends On:** T-123
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0033
- **Expected Output:** Built artefacts in `dist/` ready for publication.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-128: Tag the release version in Git

- **Task ID:** T-128
- **Title:** Tag the release version in Git
- **Phase:** Phase 9 — Production Release
- **Depends On:** T-127
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0033
- **Expected Output:** Git tag matching the version in `pyproject.toml`.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-129: Manual RC approval gate

- **Task ID:** T-129
- **Title:** Manual RC approval gate
- **Phase:** Phase 9 — Production Release
- **Depends On:** T-126
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0033
- **Expected Output:** Approval recorded in CHANGELOG before publication.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-130: Publish to PyPI

- **Task ID:** T-130
- **Title:** Publish to PyPI
- **Phase:** Phase 9 — Production Release
- **Depends On:** T-129
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0031
- **Expected Output:** Wheel and sdist uploaded to PyPI.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-131: Verify PyPI installation in a fresh virtualenv

- **Task ID:** T-131
- **Title:** Verify PyPI installation in a fresh virtualenv
- **Phase:** Phase 9 — Production Release
- **Depends On:** T-130
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0031
- **Expected Output:** `pip install un-comtrade-sdk` succeeds in a clean env.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

---

## Phase 10 — Maintenance

**Tasks:** 5

### T-132: Set up the version-control workflow (trunk-based, tags as releases)

- **Task ID:** T-132
- **Title:** Set up the version-control workflow (trunk-based, tags as releases)
- **Phase:** Phase 10 — Maintenance
- **Depends On:** T-128
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0033
- **Expected Output:** Documented branch strategy; PR template; commit-message format.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-133: Configure the dependency-update review process

- **Task ID:** T-133
- **Title:** Configure the dependency-update review process
- **Phase:** Phase 10 — Maintenance
- **Depends On:** T-132
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0033
- **Expected Output:** Process requiring manual review before accepting dependency changes.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-134: Implement changelog-to-release-notes pipeline

- **Task ID:** T-134
- **Title:** Implement changelog-to-release-notes pipeline
- **Phase:** Phase 10 — Maintenance
- **Depends On:** T-125
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0033
- **Expected Output:** Automated pipeline turning CHANGELOG entries into release notes.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-135: Set up release reproducibility from Git history

- **Task ID:** T-135
- **Title:** Set up release reproducibility from Git history
- **Phase:** Phase 10 — Maintenance
- **Depends On:** T-130
- **Primary Specification:** 014_PACKAGING_SPECIFICATION.md
- **Primary ADR:** ADR-0033
- **Expected Output:** Reproducible build verified by tagging and rebuilding from a clean checkout.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

### T-136: Establish maintenance cadence

- **Task ID:** T-136
- **Title:** Establish maintenance cadence
- **Phase:** Phase 10 — Maintenance
- **Depends On:** T-130
- **Primary Specification:** 016_IMPLEMENTATION_ROADMAP.md
- **Primary ADR:** ADR-0034
- **Expected Output:** Documented cadence for ongoing maintenance releases.
- **Definition of Done:**
  ```text
  ✓ Code implemented
  ✓ Unit tests passing
  ✓ Documentation updated
  ✓ CHANGELOG updated
  ✓ TASK_LOG updated
  ```

---

## Total tasks: 136

## Phases: 10

## First task: T-001 — Create `pyproject.toml` with `httpx` requirement and Python 3.11+ support
## Last task: T-136 — Establish maintenance cadence

---

*End of document.*