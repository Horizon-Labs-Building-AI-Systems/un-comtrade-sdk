---
title: Command-line interface
description: Drive the SDK from a terminal; five outer commands, 22 sub-subcommands, five output formats.
audience: cli
prerequisites:
  - getting_started/installation/
related_recipes:
  - RECIPE-091
  - RECIPE-095
  - RECIPE-099
  - RECIPE-100
  - RECIPE-101
  - RECIPE-104
related_api: []
related_guides:
  - guides/cli/metadata/
  - guides/cli/trade/
  - guides/cli/analytics/
  - guides/cli/storage/
  - guides/cli/etl/
---

# Command-line interface

The CLI is the `un-comtrade` console script — installed alongside the
Python package. Five outer commands, 22 sub-subcommands, and five
output formats (`json`, `table`, `csv`, `markdown`, `text`).

## Purpose

This page covers:

1. The CLI entry point and global flags.
2. The five outer commands.
3. The output formats.
4. Environment variables.
5. Composing pipelines with shell pipes.

## Prerequisites

- `un-comtrade-sdk` installed (the `un-comtrade` script is on your
  `PATH` after install).
- For authenticated endpoints, set `UN_COMTRADE_KEY` (see
  **[Authentication][auth]**).

## Walkthrough

### Top-level help

```bash
un-comtrade --help
```

```
Usage: un-comtrade [OPTIONS] COMMAND [ARGS]...

  un-comtrade-sdk CLI.

Options:
  --output-format [json|table|csv|markdown|text]
  --help                          Show this message and exit.

Commands:
  metadata   Browse reference catalogues.
  trade      Fetch annual / monthly trade flows.
  analytics  Run typed analytics on a stored dataset.
  storage    Read / write / refresh storage backends.
  etl        Compose ETL pipelines.
```

### Global flags

```bash
un-comtrade --output-format markdown metadata countries
```

The `--output-format` flag applies to every command. Default is
`json`.

### Metadata sub-commands

```bash
un-comtrade metadata countries
un-comtrade metadata partners
un-comtrade metadata hs-codes --level 2
un-comtrade metadata search "india"
un-comtrade metadata refresh
```

See **[CLI → Metadata][cli-metadata]** for the full reference.

### Trade sub-commands

```bash
un-comtrade trade exports --reporter 699 --period 2022 --partner 0
un-comtrade trade imports --reporter 699 --period 2022 --partner 0
un-comtrade trade balance --reporter 699 --period 2022
un-comtrade trade tariffline --reporter 699 --period 2022 --hs 854231
```

See **[CLI → Trade][cli-trade]** for the full reference.

### Analytics sub-commands

```bash
un-comtrade analytics top-partners --input india_exports_2022.parquet --by exports --limit 5
un-comtrade analytics top-hs-codes --input india_exports_2022.parquet --hs-level 2 --limit 10
un-comtrade analytics global-balance --input india_exports_2022.parquet
```

See **[CLI → Analytics][cli-analytics]** for the full reference.

### Storage sub-commands

```bash
un-comtrade storage write --input exports.json --out india_exports.parquet
un-comtrade storage read --input india_exports.parquet
un-comtrade storage append --input history.parquet --from new.json
un-comtrade storage refresh --input india_exports.parquet
```

See **[CLI → Storage][cli-storage]** for the full reference.

### ETL sub-commands

```bash
un-comtrade etl run --pipeline india_exports --stages fetch,export
```

See **[CLI → ETL][cli-etl]** for the full reference.

## Examples

Compose a pipeline that fetches, exports, and reports:

```bash
un-comtrade trade exports --reporter 699 --period 2022 --partner 0 \
    --output-format json \
    | un-comtrade storage write --out india_exports_2022.parquet --from -

un-comtrade analytics top-partners \
    --input india_exports_2022.parquet \
    --by exports --limit 5 \
    --output-format markdown
```

A two-decade trend:

```bash
for year in $(seq 2010 2023); do
    un-comtrade trade exports --reporter 699 --period $year --partner 0 \
        --output-format json \
        | jq -r --arg y "$year" '"\($y): \(.aggregate_total | tonumber | . / 1e9)B USD"'
done
```

A Markdown report written to disk:

```bash
un-comtrade analytics top-partners \
    --input india_exports_2022.parquet \
    --by exports --limit 10 \
    --output-format markdown > report.md
```

## Related Recipes

- **[RECIPE-091][recipe-091]** — *Drive metadata commands from the CLI*.
- **[RECIPE-095][recipe-095]** — *Drive trade commands from the CLI*.
- **[RECIPE-099][recipe-099]** — *Drive analytics commands from the CLI*.
- **[RECIPE-100][recipe-100]** — *Drive ETL from the CLI*.
- **[RECIPE-101][recipe-101]** — *Drive storage from the CLI*.
- **[RECIPE-104][recipe-104]** — *Output formats from the CLI*.

## Related API

The CLI is a thin wrapper around the Python facade — there is no
separate CLI API surface.

## Related Guides

- **[CLI → Metadata][cli-metadata]**
- **[CLI → Trade][cli-trade]**
- **[CLI → Analytics][cli-analytics]**
- **[CLI → Storage][cli-storage]**
- **[CLI → ETL][cli-etl]**

## Next steps

- **[CLI → Trade][cli-trade]** — the most common CLI workflow.
- **[Cookbook → CLI recipes][cookbook-cli]** — full executable
  forms.

[auth]: ../../getting_started/authentication/
[cli-metadata]: metadata/
[cli-trade]: trade/
[cli-analytics]: analytics/
[cli-storage]: storage/
[cli-etl]: etl/
[cookbook-cli]: ../../cookbook/cli/
[recipe-091]: ../../../recipes/cli/01_metadata_cli.py
[recipe-095]: ../../../recipes/cli/02_trade_cli.py
[recipe-099]: ../../../recipes/cli/03_analytics_cli.py
[recipe-100]: ../../../recipes/cli/05_etl_cli.py
[recipe-101]: ../../../recipes/cli/04_storage_cli.py
[recipe-104]: ../../../recipes/cli/06_output_formats_cli.py