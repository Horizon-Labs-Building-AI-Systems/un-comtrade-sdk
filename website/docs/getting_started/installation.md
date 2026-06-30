---
title: Install the SDK
description: Install un-comtrade-sdk from PyPI, verify the install, and prepare the development environment for offline work.
audience: first-time
prerequisites: []
related_recipes:
  - RECIPE-001
related_api:
  - un_comtrade.ComtradeClient
  - un_comtrade.__version__
related_guides:
  - getting_started/quick_start/
  - getting_started/authentication/
  - cookbook/index/
---

# Install the SDK

`un-comtrade-sdk` ships to PyPI as the distribution **`un-comtrade-sdk`**,
importable as the package **`un_comtrade`**. The minimum supported Python
is **3.11**; the maximum tested Python is **3.13**. The package is
typed end-to-end and has zero required dependencies outside the Python
standard library plus `httpx` for transport.

## Purpose

This page covers the supported install paths, the optional
dependency groups, the offline-mode setup, and the verification step
that confirms the install succeeded. After this page you will be
ready for **[Quick Start → Run your first query][quick-start]**.

## Prerequisites

- A working Python 3.11+ interpreter (`python --version` should
  print `Python 3.11.x` or newer).
- `pip` available on your `PATH` (`pip --version` should print a
  recent pip).
- A virtual environment is **strongly recommended** to keep SDK
  dependencies isolated from system packages.

## Walkthrough

### Recommended — install in a virtual environment

=== "macOS / Linux"

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    pip install un-comtrade-sdk
    python -c "import un_comtrade; print(un_comtrade.__version__)"
    ```

=== "Windows (PowerShell)"

    ```powershell
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install un-comtrade-sdk
    python -c "import un_comtrade; print(un_comtrade.__version__)"
    ```

    On Windows you may also need `tzdata` for the `zoneinfo` module:

    ```powershell
    pip install tzdata
    ```

The last command should print the installed SDK version
(currently `1.0.1`). If you see `ModuleNotFoundError: No module
named 'un_comtrade'`, your virtual environment is not active.

### Optional dependency groups

```bash
pip install un-comtrade-sdk[parquet]   # pyarrow-backed writer + reader
pip install un-comtrade-sdk[duckdb]    # DuckDB writer + reader
pip install un-comtrade-sdk[all]       # every optional backend
pip install un-comtrade-sdk[dev]       # pytest, ruff, mypy, build, twine
```

The `[all]` extra is recommended if you intend to round-trip data
across storage backends. The `[dev]` extra is what contributors and
release engineers use to run the full test suite locally.

### Install from source

```bash
git clone https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk.git
cd un-comtrade-sdk
pip install -e .[all,dev]
pytest tests/ -x
```

The editable install (`-e`) lets you edit SDK source and re-run tests
without re-installing. The full test suite currently runs **3,117**
tests across 38 modules; the run finishes in well under a minute on
a modern laptop.

### Install the docs toolchain (optional)

To build this documentation site locally:

```bash
pip install -r website/requirements-docs.txt
python scripts/build_docs.py
```

The `scripts/build_docs.py` script runs `mkdocs build --strict` and
the eight-step verification harness (link check, orphan detection,
duplicate-nav check, API-page count, recipe-link validity,
example compilation, search-index build).

### Offline mode

If you need to use the SDK without network access (CI runners,
air-gapped notebooks, classroom settings), the metadata layer
ships with **bundled reference data** in the package — countries,
partners, HS codes, and units are available without any HTTP call.
Trade and analytics layers require a `CanonicalDataset`; either
load one from a local storage backend or run a recipe against the
deterministic mock transport that ships with the test suite.

## Examples

Verify the install:

```python
import un_comtrade

print(un_comtrade.__version__)           # 1.0.1
print(un_comtrade.ComtradeClient)        # <class 'un_comtrade.client.ComtradeClient'>
```

Construct the client without making any network call:

```python
from un_comtrade import ComtradeClient

# No `with` block yet — instantiation is lazy and does not I/O.
client = ComtradeClient(api_key=None)
print(client.metadata)                   # MetadataService facade
print(client.trade)                      # TradeService facade
print(client.analytics)                  # AnalyticsEngine facade
print(client.etl)                        # ETLFacade facade
print(client.storage)                    # StorageRegistry facade
```

The five service attributes are lazily constructed and per-client
singletons. None of them talk to the network until you call a method
on them.

## Related Recipes

- **[RECIPE-001][recipe-001]** — *List reporter countries*. Beginner.
  Verifies the install end-to-end by fetching the country catalogue
  and printing the first five entries.

## Related API

- [`un_comtrade.ComtradeClient`][api-client] — the single public entry
  point, re-exported from `un_comtrade/__init__.py`.
- [`un_comtrade.__version__`][api-models] — the package version
  constant.

## Related Guides

- **[Quick Start][quick-start]** — run your first query against the
  live API.
- **[Authentication][auth]** — set the `UN_COMTRADE_KEY` environment
  variable for the authenticated endpoints.
- **[Cookbook][cookbook-index]** — 29 runnable recipes grouped by
  category.

## Next steps

- **[Quick Start][quick-start]** — write your first trade query in
  under five minutes.
- **[Authentication][auth]** — wire up your UN Comtrade API key for
  the authenticated endpoints.

[quick-start]: ../quick_start/
[auth]: ../authentication/
[cookbook-index]: ../../cookbook/
[recipe-001]: ../../../recipes/metadata/01_list_countries.py
[api-client]: ../../api/client/
[api-models]: ../../api/models/