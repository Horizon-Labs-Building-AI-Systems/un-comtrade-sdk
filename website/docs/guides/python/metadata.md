---
title: Metadata in Python
description: Fetch country, partner, HS-code, and unit catalogues from the UN Comtrade API; cache them locally; refresh on demand.
audience: python
prerequisites:
  - getting_started/quick_start/
  - guides/python/index/
related_recipes:
  - RECIPE-001
  - RECIPE-002
  - RECIPE-003
  - RECIPE-004
  - RECIPE-005
related_api:
  - un_comtrade.ComtradeClient
  - un_comtrade.client.ComtradeClient.metadata
related_guides:
  - guides/python/trade/
  - getting_started/authentication/
---

# Metadata

The metadata layer exposes the UN Comtrade reference catalogues:
**countries** (the reporters and partners), **HS codes** (the
commodity classification), **units** (the measurement units), and
**trade classifications** (the standard HS revisions). Every catalogue
is cached on first use and refreshable on demand.

## Purpose

This page covers:

1. The `MetadataService` interface.
2. The country, partner, HS-code, and unit catalogues.
3. The cache lifecycle (load → cache → refresh).
4. The offline-mode fallback.

## Prerequisites

- `un-comtrade-sdk` installed (see
  **[Installation][install]**).
- The `ComtradeClient` instantiated (see
  **[Quick Start][quick-start]**).
- No API key required for the metadata endpoints.

## Walkthrough

### List countries

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    countries = client.metadata.get_countries()
    print(f"{len(countries)} countries")
```

`get_countries()` returns `list[Country]` — a typed list of
frozen dataclasses. Each `Country` exposes `country_code`,
`iso_alpha2`, `iso_alpha3`, and `display_name`.

### Look up a single country

```python
with ComtradeClient() as client:
    india = client.metadata.get_country(699)
    print(f"{india.display_name} ({india.iso_alpha3})")
```

Returns `Country | None` — `None` when the code is not in the
catalogue.

### Search countries by name

```python
with ComtradeClient() as client:
    matches = client.metadata.search_countries("india")
    for c in matches:
        print(f"  {c.country_code} {c.display_name}")
```

Returns `list[Country]` ordered by ISO code. Search is
case-insensitive and matches against the display name and ISO
alpha-2/3 codes.

### List HS codes at a given level

```python
with ComtradeClient() as client:
    hs2 = client.metadata.get_hs_codes(level=2)
    print(f"{len(hs2)} HS-2 codes")
```

The `level` argument is 2, 4, or 6 for HS chapters, headings, and
subheadings respectively. Returns `list[HSCode]` — each entry
exposes `code`, `description`, and `level`.

### Refresh the catalogue

```python
with ComtradeClient() as client:
    client.metadata.refresh()
```

The `refresh()` method clears the cache, re-downloads every
catalogue, and writes the new snapshot to disk. Rate-limited to one
HTTP call per second per ADR-0035.

### Configure the cache directory

```python
from un_comtrade import ComtradeClient
from un_comtrade.config import Configuration

config = Configuration(cache_dir="/srv/un_comtrade/cache")
with ComtradeClient(config) as client:
    countries = client.metadata.get_countries()
```

See **[Authentication → Configure the cache directory][cache]** for
the full configuration surface.

## Examples

Drill into the country catalogue after a refresh:

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    client.metadata.refresh()
    countries = client.metadata.get_countries()

# Snapshot the catalogue for offline use.
import json
with open("countries.json", "w") as f:
    json.dump(
        [
            {"code": c.country_code, "iso3": c.iso_alpha3, "name": c.display_name}
            for c in countries
        ],
        f, indent=2,
    )
```

Search by ISO code (faster than text search):

```python
with ComtradeClient() as client:
    matches = client.metadata.search_countries("IN")
    print(matches[0].country_code, matches[0].display_name)
# → 699 India
```

## Related Recipes

- **[RECIPE-001][recipe-001]** — *List reporter countries*.
- **[RECIPE-002][recipe-002]** — *List partner countries*.
- **[RECIPE-003][recipe-003]** — *List HS codes at a level*.
- **[RECIPE-004][recipe-004]** — *Search HS codes by description*.
- **[RECIPE-005][recipe-005]** — *Refresh metadata catalogues*.

## Related API

- [`ComtradeClient.metadata`][api-metadata] — the metadata facade.
- [`MetadataService.get_countries`][api-client] — the country
  catalogue accessor.

## Related Guides

- **[Trade][python-trade]** — uses the country catalogue to resolve
  reporter and partner codes.
- **[Authentication → Configure the cache directory][cache]** —
  full cache configuration surface.

## Next steps

- **[Trade][python-trade]** — apply the metadata catalogues to a
  real trade query.
- **[Cookbook → metadata recipes][cookbook-metadata]** — full
  executable forms.

[install]: ../../getting_started/installation/
[quick-start]: ../../getting_started/quick_start/
[cache]: ../../getting_started/authentication/
[python-trade]: ../trade/
[cookbook-metadata]: ../../cookbook/metadata/
[recipe-001]: ../../../recipes/metadata/01_list_countries.py
[recipe-002]: ../../../recipes/metadata/02_list_partners.py
[recipe-003]: ../../../recipes/metadata/03_list_hs_codes.py
[recipe-004]: ../../../recipes/metadata/04_search_hs.py
[recipe-005]: ../../../recipes/metadata/05_refresh_metadata.py
[api-client]: ../../api/client/
[api-metadata]: ../../api/client/