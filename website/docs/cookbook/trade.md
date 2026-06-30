---
title: Trade recipes
description: 5 runnable recipes covering annual / monthly trade flows, balance, and tariffline queries.
audience: all
prerequisites: []
related_recipes:
  - RECIPE-011
  - RECIPE-012
  - RECIPE-013
  - RECIPE-014
  - RECIPE-015
related_api: []
related_guides:
  - guides/python/trade/
  - cookbook/index/
---

# Trade recipes

The trade category covers the canonical trade data fetch: annual /
monthly exports and imports, trade balance, and tariffline queries.
Recipes 011–013 are beginner; 014–015 are intermediate.

| ID         | Title                                       | Runtime  | API key |
| ---------- | ------------------------------------------- | -------- | ------- |
| RECIPE-011 | Fetch India's annual exports                | 1 – 2 s  | no      |
| RECIPE-012 | Fetch India's annual imports                | 1 – 2 s  | no      |
| RECIPE-013 | Fetch world totals                          | 1 – 2 s  | no      |
| RECIPE-014 | Compute the trade balance                   | 2 – 4 s  | no      |
| RECIPE-015 | Tariffline query                            | 2 – 4 s  | yes     |

## Path

1. **[RECIPE-011][recipe-011]** — *Fetch India's annual exports*.
2. **[RECIPE-012][recipe-012]** — *Fetch India's annual imports*.
3. **[RECIPE-013][recipe-013]** — *Fetch world totals*.
4. **[RECIPE-014][recipe-014]** — *Compute the trade balance*.
5. **[RECIPE-015][recipe-015]** — *Tariffline query*.

## Run them all

```bash
for recipe in recipes/trade/*.py; do
    UN_COMTRADE_MOCK=1 python "$recipe"
done
```

## Related Recipes

- **[RECIPE-011][recipe-011]** — *Fetch India's annual exports*.
- **[RECIPE-012][recipe-012]** — *Fetch India's annual imports*.
- **[RECIPE-013][recipe-013]** — *Fetch world totals*.
- **[RECIPE-014][recipe-014]** — *Compute the trade balance*.
- **[RECIPE-015][recipe-015]** — *Tariffline query*.

## Related Guides

- **[Python SDK → Trade][python-trade]** — full Python API
  surface.
- **[CLI → Trade][cli-trade]** — equivalent CLI commands.

## Next steps

- **[Analytics recipes][cb-analytics]** — drill into the fetched
  dataset.

[recipe-011]: ../../recipes/trade/01_exports.py
[recipe-012]: ../../recipes/trade/02_imports.py
[recipe-013]: ../../recipes/trade/03_world_trade.py
[recipe-014]: ../../recipes/trade/04_trade_balance.py
[recipe-015]: ../../recipes/trade/05_tariffline.py
[python-trade]: ../guides/python/trade/
[cli-trade]: ../guides/cli/trade/
[cb-analytics]: ../analytics/