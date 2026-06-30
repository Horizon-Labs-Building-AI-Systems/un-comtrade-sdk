---
title: Storage via the CLI
description: Read, write, append, and refresh storage backends from the terminal.
audience: cli
prerequisites:
  - guides/cli/index/
related_recipes:
  - RECIPE-101
related_api: []
related_guides:
  - guides/cli/trade/
  - guides/cli/analytics/
---

# Storage via the CLI

The `storage` command persists `CanonicalDataset` to CSV, JSON,
Parquet, or DuckDB; reads it back; appends new records; and refreshes
the metadata sidecar. The backend is auto-detected from the file
extension.

## Purpose

This page covers the `storage` sub-subcommands, their flags, and
shell-composition patterns.

## Prerequisites

- A `CanonicalDataset` (from `un-comtrade trade ...` piped through,
  or from a stored file).
- The `un-comtrade` script on your `PATH`.
- For Parquet / DuckDB, the corresponding optional dependency
  installed.

## Walkthrough

### Write a dataset

```bash
un-comtrade trade exports --reporter 699 --period 2022 --partner 0 \
    --output-format json \
    | un-comtrade storage write --out india_exports_2022.parquet --from -
```

The `--from -` reads the dataset from stdin (a JSON serialised
`CanonicalDataset`).

### Write from a stored file

```bash
un-comtrade storage write --out india_exports_2022.parquet --from exports.json
```

### Read a dataset

```bash
un-comtrade storage read --input india_exports_2022.parquet
```

Outputs the canonical JSON representation of the dataset.

### Append records

```bash
un-comtrade trade exports --reporter 699 --period 2021 --partner 0 \
    --output-format json \
    | un-comtrade storage append --input india_exports_2022.parquet --from -
```

The append mode is `MERGE` by default (de-duplicates by primary
key). Override with `--mode append` for raw append.

### Refresh the metadata sidecar

```bash
un-comtrade storage refresh --input india_exports_2022.parquet
```

Re-writes the sidecar file (`<root>/<dataset_name>.meta.json`)
without touching the dataset records.

## Examples

Round-trip through all four backends:

```bash
un-comtrade trade exports --reporter 699 --period 2022 --partner 0 --output-format json > /tmp/exports.json

for ext in csv json parquet duckdb; do
    un-comtrade storage write --out "/tmp/exports.$ext" --from /tmp/exports.json
done

# Verify the round-trip is byte-for-byte equal.
un-comtrade storage read --input /tmp/exports.parquet | jq -S . > /tmp/parquet.json
un-comtrade storage read --input /tmp/exports.duckdb | jq -S . > /tmp/duckdb.json
diff /tmp/parquet.json /tmp/duckdb.json
```

A multi-year rollup:

```bash
for year in $(seq 2010 2023); do
    un-comtrade trade exports --reporter 699 --period $year --partner 0 --output-format json \
        | un-comtrade storage append --input india_exports_history.parquet --from -
done
```

## Related Recipes

- **[RECIPE-101][recipe-101]** — *Drive storage commands from the
  CLI*.

## Related Guides

- **[CLI → Trade][cli-trade]** — produces a dataset.
- **[CLI → Analytics][cli-analytics]** — runs analytics on a stored
  dataset.

## Next steps

- **[CLI → Analytics][cli-analytics]** — drill into a stored
  dataset.
- **[Python SDK → Storage][python-storage]** — equivalent Python
  API.

[cli-trade]: ../trade/
[cli-analytics]: ../analytics/
[python-storage]: ../../python/storage/
[recipe-101]: ../../../../recipes/cli/04_storage_cli.py