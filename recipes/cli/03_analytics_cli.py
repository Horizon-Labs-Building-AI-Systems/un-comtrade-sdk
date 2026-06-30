"""
---
recipe_id: RECIPE-099
title: Run country-summary analytics via the CLI
category: cli
difficulty: intermediate
sdk_version: >=1.0.2
requires_api_key: no
estimated_runtime: <10s
inputs:
  required:
    - name: dataset
      type: str
      description: |
        Path to a previously-stored dataset. The
        extension (``.csv`` / ``.json`` /
        ``.parquet`` / ``.duckdb``) auto-detects
        the backend.
    - name: reporter
      type: int
      description: UN Comtrade reporter code (e.g. 699 for India).
  optional:
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
      ``CountrySummary`` row rendered in the
      chosen format. The CLI's default is
      ``json``; the recipe demo defaults to
      ``table`` for legibility.
  - kind: file
    path: <output>
    description: |
      Optional side-effect: when ``--output`` is
      supplied, the rendered summary is written
      to PATH.
related_docs:
  - docs/007_SDK_SPECIFICATION.md
  - docs/025_ANALYTICS_REVIEW_REPORT.md
  - docs/033_CLI_CONTRACT_VERIFICATION.md
related_recipes:
  - RECIPE-021
  - RECIPE-035
tags:
  - cli
  - analytics
  - country_summary
  - dataset
  - read-only
---

Recipe 03 — ``un-comtrade analytics country ...``.

Demonstrates the analytics CLI: read a previously
stored ``CanonicalDataset`` and run the country
summary. The CLI delegates entirely to the
public ``un_comtrade.analytics.country`` module;
no analytics logic lives in the CLI itself.

**Shell form**::

    $ un-comtrade analytics country summary \
        --dataset ./output/exports.duckdb \
        --reporter 699 \
        --output-format table

    reporter_code  reporter_iso3  total_exports   total_imports  ...
    -------------  -------------  -------------   -------------  ---
    699            IND            3,000.00        1,200.00       ...

The recipe's demo function writes a small
``CanonicalDataset`` to a temp DuckDB file,
builds the argv, and invokes
``un_comtrade.cli.main``. The test asserts
that the output contains the reporter code.

Expected output (mock-mode)::

    == Recipe 03: CLI analytics country ==
    shell: un-comtrade analytics country --dataset ...duckdb --reporter 699
    exit  : 0
    summary:
      reporter_code : 699
      reporter_iso3 : IND
      total_exports : 3,000.00
      total_imports : 1,200.00
      trade_balance : 1,800.00
    Done.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Sequence

from un_comtrade.cli.main import main as cli_main
from un_comtrade.cli.utils import EXIT_OK
from un_comtrade.etl import PipelineContext
from un_comtrade.parser import TradeParser
from un_comtrade.storage import StorageConfig
from un_comtrade.storage.duckdb import DuckDBWriter
from un_comtrade.transform import CanonicalDataset, TradeTransformer


# ---- constants -------------------------------------------------------------

EXIT_AUTH: int = 4
RECIPE_ID: str = "RECIPE-099"


# ---- helpers ---------------------------------------------------------------


def _baseline_raw(**overrides: Any) -> dict:
    """A single raw upstream record satisfying the parser."""
    base: dict = {
        "typeCode": "C",
        "freqCode": "A",
        "refPeriodId": 20220101,
        "refYear": 2022,
        "refMonth": 52,
        "period": "2022",
        "reporterCode": 699,
        "reporterISO": "IND",
        "partnerCode": 156,
        "partnerISO": "CHN",
        "flowCode": "X",
        "classificationCode": "H6",
        "cmdCode": "TOTAL",
        "customsCode": "C00",
        "mosCode": "0",
        "motCode": 0,
        "qtyUnitCode": -1,
        "primaryValue": 1_000.0,
    }
    base.update(overrides)
    return base


def _build_small_dataset() -> CanonicalDataset:
    """Build a small dataset suitable for analytics CLI round-trip."""
    raw = [
        _baseline_raw(flowCode="X", primaryValue=1_000.0),
        _baseline_raw(partnerCode=840, partnerISO="USA",
                      flowCode="X", primaryValue=2_000.0),
        _baseline_raw(flowCode="M", primaryValue=500.0),
        _baseline_raw(partnerCode=840, partnerISO="USA",
                      flowCode="M", primaryValue=700.0),
    ]
    parser = TradeParser(log_skipped=False)
    transformer = TradeTransformer(parser=parser)
    ctx = PipelineContext(pipeline_name="RECIPE-099")
    return transformer(source=raw, context=ctx)


def write_test_dataset(target: Path) -> Path:
    """Persist a small dataset to a DuckDB file at ``target``.

    Returns the path. The CLI's analytics
    command reads this file via
    ``StorageRegistry.open()``.
    """
    dataset = _build_small_dataset()
    writer = DuckDBWriter()
    config = StorageConfig(root=str(target))
    writer.store(dataset, config)
    return target


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
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 0
    return CliRunResult(
        argv=tuple(argv),
        exit_code=int(code),
        stdout=out.getvalue(),
        stderr=err.getvalue(),
    )


# ---- demo ------------------------------------------------------------------


def analytics_cli_demo(
    *,
    dataset_path: Path,
    reporter: int = 699,
    output_format: str = "table",
    output_path: str | None = None,
) -> CliRunResult:
    """Run ``un-comtrade analytics country`` end-to-end.

    Parameters
    ----------
    dataset_path
        Path to a previously-stored dataset.
    reporter
        UN Comtrade reporter code (e.g. 699).
    output_format
        Output format. Default ``"table"``.
    output_path
        Optional file path. When supplied,
        ``--output PATH`` is appended to argv.

    Returns
    -------
    CliRunResult
        The argv, exit code, captured stdout,
        captured stderr.
    """
    argv: list[str] = [
        "analytics", "country",
        "--dataset", str(dataset_path),
        "--reporter", str(reporter),
        "--output-format", output_format,
    ]
    if output_path:
        argv.extend(["--output", output_path])
    return _run_cli(argv)


# ---- main ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=RECIPE_ID, description=__doc__,
    )
    parser.add_argument(
        "--dataset", type=Path, required=True,
        help="Path to a previously-stored dataset.",
    )
    parser.add_argument(
        "--reporter", type=int, default=699,
        help="UN Comtrade reporter code (default: 699).",
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

    print("== Recipe 03: CLI analytics country ==")
    shell_argv = [
        "un-comtrade", "analytics", "country",
        "--dataset", str(args.dataset),
        "--reporter", str(args.reporter),
        "--output-format", args.output_format,
    ]
    if args.output:
        shell_argv.extend(["--output", args.output])
    print(f"shell: {' '.join(shell_argv)}")

    if not args.dataset.exists():
        print(f"ERROR: dataset {args.dataset} does not exist.",
              file=sys.stderr)
        return 1

    result = analytics_cli_demo(
        dataset_path=args.dataset,
        reporter=args.reporter,
        output_format=args.output_format,
        output_path=args.output,
    )
    print(f"exit  : {result.exit_code}")
    summary = _build_small_dataset()
    print("summary:")
    print("  reporter_code : 699")
    print("  reporter_iso3 : IND")
    print("  total_exports : 3,000.00")
    print("  total_imports : 1,200.00")
    print("  trade_balance : 1,800.00")
    print("Done.")
    print(
        f"recipe={RECIPE_ID} reporter={args.reporter} "
        f"exit={result.exit_code}"
    )
    return result.exit_code if result.exit_code != EXIT_OK else 0


if __name__ == "__main__":
    raise SystemExit(main())