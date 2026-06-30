---
title: Cookbook
description: 29 runnable recipes grouped by category — metadata, trade, analytics, storage, CLI, end-to-end.
audience: all
prerequisites: []
related_recipes:
  - RECIPE-001
  - RECIPE-011
  - RECIPE-021
  - RECIPE-091
related_api: []
related_guides:
  - cookbook/metadata/
  - cookbook/trade/
  - cookbook/analytics/
  - cookbook/storage/
  - cookbook/cli/
  - cookbook/end_to_end/
---

# Cookbook

The Cookbook is the **executable source of runnable examples** for
the SDK. Every recipe is a self-contained Python file in `recipes/`
with a matching regression test in `tests/test_recipes_*.py`. Recipes
are organised by category:

| Category | Recipes | Difficulty range |
| -------- | ------: | ---------------- |
| **[Metadata][cb-metadata]** | 5 | beginner |
| **[Trade][cb-trade]** | 5 | beginner |
| **[Analytics][cb-analytics]** | 5 | beginner – intermediate |
| **[Storage][cb-storage]** | 6 | beginner – intermediate |
| **[CLI][cb-cli]** | 6 | beginner – intermediate |
| **[End-to-end][cb-end-to-end]** | 2 | intermediate |

The website **does not duplicate** recipe content. Each category
page links to the recipe files in `recipes/<category>/<file>.py`
and surfaces the recipe's frontmatter (title, difficulty, runtime,
API-key flag) as a card.

## Path

1. **[Metadata][cb-metadata]** — country / partner / HS code /
   unit catalogues. No API key required.
2. **[Trade][cb-trade]** — annual / monthly flows, balance,
   tariffline. Requires `UN_COMTRADE_KEY` for the authenticated
   endpoints.
3. **[Analytics][cb-analytics]** — country, partner, commodity,
   time-series, balance.
4. **[Storage][cb-storage]** — ETL pipeline, CSV / Parquet / DuckDB
   exports, reload, analytics on stored data.
5. **[CLI][cb-cli]** — drive every command from the terminal.
6. **[End-to-end][cb-end-to-end]** — full pipelines from query to
   report.

## Run a recipe

Each recipe is a single Python file:

```bash
python recipes/metadata/01_list_countries.py
```

Or with mock mode (no network):

```bash
UN_COMTRADE_MOCK=1 python recipes/metadata/01_list_countries.py
```

The regression tests live in `tests/test_recipes_verification.py`
plus per-category modules; they enforce the recipe contract (no
private imports, deterministic output, mock-mode execution).

## Related API

- [`un_comtrade.ComtradeClient`][api-client] — the single public
  entry point used by every recipe.

## Related Guides

- **[Getting Started][getting-started]** — install the SDK.
- **[Python SDK → Trade][python-trade]** — the most common recipe
  family.

## Next steps

- **[Metadata][cb-metadata]** — start with the simplest recipe
  (RECIPE-001).
- **[End-to-end][cb-end-to-end]** — full pipelines from query to
  report.

[cb-metadata]: metadata/
[cb-trade]: trade/
[cb-analytics]: analytics/
[cb-storage]: storage/
[cb-cli]: cli/
[cb-end-to-end]: end_to_end/
[getting-started]: ../getting_started/
[python-trade]: ../guides/python/trade/
[api-client]: ../api/client/