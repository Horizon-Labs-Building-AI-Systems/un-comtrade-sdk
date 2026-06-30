---
title: ETL via the CLI
description: Compose ETL pipelines from the terminal; chain stages (fetch, transform, export) without writing Python.
audience: cli
prerequisites:
  - guides/cli/trade/
  - guides/cli/storage/
related_recipes:
  - RECIPE-100
related_api: []
related_guides:
  - guides/cli/trade/
  - guides/cli/storage/
---

# ETL via the CLI

The `etl` command runs ETL pipelines composed of stages (fetch,
transform, filter, aggregate, export). Pipelines are declared
inline as a comma-separated list of stage names.

## Purpose

This page covers the `etl` sub-subcommands, their flags, and
common pipeline shapes.

## Prerequisites

- `un-comtrade-sdk` installed.
- The `un-comtrade` script on your `PATH`.

## Walkthrough

### Run a fetch + export pipeline

```bash
un-comtrade etl run \
    --pipeline india_exports \
    --stages fetch,export \
    --reporter 699 --period 2022 --partner 0 \
    --out india_exports_2022.parquet
```

### Fetch + filter + export

```bash
un-comtrade etl run \
    --pipeline india_top5 \
    --stages fetch,filter,export \
    --reporter 699 --period 2022 --partner 0 \
    --filter "primary_value > 1e9" \
    --out india_top5.parquet
```

### Fetch + transform + export

```bash
un-comtrade etl run \
    --pipeline india_normalised \
    --stages fetch,transform,export \
    --reporter 699 --period 2022 --partner 0 \
    --transform-script "lambda r: r if r.flow_code == 'X' else None" \
    --out india_exports_only.parquet
```

### Validate a pipeline (dry run)

```bash
un-comtrade etl validate --pipeline india_exports --stages fetch,export
```

Validates the stage graph and the parameter set without executing
any stage.

## Examples

A full multi-year rollup:

```bash
un-comtrade etl run \
    --pipeline india_history \
    --stages fetch,export \
    --reporter 699 --period 2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022 \
    --partner 0 \
    --out india_history.parquet

un-comtrade analytics top-partners \
    --input india_history.parquet \
    --by exports --limit 10 \
    --output-format markdown > report.md
```

A composite pipeline that filters, aggregates, and exports:

```bash
un-comtrade etl run \
    --pipeline india_top_commodities \
    --stages fetch,filter,aggregate,export \
    --reporter 699 --period 2022 --partner 0 \
    --filter "primary_value > 5e8" \
    --aggregate-by hs_code \
    --out india_top_commodities.parquet
```

## Related Recipes

- **[RECIPE-100][recipe-100]** — *Drive ETL from the CLI*.

## Related Guides

- **[CLI → Trade][cli-trade]** — the `fetch` stage.
- **[CLI → Storage][cli-storage]** — the `export` stage.
- **[Python SDK → ETL][python-etl]** — equivalent Python API.

## Next steps

- **[Python SDK → ETL][python-etl]** — full Python pipeline
  composition.

[cli-trade]: ../trade/
[cli-storage]: ../storage/
[python-etl]: ../../python/etl/
[recipe-100]: ../../../../recipes/cli/05_etl_cli.py