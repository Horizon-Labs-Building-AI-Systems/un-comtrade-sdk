"""ETL Pipeline Foundation.

The ETL (Extract / Transform / Load) layer is the
highest-level orchestration layer of the SDK per
`011_ETL_SPECIFICATION.md` and
`IMPLEMENTATION_BASELINE_v1.md` §3.

This module implements **orchestration only**: it
defines the `ETLPipeline` runner, the four stage
protocols (Extract, Validate, Transform, Export),
the shared `PipelineContext`, and the result / status
types. Concrete stage implementations consume the trade
layer + metadata layer and land in later tasks; this
module does not implement any.

Pipeline shape (per `011_ETL_SPECIFICATION.md` §2 +
§12):

    Input
        |
        v
    Extract stage (kind=EXTRACT)
        |
        v
    Validate stage (kind=VALIDATE)
        |
        v
    Transform stage (kind=TRANSFORM)
        |
        v
    Export stage (kind=EXPORT)
        |
        v
    Complete

A pipeline is a tuple of `StageSpec` entries. Each
`StageSpec` carries:

- a `name` (unique within the pipeline)
- a `kind` (one of `StageKind`)
- a `factory` callable that takes the shared
  `PipelineContext` and returns the actual stage
  instance (a callable implementing one of the four
  stage protocols)

The pipeline runs the stages in declared order. The
first stage receives the caller-supplied `source`;
each subsequent stage receives the previous stage's
output. A stage failure (`PipelineError` or any
`Exception`) short-circuits the pipeline and records
the failure on the resulting `PipelineResult`.

Configuration:

- `ETLPipeline.config` is a free-form `Mapping[str, Any]`
  that the pipeline copies into `PipelineContext.config`
  before running any stage. Stages read from the
  context (not from the pipeline object directly) so
  the pipeline remains serialisable.

Concurrency:

- The MVP is **sequential** (no parallelism). Parallel
  execution is reserved for a future version per
  OQ-ETL-002.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import (
    Any,
    Callable,
    Mapping,
    MutableMapping,
    Protocol,
    Sequence,
    runtime_checkable,
)

from .exceptions import ComtradeError
from .logging import get_logger


__all__ = [
    "ETLFacade",
    "ETLPipeline",
    "ExportStage",
    "ExtractStage",
    "PipelineContext",
    "PipelineError",
    "PipelineResult",
    "PipelineStatus",
    "Stage",
    "StageKind",
    "StageSpec",
    "TransformStage",
    "ValidateStage",
]


_logger = get_logger("lifecycle")


# ---------------------------------------------------------------------------
# Stage kind
# ---------------------------------------------------------------------------


class StageKind(str, Enum):
    """The documented stage kinds.

    Per `011_ETL_SPECIFICATION.md` §2 and the P4-001
    task scope, the MVP exposes four kinds (extract,
    validate, transform, export). The full spec also
    includes normalisation, deduplication, quality
    check, and storage. `STORAGE` was added in P5-001
    (Storage Layer Foundation) to plug the storage
    layer into the ETL pipeline as a downstream stage
    that consumes the `CanonicalDataset` produced by
    the transformation layer.
    """

    EXTRACT = "extract"
    VALIDATE = "validate"
    TRANSFORM = "transform"
    EXPORT = "export"
    STORAGE = "storage"


# ---------------------------------------------------------------------------
# Stage protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class Stage(Protocol):
    """Base protocol for any pipeline stage.

    A stage is a callable that receives the previous
    stage's output (or the source, for the first
    stage) and the shared `PipelineContext`, and
    returns its own output.

    Concrete stages are callables that supply `name`
    (the stage's identifier within the pipeline) and
    implement `__call__(input, context) -> output`.
    """

    name: str

    def __call__(
        self,
        input: Any,
        context: "PipelineContext",
    ) -> Any: ...


@runtime_checkable
class ExtractStage(Stage, Protocol):
    """Extract stage protocol.

    The extract stage receives the upstream source
    (the trade layer's response, or a list of
    responses for a batch run) and produces an
    iterable of raw records. The MVP treats the
    extract stage's output as the input to the
    validate stage.
    """


@runtime_checkable
class ValidateStage(Stage, Protocol):
    """Validate stage protocol.

    The validate stage receives the raw records and
    produces the validated records. Records that fail
    validation are dropped (or quarantined, depending
    on the stage's policy) and a warning is recorded
    on the `PipelineContext`.
    """


@runtime_checkable
class TransformStage(Stage, Protocol):
    """Transform stage protocol.

    The transform stage receives the validated records
    and applies field mapping, datatype conversion,
    and code-to-name resolution. It produces canonical
    entities (`TradeRecord` instances, for the trade
    pipeline).
    """


@runtime_checkable
class ExportStage(Stage, Protocol):
    """Export stage protocol.

    The export stage receives the canonical entities
    and packages them into the requested output
    format (canonical objects by default; JSON, CSV,
    or Parquet for the serialisation exports).
    """


# ---------------------------------------------------------------------------
# StageSpec
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StageSpec:
    """Declarative specification of a single pipeline stage.

    A stage is described by its `name`, its `kind`,
    and a `factory` that builds the stage instance
    when the pipeline runs. The factory takes the
    shared `PipelineContext` so stages can pull
    configuration from it (rather than capturing
    pipeline state at construction time).

    Parameters
    ----------
    name
        Unique identifier of the stage within the
        pipeline. Used as the key for timing +
        warnings/errors.
    kind
        The stage kind. Drives documentation and
        future stage-specific behaviour.
    factory
        Callable that accepts the shared
        `PipelineContext` and returns the actual
        stage instance (a callable implementing the
        matching stage protocol).
    """

    name: str
    kind: StageKind
    factory: Callable[["PipelineContext"], Stage]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError(
                f"StageSpec.name must be a non-empty string; "
                f"got {self.name!r}"
            )
        if not isinstance(self.kind, StageKind):
            raise TypeError(
                f"StageSpec.kind must be StageKind; got "
                f"{type(self.kind).__name__}"
            )
        if not callable(self.factory):
            raise TypeError(
                f"StageSpec.factory must be callable; got "
                f"{type(self.factory).__name__}"
            )


# ---------------------------------------------------------------------------
# PipelineContext
# ---------------------------------------------------------------------------


@dataclass
class PipelineContext:
    """Mutable context threaded through every stage.

    Carries the pipeline's configuration, mutable
    metadata (counters, accumulators), warnings and
    errors, and timing info. Stages read and write
    the context freely; the pipeline copies the
    config from `ETLPipeline.config` into the
    context at run time so the pipeline remains
    serialisable.

    The context is constructed once per `run()` and
    discarded afterwards; pipeline results capture
    the relevant fields (`warnings`, `errors`,
    `records_in/out`, `stage_durations`).
    """

    pipeline_name: str
    config: MutableMapping[str, Any] = field(default_factory=dict)
    metadata: MutableMapping[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    records_in: int = 0
    records_out: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    stage_durations: MutableMapping[str, float] = field(
        default_factory=dict
    )

    def warn(self, message: str) -> None:
        """Record a row-level warning on this context."""
        self.warnings.append(message)

    def error(self, message: str) -> None:
        """Record an error on this context.

        Distinct from raising — `error()` records the
        error without interrupting execution. Raising
        `PipelineError` is the way to signal a fatal
        failure.
        """
        self.errors.append(message)

    def now(self) -> datetime:
        """Return the current UTC time.

        A small helper so stages that need to stamp
        timestamps don't reach for `datetime.now(timezone.utc)`
        directly.
        """
        return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# PipelineStatus + PipelineResult + PipelineError
# ---------------------------------------------------------------------------


class PipelineStatus(str, Enum):
    """Outcome status of a pipeline run.

    - `SUCCESS` — every stage completed without raising.
    - `FAILED` — a stage raised an unrecoverable error.
    - `PARTIAL` — reserved for future use (e.g. the
      pipeline completed with skipped / quarantined
      records). The MVP returns `SUCCESS` for any
      non-raising run; `PARTIAL` is plumbed but not
      yet emitted by `ETLPipeline.run()`.
    """

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class PipelineError(ComtradeError):
    """Raised by a stage to signal an unrecoverable failure.

    The pipeline catches this exception (or any
    subclass), records the failure on the
    `PipelineResult`, and short-circuits the run.
    Distinct from `context.error()`: raising halts the
    pipeline; `error()` merely records.
    """


@dataclass
class PipelineResult:
    """Outcome of a pipeline run.

    Captures the output, status, warnings, errors,
    record counts, and per-stage timings. The result
    is returned by `ETLPipeline.run()` even on
    failure so the caller can inspect what was
    produced before the failure.
    """

    pipeline_name: str
    status: PipelineStatus
    output: Any
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    records_in: int = 0
    records_out: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    stage_durations: MutableMapping[str, float] = field(
        default_factory=dict
    )


# ---------------------------------------------------------------------------
# ETLPipeline
# ---------------------------------------------------------------------------


@dataclass
class ETLPipeline:
    """Declarative orchestrator for an ETL pipeline.

    The pipeline is composed of a tuple of `StageSpec`
    entries. Stages run in the order declared; each
    stage receives the previous stage's output (or
    the source, for the first stage) and the shared
    `PipelineContext`.

    This is **orchestration only**: the pipeline does
    NOT implement any concrete stage. Stages are
    supplied by the caller (built by the
    `StageSpec.factory` callables). The MVP supports
    a sequential pipeline; parallel / streaming is
    reserved for future versions per OQ-ETL-002.

    Construction::

        pipeline = ETLPipeline(
            name="trade_ingest",
            stages=(
                StageSpec(
                    name="extract",
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: MyExtractor(...),
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: MyValidator(...),
                ),
                ...
            ),
            config={"batch_size": 1000},
        )

    Execution::

        result = pipeline.run(source=response_envelope)
        if result.status is PipelineStatus.SUCCESS:
            for record in result.output:
                ...
        else:
            for error in result.errors:
                ...

    Mutability:

    - `name` is required and non-empty.
    - `stages` is required and MUST be a sequence of
      `StageSpec`. The constructor accepts lists /
      tuples but freezes to a tuple.
    - `config` is a free-form mapping; the pipeline
      shallow-copies it into the `PipelineContext` at
      run time so stages cannot mutate the pipeline's
      config.

    Composition:

    - `with_stage(spec)` returns a NEW pipeline with
      the stage appended. The original is unchanged
      (the pipeline is logically immutable once
      constructed; this matches the frozen semantics
      of the SDK's other orchestrators).
    """

    name: str
    stages: tuple[StageSpec, ...]
    config: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError(
                f"ETLPipeline.name must be a non-empty string; "
                f"got {self.name!r}"
            )
        # Accept lists / sequences but force tuple.
        if not isinstance(self.stages, tuple):
            object.__setattr__(self, "stages", tuple(self.stages))
        for i, spec in enumerate(self.stages):
            if not isinstance(spec, StageSpec):
                raise TypeError(
                    f"stages[{i}] must be StageSpec; got "
                    f"{type(spec).__name__}"
                )
        # Reject duplicate stage names (timings map is
        # keyed by name; duplicates would collide).
        seen: set[str] = set()
        for spec in self.stages:
            if spec.name in seen:
                raise ValueError(
                    f"Duplicate stage name {spec.name!r} in "
                    f"pipeline {self.name!r}"
                )
            seen.add(spec.name)
        if not isinstance(self.config, Mapping):
            raise TypeError(
                f"ETLPipeline.config must be a Mapping; got "
                f"{type(self.config).__name__}"
            )

    # ----- Composition ----------------------------------------------------

    def with_stage(self, spec: StageSpec) -> "ETLPipeline":
        """Return a new pipeline with `spec` appended.

        The original pipeline is unchanged. Used to
        build pipelines incrementally.
        """
        if not isinstance(spec, StageSpec):
            raise TypeError(
                f"spec must be StageSpec; got "
                f"{type(spec).__name__}"
            )
        return ETLPipeline(
            name=self.name,
            stages=self.stages + (spec,),
            config=self.config,
        )

    def with_config(self, **overrides: Any) -> "ETLPipeline":
        """Return a new pipeline with `config` overridden.

        Original pipeline is unchanged.
        """
        new_config: dict[str, Any] = dict(self.config)
        new_config.update(overrides)
        return ETLPipeline(
            name=self.name,
            stages=self.stages,
            config=new_config,
        )

    # ----- Inspection -----------------------------------------------------

    @property
    def stage_names(self) -> tuple[str, ...]:
        """Tuple of stage names in execution order."""
        return tuple(spec.name for spec in self.stages)

    @property
    def stage_kinds(self) -> tuple[StageKind, ...]:
        """Tuple of stage kinds in execution order."""
        return tuple(spec.kind for spec in self.stages)

    # ----- Execution ------------------------------------------------------

    def run(self, source: Any) -> PipelineResult:
        """Execute the pipeline against `source`.

        Stages run in declared order. The first stage
        receives `source` as its input; subsequent
        stages receive the previous stage's output. A
        stage failure (any `Exception`) short-circuits
        the pipeline and records `FAILED` status; the
        exception is NOT re-raised so the caller can
        inspect the partial output.

        Returns a `PipelineResult` capturing output,
        warnings, errors, and per-stage timings. Even
        on failure the result is returned (with
        `status=FAILED`); the pipeline never raises
        from `run()` itself.
        """
        context = PipelineContext(
            pipeline_name=self.name,
            config=dict(self.config),
        )
        context.started_at = context.now()
        output: Any = source
        status: PipelineStatus = PipelineStatus.SUCCESS

        try:
            for spec in self.stages:
                stage_started = context.now()
                try:
                    stage = spec.factory(context)
                except Exception as exc:
                    # Factory itself failed; treat as a
                    # stage failure (the stage was never
                    # invoked).
                    context.error(
                        f"stage {spec.name!r} factory raised "
                        f"{type(exc).__name__}: {exc}"
                    )
                    status = PipelineStatus.FAILED
                    break
                try:
                    output = stage(output, context)
                except PipelineError as exc:
                    context.error(
                        f"stage {spec.name!r} raised "
                        f"PipelineError: {exc}"
                    )
                    status = PipelineStatus.FAILED
                    break
                except Exception as exc:
                    context.error(
                        f"stage {spec.name!r} raised "
                        f"{type(exc).__name__}: {exc}"
                    )
                    status = PipelineStatus.FAILED
                    break
                finally:
                    stage_finished = context.now()
                    duration = (
                        stage_finished - stage_started
                    ).total_seconds()
                    context.stage_durations[spec.name] = duration
        finally:
            context.finished_at = context.now()

        return PipelineResult(
            pipeline_name=self.name,
            status=status,
            output=output,
            warnings=list(context.warnings),
            errors=list(context.errors),
            records_in=context.records_in,
            records_out=context.records_out,
            started_at=context.started_at,
            finished_at=context.finished_at,
            stage_durations=dict(context.stage_durations),
        )


# ---------------------------------------------------------------------------
# ETLFacade — public client.etl facade (FC-001)
# ---------------------------------------------------------------------------


class ETLFacade:
    """Public facade for the ETL pipeline layer.

    Exposed via :attr:`un_comtrade.client.ComtradeClient.etl` so
    callers can build pipelines that share the client's
    :class:`un_comtrade.config.Configuration` without re-supplying
    it each time.

    Construction::

        client = ComtradeClient()
        pipeline = client.etl.pipeline(
            name="trade_ingest",
            stages=(stage_spec_a, stage_spec_b),
        )
        result = pipeline.run(source=...)

    The facade does not duplicate the ``ETLPipeline`` runner; it
    is a thin factory that injects the client's configuration.
    """

    def __init__(self, configuration: "Any") -> None:
        self._configuration = configuration

    @property
    def configuration(self) -> "Any":
        """The :class:`un_comtrade.config.Configuration` this
        facade injects into new pipelines."""
        return self._configuration

    def pipeline(
        self,
        name: str,
        stages: "tuple[StageSpec, ...] | list[StageSpec]",
    ) -> "ETLPipeline":
        """Build an :class:`ETLPipeline` that inherits the
        client's configuration.

        Parameters
        ----------
        name
            Pipeline identifier (mirrored on the resulting
            :class:`PipelineResult.pipeline_name`).
        stages
            Ordered tuple / list of :class:`StageSpec`
            entries.

        Returns
        -------
        ETLPipeline
            A ready-to-run pipeline. Call ``pipeline.run(source)``
            with the input dataset / payload.
        """
        return ETLPipeline(
            name=name,
            stages=tuple(stages),
            config=self._configuration,
        )