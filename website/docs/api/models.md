---
title: Models
description: The canonical data model — CanonicalDataset, TradeRecord, Country, HSCode, Configuration, and friends.
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
related_api:
  - un_comtrade.ComtradeClient
related_guides:
  - guides/python/index/
---

# Models

The canonical data model is the typed boundary between the upstream
wire format and the consumer's view of the world. Every record is
immutable (`frozen=True`); monetary values are `Decimal`; dates are
ISO-8601 strings; enums are `frozenset`.

## API reference

The full reference is generated from the SDK's docstrings via
[mkdocstrings][mkdocstrings].

::: un_comtrade.models
    options:
      show_source: true
      show_root_heading: true
      show_root_full_path: false
      show_symbol_type_heading: true
      members_order: source
      separate_signature: true
      docstring_section_style: table
      filters: ["!^_"]

::: un_comtrade.config
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
from un_comtrade.config import Configuration

config = Configuration(api_key="your-key", retry_attempts=3)
with ComtradeClient(config) as client:
    exports = client.trade.get_exports(reporter_code=699, period="2022")
    record = exports.records[0]
    print(record.primary_value, record.partner_code, record.flow_code)
```

## Related Recipes

- **[RECIPE-001][recipe-001]** — *List reporter countries*.

## Related Guides

- **[Python SDK → Index][python-index]** — idiomatic patterns.

[mkdocstrings]: https://mkdocstrings.github.io/
[python-index]: ../guides/python/
[recipe-001]: ../../recipes/metadata/01_list_countries.py