"""Tests for the ETL pipeline foundation (P4-001).

Per the P4-001 task scope, the ETL module implements
**orchestration only**: the `ETLPipeline` runner,
the four stage protocols (Extract, Validate,
Transform, Export), the shared `PipelineContext`,
and the result / status types. No concrete stages
land in this task; tests therefore use mock stages
that satisfy the protocols.

Coverage:

- `TestStageKind` — enum membership and values.
- `TestStageSpec` — validation: name, kind, factory.
- `TestPipelineContext` — construction, warn/error,
  timestamp helpers.
- `TestPipelineStatus` — enum membership.
- `TestPipelineResult` — construction, defaults.
- `TestPipelineError` — derives from `ComtradeError`.
- `TestETLPipelineConstruction` — validation: name,
  stages, config, duplicate names.
- `TestETLPipelineComposition` — `with_stage`,
  `with_config`, immutability.
- `TestETLPipelineInspection` — `stage_names`,
  `stage_kinds`.
- `TestStageOrdering` — stages run in declared order;
  each stage's input is the previous stage's output.
- `TestPipelineExecution` — happy path: 4-stage
  pipeline with mock Extract / Validate / Transform /
  Export stages runs to SUCCESS and produces the
  expected output.
- `TestPipelineFailureModes` — stage raises
  `PipelineError`; stage raises generic `Exception`;
  stage factory raises; empty pipeline.
- `TestPipelineContextPassesThrough` — context is
  shared across stages; records_in / records_out
  flow correctly.
- `TestStageProtocolConformance` — protocol runtime
  checks; mock stages satisfy the right protocol.

All tests are pure-Python (no HTTP, no fixtures
beyond local mocks). All stages are constructed in
the test file — no production stage is exercised.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pytest

from un_comtrade.etl import (
    ETLPipeline,
    ExportStage,
    ExtractStage,
    PipelineContext,
    PipelineError,
    PipelineResult,
    PipelineStatus,
    Stage,
    StageKind,
    StageSpec,
    TransformStage,
    ValidateStage,
)
from un_comtrade.exceptions import ComtradeError


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _identity_stage(
    name: str, kind: StageKind
) -> StageSpec:
    """Build a StageSpec whose stage is a no-op identity
    callable that returns its input unchanged."""

    class _Stage:
        def __init__(self, name: str) -> None:
            self.name = name

        def __call__(self, input: Any, context: PipelineContext) -> Any:
            return input

    return StageSpec(name=name, kind=kind, factory=lambda ctx: _Stage(name))


def _transform_stage(
    name: str, kind: StageKind, fn: Callable[[Any, PipelineContext], Any]
) -> StageSpec:
    """Build a StageSpec whose stage applies `fn`."""

    class _Stage:
        def __init__(self, name: str) -> None:
            self.name = name

        def __call__(self, input: Any, context: PipelineContext) -> Any:
            return fn(input, context)

    return StageSpec(name=name, kind=kind, factory=lambda ctx: _Stage(name))


def _failing_stage(
    name: str, kind: StageKind, exc: BaseException
) -> StageSpec:
    """Build a StageSpec whose stage raises `exc`."""

    class _Stage:
        def __init__(self, name: str) -> None:
            self.name = name

        def __call__(self, input: Any, context: PipelineContext) -> Any:
            raise exc

    return StageSpec(name=name, kind=kind, factory=lambda ctx: _Stage(name))


# ---------------------------------------------------------------------------
# StageKind
# ---------------------------------------------------------------------------


class TestStageKind:
    def test_five_kinds(self):
        # P5-001 added STORAGE; P4-001 had four kinds.
        assert {k.value for k in StageKind} == {
            "extract",
            "validate",
            "transform",
            "export",
            "storage",
        }

    def test_extract_kind(self):
        assert StageKind.EXTRACT.value == "extract"

    def test_validate_kind(self):
        assert StageKind.VALIDATE.value == "validate"

    def test_transform_kind(self):
        assert StageKind.TRANSFORM.value == "transform"

    def test_export_kind(self):
        assert StageKind.EXPORT.value == "export"

    def test_kind_is_string(self):
        # Enum members are str-compatible (used as map keys).
        assert StageKind.EXTRACT == "extract"
        assert StageKind.EXTRACT in {"extract"}


# ---------------------------------------------------------------------------
# StageSpec
# ---------------------------------------------------------------------------


class TestStageSpec:
    def test_minimal_construction(self):
        spec = _identity_stage("s1", StageKind.EXTRACT)
        assert spec.name == "s1"
        assert spec.kind is StageKind.EXTRACT
        assert callable(spec.factory)

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError, match="name"):
            StageSpec(name="", kind=StageKind.EXTRACT, factory=lambda c: None)

    def test_whitespace_only_name_rejected(self):
        with pytest.raises(ValueError, match="name"):
            StageSpec(
                name="   ", kind=StageKind.EXTRACT, factory=lambda c: None
            )

    def test_invalid_kind_rejected(self):
        with pytest.raises(TypeError, match="kind"):
            StageSpec(
                name="s1", kind="extract", factory=lambda c: None
            )

    def test_non_callable_factory_rejected(self):
        with pytest.raises(TypeError, match="factory"):
            StageSpec(name="s1", kind=StageKind.EXTRACT, factory="not-callable")

    def test_factory_receives_context(self):
        seen_contexts: list[PipelineContext] = []

        def factory(ctx: PipelineContext) -> Stage:
            seen_contexts.append(ctx)
            return lambda input, c: input

        spec = StageSpec(
            name="s1", kind=StageKind.EXTRACT, factory=factory
        )
        pipeline = ETLPipeline(
            name="p",
            stages=(spec,),
        )
        pipeline.run(source="x")

        assert len(seen_contexts) == 1
        assert isinstance(seen_contexts[0], PipelineContext)
        assert seen_contexts[0].pipeline_name == "p"

    def test_stage_spec_is_frozen(self):
        spec = _identity_stage("s1", StageKind.EXTRACT)
        with pytest.raises(Exception):
            spec.name = "renamed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PipelineContext
# ---------------------------------------------------------------------------


class TestPipelineContext:
    def test_default_construction(self):
        ctx = PipelineContext(pipeline_name="p")
        assert ctx.pipeline_name == "p"
        assert ctx.config == {}
        assert ctx.metadata == {}
        assert ctx.warnings == []
        assert ctx.errors == []
        assert ctx.records_in == 0
        assert ctx.records_out == 0
        assert ctx.started_at is None
        assert ctx.finished_at is None
        assert ctx.stage_durations == {}

    def test_warn_appends(self):
        ctx = PipelineContext(pipeline_name="p")
        ctx.warn("row 1 has null value")
        ctx.warn("row 2 missing field")
        assert ctx.warnings == [
            "row 1 has null value",
            "row 2 missing field",
        ]

    def test_error_appends(self):
        ctx = PipelineContext(pipeline_name="p")
        ctx.error("stage 1 failed")
        ctx.error("stage 2 failed")
        assert ctx.errors == ["stage 1 failed", "stage 2 failed"]

    def test_now_returns_utc_datetime(self):
        ctx = PipelineContext(pipeline_name="p")
        t = ctx.now()
        assert t.tzinfo is not None
        assert t.tzinfo.utcoffset(t).total_seconds() == 0

    def test_records_in_out_track(self):
        ctx = PipelineContext(pipeline_name="p")
        ctx.records_in = 100
        ctx.records_out = 95
        assert ctx.records_in == 100
        assert ctx.records_out == 95

    def test_stage_durations_track(self):
        ctx = PipelineContext(pipeline_name="p")
        ctx.stage_durations["extract"] = 0.5
        ctx.stage_durations["transform"] = 0.25
        assert ctx.stage_durations == {"extract": 0.5, "transform": 0.25}


# ---------------------------------------------------------------------------
# PipelineStatus
# ---------------------------------------------------------------------------


class TestPipelineStatus:
    def test_three_statuses(self):
        assert {s.value for s in PipelineStatus} == {
            "success",
            "partial",
            "failed",
        }

    def test_success_value(self):
        assert PipelineStatus.SUCCESS.value == "success"

    def test_failed_value(self):
        assert PipelineStatus.FAILED.value == "failed"

    def test_partial_value(self):
        assert PipelineStatus.PARTIAL.value == "partial"


# ---------------------------------------------------------------------------
# PipelineResult
# ---------------------------------------------------------------------------


class TestPipelineResult:
    def test_default_construction(self):
        result = PipelineResult(
            pipeline_name="p", status=PipelineStatus.SUCCESS, output=[]
        )
        assert result.pipeline_name == "p"
        assert result.status is PipelineStatus.SUCCESS
        assert result.output == []
        assert result.warnings == []
        assert result.errors == []
        assert result.records_in == 0
        assert result.records_out == 0
        assert result.started_at is None
        assert result.finished_at is None
        assert result.stage_durations == {}

    def test_carries_full_state(self):
        result = PipelineResult(
            pipeline_name="p",
            status=PipelineStatus.FAILED,
            output={"partial": True},
            warnings=["w1"],
            errors=["e1"],
            records_in=10,
            records_out=8,
            stage_durations={"extract": 0.1, "transform": 0.2},
        )
        assert result.warnings == ["w1"]
        assert result.errors == ["e1"]
        assert result.records_in == 10
        assert result.records_out == 8
        assert result.stage_durations == {
            "extract": 0.1,
            "transform": 0.2,
        }


# ---------------------------------------------------------------------------
# PipelineError
# ---------------------------------------------------------------------------


class TestPipelineError:
    def test_inherits_from_comtrade_error(self):
        err = PipelineError("stage failed")
        assert isinstance(err, ComtradeError)

    def test_message(self):
        err = PipelineError("stage failed")
        assert str(err) == "stage failed"

    def test_can_be_raised_and_caught(self):
        with pytest.raises(PipelineError):
            raise PipelineError("boom")


# ---------------------------------------------------------------------------
# ETLPipeline construction
# ---------------------------------------------------------------------------


class TestETLPipelineConstruction:
    def test_minimal_construction(self):
        pipeline = ETLPipeline(name="p", stages=())
        assert pipeline.name == "p"
        assert pipeline.stages == ()
        assert pipeline.config == {}

    def test_with_stages_and_config(self):
        s1 = _identity_stage("extract", StageKind.EXTRACT)
        s2 = _identity_stage("transform", StageKind.TRANSFORM)
        pipeline = ETLPipeline(
            name="p", stages=(s1, s2), config={"batch_size": 1000}
        )
        assert pipeline.name == "p"
        assert pipeline.stages == (s1, s2)
        assert pipeline.config == {"batch_size": 1000}

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError, match="name"):
            ETLPipeline(name="", stages=())

    def test_whitespace_only_name_rejected(self):
        with pytest.raises(ValueError, match="name"):
            ETLPipeline(name="   ", stages=())

    def test_non_stagespec_rejected(self):
        with pytest.raises(TypeError, match="StageSpec"):
            ETLPipeline(
                name="p", stages=("not-a-stagespec",)  # type: ignore[arg-type]
            )

    def test_duplicate_stage_name_rejected(self):
        s1 = _identity_stage("dup", StageKind.EXTRACT)
        s2 = _identity_stage("dup", StageKind.VALIDATE)
        with pytest.raises(ValueError, match="Duplicate stage name"):
            ETLPipeline(name="p", stages=(s1, s2))

    def test_config_must_be_mapping(self):
        with pytest.raises(TypeError, match="config"):
            ETLPipeline(
                name="p", stages=(), config="not-a-mapping"  # type: ignore[arg-type]
            )

    def test_list_of_stages_normalised_to_tuple(self):
        s1 = _identity_stage("extract", StageKind.EXTRACT)
        s2 = _identity_stage("transform", StageKind.TRANSFORM)
        pipeline = ETLPipeline(name="p", stages=[s1, s2])
        assert isinstance(pipeline.stages, tuple)
        assert pipeline.stages == (s1, s2)


# ---------------------------------------------------------------------------
# ETLPipeline composition (with_stage, with_config)
# ---------------------------------------------------------------------------


class TestETLPipelineComposition:
    def test_with_stage_appends(self):
        p1 = ETLPipeline(name="p", stages=())
        s1 = _identity_stage("extract", StageKind.EXTRACT)
        p2 = p1.with_stage(s1)
        assert p1.stages == ()
        assert p2.stages == (s1,)

    def test_with_stage_chains(self):
        s1 = _identity_stage("extract", StageKind.EXTRACT)
        s2 = _identity_stage("transform", StageKind.TRANSFORM)
        s3 = _identity_stage("export", StageKind.EXPORT)
        p = (
            ETLPipeline(name="p", stages=())
            .with_stage(s1)
            .with_stage(s2)
            .with_stage(s3)
        )
        assert p.stage_names == ("extract", "transform", "export")

    def test_with_stage_rejects_non_stagespec(self):
        p = ETLPipeline(name="p", stages=())
        with pytest.raises(TypeError, match="StageSpec"):
            p.with_stage("not a spec")  # type: ignore[arg-type]

    def test_with_stage_returns_new_instance(self):
        s1 = _identity_stage("extract", StageKind.EXTRACT)
        p1 = ETLPipeline(name="p", stages=())
        p2 = p1.with_stage(s1)
        assert p1 is not p2

    def test_with_config_overrides(self):
        p1 = ETLPipeline(
            name="p", stages=(), config={"batch_size": 100, "x": 1}
        )
        p2 = p1.with_config(batch_size=500)
        assert p1.config == {"batch_size": 100, "x": 1}
        assert p2.config == {"batch_size": 500, "x": 1}

    def test_with_config_adds_new_keys(self):
        p1 = ETLPipeline(name="p", stages=(), config={"x": 1})
        p2 = p1.with_config(y=2)
        assert p2.config == {"x": 1, "y": 2}


# ---------------------------------------------------------------------------
# ETLPipeline inspection (stage_names, stage_kinds)
# ---------------------------------------------------------------------------


class TestETLPipelineInspection:
    def test_stage_names(self):
        s1 = _identity_stage("extract", StageKind.EXTRACT)
        s2 = _identity_stage("validate", StageKind.VALIDATE)
        s3 = _identity_stage("transform", StageKind.TRANSFORM)
        s4 = _identity_stage("export", StageKind.EXPORT)
        p = ETLPipeline(name="p", stages=(s1, s2, s3, s4))
        assert p.stage_names == (
            "extract",
            "validate",
            "transform",
            "export",
        )

    def test_stage_kinds(self):
        s1 = _identity_stage("extract", StageKind.EXTRACT)
        s2 = _identity_stage("validate", StageKind.VALIDATE)
        s3 = _identity_stage("transform", StageKind.TRANSFORM)
        s4 = _identity_stage("export", StageKind.EXPORT)
        p = ETLPipeline(name="p", stages=(s1, s2, s3, s4))
        assert p.stage_kinds == (
            StageKind.EXTRACT,
            StageKind.VALIDATE,
            StageKind.TRANSFORM,
            StageKind.EXPORT,
        )

    def test_stage_names_empty(self):
        p = ETLPipeline(name="p", stages=())
        assert p.stage_names == ()
        assert p.stage_kinds == ()


# ---------------------------------------------------------------------------
# Stage ordering
# ---------------------------------------------------------------------------


class TestStageOrdering:
    def test_stages_run_in_declared_order(self):
        """Each stage receives the previous stage's output
        and the shared context; stages execute in the
        declared order."""
        execution_log: list[str] = []

        def mk(name: str, value: Any) -> StageSpec:
            def factory(ctx: PipelineContext) -> Stage:
                class _S:
                    def __init__(self) -> None:
                        self.name = name

                    def __call__(self, input: Any, c: PipelineContext) -> Any:
                        execution_log.append(name)
                        return value

                return _S()

            return StageSpec(name=name, kind=StageKind.TRANSFORM, factory=factory)

        s1 = mk("first", "after-first")
        s2 = mk("second", "after-second")
        s3 = mk("third", "after-third")

        pipeline = ETLPipeline(name="p", stages=(s1, s2, s3))
        result = pipeline.run(source="start")

        assert execution_log == ["first", "second", "third"]
        assert result.output == "after-third"

    def test_each_stage_input_is_previous_output(self):
        seen_inputs: list[Any] = []

        def mk(name: str) -> StageSpec:
            def factory(ctx: PipelineContext) -> Stage:
                class _S:
                    def __init__(self) -> None:
                        self.name = name

                    def __call__(self, input: Any, c: PipelineContext) -> Any:
                        seen_inputs.append(input)
                        return f"{input}->{name}"

                return _S()

            return StageSpec(name=name, kind=StageKind.TRANSFORM, factory=factory)

        pipeline = ETLPipeline(
            name="p",
            stages=(mk("a"), mk("b"), mk("c")),
        )
        result = pipeline.run(source="source")

        assert seen_inputs == ["source", "source->a", "source->a->b"]
        assert result.output == "source->a->b->c"

    def test_source_is_first_stage_input(self):
        captured: list[Any] = []

        def factory(ctx: PipelineContext) -> Stage:
            class _S:
                name = "extract"

                def __call__(self, input: Any, c: PipelineContext) -> Any:
                    captured.append(input)
                    return input

            return _S()

        spec = StageSpec(
            name="extract", kind=StageKind.EXTRACT, factory=factory
        )
        pipeline = ETLPipeline(name="p", stages=(spec,))
        pipeline.run(source={"data": [1, 2, 3]})
        assert captured == [{"data": [1, 2, 3]}]


# ---------------------------------------------------------------------------
# Pipeline execution (happy path with mock stages)
# ---------------------------------------------------------------------------


class TestPipelineExecution:
    """End-to-end pipeline execution with mock stages
    matching the four documented stage kinds."""

    def test_four_stage_pipeline_runs_to_success(self):
        """Extract → Validate → Transform → Export runs to
        SUCCESS and produces the expected output."""

        def extract_factory(ctx: PipelineContext) -> ExtractStage:
            class _Extract:
                name = "extract"

                def __call__(self, input: Any, c: PipelineContext) -> Any:
                    # Pretend the source is a response
                    # envelope; yield its `data` array.
                    if isinstance(input, dict) and "data" in input:
                        return list(input["data"])
                    return []

            return _Extract()

        def validate_factory(ctx: PipelineContext) -> ValidateStage:
            class _Validate:
                name = "validate"

                def __call__(
                    self, input: Any, c: PipelineContext
                ) -> Any:
                    # Keep records that have a `cmdCode` key.
                    kept = [r for r in input if "cmdCode" in r]
                    dropped = len(input) - len(kept)
                    if dropped:
                        c.warn(f"validate dropped {dropped} records")
                    return kept

            return _Validate()

        def transform_factory(ctx: PipelineContext) -> TransformStage:
            class _Transform:
                name = "transform"

                def __call__(
                    self, input: Any, c: PipelineContext
                ) -> Any:
                    # Wrap each raw record in a canonical
                    # envelope (mock).
                    return [
                        {"reporter": r["reporterCode"], "code": r["cmdCode"]}
                        for r in input
                    ]

            return _Transform()

        def export_factory(ctx: PipelineContext) -> ExportStage:
            class _Export:
                name = "export"

                def __call__(self, input: Any, c: PipelineContext) -> Any:
                    # Return as a dict (canonical objects).
                    return {"records": input, "count": len(input)}

            return _Export()

        pipeline = ETLPipeline(
            name="trade_ingest",
            stages=(
                StageSpec(
                    name="extract",
                    kind=StageKind.EXTRACT,
                    factory=extract_factory,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=validate_factory,
                ),
                StageSpec(
                    name="transform",
                    kind=StageKind.TRANSFORM,
                    factory=transform_factory,
                ),
                StageSpec(
                    name="export",
                    kind=StageKind.EXPORT,
                    factory=export_factory,
                ),
            ),
        )

        source = {
            "count": 3,
            "data": [
                {"reporterCode": 699, "cmdCode": "TOTAL"},
                {"reporterCode": 699, "cmdCode": "7102"},
                {"reporterCode": 699},  # missing cmdCode → dropped
            ],
        }
        result = pipeline.run(source=source)

        assert result.status is PipelineStatus.SUCCESS
        assert result.output == {
            "records": [
                {"reporter": 699, "code": "TOTAL"},
                {"reporter": 699, "code": "7102"},
            ],
            "count": 2,
        }
        assert result.pipeline_name == "trade_ingest"
        assert result.warnings == ["validate dropped 1 records"]
        assert result.errors == []
        assert result.started_at is not None
        assert result.finished_at is not None
        assert set(result.stage_durations.keys()) == {
            "extract",
            "validate",
            "transform",
            "export",
        }

    def test_empty_pipeline_returns_source_unchanged(self):
        pipeline = ETLPipeline(name="p", stages=())
        result = pipeline.run(source={"hello": "world"})
        assert result.status is PipelineStatus.SUCCESS
        assert result.output == {"hello": "world"}
        assert result.stage_durations == {}

    def test_single_stage_pipeline(self):
        s1 = _transform_stage(
            "only", StageKind.TRANSFORM, lambda input, ctx: input + 1
        )
        pipeline = ETLPipeline(name="p", stages=(s1,))
        result = pipeline.run(source=41)
        assert result.output == 42

    def test_pipeline_does_not_mutate_config(self):
        cfg = {"x": 1}
        pipeline = ETLPipeline(name="p", stages=(), config=cfg)
        pipeline.run(source="x")
        # Original config unchanged.
        assert cfg == {"x": 1}

    def test_context_is_shared_across_stages(self):
        seen_context_ids: list[int] = []

        def mk(name: str) -> StageSpec:
            def factory(ctx: PipelineContext) -> Stage:
                seen_context_ids.append(id(ctx))

                class _S:
                    pass

                _S.name = name

                def call(self, input: Any, c: PipelineContext) -> Any:
                    c.warn(f"{name} saw context {id(c)}")
                    return input

                _S.__call__ = call  # type: ignore[attr-defined]
                return _S()

            return StageSpec(
                name=name, kind=StageKind.TRANSFORM, factory=factory
            )

        pipeline = ETLPipeline(
            name="p", stages=(mk("a"), mk("b"), mk("c"))
        )
        result = pipeline.run(source="x")

        assert len(seen_context_ids) == 3
        # All factories see the same context instance.
        assert len(set(seen_context_ids)) == 1
        # Warnings list is shared.
        assert result.warnings == [
            "a saw context " + str(seen_context_ids[0]),
            "b saw context " + str(seen_context_ids[0]),
            "c saw context " + str(seen_context_ids[0]),
        ]


# ---------------------------------------------------------------------------
# Pipeline failure modes
# ---------------------------------------------------------------------------


class TestPipelineFailureModes:
    def test_pipeline_error_short_circuits(self):
        s1 = _identity_stage("extract", StageKind.EXTRACT)
        s2 = _failing_stage(
            "validate", StageKind.VALIDATE, PipelineError("bad row")
        )
        s3 = _identity_stage("transform", StageKind.TRANSFORM)

        pipeline = ETLPipeline(name="p", stages=(s1, s2, s3))
        result = pipeline.run(source="x")

        assert result.status is PipelineStatus.FAILED
        assert (
            "stage 'validate' raised PipelineError: bad row" in result.errors
        )

    def test_generic_exception_caught_as_failure(self):
        s1 = _failing_stage(
            "extract", StageKind.EXTRACT, ValueError("oops")
        )
        pipeline = ETLPipeline(name="p", stages=(s1,))
        result = pipeline.run(source="x")

        assert result.status is PipelineStatus.FAILED
        assert "stage 'extract' raised ValueError: oops" in result.errors

    def test_failure_skips_subsequent_stages(self):
        executed: list[str] = []

        def mk(name: str) -> StageSpec:
            def factory(ctx: PipelineContext) -> Stage:
                class _S:
                    n = name

                    def __call__(self, input: Any, c: PipelineContext) -> Any:
                        executed.append(name)
                        return input

                _S.name = name
                return _S()

            return StageSpec(
                name=name, kind=StageKind.TRANSFORM, factory=factory
            )

        # Stage 2 raises; stage 3 must not run.
        def fail_factory(ctx: PipelineContext) -> Stage:
            class _Fail:
                n = "fail"

                def __call__(self, input: Any, c: PipelineContext) -> Any:
                    executed.append("fail")
                    raise PipelineError("stage 2 failed")

            _Fail.name = "fail"
            return _Fail()

        pipeline = ETLPipeline(
            name="p",
            stages=(
                mk("a"),
                StageSpec(
                    name="fail",
                    kind=StageKind.TRANSFORM,
                    factory=fail_factory,
                ),
                mk("c"),
            ),
        )
        result = pipeline.run(source="x")

        assert result.status is PipelineStatus.FAILED
        assert executed == ["a", "fail"]  # c did NOT run

    def test_stage_factory_failure_short_circuits(self):
        def broken_factory(ctx: PipelineContext) -> Stage:
            raise RuntimeError("factory broken")

        spec = StageSpec(
            name="extract",
            kind=StageKind.EXTRACT,
            factory=broken_factory,
        )
        pipeline = ETLPipeline(name="p", stages=(spec,))
        result = pipeline.run(source="x")

        assert result.status is PipelineStatus.FAILED
        assert any(
            "factory raised RuntimeError: factory broken" in e
            for e in result.errors
        )

    def test_failure_still_records_timings(self):
        s1 = _identity_stage("extract", StageKind.EXTRACT)
        s2 = _failing_stage(
            "validate", StageKind.VALIDATE, PipelineError("bad row")
        )
        pipeline = ETLPipeline(name="p", stages=(s1, s2))
        result = pipeline.run(source="x")

        # Timings are recorded for completed stages even on
        # failure of a later stage.
        assert "extract" in result.stage_durations
        assert "validate" in result.stage_durations
        assert result.stage_durations["validate"] >= 0.0

    def test_started_and_finished_always_set(self):
        pipeline = ETLPipeline(name="p", stages=())
        result = pipeline.run(source="x")
        assert result.started_at is not None
        assert result.finished_at is not None
        assert result.finished_at >= result.started_at

    def test_failure_records_started_and_finished(self):
        s1 = _failing_stage(
            "extract", StageKind.EXTRACT, PipelineError("boom")
        )
        pipeline = ETLPipeline(name="p", stages=(s1,))
        result = pipeline.run(source="x")
        assert result.started_at is not None
        assert result.finished_at is not None
        assert result.finished_at >= result.started_at


# ---------------------------------------------------------------------------
# Stage protocol conformance
# ---------------------------------------------------------------------------


class TestStageProtocolConformance:
    def test_extract_stage_is_stage(self):
        class MyExtractor:
            name = "extract"

            def __call__(self, input, context):
                return input

        instance = MyExtractor()
        assert isinstance(instance, Stage)
        assert isinstance(instance, ExtractStage)

    def test_validate_stage_is_stage(self):
        class MyValidator:
            name = "validate"

            def __call__(self, input, context):
                return input

        instance = MyValidator()
        assert isinstance(instance, Stage)
        assert isinstance(instance, ValidateStage)

    def test_transform_stage_is_stage(self):
        class MyTransformer:
            name = "transform"

            def __call__(self, input, context):
                return input

        instance = MyTransformer()
        assert isinstance(instance, Stage)
        assert isinstance(instance, TransformStage)

    def test_export_stage_is_stage(self):
        class MyExporter:
            name = "export"

            def __call__(self, input, context):
                return input

        instance = MyExporter()
        assert isinstance(instance, Stage)
        assert isinstance(instance, ExportStage)

    def test_non_stage_not_conforming(self):
        class NotAStage:
            pass

        instance = NotAStage()
        # Missing name + __call__ → fails Stage protocol.
        assert not isinstance(instance, Stage)

    def test_function_with_name_attr_conforms(self):
        def stage_fn(input, context):
            return input

        stage_fn.name = "extract"
        assert isinstance(stage_fn, Stage)
        assert isinstance(stage_fn, ExtractStage)


# ---------------------------------------------------------------------------
# Pipeline context passes through
# ---------------------------------------------------------------------------


class TestPipelineContextPassesThrough:
    def test_records_in_out_visible_to_stages(self):
        def extract_factory(ctx: PipelineContext) -> ExtractStage:
            class _E:
                name = "extract"

                def __call__(self, input, c: PipelineContext) -> Any:
                    if isinstance(input, list):
                        c.records_in = len(input)
                    return input

            return _E()

        def validate_factory(ctx: PipelineContext) -> ValidateStage:
            class _V:
                name = "validate"

                def __call__(self, input, c: PipelineContext) -> Any:
                    kept = [r for r in input if r is not None]
                    c.records_out = len(kept)
                    return kept

            return _V()

        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name="extract",
                    kind=StageKind.EXTRACT,
                    factory=extract_factory,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=validate_factory,
                ),
            ),
        )
        result = pipeline.run(source=[1, 2, None, 3, None])
        assert result.records_in == 5
        assert result.records_out == 3

    def test_warnings_collected_across_stages(self):
        def mk_warn(name: str, msg: str) -> StageSpec:
            def factory(ctx: PipelineContext) -> Stage:
                class _S:
                    pass

                _S.name = name

                def call(self, input, c: PipelineContext) -> Any:
                    c.warn(msg)
                    return input

                _S.__call__ = call  # type: ignore[attr-defined]
                return _S()

            return StageSpec(
                name=name, kind=StageKind.TRANSFORM, factory=factory
            )

        pipeline = ETLPipeline(
            name="p",
            stages=(
                mk_warn("a", "w-a"),
                mk_warn("b", "w-b"),
                mk_warn("c", "w-c"),
            ),
        )
        result = pipeline.run(source="x")
        assert result.warnings == ["w-a", "w-b", "w-c"]

    def test_config_visible_in_context(self):
        seen_config: list[dict] = []

        def factory(ctx: PipelineContext) -> Stage:
            class _S:
                name = "s"

                def __call__(self, input, c: PipelineContext) -> Any:
                    seen_config.append(dict(c.config))
                    return input

            return _S()

        pipeline = ETLPipeline(
            name="p",
            stages=(StageSpec(name="s", kind=StageKind.TRANSFORM, factory=factory),),
            config={"batch_size": 500, "tier": "gold"},
        )
        pipeline.run(source="x")
        assert seen_config == [{"batch_size": 500, "tier": "gold"}]

    def test_stage_cannot_mutate_pipeline_config(self):
        """Stages mutate `context.config` (a copy);
        the pipeline's own config stays untouched."""

        def factory(ctx: PipelineContext) -> Stage:
            class _S:
                name = "s"

                def __call__(self, input, c: PipelineContext) -> Any:
                    c.config["mutated"] = True
                    return input

            return _S()

        original_config = {"x": 1}
        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(name="s", kind=StageKind.TRANSFORM, factory=factory),
            ),
            config=original_config,
        )
        pipeline.run(source="x")
        assert "mutated" not in original_config
        assert original_config == {"x": 1}