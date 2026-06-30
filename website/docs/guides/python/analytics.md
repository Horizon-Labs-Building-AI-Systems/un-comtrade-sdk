---
title: Analytics in Python
description: Country, partner, commodity, time-series, balance, and comparison analytics — typed, frozen, Decimal-safe — on top of CanonicalDataset.
audience: python
prerequisites:
  - guides/python/trade/
related_recipes:
  - RECIPE-021
  - RECIPE-022
  - RECIPE-023
  - RECIPE-024
  - RECIPE-025
related_api:
  - un_comtrade.ComtradeClient
  - un_comtrade.client.ComtradeClient.analytics
related_guides:
  - guides/python/trade/
  - guides/analysts/exploration/
---

# Analytics

The analytics layer exposes **typed, frozen, Decimal-safe** analytics
functions on top of `CanonicalDataset`. Every function returns a
tuple of frozen dataclasses — no raw upstream JSON, no untyped
dicts, no `float` arithmetic.

The layer is organised into six submodules:

- **Country** — total imports / exports / balance / trend.
- **Partner** — top partners, growth, bilateral summary.
- **Commodity** — top HS codes, rankings, sector summaries.
- **Time series** — annual / monthly trends, rolling averages, CAGR.
- **Balance** — exports-minus-imports aggregations.
- **Comparison** — side-by-side N-way comparisons.

## Purpose

This page covers:

1. The `AnalyticsEngine` interface.
2. The country-level analytics.
3. The partner-level analytics.
4. The commodity / HS analytics.
5. The time-series analytics.
6. The trade-balance analytics.
7. The comparative analytics.

## Prerequisites

- A `CanonicalDataset` (from `client.trade.get_*`) or any
  `Iterable[TradeRecord]`.
- The dataset lives entirely in memory; the analytics layer never
  talks to the network.

## Walkthrough

### Country — total exports

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    exports = client.trade.get_exports(reporter_code=699, period="2022")
    total = client.analytics.total_exports(exports)
    print(f"Total: ${total.value:,.2f}")
```

Returns a frozen `CountrySummary` dataclass with the `Decimal`
value, the record count, and the period range.

### Country — ranking

```python
rankings = client.analytics.country_ranking(
    exports,
    by="exports",            # or "imports", "trade_balance", "record_count"
    descending=True,
    limit=10,
)
for row in rankings:
    print(f"  {row.country_label:<32} ${row.value:>20,.2f}")
```

### Partner — top partners

```python
top_partners = client.analytics.top_partners(
    exports,
    by="exports",
    descending=True,
    limit=5,
)
```

Returns `tuple[PartnerRankingRow, ...]`. The `by` selector accepts
`"total_trade"`, `"exports"`, `"imports"`, `"trade_balance"`,
`"abs_trade_balance"`, or `"record_count"`.

### Partner — growth

```python
growth = client.analytics.partner_growth(
    exports,
    partner_code=842,        # United States
    granularity="year",     # or "period"
)
print(f"CAGR: {growth.cagr:.4f}")
```

Returns a frozen `PartnerGrowth` dataclass with the per-year
series, the absolute change, the relative change, and the CAGR.

### Commodity — top HS codes

```python
top_hs = client.analytics.top_hs_codes(
    exports,
    by="exports",
    hs_level=2,              # HS chapter; 4 or 6 also supported
    limit=10,
)
```

### Commodity — sector summaries

```python
sectors = client.analytics.sector_summaries(
    exports,
    by="exports",
)
for sector in sectors:
    print(f"  Section {sector.section_code} {sector.section_label:<32} ${sector.value:,.2f}")
```

Groups records by the WCO Harmonized System section (one row per
section; "Unknown" pseudo-section for non-HS chapters).

### Time series — annual trend

```python
trend = client.analytics.annual_trend(
    exports,
    reporter_code=699,        # optional filter
)
for point in trend:
    print(f"  {point.year}  ${point.value:>20,.2f}  ({point.record_count} records)")
```

### Time series — rolling average

```python
rolling = client.analytics.rolling_average(trend, n=3)
```

Returns a new `TrendPoint` series with a 3-point trailing rolling
mean applied.

### Balance — global

```python
balance = client.analytics.global_balance(exports)
print(f"Global balance: ${balance.value:,.2f}")
```

### Comparison — country vs country

```python
cmp = client.analytics.country_vs_country(
    [exports_india, exports_us],
    labels=["India", "United States"],
    breakdown_by="commodity",
)
```

Returns a frozen `CountryComparison` with per-country totals,
per-dimension deltas, and percentage changes.

## Examples

A full India-vs-China export comparison:

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    ind = client.trade.get_exports(reporter_code=699, period="2022", partner_code=0)
    chn = client.trade.get_exports(reporter_code=156, period="2022", partner_code=0)
    cmp = client.analytics.country_vs_country(
        [ind, chn], labels=["India", "China"], breakdown_by="commodity",
    )
    for row in cmp.rows[:5]:
        print(f"  {row.dimension_label}: India ${row.values[0]:,.0f}  China ${row.values[1]:,.0f}")
```

A CAGR-over-decade trend:

```python
with ComtradeClient() as client:
    series = []
    for year in range(2012, 2023):
        exports = client.trade.get_exports(reporter_code=699, period=str(year), partner_code=0)
        series.extend(exports.records)
    dataset = type(exports)(records=tuple(series))
    trend = client.analytics.annual_trend(dataset, reporter_code=699)
    cagr = client.analytics.cagr(trend)
    print(f"India export CAGR 2012–2022: {cagr:.2%}")
```

## Related Recipes

- **[RECIPE-021][recipe-021]** — *Compute a country trade balance*.
- **[RECIPE-022][recipe-022]** — *Top commodities*.
- **[RECIPE-023][recipe-023]** — *Partner analysis*.
- **[RECIPE-024][recipe-024]** — *Country comparison*.
- **[RECIPE-025][recipe-025]** — *Trend analysis*.

## Related API

- [`ComtradeClient.analytics`][api-analytics] — the analytics
  facade.
- [`un_comtrade.CanonicalDataset`][api-models] — the typed dataset.

## Related Guides

- **[Trade][python-trade]** — produces `CanonicalDataset`.
- **[Data Analysis → Exploration][analysts-exploration]** —
  pandas / Jupyter patterns.

## Next steps

- **[Storage][python-storage]** — round-trip analytics through
  Parquet / DuckDB.
- **[Data Analysis → Reporting][analysts-reporting]** — produce
  Markdown reports from analytics output.

[python-trade]: ../trade/
[python-storage]: ../storage/
[analysts-exploration]: ../../analysts/exploration/
[analysts-reporting]: ../../analysts/reporting/
[recipe-021]: ../../../recipes/analytics/country_balance.py
[recipe-022]: ../../../recipes/analytics/top_commodities.py
[recipe-023]: ../../../recipes/analytics/partner_analysis.py
[recipe-024]: ../../../recipes/analytics/country_comparison.py
[recipe-025]: ../../../recipes/analytics/trend_analysis.py
[api-analytics]: ../../api/client/
[api-models]: ../../api/models/