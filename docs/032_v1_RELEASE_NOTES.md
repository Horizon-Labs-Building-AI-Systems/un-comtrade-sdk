```
Document ID
032

Title
Release Notes — v1.0.0 / v1.0.1

Version
1.0.1

Status
DRAFT

Created
2026-06-28T22:50:00Z

Last Updated
2026-06-28T23:10:00Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
CHANGELOG.md, TASK_LOG.md, 031_PRODUCTION_READINESS.md

Supersedes
None
```

---

# 1. Release Overview

## 1.1 What is v1.0.0?

`v1.0.0` is the first stable release of the
`un-comtrade-sdk` package. It freezes the public
API surface, completes all six phases of the
implementation roadmap (P1 through P6), and ships
the internal Query Engine (QE) plus the F-001
Storage Read Architecture and F-002 Aggregation
Duplication fixes.

## 1.2 What ships in this release?

- **Phase 1** — Foundation: pyproject.toml,
  `Configuration`, 13-class exception hierarchy,
  `HttpTransport` (with integrated retry,
  timeout, auth middleware), redaction-aware
  logging across 8 categories, `ComtradeClient`
  skeleton, 8+ metadata models, `MetadataService`
  (16/18 catalogue fetchers), `MetadataCache`,
  `MetadataParser`.
- **Phase 2** — Trade layer: 16/18 metadata
  catalogue methods complete; `TradeQuery` +
  `TradeQueryBuilder`; 7 record-embedded trade
  models; `TradeService` (20 methods);
  `TradeParser`; end-to-end T01-T03 + T09-T11.
- **Phase 3** — Trade completion: T04-T08;
  `PaginationEngine`; `BatchDownloader`;
  `AsyncJobsService`; tariffline F01-F02; HS /
  Commodity accepts 2/4/6/8/10 digit codes.
- **Phase 4** — ETL: `ETLPipeline`, three-stage
  Extract / Transform / Export framework; ETL
  Review Report (CHG-0050).
- **Phase 5** — Storage: `Storage` Protocol;
  CSV, JSON, Parquet, DuckDB backends; logical
  partitioning (Hive-style paths); `DatasetUpdater`
  with `UpdateMode` / `DuplicatePolicy`. Storage
  Review Report (`024_STORAGE_REVIEW_REPORT.md`)
  signed off 6/6.
- **Phase 6** — Analytics: framework
  (`AnalyticsEngine`); 7 concrete submodules:
  `country.py`, `partner.py`, `commodity.py`,
  `timeseries.py`, `balance.py`, `compare.py`;
  **35 user-facing analytics functions**; Analytics
  Review Report (`025_ANALYTICS_REVIEW_REPORT.md`)
  signed off 5/5.
- **Phase 6.5 — Internal Query Engine**: `Query`,
  `Predicate` family (8 ops), `Group`,
  `AggregationResult` with sum/count/average/
  minimum/maximum/`summarize`, `SortKey`,
  ordering/windowing. Internal-only (leading
  underscore filename signals internal). QE
  Review Gate (`026_QUERY_ENGINE_REVIEW.md`).
- **F-001 — Storage Read Architecture**: `read()`
  implemented on all 4 concrete backends (CSV,
  JSON, Parquet, DuckDB); `Storage` Protocol now
  declares `read`; deterministic sort preserves
  round-trip equality; Decimal precision preserved
  end-to-end. 13 new tests.
- **F-002 — Eliminate Aggregation Duplication**:
  all 8 hand-rolled per-group Decimal summation
  patterns (`by_X[k] = by_X.get(k, Decimal("0")) + v`)
  replaced with Query-Engine-backed
  `group_by + summarize`. AST-based regression
  guard prevents reintroduction. 2 new tests.

## 1.3 What is NOT in this release?

- **Phase 7 — CLI**: deferred to v1.1.0.
- **v1.0.1 optimisations**: DuckDB bulk-insert
  speedup and `country_vs_country` filter-fusion
  deferred to v1.0.1 (immediately after 1.0.0).
- **12 EXT items** requiring live subscription
  key verification (e.g. async submit endpoint,
  matrix endpoint, balance endpoint live
  payloads) are still pending.

---

# 2. Install / Upgrade

## 2.1 From PyPI (after publish)

```bash
pip install un-comtrade-sdk==1.0.0
```

## 2.2 From source

```bash
git clone <repo>
cd india-impex-analytics
pip install -e .
```

## 2.3 Python compatibility

`>= 3.11, < 3.15` per ADR-0017. Tested on
3.14.3.

## 2.4 Dependencies (runtime)

- `httpx >= 0.27` (ADR-0018)
- `pyarrow >= 14.0` (optional, Parquet backend)
- `duckdb >= 1.0` (optional, DuckDB backend)

CSV / JSON / analytics / ETL / metadata / trade
layers have **zero third-party runtime deps** beyond
`httpx`.

---

# 3. Breaking Changes Since 0.1.0

## 3.1 Hard renames (HIGH-priority)

### R1 — `logging.DEFAULT_LOG_LEVEL` → `LOGGING_DEFAULT_LEVEL`

`un_comtrade.logging.DEFAULT_LOG_LEVEL` (an `int`,
= `logging.WARNING`) collided with
`un_comtrade.config.DEFAULT_LOG_LEVEL` (a `str`,
= `"WARNING"`) in a way that broke introspection
and IDE autocomplete.

**Action taken:** the logging-side name is now
`LOGGING_DEFAULT_LEVEL`. The old name is kept as
a deprecated alias and will be removed in 2.0.

**Migration:**

```python
# Before (0.1.0)
from un_comtrade.logging import DEFAULT_LOG_LEVEL
logger.setLevel(DEFAULT_LOG_LEVEL)  # 30

# After (1.0.0)
from un_comtrade.logging import LOGGING_DEFAULT_LEVEL
logger.setLevel(LOGGING_DEFAULT_LEVEL)  # 30

# Still works (deprecated alias):
from un_comtrade.logging import DEFAULT_LOG_LEVEL  # OK
```

The alias emits no warning yet; a `DeprecationWarning`
will be added in 1.1.0.

## 3.2 Phase 6 to Phase 6.5 internals

The Query Engine (`un_comtrade.analytics._query_engine`)
is an internal package. It has no public re-export
in `un_comtrade.analytics.__all__` and no
re-export in `un_comtrade.__init__`. No public
API surface changed in 1.0.0.

## 3.3 Storage read() addition (non-breaking)

`Storage.read(config) -> CanonicalDataset` is new
in 1.0.0. Existing `write()` callers are unaffected.
The `Storage` Protocol now declares both `write`
and `read`; both are required for concrete
implementations going forward.

---

# 4. New Public API Surface (1.0.0)

## 4.1 Top-level (`un_comtrade`)

- `un_comtrade.__version__` → `"1.0.0"`
- Re-exports: `ComtradeClient`, `Configuration`,
  exception classes, `load_configuration`,
  `get_logger`, `install_redaction`, `RedactingFilter`,
  `MetadataService`, `MetadataCache`, `MetadataParser`,
  `TradeService`, `TradeQuery`, `TradeQueryBuilder`,
  `TradeParser`, `TradeResponse`, `ETLPipeline`,
  `StageSpec`, `PipelineContext`, `PipelineResult`,
  `CanonicalDataset`, `Storage`, `CSVWriter`,
  `JSONWriter`, `ParquetWriter`, `DuckDBWriter`,
  `DatasetUpdater`, `UpdateMode`, `DuplicatePolicy`.

## 4.2 Analytics (`un_comtrade.analytics`)

35 user-facing functions across 6 modules:

- **country** (5): `total_imports`,
  `total_exports`, `country_ranking`,
  `country_summary`, `country_trend`.
- **partner** (4): `top_partners`,
  `partner_growth`, `partner_balance`,
  `bilateral_summary`.
- **commodity** (4): `top_hs_codes`,
  `commodity_ranking`, `commodity_trend`,
  `sector_summaries`.
- **timeseries** (5): `annual_trend`,
  `monthly_trend`, `rolling_average`, `cagr`,
  `growth_rates`.
- **balance** (4): `country_balance`,
  `partner_trade_balance`, `commodity_balance`,
  `global_balance`.
- **compare** (4): `country_vs_country`,
  `year_vs_year`, `commodity_vs_commodity`,
  `partner_vs_partner`.

Plus the `AnalyticsEngine` framework:
`Filter`, `Metric`, `Aggregation`,
`AggregationRow`, `AnalysisContext`,
`AnalysisResult`, `AnalyticsError`, `MetricError`,
`FilterError`, `AggregationError`.

## 4.3 Storage (`un_comtrade.storage`)

- `Storage` Protocol (read + write).
- `CSVWriter` / `JSONWriter` /
  `ParquetWriter` / `DuckDBWriter`.
- `DatasetUpdater` with `UpdateMode` (`APPEND`
  / `MERGE` / `REPLACE`) and `DuplicatePolicy`
  (`KEEP_EXISTING` / `KEEP_INCOMING` / `ERROR`).

---

# 5. Quality Gates

| Gate | Status | Notes |
| ---- | ------ | ----- |
| Test suite | **2787 / 2787 passing** | 105s wall |
| F-001 Storage Read | PASS | 13 new tests |
| F-002 Aggregation Refactor | PASS | 2 new regression tests |
| Public API Audit (`027`) | PASS | 251 public symbols, 0 accidental exports |
| Semantic Version Audit (`028`) | PASS | 14 risks catalogued; 1 hard rename (R1) applied |
| Package Hygiene (`029`) | PASS | 95/100 hygiene, 0 cycles |
| Performance Baseline (`030`) | PASS | 80+ measurements; 1k/5k/20k records |
| Production Readiness (`031`) | PASS | 91.4/100 readiness, 12/12 APPROVED |
| V-001 Independent Audit | PASS | 96.7% compatibility |

---

# 6. Known Limitations

1. **12 EXT items** still need live subscription
   key verification. These are documented in the
   PCR under "External Verification Required"
   and do not block this release.
2. **CSV / JSON read()** performance is O(n) with
   no streaming; very large datasets (≥ 1M records)
   should use Parquet or DuckDB.
3. **DuckDB backend** is single-process per
   dataset; concurrent writers require external
   locking.
4. **Phase 7 CLI** is not yet implemented;
   programmatic use only.

---

# 7. Verifying the Release

## 7.1 Test suite

```bash
python -m pytest -q
# Expected: 2787 passed
```

## 7.2 Import smoke test

```python
import un_comtrade
print(un_comtrade.__version__)  # 1.0.0

from un_comtrade.analytics import (
    country_balance, partner_trade_balance,
    commodity_balance, global_balance,
    country_vs_country, cagr,
)
from un_comtrade.storage import (
    Storage, CSVWriter, JSONWriter,
    ParquetWriter, DuckDBWriter,
    DatasetUpdater,
)

# Storage round-trip
import tempfile, pathlib
from un_comtrade.transform import CanonicalDataset
from un_comtrade.models.trade import TradeRecord

# ... build a dataset, write it, read it back ...
```

## 7.3 F-002 regression guard

```bash
python -m pytest tests/test_f002_no_handrolled_aggregation.py -v
# Expected: 2 passed (AST-based regression guard)
```

---

# 8. What's Next

## 8.1 v1.0.1 (immediate patch release)

Performance optimisations, no public API changes:

- DuckDB bulk-insert speedup (~100× via
  `pyarrow`-style bulk ingestion; avoids per-row
  INSERT statements).
- `country_vs_country` filter-fusion speedup
  (~5–10×; fuses two record filters into a single
  Query pipeline pass).

## 8.2 v1.1.0 (next minor)

- `DeprecationWarning` on `DEFAULT_LOG_LEVEL`
  alias import.
- Phase 7 CLI (`un-comtrade` console script).
- `tools/_f002_scan.py` ships as
  `un-comtrade-doctor` lint command.

## 8.3 v1.2.0 and beyond

- Async (`asyncio`) TradeService variants.
- Streaming CSV/JSON read.
- Multi-process DuckDB writer via
  `external_lock=True`.

---

# 9. Acknowledgements

v1.0.0 ships ~14 weeks of design + implementation
work documented across:

- 31 numbered docs (`000`–`031`)
- 36 ADRs (`ADR-0001`..`ADR-0036`)
- 78 CHG entries (`CHG-0001`..`CHG-0078`)
- 88 TASK entries (`TASK-001`..`TASK-088`)
- 132 CLAR entries (`CLAR-001`..`CLAR-132`)
- 9 verification / audit / review reports

Architectural baseline frozen at 36 ADRs.
Production readiness score: 91.4 / 100.

---

# 11. v1.0.1 — Performance Patch

## 11.1 What changed?

`v1.0.1` is a pure-performance release. **No
public API changes, no breaking changes, no
deprecations.**

### 11.1.1 DuckDB bulk-insert speedup (~100×)

`DuckDBWriter.store(...)` now bulk-inserts via a
`pyarrow.Table` registered into DuckDB and selected
via `CREATE TABLE AS SELECT`. Compared to the
v1.0.0 `executemany` path:

- 5000 rows × 49 cols on local NVMe:
  `executemany` ≈ 8–12s, `arrow CTAS` ≈ 0.1s.
- ~100× faster on the common path.
- `Decimal(38, 18)` precision preserved.
- 3 new tests in `tests/test_duckdb.py::TestDuckDBBulkInsertV101`.

### 11.1.2 `country_vs_country` filter-fusion speedup (~5–10×)

The comparison functions (`country_vs_country`,
`partner_vs_partner`, `year_vs_year`,
`commodity_vs_commodity`, `partner_vs_partner`)
now detect when ALL sides share the same filter
set except for one varying "axis" field, and
fuse them into a single Query that filters
`axis_field IN (...)` and groups by
`(axis_field, breakdown)`.

- Generic axis detection (not just
  `reporter_code`).
- Falls back to the per-side path when fusion is
  unsafe (≥2 varying fields).
- 3 new tests in
  `tests/test_comparative_analytics.py::TestV101FilterFusion`.

### 11.1.3 Test count

2787 (v1.0.0) → 2793 (v1.0.1). +6 tests, all
passing.

## 11.2 Migration from 1.0.0

```bash
pip install --upgrade un-comtrade-sdk==1.0.1
```

No code changes required. Existing code that worked
on 1.0.0 will work identically on 1.0.1, just
faster.

## 11.3 Limitations / known issues

- `pyarrow` is now a required dependency for the
  DuckDB fast path. The legacy `executemany`
  fallback is still used when `pyarrow` is not
  installed.
- Filter-fusion only kicks in when ALL sides share
  the same filter set except for ONE varying axis
  field. Multi-axis comparisons (≥2 varying
  fields) fall back to the per-side path.
- The 5–10× speedup is measured on small- to
  medium-sized datasets (≤100k records). Larger
  datasets benefit proportionally.

---

# 12. End of document