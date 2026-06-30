---
title: AnalyticsEngine
description: Typed analytics on top of CanonicalDataset — country, partner, commodity, time-series, balance, comparison.
audience: python
prerequisites: []
skips:
  - Purpose
  - Prerequisites
  - Walkthrough
  - Related Recipes
  - Related API
  - Related Guides
  - Next steps
related_recipes:
  - RECIPE-021
  - RECIPE-024
related_api:
  - un_comtrade.ComtradeClient
related_guides:
  - guides/python/analytics/
---

# AnalyticsEngine

The analytics engine exposes typed, frozen, Decimal-safe analytics
functions on top of `CanonicalDataset`. Six submodules cover country,
partner, commodity, time-series, balance, and comparison analytics.

## API reference

The full reference is generated from the SDK's docstrings via
[mkdocstrings][mkdocstrings].

::: un_comtrade.analytics.AnalyticsEngine
    options:
      show_source: true
      show_root_heading: true
      show_root_full_path: false
      show_symbol_type_heading: true
      members_order: source
      separate_signature: true
      docstring_section_style: table
      filters: ["!^_"]

::: un_comtrade.analytics.country
    options:
      show_source: true
      members_order: source
      separate_signature: true
      docstring_section_style: table
      filters: ["!^_"]

::: un_comtrade.analytics.partner
    options:
      show_source: true
      members_order: source
      separate_signature: true
      docstring_section_style: table
      filters: ["!^_"]

::: un_comtrade.analytics.commodity
    options:
      show_source: true
      members_order: source
      separate_signature: true
      docstring_section_style: table
      filters: ["!^_"]

::: un_comtrade.analytics.timeseries
    options:
      show_source: true
      members_order: source
      separate_signature: true
      docstring_section_style: table
      filters: ["!^_"]

::: un_comtrade.analytics.balance
    options:
      show_source: true
      members_order: source
      separate_signature: true
      docstring_section_style: table
      filters: ["!^_"]

::: un_comtrade.analytics.compare
    options:
      show_source: true
      members_order: source
      separate_signature: true
      docstring_section_style: table
      filters: ["!^_"]

## Examples

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    exports = client.trade.get_exports(reporter_code=699, period="2022")
    top = client.analytics.top_partners(exports, by="exports", limit=5)
```

## Related Recipes

- **[RECIPE-021][recipe-021]** — *Compute a country trade balance*.
- **[RECIPE-024][recipe-024]** — *Country comparison*.

## Related Guides

- **[Python SDK → Analytics][python-analytics]** — full Python API
  surface.

[mkdocstrings]: https://mkdocstrings.github.io/
[python-analytics]: ../guides/python/analytics/
[recipe-021]: ../../recipes/analytics/country_balance.py
[recipe-024]: ../../recipes/analytics/country_comparison.py