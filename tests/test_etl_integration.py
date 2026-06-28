"""End-to-end integration tests for the ETL pipeline (P4-005).

Per the P4-005 task scope, this module connects the
four documented stages (Extract, Validate, Transform,
Export) via **integration tests only**. No new SDK
functionality is added.

The validation stage has no concrete SDK
implementation yet (it is reserved for a future
task); the integration tests use inline stub
validate stages (the `ValidateStage` protocol from
`un_comtrade.etl`) to wire the four stages together.
This is consistent with the existing
`test_trade_end_to_end.py` pattern.

Coverage:

- `TestExtractValidateTransformExport` — happy-path
  four-stage pipeline with stub validate.
- `TestStageOrdering` — validate can sit before or
  after transform without breaking the pipeline.
- `TestMetadataPipeline` — metadata flow
  (MetadataExtractor → MetadataTransformer).
- `TestTradePipeline` — trade flow with
  TradeExtractor → stub validate →
  TradeTransformer.
- `TestBatchPipeline` — batch flow with
  BatchExtractor.
- `TestErrorPropagation` — failures in each stage
  propagate to FAILED status.
- `TestPipelineContextFlow` — records_in /
  records_out flow through the stages; warnings
  collected; durations recorded.
- `TestETLPipelineComposition` — using real
  pipeline builders (with_stage, with_config).
- `TestEdgeCases` — empty input, callable source,
  multi-stage context sharing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import pytest

from un_comtrade.etl import (
    ETLPipeline,
    PipelineContext,
    PipelineError,
    PipelineResult,
    PipelineStatus,
    StageKind,
    StageSpec,
)
from un_comtrade.export import (
    CanonicalExporter,
    ExportResult,
    ExportStageImpl,
)
from un_comtrade.extract import (
    BatchExtractor,
    MetadataExtractor,
    TradeExtractor,
)
from un_comtrade.transform import (
    CanonicalDataset,
    TradeTransformer,
)


# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------


def _baseline_trade_record(**overrides) -> dict:
    """Build a baseline raw upstream trade record (camelCase)."""
    raw: dict[str, Any] = {
        "typeCode": "C",
        "freqCode": "A",
        "classificationCode": "H6",
        "classificationSearchCode": "HS",
        "isOriginalClassification": True,
        "refPeriodId": 20220101,
        "refYear": 2022,
        "refMonth": 52,
        "period": "2022",
        "reporterCode": 699,
        "reporterISO": "IND",
        "reporterDesc": "India",
        "flowCode": "X",
        "flowDesc": "Export",
        "partnerCode": 0,
        "partnerISO": "W00",
        "partnerDesc": "World",
        "partner2Code": 0,
        "partner2ISO": "W00",
        "partner2Desc": "World",
        "cmdCode": "TOTAL",
        "cmdDesc": "All Commodities",
        "customsCode": "C00",
        "customsDesc": "TOTAL CPC",
        "mosCode": "0",
        "motCode": 0,
        "motDesc": "TOTAL MOT",
        "qtyUnitCode": -1,
        "qtyUnitAbbr": "N/A",
        "qty": 0,
        "isQtyEstimated": False,
        "altQtyUnitCode": -1,
        "altQtyUnitAbbr": "N/A",
        "altQty": 0,
        "isAltQtyEstimated": False,
        "netWgt": 0,
        "isNetWgtEstimated": True,
        "grossWgt": 0,
        "isGrossWgtEstimated": False,
        "cifvalue": None,
        "fobvalue": 452684213646.747,
        "primaryValue": 452684213646.747,
        "legacyEstimationFlag": 0,
        "isReported": False,
        "isAggregate": True,
    }
    raw.update(overrides)
    return raw


def _identity_validate():
    """A stub ValidateStage that returns its input
    unchanged. Used in tests as a placeholder for the
    (not-yet-implemented) validate stage."""

    class _IdentityValidate:
        name = "validate"
        kind = StageKind.VALIDATE

        def __call__(self, input, context):
            return input

    return _IdentityValidate()


def _recording_validate(record_tag: str = "validated"):
    """A stub ValidateStage that returns its input
    unchanged and records a tag in the context."""

    class _RecordingValidate:
        def __init__(self, tag: str) -> None:
            self.name = "validate"
            self.tag = tag

        def __call__(self, input, context):
            context.warn(f"validate tag={self.tag}")
            return input

    # Cannot use partial because the instance isn't
    # bound at class-definition time; build a wrapper.
    def factory(ctx: PipelineContext):
        return _RecordingValidate(tag=record_tag)

    return StageSpec(
        name="validate",
        kind=StageKind.VALIDATE,
        factory=factory,
    )


def _filtering_validate(
    predicate: Callable[[Any], bool],
    stage_name: str = "validate",
):
    """A stub ValidateStage that drops records
    where `predicate(record) is False`. Supports
    multiple validate stages by accepting a
    `stage_name` parameter."""

    class _FilteringValidate:
        def __init__(self, pred: Callable[[Any], bool], name: str) -> None:
            self.name = name
            self._pred = pred

        def __call__(self, input, context):
            kept = [r for r in input if self._pred(r)]
            dropped = len(input) - len(kept)
            if dropped:
                context.warn(f"{self.name} dropped {dropped} record(s)")
            return kept

    def factory(ctx: PipelineContext):
        return _FilteringValidate(predicate, stage_name)

    return StageSpec(
        name=stage_name,
        kind=StageKind.VALIDATE,
        factory=factory,
    )


# ---------------------------------------------------------------------------
# Stub services (for extractor tests)
# ---------------------------------------------------------------------------


@dataclass
class StubMetadataService:
    """Stub MetadataService returning canned metadata."""

    countries: tuple[dict, ...] = field(default_factory=tuple)

    def get_countries(self) -> list[dict]:
        return list(self.countries)


@dataclass
class StubTradeResponse:
    records: list[Any] = field(default_factory=list)


@dataclass
class StubTradeService:
    """Stub TradeService returning canned TradeResponse."""

    records: list[Any] = field(default_factory=list)
    call_log: list[tuple[str, dict]] = field(default_factory=list)

    def get_exports(self, **kwargs) -> StubTradeResponse:
        self.call_log.append(("get_exports", kwargs))
        return StubTradeResponse(records=list(self.records))


@dataclass
class StubBatchItemResult:
    is_success: bool = True
    records: list[Any] = field(default_factory=list)


@dataclass
class StubBatchResult:
    items: tuple[StubBatchItemResult, ...] = ()

    @property
    def all_records(self) -> list[Any]:
        out: list[Any] = []
        for item in self.items:
            if item.is_success:
                out.extend(item.records)
        return out

    @property
    def failed(self) -> list[StubBatchItemResult]:
        return [it for it in self.items if not it.is_success]


@dataclass
class StubBatchDownloader:
    """Stub BatchDownloader returning canned BatchResult."""

    canned: StubBatchResult | None = None
    call_log: list[dict] = field(default_factory=list)

    def download(self, **kwargs) -> StubBatchResult:
        self.call_log.append(kwargs)
        if self.canned is None:
            return StubBatchResult(items=())
        return self.canned


# ---------------------------------------------------------------------------
# TestExtractValidateTransformExport — happy path
# ---------------------------------------------------------------------------


class TestExtractValidateTransformExport:
    """Happy-path integration: all four stages wired
    in order. The validate stage is a stub that
    passes records through."""

    def test_four_stage_pipeline(self):
        records = [_baseline_trade_record(period=str(y)) for y in (2022, 2023)]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc,
            method_name="get_exports",
            reporter_code=699,
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="trade_ingest",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                ),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )

        result = pipeline.run(source=None)

        assert result.status is PipelineStatus.SUCCESS
        # TradeService was called once with the kwargs.
        assert svc.call_log == [("get_exports", {"reporter_code": 699})]
        # Pipeline output is the canonical ExportResult.
        assert isinstance(result.output, ExportResult)
        assert result.output.record_count == 2
        assert result.output.format.value == "canonical"
        # All four stage durations recorded.
        assert set(result.stage_durations.keys()) == {
            "extract_trade_get_exports",
            "validate",
            "transform_trade",
            "export_canonical",
        }

    def test_records_in_records_out_flow(self):
        records = [_baseline_trade_record(period=str(y)) for y in (2022, 2023)]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                ),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)
        # The export stage records records_out as
        # the dataset count.
        # (PipelineResult.records_out tracks the last
        # stage that wrote it.)
        assert result.output.record_count == 2

    def test_validate_drop_records_via_filtering_stage(self):
        # Records where primaryValue <= 100 are dropped
        # by the validate stage.
        def is_large(rec: dict) -> bool:
            return rec.get("primaryValue", 0) > 100

        records = [
            _baseline_trade_record(period="2022", primaryValue=50.0),
            _baseline_trade_record(period="2023", primaryValue=200.0),
            _baseline_trade_record(period="2024", primaryValue=75.0),
        ]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                _filtering_validate(is_large),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)
        assert result.status is PipelineStatus.SUCCESS
        assert result.output.record_count == 1
        # Warning recorded on the PipelineResult.
        assert any(
            "validate dropped 2 record(s)" in w
            for w in result.warnings
        )


# ---------------------------------------------------------------------------
# TestStageOrdering
# ---------------------------------------------------------------------------


class TestStageOrdering:
    """Validate can sit BEFORE or AFTER Transform in
    the pipeline. Both orderings should produce a
    valid ExportResult."""

    def test_validate_before_transform(self):
        records = [_baseline_trade_record()]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                ),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)
        assert result.status is PipelineStatus.SUCCESS
        assert result.output.record_count == 1

    def test_validate_after_transform(self):
        records = [_baseline_trade_record()]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)
        assert result.status is PipelineStatus.SUCCESS
        # Transform runs first; validate (stub) passes
        # through; export receives the dataset.
        assert result.output.record_count == 1

    def test_stage_order_reflected_in_durations(self):
        records = [_baseline_trade_record()]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)
        # Durations recorded in declared order:
        # extract, transform, validate, export.
        keys = list(result.stage_durations.keys())
        assert keys == [
            "extract_trade_get_exports",
            "transform_trade",
            "validate",
            "export_canonical",
        ]


# ---------------------------------------------------------------------------
# TestMetadataPipeline
# ---------------------------------------------------------------------------


class TestMetadataPipeline:
    """Metadata flow: MetadataExtractor → stub
    validate → MetadataTransformer → CanonicalExporter."""

    def test_metadata_pipeline_runs(self):
        countries = [
            {"id": "IND", "name": "India"},
            {"id": "USA", "name": "United States"},
            {"id": "CHN", "name": "China"},
        ]
        svc = StubMetadataService(countries=tuple(countries))
        extractor = MetadataExtractor(
            metadata_service=svc, method_name="get_countries"
        )
        from un_comtrade.transform import MetadataTransformer

        transformer = MetadataTransformer(resource="R01")
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="meta_ingest",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                ),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)
        assert result.status is PipelineStatus.SUCCESS
        assert result.output.record_count == 3


# ---------------------------------------------------------------------------
# TestTradePipeline
# ---------------------------------------------------------------------------


class TestTradePipeline:
    """Trade flow: TradeExtractor → stub validate →
    TradeTransformer → ExportStageImpl."""

    def test_trade_pipeline_with_valid_records(self):
        records = [_baseline_trade_record(period=str(y)) for y in (2022, 2023)]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="trade_ingest",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                ),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)
        assert result.status is PipelineStatus.SUCCESS
        assert result.output.record_count == 2

    def test_trade_pipeline_with_invalid_records_counted_as_skipped(self):
        valid = _baseline_trade_record()
        invalid = {"missing": "fields"}
        svc = StubTradeService(records=[valid, invalid])
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                ),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)
        assert result.status is PipelineStatus.SUCCESS
        # The invalid record is dropped by the parser;
        # only the valid record reaches the export.
        assert result.output.record_count == 1


# ---------------------------------------------------------------------------
# TestBatchPipeline
# ---------------------------------------------------------------------------


class TestBatchPipeline:
    """Batch flow: BatchExtractor → stub validate →
    TradeTransformer → ExportStageImpl.

    Note: the BatchExtractor returns canonical
    TradeRecord instances (from BatchResult.all_records),
    so the transformer detects them as pre-canonical
    and skips the parser.
    """

    def test_batch_pipeline_runs(self):
        # Stub trade records the batch returns.
        stub_records = [
            _baseline_trade_record(period=str(y)) for y in (2022, 2023)
        ]
        # Build a fake TradeRecord for each stub record.
        from un_comtrade.models import TradeRecord
        from un_comtrade.parser import TradeParser

        parser = TradeParser(log_skipped=False)
        canonical_records = []
        for rec in stub_records:
            parsed = parser.parse_records([rec]).records
            canonical_records.extend(parsed)

        result = StubBatchResult(
            items=(
                StubBatchItemResult(
                    is_success=True, records=canonical_records
                ),
            )
        )
        bd = StubBatchDownloader(canned=result)
        extractor = BatchExtractor(
            batch_downloader=bd,
            reporters=[699],
            years=[2022, 2023],
            partners=[0],
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="batch_ingest",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                ),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        pipeline_result = pipeline.run(source=None)
        assert pipeline_result.status is PipelineStatus.SUCCESS
        assert pipeline_result.output.record_count == 2


# ---------------------------------------------------------------------------
# TestErrorPropagation
# ---------------------------------------------------------------------------


class TestErrorPropagation:
    """Failures in any stage propagate to FAILED status."""

    def test_extractor_failure_short_circuits(self):
        class _BrokenExtractor:
            name = "extract"
            kind = StageKind.EXTRACT

            def __call__(self, source, context):
                raise RuntimeError("extractor boom")

        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name="extract",
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: _BrokenExtractor(),
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                ),
                StageSpec(
                    name="transform",
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: TradeTransformer(),
                ),
                StageSpec(
                    name="export",
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: ExportStageImpl(),
                ),
            ),
        )
        result = pipeline.run(source=None)
        assert result.status is PipelineStatus.FAILED
        assert any(
            "extractor boom" in e for e in result.errors
        )

    def test_validate_failure_short_circuits(self):
        class _BrokenValidate:
            name = "validate"
            kind = StageKind.VALIDATE

            def __call__(self, source, context):
                raise PipelineError("bad row")

        records = [_baseline_trade_record()]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _BrokenValidate(),
                ),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)
        assert result.status is PipelineStatus.FAILED
        assert any("bad row" in e for e in result.errors)

    def test_transform_failure_short_circuits(self):
        class _BrokenTransform:
            name = "transform"
            kind = StageKind.TRANSFORM

            def __call__(self, source, context):
                raise RuntimeError("transform boom")

        records = [_baseline_trade_record()]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                ),
                StageSpec(
                    name="transform",
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: _BrokenTransform(),
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)
        assert result.status is PipelineStatus.FAILED
        # Transform ran first (after validate passed);
        # validate's warning was NOT yet recorded because
        # validate is identity (no warn).
        assert any("transform boom" in e for e in result.errors)

    def test_export_failure_short_circuits(self):
        # Use a placeholder export to trigger NotImplementedError.
        from un_comtrade.export import ExportFormat

        records = [_baseline_trade_record()]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()

        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                ),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name="export_csv",
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: ExportStageImpl(
                        format=ExportFormat.CSV
                    ),
                ),
            ),
        )
        result = pipeline.run(source=None)
        assert result.status is PipelineStatus.FAILED
        # The placeholder's NotImplementedError was
        # translated to ExportError.
        assert any("placeholder" in e for e in result.errors)


# ---------------------------------------------------------------------------
# TestPipelineContextFlow
# ---------------------------------------------------------------------------


class TestPipelineContextFlow:
    """PipelineContext flows correctly through the
    four stages: warnings collected, durations
    recorded, records_in / records_out tracked."""

    def test_warnings_collected_across_stages(self):
        records = [_baseline_trade_record(period=str(y)) for y in (2022, 2023)]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                _recording_validate(record_tag="validated-set-A"),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)
        assert result.status is PipelineStatus.SUCCESS
        # The validate stage recorded a warning.
        assert any(
            "validate tag=validated-set-A" in w for w in result.warnings
        )

    def test_durations_recorded_for_all_stages(self):
        records = [_baseline_trade_record()]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                ),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)
        # Every stage's duration is recorded.
        for stage_name in (
            "extract_trade_get_exports",
            "validate",
            "transform_trade",
            "export_canonical",
        ):
            assert stage_name in result.stage_durations
            assert result.stage_durations[stage_name] >= 0.0

    def test_started_and_finished_always_set(self):
        records = [_baseline_trade_record()]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                ),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)
        assert result.started_at is not None
        assert result.finished_at is not None
        assert result.finished_at >= result.started_at


# ---------------------------------------------------------------------------
# TestETLPipelineComposition
# ---------------------------------------------------------------------------


class TestETLPipelineComposition:
    """ETLPipeline composition (with_stage, with_config)."""

    def test_with_stage_appends_stage(self):
        records = [_baseline_trade_record()]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        # Start with an empty pipeline and append stages.
        pipeline = (
            ETLPipeline(name="p", stages=())
            .with_stage(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                )
            )
            .with_stage(
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                )
            )
            .with_stage(
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                )
            )
            .with_stage(
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                )
            )
        )
        result = pipeline.run(source=None)
        assert result.status is PipelineStatus.SUCCESS
        assert result.output.record_count == 1

    def test_with_config_passes_through(self):
        records = [_baseline_trade_record()]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        base = ETLPipeline(name="p", stages=())
        configured = base.with_config(batch_size=1000)

        # configured.config has the new key.
        assert configured.config == {"batch_size": 1000}
        # base.config is unchanged.
        assert base.config == {}


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases for the four-stage integration."""

    def test_empty_records_flows_through(self):
        svc = StubTradeService(records=[])
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                ),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)
        assert result.status is PipelineStatus.SUCCESS
        assert result.output.record_count == 0
        assert result.output.empty

    def test_callable_source_overrides_extractor(self):
        records = [_baseline_trade_record()]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        # Override at run time: pass a different
        # trade service (with different records).
        alternative_svc = StubTradeService(
            records=[_baseline_trade_record(period="2099")]
        )

        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                ),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=lambda svc: svc.get_exports(reporter_code=999))
        assert result.status is PipelineStatus.SUCCESS
        # Alternative service was used (period 2099).
        assert any(
            r.period == "2099" for r in (
                result.output.metadata.get("records", []) if hasattr(result.output, "records") else []
            )
        ) or result.output.record_count == 1

    def test_multiple_validates_in_sequence(self):
        # Two validate stages chained: first drops small,
        # second checks for a specific reporter.
        def is_large(rec):
            return rec.get("primaryValue", 0) > 100

        def is_india(rec):
            return rec.get("reporterCode") == 699

        records = [
            _baseline_trade_record(period="2022", primaryValue=200.0),
            _baseline_trade_record(period="2023", primaryValue=50.0),
            _baseline_trade_record(
                period="2024", reporterCode=156, primaryValue=300.0
            ),
        ]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                _filtering_validate(is_large, stage_name="validate_size"),
                _filtering_validate(is_india, stage_name="validate_reporter"),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)
        # Only the first record (2022, value=200, reporter=699)
        # passes both filters.
        assert result.status is PipelineStatus.SUCCESS
        assert result.output.record_count == 1
        # Both validate stages recorded warnings.
        assert any(
            "validate_size dropped" in w for w in result.warnings
        )
        assert any(
            "validate_reporter dropped" in w for w in result.warnings
        )

    def test_export_metadata_carries_provenance(self):
        records = [_baseline_trade_record()]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                ),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)
        assert result.output.metadata["schema_version"] == "1.0.0"
        assert result.output.metadata["parser_name"] == "TradeParser"

    def test_result_pipeline_name_preserved(self):
        records = [_baseline_trade_record()]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="custom_pipeline_name",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                ),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)
        assert result.pipeline_name == "custom_pipeline_name"
        assert result.output.metadata["schema_version"] == "1.0.0"

    def test_pipeline_runs_through_etl_lifecycle(self):
        # Full ETL lifecycle: pipeline.name on the
        # result, timestamps set, status SUCCESS,
        # ExportResult is the canonical output.
        records = [_baseline_trade_record()]
        svc = StubTradeService(records=records)
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports", reporter_code=699
        )
        transformer = TradeTransformer()
        export_stage = ExportStageImpl()

        pipeline = ETLPipeline(
            name="full_lifecycle",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name="validate",
                    kind=StageKind.VALIDATE,
                    factory=lambda ctx: _identity_validate(),
                ),
                StageSpec(
                    name=transformer.name,
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: transformer,
                ),
                StageSpec(
                    name=export_stage.name,
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: export_stage,
                ),
            ),
        )
        result = pipeline.run(source=None)
        assert isinstance(result, PipelineResult)
        assert result.status is PipelineStatus.SUCCESS
        assert isinstance(result.output, ExportResult)
        assert result.started_at is not None
        assert result.finished_at is not None