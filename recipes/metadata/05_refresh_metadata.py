"""
---
recipe_id: RECIPE-005
title: Refresh the metadata cache
category: metadata
difficulty: beginner
sdk_version: >=1.0.2
requires_api_key: no
estimated_runtime: <1s
inputs:
  required: []
  optional:
    - name: cache_dir
      type: str
      default: "./cache"
      description: |
        Directory where the metadata cache is persisted.
        Created if it does not exist. Defaults to
        ``./cache`` so the recipe is self-contained.
    - name: resource_id
      type: str
      default: "R02"
      description: |
        Resource id to populate before refreshing. The
        default ``R02`` is the reporter catalogue
        (countries). Other valid ids include
        ``R03`` (partners), ``R05`` (HS per-edition;
        requires ``--edition``), ``R10`` (trade
        flows), ``R14`` (quantity units).
    - name: edition
      type: str
      default: "2022"
      description: |
        HS edition; only consulted when ``resource_id``
        is ``R05``.
outputs:
  - kind: stdout
    path: null
    description: |
      A short human-readable report showing:

      1. the number of records returned by the cold
         fetch that populated the cache;
      2. the cache state immediately before
         ``refresh_all``;
      3. the number of cache keys invalidated by
         ``refresh_all``;
      4. the cache state immediately after the
         invalidation.
related_docs:
  - docs/007_SDK_SPECIFICATION.md
  - docs/008_METADATA_LAYER_SPEC.md
  - docs/010_INFRASTRUCTURE_SPEC.md
related_recipes:
  - RECIPE-001
tags:
  - metadata
  - cache
  - refresh
---

Recipe 05 — Refresh the metadata cache.

Per ADR-0024 the metadata cache survives process
restarts. The cache is **manually refreshed**: the
consumer decides when to throw away the cached
payloads and re-fetch from upstream. The
``MetadataCache.refresh_all()`` method invalidates
every key (memory and disk) and returns the count of
keys that were removed.

The recipe:

1. Builds a ``ComtradeClient`` with a caller-supplied
   ``MetadataCache`` rooted at a configurable directory
   (default ``./cache``).
2. Performs a cold fetch of the requested resource
   (``R02`` by default — the reporter catalogue). The
   first call writes to the cache.
3. Performs a second fetch of the same resource. The
   cache hit is silent — no upstream call.
4. Calls ``cache.refresh_all()`` and prints the
   invalidated-key count.
5. Performs a third fetch. The cache is cold again;
   the upstream is hit, the cache is re-populated.

Expected output (mock-mode)::

    == Recipe 05: Refresh Metadata Cache ==
    Cache directory: ./cache
    Step 1: cold fetch of R02 (countries) ...
      247 records returned
      cache keys after cold fetch: ['R02']
    Step 2: warm fetch (should hit cache) ...
      247 records returned
      cache keys unchanged: ['R02']
    Step 3: refresh_all() ...
      1 key(s) invalidated
    Step 4: cold fetch (should miss cache) ...
      247 records returned
      cache keys after re-fetch: ['R02']
    Done — the cache is in a consistent state.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Mapping

from un_comtrade import ComtradeClient
from un_comtrade.cache import MetadataCache
from un_comtrade.config import Configuration
from un_comtrade.models import Country, HSCode, Partner
from un_comtrade.parser import MetadataParser


# ---- demo ------------------------------------------------------------------


def refresh_metadata_demo(
    client: ComtradeClient,
    *,
    resource_id: str = "R02",
    edition: str = "2022",
) -> dict[str, object]:
    """Demonstrate the cache-then-refresh-then-re-fetch cycle.

    The function takes a ``ComtradeClient`` that MUST have
    a ``MetadataCache`` configured (``client.metadata.cache``
    is not ``None``). The script's ``main()`` wires up the
    real cache; the regression test injects a temporary
    cache so it can run offline.

    The function returns a small dict so the regression
    test can assert on the observed state without
    re-parsing stdout.

    Parameters
    ----------
    client
        A ``ComtradeClient`` whose ``metadata`` service
        has a configured ``MetadataCache``. The demo
        raises ``RuntimeError`` when the cache is
        missing — the demo is meaningless without one.
    resource_id
        Resource id to populate before refreshing.
        Defaults to ``"R02"`` (the reporter catalogue).
    edition
        HS edition; only consulted when ``resource_id``
        is ``"R05"``. Ignored otherwise.

    Returns
    -------
    dict[str, object]
        A snapshot containing the per-step record
        counts and the cache state after each step.
    """
    # Step 0 — sanity check the precondition. The
    # recipe is about the cache, so a client without
    # a cache is a misuse, not a runtime concern.
    if client.metadata.cache is None:
        raise RuntimeError(
            "refresh_metadata_demo requires a client with "
            "a configured MetadataCache; pass cache=... to "
            "ComtradeClient"
        )
    cache_dir = client.metadata.cache.cache_dir
    print(f"Cache directory: {cache_dir}")

    # Step 1 — cold fetch. ``get_countries`` delegates
    # to R02; the cache is empty so the upstream is
    # hit. The returned list is the parsed canonical
    # models.
    print(f"Step 1: cold fetch of {resource_id} ...")
    records_1 = _fetch_for_resource(client, resource_id, edition)
    keys_after_cold = sorted(client.metadata.cache.keys())
    print(f"  {len(records_1)} records returned")
    print(f"  cache keys after cold fetch: {keys_after_cold}")

    # Step 2 — warm fetch. The cache holds the
    # payload from step 1; the upstream is not
    # touched. The returned list is the same
    # canonical models.
    print("Step 2: warm fetch (should hit cache) ...")
    records_2 = _fetch_for_resource(client, resource_id, edition)
    keys_after_warm = sorted(client.metadata.cache.keys())
    print(f"  {len(records_2)} records returned")
    print(f"  cache keys unchanged: {keys_after_warm}")

    # Step 3 — refresh. ``refresh_all`` returns the
    # number of unique keys that were removed
    # across memory and disk. With one resource
    # cached, the count is 1.
    print("Step 3: refresh_all() ...")
    invalidated = client.metadata.cache.refresh_all()
    print(f"  {invalidated} key(s) invalidated")

    # Step 4 — re-fetch. The cache is empty again
    # so the upstream is hit. The cache is
    # re-populated to its previous state.
    print("Step 4: cold fetch (should miss cache) ...")
    records_3 = _fetch_for_resource(client, resource_id, edition)
    keys_after_refetch = sorted(client.metadata.cache.keys())
    print(f"  {len(records_3)} records returned")
    print(f"  cache keys after re-fetch: {keys_after_refetch}")

    print("Done — the cache is in a consistent state.")
    return {
        "records_cold": len(records_1),
        "records_warm": len(records_2),
        "records_refetch": len(records_3),
        "invalidated": invalidated,
        "keys_after_cold": keys_after_cold,
        "keys_after_warm": keys_after_warm,
        "keys_after_refetch": keys_after_refetch,
    }


def _fetch_for_resource(
    client: ComtradeClient,
    resource_id: str,
    edition: str,
) -> list[object]:
    """Dispatch to the right ``client.metadata`` method by resource id.

    The dispatcher keeps the recipe focused: callers do
    not need to know the exact method name for each
    resource. New resource ids are added by extending
    this function.
    """
    if resource_id == "R02":
        return client.metadata.get_countries()  # list[Country]
    if resource_id == "R03":
        return client.metadata.get_partners()  # list[Partner]
    if resource_id == "R05":
        return client.metadata.get_hs_codes(edition)  # list[HSCode]
    raise ValueError(
        f"Unsupported resource_id for this recipe: {resource_id!r}; "
        f"supported: R02, R03, R05"
    )


# ---- main ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Build a real ``ComtradeClient`` and run the demo."""
    parser = argparse.ArgumentParser(
        prog="RECIPE-005",
        description=__doc__,
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("./cache"),
        help="Directory where the cache is persisted (default: ./cache).",
    )
    parser.add_argument(
        "--resource",
        default="R02",
        help="Resource id to populate (default: R02).",
    )
    parser.add_argument(
        "--edition",
        default="2022",
        help="HS edition; only used when --resource=R05 (default: 2022).",
    )
    args = parser.parse_args(argv)

    args.cache_dir.mkdir(parents=True, exist_ok=True)
    cache = MetadataCache(args.cache_dir)
    config = Configuration(api_key=os.environ.get("UN_COMTRADE_KEY") or None)
    sdk_parser = MetadataParser(log_skipped=False)
    with ComtradeClient(config, parser=sdk_parser, cache=cache) as client:
        refresh_metadata_demo(
            client,
            resource_id=args.resource,
            edition=args.edition,
        )
    return 0


if __name__ == "__main__":
    print("== Recipe 05: Refresh Metadata Cache ==")
    raise SystemExit(main())
