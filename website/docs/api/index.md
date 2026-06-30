---
title: API Reference
description: Generated reference for every public symbol in the SDK — ComtradeClient, MetadataService, TradeService, AnalyticsEngine, ETLFacade, StorageRegistry, and the canonical data models.
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
  - RECIPE-011
related_api:
  - un_comtrade.ComtradeClient
related_guides:
  - api/client/
  - api/metadata/
  - api/trade/
  - api/analytics/
  - api/etl/
  - api/storage/
  - api/cli/
  - api/models/
  - api/exceptions/
---

# API Reference

The API reference is **generated from the SDK's docstrings** via
[mkdocstrings][mkdocstrings]. No manual editing of API pages is
permitted; any docstring change propagates to this site on the next
build.

## Sections

| Section | Module | What it covers |
| ------- | ------ | -------------- |
| **[ComtradeClient][client]** | `un_comtrade.client` | The single public entry point; constructor, properties, context manager. |
| **[Metadata][metadata]** | `un_comtrade.metadata` | `MetadataService` and the country / partner / HS-code / unit accessors. |
| **[Trade][trade]** | `un_comtrade.trade` | `TradeService` and the annual / monthly / tariffline accessors. |
| **[Analytics][analytics]** | `un_comtrade.analytics` | `AnalyticsEngine` and the country / partner / commodity / time-series / balance / comparison functions. |
| **[ETL][etl]** | `un_comtrade.etl` | `ETLFacade` and the pipeline factory. |
| **[Storage][storage]** | `un_comtrade.storage` | `StorageRegistry` and the four backend writers / readers. |
| **[CLI][cli]** | `un_comtrade.cli` | Console script entry points (CLI surface). |
| **[Models][models]** | `un_comtrade.models` | `CanonicalDataset`, `TradeRecord`, `Country`, `HSCode`, and friends. |
| **[Exceptions][exceptions]** | `un_comtrade.exceptions` | `ComtradeError` and the typed exception hierarchy. |

## Public SDK surface

Per protocol §1.2 (Public SDK only), this reference documents only
the public surface exported via `un_comtrade/__init__.py`'s `__all__`,
the public submodules, and the documented surface in
`docs/007_SDK_SPECIFICATION.md`. Internal modules (anything starting
with `_`) are excluded by mkdocstrings configuration (`filters:
["!^_"]`).

## Examples

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    countries = client.metadata.get_countries()       # -> list[Country]
    exports = client.trade.get_exports(699, "2022")   # -> CanonicalDataset
    top = client.analytics.top_partners(exports, by="exports", limit=5)
```

## Related Recipes

- **[RECIPE-001][recipe-001]** — *List reporter countries*.
- **[RECIPE-011][recipe-011]** — *Fetch India's annual exports*.

## Related Guides

- **[Quick Start][quick-start]** — first-query walkthrough.
- **[Python SDK → Index][python-index]** — idiomatic patterns.

## Next steps

- **[ComtradeClient][client]** — the entry point.
- **[Models][models]** — the typed canonical model.

[client]: client/
[metadata]: metadata/
[trade]: trade/
[analytics]: analytics/
[etl]: etl/
[storage]: storage/
[cli]: cli/
[models]: models/
[exceptions]: exceptions/
[quick-start]: ../getting_started/quick_start/
[python-index]: ../guides/python/
[recipe-001]: ../../recipes/metadata/01_list_countries.py
[recipe-011]: ../../recipes/trade/01_exports.py
[mkdocstrings]: https://mkdocstrings.github.io/