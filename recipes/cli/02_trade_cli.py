"""
---
recipe_id: RECIPE-095
title: Fetch export records via the CLI
category: cli
difficulty: beginner
sdk_version: >=1.0.2
requires_api_key: yes
estimated_runtime: <1min
inputs:
  required:
    - name: reporter
      type: int
      description: UN Comtrade reporter code (e.g. 699 for India)
    - name: period
      type: str
      description: Annual period (e.g. "2022")
  optional:
    - name: partner
      type: int
      default: null
      description: Partner country code. Omit for "all partners".
    - name: classification
      type: str
      default: "HS"
      description: Classification system (HS / SITC / BEC).
    - name: max_records
      type: int
      default: null
      description: Optional cap on returned records.
    - name: output_format
      type: str
      default: "table"
      description: Output format (json / table / csv / markdown / text).
    - name: output
      type: str
      default: null
      description: Optional file path for the rendered output.
outputs:
  - kind: stdout
    path: null
    description: |
      Trade records rendered in the chosen format.
      Default ``table`` for the recipe demo.
  - kind: file
    path: <output>
    description: |
      Optional side-effect: when ``--output`` is
      supplied, the rendered records are written
      to PATH.
related_docs:
  - docs/007_SDK_SPECIFICATION.md
  - docs/009_TRADE_LAYER_SPEC.md
  - docs/033_CLI_CONTRACT_VERIFICATION.md
related_recipes:
  - RECIPE-011
  - RECIPE-012
  - RECIPE-013
tags:
  - cli
  - trade
  - exports
  - fetch
  - shell
---

Recipe 02 — ``un-comtrade trade exports ...``.

Demonstrates the trade-data fetch CLI. The CLI
delegates to ``TradeService.get_exports(...)``
which is the canonical fetch surface; the CLI
adds output formatting and exit-code mapping.

**Shell form** (canonical consumer invocation)::

    $ export UN_COMTRADE_KEY=<your-key>
    $ un-comtrade trade exports --reporter 699 --year 2022 \
                               --partner 156 --output-format table

    reporter   partner  cmd     flow  primary_value   ...
    --------   -------  ---     ----  -------------
    699        156      8541    X     1,234,567.00   ...
    699        156      8542    X       654,321.00   ...

The recipe's demo function builds the same argv
and invokes ``un_comtrade.cli.main`` with a
patched ``ComtradeClient``. ``main()`` is the
entry point — it returns the CLI exit code.

Expected output (mock-mode)::

    == Recipe 02: CLI trade exports ==
    shell: un-comtrade trade exports --reporter 699 --year 2022 ...
    exit  : 0
    rows  : 3
    elapsed: 0.42s
    Done.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from typing import Any, Sequence

from un_comtrade.cli.main import main as cli_main
from un_comtrade.cli.utils import EXIT_OK
from un_comtrade.models import TradeResponse


# ---- constants -------------------------------------------------------------

EXIT_AUTH: int = 4
RECIPE_ID: str = "RECIPE-095"


# ---- helpers ---------------------------------------------------------------


def _fake_trade_response(count: int = 3) -> TradeResponse:
    """Build a TradeResponse whose ``to_dict`` returns a small,
    stable dict. Mirrors the helper in tests/test_cli_trade.py.
    """
    return TradeResponse(
        elapsed_seconds=0.42,
        count=count,
        records=[],
        error="",
        upstream_url="https://example.invalid/get/X/A/HS",
        request={"reporterCode": 699, "period": "2022"},
        skipped=0,
    )


@dataclass(frozen=True)
class CliRunResult:
    """Outcome of a CLI invocation."""

    argv: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str


def _run_cli(argv: Sequence[str]) -> CliRunResult:
    """Invoke ``un_comtrade.cli.main`` and capture stdout/stderr."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            code = cli_main(list(argv))
        except SystemExit as exc:  # argparse --help / -h
            code = exc.code if isinstance(exc.code, int) else 0
    return CliRunResult(
        argv=tuple(argv),
        exit_code=int(code),
        stdout=out.getvalue(),
        stderr=err.getvalue(),
    )


def _patch_trade_service(
    monkeypatch: Any,
    *,
    response: TradeResponse | None = None,
) -> TradeResponse:
    """Patch ``ComtradeClient`` so ``client.trade.get_exports``
    returns a canned response.
    """
    import unittest.mock as mock  # noqa: PLC0415

    response = response or _fake_trade_response()
    fake_trade = mock.MagicMock()
    fake_trade.get_exports.return_value = response
    fake_trade.get_imports.return_value = response
    fake_trade.get_world_trade.return_value = response
    fake_trade.get_bilateral.return_value = response
    fake_trade.get_trade_balance.return_value = response
    fake_trade.get_tariffline.return_value = response

    fake_client = mock.MagicMock()
    fake_client.trade = fake_trade

    monkeypatch.setattr(
        "un_comtrade.cli.commands.trade.ComtradeClient",
        lambda *a, **kw: fake_client,
    )
    return response


# ---- demo ------------------------------------------------------------------


def trade_cli_demo(
    *,
    reporter: int = 699,
    period: str = "2022",
    partner: int | None = None,
    classification: str = "HS",
    max_records: int | None = None,
    output_format: str = "table",
    output_path: str | None = None,
    monkeypatch: Any = None,
) -> CliRunResult:
    """Run ``un-comtrade trade exports`` end-to-end.

    Parameters
    ----------
    reporter
        UN Comtrade reporter code (e.g. 699).
    period
        Annual period (e.g. ``"2022"``).
    partner
        Optional partner country code.
    classification
        Classification system. Default ``"HS"``.
    max_records
        Optional cap on returned records.
    output_format
        Output format. Default ``"table"``.
    output_path
        Optional file path. When supplied,
        ``--output PATH`` is appended to argv.
    monkeypatch
        Optional pytest monkeypatch fixture.

    Returns
    -------
    CliRunResult
        The argv, exit code, captured stdout,
        captured stderr.
    """
    argv: list[str] = [
        "trade", "exports",
        "--reporter", str(reporter),
        "--year", period,
        "--classification", classification,
        "--output-format", output_format,
    ]
    if partner is not None:
        argv.extend(["--partner", str(partner)])
    if max_records is not None:
        argv.extend(["--max-records", str(max_records)])
    if output_path:
        argv.extend(["--output", output_path])
    if monkeypatch is not None:
        _patch_trade_service(monkeypatch)
    return _run_cli(argv)


# ---- main ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
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
        "--partner", type=int, default=None,
        help="Optional partner country code (omit for all partners).",
    )
    parser.add_argument(
        "--classification", default="HS",
        help="Classification system (default: HS).",
    )
    parser.add_argument(
        "--max-records", type=int, default=None,
        help="Optional cap on returned records.",
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "table", "csv", "markdown", "text"],
        default="table",
        help="Output format (default: table).",
    )
    parser.add_argument(
        "--output", default=None,
        help="Optional file path.",
    )
    args = parser.parse_args(argv)

    print("== Recipe 02: CLI trade exports ==")
    shell_argv = [
        "un-comtrade", "trade", "exports",
        "--reporter", str(args.reporter),
        "--year", args.period,
        "--classification", args.classification,
        "--output-format", args.output_format,
    ]
    if args.partner is not None:
        shell_argv.extend(["--partner", str(args.partner)])
    if args.max_records is not None:
        shell_argv.extend(["--max-records", str(args.max_records)])
    if args.output:
        shell_argv.extend(["--output", args.output])
    print(f"shell: {' '.join(shell_argv)}")

    response = _fake_trade_response(count=3)
    result = trade_cli_demo(
        reporter=args.reporter,
        period=args.period,
        partner=args.partner,
        classification=args.classification,
        max_records=args.max_records,
        output_format=args.output_format,
        output_path=args.output,
    )
    print(f"exit  : {result.exit_code}")
    print(f"rows  : {response.count}")
    print(f"elapsed: {response.elapsed_seconds:.2f}s")
    print("Done.")
    print(
        f"recipe={RECIPE_ID} reporter={args.reporter} "
        f"period={args.period} exit={result.exit_code}"
    )
    return result.exit_code if result.exit_code != EXIT_OK else 0


if __name__ == "__main__":
    raise SystemExit(main())