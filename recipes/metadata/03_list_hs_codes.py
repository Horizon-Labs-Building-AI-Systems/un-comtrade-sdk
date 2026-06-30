"""
---
recipe_id: RECIPE-003
title: List HS commodity codes
category: metadata
difficulty: beginner
sdk_version: >=1.0.2
requires_api_key: no
estimated_runtime: <10s
inputs:
  required: []
  optional:
    - name: edition
      type: str
      default: "2022"
      description: |
        HS edition to fetch (e.g. "2022", "2017", "2012",
        "2007", "2002", "1996", "1992"). The default is
        the most recent edition documented in
        ``008_METADATA_LAYER_SPEC.md``.
outputs:
  - kind: stdout
    path: null
    description: |
      A short human-readable report containing the total
      number of HS codes for the requested edition, the
      first five codes, and a focused look-up of a
      well-known chapter.
related_docs:
  - docs/007_SDK_SPECIFICATION.md
  - docs/008_METADATA_LAYER_SPEC.md
related_recipes:
  - RECIPE-001
  - RECIPE-004
tags:
  - metadata
  - hs
  - m08
---

Recipe 03 — List HS commodity codes.

The Harmonized System (HS) is the international
nomenclature for products. The catalogue is
**versioned** by edition — the same physical code
(``0101``) can map to a different description in
HS2022 vs HS2017. The metadata layer exposes the
catalogue as a parameterised resource (``R05``); the
recipe passes the edition explicitly.

The recipe fetches the HS2022 catalogue by default,
prints the first five codes, and looks up chapter
``27`` (mineral fuels) so the reader sees a non-trivial
example of how to navigate the HS hierarchy.

Expected output (mock-mode)::

    == Recipe 03: List HS Codes (edition=2022) ==
    Total HS2022 commodity codes: 6940
    First 5:
      TOTAL  Total - All H6 commodities
      01     01 - Animals; live
      0101   0101 - Horses, asses, mules and hinnies; live
      010121 010121 - Horses; live, pure-bred breeding animals
      010129 010129 - Horses; live, other than pure-bred breeding animals
    Looking up chapter 27 (mineral fuels, oils, distillation products, etc.):
      commodity_code : 27
      display_name   : 27 - Mineral fuels, mineral oils and products of their distillation; ...
"""

from __future__ import annotations

import argparse
import os
from typing import List

from un_comtrade import ComtradeClient
from un_comtrade.config import Configuration
from un_comtrade.models import HSCode
from un_comtrade.parser import MetadataParser


# ---- demo ------------------------------------------------------------------


def list_hs_codes_demo(
    client: ComtradeClient,
    *,
    edition: str = "2022",
) -> List[HSCode]:
    """Fetch the HS code catalogue for ``edition``.

    Parameters
    ----------
    client
        A ``ComtradeClient`` whose ``metadata`` service
        is reachable.
    edition
        The HS edition to fetch. Defaults to ``"2022"``
        (the most recent edition documented in the
        specification). The edition string is passed
        verbatim to the metadata downloader.

    Returns
    -------
    list[HSCode]
        The HS codes for the requested edition.
    """
    # Step 1 — fetch the HS catalogue (M08). The
    # downloader routes ``R05`` to ``H{edition}.json``
    # on the upstream; the parser turns each record
    # into an HSCode. The catalogue is large (12k+
    # codes in HS2022) so a cold fetch takes a few
    # seconds; a warm cache returns instantly.
    codes: List[HSCode] = client.metadata.get_hs_codes(edition)

    # Step 2 — headline number. The total is the
    # ground-truth size of the edition's catalogue;
    # a smaller number means an upstream truncation.
    print(f"Total HS{edition} commodity codes: {len(codes)}")

    # Step 3 — first five codes so the reader sees
    # the head of the catalogue. HS codes are
    # ordered ascending by commodity_code.
    print("First 5:")
    for code in codes[:5]:
        _print_hs_row(code)

    # Step 4 — focused look-up of chapter 27. Chapter
    # codes are the 2-digit prefix shared by every
    # 4- and 6-digit code in the chapter; the
    # catalogue includes a record for the chapter
    # itself with that prefix as its commodity_code.
    chapter_27 = client.metadata.get_hs_code("27", edition)
    print("Looking up chapter 27 (mineral fuels, oils, distillation products, etc.):")
    if chapter_27 is None:
        print("  (not found in the catalogue)")
    else:
        print(f"  commodity_code : {chapter_27.commodity_code}")
        print(f"  display_name   : {chapter_27.display_name}")

    return codes


def _print_hs_row(code: HSCode) -> None:
    """Render one HS code on a single aligned row."""
    name = code.display_name or "(no description)"
    print(f"  {code.commodity_code:<6}  {name}")


# ---- main ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Build a real ``ComtradeClient`` and run the demo.

    The recipe accepts a single optional positional
    argument: the HS edition (default ``"2022"``).
    """
    parser = argparse.ArgumentParser(
        prog="RECIPE-003",
        description=__doc__,
    )
    parser.add_argument(
        "edition",
        nargs="?",
        default="2022",
        help="HS edition to fetch (default: 2022).",
    )
    args = parser.parse_args(argv)

    config = Configuration(api_key=os.environ.get("UN_COMTRADE_KEY") or None)
    sdk_parser = MetadataParser(log_skipped=False)
    with ComtradeClient(config, parser=sdk_parser) as client:
        list_hs_codes_demo(client, edition=args.edition)
    return 0


if __name__ == "__main__":
    print("== Recipe 03: List HS Codes ==")
    raise SystemExit(main())
