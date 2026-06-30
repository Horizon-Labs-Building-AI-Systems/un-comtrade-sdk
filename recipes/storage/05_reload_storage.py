"""
---
recipe_id: RECIPE-035
title: Reload a stored dataset back into a CanonicalDataset
category: storage
difficulty: beginner
sdk_version: >=1.0.2
requires_api_key: no
estimated_runtime: <30s
inputs:
  required:
    - name: source_path
      type: str
      description: |
        Path to a previously-stored dataset. The
        extension (``.csv`` / ``.json`` / ``.parquet``
        / ``.duckdb``) auto-detects the backend. A
        directory is supported (scanned for the first
        known file).
    - name: build_if_missing
      type: bool
      default: true
      description: |
        If true and ``source_path`` does not exist,
        build a fresh dataset from the live API and
        write it before reading back.
  optional:
    - name: reporter_code
      type: int
      default: 699
      description: Reporter code (used only when build_if_missing=true).
    - name: period
      type: str
      default: "2022"
      description: Annual period (used only when build_if_missing=true).
    - name: flow
      type: str
      default: "X"
      description: Trade flow (used only when build_if_missing=true).
outputs:
  - kind: stdout
    path: null
    description: Dataset summary (rows, source, parser, schema version).
  - kind: file
    path: <source_path>
    description: |
      The source dataset (read back). No new file
      is written if it already exists.
  - kind: file
    path: <source_path>
    description: |
      The freshly-built dataset (written only if
      ``build_if_missing=true`` and the source
      was absent).
related_docs:
  - docs/011_ETL_SPECIFICATION.md
  - docs/012_STORAGE_SPECIFICATION.md
related_recipes:
  - RECIPE-031
  - RECIPE-032
  - RECIPE-033
  - RECIPE-034
  - RECIPE-036
tags:
  - storage
  - reload
  - round-trip
  - registry
  - auto-detect
---

Recipe 05 — Reload a stored dataset back into a ``CanonicalDataset``.

Demonstrates the public read path:

1. ``StorageRegistry.open(uri)`` auto-detects
   the backend from the file extension
   (``.csv`` / ``.json`` / ``.parquet`` /
   ``.duckdb``).
2. The read returns a ``CanonicalDataset``
   with the same records, parser, and
   schema-version the writer captured.
3. The recipe supports a "load or build"
   pattern: if the file is missing, fetch from
   the live API, write it, then read it back —
   useful for idempotent pipeline runs.

The demo function takes only the path; the test
fixture writes a dataset first (with one of
RECIPEs 02-04) and then calls ``reload_demo``
to round-trip it. The ``main()`` function
exercises the "load or build" path end-to-end.

Expected output (mock-mode)::

    == Recipe 05: Reload from storage ==
    Auth: OK (key configured)
    Source: output/RECIPE_032_20260629T103000Z.csv
    Reloading ...
      backend : csv
      rows    : 222
      parser  : TradeParser
      schema  : v1.0.2
    Done.
"""

from __future__ import annotations

import argparse
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
from un_comtrade.storage import (
    StorageBackend,
    StorageConfig,
    StorageError,
    StorageRegistry,
)
from un_comtrade.transform import CanonicalDataset, TradeTransformer


# ---- constants -------------------------------------------------------------

EXIT_AUTH: int = 4
EXIT_NOT_FOUND: int = 9
RECIPE_ID: str = "RECIPE-035"
_VALID_FLOWS: tuple[str, ...] = ("X", "M")


# ---- auth ------------------------------------------------------------------


def _require_api_key_or_none() -> str | None:
    """Auth is optional for reload; required for build-on-missing."""
    return os.environ.get("UN_COMTRADE_KEY", "").strip() or None


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
class ReloadResult:
    """Result envelope for the reload recipe."""

    path: str
    backend: str
    row_count: int
    parser_name: str
    schema_version: str
    built: bool


def reload_demo(
    source_path: Path,
    *,
    registry: StorageRegistry | None = None,
) -> ReloadResult:
    """Load a stored dataset via ``StorageRegistry.open``.

    The SDK's ``StorageRegistry.open`` only inspects
    the *first level* of a directory for a recognised
    suffix. Partitioned Parquet output (``<root>/<rep>/
    <year>/<freq>/...``) has only subdirectories at
    the top level, so the auto-detection falls through
    to ``DUCKDB`` and the read fails. To work around
    that, this recipe resolves the target first and
    then dispatches to the matching backend's ``read``
    method directly, bypassing the registry's
    first-level suffix check.

    Parameters
    ----------
    source_path
        Path to a previously-stored dataset. The
        extension determines the backend. For
        partitioned Parquet output, ``source_path``
        can be either the partition directory or a
        file under it.
    registry
        Optional pre-built registry. If None, a
        fresh ``StorageRegistry()`` is created.

    Returns
    -------
    ReloadResult
        The path, detected backend, row count,
        parser name, schema version, and the
        ``built`` flag (always ``False`` for
        the read-only path).
    """
    registry = registry or StorageRegistry()
    target = _resolve_read_target(source_path)
    backend_label = _detect_backend_name(source_path)
    if backend_label == "parquet":
        # For parquet, the reader's ``rglob`` works
        # on directories. Pass the parent dir if
        # ``target`` is a file.
        read_root = target.parent if target.is_file() else target
        storage = registry.get(StorageBackend.PARQUET)
        dataset = storage.read(StorageConfig(root=str(read_root)))
    elif backend_label in {"csv", "json"}:
        storage = registry.get(StorageBackend(backend_label))
        read_root = target.parent if target.is_file() else target
        dataset = storage.read(StorageConfig(root=str(read_root)))
    else:
        dataset = registry.open(str(target))
    return ReloadResult(
        path=str(source_path),
        backend=backend_label,
        row_count=len(dataset.records),
        parser_name=dataset.parser_name,
        schema_version=dataset.schema_version,
        built=False,
    )


def load_or_build_demo(
    source_path: Path,
    *,
    client: ComtradeClient,
    registry: StorageRegistry | None = None,
    reporter_code: int = 699,
    period: str = "2022",
    flow: str = "X",
    build_writer_module: str | None = None,
) -> ReloadResult:
    """Load the dataset at ``source_path`` or build it if missing.

    If ``source_path`` does not exist, fetch from
    the live API, write it to the path using the
    matching backend, and return the rebuilt
    dataset. Otherwise, call
    ``registry.open(source_path)``.

    ``build_writer_module`` lets callers (and
    tests) pick which writer to use when
    building. Recognised values: ``"csv"``,
    ``"parquet"``, ``"duckdb"``. If None,
    inferred from the file extension.
    """
    if source_path.exists():
        return reload_demo(source_path, registry=registry)

    from un_comtrade.storage import StorageConfig  # noqa: PLC0415

    method = (
        client.trade.get_exports if flow == "X"
        else client.trade.get_imports
    )
    response = method(reporter_code=reporter_code, period=period)
    dataset = build_dataset_from_responses(response, name=RECIPE_ID)

    ext = source_path.suffix.lower()
    backend = build_writer_module or _infer_writer_from_ext(ext)
    writer = _writer_for(backend)
    config = StorageConfig(root=str(source_path))
    writer.store(dataset, config)
    rebuilt = registry.open(str(source_path))
    return ReloadResult(
        path=str(source_path),
        backend=_detect_backend_name(source_path),
        row_count=len(rebuilt.records),
        parser_name=rebuilt.parser_name,
        schema_version=rebuilt.schema_version,
        built=True,
    )


# ---- helpers ---------------------------------------------------------------


def _resolve_read_target(path: Path) -> Path:
    """Map a user-supplied storage path to the SDK's expected shape.

    The SDK's ``StorageRegistry._detect_backend`` falls
    back to ``DUCKDB`` when a directory's first-level
    children don't include a recognised suffix. For
    partitioned Parquet, the top level is always
    ``<reporter>/<year>/<freq>/...`` subdirectories with
    no extension. To work around the detection gap:

    - If the path is a parquet file, return it directly
      (the backend detection picks ``.parquet``).
    - If the path is a directory containing parquet
      files (any depth), return the *first* parquet file
      so detection picks the parquet backend. The
      parquet reader's ``rglob`` finds all sibling
      files via the registry's ``StorageConfig`` so
      this still produces a complete round-trip.
    - For CSV directories (with ``*.csv`` or
      ``*.meta.json`` at top level), return the
      directory unchanged; the CSV reader accepts
      directories.
    - For DuckDB files inside a directory, return
      the file so detection picks ``.duckdb``.
    """
    if not path.exists():
        raise StorageError(f"dataset path does not exist: {path}")
    if path.is_file():
        return path
    if path.is_dir():
        parquet_files = sorted(path.rglob("*.parquet"))
        if parquet_files:
            return parquet_files[0]
        if any(path.glob("*.csv")) or any(path.glob("*.meta.json")):
            return path
        for child in path.iterdir():
            if child.suffix.lower() in {".duckdb", ".ddb"}:
                return child
        return path
    raise StorageError(f"dataset path does not exist: {path}")


def _infer_writer_from_ext(ext: str) -> str:
    if ext == ".csv":
        return "csv"
    if ext in {".parquet", ".pq"}:
        return "parquet"
    if ext in {".duckdb", ".ddb"}:
        return "duckdb"
    raise StorageError(f"unsupported dataset extension {ext!r}")


def _writer_for(backend: str):
    if backend == "csv":
        from un_comtrade.storage.file import CSVWriter
        return CSVWriter()
    if backend == "parquet":
        from un_comtrade.storage.parquet import ParquetWriter
        return ParquetWriter()
    if backend == "duckdb":
        from un_comtrade.storage.duckdb import DuckDBWriter
        return DuckDBWriter()
    raise StorageError(f"unsupported writer: {backend!r}")


def _detect_backend_name(path: Path) -> str:
    """Best-effort backend label by file extension.

    Recurses into the directory tree to find the
    first file with a recognised suffix. This
    handles partitioned parquet output (where the
    top level contains only subdirectories) that
    the SDK's own ``StorageRegistry._detect_backend``
    misses because it only inspects the first level.
    """
    if path.is_file():
        ext = path.suffix.lower()
        if ext in StorageRegistry._EXTENSION_BACKEND:
            return StorageRegistry._EXTENSION_BACKEND[ext].value
        return StorageBackend.DUCKDB.value
    if path.is_dir():
        # Recurse top-down so the first match wins.
        for child in sorted(path.rglob("*")):
            if not child.is_file():
                continue
            ext = child.suffix.lower()
            if ext in StorageRegistry._EXTENSION_BACKEND:
                return StorageRegistry._EXTENSION_BACKEND[ext].value
    return StorageBackend.DUCKDB.value


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
    parser = argparse.ArgumentParser(
        prog=RECIPE_ID, description=__doc__,
    )
    parser.add_argument(
        "source_path", type=Path,
        help="Path to a previously-stored dataset.",
    )
    parser.add_argument(
        "--build-if-missing", action="store_true",
        help="If the source is absent, fetch from the live API and write it.",
    )
    parser.add_argument(
        "--reporter", type=int, default=699,
        help="Reporter code (default: 699). Used only with --build-if-missing.",
    )
    parser.add_argument(
        "--period", default="2022",
        help='Annual period (default: "2022"). Used only with --build-if-missing.',
    )
    parser.add_argument(
        "--flow", choices=_VALID_FLOWS, default="X",
        help="Trade flow (default: X). Used only with --build-if-missing.",
    )
    args = parser.parse_args(argv)

    print("== Recipe 05: Reload from storage ==")
    print(f"Source: {args.source_path}")

    if not args.source_path.exists() and not args.build_if_missing:
        print(
            f"ERROR: source_path {args.source_path} does not exist "
            "and --build-if-missing was not set.",
            file=sys.stderr,
        )
        return EXIT_NOT_FOUND

    try:
        if args.build_if_missing and not args.source_path.exists():
            key = _require_api_key_or_none()
            if not key:
                print(
                    "ERROR: --build-if-missing requires UN_COMTRADE_KEY.",
                    file=sys.stderr,
                )
                return EXIT_AUTH
            config = Configuration(api_key=key)
            with ComtradeClient(config) as client:
                result = load_or_build_demo(
                    args.source_path,
                    client=client,
                    reporter_code=args.reporter,
                    period=args.period,
                    flow=args.flow,
                )
            print("Building dataset ...")
        else:
            print("Reloading ...")
            result = reload_demo(args.source_path)
    except ComtradeError as exc:
        code = _exit_code_for(exc)
        print(
            f"recipe={RECIPE_ID} error_class={type(exc).__name__} "
            f"message={exc} exit_code={code}",
            file=sys.stderr,
        )
        return code

    if result.built:
        print("  status : built and persisted")
    print(f"  backend : {result.backend}")
    print(f"  rows    : {result.row_count}")
    print(f"  parser  : {result.parser_name}")
    print(f"  schema  : {result.schema_version}")
    print("Done.")
    print(
        f"recipe={RECIPE_ID} backend={result.backend} "
        f"rows={result.row_count} built={result.built}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())