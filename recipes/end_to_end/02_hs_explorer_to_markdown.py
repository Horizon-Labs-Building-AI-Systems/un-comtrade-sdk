"""
---
recipe_id: RECIPE-113
title: HS code explorer — search, fetch, compare, summarise to Markdown
category: end_to_end
difficulty: advanced
sdk_version: >=1.0.2
requires_api_key: yes
estimated_runtime: 1-10min
composes:
  - client.metadata
  - client.trade
  - client.etl
  - client.analytics
inputs:
  required:
    - name: query
      type: str
      description: |
        Substring to search the HS catalogue for
        (e.g. ``"electric vehicles"``,
        ``"petroleum oils"``).
  optional:
    - name: reporter
      type: int
      default: 699
      description: Reporter country code (default: 699 = India).
    - name: partner_a
      type: int
      default: 156
      description: First comparison partner (default: 156 = China).
    - name: partner_b
      type: int
      default: 840
      description: Second comparison partner (default: 840 = USA).
    - name: period
      type: str
      default: "2022"
      description: Annual period (default: 2022).
    - name: hs_edition
      type: str
      default: "H6"
      description: HS edition (default: H6).
    - name: output_path
      type: str
      default: "./output/hs_explorer_report.md"
      description: Path the Markdown summary is written to.
outputs:
  - kind: file
    path: <output_path>
    description: |
      Markdown summary report. Sections:
      metadata header, HS catalogue matches
      table, per-HS code partner A vs. partner B
      comparison, footer.
  - kind: stdout
    path: null
    description: |
      Stage-by-stage run summary (matched /
      fetched / parsed / compared / emitted).
related_docs:
  - docs/003_ARCHITECTURE.md
  - docs/007_SDK_SPECIFICATION.md
  - docs/008_METADATA_LAYER_SPEC.md
  - docs/009_TRADE_LAYER_SPEC.md
  - docs/025_ANALYTICS_REVIEW_REPORT.md
related_recipes:
  - RECIPE-001
  - RECIPE-002
  - RECIPE-011
  - RECIPE-022
  - RECIPE-023
tags:
  - end-to-end
  - hs-codes
  - search
  - markdown
  - comparison
  - report
---

Recipe 02 — HS code explorer, end-to-end.

The "search → trade → compare → report" pattern
for an analyst exploring a commodity category:

1. **Search the HS catalogue** via
   ``client.metadata.search_hs(query, edition)``
   to resolve a free-text query into a list of
   matching HS commodity codes.
2. **Fetch India's exports** for the period via
   ``client.trade.get_exports(...)`` (the SDK
   returns records for every HS code in one
   call; the recipe filters down to the
   matched subset).
3. **Compute per-HS code partner totals** for
   two reference partners (e.g. China vs. USA).
4. **Render a Markdown summary** suitable for
   emailing, publishing, or pasting into a
   wiki.

This is the recipe most analysts will reach
for when answering "what does India export to
China vs. USA in the electric-vehicle
category?" — the workflow generalises to any
HS substring search.

The demo function takes pre-built inputs
(``HSCode`` list + ``TradeResponse`` + partner
codes + ``Reporter`` / ``Partner`` metadata)
so the test runs offline; ``main()``
orchestrates the real flow against
``client.metadata`` + ``client.trade``.

Expected output (mock-mode)::

    == Recipe 02: HS code explorer, end-to-end ==
    Query: "electric vehicles"
    HS edition: H6

    [1/4] Searching HS catalogue ...
          5 matches: 870380, 870360, 870370, ...
    [2/4] Fetching India exports (2022) ...
          222 records (5 HS codes after filter)
    [3/4] Comparing partners (CHN vs. USA) ...
          4 commodities, totals: CHN=$5.4B / USA=$2.1B
    [4/4] Writing Markdown summary ...
          ./output/hs_explorer_report.md (24 lines)

    Done.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from un_comtrade import ComtradeClient
from un_comtrade.config import Configuration
from un_comtrade.etl import PipelineContext
from un_comtrade.exceptions import (
    APIError,
    AuthenticationError,
    ComtradeError,
    NetworkError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from un_comtrade.models import HSCode, TradeResponse
from un_comtrade.parser import TradeParser
from un_comtrade.transform import (
    CanonicalDataset,
    TradeTransformer,
)


# ---- constants -------------------------------------------------------------

EXIT_AUTH: int = 4
RECIPE_ID: str = "RECIPE-113"


# ---- helpers ---------------------------------------------------------------


def _normalise_response(
    response: TradeResponse, *, name: str = RECIPE_ID
) -> CanonicalDataset:
    """Parse + transform a ``TradeResponse`` into a dataset."""
    parser = TradeParser(log_skipped=False)
    transformer = TradeTransformer(parser=parser)
    ctx = PipelineContext(pipeline_name=name)
    return transformer(source=list(response.records), context=ctx)


def _format_money(value: Decimal | None) -> str:
    if value is None:
        return "—"
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.2f}B"
    if value >= 1_000_000:
        return f"${value / 1_000_000:,.2f}M"
    if value >= 1_000:
        return f"${value / 1_000:,.2f}K"
    return f"${value:,.2f}"


def _filter_dataset_to_hs_codes(
    dataset: CanonicalDataset, hs_codes: Iterable[str]
) -> CanonicalDataset:
    """Filter the dataset down to records whose cmd_code is in
    ``hs_codes``.

    The SDK doesn't ship a "filter by cmd_code"
    helper, but the records are TradeRecord
    instances with a ``commodity`` attribute. We
    re-wrap the filtered records as a fresh
    ``CanonicalDataset`` so downstream code
    doesn't need to know whether the data was
    pre-filtered or not.
    """
    codes = set(hs_codes)
    filtered = tuple(
        r for r in dataset.records
        if getattr(r.commodity, "commodity_code", None) in codes
    )
    return CanonicalDataset(
        name=f"{dataset.name}__filtered",
        records=filtered,
        parser_name=dataset.parser_name,
        skipped=dataset.skipped,
        duplicates_removed=dataset.duplicates_removed,
        source_count=len(filtered),
        extracted_at=dataset.extracted_at,
        schema_version=dataset.schema_version,
        metadata={
            **dataset.metadata,
            "filter": "cmd_code in " + str(sorted(codes)),
        },
    )


def _per_partner_totals_by_commodity(
    dataset: CanonicalDataset,
    partner_codes: Sequence[int],
) -> dict[str, dict[int, Decimal]]:
    """Compute per-commodity, per-partner export totals.

    Returns a nested mapping
    ``{commodity_code: {partner_code: total_value}}``.
    Only records whose ``partner_code`` is in
    ``partner_codes`` are summed.

    Parameters
    ----------
    dataset
        The (filtered) ``CanonicalDataset``.
    partner_codes
        The partner codes to include.

    Returns
    -------
    dict[str, dict[int, Decimal]]
        Nested map.
    """
    partners = set(partner_codes)
    totals: dict[str, dict[int, Decimal]] = defaultdict(
        lambda: defaultdict(lambda: Decimal("0"))
    )
    for record in dataset.records:
        partner_code = getattr(record.partner, "partner_code", None)
        commodity_code = getattr(
            record.commodity, "commodity_code", None
        )
        if partner_code not in partners or commodity_code is None:
            continue
        primary_value = getattr(
            getattr(record, "trade_value", None),
            "primary_value",
            None,
        )
        if primary_value is None:
            continue
        totals[commodity_code][partner_code] += primary_value
    return {k: dict(v) for k, v in totals.items()}


# ---- markdown rendering ---------------------------------------------------


def render_markdown(
    *,
    query: str,
    hs_edition: str,
    reporter_iso3: str | None,
    reporter_name: str | None,
    reporter_code: int,
    partner_a_iso3: str | None,
    partner_a_name: str | None,
    partner_a_code: int,
    partner_b_iso3: str | None,
    partner_b_name: str | None,
    partner_b_code: int,
    period: str,
    matched_codes: Sequence[HSCode],
    comparison_rows: Sequence[tuple[str, Decimal, Decimal, Decimal]],
    generated_at: str,
) -> str:
    """Render the Markdown summary report."""
    md: list[str] = []
    md.append(
        f"# HS explorer: India → {partner_a_iso3 or partner_a_code} "
        f"vs. {partner_b_iso3 or partner_b_code}"
    )
    md.append("")
    md.append(f"**Reporter:** {reporter_iso3 or reporter_code} "
              f"({reporter_name or '—'})")
    md.append(f"**Period:** {period}")
    md.append(f"**HS edition:** {hs_edition}")
    md.append(f"**Query:** `{query}`")
    md.append(f"**Generated at:** {generated_at}")
    md.append("")

    md.append("## HS catalogue matches")
    md.append("")
    if matched_codes:
        md.append("| Code | Description |")
        md.append("|------|-------------|")
        for code in matched_codes:
            md.append(
                f"| `{code.commodity_code}` "
                f"| {code.display_name or '—'} |"
            )
    else:
        md.append("_No HS codes matched the query._")
    md.append("")

    md.append(
        f"## {partner_a_iso3 or partner_a_code} vs. "
        f"{partner_b_iso3 or partner_b_code} — "
        "per-HS code exports"
    )
    md.append("")
    md.append(
        "| HS code | "
        f"{partner_a_iso3 or partner_a_code} | "
        f"{partner_b_iso3 or partner_b_code} | "
        "Δ (A − B) |"
    )
    md.append(
        "|---------|"
        f"----------|----------|---------|"
    )
    if comparison_rows:
        for label, a_val, b_val, delta in comparison_rows:
            md.append(
                f"| `{label}` | {_format_money(a_val)} "
                f"| {_format_money(b_val)} | "
                f"{_format_money(delta)} |"
            )
    else:
        md.append("| _no rows_ | — | — | — |")
    md.append("")

    md.append("---")
    md.append(
        f"_Generated by `un-comtrade` recipe "
        f"`{RECIPE_ID}`._"
    )
    md.append("")
    return "\n".join(md)


# ---- demo ------------------------------------------------------------------


@dataclass(frozen=True)
class HsExplorerReport:
    """Outcome of the HS explorer pipeline."""

    query: str
    matched_codes: tuple[HSCode, ...]
    comparison_rows: tuple[tuple[str, Decimal, Decimal, Decimal], ...]
    markdown_path: str
    markdown_lines: int
    partner_a_total: Decimal
    partner_b_total: Decimal
    record_count: int
    filtered_record_count: int


def hs_explorer_pipeline_demo(
    *,
    matched_codes: Sequence[HSCode],
    response: TradeResponse,
    partner_a_code: int,
    partner_b_code: int,
    reporter_code: int,
    period: str,
    output_path: Path,
    hs_edition: str,
    reporter_iso3: str | None = None,
    reporter_name: str | None = None,
    partner_a_iso3: str | None = None,
    partner_a_name: str | None = None,
    partner_b_iso3: str | None = None,
    partner_b_name: str | None = None,
) -> HsExplorerReport:
    """The full HS explorer demo.

    Parameters
    ----------
    matched_codes
        HSCode list from
        ``metadata.search_hs(query, edition)``.
    response
        Trade response (test injects a synthetic
        envelope; ``main()`` fetches real).
    partner_a_code, partner_b_code
        The two partner codes to compare.
    reporter_code, reporter_iso3, reporter_name
        Reporter metadata.
    partner_*_iso3, partner_*_name
        Partner metadata.
    period
        Annual period.
    output_path
        Where the Markdown is written.
    hs_edition
        HS edition.

    Returns
    -------
    HsExplorerReport
        Frozen summary of every artefact,
        partner totals, and Markdown size.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ----- [2] Normalise + filter to matched HS codes ---------------
    dataset = _normalise_response(response, name=RECIPE_ID)
    filtered = _filter_dataset_to_hs_codes(
        dataset, (c.commodity_code for c in matched_codes)
    )

    # ----- [3] Compare partners ----------------------------------------
    totals = _per_partner_totals_by_commodity(
        filtered, [partner_a_code, partner_b_code]
    )
    comparison_rows: list[tuple[str, Decimal, Decimal, Decimal]] = []
    partner_a_total = Decimal("0")
    partner_b_total = Decimal("0")
    for code in matched_codes:
        commodity_code = code.commodity_code
        per_partner = totals.get(commodity_code, {})
        a_value = per_partner.get(partner_a_code, Decimal("0"))
        b_value = per_partner.get(partner_b_code, Decimal("0"))
        delta = a_value - b_value
        partner_a_total += a_value
        partner_b_total += b_value
        comparison_rows.append(
            (commodity_code, a_value, b_value, delta)
        )

    # ----- [4] Render + write Markdown ------------------------------
    generated_at = datetime.now(timezone.utc).isoformat()
    md = render_markdown(
        query="(injected)",
        hs_edition=hs_edition,
        reporter_iso3=reporter_iso3,
        reporter_name=reporter_name,
        reporter_code=reporter_code,
        partner_a_iso3=partner_a_iso3,
        partner_a_name=partner_a_name,
        partner_a_code=partner_a_code,
        partner_b_iso3=partner_b_iso3,
        partner_b_name=partner_b_name,
        partner_b_code=partner_b_code,
        period=period,
        matched_codes=matched_codes,
        comparison_rows=comparison_rows,
        generated_at=generated_at,
    )
    output_path.write_text(md, encoding="utf-8")

    return HsExplorerReport(
        query="(injected)",
        matched_codes=tuple(matched_codes),
        comparison_rows=tuple(comparison_rows),
        markdown_path=str(output_path),
        markdown_lines=md.count("\n") + 1,
        partner_a_total=partner_a_total,
        partner_b_total=partner_b_total,
        record_count=len(dataset.records),
        filtered_record_count=len(filtered.records),
    )


# ---- error handling --------------------------------------------------------


def _exit_code_for(exc: BaseException) -> int:
    if isinstance(exc, ValidationError):
        return 3
    if isinstance(exc, AuthenticationError):
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
    parser = argparse.ArgumentParser(
        prog=RECIPE_ID, description=__doc__,
    )
    parser.add_argument(
        "--query", default="electric vehicles",
        help='HS substring query (default: "electric vehicles").',
    )
    parser.add_argument(
        "--reporter", type=int, default=699,
        help="Reporter code (default: 699 = India).",
    )
    parser.add_argument(
        "--partner-a", type=int, default=156,
        help="First comparison partner (default: 156 = China).",
    )
    parser.add_argument(
        "--partner-b", type=int, default=840,
        help="Second comparison partner (default: 840 = USA).",
    )
    parser.add_argument(
        "--period", default="2022",
        help='Annual period (default: "2022").',
    )
    parser.add_argument(
        "--hs-edition", default="H6",
        help="HS edition (default: H6).",
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("./output/hs_explorer_report.md"),
        help="Output Markdown path.",
    )
    args = parser.parse_args(argv)

    print("== Recipe 02: HS code explorer, end-to-end ==")
    print(f"Query: {args.query!r}")
    print(f"HS edition: {args.hs_edition}")

    key = os.environ.get("UN_COMTRADE_KEY", "").strip() or None
    if not key:
        print(
            "ERROR: UN_COMTRADE_KEY is not set.",
            file=sys.stderr,
        )
        return EXIT_AUTH
    config = Configuration(api_key=key)

    try:
        with ComtradeClient(config) as client:
            print("[1/4] Searching HS catalogue ...")
            matched = client.metadata.search_hs(
                args.query, edition=args.hs_edition
            )
            print(
                f"      {len(matched)} matches: "
                f"{', '.join(c.commodity_code for c in matched[:5])}"
            )

            print("[2/4] Fetching India exports ...")
            response = client.trade.get_exports(
                reporter_code=args.reporter, period=args.period
            )

            print("[3/4] Comparing partners ...")
            report = hs_explorer_pipeline_demo(
                matched_codes=matched,
                response=response,
                partner_a_code=args.partner_a,
                partner_b_code=args.partner_b,
                reporter_code=args.reporter,
                period=args.period,
                output_path=args.output,
                hs_edition=args.hs_edition,
            )
    except ComtradeError as exc:
        code = _exit_code_for(exc)
        print(
            f"recipe={RECIPE_ID} error_class={type(exc).__name__} "
            f"message={exc} exit_code={code}",
            file=sys.stderr,
        )
        return code

    print("[4/4] Writing Markdown summary ...")
    print(
        f"      {args.output} "
        f"({report.markdown_lines} lines)"
    )
    print(
        f"      totals: CHN={_format_money(report.partner_a_total)} "
        f"USA={_format_money(report.partner_b_total)}"
    )
    print("Done.")
    print(
        f"recipe={RECIPE_ID} query={args.query!r} "
        f"matches={len(report.matched_codes)} "
        f"records={report.record_count} "
        f"filtered={report.filtered_record_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())