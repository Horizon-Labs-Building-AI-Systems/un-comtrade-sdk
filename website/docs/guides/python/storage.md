---
title: Storage in Python
description: Round-trip CanonicalDataset through CSV, JSON, Parquet, or DuckDB; auto-detect the backend from the file extension.
audience: python
prerequisites:
  - guides/python/trade/
  - guides/python/analytics/
related_recipes:
  - RECIPE-031
  - RECIPE-032
  - RECIPE-033
  - RECIPE-034
  - RECIPE-035
  - RECIPE-036
related_api:
  - un_comtrade.ComtradeClient
  - un_comtrade.client.ComtradeClient.storage
related_guides:
  - guides/python/trade/
  - guides/python/analytics/
  - guides/python/etl/
---

# Storage

The storage layer round-trips `CanonicalDataset` through four
production backends: **CSV**, **JSON**, **Parquet**, and **DuckDB**.
The backend is auto-detected from the file extension; the SDK picks
the right writer without configuration.

## Purpose

This page covers:

1. The `StorageRegistry` interface.
2. The four backends and their trade-offs.
3. Round-trip semantics (`Decimal` preserved, ISO-8601 dates
   preserved, enums preserved).
4. Incremental updates (`APPEND` / `MERGE` / `REPLACE`).

## Prerequisites

- `un-comtrade-sdk` installed.
- For Parquet: `pip install un-comtrade-sdk[parquet]`.
- For DuckDB: `pip install un-comtrade-sdk[duckdb]`.
- A `CanonicalDataset` to write.

## Walkthrough

### Auto-detect from extension

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    exports = client.trade.get_exports(reporter_code=699, period="2022")
    client.storage.open("india_exports_2022.parquet").write(exports)
```

The `open(uri)` method inspects the extension (`.csv`, `.json`,
`.parquet`, `.duckdb`) and dispatches to the right writer.

### Explicit backend

```python
client.storage.csv("india_exports_2022.csv").write(exports)
client.storage.json("india_exports_2022.json").write(exports)
client.storage.parquet("india_exports_2022.parquet").write(exports)
client.storage.duckdb("india_exports_2022.duckdb").write(exports)
```

The explicit API is preferable when you want to fail-fast on a
typo or when the file extension is ambiguous.

### Read back a dataset

```python
dataset = client.storage.open("india_exports_2022.parquet").read()
print(f"{len(dataset.records):,} rows")
```

The `read()` method returns a fresh `CanonicalDataset`. The
round-trip is **byte-for-byte equal** to the original — `Decimal`
arithmetic preserved, ISO-8601 dates preserved, `frozenset` enums
preserved.

### Incremental update

```python
client.storage.update("india_exports_2022.parquet", mode="append")
```

Three modes:

- `APPEND` — append records to the existing dataset.
- `MERGE` — merge new records by primary key (ref_period_id +
  reporter_code + partner_code + flow_code + cmd_code).
- `REPLACE` — replace the entire dataset.

## Examples

Write to all four backends and verify equality:

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    exports = client.trade.get_exports(reporter_code=699, period="2022")

    # Write to each backend.
    for ext in (".csv", ".json", ".parquet", ".duckdb"):
        path = f"india_exports_2022{ext}"
        client.storage.open(path).write(exports)

    # Read back from each backend and compare.
    originals = sorted(exports.records, key=lambda r: (r.partner_code, r.cmd_code))
    for ext in (".csv", ".json", ".parquet", ".duckdb"):
        path = f"india_exports_2022{ext}"
        dataset = client.storage.open(path).read()
        roundtripped = sorted(dataset.records, key=lambda r: (r.partner_code, r.cmd_code))
        assert originals == roundtripped, f"mismatch on {ext}"
    print("All four backends produce identical round-trips.")
```

Incremental append with merge-by-key:

```python
# Append 2021 records to an existing 2022 file.
exports_2021 = client.trade.get_exports(reporter_code=699, period="2021")
client.storage.append("india_exports_history.parquet", exports_2021)

# Read back the merged dataset.
merged = client.storage.open("india_exports_history.parquet").read()
print(f"{len(merged.records):,} rows in the merged dataset")
```

## Related Recipes

- **[RECIPE-031][recipe-031]** — *ETL pipeline into storage*.
- **[RECIPE-032][recipe-032]** — *Export to CSV*.
- **[RECIPE-033][recipe-033]** — *Export to Parquet*.
- **[RECIPE-034][recipe-034]** — *Export to DuckDB*.
- **[RECIPE-035][recipe-035]** — *Reload from storage*.
- **[RECIPE-036][recipe-036]** — *Analytics on stored data*.

## Related API

- [`ComtradeClient.storage`][api-storage] — the storage facade.
- [`StorageRegistry.open`][api-storage] — the auto-detect accessor.

## Related Guides

- **[Trade][python-trade]** — produces `CanonicalDataset`.
- **[Analytics][python-analytics]** — typed analytics on top of the
  dataset.
- **[ETL][python-etl]** — composes the `fetch` → `export` flow.

## Next steps

- **[ETL][python-etl]** — chain storage writes into a pipeline.
- **[Cookbook → storage recipes][cookbook-storage]** — full
  executable forms.

[python-trade]: ../trade/
[python-analytics]: ../analytics/
[python-etl]: ../etl/
[cookbook-storage]: ../../cookbook/storage/
[recipe-031]: ../../../recipes/storage/01_etl_pipeline.py
[recipe-032]: ../../../recipes/storage/02_export_csv.py
[recipe-033]: ../../../recipes/storage/03_export_parquet.py
[recipe-034]: ../../../recipes/storage/04_export_duckdb.py
[recipe-035]: ../../../recipes/storage/05_reload_storage.py
[recipe-036]: ../../../recipes/storage/06_analytics_on_stored.py
[api-storage]: ../../api/storage/