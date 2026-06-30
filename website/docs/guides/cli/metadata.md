---
title: Metadata via the CLI
description: Browse reference catalogues (countries, partners, HS codes, units) from the terminal.
audience: cli
prerequisites:
  - guides/cli/index/
related_recipes:
  - RECIPE-091
related_api: []
related_guides:
  - guides/cli/trade/
  - guides/python/metadata/
---

# Metadata via the CLI

The `metadata` command browses the UN Comtrade reference catalogues.
Five sub-subcommands cover countries, partners, HS codes, search,
and refresh.

## Purpose

This page covers each `metadata` sub-subcommand in detail, with
flags, output formats, and shell-composition patterns.

## Prerequisites

- `un-comtrade-sdk` installed.
- The `un-comtrade` script on your `PATH`.

## Walkthrough

### List countries

```bash
un-comtrade metadata countries
```

Output (default `json`):

```json
[
  {"country_code": 4, "iso_alpha3": "AFG", "display_name": "Afghanistan"},
  ...
]
```

### List partner countries

```bash
un-comtrade metadata partners
```

### List HS codes at a level

```bash
un-comtrade metadata hs-codes --level 2      # HS chapters
un-comtrade metadata hs-codes --level 4      # HS headings
un-comtrade metadata hs-codes --level 6      # HS subheadings
```

### Search HS codes by description

```bash
un-comtrade metadata search "electrical"
```

### Refresh the catalogue

```bash
un-comtrade metadata refresh
```

Forces a re-download of every catalogue. Rate-limited to one HTTP
call per second.

## Examples

A Markdown table of the top-20 countries by population-equivalent
rank (the catalogue is sorted by reporter code):

```bash
un-comtrade metadata countries --output-format markdown | head -25
```

Pipe the country catalogue to `jq` for filtering:

```bash
un-comtrade metadata countries --output-format json \
    | jq '[.[] | select(.iso_alpha3 == "IND")]'
# → [{"country_code": 699, "iso_alpha3": "IND", "display_name": "India"}]
```

Search HS codes for "machinery":

```bash
un-comtrade metadata search "machinery" --output-format markdown
```

## Related Recipes

- **[RECIPE-091][recipe-091]** — *Drive metadata commands from the
  CLI*.

## Related Guides

- **[CLI → Trade][cli-trade]** — uses the country catalogue to
  resolve reporter / partner codes.
- **[Python SDK → Metadata][python-metadata]** — equivalent Python
  API.

## Next steps

- **[CLI → Trade][cli-trade]** — apply the catalogue to a real
  trade query.
- **[Cookbook → metadata recipes][cookbook-metadata]** — full
  executable forms.

[cli-trade]: ../trade/
[python-metadata]: ../../python/metadata/
[cookbook-metadata]: ../../../cookbook/metadata/
[recipe-091]: ../../../../recipes/cli/01_metadata_cli.py