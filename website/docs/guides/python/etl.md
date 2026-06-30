---
title: ETL in Python
description: Compose pipelines of stages (fetch → parse → transform → export) with shared configuration injection.
audience: python
prerequisites:
  - guides/python/trade/
  - guides/python/storage/
related_recipes:
  - RECIPE-031
  - RECIPE-111
related_api:
  - un_comtrade.ComtradeClient
  - un_comtrade.client.ComtradeClient.etl
related_guides:
  - guides/python/trade/
  - guides/python/storage/
---

# ETL

The ETL layer composes **pipelines of stages** (fetch → parse →
transform → export) with shared configuration injection. Pipelines
are declared as a list of stage definitions; the SDK executes them
sequentially with structured error propagation and per-stage
instrumentation.

## Purpose

This page covers:

1. The `ETLFacade` interface.
2. Pipeline composition.
3. Stage kinds and their parameters.
4. Configuration injection across stages.

## Prerequisites

- `un-comtrade-sdk` installed.
- A `ComtradeClient` instantiated.

## Walkthrough

### Build a pipeline

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    pipeline = client.etl.pipeline(
        name="india_exports_2022",
        stages=[
            ("fetch", {"reporter_code": 699, "period": "2022"}),
            ("export", {"path": "india_exports_2022.parquet"}),
        ],
    )
    pipeline.run()
```

The pipeline runs the stages in order. The `fetch` stage calls the
trade facade; the `export` stage calls the storage facade.

### Stage kinds

| Kind        | Purpose                                          | Required params                |
| ----------- | ------------------------------------------------ | ------------------------------ |
| `fetch`     | Run a trade query.                               | `reporter_code`, `period`      |
| `transform` | Apply a function to every record.                | `fn`                           |
| `filter`    | Drop records that don't match a predicate.       | `predicate`                    |
| `aggregate` | Apply an aggregation function.                   | `field`, `aggregation`         |
| `export`    | Persist to a storage backend.                    | `path`                         |
| `storage`   | Custom storage-stage handler.                    | (custom)                       |

### Custom transformation

```python
pipeline = client.etl.pipeline(
    name="india_top_partners",
    stages=[
        ("fetch", {"reporter_code": 699, "period": "2022"}),
        ("transform", {"fn": lambda r: r if r.partner_code != 0 else None}),
        ("export", {"path": "india_top_partners.parquet"}),
    ],
)
```

### Configuration injection

The pipeline receives the client's configuration at construction:

```python
from un_comtrade import ComtradeClient
from un_comtrade.config import Configuration

config = Configuration(cache_dir="/srv/un_comtrade/cache")

with ComtradeClient(config) as client:
    pipeline = client.etl.pipeline(
        name="audit",
        stages=[("fetch", {"reporter_code": 699, "period": "2022"})],
    )
    pipeline.run()
```

Every stage uses the client's configuration; no per-stage
configuration is required.

### Error propagation

A failure in any stage halts the pipeline and raises
`ETLPipelineError`:

```python
from un_comtrade.exceptions import ETLPipelineError

try:
    pipeline.run()
except ETLPipelineError as exc:
    print(f"Pipeline failed at stage '{exc.stage_name}': {exc}")
```

## Examples

A full fetch → filter → aggregate → export pipeline:

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    pipeline = client.etl.pipeline(
        name="india_top5_partners",
        stages=[
            ("fetch", {"reporter_code": 699, "period": "2022"}),
            ("aggregate", {"field": "primary_value", "aggregation": "sum"}),
            ("export", {"path": "india_top5_partners.parquet"}),
        ],
    )
    pipeline.run()
```

## Related Recipes

- **[RECIPE-031][recipe-031]** — *ETL pipeline*.
- **[RECIPE-111][recipe-111]** — *India exports to report*.

## Related API

- [`ComtradeClient.etl`][api-etl] — the ETL facade.
- [`un_comtrade.etl.ETLFacade`][api-etl-module] — the public ETL
  facade class.

## Related Guides

- **[Trade][python-trade]** — the `fetch` stage.
- **[Storage][python-storage]** — the `export` stage.

## Next steps

- **[Storage][python-storage]** — round-trip the output.
- **[Cookbook → ETL recipes][cookbook-etl]** — full executable
  forms.

[python-trade]: ../trade/
[python-storage]: ../storage/
[cookbook-etl]: ../../cookbook/end_to_end/
[recipe-031]: ../../../recipes/storage/01_etl_pipeline.py
[recipe-111]: ../../../recipes/end_to_end/01_india_exports_to_report.py
[api-etl]: ../../api/client/
[api-etl-module]: ../../api/etl/