---
title: CLI surface
description: The un-comtrade console script — five outer commands, 22 sub-subcommands, five output formats.
audience: cli
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
  - RECIPE-091
  - RECIPE-095
  - RECIPE-099
related_api: []
related_guides:
  - guides/cli/index/
---

# CLI surface

The CLI is the `un-comtrade` console script — installed alongside
the Python package. Five outer commands, 22 sub-subcommands, and
five output formats (`json`, `table`, `csv`, `markdown`, `text`).

## API reference

The full CLI surface is generated from the SDK's docstrings via
[mkdocstrings][mkdocstrings]. The CLI is a thin wrapper around the
Python facade; there is no separate API beyond the Python facade.

::: un_comtrade.cli
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

```bash
un-comtrade trade exports --reporter 699 --period 2022 --partner 0 --output-format markdown
```

## Related Recipes

- **[RECIPE-091][recipe-091]** — *Drive metadata commands from the CLI*.
- **[RECIPE-095][recipe-095]** — *Drive trade commands from the CLI*.
- **[RECIPE-099][recipe-099]** — *Drive analytics commands from the CLI*.

## Related Guides

- **[CLI → Index][cli-index]** — full CLI command reference.

[mkdocstrings]: https://mkdocstrings.github.io/
[cli-index]: ../guides/cli/
[recipe-091]: ../../recipes/cli/01_metadata_cli.py
[recipe-095]: ../../recipes/cli/02_trade_cli.py
[recipe-099]: ../../recipes/cli/03_analytics_cli.py