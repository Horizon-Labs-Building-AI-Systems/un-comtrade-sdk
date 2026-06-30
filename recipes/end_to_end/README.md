# Cookbook — `end_to_end/` Category

Recipes that compose **two or more SDK services** into
a single end-to-end flow. The dominant flow is:

```
client.trade  →  un_comtrade.etl  →  un_comtrade.storage  →  un_comtrade.analytics
   (fetch)         (orchestrate)        (persist)                (analyse)
```

Recipes in this category are the **integration tests**
of the Cookbook. They demonstrate how the pieces fit
together, and they serve as a smoke test for the
SDK's cross-service contracts.

## Purpose

A consumer should be able to read this category and
understand:

- How to chain a trade fetch with a storage write.
- How to chain a storage read with an analytics run.
- How to chain a fetch with an ETL pipeline with a
  storage write with an analytics run.
- How to build a reproducible batch job (one script
  that does the whole thing).
- How to handle failures in a multi-stage flow.

## SDK services exercised

`end_to_end/` recipes exercise **at least two** of:

- `client.metadata` (typically to resolve names)
- `client.trade` (typically to fetch data)
- `client.etl` (typically to orchestrate)
- `client.storage` (typically to persist)
- `client.analytics` (typically to analyse)

A recipe in this category MUST declare, in its
frontmatter, the list of services it composes.

## API key policy

| `requires_api_key` | Default for this category |
| ------------------ | ------------------------- |
| `yes`              | ✓ when the recipe composes `client.trade` |
| `no`               | ✓ otherwise (rare)        |

The default is `yes` because most `end_to_end/`
recipes fetch trade data. A recipe that composes only
`client.storage` and `client.analytics` (e.g. read
from a fixture, run an analytics engine, write
results) declares `requires_api_key: no`.

## Estimated runtime band

| `estimated_runtime` | Typical recipes in this category                  |
| ------------------- | ------------------------------------------------- |
| `<1min`             | one fetch + one storage write + one analytics run |
| `1-10min`           | multi-year or multi-reporter flows                |
| `10-60min`          | full multi-stage batch jobs                       |

The runtime is the sum of the per-stage runtimes plus
a small overhead for I/O. Recipes that compose a
multi-year fetch with an analytics run are typically
in the `1-10min` band.

## Shipped recipe roster (CB-007 batch 1)

| Recipe ID     | File                                  | Title                                                                | Difficulty      | Runtime   | API key | Services composed                              |
| ------------- | ------------------------------------- | -------------------------------------------------------------------- | --------------- | --------- | ------- | ---------------------------------------------- |
| `RECIPE-111`  | `01_india_exports_to_report.py`       | India exports — fetch, normalise, store, analyse, report             | intermediate    | `1-10min` | yes     | trade, etl, storage, analytics                 |
| `RECIPE-113`  | `02_hs_explorer_to_markdown.py`       | HS code explorer — search, fetch, compare, summarise to Markdown     | advanced        | `1-10min` | yes     | metadata, trade, etl, analytics                |

These are the two "real-world" workflows most
analysts will reach for first:

- **RECIPE-111** answers *"what does India export, who are the top partners, what share do they have?"*
- **RECIPE-113** answers *"how much does India export of HS code X to partner A vs. partner B?"*

Both compose **four SDK services** end-to-end,
producing tangible artefacts (DuckDB + CSV + JSON
for RECIPE-111; Markdown for RECIPE-113) that
downstream consumers (data analysts, journalists,
report writers) can pick up directly.

**Coverage of the four Cookbook pillars:**

- **Authentication** — both recipes declare
  `requires_api_key: yes` because they hit the
  live API in `main()`. The `*_pipeline_demo`
  seams accept a synthetic `TradeResponse` (and
  `HSCode` list) so tests run offline.
- **Filtering** — RECIPE-111 filters by reporter
  + period + flow; RECIPE-113 filters by HS code
  subset (the `search_hs` matches).
- **Output formats** — RECIPE-111 emits DuckDB
  + CSV + JSON; RECIPE-113 emits Markdown.
- **Error handling** — both recipes' `main()`
  functions catch the full `ComtradeError`
  hierarchy and map to the documented exit codes.

## Planned recipe roster

The following recipes are planned for future batches
(RECIPE-110, 112, 114-118) and have not yet been
shipped. They cover specialised scenarios
(multi-year partitions, incremental updates,
cross-storage migration, full-CLI pipelines,
failure recovery).

| Recipe ID     | Title                                                                              | Difficulty      | Runtime   | API key | Services composed                       |
| ------------- | ---------------------------------------------------------------------------------- | --------------- | --------- | ------- | --------------------------------------- |
| `RECIPE-110`  | Fetch → write Parquet → read → analytics (one script)                              | intermediate    | `1-10min` | yes     | trade, storage, analytics               |
| `RECIPE-112`  | Multi-year fetch → partitioned Parquet → analytics on a multi-year window          | advanced        | `1-10min` | yes     | trade, storage, analytics               |
| `RECIPE-114`  | Incremental update: fetch only new records, append to an existing dataset          | advanced        | `1-10min` | yes     | trade, storage                          |
| `RECIPE-115`  | Batch: one script that runs analytics on multiple countries' datasets              | advanced        | `10-60min`| yes     | storage, analytics, trade               |
| `RECIPE-116`  | Cross-storage migration: read from Parquet, write to DuckDB                         | intermediate    | `<1min`   | no      | storage                                 |
| `RECIPE-117`  | Full CLI pipeline: chain `un-comtrade` commands in a shell script                  | intermediate    | `1-10min` | yes     | cli (delegates to trade, etl, storage, analytics) |
| `RECIPE-118`  | Failure-recovery pipeline: fetch, partial failure, resume from checkpoint         | advanced        | `1-10min` | yes     | trade, etl, storage                     |

## Per-recipe cross-references

An `end_to_end/` recipe that needs to explain a
behaviour links to:

- All the per-service pages its recipe composes
  (see `metadata/`, `trade/`, `etl/`, `storage/`,
  `analytics/`, `cli/`).
- `docs/003_ARCHITECTURE.md` (the cross-layer
  integration points).
- `docs/030_PERFORMANCE_BASELINE.md` (for recipes
  whose declared band is `1-10min` or higher).

## Category-specific notes

- **Composition is the value.** The point of an
  `end_to_end/` recipe is the **wiring** between
  services. A recipe that does only what a single
  service can do is rejected.
- **Atomicity is per-stage, not per-recipe.** Each
  stage of an `end_to_end/` recipe has its own
  success / failure semantics. A recipe that
  promises "all-or-nothing" atomicity is rejected;
  the SDK's stages are not transactional.
- **Cleanup is mandatory.** A recipe that creates
  temporary files, DuckDB tables, or Parquet shards
  cleans them up on success **and** on failure. A
  recipe that leaks artefacts is rejected.
- **Failure injection is encouraged.** Recipes that
  demonstrate failure recovery (`RECIPE-118`) inject
  a controlled failure (e.g. by passing a malformed
  query to the first stage) and document how the
  pipeline recovers.

## How to add a recipe to this category

1. Choose the next free `RECIPE-NNN` ID from the
   roster above.
2. Copy `recipes/_TEMPLATE.py` to
   `recipes/end_to_end/RECIPE_NNN_<slug>.py`.
3. Implement the body per `recipes/_TEMPLATE.md`.
   The body MUST:
   - Compose at least two SDK services.
   - Declare the composed services in the
     frontmatter (a `composes:` list with one entry
     per service).
   - Set `requires_api_key` based on the recipe's
     network usage.
   - Clean up temporary artefacts on both success
     and failure.
4. Update this README's roster table.
5. Submit a pull request.

A recipe that touches only one SDK service is
rejected at review; it belongs in the relevant
single-service category.
