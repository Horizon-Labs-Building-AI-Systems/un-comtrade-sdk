---
title: Data Analysis with the SDK
description: Pandas, Jupyter, DuckDB, and Markdown report patterns for exploring UN Comtrade trade data interactively.
audience: analyst
prerequisites:
  - guides/python/trade/
  - guides/python/analytics/
related_recipes:
  - RECIPE-021
  - RECIPE-111
  - RECIPE-113
related_api: []
related_guides:
  - guides/analysts/exploration/
  - guides/analysts/reporting/
---

# Data Analysis with the SDK

The Data Analysis section is the entry point for **data analysts**
who want to explore UN Comtrade trade data interactively. The SDK
plays well with pandas, Jupyter notebooks, DuckDB, Parquet, and
Markdown report generators.

## Purpose

This page covers:

1. Loading a `CanonicalDataset` into a pandas DataFrame.
2. Querying a stored dataset with DuckDB SQL.
3. Generating Markdown reports from analytics output.
4. Iterative exploration patterns in Jupyter.

## Prerequisites

- `un-comtrade-sdk[all]` installed (includes Parquet + DuckDB).
- Familiarity with pandas, Jupyter notebooks, and SQL basics.

## Walkthrough

### Load into pandas

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    dataset = client.trade.get_exports(reporter_code=699, period="2022")
    df = dataset.to_pandas()

print(df.head())
```

`CanonicalDataset.to_pandas()` returns a `pandas.DataFrame` with
typed columns (`Decimal` → `object`, ISO-8601 → `string`,
`frozenset` → `object`).

### Query with DuckDB

```python
import duckdb

con = duckdb.connect("india_exports.duckdb")
result = con.execute("""
    SELECT partner_code, SUM(primary_value) AS total
    FROM exports
    GROUP BY partner_code
    ORDER BY total DESC
    LIMIT 10
""").fetchall()
```

### Generate a Markdown report

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    exports = client.trade.get_exports(reporter_code=699, period="2022")
    top = client.analytics.top_partners(exports, by="exports", limit=10)

print("# Top 10 export partners — India, 2022\n")
print("| Partner | Total (USD) | Records |")
print("| ------- | -----------: | ------: |")
for row in top:
    print(f"| {row.partner_label} | ${row.value:,.2f} | {row.record_count} |")
```

### Jupyter iteration

```python
import matplotlib.pyplot as plt
from un_comtrade import ComtradeClient

years, totals = [], []
with ComtradeClient() as client:
    for year in range(2010, 2024):
        exports = client.trade.get_exports(reporter_code=699, period=str(year))
        years.append(year)
        totals.append(float(exports.aggregate_total()))

plt.plot(years, totals)
plt.xlabel("Year")
plt.ylabel("Total exports (USD)")
plt.title("India exports 2010–2023")
plt.show()
```

## Examples

A pandas-only workflow:

```python
from un_comtrade import ComtradeClient
import pandas as pd

with ComtradeClient() as client:
    df = pd.concat([
        client.trade.get_exports(reporter_code=699, period=str(y)).to_pandas()
        for y in range(2020, 2024)
    ])

print(df.groupby(df.ref_period_id).primary_value.sum())
```

A DuckDB-only workflow:

```python
import duckdb
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    exports = client.trade.get_exports(reporter_code=699, period="2022")
    client.storage.open("india_exports.duckdb").write(exports)

con = duckdb.connect("india_exports.duckdb")
print(con.execute("SELECT COUNT(*) FROM exports").fetchone())
```

A Jupyter cell that produces a Markdown table:

```python
from un_comtrade import ComtradeClient
from IPython.display import Markdown, display

with ComtradeClient() as client:
    exports = client.trade.get_exports(reporter_code=699, period="2022")
    top = client.analytics.top_partners(exports, by="exports", limit=5)

md = "| Partner | Total |\n| --- | ---: |\n"
for row in top:
    md += f"| {row.partner_label} | ${row.value:,.2f} |\n"
display(Markdown(md))
```

## Related Recipes

- **[RECIPE-021][recipe-021]** — *Compute a country trade balance*.
- **[RECIPE-111][recipe-111]** — *India exports to report* — full
  Markdown report from a single CLI / Python call.
- **[RECIPE-113][recipe-113]** — *HS explorer to Markdown*.

## Related Guides

- **[Data Analysis → Exploration][exploration]** — pandas / DuckDB
  patterns.
- **[Data Analysis → Reporting][reporting]** — Markdown report
  generation.

## Next steps

- **[Exploration][exploration]** — drill into the iterative
  workflow.
- **[Reporting][reporting]** — produce shareable Markdown reports.

[exploration]: exploration/
[reporting]: reporting/
[recipe-021]: ../../../recipes/analytics/country_balance.py
[recipe-111]: ../../../recipes/end_to_end/01_india_exports_to_report.py
[recipe-113]: ../../../recipes/end_to_end/02_hs_explorer_to_markdown.py