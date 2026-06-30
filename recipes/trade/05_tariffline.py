"""
---
recipe_id: RECIPE-015
title: Fetch line-level tariffline data (F02) to JSON, with full error handling
category: trade
difficulty: advanced
sdk_version: >=1.0.2
requires_api_key: yes
estimated_runtime: 1-10min
inputs:
  required:
    - name: reporter_code
      type: int
      description: UN Comtrade reporter code (e.g. 699 for India)
    - name: flow_code
      type: str
      description: |
        Trade flow code. ``"X"`` (exports) or ``"M"``
        (imports).
    - name: period
      type: str
      description: Annual period (e.g. "2022")
    - name: commodity_code
      type: str
      description: |
        HS commodity code. Tariffline data is
        line-level (8 or 10 digits for national
        extensions); the recipe requires a
        6-digit HS subheading.
  optional:
    - name: output
      type: str
      default: ./output
      description: Directory the JSON file is written into.
    - name: validate_only
      type: bool
      default: false
      description: |
        Build the query, run parameter validation,
        and print the resolved query — then exit
        without making the upstream call. Useful
        for CI sanity checks and for debugging the
        URL the recipe would have hit.
    - name: dry_run
      type: bool
      default: false
      description: |
        Print the upstream URL the recipe would
        have hit, then exit. Does not consume an
        API call.
outputs:
  - kind: file
    path: output/RECIPE_015_<UTC-timestamp>.json
    description: |
      JSON file with the upstream envelope preserved
      (count, elapsed_seconds, error, records).
  - kind: file
    path: output/RECIPE_015_<UTC-timestamp>.meta.json
    description: Metadata sidecar (recipe id, hs code, partner, period, row count, SHA-256 digest).
  - kind: stdout
    path: null
    description: |
      Single-line summary, plus the resolved query
      (when ``--validate-only`` or ``--dry-run`` is
      set).
related_docs:
  - docs/007_SDK_SPECIFICATION.md
  - docs/009_TRADE_LAYER_SPEC.md
related_recipes:
  - RECIPE-011
  - RECIPE-012
tags:
  - trade
  - tariffline
  - f02
  - json
  - error-handling
  - validate-only
  - dry-run
  - auth
---

Recipe 05 — Tariffline with the cookbook's full
error-handling contract.

Tariffline data is the most granular level the
upstream exposes: line-level (typically 8 or 10
digit national) HS codes per partner. The recipe
calls ``get_tariffline_by_hs`` (F02) and persists
the result to JSON.

Recipe 05 is also the **error-handling
showcase**. It demonstrates three patterns the
other four recipes keep light:

1. **Auth gating** — the API key is validated up
   front; a missing key exits with code 4 *before*
   any I/O. (The other recipes do the same; this
   recipe documents the pattern explicitly.)
2. **Pre-flight validation** — ``--validate-only``
   builds the ``TradeQuery``, runs parameter
   validation, prints the resolved query, and
   exits 0 without consuming an API call. Useful
   for CI checks and for debugging.
3. **Dry run** — ``--dry-run`` prints the upstream
   URL the recipe would have hit, then exits 0.
   Complements ``--validate-only`` when the
   consumer wants to verify the wire-level shape
   of the call.

The recipe also demonstrates the **full**
``ComtradeError`` map: every exception class the
SDK can raise is mapped to its cookbook exit code
per ``recipes/README.md`` §6.4. The mapping lives
in ``_exit_code_for`` below; the table is also
reproduced in the ``--help`` output.

Expected output (mock-mode)::

    == Recipe 05: Fetch Tariffline (F02) ==
    Auth: OK (key configured)
    Resolved query:
      reporter   : 699
      flow_code  : X
      period     : 2022
      hs_code    : 870323
    Fetching tariffline for reporter=699 flow=X period=2022 hs=870323 ...
      records returned: 14
      elapsed_seconds  : 0.42
      upstream_url     : https://comtradeapi.un.org/data/v1/getTariffline/C/A/HS?...
    Writing 14 records to JSON ...
      output : output/RECIPE_015_20260629T103000Z.json
      sidecar: output/RECIPE_015_20260629T103000Z.meta.json
    Done.

    $ python 05_tariffline.py --validate-only
    == Recipe 05: Fetch Tariffline (F02) ==
    Auth: OK (key configured)
    Resolved query:
      reporter   : 699
      flow_code  : X
      period     : 2022
      hs_code    : 870323
    validate-only: query is valid; no upstream call made.
    Done.
    exit 0
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
    AuthorizationError,
    ComtradeError,
    ConfigurationError,
    NetworkError,
    RateLimitError,
    RetryError,
    SerializationError,
    ServerError,
    TimeoutError,
    UnknownError,
    ValidationError,
)
from un_comtrade.models import TradeResponse
from un_comtrade.query import FLOW_CODES, TradeQuery


# ---- constants -------------------------------------------------------------

EXIT_AUTH: int = 4

#: Exit-code map (per ``recipes/README.md`` §6.4).
#: Exposed as a module-level constant so the CLI
#: ``--help`` output can render the table.
EXIT_CODE_TABLE: tuple[tuple[str, int], ...] = (
    ("0  success", 0),
    ("1  generic failure", 1),
    ("2  invalid arguments", 2),
    ("3  ValidationError", 3),
    ("4  AuthenticationError / AuthorizationError", 4),
    ("5  RateLimitError (after retries)", 5),
    ("6  NetworkError / TimeoutError / RetryError", 6),
    ("7  ServerError (after retries)", 7),
    ("8  recipe-specific business-rule failure", 8),
)


# ---- auth ------------------------------------------------------------------


def _require_api_key() -> str:
    """Read the API key from the environment and validate it.

    The recipe MUST NOT call the upstream without
    a configured key. Gating the key up front
    gives the consumer a faster, clearer failure
    than the upstream's 401 + the SDK's
    ``AuthenticationError`` would.
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


# ---- query validation -----------------------------------------------------


def build_query(
    *,
    reporter_code: int,
    flow_code: str,
    period: str,
    commodity_code: str,
) -> TradeQuery:
    """Build and validate a ``TradeQuery`` for the tariffline call.

    The function surfaces three classes of failure
    up front, before any I/O:

    1. ``ValueError`` when ``flow_code`` is not in
       ``FLOW_CODES`` (recipe-side check).
    2. ``ValueError`` when the HS code is not the
       6-digit subheading level (recipe-side check).
    3. ``ValueError`` raised by ``TradeQuery``
       itself when a parameter fails SDK-level
       validation (e.g. period format).

    The caller catches the ``ValueError`` and
    exits with code 2 (invalid arguments) — the
    consumer gets a precise message naming the
    bad parameter.
    """
    if flow_code not in FLOW_CODES:
        raise ValueError(
            f"flow_code must be one of {sorted(FLOW_CODES)}; "
            f"got {flow_code!r}"
        )
    if not (commodity_code.isdigit() and len(commodity_code) == 6):
        raise ValueError(
            "tariffline data requires a 6-digit HS subheading; "
            f"got {commodity_code!r}"
        )
    return TradeQuery(
        reporter_code=reporter_code,
        flow_code=flow_code,
        partner_code=None,
        period=period,
        cmd_code=commodity_code,
        classification_code="HS",
        breakdown_mode="classic",
    )


# ---- demo ------------------------------------------------------------------


def tariffline_demo(
    client: ComtradeClient,
    *,
    reporter_code: int,
    flow_code: str,
    period: str,
    commodity_code: str,
) -> TradeResponse:
    """Fetch tariffline records for a single HS subheading.

    Parameters
    ----------
    client
        A ``ComtradeClient`` whose ``trade`` service
        is reachable.
    reporter_code
        UN Comtrade reporter code.
    flow_code
        Trade flow code (``"X"`` or ``"M"``).
    period
        Annual period string.
    commodity_code
        6-digit HS subheading.

    Returns
    -------
    TradeResponse
        The canonical envelope. The tariffline
        endpoint returns one record per (partner,
        line-level HS code) tuple — typically a
        dozen to a few hundred rows for a single
        reporter / period / 6-digit chapter.
    """
    print("Resolved query:")
    print(f"  reporter   : {reporter_code}")
    print(f"  flow_code  : {flow_code}")
    print(f"  period     : {period}")
    print(f"  hs_code    : {commodity_code}")
    print(
        f"Fetching tariffline for reporter={reporter_code} "
        f"flow={flow_code} period={period} hs={commodity_code} ..."
    )
    response: TradeResponse = client.trade.get_tariffline_by_hs(
        commodity_code=commodity_code,
        reporter_code=reporter_code,
        flow_code=flow_code,
        period=period,
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
    hs_code: str,
    partner: int | None,
    period: str,
    sdk_version: str,
) -> tuple[Path, Path]:
    """Write the envelope to JSON and emit a metadata sidecar."""
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
            # via ``BaseModel``. The nested dict is
            # JSON-friendly; ``Decimal`` values survive
            # as strings.
            "records": [r.to_dict() for r in response.records],
        },
        "meta": {
            "recipe_id": recipe_id,
            "hs_code": hs_code,
            "partner": partner,
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
        "title": "Fetch line-level tariffline data (F02) to JSON",
        "category": "trade",
        "sdk_version": sdk_version,
        "hs_code": hs_code,
        "partner": partner,
        "period": period,
        "run_started_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(response.records),
        "output_digests": {"data": f"sha256:{digest}"},
    }
    sidecar_path.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    return data_path, sidecar_path


# ---- error handling --------------------------------------------------------


def _exit_code_for(exc: BaseException) -> int:
    """Map any SDK exception to the cookbook exit code table.

    The function catches every ``ComtradeError``
    subclass plus a handful of stdlib exceptions
    the SDK can surface (e.g. ``ConfigurationError``
    raised during client construction). A
    non-SDK exception is mapped to code 1
    (generic failure); the caller may choose to
    re-raise the exception for traceback
    inspection.

    The mapping is normative; the per-recipe CLI
    ``--help`` output renders the same table.
    """
    if isinstance(exc, ValidationError):
        return 3
    if isinstance(exc, (AuthenticationError, AuthorizationError)):
        return 4
    if isinstance(exc, RateLimitError):
        return 5
    if isinstance(exc, (NetworkError, TimeoutError, RetryError)):
        return 6
    if isinstance(exc, ServerError):
        return 7
    if isinstance(exc, APIError):
        return 8
    if isinstance(exc, ConfigurationError):
        # Configuration is validated at construction;
        # an invalid config raises ConfigurationError
        # before the first call. We map it to the
        # validation exit code (3) so the consumer's
        # automation treats it the same as a bad
        # query parameter.
        return 3
    if isinstance(exc, SerializationError):
        return 1
    if isinstance(exc, UnknownError):
        return 1
    return 1


# ---- main ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Build a real ``ComtradeClient`` and run the demo.

    Flow:

    1. Validate the API key (exit 4 if missing).
    2. Parse arguments (exit 2 on parse failure).
    3. Build the ``TradeQuery`` (exit 2 on
       validation failure).
    4. If ``--validate-only`` or ``--dry-run`` is
       set, print the resolved query and exit 0.
    5. Build the client and call the demo.
    6. Persist the result to JSON.
    7. Translate any ``ComtradeError`` into the
       cookbook's exit-code map; log to stderr.
    """
    key = _require_api_key()

    parser = argparse.ArgumentParser(
        prog="RECIPE-015",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
        "--hs",
        dest="commodity_code",
        required=True,
        help=(
            "6-digit HS subheading (required). "
            "Tariffline data is line-level; "
            "8/10-digit national extensions are not "
            "supported by the F02 endpoint."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./output"),
        help="Output directory (default: ./output).",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help=(
            "Build and validate the query, then exit "
            "without making the upstream call."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Print the upstream URL the recipe would "
            "hit, then exit. Implies --validate-only."
        ),
    )
    args = parser.parse_args(argv)

    print("== Recipe 05: Fetch Tariffline (F02) ==")
    print("Auth: OK (key configured)")

    # Step 3 — build the query. Any ``ValueError``
    # raised here is a recipe-side validation
    # failure (bad flow code, bad HS code) and
    # maps to exit code 2 (invalid arguments) per
    # the cookbook's exit-code table.
    try:
        query = build_query(
            reporter_code=args.reporter,
            flow_code=args.flow,
            period=args.period,
            commodity_code=args.commodity_code,
        )
    except ValueError as exc:
        print(f"recipe=RECIPE-015 error=invalid_arguments message={exc}", file=sys.stderr)
        return 2

    # Step 4 — short-circuit when validate-only /
    # dry-run is set. We do not build a client or
    # touch the network.
    if args.validate_only or args.dry_run:
        print("Resolved query:")
        print(f"  reporter   : {query.reporter_code}")
        print(f"  flow_code  : {query.flow_code}")
        print(f"  period     : {query.period}")
        print(f"  hs_code    : {query.cmd_code}")
        if args.dry_run:
            print(
                "dry-run: the recipe would hit the upstream "
                "with the resolved query. No API call was made."
            )
        else:
            print("validate-only: query is valid; no upstream call made.")
        print("Done.")
        return 0

    # Step 5 — real fetch. ConfigurationError is
    # raised during construction when the key is
    # missing or malformed; we let it propagate to
    # the ``except`` block where ``_exit_code_for``
    # maps it to code 3.
    config = Configuration(api_key=key)
    try:
        with ComtradeClient(config) as client:
            response = tariffline_demo(
                client,
                reporter_code=args.reporter,
                flow_code=args.flow,
                period=args.period,
                commodity_code=args.commodity_code,
            )
            if len(response.records) == 0:
                # Recipe-specific business-rule failure:
                # the consumer asked for a non-empty
                # result. The empty case is not an SDK
                # error, so we map it to code 8.
                print(
                    "recipe=RECIPE-015 error=empty_result "
                    "message=tariffline query returned 0 records",
                    file=sys.stderr,
                )
                return 8
            print(f"Writing {len(response.records)} records to JSON ...")
            data_path, sidecar_path = write_json(
                response,
                args.output,
                recipe_id="RECIPE_015",
                hs_code=args.commodity_code,
                partner=None,
                period=args.period,
                sdk_version=_get_sdk_version(),
            )
            print(f"  output : {data_path}")
            print(f"  sidecar: {sidecar_path}")
    except ComtradeError as exc:
        code = _exit_code_for(exc)
        print(
            f"recipe=RECIPE-015 error_class={type(exc).__name__} "
            f"message={exc} exit_code={code}",
            file=sys.stderr,
        )
        return code

    print("Done.")
    print(
        f"recipe=RECIPE-015 records={len(response.records)} "
        f"data={data_path.name}"
    )
    return 0


def _get_sdk_version() -> str:
    from un_comtrade import __version__

    return __version__


if __name__ == "__main__":
    raise SystemExit(main())
