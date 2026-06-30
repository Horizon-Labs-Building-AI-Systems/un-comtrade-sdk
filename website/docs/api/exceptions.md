---
title: Exceptions
description: The ComtradeError hierarchy — typed exceptions for every documented failure mode.
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
related_recipes: []
related_api:
  - un_comtrade.ComtradeClient
related_guides:
  - guides/python/index/
---

# Exceptions

The SDK raises typed `ComtradeError` subclasses for every documented
failure mode. The base class is `un_comtrade.exceptions.ComtradeError`.

## API reference

The full reference is generated from the SDK's docstrings via
[mkdocstrings][mkdocstrings].

::: un_comtrade.exceptions
    options:
      show_source: true
      show_root_heading: true
      show_root_full_path: false
      show_symbol_type_heading: true
      members_order: source
      separate_signature: true
      docstring_section_style: table
      filters: ["!^_"]

## Hierarchy

| Exception | When raised |
| --------- | ----------- |
| `ComtradeError` | Base class. |
| `ComtradeAPIError` | Upstream API returned a non-2xx response. |
| `ComtradeAuthError` | Authentication failed (missing or invalid `UN_COMTRADE_KEY`). |
| `ComtradeRateLimitError` | Rate limit hit; the SDK retried and gave up. |
| `ComtradeTransportError` | Underlying HTTP transport failed (network, timeout). |
| `ComtradeParseError` | Upstream response could not be parsed into the canonical model. |
| `SchemaIncompatibleError` | Storage-layer schema check failed on append / merge. |
| `ETLPipelineError` | An ETL pipeline stage failed; `exc.stage_name` identifies it. |

## Examples

```python
from un_comtrade import ComtradeClient
from un_comtrade.exceptions import ComtradeError

try:
    with ComtradeClient() as client:
        result = client.trade.get_exports(reporter_code=699, period="2022")
except ComtradeError as exc:
    print(f"un-comtrade error: {exc}")
```

## Related Guides

- **[Python SDK → Index][python-index]** — idiomatic error-handling
  patterns.

[mkdocstrings]: https://mkdocstrings.github.io/
[python-index]: ../guides/python/