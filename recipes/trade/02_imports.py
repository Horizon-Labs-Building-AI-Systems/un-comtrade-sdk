"""
---
recipe_id: RECIPE-012
title: Fetch annual imports for one partner (T02) to CSV
category: trade
difficulty: beginner
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
    - name: partner_code
      type: int
      default: 156
      description: |
        UN Comtrade partner code. The default (156)
        selects China. Set to 0 for the World
        aggregate, or to a specific country code
        for a bilateral view.
    - name: output
      type: str
      default: ./output
      description: Directory the CSV file is written into.
outputs:
  - kind: file
    path: output/RECIPE_012_<UTC-timestamp>.csv
    description: |
      CSV file with one row per trade record. The
      header is fixed: ``refPeriodId,reporterCode,
      partnerCode,partnerISO,cmdCode,flowCode,
      primaryValue``.
  - kind: file
    path: output/RECIPE_012_<UTC-timestamp>.meta.json
    description: Metadata sidecar (recipe id, partner, period, row count, SHA-256 digest).
  - kind: stdout
    path: null
    description: Single-line summary of the run.
related_docs:
  - docs/007_SDK_SPECIFICATION.md
  - docs/009_TRADE_LAYER_SPEC.md
related_recipes:
  - RECIPE-011
  - RECIPE-013
  - RECIPE-014
tags:
  - trade
  - imports
  - t02
  - csv
  - bilateral
  - auth
---

Recipe 02 — Fetch annual imports for one partner to CSV.

This recipe demonstrates the **partner filter** on
the T02 imports endpoint. The trade service
restricts the upstream to records whose
``partnerCode`` matches the requested code; the
recipe then persists the result to CSV using the
stdlib ``csv`` module (the simplest portable
trade-data artefact).

The recipe covers all four pillars:

- **Authentication** — the key is read up front
  with ``_require_api_key()``; a missing key exits
  with code 4 before any I/O.
- **Filtering** — ``partner_code`` narrows the
  upstream response to one country. The default
  ``156`` selects China.
- **Output format** — CSV is the lingua franca for
  trade data; the recipe writes one row per record
  with a fixed header.
- **Error handling** — the ``main()`` body wraps
  the call in a ``try / except ComtradeError`` and
  maps the SDK exception hierarchy to the cookbook
  exit codes (``recipes/README.md`` §6.4).

Expected output (mock-mode)::

    == Recipe 02: Fetch Annual Imports (one partner) ==
    Auth: OK (key configured)
    Reporter: 699  Partner: 156  Period: 2022
    Fetching imports for reporter=699 partner=156 period=2022 ...
      records returned: 212
      elapsed_seconds  : 0.27
      upstream_url     : https://comtradeapi.un.org/data/v1/get/C/A/HS?...
    Writing 212 records to CSV ...
      output : output/RECIPE_012_20260629T103000Z.csv
      sidecar: output/RECIPE_012_20260629T103000Z.meta.json
    Done.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from un_comtrade import ComtradeClient
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


# ---- constants -------------------------------------------------------------

#: Fixed CSV column order. Documented in the frontmatter ``outputs`` block.
CSV_COLUMNS: tuple[str, ...] = (
    "refPeriodId",
    "reporterCode",
    "partnerCode",
    "partnerISO",
    "cmdCode",
    "flowCode",
    "primaryValue",
)

#: Exit code for a missing API key. Mirrors
#: ``AuthenticationError`` per ``recipes/README.md`` §6.4.
EXIT_AUTH: int = 4


# ---- auth ------------------------------------------------------------------


def _require_api_key() -> str:
    """Read the API key from the environment and validate it."""
    key = os.environ.get("UN_COMTRADE_KEY", "").strip()
    if not key:
        print(
            "ERROR: UN_COMTRADE_KEY is not set. "
            "Set it to your UN Comtrade API key and re-run.",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_AUTH)
    return key


# ---- demo ------------------------------------------------------------------


def imports_demo(
    client: ComtradeClient,
    *,
    reporter_code: int,
    period: str,
    partner_code: int,
) -> TradeResponse:
    """Fetch annual imports for one partner.

    Parameters
    ----------
    client
        A ``ComtradeClient`` whose ``trade`` service
        is reachable.
    reporter_code
        UN Comtrade reporter code (e.g. ``699`` for
        India).
    period
        Annual period string.
    partner_code
        UN Comtrade partner code. The trade service
        narrows the upstream response to records
        whose ``partnerCode`` matches this value.

    Returns
    -------
    TradeResponse
        The canonical envelope returned by the
        trade service.
    """
    print(
        f"Reporter: {reporter_code}  "
        f"Partner: {partner_code}  Period: {period}"
    )
    print(
        f"Fetching imports for reporter={reporter_code} "
        f"partner={partner_code} period={period} ..."
    )
    response: TradeResponse = client.trade.get_imports(
        reporter_code=reporter_code,
        period=period,
        partner_code=partner_code,
    )
    print(f"  records returned: {len(response.records)}")
    print(f"  elapsed_seconds  : {response.elapsed_seconds}")
    print(f"  upstream_url     : {response.upstream_url}")
    return response


# ---- output ---------------------------------------------------------------


def _record_to_row(record: Any) -> dict[str, Any]:
    """Project a ``TradeRecord`` onto the CSV column set.

    The trade service returns canonical
    ``TradeRecord`` objects. The function reaches
    into the structured fields to populate the
    CSV row; ``Decimal`` monetary values are
    serialised as strings with two decimal places
    to preserve cent precision per ADR-0027.
    """
    primary = record.trade_value.primary_value
    try:
        primary_str = f"{float(primary):.2f}" if primary is not None else ""
    except (TypeError, ValueError):
        primary_str = ""

    return {
        "refPeriodId": record.period,
        "reporterCode": str(record.reporter.reporter_code),
        "partnerCode": str(record.partner.partner_code),
        "partnerISO": record.partner.iso3 or "",
        "cmdCode": record.commodity.commodity_code,
        "flowCode": record.flow.flow_code,
        "primaryValue": primary_str,
    }


def write_csv(
    records: Iterable[Any],
    output_dir: Path,
    *,
    recipe_id: str,
    partner_code: int,
    period: str,
    sdk_version: str,
) -> tuple[Path, Path]:
    """Write ``records`` to CSV and emit a metadata sidecar.

    Returns
    -------
    tuple[Path, Path]
        ``(data_path, sidecar_path)``.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    data_path = output_dir / f"{recipe_id}_{timestamp}.csv"
    sidecar_path = output_dir / f"{recipe_id}_{timestamp}.meta.json"

    rows = [_record_to_row(r) for r in records]
    with data_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    digest = hashlib.sha256(data_path.read_bytes()).hexdigest()
    sidecar = {
        "recipe_id": recipe_id,
        "title": "Fetch annual imports for one partner (T02) to CSV",
        "category": "trade",
        "sdk_version": sdk_version,
        "partner_code": partner_code,
        "period": period,
        "run_started_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(rows),
        "output_digests": {"data": f"sha256:{digest}"},
    }
    sidecar_path.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    return data_path, sidecar_path


# ---- error handling --------------------------------------------------------


def _exit_code_for(exc: ComtradeError) -> int:
    """Map a ``ComtradeError`` to the cookbook exit code table."""
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
        prog="RECIPE-012",
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
    parser.add_argument(
        "--partner",
        type=int,
        default=156,
        help="Partner code (default: 156 = China). Use 0 for the World aggregate.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./output"),
        help="Output directory (default: ./output).",
    )
    args = parser.parse_args(argv)

    print("== Recipe 02: Fetch Annual Imports (one partner) ==")
    print("Auth: OK (key configured)")

    config = Configuration(api_key=key)
    try:
        with ComtradeClient(config) as client:
            response = imports_demo(
                client,
                reporter_code=args.reporter,
                period=args.period,
                partner_code=args.partner,
            )
            print(f"Writing {len(response.records)} records to CSV ...")
            data_path, sidecar_path = write_csv(
                response.records,
                args.output,
                recipe_id="RECIPE_012",
                partner_code=args.partner,
                period=args.period,
                sdk_version=_get_sdk_version(),
            )
            print(f"  output : {data_path}")
            print(f"  sidecar: {sidecar_path}")
    except ComtradeError as exc:
        code = _exit_code_for(exc)
        print(
            f"recipe=RECIPE-012 error_class={type(exc).__name__} "
            f"message={exc} exit_code={code}",
            file=sys.stderr,
        )
        return code

    print("Done.")
    print(
        f"recipe=RECIPE-012 records={len(response.records)} "
        f"data={data_path.name}"
    )
    return 0


def _get_sdk_version() -> str:
    from un_comtrade import __version__

    return __version__


if __name__ == "__main__":
    raise SystemExit(main())
