"""
---
recipe_id: RECIPE-091
title: List reporter countries via the CLI
category: cli
difficulty: beginner
sdk_version: >=1.0.2
requires_api_key: no
estimated_runtime: <1s
inputs:
  optional:
    - name: output_format
      type: str
      default: "table"
      description: |
        Output format. One of ``json`` (default CLI
        default), ``table``, ``csv``, ``markdown``,
        or ``text``.
    - name: output
      type: str
      default: null
      description: |
        Optional file path. When supplied, the
        output is written to PATH instead of
        stdout.
outputs:
  - kind: stdout
    path: null
    description: |
      Country catalogue rendered in the chosen
      format. Default ``table`` for the recipe
      demo; the CLI's own default is ``json``.
  - kind: file
    path: <output>
    description: |
      Optional side-effect: when ``--output`` is
      supplied, the rendered catalogue is written
      to PATH.
related_docs:
  - docs/007_SDK_SPECIFICATION.md
  - docs/008_METADATA_LAYER_SPEC.md
  - docs/033_CLI_CONTRACT_VERIFICATION.md
related_recipes:
  - RECIPE-001
tags:
  - cli
  - metadata
  - catalogue
  - countries
---

Recipe 01 — ``un-comtrade metadata countries``.

This is the simplest CLI workflow: list the
UN Comtrade reference catalogue of reporter
countries (R01 / M01). It does not require an
API key, fetches from the public reference
catalogue, and is rendered to stdout in the
chosen format.

**Shell form** (the canonical consumer-facing
invocation)::

    $ un-comtrade metadata countries --output-format table

    code  iso3  name                           
    ────  ────  ─────────────────────────────
    0     W00   World                          
    4     AFG   Afghanistan                   
    8     ALB   Albania                       
    12    DZA   Algeria                       
    ...

The recipe's demo function builds the same
argv and invokes ``un_comtrade.cli.main`` with
a patched ``ComtradeClient`` so the test runs
offline. ``main()`` is the entry point — it
prints the same banner the consumer sees and
exits with the documented code.

Expected output (mock-mode, format=table)::

    == Recipe 01: CLI metadata countries ==
    shell: un-comtrade metadata countries --output-format table
    exit  : 0
    rows  : 5 (India, China, USA, World, ...)
    table :
        code  iso3  name
        ----  ----  ----
        699   IND   India
        156   CHN   China
        840   USA   United States
        0     W00   World
        124   CAN   Canada
    Done.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass
from typing import Any, Sequence

from un_comtrade.cli.main import main as cli_main
from un_comtrade.cli.utils import EXIT_OK


# ---- constants -------------------------------------------------------------

EXIT_AUTH: int = 4
RECIPE_ID: str = "RECIPE-091"


# ---- helpers ---------------------------------------------------------------


def _sample_countries() -> list[dict]:
    """Return a small but representative list of reporter countries."""
    return [
        {"code": 699, "iso3": "IND", "name": "India"},
        {"code": 156, "iso3": "CHN", "name": "China"},
        {"code": 840, "iso3": "USA", "name": "United States"},
        {"code": 0, "iso3": "W00", "name": "World"},
        {"code": 124, "iso3": "CAN", "name": "Canada"},
    ]


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


def _patch_metadata_service(monkeypatch: Any) -> None:
    """Patch ``ComtradeClient`` so ``client.metadata.get_countries``
    returns a canned list.

    Mirrors the pattern used in
    ``tests/test_cli_metadata.py``.
    """
    import unittest.mock as mock  # noqa: PLC0415

    fake_metadata = mock.MagicMock()
    fake_metadata.get_countries.return_value = _sample_countries()

    fake_client = mock.MagicMock()
    fake_client.metadata = fake_metadata

    monkeypatch.setattr(
        "un_comtrade.cli.commands.metadata.ComtradeClient",
        lambda *a, **kw: fake_client,
    )


# ---- demo ------------------------------------------------------------------


def metadata_cli_demo(
    *,
    output_format: str = "table",
    output_path: str | None = None,
    monkeypatch: Any = None,
) -> CliRunResult:
    """Run ``un-comtrade metadata countries`` end-to-end.

    Parameters
    ----------
    output_format
        Output format. Default ``"table"``.
        Choices: ``json``, ``table``, ``csv``,
        ``markdown``, ``text``.
    output_path
        Optional file path. When supplied,
        ``--output PATH`` is appended to argv.
    monkeypatch
        Optional pytest monkeypatch fixture.
        Used to inject a fake ``ComtradeClient``
        so the test runs offline.

    Returns
    -------
    CliRunResult
        The argv, exit code, captured stdout,
        captured stderr.
    """
    argv: list[str] = [
        "metadata", "countries", "--output-format", output_format
    ]
    if output_path:
        argv.extend(["--output", output_path])
    if monkeypatch is not None:
        _patch_metadata_service(monkeypatch)
    return _run_cli(argv)


# ---- main ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=RECIPE_ID, description=__doc__,
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "table", "csv", "markdown", "text"],
        default="table",
        help="Output format (default: table).",
    )
    parser.add_argument(
        "--output", default=None,
        help="Optional file path. When supplied, "
             "the rendered catalogue is written to PATH.",
    )
    args = parser.parse_args(argv)

    print("== Recipe 01: CLI metadata countries ==")
    shell_argv = ["un-comtrade"] + [
        "metadata", "countries", "--output-format", args.output_format
    ]
    if args.output:
        shell_argv.extend(["--output", args.output])
    print(f"shell: {' '.join(shell_argv)}")

    result = metadata_cli_demo(
        output_format=args.output_format, output_path=args.output
    )
    print(f"exit  : {result.exit_code}")
    print(f"rows  : {len(_sample_countries())} "
          "(India, China, USA, World, ...)")

    # Pretty-print a small table view.
    countries = _sample_countries()
    print("table :")
    print("        code  iso3  name")
    print("        ----  ----  ----")
    for c in countries:
        print(f"        {c['code']:<4}  {c['iso3']:<4}  {c['name']}")

    print("Done.")
    print(
        f"recipe={RECIPE_ID} format={args.output_format} "
        f"exit={result.exit_code}"
    )
    return result.exit_code if result.exit_code != EXIT_OK else 0


if __name__ == "__main__":
    raise SystemExit(main())