---
title: Run your first query
description: A five-minute walkthrough that fetches India's 2022 exports and prints a one-line summary, with no API key required.
audience: first-time
prerequisites:
  - getting_started/installation/
related_recipes:
  - RECIPE-001
  - RECIPE-011
related_api:
  - un_comtrade.ComtradeClient
  - un_comtrade.client.ComtradeClient.trade
  - un_comtrade.client.ComtradeClient.metadata
related_guides:
  - getting_started/authentication/
  - guides/python/trade/
  - guides/python/metadata/
---

# Quick Start

Five minutes from a fresh install to your first trade query. The
walkthrough below exercises the **public preview** endpoint, which
does not require an API key. Once you have an API key, see
**[Authentication][auth]** for the unauthenticated-vs-authenticated
behaviour delta.

## Purpose

This page demonstrates the smallest useful workflow:

1. Construct a `ComtradeClient`.
2. Call `client.metadata.get_countries()` to load the country
   catalogue (no key required).
3. Call `client.trade.get_exports(...)` to fetch a year's annual
   trade flows for one reporter.
4. Print a one-line summary.

After this page you will be ready for the
**[Python SDK → Trade][python-trade]** guide for the full
parameter surface.

## Prerequisites

- `un-comtrade-sdk` installed in an active virtual environment
  (see **[Installation][install]**).
- Python 3.11+.
- No API key required for the snippet below; the public preview
  endpoint is unauthenticated.

## Walkthrough

### Step 1 — import the client

```python
from un_comtrade import ComtradeClient
```

The package exports one symbol: `ComtradeClient`. The canonical
import path is `un_comtrade.client.ComtradeClient`; the top-level
re-export is for ergonomics.

### Step 2 — instantiate the client

```python
client = ComtradeClient()
```

Without arguments, the client reads `UN_COMTRADE_KEY` from the
environment. When the variable is unset (or empty), the client
operates in **public-preview mode**, which can hit the metadata
endpoints and the preview trade endpoint.

### Step 3 — fetch the country catalogue

```python
countries = client.metadata.get_countries()
print(f"{len(countries)} countries in the catalogue")
```

The metadata service caches the catalogue on first use. The cache
lives in the user's cache directory (`~/.cache/un_comtrade/` on
Linux, `~/Library/Caches/un_comtrade/` on macOS,
`%LOCALAPPDATA%\un_comtrade\` on Windows). The cache TTL is
configurable; see **[Authentication][auth]** for the cache
configuration knobs.

### Step 4 — fetch India's 2022 exports

```python
exports = client.trade.get_exports(
    reporter_code=699,        # India
    period="2022",
    partner_code=0,           # World aggregate
)
```

The trade service returns a `CanonicalDataset` — a typed
container of `TradeRecord` dataclasses, all monetary values as
`Decimal`, all dates as ISO-8601 strings. Pagination across the
upstream API's record cap is automatic; the consumer sees a single
combined dataset.

### Step 5 — print the summary

```python
total = exports.aggregate_total()
print(f"India exported ${total:,.2f} to the world in 2022")
# → India exported $452,684,213,646.75 to the world in 2022
```

The `aggregate_total()` method sums the `primary_value` field of
every record, with full `Decimal` precision.

### Step 6 — close the client

```python
client.close()
```

Or use the context-manager form (preferred):

```python
with ComtradeClient() as client:
    exports = client.trade.get_exports(
        reporter_code=699, period="2022",
    )
    print(f"{len(exports.records):,} rows; total ${exports.aggregate_total():,.2f}")
```

The `with` block closes the underlying HTTP transport cleanly,
flushing any pooled connections.

## Examples

The full hello world in one block:

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    exports = client.trade.get_exports(
        reporter_code=699,
        period="2022",
        partner_code=0,
    )
    print(f"rows : {len(exports.records):,}")
    print(f"total: ${exports.aggregate_total():,.2f}")
```

Expected output (live API):

```
rows : 1
total: $452,684,213,646.75
```

A second variant that drills into the analytics facade:

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    exports = client.trade.get_exports(reporter_code=699, period="2022")
    top_partners = client.analytics.top_partners(
        exports, by="exports", descending=True, limit=5,
    )
    for row in top_partners:
        print(f"  {row.partner_label:<32} ${row.value:>20,.2f}")
```

Expected output:

```
  United States                        $     78,310,876,432.18
  United Arab Emirates                 $     28,029,441,003.94
  Netherlands                          $     17,253,990,765.31
  China                                $     15,861,453,118.76
  Bangladesh                           $     12,915,732,114.05
```

## Related Recipes

- **[RECIPE-001][recipe-001]** — *List reporter countries*.
  Beginner. The metadata half of this walkthrough, isolated into a
  runnable recipe.
- **[RECIPE-011][recipe-011]** — *Fetch India's annual exports*.
  Beginner. The trade half of this walkthrough, isolated into a
  runnable recipe.

## Related API

- [`un_comtrade.ComtradeClient`][api-client] — the single public
  entry point.
- [`ComtradeClient.trade`][api-trade] — the trade facade.
- [`ComtradeClient.metadata`][api-metadata] — the metadata facade.

## Related Guides

- **[Authentication][auth]** — set `UN_COMTRADE_KEY` for the
  authenticated endpoints.
- **[Python SDK → Trade][python-trade]** — full parameter surface
  for `client.trade.get_exports(...)`.
- **[Python SDK → Metadata][python-metadata]** — country, partner,
  HS-code, and unit catalogues.

## Next steps

- **[Authentication][auth]** — wire up your API key for the
  authenticated endpoints and the bulk-download surface.
- **[Python SDK → Trade][python-trade]** — drill into monthly
  granularity, partner breakdowns, HS-code filters, and the
  tariffline endpoint.
- **[Cookbook → RECIPE-011][recipe-011]** — the full executable form
  of this walkthrough.

[auth]: ../authentication/
[install]: ../installation/
[python-trade]: ../../guides/python/trade/
[python-metadata]: ../../guides/python/metadata/
[recipe-001]: ../../../recipes/metadata/01_list_countries.py
[recipe-011]: ../../../recipes/trade/01_exports.py
[api-client]: ../../api/client/
[api-trade]: ../../api/client/
[api-metadata]: ../../api/client/