"""
---
recipe_id: RECIPE-002
title: List partner countries
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
      number of partners, the first five entries, and a
      focused look-up of China (partner code 156).
related_docs:
  - docs/007_SDK_SPECIFICATION.md
  - docs/008_METADATA_LAYER_SPEC.md
related_recipes:
  - RECIPE-001
  - RECIPE-003
tags:
  - metadata
  - partners
  - m03
---

Recipe 02 — List partner countries.

The partner catalogue (M03) is structurally identical
to the reporter catalogue (M01) but addresses a
different role: a partner is the other side of a trade
record. The data is the same set of political entities;
the SDK uses two distinct model types (``Country`` vs
``Partner``) so the type system tells the reader which
role the entity played.

The recipe uses only ``ComtradeClient`` and prints the
catalogue summary plus a focused look-up of China
(partner code 156).

Expected output (mock-mode)::

    == Recipe 02: List Partners ==
    Total partner countries: 304
    First 5:
      004 AF AFG  Afghanistan
      008 AL ALB  Albania
      012 DZ DZA  Algeria
      016 AS ASM  American Samoa
      020 AD AND  Andorra
    Looking up China (partner code 156):
      display_name : China
      iso_alpha2   : CN
      iso_alpha3   : CHN
"""

from __future__ import annotations

import os
from typing import List

from un_comtrade import ComtradeClient
from un_comtrade.config import Configuration
from un_comtrade.models import Partner
from un_comtrade.parser import MetadataParser


# ---- demo ------------------------------------------------------------------


def list_partners_demo(client: ComtradeClient) -> List[Partner]:
    """Fetch the partner catalogue and print a summary.

    The partner catalogue is one of two parallel
    reference catalogues in the metadata layer (the
    other being the reporter catalogue of RECIPE-001).
    Both call the same upstream endpoints conceptually;
    in this build they fetch from different resource
    ids (``R03`` for partners, ``R02`` for reporters).

    Parameters
    ----------
    client
        A ``ComtradeClient`` whose ``metadata`` service
        is reachable.

    Returns
    -------
    list[Partner]
        The partners returned by ``client.metadata.get_partners()``.
    """
    # Step 1 — fetch the partner catalogue (M03). The
    # call is symmetric to RECIPE-001's get_countries;
    # the model class differs (Partner vs Country).
    partners: List[Partner] = client.metadata.get_partners()

    # Step 2 — headline number.
    print(f"Total partner countries: {len(partners)}")

    # Step 3 — first five rows so the reader can see
    # the catalogue's head. Partner codes overlap
    # with country codes by design — they refer to the
    # same political entities.
    print("First 5:")
    for partner in partners[:5]:
        _print_partner_row(partner)

    # Step 4 — focused look-up for China (156), the
    # largest trading partner for many reporters.
    china = client.metadata.get_partner(156)
    print("Looking up China (partner code 156):")
    if china is None:
        print("  (not found in the catalogue)")
    else:
        print(f"  display_name : {china.display_name}")
        print(f"  iso_alpha2   : {china.iso_alpha2}")
        print(f"  iso_alpha3   : {china.iso_alpha3}")

    return partners


def _print_partner_row(partner: Partner) -> None:
    """Render one partner on a single aligned row."""
    code = f"{partner.country_code:03d}"
    a2 = partner.iso_alpha2 or "--"
    a3 = partner.iso_alpha3 or "---"
    print(f"  {code} {a2} {a3}  {partner.display_name}")


# ---- main ------------------------------------------------------------------


def main() -> int:
    """Build a real ``ComtradeClient`` and run the demo."""
    config = Configuration(api_key=os.environ.get("UN_COMTRADE_KEY") or None)
    parser = MetadataParser(log_skipped=False)
    with ComtradeClient(config, parser=parser) as client:
        list_partners_demo(client)
    return 0


if __name__ == "__main__":
    print("== Recipe 02: List Partners ==")
    raise SystemExit(main())
