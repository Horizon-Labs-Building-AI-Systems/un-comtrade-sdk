---
title: Analytics via the CLI
description: Run typed analytics on a stored dataset; pipe output as Markdown tables or JSON.
audience: cli
prerequisites:
  - guides/cli/storage/
  - guides/cli/trade/
related_recipes:
  - RECIPE-099
related_api: []
related_guides:
  - guides/cli/trade/
  - guides/cli/storage/
  - guides/python/analytics/
---

# Analytics via the CLI

The `analytics` command runs typed analytics on a stored dataset
(file path or DuckDB table). Output is the same `tuple` of frozen
dataclasses the Python facade returns — serialised to JSON, CSV,
Markdown, table, or text.

## Purpose

This page covers the `analytics` sub-subcommands, their flags, and
shell-composition patterns.

## Prerequisites

- A stored dataset (CSV, JSON, Parquet, or DuckDB). See
  **[CLI → Storage][cli-storage]** to create one.
- The `un-comtrade` script on your `PATH`.

## Walkthrough

### Top partners

```bash
un-comtrade analytics top-partners \
    --input india_exports_2022.parquet \
    --by exports --limit 5
```

### Top HS codes

```bash
un-comtrade analytics top-hs-codes \
    --input india_exports_2022.parquet \
    --hs-level 2 --limit 10
```

### Global balance

```bash
un-comtrade analytics global-balance \
    --input india_exports_2022.parquet
```

### Country trend

```bash
un-comtrade analytics country-trend \
    --input india_exports_history.parquet \
    --reporter 699 \
    --granularity year
```

### Country comparison

```bash
un-comtrade analytics country-vs-country \
    --inputs india_exports_2022.parquet,china_exports_2022.parquet \
    --labels India,China \
    --breakdown-by commodity
```

### Sector summaries

```bash
un-comtrade analytics sector-summaries \
    --input india_exports_2022.parquet \
    --by exports
```

## Examples

A Markdown report:

```bash
un-comtrade analytics top-partners \
    --input india_exports_2022.parquet \
    --by exports --limit 10 \
    --output-format markdown > report.md
```

Pipe analytics output to `jq`:

```bash
un-comtrade analytics top-partners \
    --input india_exports_2022.parquet \
    --by exports --limit 5 \
    --output-format json \
    | jq -r '.[] | "\(.partner_label): \(.value)"'
```

Drill-down: top partner → their HS codes:

```bash
top_partner=$(un-comtrade analytics top-partners \
    --input india_exports_2022.parquet \
    --by exports --limit 1 \
    --output-format json | jq -r '.[0].partner_code')

un-comtrade trade exports --reporter 699 --period 2022 --partner "$top_partner" \
    --output-format json \
    | un-comtrade analytics top-hs-codes --input - --limit 5
```

## Related Recipes

- **[RECIPE-099][recipe-099]** — *Drive analytics commands from the
  CLI*.

## Related Guides

- **[CLI → Trade][cli-trade]** — produces a dataset.
- **[CLI → Storage][cli-storage]** — persists a dataset.
- **[Python SDK → Analytics][python-analytics]** — equivalent
  Python API.

## Next steps

- **[CLI → Storage][cli-storage]** — round-trip analytics through
  storage.
- **[Python SDK → Analytics][python-analytics]** — full Python API
  surface.

[cli-trade]: ../trade/
[cli-storage]: ../storage/
[python-analytics]: ../../python/analytics/
[recipe-099]: ../../../../recipes/cli/03_analytics_cli.py