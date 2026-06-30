---
title: ComtradeClient
description: The single public entry point to the SDK — five lazy service facades (metadata, trade, analytics, etl, storage).
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
  - RECIPE-001
  - RECIPE-011
  - RECIPE-021
related_api:
  - un_comtrade.ComtradeClient
related_guides:
  - guides/python/index/
  - getting_started/quick_start/
---

# ComtradeClient

The single public entry point to the SDK. Construct one `ComtradeClient`
per session; it opens five lazy service facades (`metadata`, `trade`,
`analytics`, `etl`, `storage`), each a per-client singleton that
shares the client's transport and configuration.

## API reference

The full reference is generated from the SDK's docstrings via
[mkdocstrings][mkdocstrings]. The page below renders the docstring
verbatim.

::: un_comtrade.ComtradeClient
    options:
      show_source: true
      show_root_heading: true
      show_root_full_path: false
      show_symbol_type_heading: true
      members_order: source
      separate_signature: true
      docstring_section_style: table
      filters: ["!^_"]

The `Configuration` dataclass lives in `un_comtrade.config` and is
documented on the **[Models][api-models]** page.

## Examples

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    countries = client.metadata.get_countries()
    exports = client.trade.get_exports(reporter_code=699, period="2022")
    top = client.analytics.top_partners(exports, by="exports", limit=5)
    client.storage.open("india_exports_2022.parquet").write(exports)
```

## Related Recipes

- **[RECIPE-001][recipe-001]** — *List reporter countries*.
- **[RECIPE-011][recipe-011]** — *Fetch India's annual exports*.
- **[RECIPE-021][recipe-021]** — *Compute a country trade balance*.

## Related Guides

- **[Python SDK → Index][python-index]** — idiomatic patterns.
- **[Quick Start][quick-start]** — first-query walkthrough.

[mkdocstrings]: https://mkdocstrings.github.io/
[python-index]: ../guides/python/
[quick-start]: ../getting_started/quick_start/
[api-models]: models/
[recipe-001]: ../../recipes/metadata/01_list_countries.py
[recipe-011]: ../../recipes/trade/01_exports.py
[recipe-021]: ../../recipes/analytics/country_balance.py