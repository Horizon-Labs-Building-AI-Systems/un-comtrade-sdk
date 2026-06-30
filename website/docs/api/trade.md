---
title: TradeService
description: Trade data service — annual / monthly flows, tariffline, world totals; auto-paginated; returns a CanonicalDataset.
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
  - RECIPE-011
  - RECIPE-014
  - RECIPE-015
related_api:
  - un_comtrade.ComtradeClient
related_guides:
  - guides/python/trade/
---

# TradeService

The trade service fetches the canonical trade data from the UN
Comtrade API: annual and monthly flows, partner breakdowns, HS-code
filters, and the tariffline endpoint. The service hides pagination
across the upstream API's per-call record cap and returns a single
combined `CanonicalDataset`.

## API reference

The full reference is generated from the SDK's docstrings via
[mkdocstrings][mkdocstrings].

::: un_comtrade.trade.TradeService
    options:
      show_source: true
      show_root_heading: true
      show_root_full_path: false
      show_symbol_type_heading: true
      members_order: source
      separate_signature: true
      docstring_section_style: table
      filters: ["!^_"]

## Examples

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    exports = client.trade.get_exports(reporter_code=699, period="2022")
    print(f"${exports.aggregate_total():,.2f}")
```

## Related Recipes

- **[RECIPE-011][recipe-011]** — *Fetch India's annual exports*.
- **[RECIPE-014][recipe-014]** — *Compute the trade balance*.
- **[RECIPE-015][recipe-015]** — *Tariffline query*.

## Related Guides

- **[Python SDK → Trade][python-trade]** — full Python API
  surface.
- **[CLI → Trade][cli-trade]** — equivalent CLI commands.

[mkdocstrings]: https://mkdocstrings.github.io/
[python-trade]: ../guides/python/trade/
[cli-trade]: ../guides/cli/trade/
[recipe-011]: ../../recipes/trade/01_exports.py
[recipe-014]: ../../recipes/trade/04_trade_balance.py
[recipe-015]: ../../recipes/trade/05_tariffline.py