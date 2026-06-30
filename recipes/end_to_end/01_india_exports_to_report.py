"""
---
recipe_id: RECIPE-111
title: India exports — fetch, normalise, store, analyse, report
category: end_to_end
difficulty: intermediate
sdk_version: >=1.0.2
requires_api_key: yes
estimated_runtime: 1-10min
composes:
  - client.trade
  - client.etl
  - client.storage
  - client.analytics
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
      description: Trade flow (X = exports, M = imports).
    - name: output_dir
      type: str
      default: "./output"
      description: Output directory for the dataset + report.
outputs:
  - kind: file
    path: <output_dir>/india_exports_<period>.duckdb
    description: |
      DuckDB database with one row per
      ``TradeRecord`` and a
      ``un_comtrade_datasets`` provenance table.
  - kind: file
    path: <output_dir>/india_exports_<period>.report.csv
    description: |
      Per-partner summary: ISO3, name,
      exports, partner_share.
  - kind: file
    path: <output_dir>/india_exports_<period>.report.json
    description: |
      Top-line summary: total exports,
      partner count, top-5 partners.
  - kind: stdout
    path: null
    description: |
      Stage-by-stage run summary (fetched /
      parsed / persisted / analysed).
related_docs:
  - docs/003_ARCHITECTURE.md
  - docs/007_SDK_SPECIFICATION.md
  - docs/025_ANALYTICS_REVIEW_REPORT.md
  - docs/011_ETL_SPECIFICATION.md
  - docs/012_STORAGE_SPECIFICATION.md
related_recipes:
  - RECIPE-021
  - RECIPE-031
  - RECIPE-034
  - RECIPE-036
tags:
  - end-to-end
  - india
  - exports
  - duckdb
  - csv
  - json
  - report
---

Recipe 01 — India exports, end-to-end.

The canonical "fetch → analyse" workflow for a
trade analyst working with India's UN Comtrade
exports:

1. **Fetch** via ``client.trade.get_exports(...)``.
2. **Normalise** via ``TradeParser`` +
   ``TradeTransformer`` (parse raw upstream
   rows into canonical ``TradeRecord`` instances).
3. **Store** in a DuckDB database via
   ``DuckDBWriter``.
4. **Analyse** via the analytics layer:
   ``country_summary`` for the totals;
   ``top_partners`` for the partner ranking.
5. **Export** the results as both CSV (per
   partner) and JSON (top-line summary).

This is the recipe most analysts will copy. It
demonstrates the full SDK integration pattern
in one script: SDK fetch → ETL normalisation
→ Storage persistence → Analytics computation
→ Report emission.

The demo function takes a pre-built
``TradeResponse`` (so the test runs offline)
plus an output directory; ``main()`` is the
real-data entry point.

Expected output (mock-mode)::

    == Recipe 01: India exports, end-to-end ==
    Reporter: 699 (India)  Period: 2022  Flow: X
    [1/5] Fetching exports (T01) ...
          222 records fetched in 0.42s
    [2/5] Normalising (TradeParser + TradeTransformer) ...
          222 canonical records (0 skipped)
    [3/5] Persisting to DuckDB ...
          222 rows written to ./output/india_exports_2022.duckdb
    [4/5] Running analytics ...
          country_summary: total_exports=432,000,000,000
          top 5 partners: CHN, USA, ARE, HKG, SGP
    [5/5] Writing reports ...
          CSV: ./output/india_exports_2022.report.csv (5 rows)
          JSON: ./output/india_exports_2022.report.json
    Done.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from un_comtrade import ComtradeClient
from un_comtrade.analytics.country import country_summary
from un_comtrade.analytics.partner import top_partners
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
from un_comtrade.models import TradeResponse
from un_comtrade.parser import TradeParser
from un_comtrade.storage import StorageConfig, StorageError
from un_comtrade.storage.duckdb import DuckDBWriter
from un_comtrade.transform import (
    CanonicalDataset,
    TradeTransformer,
)


# ---- constants -------------------------------------------------------------

EXIT_AUTH: int = 4
RECIPE_ID: str = "RECIPE-111"
_VALID_FLOWS: tuple[str, ...] = ("X", "M")


# ---- auth ------------------------------------------------------------------


def _require_api_key() -> str | None:
    """API key is required for the real-data path.

    Returns the key on success. Returns None
    when running the demo with a synthetic
    response (no fetch required).
    """
    return os.environ.get("UN_COMTRADE_KEY", "").strip() or None


# ---- dataset construction -------------------------------------------------


def normalise_response(
    response: TradeResponse, *, name: str = RECIPE_ID
) -> CanonicalDataset:
    """Parse + transform a ``TradeResponse`` into a ``CanonicalDataset``.

    The "normalise" stage of the pipeline:
    raw upstream records → TradeRecord → canonical
    dataset. The dataset is the single source of
    truth that every downstream stage consumes.
    """
    parser = TradeParser(log_skipped=False)
    transformer = TradeTransformer(parser=parser)
    ctx = PipelineContext(pipeline_name=name)
    return transformer(source=list(response.records), context=ctx)


# ---- demo ------------------------------------------------------------------


@dataclass(frozen=True)
class ReportFiles:
    """Paths to the artefacts produced by the recipe."""

    database: Path
    partner_csv: Path
    summary_json: Path


@dataclass(frozen=True)
class PipelineReport:
    """The full outcome of the India-exports pipeline."""

    reporter_code: int
    period: str
    flow: str
    record_count: int
    skipped: int
    database_path: str
    partner_csv_path: str
    summary_json_path: str
    total_exports: Decimal
    partner_count: int
    top_partner_iso3: tuple[str | None, ...]
    top_partner_codes: tuple[int, ...]
    partner_share_top5: dict[str, Decimal] = field(default_factory=dict)


def emit_reports(
    dataset: CanonicalDataset,
    *,
    reporter_code: int,
    output_dir: Path,
    period: str,
    flow: str,
) -> PipelineReport:
    """Run the full pipeline: store + analyse + emit reports.

    This is the **single function** that
    demonstrates the end-to-end composition:

    1. Persist the dataset to DuckDB.
    2. Compute the country summary (totals).
    3. Rank partners by total trade.
    4. Emit the per-partner CSV.
    5. Emit the top-line JSON summary.

    Returns a frozen ``PipelineReport`` that
    captures every artefact and the headline
    numbers. Tests assert on this dataclass.

    Raises
    ------
    StorageError
        When the DuckDB write fails.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / f"india_exports_{period}.duckdb"

    # ----- [3] Persist ---------------------------------------------------
    writer = DuckDBWriter()
    config = StorageConfig(root=str(db_path), overwrite=True)
    writer.store(dataset, config)

    # ----- [4] Analyse ---------------------------------------------------
    summary = country_summary(dataset, reporter_code=reporter_code)
    partners = top_partners(
        dataset, reporter_code=reporter_code, limit=None
    )

    total_exports: Decimal = (
        summary.total_exports if summary is not None
        else Decimal("0")
    )
    partner_count: int = (
        summary.partner_count if summary is not None else 0
    )

    # ----- [5] Emit reports ----------------------------------------------
    csv_path = output_dir / f"india_exports_{period}.report.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "rank", "partner_code", "partner_iso3",
            "partner_name", "total_trade",
            "trade_balance", "share_pct",
        ])
        for rank, row in enumerate(partners, start=1):
            share = (
                (row.total_trade / total_exports * Decimal("100"))
                if total_exports > 0 else Decimal("0")
            )
            w.writerow([
                rank, row.partner_code,
                row.partner_iso3 or "",
                row.partner_name or "",
                str(row.total_trade),
                str(row.trade_balance),
                f"{share:.2f}",
            ])

    json_path = output_dir / f"india_exports_{period}.report.json"
    summary_payload = {
        "recipe_id": RECIPE_ID,
        "reporter_code": reporter_code,
        "period": period,
        "flow": flow,
        "record_count": len(dataset.records),
        "skipped": dataset.skipped,
        "total_exports": str(total_exports),
        "partner_count": partner_count,
        "top_5_partners": [
            {
                "rank": idx + 1,
                "partner_code": row.partner_code,
                "partner_iso3": row.partner_iso3,
                "partner_name": row.partner_name,
                "total_trade": str(row.total_trade),
                "trade_balance": str(row.trade_balance),
            }
            for idx, row in enumerate(partners[:5])
        ],
        "database_path": str(db_path),
        "partner_csv_path": str(csv_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    json_path.write_text(
        json.dumps(summary_payload, indent=2, default=str),
        encoding="utf-8",
    )

    top_iso3 = tuple(
        row.partner_iso3 for row in partners[:5]
    )
    top_codes = tuple(row.partner_code for row in partners[:5])
    share_map = {
        row.partner_iso3 or "—":
        (row.total_trade / total_exports * Decimal("100"))
        if total_exports > 0 else Decimal("0")
        for row in partners[:5]
    }
    return PipelineReport(
        reporter_code=reporter_code,
        period=period,
        flow=flow,
        record_count=len(dataset.records),
        skipped=dataset.skipped,
        database_path=str(db_path),
        partner_csv_path=str(csv_path),
        summary_json_path=str(json_path),
        total_exports=total_exports,
        partner_count=partner_count,
        top_partner_iso3=top_iso3,
        top_partner_codes=top_codes,
        partner_share_top5=share_map,
    )


def india_exports_pipeline_demo(
    response: TradeResponse,
    output_dir: Path,
    *,
    reporter_code: int = 699,
    period: str = "2022",
    flow: str = "X",
) -> PipelineReport:
    """The full pipeline demo: response → DuckDB → report.

    Parameters
    ----------
    response
        A ``TradeResponse`` envelope. The test
        fixture injects a synthetic envelope;
        ``main()`` invokes
        ``client.trade.get_exports`` to fetch
        real data.
    output_dir
        Where the DuckDB file, partner CSV,
        and summary JSON land.
    reporter_code
        UN Comtrade reporter code (default
        ``699`` for India).
    period
        Annual period string (default
        ``"2022"``).
    flow
        Trade flow (``"X"`` exports, ``"M"``
        imports). Default ``"X"``.

    Returns
    -------
    PipelineReport
        Frozen summary of every artefact and
        headline number.
    """
    dataset = normalise_response(response, name=RECIPE_ID)
    return emit_reports(
        dataset,
        reporter_code=reporter_code,
        output_dir=output_dir,
        period=period,
        flow=flow,
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


# ---- main ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    key = _require_api_key()

    parser = argparse.ArgumentParser(
        prog=RECIPE_ID, description=__doc__,
    )
    parser.add_argument(
        "--reporter", type=int, default=699,
        help="UN Comtrade reporter code (default: 699 = India).",
    )
    parser.add_argument(
        "--period", default="2022",
        help='Annual period (default: "2022").',
    )
    parser.add_argument(
        "--flow", choices=_VALID_FLOWS, default="X",
        help="Trade flow (default: X = exports).",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("./output"),
        help="Output directory (default: ./output).",
    )
    args = parser.parse_args(argv)

    print("== Recipe 01: India exports, end-to-end ==")
    print(
        f"Reporter: {args.reporter} (India)  "
        f"Period: {args.period}  Flow: {args.flow}"
    )

    config = Configuration(api_key=key) if key else None
    if not key:
        print(
            "ERROR: UN_COMTRADE_KEY is not set. "
            "Set it to your UN Comtrade API key and re-run.",
            file=sys.stderr,
        )
        return EXIT_AUTH

    try:
        with ComtradeClient(config) as client:
            method = (
                client.trade.get_exports
                if args.flow == "X"
                else client.trade.get_imports
            )
            print("[1/5] Fetching exports (T01) ..."
                  if args.flow == "X"
                  else "[1/5] Fetching imports (T02) ...")
            response = method(
                reporter_code=args.reporter, period=args.period
            )
            print("[2/5] Normalising (TradeParser + TradeTransformer) ...")
            dataset = normalise_response(response, name=RECIPE_ID)
            print(
                f"      {len(dataset.records)} canonical records "
                f"({dataset.skipped} skipped)"
            )
            print("[3/5] Persisting to DuckDB ...")
            print("[4/5] Running analytics ...")
            print("[5/5] Writing reports ...")
            report = emit_reports(
                dataset,
                reporter_code=args.reporter,
                output_dir=args.output,
                period=args.period,
                flow=args.flow,
            )
    except ComtradeError as exc:
        code = _exit_code_for(exc)
        print(
            f"recipe={RECIPE_ID} error_class={type(exc).__name__} "
            f"message={exc} exit_code={code}",
            file=sys.stderr,
        )
        return code

    print(
        f"      {report.record_count} rows written to "
        f"{report.database_path}"
    )
    print(
        f"      country_summary: total_exports="
        f"{report.total_exports:,}"
    )
    print(
        f"      top 5 partners: "
        f"{', '.join(p for p in report.top_partner_iso3 if p)}"
    )
    print(
        f"      CSV: {report.partner_csv_path} "
        f"({min(report.partner_count, 5)} rows)"
    )
    print(f"      JSON: {report.summary_json_path}")
    print("Done.")
    print(
        f"recipe={RECIPE_ID} reporter={args.reporter} "
        f"period={args.period} records={report.record_count} "
        f"partners={report.partner_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())