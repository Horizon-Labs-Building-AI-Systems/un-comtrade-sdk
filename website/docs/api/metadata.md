---
title: MetadataService
description: Reference catalogue service — countries, partners, HS codes, units. Cached on first use; refreshable on demand.
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
  - RECIPE-005
related_api:
  - un_comtrade.ComtradeClient
related_guides:
  - guides/python/metadata/
---

# MetadataService

The metadata service exposes the UN Comtrade reference catalogues.
Every accessor fetches a typed list of frozen dataclasses, caches
the result on first use, and refreshes on a configurable cadence.

## API reference

The full reference is generated from the SDK's docstrings via
[mkdocstrings][mkdocstrings].

::: un_comtrade.metadata.MetadataService
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
    countries = client.metadata.get_countries()
    india = client.metadata.get_country(699)
    hs2 = client.metadata.get_hs_codes(level=2)
```

## Related Recipes

- **[RECIPE-001][recipe-001]** — *List reporter countries*.
- **[RECIPE-005][recipe-005]** — *Refresh metadata catalogues*.

## Related Guides

- **[Python SDK → Metadata][python-metadata]** — full Python API
  surface.
- **[CLI → Metadata][cli-metadata]** — equivalent CLI commands.

[mkdocstrings]: https://mkdocstrings.github.io/
[python-metadata]: ../guides/python/metadata/
[cli-metadata]: ../guides/cli/metadata/
[recipe-001]: ../../recipes/metadata/01_list_countries.py
[recipe-005]: ../../recipes/metadata/05_refresh_metadata.py