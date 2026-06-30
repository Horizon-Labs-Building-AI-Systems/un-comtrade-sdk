---
title: Metadata recipes
description: 5 runnable recipes covering country, partner, HS-code, and unit catalogues; cache refresh.
audience: all
prerequisites: []
related_recipes:
  - RECIPE-001
  - RECIPE-002
  - RECIPE-003
  - RECIPE-004
  - RECIPE-005
related_api: []
related_guides:
  - guides/python/metadata/
  - cookbook/index/
---

# Metadata recipes

The metadata category covers the **reference catalogues**: countries,
partners, HS codes, units. Every recipe in this category is a
**beginner** recipe that works without an API key.

| ID         | Title                                       | Runtime | API key |
| ---------- | ------------------------------------------- | ------- | ------- |
| RECIPE-001 | List reporter countries                     | < 1 s   | no      |
| RECIPE-002 | List partner countries                      | < 1 s   | no      |
| RECIPE-003 | List HS codes at a level                    | < 1 s   | no      |
| RECIPE-004 | Search HS codes by description              | < 1 s   | no      |
| RECIPE-005 | Refresh metadata catalogues                 | ~ 5 s   | no      |

## Path

1. **[RECIPE-001][recipe-001]** — *List reporter countries*. The
   simplest possible recipe; verify your install with this one.
2. **[RECIPE-002][recipe-002]** — *List partner countries*.
3. **[RECIPE-003][recipe-003]** — *List HS codes at a level*.
4. **[RECIPE-004][recipe-004]** — *Search HS codes by description*.
5. **[RECIPE-005][recipe-005]** — *Refresh metadata catalogues*.

## Run them all

```bash
for recipe in recipes/metadata/*.py; do
    UN_COMTRADE_MOCK=1 python "$recipe"
done
```

## Related Recipes

- **[RECIPE-001][recipe-001]** — *List reporter countries*.
- **[RECIPE-002][recipe-002]** — *List partner countries*.
- **[RECIPE-003][recipe-003]** — *List HS codes at a level*.
- **[RECIPE-004][recipe-004]** — *Search HS codes by description*.
- **[RECIPE-005][recipe-005]** — *Refresh metadata catalogues*.

## Related Guides

- **[Python SDK → Metadata][python-metadata]** — full Python API
  surface.
- **[CLI → Metadata][cli-metadata]** — equivalent CLI commands.

## Next steps

- **[Trade recipes][cb-trade]** — apply the catalogue to a real
  trade query.

[recipe-001]: ../../recipes/metadata/01_list_countries.py
[recipe-002]: ../../recipes/metadata/02_list_partners.py
[recipe-003]: ../../recipes/metadata/03_list_hs_codes.py
[recipe-004]: ../../recipes/metadata/04_search_hs.py
[recipe-005]: ../../recipes/metadata/05_refresh_metadata.py
[python-metadata]: ../guides/python/metadata/
[cli-metadata]: ../guides/cli/metadata/
[cb-trade]: ../trade/