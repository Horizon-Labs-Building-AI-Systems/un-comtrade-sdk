"""
---
recipe_id: RECIPE-032
title: Export a TradeResponse to CSV
category: storage
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
      description: Annual period (e.g. "2022")
  optional:
    - name: flow
      type: str
      default: "X"
      description: Trade flow. ``"X"`` (exports) or ``"M"`` (imports).
    - name: output
      type: str
      default: ./output
      description: Directory the CSV file is written into.
outputs:
  - kind: file
    path: output/RECIPE_032_<UTC-timestamp>.csv
    description: |
      CSV file with the documented
      ``trade_records`` schema (one row per
      parsed ``TradeRecord``).
  - kind: file
    path: output/RECIPE_032_<UTC-timestamp>.meta.json
    description: Provenance sidecar (recipe id, row count, SHA-256 digest).
  - kind: stdout
    path: null
    description: Single-line summary of the run.
related_docs:
  - docs/011_ETL_SPECIFICATION.md
  - docs/012_STORAGE_SPECIFICATION.md
related_recipes:
  - RECIPE-031
  - RECIPE-033
  - RECIPE-034
tags:
  - storage
  - csv
  - export
  - auth
---

Recipe 02 — Export a ``TradeResponse`` to CSV.

Demonstrates the simplest end-to-end "fetch +
transform + persist" path:

1. Fetch trade data via ``client.trade``.
2. Build a ``CanonicalDataset`` from the response
   via ``TradeTransformer``.
3. Write the dataset to CSV using ``CSVWriter``.

CSV is the lingua franca for trade data — easy
to open in any spreadsheet, easy to grep, and
the simplest portable artefact. The recipe
demonstrates the same flow as the full ETL
pipeline but with no pipeline orchestration: a
direct call to the writer.

The demo function takes the ``TradeResponse``
envelope and an output path; the test injects a
synthetic response and a ``tmp_path``.

Expected output (mock-mode)::

    == Recipe 02: Export to CSV ==
    Auth: OK (key configured)
    Reporter: 699  Period: 2022  Flow: X
    Fetching exports (T01) ...
    Building CanonicalDataset ...
      222 export records
    Writing CSV ...
      output : output/RECIPE_032_20260629T103000Z.csv
      sidecar: output/RECIPE_032_20260629T103000Z.meta.json
    Done.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
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
from un_comtrade.parser import TradeParser
from un_comtrade.storage import StorageConfig, StorageError
from un_comtrade.storage.file import CSVWriter
from un_comtrade.transform import CanonicalDataset, TradeTransformer


# ---- constants -------------------------------------------------------------

EXIT_AUTH: int = 4
RECIPE_ID: str = "RECIPE_032"
_VALID_FLOWS: tuple[str, ...] = ("X", "M")


# ---- auth ------------------------------------------------------------------


def _require_api_key() -> str:
    key = os.environ.get("UN_COMTRADE_KEY", "").strip()
    if not key:
        print(
            "ERROR: UN_COMTRADE_KEY is not set. "
            "Set it to your UN Comtrade API key and re-run.",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_AUTH)
    return key


# ---- dataset construction -------------------------------------------------


def build_dataset_from_responses(
    *responses: TradeResponse,
    name: str = RECIPE_ID,
) -> CanonicalDataset:
    """Parse one or more ``TradeResponse`` envelopes and wrap."""
    from un_comtrade.etl import PipelineContext
    parser = TradeParser(log_skipped=False)
    transformer = TradeTransformer(parser=parser)
    all_records: list[Any] = []
    skipped_total = 0
    for response in responses:
        ctx = PipelineContext(pipeline_name=name)
        ds = transformer(source=list(response.records), context=ctx)
        all_records.extend(ds.records)
        skipped_total += ds.skipped
    return CanonicalDataset(
        name=name,
        records=tuple(all_records),
        parser_name="TradeParser",
        skipped=skipped_total,
        source_count=sum(len(r.records) for r in responses),
        extracted_at=datetime.now(timezone.utc),
        metadata={},
    )


# ---- demo ------------------------------------------------------------------


@dataclass(frozen=True)
class ExportResult:
    """Result envelope for the export recipes."""

    output_path: str
    row_count: int
    bytes_written: int
    files: tuple[str, ...]


def export_csv_demo(
    response: TradeResponse,
    output_path: Path,
) -> ExportResult:
    """Build a dataset from ``response`` and write to CSV.

    Parameters
    ----------
    response
        A ``TradeResponse`` envelope from the
        trade service. The test fixture injects
        a synthetic envelope.
    output_path
        Full path of the CSV file. The writer
        appends ``.csv`` if missing.

    Returns
    -------
    ExportResult
        The output path, the row count, the
        number of bytes written, and the file
        paths the writer produced.
    """
    dataset = build_dataset_from_responses(response, name=RECIPE_ID)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    writer = CSVWriter()
    config = StorageConfig(root=str(output_path))
    result = writer.store(dataset, config)
    files = tuple(
        path
        for paths in result.partitions.values()
        for path in paths
    )
    return ExportResult(
        output_path=str(files[0]) if files else str(output_path),
        row_count=result.record_count,
        bytes_written=result.byte_size or 0,
        files=files,
    )


# ---- sidecar -------------------------------------------------------------


def write_sidecar(
    result: ExportResult,
    *,
    recipe_id: str = RECIPE_ID,
    sdk_version: str | None = None,
) -> Path:
    """Emit a metadata sidecar next to the dataset.

    The sidecar carries the recipe id, the row
    count, the bytes written, and a SHA-256
    digest of the data file. Useful for
    downstream consumers that want to verify
    integrity without re-reading the dataset.
    """
    data_path = Path(result.output_path)
    sidecar_path = data_path.with_suffix(".meta.json")
    digest = (
        hashlib.sha256(data_path.read_bytes()).hexdigest()
        if data_path.exists() else ""
    )
    sidecar = {
        "recipe_id": recipe_id,
        "category": "storage",
        "row_count": result.row_count,
        "bytes_written": result.bytes_written,
        "files": list(result.files),
        "sdk_version": sdk_version,
        "run_started_at": datetime.now(timezone.utc).isoformat(),
        "output_digests": {"data": f"sha256:{digest}"},
    }
    sidecar_path.write_text(
        json.dumps(sidecar, indent=2, default=str), encoding="utf-8"
    )
    return sidecar_path


# ---- error handling --------------------------------------------------------


def _exit_code_for(exc: BaseException) -> int:
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
    if isinstance(exc, (APIError, StorageError)):
        return 8
    return 1


# ---- main ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    key = _require_api_key()

    parser = argparse.ArgumentParser(
        prog=RECIPE_ID, description=__doc__,
    )
    parser.add_argument(
        "--reporter", type=int, default=699,
        help="UN Comtrade reporter code (default: 699 = India).",
    )
    parser.add_argument(
        "--period", default="2022",
        help='Annual period, e.g. "2022" (default: 2022).',
    )
    parser.add_argument(
        "--flow", choices=_VALID_FLOWS, default="X",
        help="Trade flow (default: X = exports).",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("./output"),
        help="Output directory (default: ./output).",
    )
    args = parser.parse_args(argv)

    print("== Recipe 02: Export to CSV ==")
    print("Auth: OK (key configured)")
    print(
        f"Reporter: {args.reporter}  Period: {args.period}  "
        f"Flow: {args.flow}"
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = args.output / f"{RECIPE_ID}_{timestamp}.csv"

    config = Configuration(api_key=key)
    try:
        with ComtradeClient(config) as client:
            method = (
                client.trade.get_exports
                if args.flow == "X"
                else client.trade.get_imports
            )
            print("Fetching exports (T01) ..." if args.flow == "X"
                  else "Fetching imports (T02) ...")
            response = method(
                reporter_code=args.reporter, period=args.period
            )
            print("Building CanonicalDataset ...")
            ds = build_dataset_from_responses(response, name=RECIPE_ID)
            print(f"  {len(ds.records)} records")
            print("Writing CSV ...")
            result = export_csv_demo(response, output_path)
            sidecar_path = write_sidecar(result)
    except ComtradeError as exc:
        code = _exit_code_for(exc)
        print(
            f"recipe={RECIPE_ID} error_class={type(exc).__name__} "
            f"message={exc} exit_code={code}",
            file=sys.stderr,
        )
        return code

    print(f"  output : {result.output_path}")
    print(f"  sidecar: {sidecar_path}")
    print("Done.")
    print(
        f"recipe={RECIPE_ID} rows={result.row_count} "
        f"data={Path(result.output_path).name}"
    )
    return 0


def _get_sdk_version() -> str:
    from un_comtrade import __version__
    return __version__


if __name__ == "__main__":
    raise SystemExit(main())
