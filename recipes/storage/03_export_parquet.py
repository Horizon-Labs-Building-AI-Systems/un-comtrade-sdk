"""
---
recipe_id: RECIPE-033
title: Export a TradeResponse to Parquet (partitioned)
category: storage
difficulty: intermediate
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
    - name: compression
      type: str
      default: "snappy"
      description: Parquet compression codec. ``"snappy"``, ``"gzip"``,
        ``"zstd"``, ``"brotli"``, or ``"none"``.
    - name: output
      type: str
      default: ./output
      description: Directory the Parquet files are written into.
outputs:
  - kind: file
    path: output/<dataset_name>/<reporter>/<year>/<freq>/<dataset_name>.parquet
    description: |
      One Parquet file per partition key. Default
      partition strategy is
      ``(reporter_code, ref_year, frequency_code)``
      per ADR-0029. Single-reporter single-year
      single-frequency runs produce exactly one
      file.
  - kind: file
    path: output/<dataset_name>/<...>.meta.json
    description: Parquet-specific sidecar with the
      persisted schema version + compression codec.
  - kind: stdout
    path: null
    description: Run summary (rows, partitions, bytes, codec).
related_docs:
  - docs/011_ETL_SPECIFICATION.md
  - docs/012_STORAGE_SPECIFICATION.md
  - docs/decisions/ADR-0029-partition-strategy.md
related_recipes:
  - RECIPE-031
  - RECIPE-032
  - RECIPE-034
tags:
  - storage
  - parquet
  - partitioned
  - compression
  - columnar
---

Recipe 03 — Export a ``TradeResponse`` to Parquet.

Demonstrates the Parquet backend's key features:

1. **Deterministic partitioning** per ADR-0029:
   files are organised under
   ``<root>/<reporter>/<year>/<freq>/<dataset>.parquet``.
2. **Decimal-preserving schema**: numeric
   ``primaryValue`` fields are stored as
   ``decimal128(38, 18)`` so no precision is lost
   on the round-trip.
3. **Compression codecs** via
   ``StorageConfig.compression`` (snappy default
   per ADR-0027).

Parquet is the de-facto columnar format for
data-lake / warehouse pipelines — DuckDB,
Spark, BigQuery, Athena, Snowflake all read it
natively. Compared to CSV (RECIPE-032), Parquet
is 5-10× smaller on disk and 10-100× faster to
scan for analytics queries.

Expected output (mock-mode)::

    == Recipe 03: Export to Parquet ==
    Auth: OK (key configured)
    Reporter: 699  Period: 2022  Flow: X
    Fetching exports (T01) ...
    Building CanonicalDataset ...
      222 export records
    Writing Parquet (snappy) ...
      output : ./output
      codec  : snappy
      rows   : 222
      bytes  : 18,403
      parts  : 1
    Done.
"""

from __future__ import annotations

import argparse
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
from un_comtrade.storage.parquet import ParquetWriter
from un_comtrade.transform import CanonicalDataset, TradeTransformer


# ---- constants -------------------------------------------------------------

EXIT_AUTH: int = 4
RECIPE_ID: str = "RECIPE-033"
_VALID_FLOWS: tuple[str, ...] = ("X", "M")
_VALID_CODECS: tuple[str, ...] = ("none", "snappy", "gzip", "zstd", "brotli")


# ---- auth ------------------------------------------------------------------


def _require_api_key() -> str:
    key = os.environ.get("UN_COMTRADE_KEY", "").strip() or None
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

    destination: str
    row_count: int
    bytes_written: int
    partition_files: tuple[str, ...]
    partition_count: int
    codec: str


def export_parquet_demo(
    response: TradeResponse,
    output_dir: Path,
    *,
    compression: str = "snappy",
) -> ExportResult:
    """Build a dataset and write to Parquet under ``output_dir``.

    Parameters
    ----------
    response
        A ``TradeResponse`` envelope from the
        trade service. The test fixture injects
        a synthetic envelope.
    output_dir
        Root directory for the partitioned
        Parquet output.
    compression
        Parquet compression codec. One of
        ``"none"``, ``"snappy"``, ``"gzip"``,
        ``"zstd"``, ``"brotli"``. Default
        ``"snappy"``.

    Returns
    -------
    ExportResult
        The destination root, row count, byte
        total, partition file list, partition
        count, and codec used.
    """
    dataset = build_dataset_from_responses(response, name=RECIPE_ID)
    output_dir.mkdir(parents=True, exist_ok=True)

    writer = ParquetWriter()
    config = StorageConfig(root=str(output_dir), compression=compression)
    result = writer.store(dataset, config)

    files = tuple(
        path for paths in result.partitions.values() for path in paths
    )
    return ExportResult(
        destination=str(output_dir),
        row_count=result.record_count,
        bytes_written=result.byte_size or 0,
        partition_files=files,
        partition_count=len(result.partitions),
        codec=compression,
    )


# ---- sidecar -------------------------------------------------------------


def write_parquet_sidecar(
    result: ExportResult,
    *,
    recipe_id: str = RECIPE_ID,
    sdk_version: str | None = None,
) -> Path:
    """Emit a Parquet-specific metadata sidecar.

    Parquet's metadata sidecar captures the
    codec and the partition layout so downstream
    readers can verify the write. Distinct from
    the SDK-side ``*.meta.json`` produced by the
    writer's ``write_metadata_sidecar`` helper;
    this is the *recipe*-level sidecar.
    """
    sidecar_path = Path(result.destination) / f"{RECIPE_ID}.recipe.meta.json"
    sidecar = {
        "recipe_id": recipe_id,
        "category": "storage",
        "backend": "parquet",
        "row_count": result.row_count,
        "bytes_written": result.bytes_written,
        "partition_count": result.partition_count,
        "compression": result.codec,
        "files": list(result.partition_files),
        "sdk_version": sdk_version,
        "run_started_at": datetime.now(timezone.utc).isoformat(),
    }
    sidecar_path.write_text(
        json.dumps(sidecar, indent=2, default=str), encoding="utf-8"
    )
    return sidecar_path


# ---- error handling --------------------------------------------------------


def _exit_code_for(exc: BaseException) -> int:
    if isinstance(exc, ValidationError):
        return 3
    if isinstance(exc, AuthenticationError):
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
        "--compression", choices=_VALID_CODECS, default="snappy",
        help="Parquet compression codec (default: snappy).",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("./output"),
        help="Output directory (default: ./output).",
    )
    args = parser.parse_args(argv)

    print("== Recipe 03: Export to Parquet ==")
    print("Auth: OK (key configured)")
    print(
        f"Reporter: {args.reporter}  Period: {args.period}  "
        f"Flow: {args.flow}"
    )

    output_dir = args.output / f"{RECIPE_ID}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

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
            print(f"Writing Parquet ({args.compression}) ...")
            result = export_parquet_demo(
                response, output_dir, compression=args.compression
            )
            sidecar_path = write_parquet_sidecar(result)
    except ComtradeError as exc:
        code = _exit_code_for(exc)
        print(
            f"recipe={RECIPE_ID} error_class={type(exc).__name__} "
            f"message={exc} exit_code={code}",
            file=sys.stderr,
        )
        return code

    print(f"  output : {result.destination}")
    print(f"  codec  : {result.codec}")
    print(f"  rows   : {result.row_count}")
    print(f"  bytes  : {result.bytes_written:,}")
    print(f"  parts  : {result.partition_count}")
    print(f"  sidecar: {sidecar_path}")
    print("Done.")
    print(
        f"recipe={RECIPE_ID} rows={result.row_count} "
        f"parts={result.partition_count} codec={result.codec}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())