"""
---
recipe_id: RECIPE-031
title: Complete ETL pipeline (extract → transform → load)
category: storage
difficulty: intermediate
sdk_version: >=1.0.2
requires_api_key: yes
estimated_runtime: 1-10min
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
      description: Directory the pipeline writes the dataset to.
outputs:
  - kind: file
    path: output/RECIPE_031_<UTC-timestamp>.parquet
    description: Parquet file with one row per trade record.
  - kind: file
    path: output/RECIPE_031_<UTC-timestamp>.meta.json
    description: Pipeline provenance sidecar (per-stage timings, status, source_count).
  - kind: stdout
    path: null
    description: Per-stage timings + the headline row count.
related_docs:
  - docs/011_ETL_SPECIFICATION.md
  - docs/012_STORAGE_SPECIFICATION.md
related_recipes:
  - RECIPE-032
  - RECIPE-033
  - RECIPE-034
tags:
  - etl
  - pipeline
  - extract
  - transform
  - load
  - parquet
---

Recipe 01 — Complete ETL pipeline.

Demonstrates the full ETL stack wired together:

1. **Extract** — call ``client.trade.get_exports``
   (or ``get_imports``), wrap the response in an
   ``ExtractPayload`` carrier.
2. **Transform** — ``TradeTransformer`` parses the
   raw records into canonical ``TradeRecord``
   instances and wraps them in a
   ``CanonicalDataset``.
3. **Load** — ``ParquetWriter.store(...)`` writes
   the dataset to disk in partition-friendly
   Parquet.

The recipe builds the pipeline via
``client.etl.pipeline(name, stages)`` (the
declarative public facade), runs it against the
extract payload, and prints per-stage timings.
The pipeline never raises — failures land in
``PipelineResult.status`` and the caller decides
whether to re-raise.

The demo function takes the ``TradeResponse``
envelope + an output directory, builds the
pipeline, and runs it. The test injects a
synthetic ``TradeResponse`` and a ``tmp_path``.

Expected output (mock-mode)::

    == Recipe 01: Complete ETL Pipeline ==
    Reporter: 699  Period: 2022  Flow: X
    Building pipeline: extract -> transform -> load_parquet ...
    Running pipeline ...
    Pipeline status: SUCCESS
    Per-stage timings:
      extract       0.045s
      transform     0.012s
      load_parquet  0.038s
    Headline numbers:
      source_count  : 224
      skipped       : 2
      duplicates    : 0
      output_path   : output/RECIPE_031_20260629T103000Z.parquet
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
from un_comtrade.etl import (
    ETLFacade,
    ExportStage,
    ExtractStage,
    PipelineContext,
    PipelineResult,
    PipelineStatus,
    StageKind,
    StageSpec,
    TransformStage,
)
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
from un_comtrade.transform import TradeTransformer


# ---- constants -------------------------------------------------------------

EXIT_AUTH: int = 4
RECIPE_ID: str = "RECIPE_031"

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


# ---- stages ---------------------------------------------------------------
#
# These are minimal, focused stage classes that
# implement the Stage protocols from
# ``un_comtrade.etl``. They are local to the
# recipe — a production pipeline would import
# from a shared ``stages.py`` module.

class _ExtractFromTrade:
    """Call ``client.trade`` and emit a payload the
    next stage can consume.

    The contract: ``(context) -> TradeResponse``.
    The next stage (``_TransformToDataset``) knows
    how to parse the response into a
    ``CanonicalDataset``.
    """

    def __init__(self, *, reporter_code: int, period: str, flow: str):
        self._reporter_code = reporter_code
        self._period = period
        self._flow = flow

    def __call__(self, context: PipelineContext) -> TradeResponse:
        client = context.metadata["client"]
        if self._flow == "X":
            return client.trade.get_exports(
                reporter_code=self._reporter_code,
                period=self._period,
            )
        return client.trade.get_imports(
            reporter_code=self._reporter_code,
            period=self._period,
        )


class _TransformToDataset:
    """Convert a ``TradeResponse`` into a
    ``CanonicalDataset`` via ``TradeTransformer``."""

    def __init__(self, *, name: str):
        self._name = name

    def __call__(self, context: PipelineContext, source: TradeResponse) -> Any:
        from un_comtrade.transform import CanonicalDataset
        from un_comtrade.parser import TradeParser

        parser = TradeParser(log_skipped=False)
        transformer = TradeTransformer(parser=parser)
        # The trade transformer is itself a
        # ``TransformStage``; delegate to it.
        return transformer(source=list(source.records), context=context)


class _LoadToParquet:
    """Persist the upstream ``CanonicalDataset`` to
    Parquet via the standard writer.
    """

    def __init__(self, *, output_path: Path):
        self._output_path = output_path

    def __call__(self, context: PipelineContext, source: Any) -> dict:
        from un_comtrade.storage import StorageConfig, StorageError
        from un_comtrade.storage.parquet import ParquetWriter

        writer = ParquetWriter()
        config = StorageConfig(root=str(self._output_path))
        result = writer.store(source, config)
        return {
            "path": str(self._output_path),
            "row_count": result.row_count,
            "bytes": result.total_bytes,
            "files": result.files,
        }


# Adapt the local classes to the protocol shape
# the pipeline expects. The pipeline doesn't
# require a specific class — just that they
# implement ``__call__(context, source?)``.
# The ExtractStage protocol takes only context;
# TransformStage / ExportStage take (context,
# source).

class _TradeExtractAdapter(ExtractStage):
    """Wrap ``_ExtractFromTrade`` in the protocol."""

    def __init__(self, inner: "_ExtractFromTrade"):
        self._inner = inner
        self.name = "extract"
        self.kind = StageKind.EXTRACT

    def __call__(self, context: PipelineContext) -> TradeResponse:  # type: ignore[override]
        return self._inner(context)


class _TradeTransformAdapter(TransformStage):
    """Wrap ``_TransformToDataset`` in the protocol."""

    def __init__(self, inner: "_TransformToDataset"):
        self._inner = inner
        self.name = "transform"
        self.kind = StageKind.TRANSFORM

    def __call__(self, context: PipelineContext, source: Any) -> Any:  # type: ignore[override]
        return self._inner(context, source)


class _ParquetLoadAdapter(ExportStage):
    """Wrap ``_LoadToParquet`` in the protocol."""

    def __init__(self, inner: "_LoadToParquet"):
        self._inner = inner
        self.name = "load_parquet"
        self.kind = StageKind.EXPORT

    def __call__(self, context: PipelineContext, source: Any) -> dict:  # type: ignore[override]
        return self._inner(context, source)


# ---- demo ------------------------------------------------------------------


@dataclass(frozen=True)
class EtlPipelineResult:
    """Result envelope for the ETL pipeline demo.

    Captures the headline numbers the recipe
    prints plus the per-stage durations for
    diagnostics.
    """

    status: str
    source_count: int
    skipped: int
    duplicates_removed: int
    output_path: str
    output_row_count: int
    stage_durations: dict[str, float]


def etl_pipeline_demo(
    client: ComtradeClient,
    *,
    reporter_code: int,
    period: str,
    flow: str,
    output_path: Path,
) -> EtlPipelineResult:
    """Build and run a 3-stage ETL pipeline.

    Stages:
      1. extract       — ``_ExtractFromTrade``
      2. transform     — ``_TransformToDataset``
      3. load_parquet  — ``_LoadToParquet``

    The pipeline is constructed via
    ``client.etl.pipeline(name, stages)``; the
    facade injects the client's configuration
    into the ``PipelineContext``.

    Parameters
    ----------
    client
        A live ``ComtradeClient`` (real or with a
        mock transport).
    reporter_code
        UN Comtrade reporter code.
    period
        Annual period string.
    flow
        ``"X"`` (exports) or ``"M"`` (imports).
    output_path
        The Parquet file the load stage writes.

    Returns
    -------
    EtlPipelineResult
        Captures the pipeline status, per-stage
        durations, and headline row counts.
    """
    if flow not in _VALID_FLOWS:
        raise ValueError(
            f"flow must be one of {_VALID_FLOWS}; got {flow!r}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # The extract stage needs the client; stash it
    # on the context metadata so the closure can
    # find it.
    def _extract_factory(ctx: PipelineContext) -> _TradeExtractAdapter:
        # Stash the client on the context so the
        # adapter's ``__call__`` can reach it without
        # capturing it in a closure (which would
        # couple the adapter to a specific client).
        ctx.metadata["client"] = client
        return _TradeExtractAdapter(
            _ExtractFromTrade(
                reporter_code=reporter_code,
                period=period,
                flow=flow,
            )
        )

    stages = (
        StageSpec(
            name="extract", kind=StageKind.EXTRACT,
            factory=_extract_factory,
        ),
        StageSpec(
            name="transform", kind=StageKind.TRANSFORM,
            factory=lambda ctx: _TradeTransformAdapter(
                _TransformToDataset(name=RECIPE_ID),
            ),
        ),
        StageSpec(
            name="load_parquet", kind=StageKind.EXPORT,
            factory=lambda ctx: _ParquetLoadAdapter(
                _LoadToParquet(output_path=output_path),
            ),
        ),
    )
    pipeline = client.etl.pipeline(name=RECIPE_ID, stages=stages)
    result: PipelineResult = pipeline.run(source=None)

    return EtlPipelineResult(
        status=result.status.value,
        source_count=result.source_count,
        skipped=result.skipped,
        duplicates_removed=result.duplicates_removed,
        output_path=str(output_path),
        output_row_count=(
            result.output.get("row_count", 0)
            if isinstance(result.output, dict) else 0
        ),
        stage_durations=dict(result.stage_durations),
    )


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

    print("== Recipe 01: Complete ETL Pipeline ==")
    print(
        f"Reporter: {args.reporter}  Period: {args.period}  "
        f"Flow: {args.flow}"
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = args.output / f"{RECIPE_ID}_{timestamp}.parquet"

    config = Configuration(api_key=key)
    try:
        with ComtradeClient(config) as client:
            print(
                f"Building pipeline: extract -> transform -> "
                f"load_parquet ..."
            )
            print("Running pipeline ...")
            result = etl_pipeline_demo(
                client,
                reporter_code=args.reporter,
                period=args.period,
                flow=args.flow,
                output_path=output_path,
            )
    except ComtradeError as exc:
        code = _exit_code_for(exc)
        print(
            f"recipe={RECIPE_ID} error_class={type(exc).__name__} "
            f"message={exc} exit_code={code}",
            file=sys.stderr,
        )
        return code

    print(f"Pipeline status: {result.status}")
    print("Per-stage timings:")
    for stage_name, duration in result.stage_durations.items():
        print(f"  {stage_name:<14}  {duration:.3f}s")
    print("Headline numbers:")
    print(f"  source_count  : {result.source_count}")
    print(f"  skipped       : {result.skipped}")
    print(f"  duplicates    : {result.duplicates_removed}")
    print(f"  output_path   : {result.output_path}")
    print(f"  output rows   : {result.output_row_count}")

    # Persist a small provenance sidecar next to
    # the dataset so the consumer can audit the
    # run without re-running the pipeline.
    sidecar_path = output_path.with_suffix(".meta.json")
    sidecar = {
        "recipe_id": RECIPE_ID,
        "title": "Complete ETL pipeline",
        "category": "storage",
        "status": result.status,
        "source_count": result.source_count,
        "skipped": result.skipped,
        "duplicates_removed": result.duplicates_removed,
        "stage_durations": result.stage_durations,
        "output_path": result.output_path,
        "output_digests": {
            "data": f"sha256:{_sha256_or_empty(output_path)}"
        },
    }
    sidecar_path.write_text(
        json.dumps(sidecar, indent=2, default=str), encoding="utf-8"
    )
    print(f"  sidecar        : {sidecar_path}")
    print("Done.")
    print(
        f"recipe={RECIPE_ID} status={result.status} "
        f"rows={result.output_row_count} data={output_path.name}"
    )
    return 0 if result.status == PipelineStatus.SUCCESS.value else 8


def _sha256_or_empty(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
