"""
---
recipe_id: RECIPE-104
title: Render the same command in five output formats
category: cli
difficulty: beginner
sdk_version: >=1.0.2
requires_api_key: no
estimated_runtime: <1s
inputs:
  optional:
    - name: reporter
      type: int
      default: 699
      description: Reporter code for the metadata lookup.
    - name: formats
      type: list
      default: ["json", "table", "csv", "markdown", "text"]
      description: Output formats to render.
outputs:
  - kind: stdout
    path: null
    description: |
      Five rendered variants of the same
      metadata query — one per output format.
      Useful for picking the right format for
      a downstream consumer (spreadsheet,
      dashboard, terminal).
related_docs:
  - docs/007_SDK_SPECIFICATION.md
  - docs/033_CLI_CONTRACT_VERIFICATION.md
related_recipes:
  - RECIPE-091
tags:
  - cli
  - output-format
  - json
  - table
  - csv
  - markdown
  - text
---

Recipe 06 — render the same command in every output format.

The CLI ships with five output formats:
``json`` (default), ``table``, ``csv``,
``markdown``, and ``text``. Switching between
them is a single ``--output-format`` flag.

**Shell form**::

    $ un-comtrade metadata countries --output-format json | jq .
    $ un-comtrade metadata countries --output-format table
    $ un-comtrade metadata countries --output-format csv > countries.csv
    $ un-comtrade metadata countries --output-format markdown | pbcopy
    $ un-comtrade metadata countries --output-format text

This recipe runs all five variants back-to-back
on the same canned response, demonstrating how
each format renders the same underlying data.

Expected output (mock-mode, abridged)::

    == Recipe 06: CLI output formats ==
    shell: un-comtrade metadata countries --output-format json
    exit  : 0
    json  :
        [{"code": 699, "iso3": "IND", "name": "India"}, ...]

    shell: un-comtrade metadata countries --output-format table
    exit  : 0
    table :
        code  iso3  name
        ----  ----  ----
        699   IND   India
        ...

    shell: un-comtrade metadata countries --output-format csv
    exit  : 0
    csv   : code,iso3,name\n699,IND,India\n...

    shell: un-comtrade metadata countries --output-format markdown
    exit  : 0
    md    : | code | iso3 | name   |\n|-----|------|-------|\n| 699 | IND  | India |\n...

    shell: un-comtrade metadata countries --output-format text
    exit  : 0
    text  : India (699 / IND)\nChina (156 / CHN)\n...
    Done.
"""

from __future__ import annotations

import argparse
import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from typing import Any, Sequence

from un_comtrade.cli.main import main as cli_main
from un_comtrade.cli.utils import EXIT_OK


# ---- constants -------------------------------------------------------------

EXIT_AUTH: int = 4
RECIPE_ID: str = "RECIPE-104"
_VALID_FORMATS: tuple[str, ...] = (
    "json", "table", "csv", "markdown", "text",
)


# ---- helpers ---------------------------------------------------------------


def _sample_countries() -> list[dict]:
    """Small representative list of reporter countries."""
    return [
        {"code": 699, "iso3": "IND", "name": "India"},
        {"code": 156, "iso3": "CHN", "name": "China"},
        {"code": 840, "iso3": "USA", "name": "United States"},
        {"code": 0, "iso3": "W00", "name": "World"},
        {"code": 124, "iso3": "CAN", "name": "Canada"},
    ]


@dataclass(frozen=True)
class CliRunResult:
    """Outcome of one CLI invocation."""

    argv: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class FormatRun:
    """One format's rendered output."""

    fmt: str
    argv: tuple[str, ...]
    exit_code: int
    stdout: str


def _run_cli(argv: Sequence[str]) -> CliRunResult:
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


def _patch_metadata_service(monkeypatch: Any) -> None:
    """Patch ``ComtradeClient`` so ``client.metadata.get_countries``
    returns a canned list."""
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


def output_formats_cli_demo(
    *,
    formats: Sequence[str] = _VALID_FORMATS,
    monkeypatch: Any = None,
) -> tuple[FormatRun, ...]:
    """Run ``un-comtrade metadata countries`` in every format.

    Parameters
    ----------
    formats
        Sequence of formats to render. Default
        is all five (``json``, ``table``,
        ``csv``, ``markdown``, ``text``).
    monkeypatch
        Optional pytest monkeypatch fixture.

    Returns
    -------
    tuple[FormatRun, ...]
        One ``FormatRun`` per format, in the
        order given. Each ``FormatRun`` carries
        the format name, argv, exit code, and
        captured stdout.
    """
    if monkeypatch is not None:
        _patch_metadata_service(monkeypatch)

    runs: list[FormatRun] = []
    for fmt in formats:
        argv = (
            "metadata", "countries",
            "--output-format", fmt,
        )
        result = _run_cli(argv)
        runs.append(FormatRun(
            fmt=fmt,
            argv=argv,
            exit_code=result.exit_code,
            stdout=result.stdout,
        ))
    return tuple(runs)


# ---- main ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=RECIPE_ID, description=__doc__,
    )
    parser.add_argument(
        "--formats", nargs="+",
        choices=_VALID_FORMATS,
        default=list(_VALID_FORMATS),
        help="Output formats to render.",
    )
    args = parser.parse_args(argv)

    print("== Recipe 06: CLI output formats ==")
    runs = output_formats_cli_demo(formats=args.formats)
    for run in runs:
        shell_argv = (
            ["un-comtrade", "metadata", "countries",
             "--output-format", run.fmt]
        )
        print(f"shell: {' '.join(shell_argv)}")
        print(f"exit  : {run.exit_code}")
        # Show a short preview of each format's stdout.
        preview = run.stdout.strip().splitlines()
        for line in preview[:3]:
            print(f"{run.fmt:<8}: {line}")
        if len(preview) > 3:
            print(f"{run.fmt:<8}: ... ({len(preview) - 3} more lines)")
        print()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())