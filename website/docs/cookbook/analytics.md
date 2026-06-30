---
title: Analytics recipes
description: 5 runnable recipes covering country, partner, commodity, and time-series analytics.
audience: all
prerequisites: []
related_recipes:
  - RECIPE-021
  - RECIPE-022
  - RECIPE-023
  - RECIPE-024
  - RECIPE-025
related_api: []
related_guides:
  - guides/python/analytics/
  - cookbook/index/
---

# Analytics recipes

The analytics category covers typed, frozen, Decimal-safe analytics
functions on top of `CanonicalDataset`.

| ID         | Title                                       | Runtime  | API key |
| ---------- | ------------------------------------------- | -------- | ------- |
| RECIPE-021 | Compute a country trade balance             | < 1 s    | no      |
| RECIPE-022 | Top commodities                             | < 1 s    | no      |
| RECIPE-023 | Partner analysis                            | < 1 s    | no      |
| RECIPE-024 | Country comparison                          | < 1 s    | no      |
| RECIPE-025 | Trend analysis                              | < 1 s    | no      |

## Path

1. **[RECIPE-021][recipe-021]** — *Compute a country trade balance*.
2. **[RECIPE-022][recipe-022]** — *Top commodities*.
3. **[RECIPE-023][recipe-023]** — *Partner analysis*.
4. **[RECIPE-024][recipe-024]** — *Country comparison*.
5. **[RECIPE-025][recipe-025]** — *Trend analysis*.

## Run them all

```bash
for recipe in recipes/analytics/*.py; do
    UN_COMTRADE_MOCK=1 python "$recipe"
done
```

## Related Recipes

- **[RECIPE-021][recipe-021]** — *Compute a country trade balance*.
- **[RECIPE-022][recipe-022]** — *Top commodities*.
- **[RECIPE-023][recipe-023]** — *Partner analysis*.
- **[RECIPE-024][recipe-024]** — *Country comparison*.
- **[RECIPE-025][recipe-025]** — *Trend analysis*.

## Related Guides

- **[Python SDK → Analytics][python-analytics]** — full Python API
  surface.
- **[CLI → Analytics][cli-analytics]** — equivalent CLI commands.

## Next steps

- **[Storage recipes][cb-storage]** — persist analytics output.

[recipe-021]: ../../recipes/analytics/country_balance.py
[recipe-022]: ../../recipes/analytics/top_commodities.py
[recipe-023]: ../../recipes/analytics/partner_analysis.py
[recipe-024]: ../../recipes/analytics/country_comparison.py
[recipe-025]: ../../recipes/analytics/trend_analysis.py
[python-analytics]: ../guides/python/analytics/
[cli-analytics]: ../guides/cli/analytics/
[cb-storage]: ../storage/