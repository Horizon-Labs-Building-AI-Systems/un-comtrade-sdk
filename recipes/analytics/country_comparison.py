"""
---
recipe_id: RECIPE-024
title: Country vs country comparison (analytics)
category: analytics
difficulty: intermediate
sdk_version: >=1.0.2
requires_api_key: yes
estimated_runtime: <1min
inputs:
  required:
    - name: period
      type: str
      description: Annual period (e.g. "2022")
  optional:
    - name: reporter_a
      type: int
      default: 699
      description: First reporter code (default: 699 = India).
    - name: reporter_b
      type: int
      default: 156
      description: Second reporter code (default: 156 = China).
    - name: flow
      type: str
      default: "X"
      description: Trade flow. ``"X"`` (exports) or ``"M"`` (imports).
    - name: breakdown_by
      type: str
      default: "commodity"
      description: |
        Group-by dimension. ``"commodity"`` rolls
        up to the chapter level; ``"partner"``
        rolls up to the partner level.
    - name: limit
      type: int
      default: 10
      description: Top-N rows to print (default: 10).
outputs:
  - kind: stdout
    path: null
    description: |
      Side-by-side comparison of two reporters
      across a single dimension (commodity or
      partner), with delta and percent change
      vs. the baseline reporter.
related_docs:
  - docs/007_SDK_SPECIFICATION.md
related_recipes:
  - RECIPE-021
  - RECIPE-022
tags:
  - analytics
  - comparison
  - country
  - cross-section
---

Recipe 04 — Country vs country comparison.

Demonstrates ``compare.country_vs_country(...)``:

1. Fetch trade data for both reporters in a
   single fetch (one upstream call each).
2. Build a ``CanonicalDataset`` containing
   records from both reporters.
3. Call ``country_vs_country(...)`` with
   ``breakdown_by="commodity"`` (or ``"partner"``).
4. Render the side-by-side comparison with
   delta and percent change vs. the baseline.

The first entry in ``reporter_codes`` is the
baseline; subsequent entries are compared
against it. The percent change is ``None``
when the baseline value is zero (undefined
division).

Expected output (mock-mode)::

    == Recipe 04: Country vs Country Comparison ==
    A=699 (IND)  B=156 (CHN)  Period: 2022  Flow: X  Breakdown: commodity
    Loading exports (T01) ...
    Building CanonicalDataset ...
      500 export records
    Top 10 commodities by export value (delta vs A=699):
      HS      description                                     A (IND)          B (CHN)        delta       pct
      ------  ----------------------------------------------  --------------  ------------  ----------  ----
      27      Mineral fuels, mineral oils, ...               12,345,678,901    1,234,567,890  -11,111,111  -90.0%
      71      Pearls, precious stones, metals, ...             9,876,543,210    5,432,109,876  -4,444,433  -45.0%
      85      Electrical machinery and equipment               7,654,321,098    8,765,432,109  +1,111,111  +14.5%
      ...
    Aggregate totals:
      A=699 (IND) : 452,684,213,646.75
      B=156 (CHN) : 3,212,345,678,901.23
      delta       :  +2,759,661,465,254.48
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
from un_comtrade.analytics.compare import country_vs_country
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
_VALID_BREAKDOWNS: tuple[str, ...] = ("commodity", "partner")


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
    name: str = "country_comparison",
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
class ComparisonRowView:
    """One row of the country comparison, decoupled from
    ``compare.ComparisonRow``.
    """

    dimension_key: str
    dimension_label: str | None
    values: tuple[Decimal, ...]
    deltas: tuple[Decimal, ...]
    pct_changes: tuple[Decimal | None, ...]
    record_counts: tuple[int, ...]


@dataclass(frozen=True)
class ComparisonSummaryView:
    """The aggregate totals (per reporter, not per dimension)."""

    labels: tuple[str, ...]
    total_values: tuple[Decimal, ...]
    total_records: tuple[int, ...]


@dataclass(frozen=True)
class CountryComparisonResult:
    """Result envelope for the country comparison demo."""

    reporter_codes: tuple[int, ...]
    reporter_iso3: tuple[str | None, ...]
    reporter_names: tuple[str | None, ...]
    breakdown_by: str
    flow: str | None
    period: str | None
    summary: ComparisonSummaryView
    rows: tuple[ComparisonRowView, ...]


def country_comparison_demo(
    dataset: CanonicalDataset,
    *,
    reporter_a: int,
    reporter_b: int,
    period: str,
    flow: str = "X",
    breakdown_by: str = "commodity",
    limit: int = 10,
) -> CountryComparisonResult:
    """Run ``country_vs_country`` for two reporters.

    Parameters
    ----------
    dataset
        The ``CanonicalDataset`` to analyse. May
        contain records from many reporters;
        the function filters to the two
        requested.
    reporter_a
        First reporter code (the baseline; rows
        are delta'd against this).
    reporter_b
        Second reporter code.
    period
        Annual period string (e.g. ``"2022"``).
    flow
        ``"X"`` (exports) or ``"M"`` (imports).
    breakdown_by
        ``"commodity"`` or ``"partner"``.
    limit
        Top-N rows to return.
    """
    if flow not in _VALID_FLOWS:
        raise ValueError(
            f"flow must be one of {_VALID_FLOWS}; got {flow!r}"
        )
    if breakdown_by not in _VALID_BREAKDOWNS:
        raise ValueError(
            f"breakdown_by must be one of {_VALID_BREAKDOWNS}; "
            f"got {breakdown_by!r}"
        )
    raw = country_vs_country(
        dataset,
        reporter_codes=[reporter_a, reporter_b],
        breakdown_by=breakdown_by,
        flow=flow,
        period=period,
        limit=limit,
    )
    rows = tuple(
        ComparisonRowView(
            dimension_key=r.dimension_key,
            dimension_label=r.dimension_label,
            values=r.values,
            deltas=r.deltas,
            pct_changes=r.pct_changes,
            record_counts=r.record_counts,
        )
        for r in raw.rows
    )
    summary = ComparisonSummaryView(
        labels=raw.summary.labels,
        total_values=raw.summary.total_values,
        total_records=raw.summary.total_records,
    )
    return CountryComparisonResult(
        reporter_codes=raw.reporter_codes,
        reporter_iso3=raw.reporter_iso3,
        reporter_names=raw.reporter_names,
        breakdown_by=raw.breakdown_by,
        flow=raw.flow,
        period=raw.period,
        summary=summary,
        rows=rows,
    )


# ---- output ---------------------------------------------------------------


def _fmt_pct(p: Decimal | None) -> str:
    if p is None:
        return "   n/a"
    sign = "+" if p >= 0 else ""
    return f"{sign}{p:.1f}%"


def render(result: CountryComparisonResult) -> str:
    """Format the country comparison for stdout."""
    a_code = result.reporter_codes[0]
    a_iso = result.reporter_iso3[0] or "???"
    a_name = result.reporter_names[0] or "(unknown)"
    b_code = result.reporter_codes[1] if len(result.reporter_codes) > 1 else None
    b_iso = result.reporter_iso3[1] if len(result.reporter_iso3) > 1 else None
    b_name = result.reporter_names[1] if len(result.reporter_names) > 1 else None
    header = f"A={a_code} ({a_iso}/{a_name})"
    if b_code is not None:
        header += f"  B={b_code} ({b_iso}/{b_name})"

    lines: list[str] = []
    lines.append(
        f"{header}  Period: {result.period}  Flow: {result.flow}  "
        f"Breakdown: {result.breakdown_by}"
    )
    lines.append(
        f"Top {len(result.rows)} {result.breakdown_by} rows "
        f"(delta vs A={a_code}):"
    )
    # Column widths: dimension 6, label 46, A 16, B 16, delta 14, pct 8
    lines.append(
        f"  {'key':<6}  {'description':<46}  "
        f"{'A':>16}  {'B':>16}  {'delta':>14}  {'pct':>8}"
    )
    lines.append("  " + "-" * 110)
    for row in result.rows:
        a_val = row.values[0]
        b_val = row.values[1] if len(row.values) > 1 else Decimal("0")
        delta = row.deltas[1] if len(row.deltas) > 1 else Decimal("0")
        pct = row.pct_changes[1] if len(row.pct_changes) > 1 else None
        desc = (row.dimension_label or "")[:46]
        lines.append(
            f"  {row.dimension_key:<6}  {desc:<46}  "
            f"{a_val:>16,.0f}  {b_val:>16,.0f}  "
            f"{delta:>+14,.0f}  {_fmt_pct(pct):>8}"
        )

    lines.append("")
    lines.append("Aggregate totals:")
    for i, label in enumerate(result.summary.labels):
        v = result.summary.total_values[i]
        n = result.summary.total_records[i]
        lines.append(f"  {label:<14} : {v:>20,.2f}  ({n} records)")
    if len(result.summary.total_values) >= 2:
        a_total = result.summary.total_values[0]
        b_total = result.summary.total_values[1]
        delta = b_total - a_total
        lines.append(f"  {'delta':<14} : {delta:>+20,.2f}")

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
        prog="RECIPE-024",
        description=__doc__,
    )
    parser.add_argument(
        "--reporter-a", type=int, default=699,
        help="First reporter code, baseline (default: 699 = India).",
    )
    parser.add_argument(
        "--reporter-b", type=int, default=156,
        help="Second reporter code (default: 156 = China).",
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
        "--breakdown-by", choices=_VALID_BREAKDOWNS, default="commodity",
        help="Group-by dimension (default: commodity).",
    )
    parser.add_argument(
        "--limit", type=int, default=10,
        help="Top-N rows to print (default: 10).",
    )
    args = parser.parse_args(argv)

    print("== Recipe 04: Country vs Country Comparison ==")
    print(
        f"A={args.reporter_a}  B={args.reporter_b}  "
        f"Period: {args.period}  Flow: {args.flow}  "
        f"Breakdown: {args.breakdown_by}"
    )

    config = Configuration(api_key=key)
    try:
        with ComtradeClient(config) as client:
            method = (
                client.trade.get_exports
                if args.flow == "X"
                else client.trade.get_imports
            )
            resp_a = method(
                reporter_code=args.reporter_a, period=args.period
            )
            resp_b = method(
                reporter_code=args.reporter_b, period=args.period
            )
            dataset = build_dataset_from_responses(resp_a, resp_b)
            print(
                f"Building CanonicalDataset ...\n"
                f"  {len(dataset.records)} records"
            )
            result = country_comparison_demo(
                dataset,
                reporter_a=args.reporter_a,
                reporter_b=args.reporter_b,
                period=args.period,
                flow=args.flow,
                breakdown_by=args.breakdown_by,
                limit=args.limit,
            )
    except ComtradeError as exc:
        code = _exit_code_for(exc)
        print(
            f"recipe=RECIPE-024 error_class={type(exc).__name__} "
            f"message={exc} exit_code={code}",
            file=sys.stderr,
        )
        return code

    print(render(result))
    print(
        f"recipe=RECIPE-024 rows={len(result.rows)} "
        f"a={args.reporter_a} b={args.reporter_b}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
