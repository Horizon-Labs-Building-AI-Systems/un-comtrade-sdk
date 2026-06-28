"""Tests for the extract layer (P4-002).

Per the P4-002 task scope, the extract layer wraps
the SDK's high-level services (MetadataService,
TradeService, BatchDownloader) and produces raw
records for the validate / transform / export stages.

Coverage:

- `TestMetadataExtractor` — wraps `MetadataService`
  method, returns canonical metadata records.
- `TestTradeExtractor` — wraps `TradeService`
  method, returns canonical TradeRecord list.
- `TestBatchExtractor` — wraps `BatchDownloader`
  `download(...)`, returns union of successful records.
- `TestExtractStageConformance` — every extractor
  implements the `ExtractStage` protocol
  (`name` + `kind` + callable).
- `TestExtractorInPipeline` — extractors plug into
  an `ETLPipeline` as the EXTRACT stage and run
  end-to-end with mock downstream stages.
- `TestExtractorEdgeCases` — bad method names,
  empty results, callable source override,
  PipelineContext integration.

All tests use stub services (no HTTP, no live API).
The stubs expose the methods the extractor expects
and return canned responses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import pytest

from un_comtrade.etl import (
    ETLPipeline,
    PipelineContext,
    PipelineStatus,
    StageKind,
    StageSpec,
)
from un_comtrade.extract import (
    BatchExtractor,
    MetadataExtractor,
    TradeExtractor,
)


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


@dataclass
class StubMetadataService:
    """Stub MetadataService for extractor tests.

    Records every method call so the test can verify
    that the extractor invoked the right method with
    the right kwargs. The stub's methods return
    canned lists (the canonical metadata models are
    out of scope for P4-002).
    """

    call_log: list[tuple[str, dict]] = field(default_factory=list)
    canned_results: dict[str, list[Any]] = field(default_factory=dict)

    def get_countries(self) -> list[Any]:
        self.call_log.append(("get_countries", {}))
        return self.canned_results.get("get_countries", [])

    def get_partners(self) -> list[Any]:
        self.call_log.append(("get_partners", {}))
        return self.canned_results.get("get_partners", [])

    def get_classifications(self) -> list[Any]:
        self.call_log.append(("get_classifications", {}))
        return self.canned_results.get("get_classifications", [])

    def get_hs_codes(self, edition: str) -> list[Any]:
        self.call_log.append(("get_hs_codes", {"edition": edition}))
        return self.canned_results.get("get_hs_codes", [])

    def get_trade_flows(self) -> list[Any]:
        self.call_log.append(("get_trade_flows", {}))
        return self.canned_results.get("get_trade_flows", [])


@dataclass
class StubTradeResponse:
    """Stub TradeResponse — has `.records` attribute."""

    records: list[Any] = field(default_factory=list)


@dataclass
class StubTradeService:
    """Stub TradeService for extractor tests."""

    call_log: list[tuple[str, dict]] = field(default_factory=list)
    canned_results: dict[str, StubTradeResponse] = field(
        default_factory=dict
    )

    def get_exports(self, **kwargs) -> StubTradeResponse:
        self.call_log.append(("get_exports", kwargs))
        return self.canned_results.get(
            "get_exports", StubTradeResponse()
        )

    def get_imports(self, **kwargs) -> StubTradeResponse:
        self.call_log.append(("get_imports", kwargs))
        return self.canned_results.get(
            "get_imports", StubTradeResponse()
        )

    def get_trade(self, **kwargs) -> StubTradeResponse:
        self.call_log.append(("get_trade", kwargs))
        return self.canned_results.get(
            "get_trade", StubTradeResponse()
        )

    def get_trade_by_hs(self, **kwargs) -> StubTradeResponse:
        self.call_log.append(("get_trade_by_hs", kwargs))
        return self.canned_results.get(
            "get_trade_by_hs", StubTradeResponse()
        )

    def get_tariffline(self, **kwargs) -> StubTradeResponse:
        self.call_log.append(("get_tariffline", kwargs))
        return self.canned_results.get(
            "get_tariffline", StubTradeResponse()
        )


@dataclass
class StubBatchItemResult:
    is_success: bool
    records: list[Any] = field(default_factory=list)
    error: BaseException | None = None


@dataclass
class StubBatchResult:
    """Stub BatchResult — has `.all_records` property."""

    items: tuple[StubBatchItemResult, ...]

    @property
    def all_records(self) -> list[Any]:
        out: list[Any] = []
        for item in self.items:
            if item.is_success:
                out.extend(item.records)
        return out

    @property
    def successful(self) -> list[StubBatchItemResult]:
        return [it for it in self.items if it.is_success]

    @property
    def failed(self) -> list[StubBatchItemResult]:
        return [it for it in self.items if not it.is_success]


@dataclass
class StubBatchDownloader:
    """Stub BatchDownloader for extractor tests."""

    call_log: list[dict] = field(default_factory=list)
    canned_results: StubBatchResult | None = None

    def download(self, **kwargs) -> StubBatchResult:
        self.call_log.append(kwargs)
        if self.canned_results is None:
            return StubBatchResult(items=())
        return self.canned_results


# ---------------------------------------------------------------------------
# MetadataExtractor
# ---------------------------------------------------------------------------


class TestMetadataExtractor:
    def test_minimal_construction(self):
        svc = StubMetadataService()
        extractor = MetadataExtractor(
            metadata_service=svc, method_name="get_countries"
        )
        assert extractor.metadata_service is svc
        assert extractor.method_name == "get_countries"
        assert extractor.method_kwargs == {}

    def test_with_kwargs(self):
        svc = StubMetadataService()
        extractor = MetadataExtractor(
            metadata_service=svc,
            method_name="get_hs_codes",
            edition="H6",
        )
        assert extractor.method_kwargs == {"edition": "H6"}

    def test_name_property(self):
        svc = StubMetadataService()
        extractor = MetadataExtractor(
            metadata_service=svc, method_name="get_countries"
        )
        assert extractor.name == "extract_metadata_get_countries"

    def test_kind_property(self):
        svc = StubMetadataService()
        extractor = MetadataExtractor(
            metadata_service=svc, method_name="get_countries"
        )
        assert extractor.kind is StageKind.EXTRACT

    def test_empty_method_name_rejected(self):
        svc = StubMetadataService()
        with pytest.raises(ValueError, match="method_name"):
            MetadataExtractor(metadata_service=svc, method_name="")

    def test_unknown_method_rejected(self):
        svc = StubMetadataService()
        with pytest.raises(ValueError, match="has no method"):
            MetadataExtractor(
                metadata_service=svc, method_name="get_nonexistent"
            )

    def test_call_invokes_metadata_service(self):
        svc = StubMetadataService()
        extractor = MetadataExtractor(
            metadata_service=svc, method_name="get_countries"
        )
        ctx = PipelineContext(pipeline_name="p")
        records = extractor(source=None, context=ctx)
        assert records == []
        assert svc.call_log == [("get_countries", {})]

    def test_call_returns_canonical_records(self):
        canonical = [{"id": "USA", "name": "United States"}]
        svc = StubMetadataService(canned_results={"get_countries": canonical})
        extractor = MetadataExtractor(
            metadata_service=svc, method_name="get_countries"
        )
        ctx = PipelineContext(pipeline_name="p")
        records = extractor(source=None, context=ctx)
        assert records == canonical

    def test_call_passes_kwargs(self):
        svc = StubMetadataService()
        extractor = MetadataExtractor(
            metadata_service=svc,
            method_name="get_hs_codes",
            edition="H5",
        )
        ctx = PipelineContext(pipeline_name="p")
        extractor(source=None, context=ctx)
        assert svc.call_log == [("get_hs_codes", {"edition": "H5"})]

    def test_call_updates_context_records(self):
        svc = StubMetadataService(
            canned_results={"get_countries": [1, 2, 3]}
        )
        extractor = MetadataExtractor(
            metadata_service=svc, method_name="get_countries"
        )
        ctx = PipelineContext(pipeline_name="p")
        extractor(source=None, context=ctx)
        assert ctx.records_in == 3
        assert ctx.records_out == 3

    def test_callable_source_overrides_method(self):
        svc = StubMetadataService()
        extractor = MetadataExtractor(
            metadata_service=svc, method_name="get_countries"
        )
        ctx = PipelineContext(pipeline_name="p")
        records = extractor(
            source=lambda s: s.get_partners(), context=ctx
        )
        # The callable invoked get_partners, NOT get_countries.
        assert svc.call_log == [("get_partners", {})]
        assert records == []


# ---------------------------------------------------------------------------
# TradeExtractor
# ---------------------------------------------------------------------------


class TestTradeExtractor:
    def test_minimal_construction(self):
        svc = StubTradeService()
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports"
        )
        assert extractor.trade_service is svc
        assert extractor.method_name == "get_exports"
        assert extractor.method_kwargs == {}

    def test_with_kwargs(self):
        svc = StubTradeService()
        extractor = TradeExtractor(
            trade_service=svc,
            method_name="get_exports",
            reporter_code=699,
            period="2022",
        )
        assert extractor.method_kwargs == {
            "reporter_code": 699,
            "period": "2022",
        }

    def test_name_property(self):
        svc = StubTradeService()
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports"
        )
        assert extractor.name == "extract_trade_get_exports"

    def test_kind_property(self):
        svc = StubTradeService()
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports"
        )
        assert extractor.kind is StageKind.EXTRACT

    def test_empty_method_name_rejected(self):
        svc = StubTradeService()
        with pytest.raises(ValueError, match="method_name"):
            TradeExtractor(trade_service=svc, method_name="")

    def test_unknown_method_rejected(self):
        svc = StubTradeService()
        with pytest.raises(ValueError, match="has no method"):
            TradeExtractor(
                trade_service=svc, method_name="get_nonexistent"
            )

    def test_call_invokes_trade_service(self):
        svc = StubTradeService()
        extractor = TradeExtractor(
            trade_service=svc,
            method_name="get_exports",
            reporter_code=699,
            period="2022",
        )
        ctx = PipelineContext(pipeline_name="p")
        extractor(source=None, context=ctx)
        assert svc.call_log == [
            (
                "get_exports",
                {"reporter_code": 699, "period": "2022"},
            )
        ]

    def test_call_returns_canonical_records(self):
        canonical = ["record1", "record2"]
        svc = StubTradeService(
            canned_results={
                "get_exports": StubTradeResponse(records=canonical)
            }
        )
        extractor = TradeExtractor(
            trade_service=svc,
            method_name="get_exports",
            reporter_code=699,
            period="2022",
        )
        ctx = PipelineContext(pipeline_name="p")
        records = extractor(source=None, context=ctx)
        assert records == canonical

    def test_call_updates_context_records(self):
        canonical = ["r1", "r2", "r3", "r4"]
        svc = StubTradeService(
            canned_results={
                "get_exports": StubTradeResponse(records=canonical)
            }
        )
        extractor = TradeExtractor(
            trade_service=svc,
            method_name="get_exports",
            reporter_code=699,
            period="2022",
        )
        ctx = PipelineContext(pipeline_name="p")
        extractor(source=None, context=ctx)
        assert ctx.records_in == 4
        assert ctx.records_out == 4

    def test_callable_source_overrides_method(self):
        svc = StubTradeService()
        extractor = TradeExtractor(
            trade_service=svc,
            method_name="get_exports",
            reporter_code=699,
            period="2022",
        )
        ctx = PipelineContext(pipeline_name="p")
        # Caller passes a callable that hits a DIFFERENT method.
        records = extractor(
            source=lambda s: s.get_tariffline(reporter_code=699),
            context=ctx,
        )
        assert svc.call_log == [
            ("get_tariffline", {"reporter_code": 699})
        ]

    def test_extract_trade_by_hs(self):
        svc = StubTradeService()
        extractor = TradeExtractor(
            trade_service=svc,
            method_name="get_trade_by_hs",
            commodity_code="71023100",
            reporter_code=699,
            flow_code="X",
            period="2022",
        )
        ctx = PipelineContext(pipeline_name="p")
        extractor(source=None, context=ctx)
        assert svc.call_log[0] == (
            "get_trade_by_hs",
            {
                "commodity_code": "71023100",
                "reporter_code": 699,
                "flow_code": "X",
                "period": "2022",
            },
        )

    def test_extract_tariffline(self):
        svc = StubTradeService()
        extractor = TradeExtractor(
            trade_service=svc,
            method_name="get_tariffline",
            reporter_code=699,
            flow_code="X",
            period="2022",
        )
        ctx = PipelineContext(pipeline_name="p")
        extractor(source=None, context=ctx)
        assert svc.call_log[0][0] == "get_tariffline"


# ---------------------------------------------------------------------------
# BatchExtractor
# ---------------------------------------------------------------------------


class TestBatchExtractor:
    def test_minimal_construction(self):
        bd = StubBatchDownloader()
        extractor = BatchExtractor(
            batch_downloader=bd,
            reporters=[699],
            years=[2022],
            partners=[0],
        )
        assert extractor.batch_downloader is bd
        assert extractor.reporters == (699,)
        assert extractor.years == (2022,)
        assert extractor.partners == (0,)
        assert extractor.flow_code == "X"
        assert extractor.commodity_code == "TOTAL"
        assert extractor.classification is None
        assert extractor.on_progress is None

    def test_with_overrides(self):
        bd = StubBatchDownloader()
        extractor = BatchExtractor(
            batch_downloader=bd,
            reporters=[699, 156],
            years=[2020, 2021, 2022],
            partners=[0, 840],
            flow_code="M",
            commodity_code="TOTAL",
            classification="HS",
            on_progress=lambda p: True,
        )
        assert extractor.flow_code == "M"
        assert extractor.classification == "HS"
        assert callable(extractor.on_progress)

    def test_name_property(self):
        bd = StubBatchDownloader()
        extractor = BatchExtractor(
            batch_downloader=bd,
            reporters=[699],
            years=[2022],
            partners=[0],
        )
        assert extractor.name == "extract_batch"

    def test_kind_property(self):
        bd = StubBatchDownloader()
        extractor = BatchExtractor(
            batch_downloader=bd,
            reporters=[699],
            years=[2022],
            partners=[0],
        )
        assert extractor.kind is StageKind.EXTRACT

    def test_sequences_normalised_to_tuples(self):
        bd = StubBatchDownloader()
        extractor = BatchExtractor(
            batch_downloader=bd,
            reporters=[699, 156],  # list
            years=[2022],
            partners=[0],
        )
        assert isinstance(extractor.reporters, tuple)
        assert isinstance(extractor.years, tuple)
        assert isinstance(extractor.partners, tuple)

    def test_call_invokes_batch_downloader(self):
        bd = StubBatchDownloader()
        extractor = BatchExtractor(
            batch_downloader=bd,
            reporters=[699],
            years=[2022],
            partners=[0],
        )
        ctx = PipelineContext(pipeline_name="p")
        extractor(source=None, context=ctx)
        assert bd.call_log == [
            {
                "reporters": (699,),
                "years": (2022,),
                "partners": (0,),
                "flow_code": "X",
                "commodity_code": "TOTAL",
            }
        ]

    def test_call_with_overrides(self):
        bd = StubBatchDownloader()
        extractor = BatchExtractor(
            batch_downloader=bd,
            reporters=[699],
            years=[2022],
            partners=[0],
            flow_code="M",
            classification="HS",
        )
        ctx = PipelineContext(pipeline_name="p")
        extractor(source=None, context=ctx)
        kwargs = bd.call_log[0]
        assert kwargs["flow_code"] == "M"
        assert kwargs["classification"] == "HS"

    def test_call_returns_all_records(self):
        result = StubBatchResult(
            items=(
                StubBatchItemResult(
                    is_success=True, records=["a", "b"]
                ),
                StubBatchItemResult(
                    is_success=True, records=["c"]
                ),
            )
        )
        bd = StubBatchDownloader(canned_results=result)
        extractor = BatchExtractor(
            batch_downloader=bd,
            reporters=[699],
            years=[2022],
            partners=[0],
        )
        ctx = PipelineContext(pipeline_name="p")
        records = extractor(source=None, context=ctx)
        assert records == ["a", "b", "c"]
        assert ctx.records_in == 3
        assert ctx.records_out == 3

    def test_call_warns_on_failed_items(self):
        result = StubBatchResult(
            items=(
                StubBatchItemResult(
                    is_success=True, records=["a"]
                ),
                StubBatchItemResult(
                    is_success=False,
                    error=RuntimeError("boom"),
                ),
                StubBatchItemResult(
                    is_success=False,
                    error=RuntimeError("also boom"),
                ),
            )
        )
        bd = StubBatchDownloader(canned_results=result)
        extractor = BatchExtractor(
            batch_downloader=bd,
            reporters=[699],
            years=[2022],
            partners=[0],
        )
        ctx = PipelineContext(pipeline_name="p")
        records = extractor(source=None, context=ctx)
        assert records == ["a"]
        assert any(
            "2 item(s) failed" in w for w in ctx.warnings
        )

    def test_empty_batch_returns_empty_list(self):
        bd = StubBatchDownloader(
            canned_results=StubBatchResult(items=())
        )
        extractor = BatchExtractor(
            batch_downloader=bd,
            reporters=[699],
            years=[2022],
            partners=[0],
        )
        ctx = PipelineContext(pipeline_name="p")
        records = extractor(source=None, context=ctx)
        assert records == []
        assert ctx.records_in == 0
        assert ctx.records_out == 0

    def test_callable_source_overrides(self):
        bd = StubBatchDownloader()
        extractor = BatchExtractor(
            batch_downloader=bd,
            reporters=[699],
            years=[2022],
            partners=[0],
        )
        ctx = PipelineContext(pipeline_name="p")
        # Override at call-time: pass a callable that
        # builds a different (reporters, years) pair.
        records = extractor(
            source=lambda b: b.download(
                reporters=[156],
                years=[2020],
                partners=[0],
            ),
            context=ctx,
        )
        assert bd.call_log[0]["reporters"] == [156]
        assert bd.call_log[0]["years"] == [2020]


# ---------------------------------------------------------------------------
# ExtractStage conformance
# ---------------------------------------------------------------------------


class TestExtractStageConformance:
    """All three extractors implement the ExtractStage
    protocol (`name` + `kind` + callable)."""

    def test_metadata_extractor_is_extract_stage(self):
        from un_comtrade.etl import ExtractStage

        svc = StubMetadataService()
        extractor = MetadataExtractor(
            metadata_service=svc, method_name="get_countries"
        )
        assert isinstance(extractor, ExtractStage)

    def test_trade_extractor_is_extract_stage(self):
        from un_comtrade.etl import ExtractStage

        svc = StubTradeService()
        extractor = TradeExtractor(
            trade_service=svc, method_name="get_exports"
        )
        assert isinstance(extractor, ExtractStage)

    def test_batch_extractor_is_extract_stage(self):
        from un_comtrade.etl import ExtractStage

        bd = StubBatchDownloader()
        extractor = BatchExtractor(
            batch_downloader=bd,
            reporters=[699],
            years=[2022],
            partners=[0],
        )
        assert isinstance(extractor, ExtractStage)

    def test_all_extractors_have_unique_names(self):
        svc_meta = StubMetadataService()
        svc_trade = StubTradeService()
        bd = StubBatchDownloader()
        e1 = MetadataExtractor(
            metadata_service=svc_meta, method_name="get_countries"
        )
        e2 = TradeExtractor(
            trade_service=svc_trade, method_name="get_exports"
        )
        e3 = BatchExtractor(
            batch_downloader=bd,
            reporters=[699],
            years=[2022],
            partners=[0],
        )
        assert e1.name != e2.name
        assert e1.name != e3.name
        assert e2.name != e3.name

    def test_all_extractors_have_extract_kind(self):
        svc_meta = StubMetadataService()
        svc_trade = StubTradeService()
        bd = StubBatchDownloader()
        e1 = MetadataExtractor(
            metadata_service=svc_meta, method_name="get_countries"
        )
        e2 = TradeExtractor(
            trade_service=svc_trade, method_name="get_exports"
        )
        e3 = BatchExtractor(
            batch_downloader=bd,
            reporters=[699],
            years=[2022],
            partners=[0],
        )
        assert e1.kind is StageKind.EXTRACT
        assert e2.kind is StageKind.EXTRACT
        assert e3.kind is StageKind.EXTRACT


# ---------------------------------------------------------------------------
# End-to-end ETL pipeline integration
# ---------------------------------------------------------------------------


class TestExtractorInPipeline:
    """Extractors plug into an ETLPipeline as the
    EXTRACT stage and run end-to-end with mock
    downstream stages."""

    def test_metadata_extractor_in_pipeline(self):
        canonical = [{"id": "IND", "name": "India"}]
        svc = StubMetadataService(
            canned_results={"get_countries": canonical}
        )
        extractor = MetadataExtractor(
            metadata_service=svc, method_name="get_countries"
        )

        # Downstream stage: identity (no transform).
        class _Identity:
            name = "validate"

            def __call__(self, input, c):
                return input

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
                    factory=lambda ctx: _Identity(),
                ),
            ),
        )
        result = pipeline.run(source=None)

        assert result.status is PipelineStatus.SUCCESS
        assert result.output == canonical
        assert svc.call_log == [("get_countries", {})]
        assert result.pipeline_name == "meta_ingest"

    def test_trade_extractor_in_pipeline(self):
        canonical = ["r1", "r2"]
        svc = StubTradeService(
            canned_results={
                "get_exports": StubTradeResponse(records=canonical)
            }
        )
        extractor = TradeExtractor(
            trade_service=svc,
            method_name="get_exports",
            reporter_code=699,
            period="2022",
        )

        class _Transform:
            name = "transform"

            def __call__(self, input, c):
                # Add a derived field to each record.
                return [{"record": r, "tag": "extracted"} for r in input]

        pipeline = ETLPipeline(
            name="trade_ingest",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name="transform",
                    kind=StageKind.TRANSFORM,
                    factory=lambda ctx: _Transform(),
                ),
            ),
        )
        result = pipeline.run(source=None)

        assert result.status is PipelineStatus.SUCCESS
        assert result.output == [
            {"record": "r1", "tag": "extracted"},
            {"record": "r2", "tag": "extracted"},
        ]
        assert svc.call_log == [
            (
                "get_exports",
                {"reporter_code": 699, "period": "2022"},
            )
        ]
        assert set(result.stage_durations.keys()) == {
            "extract_trade_get_exports",
            "transform",
        }

    def test_batch_extractor_in_pipeline(self):
        result = StubBatchResult(
            items=(
                StubBatchItemResult(
                    is_success=True, records=["r1"]
                ),
                StubBatchItemResult(
                    is_success=True, records=["r2", "r3"]
                ),
            )
        )
        bd = StubBatchDownloader(canned_results=result)
        extractor = BatchExtractor(
            batch_downloader=bd,
            reporters=[699, 156],
            years=[2022],
            partners=[0],
        )

        class _Export:
            name = "export"

            def __call__(self, input, c):
                return {"records": input, "count": len(input)}

        pipeline = ETLPipeline(
            name="batch_ingest",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
                StageSpec(
                    name="export",
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: _Export(),
                ),
            ),
        )
        result_out = pipeline.run(source=None)

        assert result_out.status is PipelineStatus.SUCCESS
        assert result_out.output == {
            "records": ["r1", "r2", "r3"],
            "count": 3,
        }
        assert len(bd.call_log) == 1
        assert bd.call_log[0]["reporters"] == (699, 156)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestExtractorEdgeCases:
    def test_metadata_extractor_kwargs_immutable(self):
        """Extractor kwargs are not mutated by the call."""
        svc = StubMetadataService()
        original = {"edition": "H6"}
        extractor = MetadataExtractor(
            metadata_service=svc,
            method_name="get_hs_codes",
            **original,
        )
        ctx = PipelineContext(pipeline_name="p")
        extractor(source=None, context=ctx)
        assert original == {"edition": "H6"}

    def test_trade_extractor_kwargs_immutable(self):
        svc = StubTradeService()
        original = {"reporter_code": 699, "period": "2022"}
        extractor = TradeExtractor(
            trade_service=svc,
            method_name="get_exports",
            **original,
        )
        ctx = PipelineContext(pipeline_name="p")
        extractor(source=None, context=ctx)
        assert original == {"reporter_code": 699, "period": "2022"}

    def test_metadata_extractor_handles_non_list(self):
        """If the canned method returns a single value
        (not a list), the extractor wraps it in a list."""
        svc = StubMetadataService()
        svc.get_countries = lambda: {"id": "USA"}  # type: ignore[assignment]
        extractor = MetadataExtractor(
            metadata_service=svc, method_name="get_countries"
        )
        ctx = PipelineContext(pipeline_name="p")
        records = extractor(source=None, context=ctx)
        # Wraps single value in a list.
        assert records == [{"id": "USA"}]

    def test_metadata_extractor_none_returns_empty(self):
        """If the canned method returns None, the
        extractor returns an empty list."""
        svc = StubMetadataService()
        svc.get_countries = lambda: None  # type: ignore[assignment]
        extractor = MetadataExtractor(
            metadata_service=svc, method_name="get_countries"
        )
        ctx = PipelineContext(pipeline_name="p")
        records = extractor(source=None, context=ctx)
        assert records == []

    def test_trade_extractor_none_returns_empty(self):
        svc = StubTradeService()
        svc.get_exports = lambda **kw: None  # type: ignore[assignment]
        extractor = TradeExtractor(
            trade_service=svc,
            method_name="get_exports",
            reporter_code=699,
            period="2022",
        )
        ctx = PipelineContext(pipeline_name="p")
        records = extractor(source=None, context=ctx)
        assert records == []

    def test_pipeline_with_only_extractor_succeeds(self):
        """A pipeline with just one EXTRACT stage
        succeeds and returns the extracted records."""
        canonical = ["r1", "r2"]
        svc = StubTradeService(
            canned_results={
                "get_exports": StubTradeResponse(records=canonical)
            }
        )
        extractor = TradeExtractor(
            trade_service=svc,
            method_name="get_exports",
            reporter_code=699,
            period="2022",
        )
        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name=extractor.name,
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: extractor,
                ),
            ),
        )
        result = pipeline.run(source=None)
        assert result.status is PipelineStatus.SUCCESS
        assert result.output == canonical

    def test_extractor_failure_short_circuits_pipeline(self):
        """An extractor that raises propagates the
        failure to the pipeline (status=FAILED)."""
        class _Broken:
            name = "broken_extractor"
            kind = StageKind.EXTRACT

            def __call__(self, input, c):
                raise RuntimeError("extractor failed")

        pipeline = ETLPipeline(
            name="p",
            stages=(
                StageSpec(
                    name="broken_extractor",
                    kind=StageKind.EXTRACT,
                    factory=lambda ctx: _Broken(),
                ),
            ),
        )
        result = pipeline.run(source=None)
        assert result.status is PipelineStatus.FAILED
        assert any("RuntimeError: extractor failed" in e for e in result.errors)

    def test_extractor_with_no_records_returns_empty(self):
        """Extractor with no records from upstream
        still updates context.records_out."""
        svc = StubMetadataService(
            canned_results={"get_countries": []}
        )
        extractor = MetadataExtractor(
            metadata_service=svc, method_name="get_countries"
        )
        ctx = PipelineContext(pipeline_name="p")
        records = extractor(source=None, context=ctx)
        assert records == []
        assert ctx.records_in == 0
        assert ctx.records_out == 0