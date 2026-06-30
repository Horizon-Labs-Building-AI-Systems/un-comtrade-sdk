"""
---
recipe_id: RECIPE-013
title: Fetch world aggregate trade (T05) to JSON
category: trade
difficulty: beginner
sdk_version: >=1.0.2
requires_api_key: yes
estimated_runtime: <10s
inputs:
  required:
    - name: reporter_code
      type: int
      description: UN Comtrade reporter code (e.g. 699 for India)
    - name: flow_code
      type: str
      description: |
        Trade flow code. One of:
        ``"X"`` (exports), ``"M"`` (imports),
        ``"RX"`` (re-exports), ``"RM"`` (re-imports).
    - name: period
      type: str
      description: Annual period (e.g. "2022")
  optional:
    - name: commodity_code
      type: str
      default: TOTAL
      description: |
        HS commodity code. ``"TOTAL"`` selects
        every commodity (the world aggregate for
        the reporter). Use a 2/4/6-digit HS code
        to scope the world aggregate to a single
        chapter / heading / subheading.
    - name: output
      type: str
      default: ./output
      description: Directory the JSON file is written into.
outputs:
  - kind: file
    path: output/RECIPE_013_<UTC-timestamp>.json
    description: |
      JSON file with the upstream envelope preserved
      (``count``, ``elapsed_seconds``, ``error``,
      ``data``). The recipe emits a structured object
      with two top-level keys: ``envelope`` (the raw
      SDK response) and ``meta`` (the recipe's own
      provenance).
  - kind: file
    path: output/RECIPE_013_<UTC-timestamp>.meta.json
    description: Metadata sidecar (recipe id, flow, period, row count, SHA-256 digest).
  - kind: stdout
    path: null
    description: Single-line summary of the run.
related_docs:
  - docs/007_SDK_SPECIFICATION.md
  - docs/009_TRADE_LAYER_SPEC.md
related_recipes:
  - RECIPE-011
  - RECIPE-012
  - RECIPE-014
tags:
  - trade
  - world
  - t05
  - json
  - auth
---

Recipe 03 — Fetch the world aggregate for a reporter.

The world aggregate (T05) returns the reporter's
total trade with **all partners** in a single row.
The upstream enforces ``partner_code=0`` (the
``PARTNER_WORLD`` sentinel); the recipe simply
passes ``flow_code`` and ``period`` and the SDK
fills in the world filter.

The recipe writes the canonical envelope (count,
elapsed_seconds, records) to a JSON file alongside
a metadata sidecar. JSON is the natural format
here: the world aggregate is a single row, the
envelope is small, and the consumer usually pipes
the file into a downstream tool without
converting to a tabular format.

Coverage of the four pillars:

- **Authentication** — key validated up front; exit 4
  on missing.
- **Filtering** — ``flow_code`` selects the side
  (X / M / RX / RM) and ``commodity_code`` defaults
  to ``"TOTAL"`` for the headline figure.
- **Output format** — JSON envelope + sidecar.
- **Error handling** — full ``ComtradeError`` map
  in ``main()``.

Expected output (mock-mode)::

    == Recipe 03: Fetch World Aggregate Trade ==
    Auth: OK (key configured)
    Reporter: 699  Flow: X  Period: 2022  Commodity: TOTAL
    Fetching world trade for reporter=699 flow=X period=2022 ...
      records returned: 1
      elapsed_seconds  : 0.18
      upstream_url     : https://comtradeapi.un.org/data/v1/get/C/A/HS?...
    Writing world aggregate to JSON ...
      output : output/RECIPE_013_20260629T103000Z.json
      sidecar: output/RECIPE_013_20260629T103000Z.meta.json
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
from un_comtrade.query import FLOW_CODES


# ---- constants -------------------------------------------------------------

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


def world_trade_demo(
    client: ComtradeClient,
    *,
    reporter_code: int,
    flow_code: str,
    period: str,
    commodity_code: str,
) -> TradeResponse:
    """Fetch the world aggregate for a reporter.

    Parameters
    ----------
    client
        A ``ComtradeClient`` whose ``trade`` service
        is reachable.
    reporter_code
        UN Comtrade reporter code.
    flow_code
        Trade flow code (``"X"`` / ``"M"`` /
        ``"RX"`` / ``"RM"``). The recipe validates
        this against the documented ``FLOW_CODES``
        set; an unknown value exits with code 2
        (invalid arguments) before any I/O.
    period
        Annual period string.
    commodity_code
        HS commodity code, or ``"TOTAL"`` for the
        all-commodities world aggregate.

    Returns
    -------
    TradeResponse
        The canonical envelope. The world aggregate
        is normally a single row, but a chapter-level
        ``commodity_code`` may return a few rows
        when the upstream chooses to split by some
        other dimension.
    """
    if flow_code not in FLOW_CODES:
        raise ValueError(
            f"flow_code must be one of {sorted(FLOW_CODES)}; "
            f"got {flow_code!r}"
        )
    print(
        f"Reporter: {reporter_code}  "
        f"Flow: {flow_code}  Period: {period}  "
        f"Commodity: {commodity_code}"
    )
    print(
        f"Fetching world trade for reporter={reporter_code} "
        f"flow={flow_code} period={period} commodity={commodity_code} ..."
    )
    response: TradeResponse = client.trade.get_world_trade(
        reporter_code=reporter_code,
        flow_code=flow_code,
        period=period,
        commodity_code=commodity_code,
    )
    print(f"  records returned: {len(response.records)}")
    print(f"  elapsed_seconds  : {response.elapsed_seconds}")
    print(f"  upstream_url     : {response.upstream_url}")
    return response


# ---- output ---------------------------------------------------------------


def write_json(
    response: TradeResponse,
    output_dir: Path,
    *,
    recipe_id: str,
    flow_code: str,
    period: str,
    sdk_version: str,
) -> tuple[Path, Path]:
    """Write the envelope to JSON and emit a metadata sidecar.

    The data file embeds both the SDK's envelope
    (``envelope``) and the recipe's own provenance
    (``meta``). A consumer that wants only the
    upstream payload can read ``payload['envelope']``
    ; a consumer that wants the recipe's
    provenance can read ``payload['meta']``.

    Returns
    -------
    tuple[Path, Path]
        ``(data_path, sidecar_path)``.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    data_path = output_dir / f"{recipe_id}_{timestamp}.json"
    sidecar_path = output_dir / f"{recipe_id}_{timestamp}.meta.json"

    payload = {
        "envelope": {
            "count": response.count,
            "elapsed_seconds": response.elapsed_seconds,
            "error": response.error,
            "upstream_url": response.upstream_url,
            "skipped": response.skipped,
            # ``TradeRecord`` exposes a ``to_dict()`` method
            # via ``BaseModel``. We round-trip through it
            # to get a JSON-friendly nested dict;
            # ``Decimal`` values survive as strings.
            "records": [r.to_dict() for r in response.records],
        },
        "meta": {
            "recipe_id": recipe_id,
            "flow_code": flow_code,
            "period": period,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "sdk_version": sdk_version,
        },
    }
    data_path.write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )

    digest = hashlib.sha256(data_path.read_bytes()).hexdigest()
    sidecar = {
        "recipe_id": recipe_id,
        "title": "Fetch world aggregate trade (T05) to JSON",
        "category": "trade",
        "sdk_version": sdk_version,
        "flow_code": flow_code,
        "period": period,
        "run_started_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(response.records),
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
        prog="RECIPE-013",
        description=__doc__,
    )
    parser.add_argument(
        "--reporter",
        type=int,
        default=699,
        help="UN Comtrade reporter code (default: 699 = India).",
    )
    parser.add_argument(
        "--flow",
        choices=sorted(FLOW_CODES),
        default="X",
        help="Trade flow (default: X = exports).",
    )
    parser.add_argument(
        "--period",
        default="2022",
        help='Annual period, e.g. "2022" (default: 2022).',
    )
    parser.add_argument(
        "--commodity",
        default="TOTAL",
        help='HS commodity code, or "TOTAL" (default: TOTAL).',
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./output"),
        help="Output directory (default: ./output).",
    )
    args = parser.parse_args(argv)

    print("== Recipe 03: Fetch World Aggregate Trade ==")
    print("Auth: OK (key configured)")

    config = Configuration(api_key=key)
    try:
        with ComtradeClient(config) as client:
            response = world_trade_demo(
                client,
                reporter_code=args.reporter,
                flow_code=args.flow,
                period=args.period,
                commodity_code=args.commodity,
            )
            print("Writing world aggregate to JSON ...")
            data_path, sidecar_path = write_json(
                response,
                args.output,
                recipe_id="RECIPE_013",
                flow_code=args.flow,
                period=args.period,
                sdk_version=_get_sdk_version(),
            )
            print(f"  output : {data_path}")
            print(f"  sidecar: {sidecar_path}")
    except ComtradeError as exc:
        code = _exit_code_for(exc)
        print(
            f"recipe=RECIPE-013 error_class={type(exc).__name__} "
            f"message={exc} exit_code={code}",
            file=sys.stderr,
        )
        return code

    print("Done.")
    print(
        f"recipe=RECIPE-013 records={len(response.records)} "
        f"data={data_path.name}"
    )
    return 0


def _get_sdk_version() -> str:
    from un_comtrade import __version__

    return __version__


if __name__ == "__main__":
    raise SystemExit(main())
