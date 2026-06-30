"""
---
recipe_id: RECIPE-021
title: Country trade balance (analytics)
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
outputs:
  - kind: stdout
    path: null
    description: |
      Single-line headline + a small table with
      exports, imports, balance, and record count
      for the reporter.
related_docs:
  - docs/007_SDK_SPECIFICATION.md
  - docs/011_ETL_SPECIFICATION.md
related_recipes:
  - RECIPE-022
  - RECIPE-023
tags:
  - analytics
  - balance
  - country
---

Recipe 01 — Country trade balance.

Demonstrates the canonical analytics flow:

1. Fetch trade data via ``client.trade``
   (one call per flow: exports + imports).
2. Parse the upstream records into canonical
   ``TradeRecord`` instances.
3. Wrap the parsed records in a
   ``CanonicalDataset``.
4. Run ``balance.country_balance(...)`` against
   the dataset.
5. Render the result.

The demo function takes a pre-built
``CanonicalDataset``. The script's ``main()``
fetches the data and builds the dataset. The
regression test injects a synthetic dataset.

Expected output (mock-mode)::

    == Recipe 01: Country Trade Balance ==
    Reporter: 699 (IND)  Period: 2022
    Loading exports (T01) ...
    Loading imports (T02) ...
    Building CanonicalDataset ...
      222 export records + 210 import records
    Country balance (analytics):
      exports  : 123,456,789,012.34
      imports  : 234,567,890,123.45
      balance  : -111,111,101,111.11
      records  : 432 (222 exports + 210 imports)
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
from un_comtrade.analytics.balance import country_balance
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
    name: str = "country_balance",
) -> CanonicalDataset:
    """Parse a sequence of trade responses and wrap the result.

    The analytics layer operates exclusively on
    ``CanonicalDataset``. The recipe's ``main()``
    uses this helper to convert one or more
    ``TradeResponse`` envelopes (one per flow,
    per period) into a single dataset.
    """
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
        metadata={
            "responses": [
                {
                    "count": r.count,
                    "elapsed_seconds": r.elapsed_seconds,
                    "skipped": r.skipped,
                }
                for r in responses
            ]
        },
    )


# ---- demo ------------------------------------------------------------------


@dataclass(frozen=True)
class CountryBalanceResult:
    """Demo return value — frozen for testability.

    Captures the headline numbers the recipe
    prints. The underlying ``CountryBalanceRow``
    is also returned in case the consumer wants
    the full row.
    """

    reporter_code: int
    reporter_iso3: str | None
    reporter_name: str | None
    total_exports: Decimal
    total_imports: Decimal
    trade_balance: Decimal
    record_count: int


def country_balance_demo(
    dataset: CanonicalDataset,
    *,
    reporter_code: int,
) -> CountryBalanceResult | None:
    """Run ``country_balance`` for one reporter.

    The function returns ``None`` when the
    reporter has no records in the dataset — the
    caller decides whether that's a business
    outcome (print "no data") or an error
    (raise).
    """
    rows = country_balance(dataset, reporter_code=reporter_code)
    if not rows:
        return None
    row = rows[0]
    return CountryBalanceResult(
        reporter_code=row.reporter_code,
        reporter_iso3=row.reporter_iso3,
        reporter_name=row.reporter_name,
        total_exports=row.total_exports,
        total_imports=row.total_imports,
        trade_balance=row.trade_balance,
        record_count=row.record_count,
    )


# ---- output ---------------------------------------------------------------


def render(result: CountryBalanceResult) -> str:
    """Format the balance result for stdout."""
    name = result.reporter_name or "(unknown)"
    iso = result.reporter_iso3 or "???"
    return (
        f"Country balance (analytics):\n"
        f"  reporter  : {result.reporter_code} ({iso} / {name})\n"
        f"  exports   : {result.total_exports:>20,.2f}\n"
        f"  imports   : {result.total_imports:>20,.2f}\n"
        f"  balance   : {result.trade_balance:>20,.2f}\n"
        f"  records   : {result.record_count}\n"
    )


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
    """Build a real ``ComtradeClient`` and run the demo."""
    key = _require_api_key()

    parser = argparse.ArgumentParser(
        prog="RECIPE-021",
        description=__doc__,
    )
    parser.add_argument(
        "--reporter",
        type=int,
        default=699,
        help="UN Comtrade reporter code (default: 699 = India).",
    )
    parser.add_argument(
        "--period",
        default="2022",
        help='Annual period, e.g. "2022" (default: 2022).',
    )
    args = parser.parse_args(argv)

    print("== Recipe 01: Country Trade Balance ==")
    print(f"Reporter: {args.reporter}  Period: {args.period}")
    print("Loading exports (T01) ...")
    print("Loading imports (T02) ...")
    print("Building CanonicalDataset ...")

    config = Configuration(api_key=key)
    try:
        with ComtradeClient(config) as client:
            exports_resp = client.trade.get_exports(
                reporter_code=args.reporter, period=args.period
            )
            imports_resp = client.trade.get_imports(
                reporter_code=args.reporter, period=args.period
            )
            dataset = build_dataset_from_responses(
                exports_resp, imports_resp
            )
            print(
                f"  {sum(1 for r in dataset.records if r.flow.flow_code == 'X')} "
                f"export records + "
                f"{sum(1 for r in dataset.records if r.flow.flow_code == 'M')} "
                f"import records"
            )
            result = country_balance_demo(
                dataset, reporter_code=args.reporter
            )
    except ComtradeError as exc:
        code = _exit_code_for(exc)
        print(
            f"recipe=RECIPE-021 error_class={type(exc).__name__} "
            f"message={exc} exit_code={code}",
            file=sys.stderr,
        )
        return code

    if result is None:
        print(f"no records for reporter={args.reporter} in period={args.period}")
        return 8
    print(render(result))
    print(
        f"recipe=RECIPE-021 reporter={args.reporter} "
        f"balance={result.trade_balance:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
