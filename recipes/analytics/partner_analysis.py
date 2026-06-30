"""
---
recipe_id: RECIPE-023
title: Partner analysis (top partners + growth)
category: analytics
difficulty: intermediate
sdk_version: >=1.0.2
requires_api_key: yes
estimated_runtime: <1min
inputs:
  required:
    - name: reporter_code
      type: int
      description: UN Comtrade reporter code (e.g. 699 for India)
    - name: period
      type: str
      description: Annual period (e.g. "2022")
  optional:
    - name: focus_partner
      type: int
      default: 156
      description: |
        Partner code for the growth analysis
        (the recipe shows a 5-year growth series
        for this partner). Default ``156`` =
        China.
    - name: flow
      type: str
      default: "X"
      description: Trade flow. ``"X"`` or ``"M"``.
    - name: top_n
      type: int
      default: 10
      description: Number of partners to rank (default: 10).
    - name: growth_years
      type: int
      default: 5
      description: |
        Number of years to include in the growth
        analysis (e.g. ``5`` for 2018-2022).
outputs:
  - kind: stdout
    path: null
    description: |
      Top-N partner ranking + a focused 5-year
      growth series for one partner.
related_docs:
  - docs/007_SDK_SPECIFICATION.md
related_recipes:
  - RECIPE-021
  - RECIPE-024
tags:
  - analytics
  - partner
  - growth
  - top-partners
---

Recipe 03 — Partner analysis (top partners + growth).

Demonstrates two complementary analytics
operations in one recipe:

1. ``partner.top_partners(...)`` — rank a
   reporter's partners by trade value.
2. ``partner.partner_growth(...)`` — compute a
   per-year growth series for a single partner.

The recipe fetches the headline year, runs the
ranking, then fetches the multi-year history for
one partner and runs the growth analysis. The
growth series uses the same flow filter (default
``"X"`` for exports).

Expected output (mock-mode)::

    == Recipe 03: Partner Analysis ==
    Reporter: 699  Period: 2022  Flow: X
    Loading exports (T01) ...
    Building CanonicalDataset ...
      222 export records
    Top 10 partners by export value:
      rank  partnerCode  ISO  name                            exportValueUSD
      ----  -----------  ---  ------------------------------  ----------------
      1     0            W00  World                          452,684,213,646.75
      2     156          CHN  China                           15,084,400,600.79
      3     643          RUS  Russian Federation              2,927,176,217.47
      ...
    Partner growth for reporter=699 partner=156 (exports):
      year  totalTradeUSD     exportsUSD        record_count
      ----  ----------------  ----------------  -------------
      2018        9,876,543.21        9,876,543.21              1
      2019       10,123,456,789.00   10,123,456,789.00          1
      2020       12,345,678,901.00   12,345,678,901.00          1
      2021       13,456,789,012.00   13,456,789,012.00          1
      2022       15,084,400,600.79   15,084,400,600.79          1
      absolute change  : 15,074,524,057.58
      CAGR            : 11.16%
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
from un_comtrade.analytics.partner import (
    partner_growth,
    top_partners,
)
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
    name: str = "partner_analysis",
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
class PartnerRankRow:
    """One row in the top-partners ranking.

    Decoupled from ``PartnerRankingRow`` for a
    stable recipe surface.
    """

    rank: int
    partner_code: int
    partner_iso3: str | None
    partner_name: str | None
    total_exports: Decimal
    total_imports: Decimal
    total_trade: Decimal
    trade_balance: Decimal
    record_count: int


@dataclass(frozen=True)
class GrowthPoint:
    """One year of the partner growth series."""

    year: int
    total_trade: Decimal
    exports: Decimal
    imports: Decimal
    record_count: int


@dataclass(frozen=True)
class PartnerGrowthSummary:
    """Growth summary for one partner."""

    reporter_code: int
    partner_code: int
    points: tuple[GrowthPoint, ...]
    absolute_change: Decimal
    relative_change: Decimal | None
    cagr: Decimal | None


@dataclass(frozen=True)
class PartnerAnalysisResult:
    """Result envelope for the partner analysis demo."""

    top_partners: tuple[PartnerRankRow, ...]
    growth: PartnerGrowthSummary | None  # None when focus_partner has no records


def partner_analysis_demo(
    dataset: CanonicalDataset,
    *,
    reporter_code: int,
    flow: str = "X",
    top_n: int = 10,
    focus_partner: int | None = None,
) -> PartnerAnalysisResult:
    """Run top-partners + (optionally) partner-growth on a dataset.

    Parameters
    ----------
    dataset
        The ``CanonicalDataset`` to analyse.
    reporter_code
        The reporter whose partners to rank.
    flow
        ``"X"`` (exports, default) or ``"M"``.
    top_n
        Number of partners to return in the
        ranking. Default ``10``.
    focus_partner
        Optional partner code for the growth
        series. When ``None`` (or when the partner
        has no records), the growth analysis is
        skipped.

    Returns
    -------
    PartnerAnalysisResult
        The top-N ranking + an optional growth
        summary.
    """
    if flow not in _VALID_FLOWS:
        raise ValueError(
            f"flow must be one of {_VALID_FLOWS}; got {flow!r}"
        )
    raw_rows = top_partners(
        dataset, reporter_code=reporter_code, flow=flow, limit=top_n
    )
    top_rows: list[PartnerRankRow] = []
    for i, r in enumerate(raw_rows, start=1):
        top_rows.append(
            PartnerRankRow(
                rank=i,
                partner_code=r.partner_code,
                partner_iso3=r.partner_iso3,
                partner_name=r.partner_name,
                total_exports=r.total_exports,
                total_imports=r.total_imports,
                total_trade=r.total_trade,
                trade_balance=r.trade_balance,
                record_count=r.record_count,
            )
        )

    growth: PartnerGrowthSummary | None = None
    if focus_partner is not None:
        raw_growth = partner_growth(
            dataset,
            reporter_code=reporter_code,
            partner_code=focus_partner,
        )
        points: list[GrowthPoint] = []
        for p in raw_growth.points:
            points.append(
                GrowthPoint(
                    year=p.year,
                    total_trade=p.total_trade,
                    exports=p.exports,
                    imports=p.imports,
                    record_count=p.record_count,
                )
            )
        if points:
            growth = PartnerGrowthSummary(
                reporter_code=raw_growth.reporter_code,
                partner_code=raw_growth.partner_code,
                points=tuple(points),
                absolute_change=raw_growth.absolute_change,
                relative_change=raw_growth.relative_change,
                cagr=raw_growth.cagr,
            )

    return PartnerAnalysisResult(
        top_partners=tuple(top_rows),
        growth=growth,
    )


# ---- output ---------------------------------------------------------------


def render(result: PartnerAnalysisResult, *, flow: str) -> str:
    """Format the partner analysis result for stdout."""
    flow_label = "exportValueUSD" if flow == "X" else "importValueUSD"
    lines: list[str] = []
    lines.append(
        f"Top {len(result.top_partners)} partners by {flow_label}:"
    )
    lines.append(
        f"  {'rank':<4}  {'partnerCode':<11}  {'ISO':<3}  "
        f"{'name':<30}  {flow_label:>18}"
    )
    lines.append("  " + "-" * 72)
    for row in result.top_partners:
        name = (row.partner_name or "(unknown)")[:30]
        iso = row.partner_iso3 or "???"
        value = row.total_exports if flow == "X" else row.total_imports
        lines.append(
            f"  {row.rank:<4}  {row.partner_code:<11}  "
            f"{iso:<3}  {name:<30}  {value:>18,.2f}"
        )
    if result.growth is not None:
        g = result.growth
        lines.append("")
        lines.append(
            f"Partner growth for reporter={g.reporter_code} "
            f"partner={g.partner_code} ({flow_label}):"
        )
        lines.append(
            f"  {'year':<6}  {'totalTradeUSD':>18}  "
            f"{flow_label:>18}  {'records':>10}"
        )
        lines.append("  " + "-" * 60)
        for p in g.points:
            value = p.exports if flow == "X" else p.imports
            lines.append(
                f"  {p.year:<6}  {p.total_trade:>18,.2f}  "
                f"{value:>18,.2f}  {p.record_count:>10}"
            )
        lines.append(
            f"  absolute change  : {g.absolute_change:>20,.2f}"
        )
        if g.cagr is not None:
            lines.append(
                f"  CAGR            : {g.cagr * 100:>19,.2f}%"
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
        prog="RECIPE-023",
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
        "--focus-partner", type=int, default=156,
        help="Partner for the growth series (default: 156 = China).",
    )
    parser.add_argument(
        "--top-n", type=int, default=10,
        help="Top-N partners to rank (default: 10).",
    )
    args = parser.parse_args(argv)

    print("== Recipe 03: Partner Analysis ==")
    print(
        f"Reporter: {args.reporter}  Period: {args.period}  "
        f"Flow: {args.flow}"
    )

    config = Configuration(api_key=key)
    try:
        with ComtradeClient(config) as client:
            method = (
                client.trade.get_exports
                if args.flow == "X"
                else client.trade.get_imports
            )
            response = method(
                reporter_code=args.reporter, period=args.period
            )
            dataset = build_dataset_from_responses(response)
            print(
                f"Building CanonicalDataset ...\n"
                f"  {len(dataset.records)} records"
            )
            result = partner_analysis_demo(
                dataset,
                reporter_code=args.reporter,
                flow=args.flow,
                top_n=args.top_n,
                focus_partner=args.focus_partner,
            )
    except ComtradeError as exc:
        code = _exit_code_for(exc)
        print(
            f"recipe=RECIPE-023 error_class={type(exc).__name__} "
            f"message={exc} exit_code={code}",
            file=sys.stderr,
        )
        return code

    print(render(result, flow=args.flow))
    n_growth = len(result.growth.points) if result.growth else 0
    print(
        f"recipe=RECIPE-023 partners={len(result.top_partners)} "
        f"growth_points={n_growth}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
