---
title: Interactive exploration
description: Pandas, DuckDB, and Jupyter patterns for exploring UN Comtrade trade data interactively.
audience: analyst
prerequisites:
  - guides/analysts/index/
related_recipes:
  - RECIPE-021
  - RECIPE-022
related_api: []
related_guides:
  - guides/analysts/reporting/
  - guides/python/analytics/
---

# Interactive exploration

The exploration workflow is **iterative**: fetch a small dataset,
inspect it, drill into a slice, fetch a bigger dataset, repeat. The
SDK plays well with pandas, Jupyter, and DuckDB at every step.

## Purpose

This page covers:

1. Iterative fetch + inspect loops.
2. Filtering and slicing with pandas.
3. SQL queries with DuckDB.
4. Notebook-driven exploration patterns.

## Prerequisites

- `un-comtrade-sdk[all]` installed.
- A Jupyter environment (`jupyter lab` or VS Code notebook).

## Walkthrough

### Step 1 — fetch a small dataset

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    exports = client.trade.get_exports(reporter_code=699, period="2022")
    df = exports.to_pandas()

df.shape    # → (1, N)
df.head()
```

### Step 2 — inspect the schema

```python
df.dtypes
# ref_period_id            int64
# reporter_code            int64
# partner_code             int64
# flow_code               object
# cmd_code                object
# primary_value           object  (Decimal)
# ...
```

The `Decimal` columns arrive as Python objects; convert explicitly
when you need numeric arithmetic:

```python
df["primary_value_float"] = df["primary_value"].astype(float)
df["primary_value_float"].describe()
```

### Step 3 — drill into a slice

```python
us_exports = df[df.partner_code == 842]
print(f"India → US exports: ${us_exports.primary_value_float.sum():,.2f}")
```

### Step 4 — fetch a bigger dataset

```python
multi_year = []
with ComtradeClient() as client:
    for year in range(2010, 2024):
        exports = client.trade.get_exports(reporter_code=699, period=str(year))
        multi_year.append(exports.to_pandas())

df = pd.concat(multi_year, ignore_index=True)
df.shape    # → (13, N)
```

### Step 5 — group and rank

```python
rankings = (
    df.groupby("partner_code")
      .primary_value_float.sum()
      .sort_values(ascending=False)
      .head(10)
)
print(rankings)
```

### Step 6 — persist and re-load with DuckDB

```python
import duckdb

with ComtradeClient() as client:
    client.storage.open("india_history.duckdb").write(
        client.trade.get_exports(reporter_code=699, period="2010-2022"),
    )

con = duckdb.connect("india_history.duckdb")
top = con.execute("""
    SELECT partner_code, SUM(primary_value) AS total
    FROM exports
    GROUP BY partner_code
    ORDER BY total DESC
    LIMIT 10
""").fetch_df()
```

DuckDB reads the Parquet / DuckDB file in place — no pandas
intermediate, no memory pressure on large datasets.

## Examples

A side-by-side India-vs-China comparison:

```python
import pandas as pd
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    ind = client.trade.get_exports(reporter_code=699, period="2022").to_pandas()
    chn = client.trade.get_exports(reporter_code=156, period="2022").to_pandas()

ind_total = ind.primary_value_float.sum()
chn_total = chn.primary_value_float.sum()
print(f"India total exports: ${ind_total:,.2f}")
print(f"China total exports: ${chn_total:,.2f}")
print(f"Ratio (India / China): {ind_total / chn_total:.2%}")
```

A monthly seasonality analysis:

```python
import pandas as pd
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    monthly = pd.concat([
        client.trade.get_exports(reporter_code=699, period=f"2022{m:02d}").to_pandas()
        for m in range(1, 13)
    ])

monthly["month"] = monthly["period"].str[-2:].astype(int)
print(monthly.groupby("month").primary_value_float.sum())
```

## Related Recipes

- **[RECIPE-021][recipe-021]** — *Compute a country trade balance*.
- **[RECIPE-022][recipe-022]** — *Top commodities*.

## Related Guides

- **[Data Analysis → Reporting][reporting]** — produce shareable
  Markdown reports.
- **[Python SDK → Analytics][python-analytics]** — typed analytics
  on `CanonicalDataset`.

## Next steps

- **[Reporting][reporting]** — turn exploration results into
  Markdown reports.
- **[Cookbook → End-to-end recipes][end-to-end]** — full pipeline
  patterns.

[reporting]: ../reporting/
[python-analytics]: ../../python/analytics/
[end-to-end]: ../../../cookbook/end_to_end/
[recipe-021]: ../../../../recipes/analytics/country_balance.py
[recipe-022]: ../../../../recipes/analytics/top_commodities.py