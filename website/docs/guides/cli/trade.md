---
title: Trade via the CLI
description: Fetch annual / monthly trade flows from the terminal; pipe output to storage or other Unix tools.
audience: cli
prerequisites:
  - guides/cli/index/
related_recipes:
  - RECIPE-095
related_api: []
related_guides:
  - guides/cli/metadata/
  - guides/cli/storage/
---

# Trade via the CLI

The `trade` command fetches the canonical trade data from the UN
Comtrade API. Four sub-subcommands cover exports, imports, balance,
and tariffline.

## Purpose

This page covers each `trade` sub-subcommand in detail, with flags,
output formats, and shell-composition patterns.

## Prerequisites

- `un-comtrade-sdk` installed.
- The `un-comtrade` script on your `PATH`.
- For authenticated endpoints, `UN_COMTRADE_KEY` set.

## Walkthrough

### Fetch exports

```bash
un-comtrade trade exports --reporter 699 --period 2022 --partner 0
```

Output (`json` default):

```json
{
  "records": [
    {
      "ref_period_id": 2022,
      "reporter_code": 699,
      "partner_code": 0,
      "flow_code": "X",
      "cmd_code": "TOTAL",
      "primary_value": "452684213646.747"
    }
  ],
  "aggregate_total": "452684213646.747"
}
```

### Fetch imports

```bash
un-comtrade trade imports --reporter 699 --period 2022 --partner 0
```

### Fetch the trade balance

```bash
un-comtrade trade balance --reporter 699 --period 2022
```

### Fetch tariffline data

```bash
un-comtrade trade tariffline --reporter 699 --period 2022 --hs 854231
```

### Period range

```bash
un-comtrade trade exports --reporter 699 --period 2010,2011,2012,2013 --partner 0
```

### HS chapter filter

```bash
un-comtrade trade exports --reporter 699 --period 2022 --hs 84
```

### Output formats

```bash
un-comtrade trade exports --reporter 699 --period 2022 --output-format markdown
```

See **[CLI → Output formats][output-formats]** for the five
formats.

## Examples

A Markdown table of 2022 exports:

```bash
un-comtrade trade exports --reporter 699 --period 2022 \
    --output-format markdown
```

A two-decade trend in CSV:

```bash
for year in $(seq 2010 2023); do
    un-comtrade trade exports --reporter 699 --period $year --partner 0 \
        --output-format csv \
        | tail -n +2
done > india_exports_2010_2023.csv
```

A partner-specific drill-down:

```bash
un-comtrade trade exports --reporter 699 --period 2022 --partner 842 \
    --output-format json \
    | jq '.aggregate_total'
# → "78310876432.18"
```

## Related Recipes

- **[RECIPE-095][recipe-095]** — *Drive trade commands from the
  CLI*.

## Related Guides

- **[CLI → Metadata][cli-metadata]** — uses the country catalogue.
- **[CLI → Storage][cli-storage]** — pipes trade output to a
  storage backend.
- **[Python SDK → Trade][python-trade]** — equivalent Python API.

## Next steps

- **[CLI → Storage][cli-storage]** — persist trade output.
- **[CLI → Analytics][cli-analytics]** — drill into the stored
  dataset.

[cli-metadata]: ../metadata/
[cli-storage]: ../storage/
[cli-analytics]: ../analytics/
[output-formats]: ../index/
[python-trade]: ../../python/trade/
[recipe-095]: ../../../../recipes/cli/02_trade_cli.py