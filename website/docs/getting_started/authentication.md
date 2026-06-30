---
title: Configure authentication
description: Set the UN_COMTRADE_KEY environment variable, choose between preview and subscription tiers, and configure the cache directory.
audience: first-time
prerequisites:
  - getting_started/installation/
related_recipes:
  - RECIPE-005
related_api:
  - un_comtrade.ComtradeClient
  - un_comtrade.config.Configuration
related_guides:
  - getting_started/quick_start/
  - getting_started/installation/
---

# Authentication

The UN Comtrade API has two modes:

- **Public preview** — no API key required; metadata catalogues plus
  the preview trade endpoint (a 500-record cap per call).
- **Subscription** — `UN_COMTRADE_KEY` required; full annual /
  monthly trade history, the tariffline endpoint, bulk downloads,
  async requests, and the 50,000,000-record-per-day cap.

The SDK supports both modes transparently. The client inspects
`UN_COMTRADE_KEY` at construction time and routes requests to the
appropriate upstream endpoint.

## Purpose

This page covers:

1. How to obtain a UN Comtrade API key.
2. How to set `UN_COMTRADE_KEY` on each platform.
3. The configuration knobs (`Configuration`) and how they map to
   the public-preview-vs-subscription delta.
4. How to verify the key is wired correctly.

## Prerequisites

- A UN Comtrade account. Sign up at
  <https://uncomtrade.un.org/> if you don't have one.
- The key value, obtainable from
  <https://uncomtrade.un.org/db/help/uReadApiHelp.cfm> (after login).
- `un-comtrade-sdk` installed (see **[Installation][install]**).

## Walkthrough

### Step 1 — set the environment variable

=== "macOS / Linux"

    ```bash
    # ~/.bashrc, ~/.zshrc, or your shell's startup file
    export UN_COMTRADE_KEY="your-32-char-key-here"
    ```

=== "Windows (PowerShell)"

    ```powershell
    # Current user, current session
    [Environment]::SetEnvironmentVariable(
        "UN_COMTRADE_KEY", "your-32-char-key-here", "User"
    )
    ```

=== "Windows (cmd)"

    ```cmd
    setx UN_COMTRADE_KEY "your-32-char-key-here"
    ```

Restart your terminal (or re-source your shell init file) so the
variable is picked up.

### Step 2 — verify the key

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    print(f"auth mode : {client.config.auth_mode}")
    print(f"base URL  : {client.config.base_url}")
```

Expected output for a wired key:

```
auth mode : subscription
base URL  : https://comtradeapi.un.org/data/v1
```

Without a key:

```
auth mode : preview
base URL  : https://comtradeapi.un.org/data/v1
```

Both URLs hit the same upstream host; the `subscription` mode adds
the `subscription-key` header to every request.

### Step 3 — configure the cache directory

The metadata layer caches reference catalogues on first use. The
default location is platform-specific:

| Platform | Default cache dir                            |
| -------- | -------------------------------------------- |
| Linux    | `~/.cache/un_comtrade/`                      |
| macOS    | `~/Library/Caches/un_comtrade/`              |
| Windows  | `%LOCALAPPDATA%\un_comtrade\`                |

Override with the `cache_dir` configuration knob:

```python
from un_comtrade import ComtradeClient
from un_comtrade.config import Configuration

config = Configuration(
    api_key="your-key",
    cache_dir="/srv/un_comtrade/cache",
    cache_ttl_seconds=86400 * 7,    # 7 days
)

with ComtradeClient(config) as client:
    countries = client.metadata.get_countries()
```

### Step 4 — refresh the metadata catalogue

The cache TTL is 7 days by default. To force a refresh:

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    client.metadata.refresh()    # re-download + re-parse all catalogues
    countries = client.metadata.get_countries()
```

The `refresh()` method clears the cache, downloads every reference
catalogue, and writes the new snapshot to disk. It is rate-limited
to one HTTP call per second per ADR-0035.

### Step 5 — handle the rate limit

The UN Comtrade service imposes a soft rate limit (≈1 request per
second, token-bucket refill; no rate-limit headers). The SDK honours
the limit automatically with `Retry-After: 1` handling:

```python
from un_comtrade import ComtradeClient
from un_comtrade.exceptions import ComtradeError

try:
    with ComtradeClient() as client:
        for period in range(2010, 2024):
            exports = client.trade.get_exports(
                reporter_code=699, period=str(period),
            )
            print(f"{period}: ${exports.aggregate_total():,.2f}")
except ComtradeError as exc:
    print(f"un-comtrade error: {exc}")
```

The SDK retries up to 3 times (per ADR-0008) before raising
`ComtradeError`. Override with `retry_attempts=5` in the
`Configuration` if your workload justifies it.

## Examples

Construct an explicitly authenticated client without an env var:

```python
from un_comtrade import ComtradeClient

with ComtradeClient(api_key="your-32-char-key-here") as client:
    exports = client.trade.get_exports(reporter_code=699, period="2022")
    print(f"${exports.aggregate_total():,.2f}")
```

Construct a preview-mode client explicitly (ignoring any env var):

```python
from un_comtrade import ComtradeClient

with ComtradeClient(api_key=None) as client:
    countries = client.metadata.get_countries()
    print(f"{len(countries)} countries")
```

The `api_key=None` short-form is useful in CI runners that share
the same shell with a developer machine where the env var is set.

## Related Recipes

- **[RECIPE-005][recipe-005]** — *Refresh metadata catalogues*.
  Beginner. Forces a cache refresh and prints the catalogue sizes.

## Related API

- [`un_comtrade.ComtradeClient`][api-client] — the single public
  entry point.
- [`un_comtrade.config.Configuration`][api-models] — the typed
  configuration object.

## Related Guides

- **[Installation][install]** — install the SDK and verify the
  version.
- **[Quick Start][quick-start]** — run your first query.

## Next steps

- **[Python SDK → Trade][python-trade]** — full parameter surface
  for the trade facade.
- **[Architecture → SDK Overview][arch-overview]** — how the auth
  mode flows from `Configuration` to the request layer.

[install]: ../installation/
[quick-start]: ../quick_start/
[python-trade]: ../../guides/python/trade/
[arch-overview]: ../../architecture/sdk_overview/
[recipe-005]: ../../../recipes/metadata/05_refresh_metadata.py
[api-client]: ../../api/client/
[api-models]: ../../api/models/