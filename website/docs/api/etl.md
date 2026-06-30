---
title: ETLFacade
description: Pipeline orchestration — fetch → transform → filter → aggregate → export. Configured via stage definitions.
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
  - RECIPE-111
related_api:
  - un_comtrade.ComtradeClient
related_guides:
  - guides/python/etl/
---

# ETLFacade

The ETL facade composes pipelines of stages (fetch, transform,
filter, aggregate, export) with shared configuration injection.
Pipelines are declared as a list of stage definitions; the SDK
executes them sequentially with structured error propagation.

## API reference

The full reference is generated from the SDK's docstrings via
[mkdocstrings][mkdocstrings].

::: un_comtrade.etl.ETLFacade
    options:
      show_source: true
      show_root_heading: true
      show_root_full_path: false
      show_symbol_type_heading: true
      members_order: source
      separate_signature: true
      docstring_section_style: table
      filters: ["!^_"]

::: un_comtrade.etl.ETLPipeline
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
    pipeline = client.etl.pipeline(
        name="india_exports",
        stages=[
            ("fetch", {"reporter_code": 699, "period": "2022"}),
            ("export", {"path": "india_exports.parquet"}),
        ],
    )
    pipeline.run()
```

## Related Recipes

- **[RECIPE-031][recipe-031]** — *ETL pipeline*.
- **[RECIPE-111][recipe-111]** — *India exports to report*.

## Related Guides

- **[Python SDK → ETL][python-etl]** — full Python API surface.

[mkdocstrings]: https://mkdocstrings.github.io/
[python-etl]: ../guides/python/etl/
[recipe-031]: ../../recipes/storage/01_etl_pipeline.py
[recipe-111]: ../../recipes/end_to_end/01_india_exports_to_report.py