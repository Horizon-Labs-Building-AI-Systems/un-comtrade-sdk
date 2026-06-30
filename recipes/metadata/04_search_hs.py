"""
---
recipe_id: RECIPE-004
title: Search HS commodity codes by keyword
category: metadata
difficulty: beginner
sdk_version: >=1.0.2
requires_api_key: no
estimated_runtime: <1s
inputs:
  required:
    - name: query
      type: str
      description: |
        Case-insensitive substring matched against
        ``HSCode.display_name``. The match is
        substring-based; supply a single word for
        tighter results.
  optional:
    - name: edition
      type: str
      default: "2022"
      description: HS edition to search in.
    - name: limit
      type: int
      default: 10
      description: Maximum number of matches to print.
outputs:
  - kind: stdout
    path: null
    description: |
      A short human-readable report listing the matches
      found for ``query`` in HS ``edition``, capped at
      ``limit`` rows.
related_docs:
  - docs/007_SDK_SPECIFICATION.md
  - docs/008_METADATA_LAYER_SPEC.md
related_recipes:
  - RECIPE-003
tags:
  - metadata
  - hs
  - search
  - m10
---

Recipe 04 — Search HS commodity codes by keyword.

The HS nomenclature contains thousands of codes; the
search helper (M10) lets a consumer find the right
code without scanning the full catalogue. The
metadata layer performs a case-insensitive substring
match against each code's ``display_name``.

The recipe takes a positional ``query`` argument and
optionally ``--edition`` (default ``"2022"``) and
``--limit`` (default ``10``). The output is the
matched codes, ordered as they appear in the
catalogue.

Expected output (mock-mode, ``python search_hs.py
electric --limit 5``)::

    == Recipe 04: Search HS Codes ==
    Query: "electric" (edition=2022, limit=5)
    333 matches:
      2716    2716 - Electrical energy
      271600  271600 - Electrical energy
      3603    3603 - Safety fuses; detonating cords; percussion or detonating caps; igniters; electric detonators
      360360  360360 - Electric detonators
      630110  630110 - Blankets; electric
      ... 328 more not shown
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


def search_hs_demo(
    client: ComtradeClient,
    *,
    query: str,
    edition: str = "2022",
    limit: int = 10,
) -> List[HSCode]:
    """Search the HS catalogue for ``query``.

    The search delegates to ``client.metadata.search_hs``,
    which performs a case-insensitive substring match
    against each code's ``display_name``. The result is
    capped at ``limit`` rows for the printed report;
    the full result list is returned to the caller.

    Parameters
    ----------
    client
        A ``ComtradeClient`` whose ``metadata`` service
        is reachable.
    query
        The case-insensitive substring to search for.
        Empty queries return an empty list (the SDK
        guards against an unbounded search).
    edition
        The HS edition to search in. Defaults to
        ``"2022"``.
    limit
        Maximum number of rows to print. Defaults to
        ``10``. The full result is still returned to
        the caller.

    Returns
    -------
    list[HSCode]
        The matched HS codes, in catalogue order.
    """
    # Step 1 — run the search. ``search_hs`` returns
    # an empty list when the query is empty or no
    # codes match; both cases are handled uniformly
    # by the rest of the function.
    matches: List[HSCode] = client.metadata.search_hs(query, edition)

    # Step 2 — headline summary.
    print(
        f"Query: {query!r} "
        f"(edition={edition}, limit={limit})"
    )
    print(f"{len(matches)} matches:")

    # Step 3 — print up to ``limit`` rows.
    for code in matches[:limit]:
        _print_hs_row(code)

    # Step 4 — if the catalogue returned more matches
    # than ``limit``, hint at the truncation so the
    # reader knows there's more to see.
    if len(matches) > limit:
        print(f"  ... {len(matches) - limit} more not shown")

    return matches


def _print_hs_row(code: HSCode) -> None:
    """Render one HS code on a single aligned row."""
    name = code.display_name or "(no description)"
    print(f"  {code.commodity_code:<6}  {name}")


# ---- main ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Build a real ``ComtradeClient`` and run the demo."""
    parser = argparse.ArgumentParser(
        prog="RECIPE-004",
        description=__doc__,
    )
    parser.add_argument(
        "query",
        help="Case-insensitive substring to search for.",
    )
    parser.add_argument(
        "--edition",
        default="2022",
        help="HS edition to search in (default: 2022).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of matches to print (default: 10).",
    )
    args = parser.parse_args(argv)

    config = Configuration(api_key=os.environ.get("UN_COMTRADE_KEY") or None)
    sdk_parser = MetadataParser(log_skipped=False)
    with ComtradeClient(config, parser=sdk_parser) as client:
        search_hs_demo(
            client,
            query=args.query,
            edition=args.edition,
            limit=args.limit,
        )
    return 0


if __name__ == "__main__":
    print("== Recipe 04: Search HS Codes ==")
    raise SystemExit(main())
