# Cookbook — `etl/` Category

Recipes that exercise the **`client.etl` facade** —
the ETL pipeline factory that composes `extract`,
`transform`, and `load` stages (per
`011_ETL_SPECIFICATION.md`).

The ETL layer is the **orchestration** layer between
the trade service (which produces raw fetches) and
the storage layer (which persists canonical datasets).
Recipes in this category typically:

1. Define a pipeline (extract → transform → load).
2. Run the pipeline against a source.
3. Inspect the pipeline's `PipelineContext` for
   warnings, errors, and metrics.

## Purpose

A consumer should be able to read this category and
understand:

- How to define an ETL pipeline declaratively.
- How to add custom stages.
- How to inspect a pipeline's intermediate state.
- How to recover from a failed pipeline.
- How to chain pipelines.

## SDK services exercised

| Service / symbol                              | Used in planned recipes |
| --------------------------------------------- | ------------------------ |
| `client.etl.pipeline()`                       | ✓                        |
| `client.etl.Pipeline`                         | ✓                        |
| `client.etl.ExtractStage`                     | ✓                        |
| `client.etl.TransformStage`                   | ✓                        |
| `client.etl.LoadStage`                        | ✓                        |
| `client.etl.PipelineContext`                  | ✓                        |
| `client.etl.PipelineResult`                   | ✓                        |
| `un_comtrade.extract.*` (read by the pipeline)| ✓                        |
| `un_comtrade.transform.*` (read by the pipeline) | ✓                     |

## API key policy

| `requires_api_key` | Default for this category |
| ------------------ | ------------------------- |
| `yes`              | ✓ (per `recipes/README.md` §8.2) |

ETL pipelines that read from the upstream API require
a key. A recipe in this category whose pipeline reads
from a local file or an in-memory source declares
`requires_api_key: no` in its frontmatter.

## Estimated runtime band

| `estimated_runtime` | Typical recipes in this category                  |
| ------------------- | ------------------------------------------------- |
| `<10s`              | a pipeline that reads from a local file           |
| `<1min`             | a pipeline that fetches a small trade dataset     |
| `1-10min`           | a pipeline that fetches a multi-year dataset      |
| `10-60min`          | a pipeline that fetches a full-year multi-reporter dataset |

A pipeline's runtime is dominated by its slowest stage;
the `extract` stage (network) is usually the bottleneck.

## Planned recipe roster

| Recipe ID     | Title                                                                  | Difficulty      | Runtime   | API key |
| ------------- | ---------------------------------------------------------------------- | --------------- | --------- | ------- |
| `RECIPE-050`  | Build a minimal extract → transform → load pipeline                     | beginner        | `<10s`    | no      |
| `RECIPE-051`  | Build a pipeline that fetches → normalises → writes to Parquet          | intermediate    | `<1min`   | yes     |
| `RECIPE-052`  | Build a pipeline that fetches → normalises → writes to DuckDB          | intermediate    | `<1min`   | yes     |
| `RECIPE-053`  | Add a custom validation stage to a pipeline                            | intermediate    | `<1min`   | yes     |
| `RECIPE-054`  | Add a custom enrichment stage to a pipeline                            | intermediate    | `<1min`   | yes     |
| `RECIPE-055`  | Inspect the `PipelineContext` (warnings, errors, metrics)              | beginner        | `<1min`   | yes     |
| `RECIPE-056`  | Chain two pipelines (pipeline B reads pipeline A's output)             | intermediate    | `1-10min` | yes     |
| `RECIPE-057`  | Resume a failed pipeline (checkpoint / restart)                        | advanced        | `1-10min` | yes     |
| `RECIPE-058`  | Build a multi-reporter / multi-year batch pipeline                     | advanced        | `10-60min`| yes     |

## Per-recipe cross-references

An `etl/` recipe that needs to explain a behaviour
links to:

- `docs/007_SDK_SPECIFICATION.md` §3.4 (ETL surface)
- `docs/011_ETL_SPECIFICATION.md`
- `docs/009_TRADE_LAYER_SPEC.md` (the extract stage's
  source)
- `docs/012_STORAGE_SPECIFICATION.md` (the load
  stage's sink)
- `docs/023_ETL_REVIEW_REPORT.md` (the design history
  of the ETL layer)

## Category-specific notes

- **Stages are declarative.** A recipe's `run()` body
  defines the pipeline first (`pipeline = ...`), then
  runs it (`pipeline.run(source)`). A recipe that mixes
  definition and execution is rejected.
- **Source and sink are explicit.** Every pipeline
  declares its source (a query, a file, an in-memory
  iterable) and its sink (a Parquet file, a DuckDB
  table, a CSV path). A recipe with an implicit sink
  is rejected.
- **PipelineContext is the contract.** Recipes that
  demonstrate a pipeline (`RECIPE-051`, `RECIPE-052`,
  …) print the `PipelineContext.warnings` and
  `PipelineContext.errors` after the run. A recipe
  that ignores warnings is rejected.
- **Reuse the trade layer.** The `extract` stage of an
  ETL pipeline is a thin wrapper over `client.trade`.
  A recipe that bypasses the trade layer to call the
  upstream API directly is rejected.

## How to add a recipe to this category

1. Choose the next free `RECIPE-NNN` ID from the
   roster above.
2. Copy `recipes/_TEMPLATE.py` to
   `recipes/etl/RECIPE_NNN_<slug>.py`.
3. Implement the body per `recipes/_TEMPLATE.md`. The
   body MUST:
   - Define the pipeline declaratively.
   - Declare the source and the sink explicitly.
   - Print the `PipelineContext.warnings` after the
     run.
4. Update this README's roster table.
5. Submit a pull request.

A recipe that runs a one-off trade query without
defining a pipeline belongs in `trade/`, not here.
A recipe that defines a pipeline and then chains it
with an analytics or storage step belongs in
`end_to_end/`.
