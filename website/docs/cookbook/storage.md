---
title: Storage recipes
description: 6 runnable recipes covering ETL pipeline, CSV / Parquet / DuckDB exports, reload, and analytics on stored data.
audience: all
prerequisites: []
related_recipes:
  - RECIPE-031
  - RECIPE-032
  - RECIPE-033
  - RECIPE-034
  - RECIPE-035
  - RECIPE-036
related_api: []
related_guides:
  - guides/python/storage/
  - cookbook/index/
---

# Storage recipes

The storage category covers ETL pipelines into storage, the four
backends (CSV, JSON, Parquet, DuckDB), reload, and analytics on
stored data.

| ID         | Title                                       | Runtime | API key |
| ---------- | ------------------------------------------- | ------- | ------- |
| RECIPE-031 | ETL pipeline                                | 2 – 4 s | no      |
| RECIPE-032 | Export to CSV                               | < 1 s   | no      |
| RECIPE-033 | Export to Parquet                           | < 1 s   | no      |
| RECIPE-034 | Export to DuckDB                            | < 1 s   | no      |
| RECIPE-035 | Reload from storage                         | < 1 s   | no      |
| RECIPE-036 | Analytics on stored data                    | < 1 s   | no      |

## Path

1. **[RECIPE-031][recipe-031]** — *ETL pipeline*. Fetch → export.
2. **[RECIPE-032][recipe-032]** — *Export to CSV*.
3. **[RECIPE-033][recipe-033]** — *Export to Parquet*.
4. **[RECIPE-034][recipe-034]** — *Export to DuckDB*.
5. **[RECIPE-035][recipe-035]** — *Reload from storage*.
6. **[RECIPE-036][recipe-036]** — *Analytics on stored data*.

## Run them all

```bash
for recipe in recipes/storage/*.py; do
    UN_COMTRADE_MOCK=1 python "$recipe"
done
```

## Related Recipes

- **[RECIPE-031][recipe-031]** — *ETL pipeline*.
- **[RECIPE-032][recipe-032]** — *Export to CSV*.
- **[RECIPE-033][recipe-033]** — *Export to Parquet*.
- **[RECIPE-034][recipe-034]** — *Export to DuckDB*.
- **[RECIPE-035][recipe-035]** — *Reload from storage*.
- **[RECIPE-036][recipe-036]** — *Analytics on stored data*.

## Related Guides

- **[Python SDK → Storage][python-storage]** — full Python API
  surface.
- **[CLI → Storage][cli-storage]** — equivalent CLI commands.

## Next steps

- **[CLI recipes][cb-cli]** — drive storage from the terminal.

[recipe-031]: ../../recipes/storage/01_etl_pipeline.py
[recipe-032]: ../../recipes/storage/02_export_csv.py
[recipe-033]: ../../recipes/storage/03_export_parquet.py
[recipe-034]: ../../recipes/storage/04_export_duckdb.py
[recipe-035]: ../../recipes/storage/05_reload_storage.py
[recipe-036]: ../../recipes/storage/06_analytics_on_stored.py
[python-storage]: ../guides/python/storage/
[cli-storage]: ../guides/cli/storage/
[cb-cli]: ../cli/