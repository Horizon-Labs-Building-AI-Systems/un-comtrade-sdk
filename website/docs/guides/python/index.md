---
title: Python SDK
description: Idiomatic patterns for using the un-comtrade-sdk from Python — type hints, dataclasses, context managers, and the five service facades.
audience: python
prerequisites:
  - getting_started/installation/
  - getting_started/quick_start/
related_recipes: []
related_api:
  - un_comtrade.ComtradeClient
related_guides:
  - guides/python/metadata/
  - guides/python/trade/
  - guides/python/analytics/
  - guides/python/etl/
  - guides/python/storage/
---

# Python SDK

The Python SDK section is the entry point for **Python developers**
integrating `un-comtrade-sdk` into a script, application, or pipeline.
The SDK is designed for idiomatic Python — type hints end-to-end,
frozen dataclasses for every model, context managers for resource
cleanup, and a single lazy entry point (`ComtradeClient`) that opens
five service facades.

## Path

| Guide | Audience | What it covers |
| ----- | -------- | -------------- |
| **[Metadata][python-metadata]** | Python developers | Country / partner / HS-code catalogues, the metadata cache, the refresh flow. |
| **[Trade][python-trade]** | Python developers | Annual / monthly flows, tariffline, world totals, partner breakdowns, the pagination engine. |
| **[Analytics][python-analytics]** | Data analysts, Python developers | Country / partner / commodity / time-series / balance / comparison analytics on top of `CanonicalDataset`. |
| **[ETL][python-etl]** | Python developers | Pipeline composition, stage orchestration, configuration injection. |
| **[Storage][python-storage]** | Python developers | CSV / JSON / Parquet / DuckDB writers and readers; cross-backend round-trip equality. |

## Idiomatic patterns

### Single entry point, five facades

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    client.metadata         # MetadataService
    client.trade            # TradeService
    client.analytics        # AnalyticsEngine
    client.etl              # ETLFacade
    client.storage          # StorageRegistry
```

Each facade is a per-client singleton; constructing the client
multiple times yields independent state. The five facades never
talk to the network until you call a method on them.

### Typed return values

Every public method returns a typed object:

- `client.metadata.get_countries()` → `list[Country]`
- `client.trade.get_exports(...)` → `CanonicalDataset`
- `client.analytics.top_partners(...)` → `tuple[PartnerRankingRow, ...]`

Monetary values are `Decimal`; dates are ISO-8601 strings; enums are
`frozenset`. No raw upstream JSON ever leaks into your code.

### Error handling

Every public method raises `ComtradeError` (or a subclass) on
upstream failure. The standard pattern:

```python
from un_comtrade import ComtradeClient
from un_comtrade.exceptions import ComtradeError

try:
    with ComtradeClient() as client:
        result = client.trade.get_exports(reporter_code=699, period="2022")
except ComtradeError as exc:
    print(f"un-comtrade error: {exc}")
```

The exception hierarchy is documented in the
**[API → Exceptions][api-exceptions]** reference.

### Configuration injection

The `Configuration` dataclass controls every knob:

```python
from un_comtrade import ComtradeClient
from un_comtrade.config import Configuration

config = Configuration(
    api_key="your-key",
    retry_attempts=3,                # ADR-0008
    timeout_seconds=30,              # ADR-0011
    cache_dir="/srv/un_comtrade/cache",
    cache_ttl_seconds=86400 * 7,
)

with ComtradeClient(config) as client:
    ...
```

The full configuration surface is in the
**[API → Models][api-models]** reference.

## Related API

- [`un_comtrade.ComtradeClient`][api-client] — the single public
  entry point.
- [`un_comtrade.config.Configuration`][api-models] — the typed
  configuration object.

## Related Guides

- **[Metadata][python-metadata]** — reference catalogues.
- **[Trade][python-trade]** — annual / monthly trade flows.
- **[Analytics][python-analytics]** — typed analytics functions.
- **[ETL][python-etl]** — pipeline composition.
- **[Storage][python-storage]** — persistence backends.

## Next steps

- **[Trade][python-trade]** — the most common entry point.
- **[Analytics][python-analytics]** — drill into the typed analytics
  layer.
- **[Cookbook → Python recipes][cookbook-index]** — runnable code
  for every page in this section.

[python-metadata]: metadata/
[python-trade]: trade/
[python-analytics]: analytics/
[python-etl]: etl/
[python-storage]: storage/
[cookbook-index]: ../../cookbook/
[api-client]: ../../api/client/
[api-exceptions]: ../../api/exceptions/
[api-models]: ../../api/models/