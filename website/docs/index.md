---
title: un-comtrade-sdk
description: A Pythonic client for the UN Comtrade API — fetch trade data, parse it into canonical models, persist it, and analyse it.
audience: all
prerequisites: []
related_recipes:
  - RECIPE-001
  - RECIPE-011
  - RECIPE-021
  - RECIPE-091
related_api:
  - un_comtrade.ComtradeClient
  - un_comtrade.client.ComtradeClient
related_guides:
  - getting_started/index.md
  - cookbook/index.md
  - api/index.md
  - architecture/index.md
---

# un-comtrade-sdk

A Pythonic client for the **UN Comtrade** (UNSD) trade statistics API.
The SDK ships a single public entry point —
[`ComtradeClient`][un_comtrade.ComtradeClient] — that opens five service
facades (`metadata`, `trade`, `analytics`, `etl`, `storage`), each
typed, documented, and tested against the live API plus a deterministic
offline mock.

The package targets the **public preview** and **subscription-backed**
endpoints of the upstream service, plus the reference catalogues
(countries, partners, HS codes, units), the bulk-download and
async-request surfaces, and a local storage layer that round-trips
canonical `Decimal`-accurate trade records across CSV, JSON, Parquet,
and DuckDB.

## What you get

| Layer      | Purpose                                                           | Entry point                          |
| ---------- | ----------------------------------------------------------------- | ------------------------------------ |
| `metadata` | Reference catalogues (countries, partners, HS codes, units, …)    | [`client.metadata`][un_comtrade.client.ComtradeClient.metadata] |
| `trade`    | Annual and monthly trade flows, tariffline, world totals          | [`client.trade`][un_comtrade.client.ComtradeClient.trade]       |
| `analytics`| Country, partner, commodity, time-series, balance, comparison    | [`client.analytics`][un_comtrade.client.ComtradeClient.analytics] |
| `etl`      | Pipeline orchestration with shared configuration injection        | [`client.etl`][un_comtrade.client.ComtradeClient.etl]       |
| `storage`  | CSV / JSON / Parquet / DuckDB writers and readers                 | [`client.storage`][un_comtrade.client.ComtradeClient.storage]   |

## Purpose

This site is the **user-facing documentation** for `un-comtrade-sdk`.
It is written for six audiences:

- **First-time users** — install the SDK and run a hello-world query.
- **Python developers** — integrate the SDK into a script or
  application.
- **CLI users** — drive the SDK from a terminal and pipe output to
  other Unix tools.
- **Data analysts** — explore UN Comtrade trade data interactively
  with pandas, Jupyter, DuckDB, or Parquet.
- **Contributors** — extend the SDK; add a new analytics function or
  a new storage backend.
- **Maintainers** — cut a release; deprecate pages; write migration
  guides.

The seven sections of this site (sidebar on the left) map one-to-one
to those audiences. The **Cookbook** is the executable source of
every code example you see on this site — guide pages link to recipes
rather than duplicating code.

## Prerequisites

None for browsing this site. To run the code snippets you see:

- **Python 3.11 or newer** (the SDK declares `requires-python=">=3.11"`).
- `pip` available on your `PATH`.
- Optional: a `UN_COMTRADE_KEY` environment variable if you want to
  exercise the authenticated endpoints (preview and reference metadata
  work without a key; the annual / monthly trade data and the
  subscription-grade limits do not).

## Walkthrough

### Hello world — fetch India's 2022 exports

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    result = client.trade.get_exports(reporter_code=699, period="2022")

print(f"{len(result.records):,} rows fetched")
print(f"Total export value: ${result.aggregate_total():,.2f}")
```

The `with` block closes the underlying HTTP transport cleanly. The
`ComtradeClient` reads `UN_COMTRADE_KEY` from the environment when
present; an unauthenticated client still works against the public
preview endpoints.

### Hello world — list countries and look up India

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    countries = client.metadata.get_countries()
    india = client.metadata.get_country(699)

print(f"{len(countries)} countries in the catalogue")
print(f"India: {india.display_name} ({india.iso_alpha3})")
```

No API key is required for the metadata layer. The catalogue is
cached on first use and refreshed on a configurable cadence.

### Hello world — top five partners for India's 2022 exports

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    exports = client.trade.get_exports(reporter_code=699, period="2022")

# Drill into the analytics facade for the ranking.
top5 = client.analytics.top_partners(
    exports, by="exports", descending=True, limit=5,
)

for row in top5:
    print(f"  {row.partner_label:<32}  ${row.value:>20,.2f}")
```

Every analytics function takes a [`CanonicalDataset`][un_comtrade.CanonicalDataset]
(or any `Iterable[TradeRecord]` produced by the trade layer) and
returns typed, `frozen=True` result objects — no raw upstream
JSON ever leaks into your code.

### Hello world — persist the dataset to Parquet

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    exports = client.trade.get_exports(reporter_code=699, period="2022")

# Round-trip via the public storage registry.
client.storage.open("india_exports_2022.parquet").write(exports)
```

The storage layer auto-detects the backend from the file extension.
Re-loading the same file yields a `CanonicalDataset` that compares
**byte-for-byte equal** to the original — `Decimal` arithmetic
preserved, ISO-8601 dates preserved, `frozenset` enums preserved.

## Examples

Run the snippets above against the deterministic offline mock:

```python
from unittest.mock import patch
from un_comtrade import ComtradeClient

with patch("un_comtrade.transport.HttpTransport") as MockTransport:
    MockTransport.return_value.get.return_value.json.return_value = {
        "data": [
            {
                "refPeriodId": 2022,
                "reporterCode": 699,
                "reporterISO": "IND",
                "partnerCode": 0,
                "partnerISO": "WLD",
                "flowCode": "X",
                "flowDesc": "Export",
                "cmdCode": "TOTAL",
                "primaryValue": 452_684_213_646.747,
            }
        ]
    }
    with ComtradeClient() as client:
        result = client.trade.get_exports(reporter_code=699, period="2022")
        assert result.aggregate_total() > 0
```

Every documentation page follows the **mock-mode** pattern for
offline CI verification — the build pipeline runs a syntax check on
every fenced Python block and the CB-008 verification layer confirms
that the example imports only public symbols.

## Related Recipes

| ID         | Title                                       | Difficulty  |
| ---------- | ------------------------------------------- | ----------- |
| RECIPE-001 | List reporter countries                     | beginner    |
| RECIPE-011 | Fetch India's annual exports                | beginner    |
| RECIPE-021 | Compute a country trade balance             | beginner    |
| RECIPE-091 | Drive metadata commands from the CLI        | beginner    |

See the [Cookbook][cookbook-index] for the full table of 29 recipes
across metadata, trade, analytics, storage, CLI, and end-to-end
pipelines.

## Related API

- [`un_comtrade.ComtradeClient`][un_comtrade.ComtradeClient] — the
  single public entry point.
- [`un_comtrade.client.ComtradeClient`][un_comtrade.client.ComtradeClient]
  — the canonical import path.
- Five lazy service attributes: `metadata`, `trade`, `analytics`,
  `etl`, `storage`.

The full reference is generated from docstrings via
[mkdocstrings][mkdocstrings] and lives under the
[API][api-index] section.

## Related Guides

- [Getting Started][getting-started-index] — install, configure, run
  a first query.
- [Cookbook][cookbook-index] — 29 runnable recipes grouped by
  category.
- [API Reference][api-index] — generated reference for every public
  symbol.
- [Architecture][architecture-index] — SDK design, contributing,
  release process.

## Next steps

- New to the SDK? Read **[Getting Started → Installation][install]**
  to install `un-comtrade-sdk` from PyPI.
- Want a working query in five minutes? Jump to
  **[Getting Started → Quick Start][quick-start]**.
- Looking for runnable code? Browse the **[Cookbook][cookbook-index]**.
- Want the API surface? Open the **[API Reference][api-index]**.
- Building a pipeline? Read the
  **[Python SDK → ETL][python-etl]** guide.

[un_comtrade.ComtradeClient]: ../api/client/
[un_comtrade.client.ComtradeClient]: ../api/client/
[un_comtrade.client.ComtradeClient.metadata]: ../api/client/
[un_comtrade.client.ComtradeClient.trade]: ../api/client/
[un_comtrade.client.ComtradeClient.analytics]: ../api/client/
[un_comtrade.client.ComtradeClient.etl]: ../api/client/
[un_comtrade.client.ComtradeClient.storage]: ../api/client/
[un_comtrade.CanonicalDataset]: ../api/models/
[cookbook-index]: ../cookbook/
[api-index]: ../api/
[architecture-index]: ../architecture/
[getting-started-index]: ../getting_started/
[install]: ../getting_started/installation/
[quick-start]: ../getting_started/quick_start/
[python-etl]: ../guides/python/etl/
[mkdocstrings]: https://mkdocstrings.github.io/