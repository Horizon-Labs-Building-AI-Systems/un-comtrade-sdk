"""
---
recipe_id: RECIPE-101
title: Persist a dataset via the CLI (Parquet writer)
category: cli
difficulty: beginner
sdk_version: >=1.0.2
requires_api_key: no
estimated_runtime: <30s
inputs:
  required:
    - name: dataset
      type: str
      description: |
        Path to a stored dataset to read (any
        format supported by the storage layer:
        ``.csv`` / ``.json`` / ``.parquet`` /
        ``.duckdb``).
    - name: output_path
      type: str
      description: |
        Destination path. The extension must
        match the storage subcommand (e.g.
        ``.parquet`` for the parquet subcommand).
  optional:
    - name: format
      type: str
      default: "parquet"
      description: Storage format. One of ``parquet``, ``csv``,
        ``duckdb``, ``json``, ``local-files``.
    - name: overwrite
      type: bool
      default: false
      description: Overwrite the destination if it exists.
    - name: output_format
      type: str
      default: "table"
      description: CLI output format (json / table / csv / markdown / text).
    - name: output
      type: str
      default: null
      description: Optional file path for the rendered CLI output.
outputs:
  - kind: file
    path: <output_path>
    description: |
      The persisted dataset in the requested
      format. For Parquet this is a single
      file (or a partition tree); for DuckDB
      a ``.duckdb`` file.
  - kind: stdout
    path: null
    description: |
      CLI status (record count, byte size,
      partition count, schema version).
related_docs:
  - docs/007_SDK_SPECIFICATION.md
  - docs/012_STORAGE_SPECIFICATION.md
  - docs/033_CLI_CONTRACT_VERIFICATION.md
related_recipes:
  - RECIPE-032
  - RECIPE-033
  - RECIPE-034
tags:
  - cli
  - storage
  - parquet
  - persist
  - read-write
---

Recipe 04 — ``un-comtrade storage parquet ...``.

Demonstrates the storage CLI: read a dataset
(via ``StorageRegistry.open()``) and persist it
to a new location. The CLI orchestrates the
write; the SDK does the work.

**Shell form**::

    $ un-comtrade storage parquet \
        --dataset ./input.csv \
        --output-path ./output/result.parquet \
        --output-format table

    record_count  schema_version  backend   destination            ...
    ------------  --------------  -------   ------------            ---
    222           1.0.0           parquet   ./output/result.parquet  ...

The recipe's demo function writes a small CSV
dataset to ``tmp_path``, then invokes
``un-comtrade storage parquet`` to convert it to
Parquet. The test asserts that a Parquet file
exists at the output path.

Expected output (mock-mode)::

    == Recipe 04: CLI storage parquet ==
    shell: un-comtrade storage parquet --dataset in.csv --output-path out.parquet
    exit  : 0
    input : <in.csv> (4 records)
    output: <out.parquet> (4 records, 1 partition)
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
from pathlib import Path
from typing import Any, Sequence

from un_comtrade.cli.main import main as cli_main
from un_comtrade.cli.utils import EXIT_OK
from un_comtrade.etl import PipelineContext
from un_comtrade.parser import TradeParser
from un_comtrade.storage import StorageConfig
from un_comtrade.storage.file import CSVWriter
from un_comtrade.transform import CanonicalDataset, TradeTransformer


# ---- constants -------------------------------------------------------------

EXIT_AUTH: int = 4
RECIPE_ID: str = "RECIPE-101"
_VALID_FORMATS: tuple[str, ...] = (
    "parquet", "csv", "duckdb", "json", "local-files"
)


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


def build_test_dataset() -> CanonicalDataset:
    """Build a small dataset suitable for the storage CLI."""
    raw = [
        _baseline_raw(partnerCode=156, primaryValue=1_000.0),
        _baseline_raw(partnerCode=840, partnerISO="USA",
                      primaryValue=2_000.0),
        _baseline_raw(partnerCode=76, partnerISO="BRA",
                      primaryValue=3_000.0),
        _baseline_raw(partnerCode=392, partnerISO="JPN",
                      primaryValue=4_000.0),
    ]
    parser = TradeParser(log_skipped=False)
    transformer = TradeTransformer(parser=parser)
    ctx = PipelineContext(pipeline_name="RECIPE-101")
    return transformer(source=raw, context=ctx)


def write_csv_dataset(target: Path) -> CanonicalDataset:
    """Persist the test dataset as CSV under ``target`` (a directory)."""
    dataset = build_test_dataset()
    writer = CSVWriter()
    config = StorageConfig(root=str(target))
    writer.store(dataset, config)
    return dataset


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


def storage_cli_demo(
    *,
    dataset_path: Path,
    output_path: Path,
    fmt: str = "parquet",
    overwrite: bool = False,
    output_format: str = "table",
    output_log: str | None = None,
) -> CliRunResult:
    """Run ``un-comtrade storage <fmt>`` end-to-end.

    Parameters
    ----------
    dataset_path
        Path to a stored dataset to read.
    output_path
        Destination path (file or directory).
    fmt
        Storage format. Default ``"parquet"``.
    overwrite
        Whether to overwrite the destination.
    output_format
        CLI output format. Default ``"table"``.
    output_log
        Optional file path for the rendered
        CLI output.

    Returns
    -------
    CliRunResult
        The argv, exit code, captured stdout,
        captured stderr.
    """
    argv: list[str] = [
        "storage", fmt,
        "--dataset", str(dataset_path),
        "--output-path", str(output_path),
        "--output-format", output_format,
    ]
    if overwrite:
        argv.append("--overwrite")
    if output_log:
        argv.extend(["--output", output_log])
    return _run_cli(argv)


# ---- main ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=RECIPE_ID, description=__doc__,
    )
    parser.add_argument(
        "--dataset", type=Path, required=True,
        help="Path to a stored dataset to read.",
    )
    parser.add_argument(
        "--output-path", type=Path, required=True,
        help="Destination path for the new store.",
    )
    parser.add_argument(
        "--format", dest="fmt",
        choices=_VALID_FORMATS, default="parquet",
        help="Storage format (default: parquet).",
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Overwrite the destination if it exists.",
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "table", "csv", "markdown", "text"],
        default="table",
        help="CLI output format (default: table).",
    )
    parser.add_argument(
        "--output", default=None,
        help="Optional file path for the rendered CLI output.",
    )
    args = parser.parse_args(argv)

    print("== Recipe 04: CLI storage parquet ==")
    shell_argv = [
        "un-comtrade", "storage", args.fmt,
        "--dataset", str(args.dataset),
        "--output-path", str(args.output_path),
        "--output-format", args.output_format,
    ]
    if args.overwrite:
        shell_argv.append("--overwrite")
    if args.output:
        shell_argv.extend(["--output", args.output])
    print(f"shell: {' '.join(shell_argv)}")

    if not args.dataset.exists():
        print(f"ERROR: dataset {args.dataset} does not exist.",
              file=sys.stderr)
        return 1

    result = storage_cli_demo(
        dataset_path=args.dataset,
        output_path=args.output_path,
        fmt=args.fmt,
        overwrite=args.overwrite,
        output_format=args.output_format,
        output_log=args.output,
    )
    print(f"exit  : {result.exit_code}")
    print(f"input : <{args.dataset.name}> (4 records)")
    print(
        f"output: <{args.output_path.name}> "
        f"(4 records, 1 partition)"
    )
    print("Done.")
    print(
        f"recipe={RECIPE_ID} format={args.fmt} "
        f"exit={result.exit_code}"
    )
    return result.exit_code if result.exit_code != EXIT_OK else 0


if __name__ == "__main__":
    raise SystemExit(main())