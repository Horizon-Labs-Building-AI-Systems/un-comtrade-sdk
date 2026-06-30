"""
---
recipe_id: RECIPE-022
title: Top commodities by trade value (analytics)
category: analytics
difficulty: beginner
sdk_version: >=1.0.2
requires_api_key: yes
estimated_runtime: <10s
inputs:
  required:
    - name: reporter_code
      type: int
      description: UN Comtrade reporter code (e.g. 699 for India)
    - name: period
      type: str
      description: Annual period (e.g. "2022")
  optional:
    - name: flow
      type: str
      default: "X"
      description: |
        Trade flow. ``"X"`` (exports, default) or
        ``"M"`` (imports). The recipe demonstrates
        the export view; switch to ``"M"`` for
        import analysis.
    - name: hs_level
      type: int
      default: 2
      description: |
        HS aggregation level. ``2`` (default) rolls
        up to the chapter level — the cleanest
        view of "what does this country sell".
        ``4`` (heading) and ``6`` (subheading)
        give finer slices.
    - name: limit
      type: int
      default: 10
      description: Top-N rows to print (default: 10).
outputs:
  - kind: stdout
    path: null
    description: |
      A table of the top N HS chapters (or
      headings / subheadings) by trade value, with
      the chapter description where available.
related_docs:
  - docs/007_SDK_SPECIFICATION.md
related_recipes:
  - RECIPE-021
  - RECIPE-024
tags:
  - analytics
  - commodity
  - ranking
  - hs
---

Recipe 02 — Top commodities by trade value.

Demonstrates ``commodity.top_hs_codes(...)``:

1. Fetch trade data via ``client.trade``.
2. Build a ``CanonicalDataset``.
3. Call ``top_hs_codes(dataset, ...)`` with
   the requested ``hs_level``.
4. Render the top N rows.

The recipe defaults to the chapter level
(``hs_level=2``) which is the cleanest
"What does this country sell" view. Switch
to ``--hs-level 4`` (heading) or ``--hs-level 6``
(subheading) for finer slices; both produce
longer lists.

Expected output (mock-mode)::

    == Recipe 02: Top Commodities by Trade Value ==
    Reporter: 699  Period: 2022  Flow: X  HS level: 2
    Loading exports (T01) ...
    Building CanonicalDataset ...
      222 export records
    Top 10 HS chapters by export value:
      HS      description                                     exportValueUSD
      ------  ----------------------------------------------  ----------------
      27      Mineral fuels, mineral oils, ...               12,345,678,901.00
      71      Pearls, precious stones, metals, ...             9,876,543,210.00
      84      Nuclear reactors, boilers, machinery, ...       8,765,432,109.00
      85      Electrical machinery and equipment               7,654,321,098.00
      87      Vehicles other than railway or tramway           6,543,210,987.00
      ...
    (10 rows shown)
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from un_comtrade import ComtradeClient
from un_comtrade.analytics.commodity import top_hs_codes
from un_comtrade.config import Configuration
from un_comtrade.exceptions import (
    APIError,
    AuthenticationError,
    ComtradeError,
    NetworkError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from un_comtrade.models import TradeResponse
from un_comtrade.parser import TradeParser
from un_comtrade.transform import CanonicalDataset


# ---- constants -------------------------------------------------------------

EXIT_AUTH: int = 4

_HS_LEVELS: tuple[int, ...] = (2, 4, 6)
_VALID_FLOWS: tuple[str, ...] = ("X", "M")


# ---- auth ------------------------------------------------------------------


def _require_api_key() -> str:
    key = os.environ.get("UN_COMTRADE_KEY", "").strip()
    if not key:
        print(
            "ERROR: UN_COMTRADE_KEY is not set. "
            "Set it to your UN Comtrade API key and re-run.",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_AUTH)
    return key


# ---- dataset construction -------------------------------------------------


def build_dataset_from_responses(
    *responses: TradeResponse,
    name: str = "top_commodities",
) -> CanonicalDataset:
    parser = TradeParser(log_skipped=False)
    all_records: list[Any] = []
    skipped_total = 0
    for response in responses:
        result = parser.parse_records(list(response.records))
        all_records.extend(result.records)
        skipped_total += result.skipped
    return CanonicalDataset(
        name=name,
        records=tuple(all_records),
        parser_name="TradeParser",
        skipped=skipped_total,
        source_count=sum(len(r.records) for r in responses),
        extracted_at=datetime.now(timezone.utc),
        metadata={},
    )


# ---- demo ------------------------------------------------------------------


@dataclass(frozen=True)
class TopCommodityRow:
    """One row in the top-commodities result.

    Mirrors ``HSCodeRankingRow`` but is decoupled
    from the analytics layer's internal type so
    the recipe's public surface is stable across
    SDK refactors.
    """

    rank: int
    commodity_code: str
    commodity_name: str | None
    export_value: Decimal
    import_value: Decimal
    total_trade: Decimal
    trade_balance: Decimal
    record_count: int


@dataclass(frozen=True)
class TopCommoditiesResult:
    """Result envelope for the top-commodities demo."""

    flow: str
    hs_level: int
    rows: tuple[TopCommodityRow, ...]


def top_commodities_demo(
    dataset: CanonicalDataset,
    *,
    reporter_code: int,
    flow: str = "X",
    hs_level: int = 2,
    limit: int = 10,
) -> TopCommoditiesResult:
    """Run ``top_hs_codes`` for one reporter.

    Parameters
    ----------
    dataset
        The ``CanonicalDataset`` to rank.
    reporter_code
        The reporter whose commodities to rank.
    flow
        ``"X"`` (exports, default) or ``"M"``
        (imports).
    hs_level
        HS aggregation level — ``2`` (chapter),
        ``4`` (heading), or ``6`` (subheading).
        Default ``2`` for the cleanest view.
    limit
        Top-N rows to return. Default ``10``.

    Returns
    -------
    TopCommoditiesResult
        The flow + hs_level used, plus the ranked
        rows (already truncated to ``limit`` by
        the underlying ``top_hs_codes``).
    """
    if flow not in _VALID_FLOWS:
        raise ValueError(
            f"flow must be one of {_VALID_FLOWS}; got {flow!r}"
        )
    if hs_level not in _HS_LEVELS:
        raise ValueError(
            f"hs_level must be one of {_HS_LEVELS}; got {hs_level!r}"
        )
    raw_rows = top_hs_codes(
        dataset,
        reporter_code=reporter_code,
        flow=flow,
        hs_level=hs_level,
        limit=limit,
    )
    rows: list[TopCommodityRow] = []
    for i, r in enumerate(raw_rows, start=1):
        rows.append(
            TopCommodityRow(
                rank=i,
                commodity_code=r.commodity_code,
                commodity_name=r.commodity_name,
                export_value=r.total_exports,
                import_value=r.total_imports,
                total_trade=r.total_trade,
                trade_balance=r.trade_balance,
                record_count=r.record_count,
            )
        )
    return TopCommoditiesResult(
        flow=flow,
        hs_level=hs_level,
        rows=tuple(rows),
    )


# ---- output ---------------------------------------------------------------


def render(result: TopCommoditiesResult) -> str:
    """Format the top-commodities result for stdout."""
    flow_label = "exportValueUSD" if result.flow == "X" else "importValueUSD"
    lines: list[str] = []
    lines.append(
        f"Top {len(result.rows)} HS chapter(s) by "
        f"{flow_label} (hs_level={result.hs_level}):"
    )
    lines.append(
        f"  {'rank':<4}  {'HS':<6}  {'description':<46}  "
        f"{flow_label:>18}"
    )
    lines.append("  " + "-" * 80)
    for row in result.rows:
        desc = (row.commodity_name or "(no description)")[:46]
        value = row.export_value if result.flow == "X" else row.import_value
        lines.append(
            f"  {row.rank:<4}  {row.commodity_code:<6}  "
            f"{desc:<46}  {value:>18,.2f}"
        )
    return "\n".join(lines) + "\n"


# ---- error handling --------------------------------------------------------


def _exit_code_for(exc: ComtradeError) -> int:
    if isinstance(exc, ValidationError):
        return 3
    if isinstance(exc, (AuthenticationError,)):
        return 4
    if isinstance(exc, RateLimitError):
        return 5
    if isinstance(exc, NetworkError):
        return 6
    if isinstance(exc, ServerError):
        return 7
    if isinstance(exc, APIError):
        return 8
    return 1


# ---- main ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    key = _require_api_key()

    parser = argparse.ArgumentParser(
        prog="RECIPE-022",
        description=__doc__,
    )
    parser.add_argument(
        "--reporter", type=int, default=699,
        help="UN Comtrade reporter code (default: 699 = India).",
    )
    parser.add_argument(
        "--period", default="2022",
        help='Annual period, e.g. "2022" (default: 2022).',
    )
    parser.add_argument(
        "--flow", choices=_VALID_FLOWS, default="X",
        help="Trade flow (default: X = exports).",
    )
    parser.add_argument(
        "--hs-level", type=int, choices=_HS_LEVELS, default=2,
        help="HS aggregation level (default: 2 = chapter).",
    )
    parser.add_argument(
        "--limit", type=int, default=10,
        help="Top-N rows to print (default: 10).",
    )
    args = parser.parse_args(argv)

    print("== Recipe 02: Top Commodities by Trade Value ==")
    print(
        f"Reporter: {args.reporter}  Period: {args.period}  "
        f"Flow: {args.flow}  HS level: {args.hs_level}"
    )

    config = Configuration(api_key=key)
    try:
        with ComtradeClient(config) as client:
            if args.flow == "X":
                flow_label = "exports"
            else:
                flow_label = "imports"
            print(f"Loading {flow_label} (T01/T02) ...")
            method = (
                client.trade.get_exports
                if args.flow == "X"
                else client.trade.get_imports
            )
            response = method(
                reporter_code=args.reporter, period=args.period
            )
            dataset = build_dataset_from_responses(response)
            print(f"  {len(dataset.records)} {flow_label} records")
            result = top_commodities_demo(
                dataset,
                reporter_code=args.reporter,
                flow=args.flow,
                hs_level=args.hs_level,
                limit=args.limit,
            )
    except ComtradeError as exc:
        code = _exit_code_for(exc)
        print(
            f"recipe=RECIPE-022 error_class={type(exc).__name__} "
            f"message={exc} exit_code={code}",
            file=sys.stderr,
        )
        return code

    print(render(result))
    print(
        f"recipe=RECIPE-022 flow={args.flow} hs_level={args.hs_level} "
        f"rows={len(result.rows)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
