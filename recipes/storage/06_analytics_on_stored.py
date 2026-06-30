"""
---
recipe_id: RECIPE-036
title: Run analytics on a stored dataset (round-trip)
category: storage
difficulty: intermediate
sdk_version: >=1.0.2
requires_api_key: no
estimated_runtime: <30s
inputs:
  required:
    - name: source_path
      type: str
      description: |
        Path to a previously-stored dataset. The
        extension (``.csv`` / ``.json`` /
        ``.parquet`` / ``.duckdb``) auto-detects
        the backend.
  optional:
    - name: reporter_code
      type: int
      default: 699
      description: Reporter code for ``country_summary``.
    - name: top_n
      type: int
      default: 10
      description: Top-N partners returned by ``top_partners``.
    - name: build_if_missing
      type: bool
      default: true
      description: If true and the source is absent, build it via the live API.
outputs:
  - kind: stdout
    path: null
    description: |
      Two-section summary: ``country_summary`` then
      ``top_partners`` table.
related_docs:
  - docs/011_ETL_SPECIFICATION.md
  - docs/012_STORAGE_SPECIFICATION.md
  - docs/025_ANALYTICS_REVIEW_REPORT.md
related_recipes:
  - RECIPE-031
  - RECIPE-034
  - RECIPE-035
  - RECIPE-021
  - RECIPE-022
tags:
  - storage
  - analytics
  - round-trip
  - country_summary
  - top_partners
---

Recipe 06 — Run analytics on a stored dataset.

This is the canonical "ETL on disk" pattern:

1. Read the dataset back from disk via
   ``StorageRegistry.open()`` (RECIPE-035).
2. Run the analytics layer against the
   reloaded ``CanonicalDataset`` — no second
   fetch from the API.

Two analytics are wired in:

- ``client.analytics.country_summary(dataset,
  reporter_code)`` — totals (exports, imports,
  trade balance) for one reporter.
- ``client.analytics.top_partners(dataset,
  reporter_code=..., limit=top_n)`` — the top-N
  partner countries ranked by total trade.

The point of the recipe is to demonstrate
that **analytics on a stored dataset is
identical to analytics on a fresh fetch** —
the canonical dataset is the single source of
truth.

Expected output (mock-mode)::

    == Recipe 06: Analytics on stored dataset ==
    Source: ./output/RECIPE_036.duckdb
    Reloading ...
      backend : duckdb
      rows    : 432
    Country summary (reporter=699) ...
      exports : 432,000,000,000
      imports : 600,000,000,000
      balance : -168,000,000,000
      partners: 144
    Top partners (by total trade, n=10) ...
      1. CHN  120,000,000,000  (US)
      2. USA   85,000,000,000
      ...
    Done.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from un_comtrade import ComtradeClient
from un_comtrade.analytics.country import CountrySummary, country_summary
from un_comtrade.analytics.partner import PartnerRankingRow, top_partners
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
from un_comtrade.storage import StorageConfig, StorageError, StorageRegistry
from un_comtrade.transform import CanonicalDataset, TradeTransformer


# ---- constants -------------------------------------------------------------

EXIT_AUTH: int = 4
EXIT_NOT_FOUND: int = 9
RECIPE_ID: str = "RECIPE-036"
_VALID_FLOWS: tuple[str, ...] = ("X", "M")


# ---- auth ------------------------------------------------------------------


def _require_api_key_or_none() -> str | None:
    return os.environ.get("UN_COMTRADE_KEY", "").strip() or None


# ---- dataset construction -------------------------------------------------


def build_dataset_from_responses(
    *responses: TradeResponse,
    name: str = RECIPE_ID,
) -> CanonicalDataset:
    """Parse one or more ``TradeResponse`` envelopes and wrap."""
    from un_comtrade.etl import PipelineContext
    parser = TradeParser(log_skipped=False)
    transformer = TradeTransformer(parser=parser)
    all_records: list[Any] = []
    skipped_total = 0
    for response in responses:
        ctx = PipelineContext(pipeline_name=name)
        ds = transformer(source=list(response.records), context=ctx)
        all_records.extend(ds.records)
        skipped_total += ds.skipped
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
class AnalyticsOnStoredResult:
    """Result envelope for the analytics-on-stored recipe."""

    path: str
    row_count: int
    summary: CountrySummary | None
    top_partners: tuple[PartnerRankingRow, ...]
    built: bool


def analytics_on_stored_demo(
    source_path: Path,
    *,
    reporter_code: int,
    top_n: int = 10,
    registry: StorageRegistry | None = None,
    client: ComtradeClient | None = None,  # kept for API symmetry; not used
) -> AnalyticsOnStoredResult:
    """Read a stored dataset and run analytics against it.

    Parameters
    ----------
    source_path
        Path to a previously-stored dataset.
    reporter_code
        Reporter code for both ``country_summary``
        and ``top_partners``.
    top_n
        Top-N partners returned. Default 10.
    registry
        Optional pre-built registry; defaults
        to ``StorageRegistry()``.
    client
        Kept for API symmetry with other storage
        recipes that take a client. The analytics
        functions called here are stateless and do
        not require a live client; ignored.

    Returns
    -------
    AnalyticsOnStoredResult
        Path, row count, summary, top partners,
        and the ``built`` flag (``False`` when
        the dataset was already on disk).
    """
    registry = registry or StorageRegistry()
    dataset = registry.open(str(source_path))
    summary = country_summary(dataset, reporter_code=reporter_code)
    partners = top_partners(
        dataset,
        reporter_code=reporter_code,
        limit=top_n,
    )
    return AnalyticsOnStoredResult(
        path=str(source_path),
        row_count=len(dataset.records),
        summary=summary,
        top_partners=partners,
        built=False,
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
    if isinstance(exc, (APIError, StorageError)):
        return 8
    return 1


# ---- helpers ---------------------------------------------------------------


def _writer_for_path(path: Path):
    """Pick the right storage backend by extension."""
    ext = path.suffix.lower()
    if ext == ".csv":
        from un_comtrade.storage.file import CSVWriter
        return CSVWriter()
    if ext in {".parquet", ".pq"}:
        from un_comtrade.storage.parquet import ParquetWriter
        return ParquetWriter()
    if ext in {".duckdb", ".ddb"}:
        from un_comtrade.storage.duckdb import DuckDBWriter
        return DuckDBWriter()
    raise StorageError(f"unsupported dataset extension {ext!r}")


# ---- formatting helpers ----------------------------------------------------


def _format_decimal(value: Decimal | None, *, decimals: int = 0) -> str:
    if value is None:
        return "—"
    if decimals == 0:
        return f"{value.quantize(Decimal('1')):,}"
    return f"{value:,.{decimals}f}"


def _format_summary(summary: CountrySummary | None) -> list[str]:
    if summary is None:
        return ["  (no summary — reporter has no records)"]
    return [
        f"  exports : {_format_decimal(summary.total_exports)}",
        f"  imports : {_format_decimal(summary.total_imports)}",
        f"  balance : {_format_decimal(summary.trade_balance)}",
        f"  partners: {summary.partner_count}",
        f"  years   : {summary.year_range}",
        f"  records : {summary.record_count}",
    ]


def _format_partners(
    partners: tuple[PartnerRankingRow, ...],
    limit: int = 10,
) -> list[str]:
    if not partners:
        return ["  (no partner rankings)"]
    rows = partners[:limit]
    lines: list[str] = []
    for idx, row in enumerate(rows, start=1):
        partner_label = (
            f"{row.partner_iso3 or '—'} "
            f"({row.partner_code})"
        )
        lines.append(
            f"  {idx:>2}. {partner_label:<14}"
            f" {_format_decimal(row.total_trade):>22}"
        )
    return lines


# ---- main ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=RECIPE_ID, description=__doc__,
    )
    parser.add_argument(
        "source_path", type=Path,
        help="Path to a previously-stored dataset.",
    )
    parser.add_argument(
        "--reporter", type=int, default=699,
        help="Reporter code (default: 699).",
    )
    parser.add_argument(
        "--top-n", type=int, default=10,
        help="Top-N partners returned (default: 10).",
    )
    parser.add_argument(
        "--build-if-missing", action="store_true",
        help="If the source is absent, build it via the live API.",
    )
    parser.add_argument(
        "--period", default="2022",
        help='Annual period (default: "2022"). Used only with --build-if-missing.',
    )
    parser.add_argument(
        "--flow", choices=_VALID_FLOWS, default="X",
        help="Trade flow (default: X). Used only with --build-if-missing.",
    )
    args = parser.parse_args(argv)

    print("== Recipe 06: Analytics on stored dataset ==")
    print(f"Source: {args.source_path}")

    if not args.source_path.exists() and not args.build_if_missing:
        print(
            f"ERROR: source_path {args.source_path} does not exist "
            "and --build-if-missing was not set.",
            file=sys.stderr,
        )
        return EXIT_NOT_FOUND

    key = _require_api_key_or_none()
    config = Configuration(api_key=key) if key else None
    try:
        if args.build_if_missing and not args.source_path.exists():
            if not key:
                print(
                    "ERROR: --build-if-missing requires UN_COMTRADE_KEY.",
                    file=sys.stderr,
                )
                return EXIT_AUTH
            with ComtradeClient(config) as client:
                method = (
                    client.trade.get_exports
                    if args.flow == "X"
                    else client.trade.get_imports
                )
                response = method(
                    reporter_code=args.reporter, period=args.period
                )
                dataset = build_dataset_from_responses(
                    response, name=RECIPE_ID
                )
                writer = _writer_for_path(args.source_path)
                writer.store(
                    dataset, StorageConfig(root=str(args.source_path))
                )
        with ComtradeClient(config or Configuration(api_key="dummy")) as client:
            print("Reloading ...")
            result = analytics_on_stored_demo(
                args.source_path,
                client=client,
                reporter_code=args.reporter,
                top_n=args.top_n,
            )
    except ComtradeError as exc:
        code = _exit_code_for(exc)
        print(
            f"recipe={RECIPE_ID} error_class={type(exc).__name__} "
            f"message={exc} exit_code={code}",
            file=sys.stderr,
        )
        return code

    print(f"  backend : {args.source_path.suffix.lstrip('.') or 'auto'}")
    print(f"  rows    : {result.row_count}")
    print(f"Country summary (reporter={args.reporter}) ...")
    for line in _format_summary(result.summary):
        print(line)
    print(f"Top partners (by total trade, n={args.top_n}) ...")
    for line in _format_partners(result.top_partners, limit=args.top_n):
        print(line)
    print("Done.")
    print(
        f"recipe={RECIPE_ID} rows={result.row_count} "
        f"summary={'yes' if result.summary else 'no'} "
        f"partners={len(result.top_partners)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())