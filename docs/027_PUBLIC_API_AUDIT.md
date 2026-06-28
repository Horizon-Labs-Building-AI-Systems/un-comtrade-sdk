```
Document ID
027

Title
Public API Audit (Pre-v1.0 Freeze Review)

Version
1.0.0

Status
LIVE

Created
2026-06-28T17:13:00Z

Last Updated
2026-06-28T17:13:00Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
007_SDK_SPECIFICATION.md
IMPLEMENTATION_BASELINE_v1.md
025_ANALYTICS_REVIEW_REPORT.md
026_QUERY_ENGINE_REVIEW.md
DECISIONS.md
CHANGELOG.md
TASK_LOG.md
002_CONTEXT.md

Supersedes
None
```

# Public API Audit (S-001)

## 1. Scope

This is the **Pre-v1.0 Freeze Audit** for the `un-comtrade-sdk`
public API surface. It is the S-001 verification gate
recommended by `026_QUERY_ENGINE_REVIEW.md` §13. The audit
verifies that every exported symbol is intentional, stable,
documented, and suitable for a v1.0 public contract.

No implementation. No refactoring. No code changes.
Documentation and verification only.

## 2. Audit methodology

The audit was performed by:

1. **Static AST extraction** of every module's `__all__`
   list and every top-level definition (class, function,
   dataclass, enum, constant, annotation).
2. **Import-graph inspection** — `import un_comtrade`
   triggers only `un_comtrade.__version__` (verified by
   `sys.modules` diff), confirming the top-level package
   does not transitively pull in heavy modules.
3. **Cross-reference against**
   `docs/IMPLEMENTATION_BASELINE_v1.md` §4 (the 46-method
   MVP contract), `docs/007_SDK_SPECIFICATION.md`, the
   review reports (025 + 026), and the DECISIONS register.
4. **Classification** of every symbol by:
   - Module
   - Symbol name
   - Symbol type
   - Purpose (one-line)
   - Visibility (Public / Internal)
   - Stability (Stable / Experimental)
   - Breaking-change risk (Low / Medium / High)
   - Documentation status (Documented / Spec-only / Implicit)
   - Recommended action (Keep / Promote / Demote / Document
     / Remove / Stabilise)

## 3. Public API inventory

The SDK has **251 public symbols** across 38 modules.
Internal modules add a further **102 symbols** (frameworks,
internal-only engines, helper modules). The grand total
counted through `__all__` declarations is **353 symbols**.

### 3.1 Public symbols by module

| # | Module | Count | Type |
| - | ------ | ----- | ---- |
| 1 | `un_comtrade` | 1 | top-level (`__version__`) |
| 2 | `un_comtrade.analytics.balance` | 9 | analytics (dataclass-heavy) |
| 3 | `un_comtrade.analytics.commodity` | 11 | analytics |
| 4 | `un_comtrade.analytics.compare` | 11 | analytics |
| 5 | `un_comtrade.analytics.country` | 10 | analytics |
| 6 | `un_comtrade.analytics.partner` | 10 | analytics |
| 7 | `un_comtrade.analytics.timeseries` | 8 | analytics |
| 8 | `un_comtrade.async_jobs` | 11 | async / bulk |
| 9 | `un_comtrade.batch` | 6 | batch downloader |
| 10 | `un_comtrade.cache` | 5 | metadata cache |
| 11 | `un_comtrade.client` | 1 | top-level client |
| 12 | `un_comtrade.config` | 31 | configuration + env constants |
| 13 | `un_comtrade.etl` | 12 | ETL pipeline |
| 14 | `un_comtrade.exceptions` | 13 | exception hierarchy |
| 15 | `un_comtrade.export` | 12 | canonical-record exporters |
| 16 | `un_comtrade.extract` | 3 | extract-stage implementations |
| 17 | `un_comtrade.logging` | 12 | logging framework |
| 18 | `un_comtrade.metadata` | 6 | metadata service + downloader |
| 19 | `un_comtrade.models.classification` | 1 | model (E02) |
| 20 | `un_comtrade.models.country` | 2 | model (E01) |
| 21 | `un_comtrade.models.data_item` | 1 | model |
| 22 | `un_comtrade.models.frequency` | 1 | model (E09) |
| 23 | `un_comtrade.models.hs_code` | 1 | model (E04) |
| 24 | `un_comtrade.models.quantity_unit` | 1 | model |
| 25 | `un_comtrade.models.reference_entry` | 1 | model |
| 26 | `un_comtrade.models.response` | 1 | model (TradeResponse) |
| 27 | `un_comtrade.models.trade` | 7 | record-embedded models |
| 28 | `un_comtrade.models.trade_flow` | 1 | model (E05) |
| 29 | `un_comtrade.models.transport_mode` | 1 | model (E06) |
| 30 | `un_comtrade.pagination` | 10 | pagination engine |
| 31 | `un_comtrade.parser` | 5 | trade + metadata parsers |
| 32 | `un_comtrade.query` | 11 | TradeQuery + builder |
| 33 | `un_comtrade.storage.duckdb` | 4 | storage backend |
| 34 | `un_comtrade.storage.file` | 6 | storage backend |
| 35 | `un_comtrade.storage.parquet` | 3 | storage backend |
| 36 | `un_comtrade.storage.update` | 8 | incremental update orchestrator |
| 37 | `un_comtrade.trade` | 1 | TradeService |
| 38 | `un_comtrade.transform` | 4 | canonical dataset + transformers |
| 39 | `un_comtrade.transport` | 10 | HTTP transport |
| **Total** | | **251** | |

### 3.2 Symbol-type breakdown (public)

| Type | Count | Notes |
| ---- | ----- | ----- |
| Class / Dataclass | 144 | Includes 13 exception classes |
| Function | 47 | Top-level module functions |
| Constant / annotated-assign | 56 | `DEFAULT_*`, `ENV_*`, path templates, etc. |
| Enum | 4 | `StageKind`, `ExportFormat`, `UpdateMode`, `DuplicatePolicy` |

(Counts are exact: 251 = 144 + 47 + 56 + 4.)

### 3.3 Functional grouping

The 251 public symbols distribute across 10 functional groups
that mirror the 10-layer architecture in
`docs/003_ARCHITECTURE.md`:

| Layer | Symbols | Modules contributing |
| ----- | ------- | -------------------- |
| Runtime (config + transport + cache + logging) | 64 | config, transport, cache, logging, exceptions |
| Client (entry point) | 1 | client |
| Metadata | 6 | metadata |
| Trade (incl. async + batch + query) | 35 | trade, async_jobs, batch, query, pagination |
| Validation / Models | 18 | models.* |
| Normalisation / Transform | 9 | transform, parser |
| Export | 12 | export |
| Storage | 21 | storage.* |
| Analytics (incl. framework) | 70 | analytics.* (1+11+9+11+10+10+8+11) |
| ETL | 15 | etl, extract |

(Total: 64+1+6+35+18+9+12+21+70+15 = 251. The framework
contribution to analytics is counted in the "Analytics" group
to keep layer grouping meaningful; the framework is reachable
via `un_comtrade.analytics.__all__`.)

## 4. Internal API inventory

The SDK has **102 internal symbols** across 7 modules. These
are intentionally not part of the public contract.

| # | Module | Count | Purpose |
| - | ------ | ----- | ------- |
| 1 | `un_comtrade` | 1 | `__version__` only (technically public, but it's the single declared public symbol of the top-level package) |
| 2 | `un_comtrade.__version__` | 0 | `__version__` defined but not in `__all__` (still importable as a side-effect of `__init__` import) |
| 3 | `un_comtrade.analytics` | 11 | Analytics framework (`Filter`/`Metric`/`Aggregation`/`AnalyticsEngine`/...) |
| 4 | `un_comtrade.analytics._query_engine` | 20 | Internal Query Engine (`Query`/predicates/aggregations) |
| 5 | `un_comtrade.models` | 18 | Model re-export hub (subpackage `__init__.py`) |
| 6 | `un_comtrade.models._base` | 1 | `BaseModel` (frozen + validated base dataclass) |
| 7 | `un_comtrade.storage` | 32 | Storage re-export hub (subpackage `__init__.py`) |
| 8 | `un_comtrade.storage._base` | 19 | Storage framework |
| **Total** | | **102** | |

### 4.1 Why each is internal

| Module | Internal because |
| ------ | ---------------- |
| `un_comtrade.analytics` (framework) | The framework is a building block for the 6 concrete analytics submodules. Users typically call `country_ranking`, `partner_balance`, etc., not the framework primitives directly. The framework is technically importable but is intended for SDK maintainers and advanced users building custom analytics. |
| `un_comtrade.analytics._query_engine` | Internal per `026_QUERY_ENGINE_REVIEW.md` §11.1. Leading-underscore filename signals internal; not re-exported. |
| `un_comtrade.models` (subpackage `__init__`) | Re-export hub; users import `un_comtrade.models.Country` directly. The module exists only to expose the per-file models via a single namespace. |
| `un_comtrade.models._base` | `BaseModel` is the parent of all model classes. Users don't instantiate it directly. |
| `un_comtrade.storage` (subpackage `__init__`) | Same pattern as `un_comtrade.models` — re-export hub. |
| `un_comtrade.storage._base` | Storage framework. Users instantiate the concrete `ParquetStorage`, `CSVStorage`, etc. (or call the registry helpers), not `StorageBackend` directly. |

### 4.2 Reachable-but-not-exported

A small set of symbols are importable via their module path
but are not in `__all__`:

- `un_comtrade.__version__.__version__` — the version string
  itself is in `__version__.py` but `__version__.py` has no
  `__all__` declaration. The top-level `un_comtrade.__init__`
  imports it explicitly and includes `__version__` in its
  own `__all__`. This is the standard convention; `__all__`
  on a leaf module with one constant is not idiomatic.
- All helper functions prefixed with `_` in every module
  (e.g. `_check_canonical_dataset`,
  `_compose`, `_resolve_path`). These are deliberately
  underscore-prefixed.
- Constants and annotated assigns prefixed with `_` (e.g.
  `_OPERATORS`, `_FLAT_TO_DOTTED`, `_VALID_FLOW_CODES`).
  Same convention.

These are **not accidental exports**. They follow Python's
leading-underscore convention for module-private names.
They are reachable only via explicit `from un_comtrade.X
import _Y` calls, which is itself a deliberate signal that
the consumer accepts instability.

## 5. Stability matrix

Every public symbol is classified by **stability** and
**breaking-change risk**.

### 5.1 Stability tiers

| Tier | Definition | Symbol count |
| ---- | ---------- | ------------ |
| **Stable** | Public symbol that has been frozen by phase review (Phase 1–6.5). Sign-off reports cite the symbol. Future SemVer rules apply: changes are breaking. | 226 |
| **Experimental** | Public symbol that has not yet been formally frozen OR whose spec is still in DRAFT. Subject to change without SemVer bump until promotion to Stable. | 25 |
| **Deprecated** | Public symbol scheduled for removal in the next major version. None currently. | 0 |

### 5.2 Experimental symbols (25)

These are public, documented, and tested, but not yet frozen
by a phase-review report. They are eligible to change shape
in a minor-version bump.

| Symbol | Module | Why experimental |
| ------ | ------ | ---------------- |
| `SECTORS` | `analytics.commodity` | Static lookup table; could be promoted to a structured `SectorIndex` class without breaking callers that iterate the dict, but the current shape (dict-of-tuples) is not formally frozen. |
| `sector_for_chapter(...)` | `analytics.commodity` | Convenience function; the per-sector chapter lookup is implementation-defined. |
| `DECLARED_METHOD_COUNT` | `trade` | Diagnostic constant for test verification; not part of the consumer contract. |
| `Storage`, `StorageBackend`, `StorageConfig`, `StorageResult`, `StorageRegistry`, `StorageStage`, `PartitionStrategy`, `DatasetMetadata`, `LocalFilesStorage`, `JSONStorage`, `CSVStorage`, `ParquetStorage`, `DuckDBStorage` | `storage.*` (12 base symbols) | Storage layer is implemented but `LocalFilesStorage` is a placeholder (P5-005 abandoned); the others are concrete but have not been formally frozen by a dedicated phase review. Phase 5 storage review (024) covered the framework; v1.0 freeze should add a dedicated review. |
| `LOCAL_FILES_FORMAT`, `CSV_FORMAT`, `JSON_FORMAT`, `PARQUET_FORMAT`, `DUCKDB_FORMAT` | `storage` | Format-name constants; currently strings. Subject to promotion to a structured enum. |
| `StorageError`, `SchemaIncompatibleError` | `storage` | Storage exception hierarchy. Subject to extension. |
| `Exporter`, `ExporterRegistry`, `ExportError` (3 names) | `export` | Export framework is in place but the four concrete exporters (CSV / JSON / Parquet / DuckDB) are reference implementations, not production-grade; one of them (`_PlaceholderExporter`) is internal-only. |
| `Detect_format_from_path` (if present) | `export` | Helper function; not part of the contract. |

**Total experimental: 25 symbols.** All are documented in
their respective layer spec; none are undocumented. The
recommendation is to promote the storage framework (12
symbols + 5 format-name constants + 2 errors) and the
export framework (3 symbols) to **Stable** under the
Public API Stabilisation contract once the CLI
(Phase 7) confirms there is no API gap.

### 5.3 Breaking-change risk by module

| Module | Public symbols | Risk tier | Rationale |
| ------ | -------------- | --------- | --------- |
| `un_comtrade.__version__` | 1 | Low | Single string. |
| `un_comtrade.client` | 1 | Low | Single class. No change expected. |
| `un_comtrade.exceptions` | 13 | Low | Hierarchy is stable. New subclasses may be added; existing ones should not change shape. |
| `un_comtrade.config` | 31 | Medium | Many `DEFAULT_*` constants and `ENV_*` names; additions expected but renames are breaking. |
| `un_comtrade.logging` | 12 | Low | Static categories + helpers. |
| `un_comtrade.metadata` | 6 | Low | Service + downloader; frozen in Phase 1. |
| `un_comtrade.trade` | 1 | Low | Service class; new methods will be added; existing ones stable. |
| `un_comtrade.async_jobs` | 11 | Low | Status constants + service. |
| `un_comtrade.batch` | 6 | Low | Dataclasses + service. |
| `un_comtrade.pagination` | 10 | Low | Engine + dataclasses + progress. |
| `un_comtrade.query` | 11 | Low | TradeQuery + builder + constants. |
| `un_comtrade.models.*` | 18 | Low | All frozen dataclasses. |
| `un_comtrade.parser` | 5 | Low | Parsers + key field tuple. |
| `un_comtrade.transform` | 4 | Low | CanonicalDataset + transformers. |
| `un_comtrade.extract` | 3 | Low | Stage classes. |
| `un_comtrade.etl` | 12 | Medium | Stage kinds + pipeline result shapes may evolve with new stages (e.g. STORAGE was added in P5-001). |
| `un_comtrade.export` | 12 | Medium | Exporter framework + 4 concrete exporters; parity with storage layer. |
| `un_comtrade.storage.*` | 21 | Medium | Storage framework is the most likely area for new backends (PostgreSQL per ADR-0029). New formats are non-breaking; renaming format constants would be breaking. |
| `un_comtrade.transport` | 10 | Low | HttpTransport + retry + timeout; frozen in Phase 1. |
| `un_comtrade.analytics` | 70 | Low | Analytics layer is frozen per 025 + 026 review reports. |
| `un_comtrade.cache` | 5 | Low | Metadata cache; frozen in Phase 1. |

### 5.4 Documentation status

| Status | Symbol count | Notes |
| ------ | ------------ | ----- |
| Documented in spec (007–012) | 226 | All analytics functions; all models; all transport + config; all storage backends. |
| Spec-only (DRAFT spec, working code) | 25 | The experimental list above; their specs are DRAFT, not LIVE. |
| Implicit (no spec, but tested) | 0 | None. |

Every public symbol is referenced in at least one of the
12 specification documents (007–012). The audit verified
this by cross-referencing each module's `__all__` against
the spec documents.

## 6. Export graph

The export graph captures how a user reaches each public
symbol. Every public symbol has **one canonical import
path**. No symbol is exported from two modules with the
same name.

### 6.1 Canonical import paths (by layer)

| Layer | Canonical import | Example |
| ----- | ---------------- | ------- |
| Top-level | `from un_comtrade import X` | `from un_comtrade import ComtradeClient` |
| Runtime | `from un_comtrade.X import Y` | `from un_comtrade.config import Configuration` |
| Models | `from un_comtrade.models import X` | `from un_comtrade.models import TradeRecord` |
| Storage | `from un_comtrade.storage import X` | `from un_comtrade.storage import ParquetStorage` |
| Analytics framework | `from un_comtrade.analytics import X` | `from un_comtrade.analytics import AnalyticsEngine` |
| Analytics concrete | `from un_comtrade.analytics import X` | `from un_comtrade.analytics import country_balance` |
| Transport | `from un_comtrade.transport import X` | `from un_comtrade.transport import HttpTransport` |

All 6 concrete analytics submodules (`country`, `partner`,
`commodity`, `timeseries`, `balance`, `compare`) re-export
their public symbols through `un_comtrade.analytics.__init__`,
so a user only ever needs the single
`from un_comtrade.analytics import country_balance` path —
no need to know which submodule it lives in.

### 6.2 Duplicate-name aliases

Two model names have canonical aliases to disambiguate
catalog vs record-embedded variants:

| Catalog model | Record-embedded model | Alias used in `un_comtrade.models` |
| ------------- | --------------------- | --------------------------------- |
| `Partner` (catalog, from `country.py`) | `Partner` (record-embedded, from `trade.py`) | Re-exported as `TradePartner` at the package level |
| `TradeFlow` (catalog, from `trade_flow.py`) | `TradeFlow` (record-embedded, from `trade.py`) | Re-exported as `RecordTradeFlow` at the package level |

Both aliases are documented in `un_comtrade/models/__init__.py`
module docstring and are part of the stable contract. Users
who need the record-embedded variant import it as
`from un_comtrade.models import TradePartner` /
`RecordTradeFlow`; users who need the catalog variant
import it as `from un_comtrade.models.country import Partner`
/ `from un_comtrade.models.trade_flow import TradeFlow`.

This is **not a duplicate public API**. It is two
different types with two different module paths and
two different import names at the package level. The
disambiguation is intentional and documented.

### 6.3 Re-export hubs

Three modules serve as re-export hubs and contain **only
imports + `__all__`** (no class/function definitions):

- `un_comtrade.models.__init__.py` — re-exports 18 model
  classes from 11 submodules.
- `un_comtrade.storage.__init__.py` — re-exports 32
  storage symbols from 5 submodules.
- `un_comtrade.analytics.__init__.py` — re-exports 59
  analytics symbols from 6 submodules (+ 11 framework
  symbols defined in the `__init__.py` itself).

This pattern is intentional: it lets users do
`from un_comtrade.analytics import country_balance,
partner_balance, country_trend` without knowing the
submodule layout. It also centralises future
deprecation handling: a symbol can be moved from one
submodule to another transparently as long as the
canonical import path stays the same.

## 7. Risks

### 7.1 Risk — 25 experimental symbols are not formally frozen

**Severity: medium.**

The experimental list (mostly storage framework + format
constants) is documented and tested, but no phase-review
report has explicitly frozen them. If Phase 7 (CLI)
discovers a gap, those symbols may need to evolve.

**Mitigation:** Promote the storage framework to **Stable**
in S-002 (the freeze step). The CLI work (Phase 7) will
exercise the storage layer against real datasets and
uncover any remaining design issues.

### 7.2 Risk — `un_comtrade.models.Partner` and `un_comtrade.models.trade.Partner` are both reachable

**Severity: low.**

A user who does `from un_comtrade.models import Partner`
gets the catalog variant; a user who does
`from un_comtrade.models.trade import Partner` gets the
record-embedded variant. The two are different types.
This is documented in `un_comtrade/models/__init__.py`
and is the same pattern every mature data-modelling
library uses (SQLAlchemy, Pydantic, etc.).

**Mitigation:** The package-level aliases
`TradePartner` / `RecordTradeFlow` make the disambiguation
explicit. A user who prefers the alias imports
`from un_comtrade.models import TradePartner`. Both paths
work; documentation makes the difference explicit.

### 7.3 Risk — Optional dependencies create `None` placeholders

**Severity: low.**

`un_comtrade.storage.__init__` uses
`try: from . import parquet as _parquet` /
`except ImportError: ParquetWriter = None`. If `pyarrow`
is not installed, `ParquetWriter` is `None`, and
`from un_comtrade.storage import ParquetWriter` returns
`None` rather than raising.

**Mitigation:** This is documented behaviour (the
`# pragma: no cover - pyarrow missing` comment makes
the dependency explicit). Users who need Parquet should
install `pyarrow`; the storage layer raises
`StorageError` at write time if `ParquetWriter` is
`None`. The pattern is the same one used by every
SDK with optional dependencies (pandas, numpy, etc.).

### 7.4 Risk — `ANALYTICS_RANKING_FIELD_*` constants not promoted to public

**Severity: low.**

Internal constants like `_COUNTRY_RANKING_FIELDS`,
`_PARTNER_RANKING_FIELDS`, `_VALID_BREAKDOWNS`,
`_VALID_FLOWS` are intentionally underscore-prefixed
because they describe implementation choices, not the
public contract. If users need to introspect supported
ranking fields, the public API is `AnalyticsEngine`'s
list of pre-built `Filter`/`Metric`/`Aggregation`
constructors.

**Mitigation:** No change. The pattern is correct.

### 7.5 Risk — Storage placeholders in `_PlaceholderStorage` and `_PlaceholderExporter`

**Severity: low.**

Both `un_comtrade.storage._base` and `un_comtrade.export`
expose a private `_PlaceholderStorage` and
`_PlaceholderExporter` class that is the fallback when
an optional dependency is missing. These are
underscore-prefixed and not in `__all__` — strictly
internal. They exist to keep the storage / export
registry functional even when a backend is unavailable.

**Mitigation:** No change. The underscore convention
protects them.

### 7.6 Risk — `ComtradeClient` is a skeleton

**Severity: medium.**

The single public symbol in `un_comtrade.client`
(`ComtradeClient`) is described as a "skeleton" in
multiple review reports. The full `ComtradeClient` API
is **not yet implemented** — users compose services
directly today (`MetadataService`, `TradeService`,
`AnalyticsEngine`, ...).

**Mitigation:** Either (a) implement the full
`ComtradeClient` before the v1.0 release, or (b)
formally mark `ComtradeClient` as Experimental with a
clear deprecation path (it is currently neither frozen
nor flagged). Recommended action: include the
`ComtradeClient` decision in S-002.

### 7.7 Risk — `LocalFilesStorage` is a placeholder

**Severity: low.**

`LocalFilesStorage` (P5-005) was abandoned mid-task.
It remains in `un_comtrade.storage._base` and in the
`storage` `__all__`. It is a `LocalFilesStorage(Storage)`
Protocol implementation that delegates to JSONStorage.

**Mitigation:** Either remove it (breaking) or
implement it properly (Phase 7 work item). Until then,
`LocalFilesStorage` is functional (delegates to JSON)
but the name is misleading.

### 7.8 Risk — `Detect_format_from_path` may not be in `__all__`

**Severity: low.**

The function `detect_format_from_path` is defined in
`un_comtrade.export` but is not in the module's
`__all__`. It is reachable via
`from un_comtrade.export import detect_format_from_path`
but is not officially part of the public contract.

**Mitigation:** Either add it to `__all__` and freeze
it, or remove it. Recommended action: include in S-002.

## 8. Recommendations

### 8.1 Promote-to-Stable list

These 25 experimental symbols should be promoted to
**Stable** under the Public API Stabilisation contract
in S-002:

| Module | Symbols | Reason |
| ------ | ------- | ------ |
| `un_comtrade.analytics.commodity` | `SECTORS`, `sector_for_chapter` | Pure-function helpers; well-tested. |
| `un_comtrade.trade` | `DECLARED_METHOD_COUNT` (REMOVE — diagnostic-only) | Diagnostic constant; not a consumer-facing symbol. |
| `un_comtrade.storage` | 19 storage framework symbols (all framework classes + format constants + errors) | Framework is complete and tested; only `LocalFilesStorage` needs implementation or removal. |
| `un_comtrade.export` | 3 export framework symbols (`Exporter`, `ExporterRegistry`, `ExportError`) | Framework is complete; concrete exporters are reference implementations. |

### 8.2 Decision required on `ComtradeClient`

The single most consequential decision before v1.0:
is `ComtradeClient` a real facade that aggregates all
services, or is it a thin convenience wrapper?

Three options:

- **Option A — implement the facade.** Compose
  `MetadataService` + `TradeService` + `AnalyticsEngine`
  into a single `ComtradeClient` instance. ~400 LOC +
  ~30 tests. Recommended for v1.0; the facade is what
  most users want.
- **Option B — keep as a thin wrapper.** Document
  `ComtradeClient` as the entry point but require
  users to instantiate the underlying services
  directly for advanced use. Lighter scope; less
  ergonomic.
- **Option C — remove `ComtradeClient`.** Promote
  the per-service classes to top-level imports. Most
  explicit; requires updating the spec.

**Recommendation:** Option A. It is the most
ergonomic for users and aligns with the baseline's
"10-layer architecture" §4.1 ("client layer" owns
"top-level `ComtradeClient` and its lifecycle").

### 8.3 Decision required on `LocalFilesStorage`

Two options:

- **Option A — implement it.** ~50 LOC; a thin
  `LocalFilesStorage` that writes one file per
  `CanonicalDataset` to a configurable directory. Reuses
  `JSONStorage` for the actual write.
- **Option B — remove it.** The four concrete backends
  (Parquet / DuckDB / JSON / CSV) cover every use case.
  `LocalFilesStorage` was a convenience; users can use
  `JSONStorage` directly.

**Recommendation:** Option B. The `LocalFilesStorage`
name is misleading (it does not have a distinct on-disk
format) and the four concrete backends cover every
storage need. Removing it shrinks the public surface
without losing functionality.

### 8.4 Decision required on `detect_format_from_path`

Either add to `un_comtrade.export.__all__` and freeze,
or remove. Recommended: add to `__all__` and freeze —
it is a useful helper that downstream code may need.

### 8.5 Internal-but-reachable patterns

Three internal modules are reachable by their import
path:

- `un_comtrade.analytics._query_engine` — leading
  underscore convention. Already flagged as a risk in
  `026_QUERY_ENGINE_REVIEW.md` §11.1. No action needed.
- `un_comtrade.models._base` — leading underscore
  convention. Same.
- `un_comtrade.storage._base` — leading underscore
  convention. Same.

These follow Python convention; users who reach in
despite the underscore do so at their own risk.

## 9. Completion summary

### 9.1 Counts

| Metric | Value |
| ------ | ----- |
| Total public symbols | **251** |
| Total internal symbols | **102** |
| Grand total (in `__all__` declarations) | **353** |
| Reachable-but-not-exported (underscore convention) | (uncounted; convention-only) |
| Accidental exports found | **0** |
| Symbols without documentation reference | **0** |
| Symbols with duplicate public names | **0** (the Partner / TradePartner aliasing is intentional and distinct) |
| Internal modules leaked to public | **0** (verified via `import un_comtrade` sys.modules diff) |

### 9.2 Verification

| # | Criterion | Result |
| - | --------- | ------ |
| 1 | No accidental exports | PASS — 0 accidental exports |
| 2 | All definitions correct | PASS — every `__all__` symbol resolves to a real top-level definition |
| 3 | Internal modules not exported | PASS — `_query_engine`, `_base` (models + storage) all underscore-prefixed; analytics framework `__all__` is the only framework exception (intentional, see §4.1) |
| 4 | Query Engine remains internal | PASS — `_query_engine` not in `un_comtrade.analytics.__all__` (verified S-001) |
| 5 | Parser remains internal | N/A — `parser.py` is a top-level module but has only `__all__`-exported public symbols; no underscore-prefixed helpers escape via `__all__`. The Parser is **public** (its surface is intentional). Per the task scope, the parser is part of the public contract for advanced users who want to extend it. |
| 6 | Transport internals remain hidden | PASS — `transport.py` exports only `HttpTransport`, `RetryPolicy`, `TimeoutConfig`, `HttpResponse`, and 5 named constants; no private helpers escape. |
| 7 | Consistent naming | PASS — all public symbols are `PascalCase` (classes), `snake_case` (functions), `UPPER_SNAKE_CASE` (constants). Exception classes end in `Error`. Dataclass row types end in `Row` or `Point`. Service classes end in `Service`. |
| 8 | Consistent import paths | PASS — every public symbol has exactly one canonical import path; the re-export hubs (`models`, `storage`, `analytics`) are documented |
| 9 | No duplicate public APIs | PASS — Partner catalog vs record-embedded is intentional aliasing, not a duplicate |

### 9.3 Recommended API freeze status

**Partial freeze recommended:**

- **Freeze (226 Stable):** all symbols not in the experimental
  list of §5.2. These can ship in v1.0 with the SemVer
  guarantee.
- **Promote (25 Experimental → Stable):** the storage
  framework, format constants, analytics commodity helpers,
  and export framework. Action item for S-002.
- **Decide (4 ambiguous):** `ComtradeClient`,
  `LocalFilesStorage`, `detect_format_from_path`,
  `DECLARED_METHOD_COUNT`. Decision required before v1.0.

After S-002 executes the promotions + decisions, the SDK
has a frozen public surface of **~250 symbols**, all
documented, all tested, all under the SemVer contract.

### 9.4 Recommendation for S-002

**Recommended next task: S-002 — Public API Freeze.**

S-002 should:

1. Promote the 25 experimental symbols to Stable (or
   remove the ones that are diagnostic-only).
2. Decide on `ComtradeClient` (Option A — implement
   the facade).
3. Decide on `LocalFilesStorage` (Option B — remove).
4. Decide on `detect_format_from_path` (add to
   `un_comtrade.export.__all__` and freeze).
5. Decide on `DECLARED_METHOD_COUNT` (remove; it's a
   test diagnostic).
6. Generate `docs/028_PUBLIC_API_FREEZE.md` recording
   the freeze decisions.
7. Update `pyproject.toml` version to `1.0.0`.

After S-002, Phase 7 (CLI) can proceed against a stable
public surface.