# Cookbook — `analytics/` Category

Recipes that exercise the **`client.analytics` engine**
and the six concrete analytics modules:

- `un_comtrade.analytics.country` (country_summary,
  country_trend, country_ranking, total_exports,
  total_imports)
- `un_comtrade.analytics.partner` (bilateral_summary,
  partner_balance, partner_growth, top_partners)
- `un_comtrade.analytics.commodity` (commodity_ranking,
  commodity_trend, sector_summaries, top_hs_codes)
- `un_comtrade.analytics.timeseries` (annual_trend,
  monthly_trend, growth_rates, rolling_average, cagr)
- `un_comtrade.analytics.balance` (country_balance,
  partner_trade_balance, commodity_balance,
  global_balance)
- `un_comtrade.analytics.compare` (country_vs_country,
  partner_vs_partner, commodity_vs_commodity,
  year_vs_year)

The analytics layer operates **exclusively on a
`CanonicalDataset`**. Recipes in this category are
**read-only** and **network-free** — they do not call
the upstream API; they consume a `CanonicalDataset`
that another recipe (in `trade/` or `end_to_end/`)
has produced.

## Purpose

A consumer should be able to read this category and
understand:

- How to build an `AnalyticsEngine` (filter chain,
  metrics, aggregations).
- How to use the six concrete analytics modules.
- How to combine multiple aggregations in one run.
- How to interpret `AnalysisResult` (metrics,
  aggregations, warnings, errors).
- How to render an `AnalysisResult` as a table
  (Markdown, CSV, Parquet).

## SDK services exercised

| Service / symbol                                            | Used in planned recipes |
| ----------------------------------------------------------- | ------------------------ |
| `un_comtrade.analytics.AnalyticsEngine`                     | ✓                        |
| `un_comtrade.analytics.Filter` (and its pre-built filters)  | ✓                        |
| `un_comtrade.analytics.Metric` (and its pre-built metrics)  | ✓                        |
| `un_comtrade.analytics.Aggregation`                         | ✓                        |
| `un_comtrade.analytics.country.*`                           | ✓                        |
| `un_comtrade.analytics.partner.*`                           | ✓                        |
| `un_comtrade.analytics.commodity.*`                         | ✓                        |
| `un_comtrade.analytics.timeseries.*`                        | ✓                        |
| `un_comtrade.analytics.balance.*`                           | ✓                        |
| `un_comtrade.analytics.compare.*`                           | ✓                        |

## API key policy

| `requires_api_key` | Default for this category |
| ------------------ | ------------------------- |
| depends on the recipe | see per-recipe frontmatter |

The **analytics layer itself** is offline — it operates
on a pre-built ``CanonicalDataset`` and never makes a
network call. The ``*_demo(dataset, ...)`` signature
makes this explicit: the demo takes a dataset, the
caller decides how to build it.

The recipe's ``main()`` function, however, typically
DOES need a key — it fetches the underlying trade
data via ``client.trade`` and builds the dataset. So
the per-recipe ``requires_api_key`` flag reflects the
end-to-end recipe, not just the analytics surface:

- A recipe whose ``main()`` fetches trade data →
  ``requires_api_key: yes``.
- A recipe whose ``main()`` reads a pre-built
  dataset from disk (e.g. via ``client.storage``) →
  ``requires_api_key: no``.

CB-004 ships five recipes whose ``main()``s all
build a dataset inline; they all declare
``requires_api_key: yes``. Future recipes in this
category that consume a pre-built dataset may declare
``requires_api_key: no`` and live alongside the
``end_to_end/`` category as alternative entry points.

## Estimated runtime band

| `estimated_runtime` | Typical recipes in this category                  |
| ------------------- | ------------------------------------------------- |
| `<1s`               | in-memory aggregations on < 10k records          |
| `<10s`              | in-memory aggregations on < 1M records            |
| `<1min`             | aggregations on multi-million-record datasets     |

The dataset size is the dominant factor. Recipes that
operate on a fixture dataset are in `<1s`; recipes that
operate on a real `CanonicalDataset` are in `<10s` or
`<1min`.

## Planned recipe roster

| Recipe ID     | Title                                                                | Difficulty      | Runtime   | API key | Status   | Source file                  |
| ------------- | -------------------------------------------------------------------- | --------------- | --------- | ------- | -------- | ---------------------------- |
| `RECIPE-021`  | Country trade balance (analytics)                                    | beginner        | `<10s`    | yes     | DRAFT    | `country_balance.py`         |
| `RECIPE-022`  | Top commodities by trade value (analytics)                           | beginner        | `<10s`    | yes     | DRAFT    | `top_commodities.py`         |
| `RECIPE-023`  | Partner analysis — top partners + growth (analytics)                 | intermediate    | `<1min`   | yes     | DRAFT    | `partner_analysis.py`        |
| `RECIPE-024`  | Country vs country comparison (analytics)                            | intermediate    | `<1min`   | yes     | DRAFT    | `country_comparison.py`      |
| `RECIPE-025`  | Trade trend analysis with growth + CAGR (analytics)                  | intermediate    | `<1min`   | yes     | DRAFT    | `trend_analysis.py`         |
| `RECIPE-026`  | Build a country summary from a `CanonicalDataset`                    | beginner        | `<1s`     | no      | PROPOSED | —                            |
| `RECIPE-027`  | Compute top-N imported HS chapters                                   | beginner        | `<1s`     | no      | PROPOSED | —                            |
| `RECIPE-028`  | Compute a rolling 12-month average                                  | intermediate    | `<1s`     | no      | PROPOSED | —                            |
| `RECIPE-029`  | Build a sector summary from HS chapter codes                         | intermediate    | `<1s`     | no      | PROPOSED | —                            |
| `RECIPE-030`  | Build an `AnalyticsEngine` with filters, metrics, and aggregations   | intermediate    | `<1s`     | no      | PROPOSED | —                            |

**CB-004 (DRAFT).** Recipes `RECIPE-021` through
`RECIPE-025` are the first batch of analytics
recipes. Every recipe consumes a
``CanonicalDataset`` (per the brief): the
``*_demo(dataset, ...)`` signature is the testable
seam; the ``main()`` builds the dataset from real
trade data via the trade service.

Coverage of the four pillars:

- **Authentication** — each recipe's ``main()``
  reads the key from ``UN_COMTRADE_KEY`` and
  exits with code 4 when missing; the
  ``*_demo()`` functions do not need a key
  (they are offline).
- **Filtering** — recipe 21 filters by reporter;
  recipe 22 by reporter + flow + HS level; recipe
  23 by reporter + flow + partner; recipe 24 by
  reporter pair + flow + breakdown; recipe 25 by
  reporter + flow + period range.
- **Output format** — every recipe prints a
  formatted table to stdout; the recipes return
  stable frozen dataclasses (``CountryBalanceResult``,
  ``TopCommoditiesResult``, …) that decouple the
  public recipe surface from the analytics
  layer's internal types.
- **Error handling** — each recipe wires the
  full CB-001 §7 error-handling contract via
  ``_exit_code_for(exc)``; recipe 25 adds the
  ``--start-year > --end-year`` validation as a
  recipe-side argument check (exit code 2).

The 15-test regression suite
(``tests/test_recipes_analytics.py``) is green.
The on-screen output has been smoke-checked
against the recorded fixtures; the recipes have
NOT been exercised against the live upstream API
in CI.

## Per-recipe cross-references

An `analytics/` recipe that needs to explain a
behaviour links to:

- `docs/007_SDK_SPECIFICATION.md` §3.4 (analytics
  surface)
- `docs/025_ANALYTICS_REVIEW_REPORT.md` (the
  design history of the analytics engine)
- `docs/006_DATA_MODEL.md` (the canonical data model
  that the engine operates on)
- `docs/011_ETL_SPECIFICATION.md` (when the recipe's
  input dataset is produced by an ETL pipeline)

## Category-specific notes

- **The analytics layer is offline; the recipe's
  ``main()`` is not.** The analytics functions
  operate exclusively on a pre-built
  ``CanonicalDataset`` and never call the network.
  The recipe's ``main()``, however, typically
  builds the dataset inline by calling
  ``client.trade``, which DOES touch the network.
  The ``*_demo(dataset, ...)`` signature makes
  the testable seam explicit: the demo function
  is offline, the main function is online.
- **Input dataset is required.** An `analytics/` recipe
  needs a `CanonicalDataset`. The recipe either:
  - Builds one inline via ``client.trade`` (most
    common; ``main()`` does the I/O).
  - Loads one from a file produced by a previous
    ``trade/`` or ``end_to_end/`` recipe.
  - Generates one in-memory from a small built-in
    dataset (acceptable for tutorials).
- **Output is tabular.** Analytics output is rendered
  as a table. Recipes that need a permanent artefact
  write the table to a storage backend
  (`RECIPE-041`).
- **Reuse the engine.** Recipes that demonstrate a
  specific analytics method (`RECIPE-030` …
  `RECIPE-038`) build a fresh `AnalyticsEngine` and
  discard it. Recipes that demonstrate **how** to
  build an engine (`RECIPE-039`) keep the engine in
  scope to show its builder pattern.

## How to add a recipe to this category

1. Choose the next free `RECIPE-NNN` ID from the
   roster above.
2. Copy `recipes/_TEMPLATE.py` to
   `recipes/analytics/RECIPE_NNN_<slug>.py`.
3. Implement the body per `recipes/_TEMPLATE.md`. The
   body MUST:
   - Set `requires_api_key: no` in the frontmatter.
   - Load a `CanonicalDataset` (from file, fixture,
     or in-memory construction).
   - Operate **only** on the dataset; no network
     calls.
4. Update this README's roster table.
5. Submit a pull request.

A recipe that needs a `CanonicalDataset` it cannot
load belongs in `end_to_end/`, not here.
