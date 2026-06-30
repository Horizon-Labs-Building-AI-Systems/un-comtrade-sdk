"""
---
recipe_id: RECIPE-034
title: Export a TradeResponse to a DuckDB database
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
    - name: mode
      type: str
      default: "replace"
      description: ``"replace"`` (drop + recreate the table) or
        ``"append"`` (insert into the existing table).
    - name: table_name
      type: str
      default: trade_records
      description: DuckDB table to write into.
    - name: output
      type: str
      default: ./output
      description: Directory the .duckdb file is written into.
outputs:
  - kind: file
    path: output/RECIPE_034_<UTC-timestamp>.duckdb
    description: |
      DuckDB database with one row per
      ``TradeRecord`` in the
      ``trade_records`` table and a
      ``un_comtrade_datasets`` provenance table.
  - kind: stdout
    path: null
    description: Run summary (rows, table, mode, db size).
related_docs:
  - docs/011_ETL_SPECIFICATION.md
  - docs/012_STORAGE_SPECIFICATION.md
related_recipes:
  - RECIPE-031
  - RECIPE-032
  - RECIPE-033
  - RECIPE-035
tags:
  - storage
  - duckdb
  - sql
  - analytics
  - replace
  - append
---

Recipe 04 — Export a ``TradeResponse`` to a DuckDB database.

DuckDB is the in-process analytics engine
behind the SDK's bulk-write path: it accepts a
``pyarrow.Table`` and CTAS's the rows into a
typed schema, ~100× faster than per-row
``executemany`` calls. The persisted database
file is round-trippable: open it with
``duckdb.connect()`` directly, or reload it
via the storage layer (RECIPE-035).

The recipe demonstrates three DuckDB-specific
capabilities:

1. **Append vs replace modes** — set
   ``config.overwrite=False`` for append, ``True``
   for replace.
2. **Per-run dataset registration** —
   ``DuckDBWriter`` writes a row to the
   ``un_comtrade_datasets`` table for every
   ``store()`` call, so the database is
   self-documenting.
3. **Schema versioning** — the persisted
   schema is decoupled from the SDK's
   ``schema_version``; mismatches surface as a
   ``StorageError`` rather than silent drift.

Expected output (mock-mode)::

    == Recipe 04: Export to DuckDB ==
    Auth: OK (key configured)
    Reporter: 699  Period: 2022  Flow: X
    Fetching exports (T01) ...
    Building CanonicalDataset ...
      222 export records
    Writing DuckDB (replace) ...
      db     : ./output/RECIPE_034_20260629T103000Z.duckdb
      table  : trade_records
      mode   : replace
      rows   : 222
      size   : 18,403 bytes
    Done.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

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
from un_comtrade.storage.duckdb import DuckDBWriter
from un_comtrade.transform import CanonicalDataset, TradeTransformer


# ---- constants -------------------------------------------------------------

EXIT_AUTH: int = 4
RECIPE_ID: str = "RECIPE-034"
_VALID_FLOWS: tuple[str, ...] = ("X", "M")
_VALID_MODES: tuple[Literal["replace", "append"], ...] = ("replace", "append")


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

    db_path: str
    table_name: str
    mode: str
    row_count: int
    bytes_written: int
    partition_keys: tuple[tuple[Any, ...], ...]


def export_duckdb_demo(
    response: TradeResponse,
    db_path: Path,
    *,
    mode: Literal["replace", "append"] = "replace",
    table_name: str = "trade_records",
) -> ExportResult:
    """Build a dataset and write to a DuckDB database at ``db_path``.

    Parameters
    ----------
    response
        A ``TradeResponse`` envelope from the
        trade service. The test fixture injects
        a synthetic envelope.
    db_path
        Path to the ``.duckdb`` database file
        (created if missing).
    mode
        ``"replace"`` (drop + recreate the table)
        or ``"append"`` (insert into the existing
        table). Default ``"replace"``.
    table_name
        The target DuckDB table. Default
        ``"trade_records"``.

    Returns
    -------
    ExportResult
        The database path, target table, mode,
        row count, approximate database file
        size, and partition keys recorded in the
        ``un_comtrade_datasets`` provenance
        table.
    """
    dataset = build_dataset_from_responses(response, name=RECIPE_ID)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    writer = DuckDBWriter()
    config = StorageConfig(
        root=str(db_path),
        table_name=table_name,
        overwrite=(mode == "replace"),
    )
    result = writer.store(dataset, config)
    return ExportResult(
        db_path=str(db_path),
        table_name=table_name,
        mode=mode,
        row_count=result.record_count,
        bytes_written=result.byte_size or 0,
        partition_keys=tuple(result.metadata.partition_keys),
    )


# ---- query helper ----------------------------------------------------------


def query_demo(db_path: str, sql: str) -> Any:
    """Open the DB and run a read-only SQL query (helper for tests).

    Demonstrates the round-trip: after RECIPE-034
    writes the DB, RECIPE-035 (or any consumer)
    can open the file with ``duckdb.connect()``
    directly and query the persisted rows. The
    return value is whatever
    ``conn.execute(sql).fetchall()`` produces —
    list[tuple] for non-pyarrow backends.
    """
    import duckdb  # local import to keep duckdb optional
    conn = duckdb.connect(db_path, read_only=True)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


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
        "--mode", choices=_VALID_MODES, default="replace",
        help='DuckDB write mode (default: "replace").',
    )
    parser.add_argument(
        "--table", default="trade_records",
        help="Target DuckDB table (default: trade_records).",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("./output"),
        help="Output directory (default: ./output).",
    )
    args = parser.parse_args(argv)

    print("== Recipe 04: Export to DuckDB ==")
    print("Auth: OK (key configured)")
    print(
        f"Reporter: {args.reporter}  Period: {args.period}  "
        f"Flow: {args.flow}"
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    db_path = args.output / f"{RECIPE_ID}_{timestamp}.duckdb"

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
            print(f"Writing DuckDB ({args.mode}) ...")
            result = export_duckdb_demo(
                response, db_path, mode=args.mode, table_name=args.table
            )
    except ComtradeError as exc:
        code = _exit_code_for(exc)
        print(
            f"recipe={RECIPE_ID} error_class={type(exc).__name__} "
            f"message={exc} exit_code={code}",
            file=sys.stderr,
        )
        return code

    print(f"  db     : {result.db_path}")
    print(f"  table  : {result.table_name}")
    print(f"  mode   : {result.mode}")
    print(f"  rows   : {result.row_count}")
    print(f"  size   : {result.bytes_written:,} bytes")
    print("Done.")
    print(
        f"recipe={RECIPE_ID} rows={result.row_count} "
        f"table={result.table_name} mode={result.mode}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())