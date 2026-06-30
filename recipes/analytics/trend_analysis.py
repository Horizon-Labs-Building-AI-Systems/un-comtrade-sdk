"""
---
recipe_id: RECIPE-025
title: Trade trend analysis with growth rates and CAGR (analytics)
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
    - name: start_year
      type: int
      description: First year of the trend (e.g. 2018)
    - name: end_year
      type: int
      description: Last year of the trend (e.g. 2022)
  optional:
    - name: flow
      type: str
      default: "X"
      description: Trade flow. ``"X"`` (exports) or ``"M"`` (imports).
outputs:
  - kind: stdout
    path: null
    description: |
      Year-by-year trend with period-over-period
      growth rates, plus a headline CAGR.
related_docs:
  - docs/007_SDK_SPECIFICATION.md
related_recipes:
  - RECIPE-021
  - RECIPE-023
tags:
  - analytics
  - timeseries
  - growth
  - cagr
  - trend
---

Recipe 05 — Trade trend with growth + CAGR.

Demonstrates the time-series analytics surface:

1. ``timeseries.annual_trend(...)`` — build a
   per-year trend.
2. ``timeseries.growth_rates(...)`` — compute
   period-over-period growth.
3. ``timeseries.cagr(...)`` — compute the
   compound annual growth rate.

The recipe fetches one upstream call per year
in the requested range, builds a single
``CanonicalDataset``, and runs the three
analytics operations on top of it.

Expected output (mock-mode)::

    == Recipe 05: Trade Trend Analysis ==
    Reporter: 699  Period: 2018-2022  Flow: X
    Loading exports (T01) for 5 years ...
    Building CanonicalDataset ...
      1100 export records
    Annual trend (exports):
      year  valueUSD        growth   record_count
      ----  -------------  --------  -------------
      2018   9,876,543.21    n/a        220
      2019  10,123,456,789.00  +2.5%    220
      2020  12,345,678,901.00  +22.0%   220
      2021  13,456,789,012.00  +9.0%    220
      2022  15,084,400,600.79  +12.1%   220
    CAGR (2018 -> 2022): 11.16%
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
from un_comtrade.analytics.timeseries import (
    annual_trend,
    cagr,
    growth_rates,
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
    name: str = "trend_analysis",
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
class TrendPointView:
    """One annual trend point, decoupled from
    ``timeseries.TrendPoint`` for a stable recipe
    surface.
    """

    year: int
    value: Decimal
    record_count: int


@dataclass(frozen=True)
class GrowthRowView:
    """One growth-rate row, joining a trend point
    with its year-over-year growth."""

    year: int
    value: Decimal
    growth: Decimal | None  # None for the first row
    record_count: int


@dataclass(frozen=True)
class TrendAnalysisResult:
    """Result envelope for the trend analysis demo."""

    flow: str
    years: tuple[int, ...]
    rows: tuple[GrowthRowView, ...]
    cagr: Decimal | None


def trend_analysis_demo(
    dataset: CanonicalDataset,
    *,
    reporter_code: int,
    flow: str = "X",
) -> TrendAnalysisResult:
    """Run annual_trend + growth_rates + cagr on a dataset.

    Parameters
    ----------
    dataset
        The ``CanonicalDataset`` to analyse. May
        span multiple years; the recipe's
        ``main()`` builds one call per year and
        combines the responses.
    reporter_code
        The reporter whose trend to compute.
    flow
        ``"X"`` (exports) or ``"M"`` (imports).

    Returns
    -------
    TrendAnalysisResult
        The annual trend, with year-over-year
        growth, plus the CAGR for the span.
        Empty ``years`` / ``rows`` when the
        dataset has no records for the reporter.
    """
    if flow not in _VALID_FLOWS:
        raise ValueError(
            f"flow must be one of {_VALID_FLOWS}; got {flow!r}"
        )
    points = annual_trend(
        dataset, reporter_code=reporter_code, flow=flow
    )
    if not points:
        return TrendAnalysisResult(
            flow=flow, years=(), rows=(), cagr=None
        )

    growth_points = growth_rates(points)
    growth_by_year = {gp.year: gp.growth for gp in growth_points}

    rows: list[GrowthRowView] = []
    for p in points:
        rows.append(
            GrowthRowView(
                year=p.year,
                value=p.value,
                growth=growth_by_year.get(p.year),
                record_count=p.record_count,
            )
        )
    overall_cagr = cagr(points)

    years = tuple(p.year for p in points)
    return TrendAnalysisResult(
        flow=flow,
        years=years,
        rows=tuple(rows),
        cagr=overall_cagr,
    )


# ---- output ---------------------------------------------------------------


def _fmt_growth(g: Decimal | None) -> str:
    if g is None:
        return "  n/a "
    sign = "+" if g >= 0 else ""
    return f"{sign}{g * 100:.1f}%"


def render(result: TrendAnalysisResult) -> str:
    """Format the trend analysis for stdout."""
    flow_label = "valueUSD" if result.flow == "X" else "valueUSD"
    lines: list[str] = []
    lines.append(
        f"Annual trend ({'exports' if result.flow == 'X' else 'imports'}):"
    )
    lines.append(
        f"  {'year':<6}  {flow_label:>18}  {'growth':>8}  "
        f"{'records':>10}"
    )
    lines.append("  " + "-" * 50)
    for row in result.rows:
        lines.append(
            f"  {row.year:<6}  {row.value:>18,.2f}  "
            f"{_fmt_growth(row.growth):>8}  {row.record_count:>10}"
        )
    if result.cagr is not None:
        span = (
            f"{result.years[0]} -> {result.years[-1]}"
            if result.years
            else "n/a"
        )
        lines.append("")
        lines.append(f"CAGR ({span}): {result.cagr * 100:.2f}%")
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
        prog="RECIPE-025",
        description=__doc__,
    )
    parser.add_argument(
        "--reporter", type=int, default=699,
        help="UN Comtrade reporter code (default: 699 = India).",
    )
    parser.add_argument(
        "--start-year", type=int, default=2018,
        help="First year of the trend (default: 2018).",
    )
    parser.add_argument(
        "--end-year", type=int, default=2022,
        help="Last year of the trend (default: 2022).",
    )
    parser.add_argument(
        "--flow", choices=_VALID_FLOWS, default="X",
        help="Trade flow (default: X = exports).",
    )
    args = parser.parse_args(argv)

    if args.end_year < args.start_year:
        print(
            f"ERROR: --end-year ({args.end_year}) must be >= "
            f"--start-year ({args.start_year})",
            file=sys.stderr,
        )
        return 2

    years = list(range(args.start_year, args.end_year + 1))
    print("== Recipe 05: Trade Trend Analysis ==")
    print(
        f"Reporter: {args.reporter}  "
        f"Period: {args.start_year}-{args.end_year}  "
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
            print(
                f"Loading {'exports' if args.flow == 'X' else 'imports'} "
                f"(T01/T02) for {len(years)} years ..."
            )
            responses: list[TradeResponse] = []
            for year in years:
                responses.append(
                    method(
                        reporter_code=args.reporter, period=str(year)
                    )
                )
            dataset = build_dataset_from_responses(*responses)
            print(
                f"Building CanonicalDataset ...\n"
                f"  {len(dataset.records)} records"
            )
            result = trend_analysis_demo(
                dataset,
                reporter_code=args.reporter,
                flow=args.flow,
            )
    except ComtradeError as exc:
        code = _exit_code_for(exc)
        print(
            f"recipe=RECIPE-025 error_class={type(exc).__name__} "
            f"message={exc} exit_code={code}",
            file=sys.stderr,
        )
        return code

    if not result.rows:
        print(
            f"no records for reporter={args.reporter} in "
            f"period={args.start_year}-{args.end_year}"
        )
        return 8
    print(render(result))
    cagr_str = (
        f"{result.cagr * 100:.2f}%" if result.cagr is not None else "n/a"
    )
    print(
        f"recipe=RECIPE-025 years={len(result.years)} "
        f"cagr={cagr_str}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
