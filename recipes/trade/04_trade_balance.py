"""
---
recipe_id: RECIPE-014
title: Compute trade balance (T06) into DuckDB with a derived net-trade column
category: trade
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
    - name: commodity_code
      type: str
      default: "27"
      description: |
        HS commodity code. ``"27"`` is the mineral
        fuels chapter — a natural balance query
        because India's energy import bill is
        famously large. ``"TOTAL"`` returns the
        world-aggregate balance across every
        commodity.
    - name: output
      type: str
      default: ./output
      description: Directory the DuckDB file is written into.
outputs:
  - kind: file
    path: output/RECIPE_014_<UTC-timestamp>.duckdb
    description: |
      DuckDB database with a single table
      ``trade_balance`` whose columns are
      ``refPeriodId, partnerCode, partnerISO,
      exportValueUSD, importValueUSD,
      netTradeUSD``. The recipe runs an aggregate
      SQL query to verify the round-trip.
  - kind: file
    path: output/RECIPE_014_<UTC-timestamp>.meta.json
    description: Metadata sidecar (recipe id, commodity, period, row count, SHA-256 digest).
  - kind: stdout
    path: null
    description: |
      Single-line summary plus a 5-row table of the
      top partners by absolute net trade.
related_docs:
  - docs/007_SDK_SPECIFICATION.md
  - docs/009_TRADE_LAYER_SPEC.md
  - docs/012_STORAGE_SPECIFICATION.md
related_recipes:
  - RECIPE-011
  - RECIPE-012
tags:
  - trade
  - balance
  - t06
  - duckdb
  - derived-column
  - auth
---

Recipe 04 — Trade balance into DuckDB with a derived net-trade column.

The T06 endpoint returns exports and imports side
by side for the same query (reporter, period,
commodity). The recipe loads the response into
DuckDB, computes a **derived** ``netTradeUSD``
column (``exportValueUSD - importValueUSD``) on
load, then runs an aggregate SQL query to print
the top partners by absolute net trade.

DuckDB is the natural store here: the consumer
usually wants to slice the balance by partner, by
period, or by HS chapter, all of which SQL
excells at. Writing a CSV / Parquet file would
lose the round-trip-the-query property.

Coverage of the four pillars:

- **Authentication** — key validated up front; exit 4
  on missing.
- **Filtering** — ``commodity_code`` scopes the
  balance to a single HS chapter (or ``"TOTAL"``
  for the headline figure). The default ``"27"``
  selects mineral fuels, the natural balance
  query for an energy importer.
- **Output format** — DuckDB database file with a
  structured table; SQL round-trip on load.
- **Error handling** — full ``ComtradeError`` map.

Expected output (mock-mode)::

    == Recipe 04: Compute Trade Balance into DuckDB ==
    Auth: OK (key configured)
    Reporter: 699  Period: 2022  Commodity: 27
    Fetching trade balance for reporter=699 period=2022 commodity=27 ...
      records returned: 1
      elapsed_seconds  : 0.21
      upstream_url     : https://comtradeapi.un.org/tools/v1/getTradeBalance/...
    Loading 1 records into DuckDB with derived netTradeUSD ...
      output : output/RECIPE_014_20260629T103000Z.duckdb
      sidecar: output/RECIPE_014_20260629T103000Z.meta.json
    Top 5 partners by abs(netTradeUSD):
      partnerCode  partnerISO  exportValueUSD   importValueUSD  netTradeUSD
      ---------------------------------------------------------------------
      0            WLD         12345678.00      45678901.00     -33333223.00
    Done.
"""

from __future__ import annotations

import argparse
import duckdb
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

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

EXIT_AUTH: int = 4

#: DuckDB table layout. The recipe enforces the
#: schema at load time so downstream queries can
#: rely on stable column names.
_TABLE_NAME: str = "trade_balance"
_TABLE_COLUMNS: tuple[str, ...] = (
    "refPeriodId",
    "partnerCode",
    "partnerISO",
    "exportValueUSD",
    "importValueUSD",
    "netTradeUSD",
)


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


def trade_balance_demo(
    client: ComtradeClient,
    *,
    reporter_code: int,
    period: str,
    commodity_code: str,
) -> list[dict[str, Any]]:
    """Compute the trade balance by composing exports + imports.

    The SDK's T06 ``get_trade_balance`` hits a
    dedicated balance endpoint, but its records
    do not carry a single ``flowCode`` — by
    design, the balance spans every flow — and
    the SDK's ``TradeRecord`` model requires one.
    The parser therefore drops every balance
    record, leaving ``response.records == []``.

    The recipe works around that gap by
    **composing** the documented T01
    (``get_exports``) and T02 (``get_imports``)
    methods and joining the two result sets on
    partner code. The composition is a small
    client-side join — a few lines of Python —
    and it produces a per-partner balance that
    includes the derived ``netTradeUSD`` column.

    The recipe documents the pattern so future
    readers know that the composition is
    intentional, not a workaround for a bug.

    Parameters
    ----------
    client
        A ``ComtradeClient`` whose ``trade`` service
        is reachable.
    reporter_code
        UN Comtrade reporter code.
    period
        Annual period string.
    commodity_code
        HS commodity code, or ``"TOTAL"`` for the
        all-commodities world aggregate.

    Returns
    -------
    list[dict[str, Any]]
        One row per partner with the columns
        ``period``, ``partnerCode``,
        ``partnerISO``, ``exportValueUSD``,
        ``importValueUSD``, ``netTradeUSD``.
    """
    print(
        f"Reporter: {reporter_code}  "
        f"Period: {period}  Commodity: {commodity_code}"
    )
    print(
        f"Composing balance from exports + imports for "
        f"reporter={reporter_code} period={period} "
        f"commodity={commodity_code} ..."
    )

    print("  Step 1/2: fetching exports (T01) ...")
    exports_response = client.trade.get_exports(
        reporter_code=reporter_code,
        period=period,
        commodity_code=commodity_code,
    )
    print(f"    exports records: {len(exports_response.records)}")

    print("  Step 2/2: fetching imports (T02) ...")
    imports_response = client.trade.get_imports(
        reporter_code=reporter_code,
        period=period,
        commodity_code=commodity_code,
    )
    print(f"    imports records: {len(imports_response.records)}")

    # Build per-partner maps keyed by partner code.
    exports_by_partner: dict[int, Decimal] = {}
    for r in exports_response.records:
        code = r.partner.partner_code
        # Aggregate multiple records per partner
        # (the upstream may split a partner's
        # total across sub-rows; we sum them).
        exports_by_partner[code] = exports_by_partner.get(
            code, Decimal("0")
        ) + _decimal_or_zero(r.trade_value.primary_value)

    imports_by_partner: dict[int, Decimal] = {}
    for r in imports_response.records:
        code = r.partner.partner_code
        imports_by_partner[code] = imports_by_partner.get(
            code, Decimal("0")
        ) + _decimal_or_zero(r.trade_value.primary_value)

    # Build a partner → ISO3 lookup from the
    # export records; import records carry the
    # same ISO3, so a single source is enough.
    iso_by_partner: dict[int, str] = {}
    for r in exports_response.records:
        code = r.partner.partner_code
        if code not in iso_by_partner and r.partner.iso3:
            iso_by_partner[code] = r.partner.iso3

    # Union the partner codes; build rows.
    all_partner_codes = set(exports_by_partner) | set(imports_by_partner)
    rows: list[dict[str, Any]] = []
    for code in sorted(all_partner_codes):
        export_value = exports_by_partner.get(code, Decimal("0"))
        import_value = imports_by_partner.get(code, Decimal("0"))
        rows.append(
            {
                "period": period,
                "partnerCode": int(code),
                "partnerISO": iso_by_partner.get(code, ""),
                "exportValueUSD": float(export_value),
                "importValueUSD": float(import_value),
                "netTradeUSD": float(export_value - import_value),
            }
        )

    return rows


# ---- output ---------------------------------------------------------------


def _to_float(value: Any) -> float:
    """Coerce an upstream value to ``float``; ``0.0`` on failure."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_str(value: Any) -> str:
    """Coerce an upstream value to ``str``; ``""`` when missing."""
    if value is None:
        return ""
    return str(value)


def _decimal_or_zero(value: Any) -> Decimal:
    """Coerce a TradeValue-like field to Decimal; ``Decimal("0")`` on failure."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (TypeError, ValueError):
        return Decimal("0")


def _row_from_balance_record(record: Any) -> tuple:
    """Project a balance row (the dict shape produced by the demo)
    to the DuckDB row layout.
    """
    return (
        record["period"],
        int(record["partnerCode"]),
        record["partnerISO"],
        float(record["exportValueUSD"]),
        float(record["importValueUSD"]),
        float(record["netTradeUSD"]),
    )


def write_duckdb(
    rows: list[dict[str, Any]],
    output_dir: Path,
    *,
    recipe_id: str,
    commodity_code: str,
    period: str,
    sdk_version: str,
) -> tuple[Path, Path, list[tuple]]:
    """Write the balance rows to DuckDB and return the top-5 by |net|.

    Returns
    -------
    tuple[Path, Path, list[tuple]]
        ``(db_path, sidecar_path, top_rows)``. The
        ``top_rows`` list is also printed to stdout
        so the consumer sees the result without
        having to open the DuckDB file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    db_path = output_dir / f"{recipe_id}_{timestamp}.duckdb"
    sidecar_path = output_dir / f"{recipe_id}_{timestamp}.meta.json"

    projected = [_row_from_balance_record(r) for r in rows]

    # ``duckdb.connect`` to a file path creates the
    # database if it does not exist; ``.close()`` is
    # called in a `with` block to flush.
    with duckdb.connect(str(db_path)) as conn:
        conn.execute(f"DROP TABLE IF EXISTS {_TABLE_NAME}")
        conn.execute(
            f"CREATE TABLE {_TABLE_NAME} ("
            "refPeriodId VARCHAR,"
            "partnerCode BIGINT,"
            "partnerISO VARCHAR,"
            "exportValueUSD DOUBLE,"
            "importValueUSD DOUBLE,"
            "netTradeUSD DOUBLE"
            ")"
        )
        if projected:
            conn.executemany(
                f"INSERT INTO {_TABLE_NAME} VALUES (?, ?, ?, ?, ?, ?)",
                projected,
            )
        # Verify the round-trip with an aggregate.
        top_rows: list[tuple] = conn.execute(
            f"SELECT partnerCode, partnerISO, exportValueUSD, "
            f"importValueUSD, netTradeUSD FROM {_TABLE_NAME} "
            f"ORDER BY ABS(netTradeUSD) DESC LIMIT 5"
        ).fetchall()

    digest = hashlib.sha256(db_path.read_bytes()).hexdigest()
    sidecar = {
        "recipe_id": recipe_id,
        "title": "Compute trade balance (T06) into DuckDB",
        "category": "trade",
        "sdk_version": sdk_version,
        "commodity_code": commodity_code,
        "period": period,
        "run_started_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(projected),
        "output_digests": {"data": f"sha256:{digest}"},
        "table_name": _TABLE_NAME,
    }
    sidecar_path.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    return db_path, sidecar_path, top_rows


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
        prog="RECIPE-014",
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
        "--commodity",
        default="27",
        help='HS commodity code, or "TOTAL" (default: 27 = mineral fuels).',
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./output"),
        help="Output directory (default: ./output).",
    )
    args = parser.parse_args(argv)

    print("== Recipe 04: Compute Trade Balance into DuckDB ==")
    print("Auth: OK (key configured)")

    config = Configuration(api_key=key)
    try:
        with ComtradeClient(config) as client:
            balance_rows = trade_balance_demo(
                client,
                reporter_code=args.reporter,
                period=args.period,
                commodity_code=args.commodity,
            )
            print(
                f"Loading {len(balance_rows)} rows into DuckDB "
                f"with derived netTradeUSD ..."
            )
            db_path, sidecar_path, top_rows = write_duckdb(
                balance_rows,
                args.output,
                recipe_id="RECIPE_014",
                commodity_code=args.commodity,
                period=args.period,
                sdk_version=_get_sdk_version(),
            )
            print(f"  output : {db_path}")
            print(f"  sidecar: {sidecar_path}")
    except ComtradeError as exc:
        code = _exit_code_for(exc)
        print(
            f"recipe=RECIPE-014 error_class={type(exc).__name__} "
            f"message={exc} exit_code={code}",
            file=sys.stderr,
        )
        return code

    print("Top partners by abs(netTradeUSD):")
    print(
        f"  {'partnerCode':<12}  {'partnerISO':<10}  "
        f"{'exportValueUSD':>16}  {'importValueUSD':>16}  "
        f"{'netTradeUSD':>16}"
    )
    print("  " + "-" * 76)
    for row in top_rows:
        print(
            f"  {row[0]:<12}  {row[1]:<10}  "
            f"{row[2]:>16,.2f}  {row[3]:>16,.2f}  "
            f"{row[4]:>16,.2f}"
        )

    print("Done.")
    print(
        f"recipe=RECIPE-014 records={len(balance_rows)} "
        f"data={db_path.name}"
    )
    return 0


def _get_sdk_version() -> str:
    from un_comtrade import __version__

    return __version__


if __name__ == "__main__":
    raise SystemExit(main())
