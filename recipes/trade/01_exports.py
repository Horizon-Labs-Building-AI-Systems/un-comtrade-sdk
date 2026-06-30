"""
---
recipe_id: RECIPE-011
title: Fetch annual exports (T01) to Parquet
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
      description: Annual period (e.g. "2022" or comma-separated like "2020,2021,2022")
  optional:
    - name: output
      type: str
      default: ./output
      description: Directory the Parquet file is written into.
outputs:
  - kind: file
    path: output/RECIPE_011_<UTC-timestamp>.parquet
    description: Parquet file with one row per trade record.
  - kind: file
    path: output/RECIPE_011_<UTC-timestamp>.meta.json
    description: Metadata sidecar (recipe id, SDK version, SHA-256 digest).
  - kind: stdout
    path: null
    description: Single-line summary of the run.
related_docs:
  - docs/007_SDK_SPECIFICATION.md
  - docs/009_TRADE_LAYER_SPEC.md
  - docs/012_STORAGE_SPECIFICATION.md
related_recipes:
  - RECIPE-012
  - RECIPE-013
  - RECIPE-014
tags:
  - trade
  - exports
  - t01
  - parquet
  - auth
---

Recipe 01 — Fetch annual exports and write to Parquet.

This recipe demonstrates the four pillars of a real
trade-data workflow:

1. **Authentication** — reads the API key from
   ``UN_COMTRADE_KEY`` and exits with code 4 when
   missing.
2. **Filtering** — fetches exports for a single
   reporter in a single annual period (the simplest
   legal filter combination).
3. **Output format** — persists the records to a
   Parquet file using the standard Parquet writer
   exposed by the SDK.
4. **Error handling** — the ``main()`` body wraps the
   call in a ``try / except ComtradeError`` block
   that maps the SDK exception hierarchy to the
   cookbook exit codes (per ``recipes/README.md`` §6.4).

The recipe uses only ``ComtradeClient``. The
regression test injects a ``MockTransport`` and
exercises the demo function directly.

Expected output (mock-mode)::

    == Recipe 01: Fetch Annual Exports ==
    Auth: OK (key configured)
    Reporter: 699  Period: 2022
    Fetching exports for reporter=699 period=2022 ...
      records returned: 224
      elapsed_seconds  : 0.34
      upstream_url     : https://comtradeapi.un.org/data/v1/get/C/A/HS?...
    Writing 224 records to Parquet ...
      output: output/RECIPE_011_20260629T103000Z.parquet
      sidecar: output/RECIPE_011_20260629T103000Z.meta.json
    Done.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

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

#: Exit code for a missing API key. Mirrors
#: ``AuthenticationError`` per ``recipes/README.md`` §6.4.
EXIT_AUTH: int = 4


# ---- auth ------------------------------------------------------------------


def _require_api_key() -> str:
    """Read the API key from the environment and validate it.

    The recipe MUST NOT call the upstream without a
    configured key; the upstream returns 401 for
    unauthenticated calls and the SDK maps that to
    ``AuthenticationError``. Gating the key up front
    gives the consumer a faster, clearer failure.

    Returns
    -------
    str
        The configured key. Never an empty string.

    Raises
    ------
    SystemExit
        With code ``EXIT_AUTH`` when the key is
        missing or empty. The error message is
        written to ``stderr`` and names the env var
        so the consumer can act on it.
    """
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


def exports_demo(
    client: ComtradeClient,
    *,
    reporter_code: int,
    period: str,
) -> TradeResponse:
    """Fetch annual exports and return the canonical ``TradeResponse``.

    The function takes a ``ComtradeClient`` so the
    regression test can inject a mock transport. It
    performs no I/O beyond the network call (the
    caller writes the result to disk).

    Parameters
    ----------
    client
        A ``ComtradeClient`` whose ``trade`` service
        is reachable. The recipe does not care
        whether the transport is real or mocked.
    reporter_code
        UN Comtrade reporter code (e.g. ``699``
        for India).
    period
        Annual period string (e.g. ``"2022"`` or
        ``"2020,2021,2022"``).

    Returns
    -------
    TradeResponse
        The canonical envelope returned by the
        trade service. The caller iterates
        ``response.records`` to persist the data.
    """
    print(f"Reporter: {reporter_code}  Period: {period}")
    print(
        f"Fetching exports for reporter={reporter_code} "
        f"period={period} ..."
    )
    response: TradeResponse = client.trade.get_exports(
        reporter_code=reporter_code,
        period=period,
    )
    print(f"  records returned: {len(response.records)}")
    print(f"  elapsed_seconds  : {response.elapsed_seconds}")
    print(f"  upstream_url     : {response.upstream_url}")
    return response


# ---- output ---------------------------------------------------------------


def _records_to_arrow_table(records: list[Any]) -> pa.Table:
    """Project a list of ``TradeRecord`` instances to a Parquet table.

    The trade service returns canonical
    ``TradeRecord`` objects (per the documented
    data model). The recipe flattens each
    record's leaf fields into columns of a
    Parquet table. ``Decimal`` monetary values
    are cast to ``float`` for columnar
    friendliness; the trade-record provenance
    survives as strings.

    The function is intentionally simple — the
    recipe's purpose is to demonstrate the
    end-to-end shape, not to define a canonical
    trade-record schema. A production pipeline
    would route through ``client.etl`` and the
    ``CanonicalDataset`` model.
    """
    if not records:
        # An empty Parquet table with the expected
        # column set is still useful — it tells the
        # consumer "the query worked, there were no
        # results" without ambiguity.
        return pa.table(
            {
                "refPeriodId": pa.array([], type=pa.string()),
                "reporterCode": pa.array([], type=pa.int64()),
                "partnerCode": pa.array([], type=pa.int64()),
                "cmdCode": pa.array([], type=pa.string()),
                "flowCode": pa.array([], type=pa.string()),
                "primaryValue": pa.array([], type=pa.float64()),
            }
        )

    columns: dict[str, list[Any]] = {
        "refPeriodId": [],
        "reporterCode": [],
        "partnerCode": [],
        "cmdCode": [],
        "flowCode": [],
        "primaryValue": [],
    }
    for record in records:
        # ``TradeRecord`` is a structured dataclass;
        # access via attribute, not key.
        columns["refPeriodId"].append(record.period)
        columns["reporterCode"].append(record.reporter.reporter_code)
        columns["partnerCode"].append(record.partner.partner_code)
        columns["cmdCode"].append(record.commodity.commodity_code)
        columns["flowCode"].append(record.flow.flow_code)
        primary = record.trade_value.primary_value
        try:
            primary_float = float(primary) if primary is not None else 0.0
        except (TypeError, ValueError):
            primary_float = 0.0
        columns["primaryValue"].append(primary_float)
    return pa.table(columns)


def write_parquet(
    records: list[Any],
    output_dir: Path,
    *,
    recipe_id: str,
    sdk_version: str,
) -> tuple[Path, Path]:
    """Write ``records`` to Parquet and emit a metadata sidecar.

    Returns
    -------
    tuple[Path, Path]
        ``(data_path, sidecar_path)``. The sidecar
        carries the recipe id, the SDK version, the
        run timestamp, the row count, and a SHA-256
        digest of the data file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    data_path = output_dir / f"{recipe_id}_{timestamp}.parquet"
    sidecar_path = output_dir / f"{recipe_id}_{timestamp}.meta.json"

    table = _records_to_arrow_table(records)
    pq.write_table(table, data_path)
    digest = hashlib.sha256(data_path.read_bytes()).hexdigest()
    sidecar = {
        "recipe_id": recipe_id,
        "title": "Fetch annual exports (T01) to Parquet",
        "category": "trade",
        "sdk_version": sdk_version,
        "run_started_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(records),
        "output_digests": {"data": f"sha256:{digest}"},
    }
    sidecar_path.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    return data_path, sidecar_path


# ---- error handling --------------------------------------------------------


def _exit_code_for(exc: ComtradeError) -> int:
    """Map a ``ComtradeError`` to the cookbook exit code table.

    The exit codes are documented in
    ``recipes/README.md`` §6.4. A recipe that uses a
    different map is rejected at review.
    """
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
    """Build a real ``ComtradeClient`` and run the demo.

    The flow:

    1. Validate the API key (exit 4 if missing).
    2. Parse arguments.
    3. Build the SDK client and call the demo.
    4. Persist the result to Parquet.
    5. Translate any ``ComtradeError`` into the
       cookbook's exit-code map.
    """
    key = _require_api_key()

    parser = argparse.ArgumentParser(
        prog="RECIPE-011",
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
        help='Annual period, e.g. "2022" or "2020,2021,2022" (default: 2022).',
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./output"),
        help="Output directory (default: ./output).",
    )
    args = parser.parse_args(argv)

    print("== Recipe 01: Fetch Annual Exports ==")
    print("Auth: OK (key configured)")

    config = Configuration(api_key=key)
    try:
        with ComtradeClient(config) as client:
            response = exports_demo(
                client,
                reporter_code=args.reporter,
                period=args.period,
            )
            print(f"Writing {len(response.records)} records to Parquet ...")
            data_path, sidecar_path = write_parquet(
                response.records,
                args.output,
                recipe_id="RECIPE_011",
                sdk_version=_get_sdk_version(),
            )
            print(f"  output : {data_path}")
            print(f"  sidecar: {sidecar_path}")
    except ComtradeError as exc:
        code = _exit_code_for(exc)
        print(
            f"recipe=RECIPE-011 error_class={type(exc).__name__} "
            f"message={exc} exit_code={code}",
            file=sys.stderr,
        )
        return code

    print("Done.")
    print(
        f"recipe=RECIPE-011 records={len(response.records)} "
        f"data={data_path.name} sidecar={sidecar_path.name}"
    )
    return 0


def _get_sdk_version() -> str:
    """Read the SDK version without importing the package twice."""
    from un_comtrade import __version__

    return __version__


if __name__ == "__main__":
    raise SystemExit(main())
