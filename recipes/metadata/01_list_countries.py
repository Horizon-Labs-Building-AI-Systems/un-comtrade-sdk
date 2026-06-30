"""
---
recipe_id: RECIPE-001
title: List reporter countries
category: metadata
difficulty: beginner
sdk_version: >=1.0.2
requires_api_key: no
estimated_runtime: <1s
inputs:
  required: []
  optional: []
outputs:
  - kind: stdout
    path: null
    description: |
      A short human-readable report containing the total
      number of countries, the first five entries, and a
      focused look-up of India (reporter code 699).
related_docs:
  - docs/007_SDK_SPECIFICATION.md
  - docs/008_METADATA_LAYER_SPEC.md
related_recipes:
  - RECIPE-002
  - RECIPE-003
tags:
  - metadata
  - countries
  - m01
---

Recipe 01 — List reporter countries.

This recipe demonstrates the simplest possible use of
``client.metadata``: fetch the catalogue of reporter
countries and print a short summary. No API key is
required for the metadata layer.

The recipe uses only ``ComtradeClient``. It follows the
CB-001 contract: the demo logic lives in
``list_countries_demo(client)`` so the regression test
can inject a mock transport; ``main()`` builds the real
client from environment variables.

Expected output (mock-mode)::

    == Recipe 01: List Countries ==
    Total reporter countries: 247
    First 5:
      004 AF AFG  Afghanistan
      008 AL ALB  Albania
      012 DZ DZA  Algeria
      016 AS ASM  American Samoa
      020 AD AND  Andorra
    Looking up India (reporter code 699):
      display_name : India
      iso_alpha2   : IN
      iso_alpha3   : IND
"""

from __future__ import annotations

import os
import sys
from typing import Iterable

from un_comtrade import ComtradeClient
from un_comtrade.config import Configuration
from un_comtrade.models import Country
from un_comtrade.parser import MetadataParser


# ---- demo ------------------------------------------------------------------


def list_countries_demo(client: ComtradeClient) -> list[Country]:
    """Fetch the country catalogue and print a summary.

    The function is intentionally side-effect-light
    outside of ``print``: it returns the list of
    countries it fetched so the regression test can
    inspect the result without re-parsing stdout.

    Parameters
    ----------
    client
        A ``ComtradeClient`` whose ``metadata`` service
        is reachable. The recipe does not care whether
        the client talks to the live API or a mock
        transport.

    Returns
    -------
    list[Country]
        The countries returned by ``client.metadata.get_countries()``.
    """
    # Step 1 — fetch the catalogue (M01). The metadata
    # service hides the cache-then-fetch-then-parse
    # pipeline; we just see the canonical models.
    countries: list[Country] = client.metadata.get_countries()

    # Step 2 — print the headline number.
    print(f"Total reporter countries: {len(countries)}")

    # Step 3 — print the first five entries so the
    # reader can sanity-check the catalogue is real.
    print("First 5:")
    for country in countries[:5]:
        _print_country_row(country)

    # Step 4 — a focused look-up for India (reporter
    # code 699) so the reader sees a non-trivial
    # example of how to query the catalogue.
    india = client.metadata.get_country(699)
    print("Looking up India (reporter code 699):")
    if india is None:
        print("  (not found in the catalogue)")
    else:
        print(f"  display_name : {india.display_name}")
        print(f"  iso_alpha2   : {india.iso_alpha2}")
        print(f"  iso_alpha3   : {india.iso_alpha3}")

    return countries


def _print_country_row(country: Country) -> None:
    """Render one country on a single aligned row."""
    code = f"{country.country_code:03d}"
    a2 = country.iso_alpha2 or "--"
    a3 = country.iso_alpha3 or "---"
    print(f"  {code} {a2} {a3}  {country.display_name}")


# ---- main ------------------------------------------------------------------


def main() -> int:
    """Build a real ``ComtradeClient`` and run the demo.

    The real client reads ``UN_COMTRADE_KEY`` (unused
    here — metadata is unauthenticated) and the
    standard SDK env vars. A quiet parser
    (``log_skipped=False``) keeps the recipe's output
    free of validation warnings for upstream records
    that fail the ISO-code pattern.
    """
    # ``or None`` converts the empty-string default
    # (when UN_COMTRADE_KEY is unset) into ``None``
    # so the Configuration validation accepts it.
    config = Configuration(api_key=os.environ.get("UN_COMTRADE_KEY") or None)
    parser = MetadataParser(log_skipped=False)
    with ComtradeClient(config, parser=parser) as client:
        list_countries_demo(client)
    return 0


if __name__ == "__main__":
    print("== Recipe 01: List Countries ==")
    raise SystemExit(main())
