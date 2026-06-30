---
title: Getting Started
description: Install the SDK, run your first query, and configure authentication for the authenticated endpoints.
audience: first-time
prerequisites: []
related_recipes:
  - RECIPE-001
  - RECIPE-011
related_api:
  - un_comtrade.ComtradeClient
related_guides:
  - getting_started/installation/
  - getting_started/quick_start/
  - getting_started/authentication/
---

# Getting Started

The Getting Started section is the entry point for **first-time users**
and **CLI users**. Three pages take you from a fresh Python install to
a working authenticated query against the UN Comtrade API.

## Path

| Page | Time | What you will do |
| ---- | ---- | ---------------- |
| **[Installation][install]** | 2 min | `pip install un-comtrade-sdk`, verify the version, set up an optional dependency group. |
| **[Quick Start][quick-start]** | 5 min | Fetch India's 2022 exports and print a one-line summary. No API key required. |
| **[Authentication][auth]** | 5 min | Wire up `UN_COMTRADE_KEY`, choose preview-vs-subscription, configure the metadata cache. |

After these three pages, jump to the
**[Python SDK → Trade][python-trade]** guide or browse the
**[Cookbook][cookbook-index]** for runnable recipes.

## What you should already know

- Basic Python — interpreter installed, `pip` understood.
- Comfortable opening a terminal (POSIX shell or PowerShell).
- No prior knowledge of the UN Comtrade API, the SDK, or the trade
  data format is required.

## Pages

### [Installation][install]

The minimum viable install. Includes the optional dependency groups
(`parquet`, `duckdb`, `all`, `dev`), the source-tree install for
contributors, and the offline-mode notes for air-gapped environments.

### [Quick Start][quick-start]

A five-minute walkthrough that constructs the client, fetches the
country catalogue, fetches India's 2022 exports, and prints a one-line
summary. No API key required.

### [Authentication][auth]

Wires up `UN_COMTRADE_KEY`, distinguishes preview-vs-subscription
modes, configures the metadata cache directory, and explains the
rate-limit handling.

## Related Recipes

- **[RECIPE-001][recipe-001]** — *List reporter countries*. Beginner.
- **[RECIPE-011][recipe-011]** — *Fetch India's annual exports*.
  Beginner.

## Related API

- [`un_comtrade.ComtradeClient`][api-client] — the single public entry
  point.

## Related Guides

- **[Installation][install]** — install the SDK.
- **[Quick Start][quick-start]** — run your first query.
- **[Authentication][auth]** — configure the API key.

## Next steps

- **[Python SDK → Trade][python-trade]** — full parameter surface for
  the trade facade.
- **[Cookbook][cookbook-index]** — 29 runnable recipes grouped by
  category.

[install]: installation/
[quick-start]: quick_start/
[auth]: authentication/
[python-trade]: ../guides/python/trade/
[cookbook-index]: ../cookbook/
[recipe-001]: ../../recipes/metadata/01_list_countries.py
[recipe-011]: ../../recipes/trade/01_exports.py
[api-client]: ../api/client/