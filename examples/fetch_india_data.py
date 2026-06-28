"""
Fetch India's trade data and HS code metadata, save as JSON.

Run from the project root:
    python -m examples.fetch_india_data

Outputs land in ``./data/``:
    india_exports_2022_annual.json
    india_imports_2022_annual.json
    india_exports_2022_monthly.json
    india_exports_2022_single_hs.json
    india_exports_2022_world_total.json
    india_exports_2022_single_partner.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Make the package importable when run as a script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from comtrade import ComtradeClient  # noqa: E402

# India = UN Comtrade reporter code 699 (the *current* code).
# Code 356 is the historical "India (...1974)" — do NOT use it.
INDIA = "699"
WORLD = "0"   # special partner code = "World" aggregate
USA   = "842"
HS_TOTAL = "TOTAL"  # wildcard cmdCode = "all products in the classification"
HS_COFFEE_2DIGIT = "09"
HS_PETROLEUM_OIL = "2709"  # HS 4-digit heading for petroleum oils
HS_JEWELRY = "7113"        # HS chapter — articles of jewellery
HS_PHARMA_2DIGIT = "30"  # pharmaceutical products chapter

OUT = PROJECT_ROOT / "data"
OUT.mkdir(parents=True, exist_ok=True)

# A subscription key, if you have one — read from env so we don't hard-code it
SUBSCRIPTION_KEY = os.environ.get("COMTRADE_KEY") or None


def _save(name: str, resp) -> Path:
    path = OUT / name
    resp.to_json(path)
    print(f"  wrote {path}  ({len(resp)} records, {resp.elapsed_seconds:.2f}s)")
    return path


def main() -> None:
    client = ComtradeClient(subscription_key=SUBSCRIPTION_KEY)
    print(f"Mode: {'authenticated (key present)' if client.is_authenticated else 'public preview (no key, 500-record cap)'}")

    # ------------------------------------------------------------------
    # 1) India exports 2022 — annual, all products, all partners
    # ------------------------------------------------------------------
    print("\n[1] India 2022 annual exports — all products, all partners")
    r = client.preview_final(
        typeCode="C", freqCode="A", clCode="HS",
        reporterCode=INDIA, period="2022", flowCode="X",
        cmdCode=HS_TOTAL, partnerCode=None,  # partnerCode=None = all partners
        maxRecords=10, includeDesc=True,
    )
    _save("india_exports_2022_annual.json", r)

    # ------------------------------------------------------------------
    # 2) India imports 2022 — annual, all products, all partners
    # ------------------------------------------------------------------
    print("\n[2] India 2022 annual imports — all products, all partners")
    r = client.preview_final(
        typeCode="C", freqCode="A", clCode="HS",
        reporterCode=INDIA, period="2022", flowCode="M",
        cmdCode=HS_TOTAL, partnerCode=None,
        maxRecords=10, includeDesc=True,
    )
    _save("india_imports_2022_annual.json", r)

    # ------------------------------------------------------------------
    # 3) India exports 2022 monthly — single HS code (jewellery)
    # ------------------------------------------------------------------
    print("\n[3] India 2022 monthly exports — HS 7113 (articles of jewellery)")
    r = client.preview_final(
        typeCode="C", freqCode="M", clCode="HS",
        reporterCode=INDIA, period=[f"2022{m:02d}" for m in range(1, 13)],
        flowCode="X", cmdCode=HS_JEWELRY,
        partnerCode=None, maxRecords=20, includeDesc=True,
    )
    _save("india_exports_2022_monthly.json", r)

    # ------------------------------------------------------------------
    # 4) Single HS chapter (pharma) — annual, 2022, all partners
    # ------------------------------------------------------------------
    print("\n[4] India 2022 annual exports — HS chapter 30 (pharma)")
    r = client.preview_final(
        typeCode="C", freqCode="A", clCode="HS",
        reporterCode=INDIA, period="2022", flowCode="X",
        cmdCode=HS_PHARMA_2DIGIT, partnerCode=None,
        maxRecords=10, includeDesc=True,
    )
    _save("india_exports_2022_single_hs.json", r)

    # ------------------------------------------------------------------
    # 5) World totals — partner=0
    # ------------------------------------------------------------------
    print("\n[5] India 2022 annual exports to WORLD")
    r = client.preview_final(
        typeCode="C", freqCode="A", clCode="HS",
        reporterCode=INDIA, period="2022", flowCode="X",
        cmdCode=HS_TOTAL, partnerCode=WORLD,
        maxRecords=5, includeDesc=True,
    )
    _save("india_exports_2022_world_total.json", r)

    # ------------------------------------------------------------------
    # 6) Single partner (USA) — annual, 2022, all products
    # ------------------------------------------------------------------
    print("\n[6] India 2022 annual exports to USA — all products")
    r = client.preview_final(
        typeCode="C", freqCode="A", clCode="HS",
        reporterCode=INDIA, period="2022", flowCode="X",
        cmdCode=HS_TOTAL, partnerCode=USA,
        maxRecords=5, includeDesc=True,
    )
    _save("india_exports_2022_single_partner.json", r)

    # ------------------------------------------------------------------
    # 7) Trade balance (requires key) — only if user has one
    # ------------------------------------------------------------------
    if client.is_authenticated:
        print("\n[7] India 2022 trade balance (exports vs imports)")
        r = client.get_trade_balance(
            typeCode="C", freqCode="A", clCode="HS",
            reporterCode=INDIA, period="2022",
            cmdCode=HS_TOTAL, partnerCode=None,
        )
        _save("india_trade_balance_2022.json", r)
    else:
        print("\n[7] Skipped trade balance (needs COMTRADE_KEY env var)")

    print("\nDone. JSON files written to:", OUT)


if __name__ == "__main__":
    main()
