---
title: StorageRegistry
description: Storage facade — CSV / JSON / Parquet / DuckDB writers and readers; auto-detect from extension.
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
  - RECIPE-031
  - RECIPE-032
  - RECIPE-033
  - RECIPE-034
related_api:
  - un_comtrade.ComtradeClient
related_guides:
  - guides/python/storage/
---

# StorageRegistry

The storage registry exposes the four production backends
(CSV, JSON, Parquet, DuckDB) plus the auto-detect `open(uri)`
convenience method. The backend is picked from the file extension;
the SDK round-trips `CanonicalDataset` byte-for-byte across all
four.

## API reference

The full reference is generated from the SDK's docstrings via
[mkdocstrings][mkdocstrings].

::: un_comtrade.storage.StorageRegistry
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
    client.storage.open("india_exports_2022.parquet").write(exports)
```

## Related Recipes

- **[RECIPE-031][recipe-031]** — *ETL pipeline*.
- **[RECIPE-032][recipe-032]** — *Export to CSV*.
- **[RECIPE-033][recipe-033]** — *Export to Parquet*.
- **[RECIPE-034][recipe-034]** — *Export to DuckDB*.

## Related Guides

- **[Python SDK → Storage][python-storage]** — full Python API
  surface.

[mkdocstrings]: https://mkdocstrings.github.io/
[python-storage]: ../guides/python/storage/
[recipe-031]: ../../recipes/storage/01_etl_pipeline.py
[recipe-032]: ../../recipes/storage/02_export_csv.py
[recipe-033]: ../../recipes/storage/03_export_parquet.py
[recipe-034]: ../../recipes/storage/04_export_duckdb.py