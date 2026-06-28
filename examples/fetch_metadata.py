"""Fetch reference metadata (HS codes, reporters, partners, etc.) and save to JSON.

Run from the project root:
    python -m examples.fetch_metadata
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from comtrade import ComtradeClient  # noqa: E402

OUT = PROJECT_ROOT / "data"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    client = ComtradeClient()

    print("[1] List of all reference tables")
    refs = client.list_references()
    (OUT / "reference_list.json").write_text(
        __import__("json").dumps(refs, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  wrote {OUT / 'reference_list.json'}  ({len(refs)} reference tables)")

    # Core reference tables we care about
    targets = [
        ("hs_combined.json",        "HS",   "Combined HS — all editions"),
        ("hs_2022.json",            "H6",   "HS 2022 (6-digit)"),
        ("hs_2017.json",            "H5",   "HS 2017 (6-digit)"),
        ("reporters.json",          "Reporters", "Reporter countries"),
        ("partners.json",           "partnerAreas", "Partner countries/areas"),
        ("trade_flows.json",        "tradeRegimes", "Trade flow codes"),
        ("frequency.json",          "Frequency", "Frequency codes (A/M)"),
        ("quantity_units.json",     "QuantityUnits", "Quantity units"),
        ("modes_of_transport.json", "ModeOfTransportCodes", "Mode of transport"),
        ("data_items.json",         "TradeDataItems", "Data item (column) codes"),
    ]

    for filename, category, description in targets:
        try:
            data = client.get_reference(category)
            (OUT / filename).write_text(
                __import__("json").dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"  {filename:30s} <- {description}  ({len(data)} rows)")
        except Exception as exc:
            print(f"  {filename:30s} FAILED: {exc}")

    # Quick spot-check: filter HS chapter 27 (mineral fuels) from the combined HS list
    try:
        hs = client.get_reference("HS")
        # ``HS`` rows can be either a dict with "id"/"text" or a list
        if isinstance(hs, list) and hs and isinstance(hs[0], dict):
            ch27 = [row for row in hs if str(row.get("id", "")).startswith("27")]
            (OUT / "hs_chapter_27_mineral_fuels.json").write_text(
                __import__("json").dumps(ch27, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"  hs_chapter_27_mineral_fuels.json  (HS chapter 27 — {len(ch27)} rows)")
    except Exception as exc:
        print(f"  HS chapter 27 spot-check FAILED: {exc}")

    print("\nDone. Files in:", OUT)


if __name__ == "__main__":
    main()
