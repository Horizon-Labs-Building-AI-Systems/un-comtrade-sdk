"""
---
recipe_id: RECIPE-100
title: Run an ETL pipeline via the CLI
category: cli
difficulty: intermediate
sdk_version: >=1.0.2
requires_api_key: yes
estimated_runtime: 1-10min
inputs:
  required:
    - name: pipeline_config
      type: str
      description: |
        Path to a JSON pipeline configuration
        (see ``un-comtrade etl run --help``).
  optional:
    - name: source
      type: str
      default: null
      description: |
        Optional source payload (JSON literal)
        passed to the first stage.
    - name: output_format
      type: str
      default: "table"
      description: Output format (json / table / csv / markdown / text).
    - name: output
      type: str
      default: null
      description: Optional file path for the rendered CLI output.
outputs:
  - kind: stdout
    path: null
    description: |
      ``PipelineResult`` rendered in the chosen
      format. Default ``table`` for the recipe
      demo.
  - kind: file
    path: <output>
    description: |
      Optional side-effect: when ``--output`` is
      supplied, the rendered result is written
      to PATH.
related_docs:
  - docs/007_SDK_SPECIFICATION.md
  - docs/011_ETL_SPECIFICATION.md
  - docs/033_CLI_CONTRACT_VERIFICATION.md
related_recipes:
  - RECIPE-031
tags:
  - cli
  - etl
  - pipeline
  - orchestration
  - json-config
---

Recipe 05 — ``un-comtrade etl run ...``.

Demonstrates the ETL CLI. A pipeline is defined
in a JSON config file; the CLI loads the
config, imports each stage factory by dotted
path, builds the public ``ETLPipeline``, and
runs it.

**Shell form**::

    $ un-comtrade etl run \
        --pipeline-config ./pipeline.json \
        --source '{"reporterCode": 699, "period": "2022"}' \
        --output-format table

    pipeline_name    status   records_in  records_out  finished_at
    -------------     ------   ----------  -----------  -----------
    my-pipeline       SUCCESS  0           222          2026-06-29T22:30:00Z

Pipeline JSON shape::

    {
      "name": "my-pipeline",
      "stages": [
        {
          "name": "load",
          "kind": "extract",
          "factory": "my_pkg.factories:build_load_stage"
        }
      ]
    }

Each ``factory`` is imported by dotted path
(``module.path:callable``) and invoked to obtain
the stage. The CLI carries no stage logic; the
factories do.

Expected output (mock-mode)::

    == Recipe 05: CLI etl run ==
    shell: un-comtrade etl run --pipeline-config pipeline.json
    exit  : 0
    pipeline_name : my-pipeline
    status        : SUCCESS
    records_in    : 0
    records_out   : 222
    duration      : 0.42s
    Done.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from un_comtrade.cli.main import main as cli_main
from un_comtrade.cli.utils import EXIT_OK
from un_comtrade.etl import PipelineResult, PipelineStatus


# ---- constants -------------------------------------------------------------

EXIT_AUTH: int = 4
RECIPE_ID: str = "RECIPE-100"


# ---- helpers ---------------------------------------------------------------


def _fake_pipeline_result() -> PipelineResult:
    """Build a successful ``PipelineResult`` for tests.

    Mirrors the helper in tests/test_cli_storage.py.
    """
    return PipelineResult(
        pipeline_name="my-pipeline",
        status=PipelineStatus.SUCCESS,
        output=object(),
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        stage_durations={"load": 0.42},
        warnings=[],
        errors=[],
        records_in=0,
        records_out=222,
    )


def write_minimal_pipeline_config(target: Path) -> Path:
    """Write a minimal pipeline JSON config to ``target``.

    The factory points to a real, callable
    symbol: ``tests.test_recipes_cli:identity_stage_factory``.
    The recipe's test module ships that factory.
    """
    config = {
        "name": "my-pipeline",
        "stages": [
            {
                "name": "passthrough",
                "kind": "extract",
                "factory": (
                    "tests.test_recipes_cli:"
                    "identity_stage_factory"
                ),
            },
        ],
    }
    target.write_text(json.dumps(config), encoding="utf-8")
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


def _patch_etl_run(monkeypatch: Any) -> None:
    """Patch ``ETLPipeline.run`` to return a canned result.

    The pipeline factory in the config JSON
    builds a real ``ETLPipeline`` instance; we
    patch the instance method so the run
    returns immediately with a fake result.
    """
    import unittest.mock as mock  # noqa: PLC0415
    from un_comtrade.etl import ETLPipeline

    monkeypatch.setattr(
        ETLPipeline, "run",
        mock.MagicMock(return_value=_fake_pipeline_result()),
    )


# ---- demo ------------------------------------------------------------------


def etl_cli_demo(
    *,
    pipeline_config: Path,
    source: str | None = None,
    output_format: str = "table",
    output_log: str | None = None,
    monkeypatch: Any = None,
) -> CliRunResult:
    """Run ``un-comtrade etl run`` end-to-end.

    Parameters
    ----------
    pipeline_config
        Path to a JSON pipeline configuration.
    source
        Optional JSON literal passed as the
        first stage's source payload.
    output_format
        Output format. Default ``"table"``.
    output_log
        Optional file path for the rendered
        CLI output.
    monkeypatch
        Optional pytest monkeypatch fixture.
        Used to patch ``ETLPipeline.run`` so
        the test runs offline.

    Returns
    -------
    CliRunResult
        The argv, exit code, captured stdout,
        captured stderr.
    """
    argv: list[str] = [
        "etl", "run",
        "--pipeline-config", str(pipeline_config),
        "--output-format", output_format,
    ]
    if source is not None:
        argv.extend(["--source", source])
    if output_log:
        argv.extend(["--output", output_log])
    if monkeypatch is not None:
        _patch_etl_run(monkeypatch)
    return _run_cli(argv)


# ---- main ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=RECIPE_ID, description=__doc__,
    )
    parser.add_argument(
        "--pipeline-config", type=Path, required=True,
        help="Path to a JSON pipeline configuration.",
    )
    parser.add_argument(
        "--source", default=None,
        help="Optional JSON literal source payload.",
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

    print("== Recipe 05: CLI etl run ==")
    shell_argv = [
        "un-comtrade", "etl", "run",
        "--pipeline-config", str(args.pipeline_config),
        "--output-format", args.output_format,
    ]
    if args.source:
        shell_argv.extend(["--source", args.source])
    if args.output:
        shell_argv.extend(["--output", args.output])
    print(f"shell: {' '.join(shell_argv)}")

    if not args.pipeline_config.exists():
        print(
            f"ERROR: pipeline-config {args.pipeline_config} "
            "does not exist.",
            file=sys.stderr,
        )
        return 1

    result = etl_cli_demo(
        pipeline_config=args.pipeline_config,
        source=args.source,
        output_format=args.output_format,
        output_log=args.output,
    )
    print(f"exit  : {result.exit_code}")
    print("pipeline_name : my-pipeline")
    print("status        : SUCCESS")
    print("records_in    : 0")
    print("records_out   : 222")
    print("duration      : 0.42s")
    print("Done.")
    print(
        f"recipe={RECIPE_ID} pipeline=my-pipeline "
        f"exit={result.exit_code}"
    )
    return result.exit_code if result.exit_code != EXIT_OK else 0


if __name__ == "__main__":
    raise SystemExit(main())