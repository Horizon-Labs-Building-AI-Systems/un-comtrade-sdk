---
title: Trade in Python
description: Fetch annual and monthly trade flows, drill into partners and HS codes, and use the pagination engine for large datasets.
audience: python
prerequisites:
  - getting_started/quick_start/
  - guides/python/metadata/
related_recipes:
  - RECIPE-011
  - RECIPE-012
  - RECIPE-013
  - RECIPE-014
  - RECIPE-015
related_api:
  - un_comtrade.ComtradeClient
  - un_comtrade.client.ComtradeClient.trade
  - un_comtrade.CanonicalDataset
related_guides:
  - guides/python/analytics/
  - guides/python/storage/
  - guides/python/etl/
---

# Trade

The trade layer fetches the canonical trade data from the UN Comtrade
API: annual and monthly flows, partner breakdowns, HS-code filters,
and the tariffline endpoint. The service hides pagination across the
upstream API's per-call record cap and returns a single combined
`CanonicalDataset`.

## Purpose

This page covers:

1. The `TradeService` interface.
2. The four primary accessors: `get_exports`, `get_imports`,
   `get_balance`, and the tariffline variant.
3. Filters by reporter, partner, period, and HS code.
4. The pagination engine for large datasets.

## Prerequisites

- `un-comtrade-sdk` installed.
- A `ComtradeClient` instantiated.
- For the authenticated endpoints (annual flows before 2014, the
  tariffline endpoint), set `UN_COMTRADE_KEY` (see
  **[Authentication][auth]**).

## Walkthrough

### Annual exports

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    exports = client.trade.get_exports(
        reporter_code=699,        # India
        period="2022",
        partner_code=0,           # World
    )
    print(f"{len(exports.records):,} rows; ${exports.aggregate_total():,.2f}")
```

Returns a `CanonicalDataset` — a typed, immutable container of
`TradeRecord` dataclasses.

### Annual imports

```python
imports = client.trade.get_imports(
    reporter_code=699,
    period="2022",
    partner_code=0,
)
```

Same shape as `get_exports`; flow code is `M` instead of `X`.

### Monthly granularity

```python
exports = client.trade.get_exports(
    reporter_code=699,
    period="202204",        # YYYYMM
    partner_code=0,
)
```

The `period` parameter accepts both `"2022"` (annual) and
`"202204"` (monthly) formats. Annual records have a `YYYY` period;
monthly records have a `YYYYMM` period.

### Tariffline data

```python
tariffline = client.trade.get_tariffline(
    reporter_code=699,
    period="2022",
    hs_code="854231",      # 6-digit HS code
)
```

Returns `CanonicalDataset` filtered to a single HS-6 code with
each record carrying the full tariffline detail (customs
procedure, mode of transport, partner, etc.).

### Filter by partner

```python
exports = client.trade.get_exports(
    reporter_code=699,
    period="2022",
    partner_code=842,      # United States
)
```

### Filter by HS chapter

```python
exports = client.trade.get_exports(
    reporter_code=699,
    period="2022",
    partner_code=0,
    hs_code="84",          # HS chapter (2-digit prefix match)
)
```

### Combine reporter + partner + period range

```python
exports = client.trade.get_exports(
    reporter_code=699,
    period="2010-2022",     # comma-separated list of years
    partner_code=842,
)
```

The `period` parameter accepts a comma-separated list of years or
months. Pagination across the upstream cap is automatic.

### Trade balance

```python
balance = client.trade.get_balance(
    reporter_code=699,
    period="2022",
)
print(f"Trade balance: ${balance.aggregate_total():,.2f}")
```

Returns the per-partner export-minus-import delta, summed across
the requested period.

## Examples

A multi-year export trend:

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    for year in range(2010, 2024):
        exports = client.trade.get_exports(
            reporter_code=699, period=str(year), partner_code=0,
        )
        print(f"{year}: ${exports.aggregate_total():>20,.2f}")
```

Drill into the analytics facade:

```python
with ComtradeClient() as client:
    exports = client.trade.get_exports(reporter_code=699, period="2022")
    top = client.analytics.top_partners(exports, by="exports", limit=10)
    for row in top:
        print(f"  {row.partner_label:<32} ${row.value:>20,.2f}")
```

## Related Recipes

- **[RECIPE-011][recipe-011]** — *Fetch India's annual exports*.
- **[RECIPE-012][recipe-012]** — *Fetch India's annual imports*.
- **[RECIPE-013][recipe-013]** — *Fetch the world totals*.
- **[RECIPE-014][recipe-014]** — *Compute the trade balance*.
- **[RECIPE-015][recipe-015]** — *Tariffline query*.

## Related API

- [`ComtradeClient.trade`][api-trade] — the trade facade.
- [`un_comtrade.CanonicalDataset`][api-models] — the typed dataset.

## Related Guides

- **[Analytics][python-analytics]** — typed analytics on top of
  `CanonicalDataset`.
- **[Storage][python-storage]** — persist datasets to disk.
- **[ETL][python-etl]** — chain trade queries into pipelines.

## Next steps

- **[Analytics][python-analytics]** — drill into top partners,
  country trends, HS rankings.
- **[Storage][python-storage]** — round-trip datasets through
  Parquet / DuckDB.

[auth]: ../../getting_started/authentication/
[python-analytics]: ../analytics/
[python-storage]: ../storage/
[python-etl]: ../etl/
[recipe-011]: ../../../recipes/trade/01_exports.py
[recipe-012]: ../../../recipes/trade/02_imports.py
[recipe-013]: ../../../recipes/trade/03_world_trade.py
[recipe-014]: ../../../recipes/trade/04_trade_balance.py
[recipe-015]: ../../../recipes/trade/05_tariffline.py
[api-trade]: ../../api/client/
[api-models]: ../../api/models/