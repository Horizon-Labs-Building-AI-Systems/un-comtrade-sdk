---
title: End-to-end recipes
description: 2 runnable recipes that compose the full pipeline — query, persist, analyse, render a report.
audience: all
prerequisites:
  - guides/python/trade/
  - guides/python/analytics/
  - guides/python/storage/
related_recipes:
  - RECIPE-111
  - RECIPE-113
related_api: []
related_guides:
  - guides/analysts/reporting/
  - cookbook/index/
---

# End-to-end recipes

The end-to-end category covers **full pipelines** that compose every
layer of the SDK: query → persist → analyse → render a report.

| ID         | Title                                       | Runtime | API key |
| ---------- | ------------------------------------------- | ------- | ------- |
| RECIPE-111 | India exports to report                     | 4 – 8 s | no      |
| RECIPE-113 | HS explorer to Markdown                     | 4 – 8 s | no      |

## Path

1. **[RECIPE-111][recipe-111]** — *India exports to report*.
   Fetch India's 2022 exports, persist to Parquet, drill into the
   top-10 partners and HS chapters, render a Markdown report.
2. **[RECIPE-113][recipe-113]** — *HS explorer to Markdown*.
   Fetch HS-2 trade data for India, group by chapter, render a
   hierarchical Markdown table.

## Run them all

```bash
for recipe in recipes/end_to_end/*.py; do
    UN_COMTRADE_MOCK=1 python "$recipe"
done
```

## Related Recipes

- **[RECIPE-111][recipe-111]** — *India exports to report*.
- **[RECIPE-113][recipe-113]** — *HS explorer to Markdown*.

## Related Guides

- **[Data Analysis → Reporting][reporting]** — the pattern these
  recipes embody.
- **[Python SDK → ETL][python-etl]** — pipeline composition.

## Next steps

- **[Release Notes][release-notes]** — what's shipped per version.

[recipe-111]: ../../recipes/end_to_end/01_india_exports_to_report.py
[recipe-113]: ../../recipes/end_to_end/02_hs_explorer_to_markdown.py
[reporting]: ../guides/analysts/reporting/
[python-etl]: ../guides/python/etl/
[release-notes]: ../release_notes/