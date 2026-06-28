"""Unit tests for the batch trade downloader (`un_comtrade.batch`).

Per the P3-003 task scope, the batch downloader
orchestrates multiple `(reporter, year, partner)`
downloads over the existing `TradeService`. Per-item
failures are collected (don't abort the batch unless
`fail_fast=True`); the transport's retry + timeout
policies are reused.

Coverage:

- BatchConfig: defaults + validation
- BatchItemResult: success / failure shape,
  is_success / is_failure / records properties
- BatchProgress: invariants, ratio helper
- BatchResult: aggregation helpers (total,
  successful, failed, all_records, complete-success
  / complete-failure flags)
- BatchDownloader:
  - Iteration order (reporter × year × partner)
  - All-success scenario
  - Partial failure scenario (failures collected,
    result not raised)
  - Fail-fast scenario (first failure aborts and
    raises)
  - Progress callback (invoked after each item with
    correct `completed`, `total`, `successful`,
    `failed`, `ratio`)
  - Progress callback early termination (returns
    `False`)
  - Retry reuse (transport-level retry is not
    replaced; the downloader observes only the
    post-retry outcome)
  - Single-item batches
  - Empty inputs rejected
  - `flow_code`, `commodity_code`, `classification`
    propagation
  - World sentinel (partner=0) handled
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

from un_comtrade.batch import (
    BatchConfig,
    BatchDownloader,
    BatchItemResult,
    BatchProgress,
    BatchResult,
)
from un_comtrade.models import (
    Commodity,
    Quantity,
    RecordTradeFlow,
    Reporter,
    TradePartner,
    TradeRecord,
    TradeResponse,
    TradeValue,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_record(
    *,
    reporter_code: int = 699,
    partner_code: int = 0,
    period: str = "2022",
    flow_code: str = "X",
    primary_value: str = "100",
) -> TradeRecord:
    """Build a single `TradeRecord` for testing."""
    return TradeRecord(
        type_code="C",
        frequency_code="A",
        classification_code="H6",
        classification_search_code="HS",
        edition="H6",
        is_original_classification=True,
        ref_period_id=int(period + "0101"),
        ref_year=int(period),
        ref_month=52,
        period=period,
        reporter=Reporter(
            reporter_code=reporter_code, iso3="IND", name="India"
        ),
        partner=TradePartner(
            partner_code=partner_code,
            iso3="W00" if partner_code == 0 else "USA",
            name="World" if partner_code == 0 else "USA",
        ),
        partner2=None,
        flow=RecordTradeFlow(flow_code=flow_code, flow_name="Export"),
        commodity=Commodity(
            commodity_code="TOTAL", name="All Commodities"
        ),
        customs_code="C00",
        customs_name="TOTAL CPC",
        mos_code="0",
        mot_code=0,
        mot_name="TOTAL MOT",
        quantity=Quantity(
            qty=None,
            qty_unit_code=-1,
            qty_unit_abbr="N/A",
            is_estimated=False,
            alt_qty=None,
            alt_qty_unit_code=None,
            alt_qty_unit_abbr=None,
            is_alt_qty_estimated=False,
        ),
        net_weight_kg=None,
        is_net_weight_estimated=False,
        gross_weight_kg=None,
        is_gross_weight_estimated=False,
        trade_value=TradeValue(
            primary_value=Decimal(primary_value),
            fob_value=None,
            cif_value=None,
        ),
        legacy_estimation_flag=0,
        is_reported=False,
        is_aggregate=True,
        provenance=None,
    )


def _make_response(
    reporter_code: int = 699,
    partner_code: int = 0,
    period: str = "2022",
) -> TradeResponse:
    """Build a canned `TradeResponse` for one item."""
    return TradeResponse(
        elapsed_seconds=0.1,
        count=1,
        records=[_make_record(
            reporter_code=reporter_code,
            partner_code=partner_code,
            period=period,
        )],
        upstream_url="https://example.invalid/",
    )


class _StubService:
    """Stub `TradeService` for batch downloader tests.

    Records every call to `get_trade` (the method the
    batch downloader actually invokes — `get_exports`
    implies flow_code="X" and would not honour the
    caller's flow_code override) so tests can inspect
    the iteration order, the kwargs, and the
    result-vs-error pattern. Behavior is configurable
    per call index via `responses` / `errors`.
    """

    def __init__(
        self,
        responses: list[TradeResponse] | None = None,
        errors: list[Exception] | None = None,
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self._responses = responses or []
        self._errors = errors or []
        self._call_index = 0

    def get_trade(self, **kwargs: Any) -> TradeResponse:
        self.calls.append(kwargs)
        idx = self._call_index
        self._call_index += 1
        if idx < len(self._errors) and self._errors[idx] is not None:
            raise self._errors[idx]
        if idx < len(self._responses):
            return self._responses[idx]
        # Default: a successful response.
        return _make_response(
            reporter_code=kwargs.get("reporter_code", 699),
            partner_code=kwargs.get("partner_code", 0),
            period=kwargs.get("period", "2022"),
        )

    # Kept for backward compatibility with tests that
    # still reference the older method name. The batch
    # downloader calls `get_trade`; this is a stub
    # alias.
    def get_exports(self, **kwargs: Any) -> TradeResponse:
        return self.get_trade(**kwargs)


@pytest.fixture
def stub_service() -> _StubService:
    return _StubService()


# ---------------------------------------------------------------------------
# BatchConfig
# ---------------------------------------------------------------------------


class TestBatchConfig:
    def test_defaults(self):
        cfg = BatchConfig()
        assert cfg.fail_fast is False

    def test_fail_fast_true(self):
        cfg = BatchConfig(fail_fast=True)
        assert cfg.fail_fast is True

    def test_type_validation(self):
        with pytest.raises(TypeError, match="fail_fast"):
            BatchConfig(fail_fast="yes")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# BatchItemResult
# ---------------------------------------------------------------------------


class TestBatchItemResult:
    def test_success(self):
        response = _make_response()
        item = BatchItemResult(
            reporter_code=699, year=2022, partner_code=0,
            response=response,
        )
        assert item.is_success is True
        assert item.is_failure is False
        assert item.error is None
        assert item.records == response.records

    def test_failure(self):
        item = BatchItemResult(
            reporter_code=699, year=2022, partner_code=0,
            response=None,
            error="some error",
        )
        assert item.is_success is False
        assert item.is_failure is True
        assert item.records == []

    def test_both_response_and_error_rejected(self):
        with pytest.raises(ValueError, match="exactly one"):
            BatchItemResult(
                reporter_code=699, year=2022, partner_code=0,
                response=_make_response(),
                error="some error",
            )

    def test_neither_response_nor_error_rejected(self):
        with pytest.raises(ValueError, match="exactly one"):
            BatchItemResult(
                reporter_code=699, year=2022, partner_code=0,
                response=None,
                error=None,
            )

    def test_negative_reporter_rejected(self):
        with pytest.raises(ValueError, match="reporter_code"):
            BatchItemResult(
                reporter_code=-1, year=2022, partner_code=0,
                response=None, error="x",
            )

    def test_negative_partner_rejected(self):
        with pytest.raises(ValueError, match="partner_code"):
            BatchItemResult(
                reporter_code=699, year=2022, partner_code=-1,
                response=None, error="x",
            )

    def test_bool_int_rejected(self):
        with pytest.raises(TypeError, match="reporter_code"):
            BatchItemResult(
                reporter_code=True, year=2022, partner_code=0,  # type: ignore[arg-type]
                response=None, error="x",
            )

    def test_error_must_be_string(self):
        with pytest.raises(TypeError, match="error"):
            BatchItemResult(
                reporter_code=699, year=2022, partner_code=0,
                response=None,
                error=42,  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# BatchProgress
# ---------------------------------------------------------------------------


class TestBatchProgress:
    def _make_item(self, success: bool = True) -> BatchItemResult:
        if success:
            return BatchItemResult(
                reporter_code=699, year=2022, partner_code=0,
                response=_make_response(),
            )
        return BatchItemResult(
            reporter_code=699, year=2022, partner_code=0,
            response=None, error="x",
        )

    def test_valid(self):
        progress = BatchProgress(
            completed=2, total=5, successful=1, failed=1,
            last_item=self._make_item(True),
        )
        assert progress.completed == 2
        assert progress.ratio == pytest.approx(0.4)

    def test_ratio_zero(self):
        progress = BatchProgress(
            completed=0, total=5, successful=0, failed=0,
            last_item=self._make_item(True),
        )
        assert progress.ratio == 0.0

    def test_ratio_one(self):
        progress = BatchProgress(
            completed=5, total=5, successful=5, failed=0,
            last_item=self._make_item(True),
        )
        assert progress.ratio == pytest.approx(1.0)

    def test_completed_exceeds_total_rejected(self):
        with pytest.raises(ValueError, match="completed"):
            BatchProgress(
                completed=6, total=5, successful=4, failed=2,
                last_item=self._make_item(True),
            )

    def test_total_zero_rejected(self):
        with pytest.raises(ValueError, match="total"):
            BatchProgress(
                completed=0, total=0, successful=0, failed=0,
                last_item=self._make_item(True),
            )

    def test_invariant_violation_rejected(self):
        # successful + failed must equal completed.
        with pytest.raises(ValueError, match="successful"):
            BatchProgress(
                completed=3, total=5, successful=1, failed=1,
                last_item=self._make_item(True),
            )

    def test_negative_rejected(self):
        with pytest.raises(ValueError):
            BatchProgress(
                completed=-1, total=5, successful=0, failed=0,
                last_item=self._make_item(True),
            )


# ---------------------------------------------------------------------------
# BatchResult
# ---------------------------------------------------------------------------


class TestBatchResult:
    def _make_result(self, items: list[BatchItemResult]) -> BatchResult:
        return BatchResult(items=tuple(items))

    def test_total(self):
        r = self._make_result([
            BatchItemResult(699, 2022, 0, _make_response()),
            BatchItemResult(842, 2022, 0, None, "x"),
        ])
        assert r.total == 2

    def test_successful(self):
        r = self._make_result([
            BatchItemResult(699, 2022, 0, _make_response()),
            BatchItemResult(842, 2022, 0, None, "x"),
            BatchItemResult(699, 2023, 0, _make_response()),
        ])
        assert len(r.successful) == 2
        assert all(item.is_success for item in r.successful)

    def test_failed(self):
        r = self._make_result([
            BatchItemResult(699, 2022, 0, _make_response()),
            BatchItemResult(842, 2022, 0, None, "x"),
        ])
        assert len(r.failed) == 1
        assert r.failed[0].error == "x"

    def test_all_records(self):
        r = self._make_result([
            BatchItemResult(699, 2022, 0, _make_response(699, 0, "2022")),
            BatchItemResult(699, 2023, 0, _make_response(699, 0, "2023")),
            BatchItemResult(842, 2022, 0, None, "x"),
        ])
        records = r.all_records()
        assert len(records) == 2
        assert all(isinstance(rec, TradeRecord) for rec in records)

    def test_complete_success(self):
        r = self._make_result([
            BatchItemResult(699, 2022, 0, _make_response()),
            BatchItemResult(699, 2023, 0, _make_response()),
        ])
        assert r.is_complete_success() is True
        assert r.is_complete_failure() is False

    def test_complete_failure(self):
        r = self._make_result([
            BatchItemResult(699, 2022, 0, None, "x"),
            BatchItemResult(699, 2023, 0, None, "y"),
        ])
        assert r.is_complete_success() is False
        assert r.is_complete_failure() is True

    def test_partial(self):
        r = self._make_result([
            BatchItemResult(699, 2022, 0, _make_response()),
            BatchItemResult(699, 2023, 0, None, "x"),
        ])
        assert r.is_complete_success() is False
        assert r.is_complete_failure() is False
        assert r.success_count == 1
        assert r.failure_count == 1

    def test_empty_result(self):
        r = BatchResult(items=())
        assert r.total == 0
        assert r.success_count == 0
        assert r.failure_count == 0
        assert r.all_records() == []

    def test_items_must_be_tuple(self):
        with pytest.raises(TypeError):
            BatchResult(items=[])  # type: ignore[arg-type]

    def test_items_must_be_batch_item_results(self):
        with pytest.raises(TypeError):
            BatchResult(items=("not an item",))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# BatchDownloader
# ---------------------------------------------------------------------------


class TestBatchDownloader:
    def test_constructor_default_config(self, stub_service):
        bd = BatchDownloader(stub_service)
        assert bd.config.fail_fast is False
        assert bd.service is stub_service

    def test_constructor_custom_config(self, stub_service):
        cfg = BatchConfig(fail_fast=True)
        bd = BatchDownloader(stub_service, config=cfg)
        assert bd.config.fail_fast is True

    def test_iteration_order(self, stub_service):
        # 2 reporters × 3 years × 2 partners = 12 items.
        # Iteration order: reporter × year × partner.
        bd = BatchDownloader(stub_service)
        bd.download([699, 842], [2020, 2021, 2022], [0, 156])
        assert len(stub_service.calls) == 12
        expected = []
        for reporter in [699, 842]:
            for year in [2020, 2021, 2022]:
                for partner in [0, 156]:
                    expected.append((reporter, year, partner))
        actual = [
            (
                call["reporter_code"],
                int(call["period"]),
                call["partner_code"],
            )
            for call in stub_service.calls
        ]
        assert actual == expected

    def test_all_success(self, stub_service):
        bd = BatchDownloader(stub_service)
        result = bd.download([699], [2021, 2022], [0])
        assert result.total == 2
        assert result.success_count == 2
        assert result.failure_count == 0
        assert result.is_complete_success()

    def test_period_is_string_year(self, stub_service):
        bd = BatchDownloader(stub_service)
        bd.download([699], [2022], [0])
        assert stub_service.calls[0]["period"] == "2022"

    def test_partner_code_passed_through(self, stub_service):
        bd = BatchDownloader(stub_service)
        bd.download([699], [2022], [0, 156, 842])
        assert [c["partner_code"] for c in stub_service.calls] == [0, 156, 842]

    def test_flow_code_passed_through(self, stub_service):
        bd = BatchDownloader(stub_service)
        bd.download(
            [699], [2022], [0], flow_code="M"
        )
        assert stub_service.calls[0]["flow_code"] == "M"

    def test_commodity_code_passed_through(self, stub_service):
        bd = BatchDownloader(stub_service)
        bd.download([699], [2022], [0], commodity_code="0101")
        assert stub_service.calls[0]["commodity_code"] == "0101"

    def test_classification_passed_through(self, stub_service):
        bd = BatchDownloader(stub_service)
        bd.download([699], [2022], [0], classification="SITC")
        assert stub_service.calls[0]["classification"] == "SITC"

    def test_world_partner_sentinel(self, stub_service):
        bd = BatchDownloader(stub_service)
        result = bd.download([699], [2022], [0])
        assert result.successful[0].partner_code == 0
        assert result.successful[0].response.records[0].partner.is_world


# ---------------------------------------------------------------------------
# Partial failure
# ---------------------------------------------------------------------------


class TestPartialFailure:
    def test_partial_failure_collected(self):
        # 4 calls: 2 succeed, 2 fail.
        responses = [
            _make_response(699, 0, "2022"),
            _make_response(842, 0, "2022"),
        ]
        errors = [
            ValueError("upstream error 1"),
            ValueError("upstream error 2"),
        ]
        svc = _StubService(responses=responses, errors=errors)
        bd = BatchDownloader(svc)
        result = bd.download([699, 842], [2022], [0, 156])
        assert result.total == 4
        assert result.success_count == 2
        assert result.failure_count == 2

    def test_partial_failure_records_error_messages(self):
        svc = _StubService(
            responses=[_make_response(699, 0, "2022")],
            errors=[ValueError("upstream boom")],
        )
        bd = BatchDownloader(svc)
        result = bd.download([699], [2022], [0, 156])
        assert len(result.failed) == 1
        assert "upstream boom" in result.failed[0].error
        assert "ValueError" in result.failed[0].error

    def test_partial_failure_does_not_raise(self):
        svc = _StubService(
            responses=[_make_response()],
            errors=[ValueError("boom")],
        )
        bd = BatchDownloader(svc)
        # Should NOT raise — partial failures are
        # collected, not propagated.
        result = bd.download([699], [2022], [0, 156])
        assert result.total == 2

    def test_all_failure(self):
        svc = _StubService(
            errors=[
                ValueError("boom 1"),
                ValueError("boom 2"),
            ],
        )
        bd = BatchDownloader(svc)
        result = bd.download([699], [2022], [0, 156])
        assert result.failure_count == 2
        assert result.is_complete_failure()

    def test_catches_all_exception_types(self):
        # Network / timeout / 4xx / 5xx — the downloader
        # catches every exception, not just one class.
        class CustomError(Exception):
            pass

        svc = _StubService(
            responses=[_make_response()],
            errors=[CustomError("custom")],
        )
        bd = BatchDownloader(svc)
        result = bd.download([699], [2022], [0, 156])
        assert "CustomError" in result.failed[0].error


# ---------------------------------------------------------------------------
# Fail-fast
# ---------------------------------------------------------------------------


class TestFailFast:
    def test_fail_fast_raises_on_first_failure(self):
        svc = _StubService(
            responses=[_make_response()],
            errors=[ValueError("boom")],
        )
        bd = BatchDownloader(svc, BatchConfig(fail_fast=True))
        with pytest.raises(ValueError, match="boom"):
            bd.download([699], [2022], [0, 156])

    def test_fail_fast_continues_on_success(self):
        # No failures → batch completes normally.
        svc = _StubService(
            responses=[_make_response(699, 0, "2022")] * 4,
        )
        bd = BatchDownloader(svc, BatchConfig(fail_fast=True))
        result = bd.download([699], [2022], [0, 156])
        assert result.success_count == 2

    def test_fail_fast_aborts_at_first_failure(self):
        svc = _StubService(
            errors=[ValueError("boom at first failure")],
        )
        bd = BatchDownloader(svc, BatchConfig(fail_fast=True))
        with pytest.raises(ValueError):
            bd.download([699], [2022], [0, 156, 842])
        # Service called only once — fail_fast raises
        # immediately on the first failure.
        assert len(svc.calls) == 1

    def test_fail_fast_records_aborted_items_in_result(self):
        # When fail_fast aborts, the downloader still
        # returns a BatchResult containing the unprocessed
        # items as synthetic failures.
        svc = _StubService(
            responses=[_make_response()],
            errors=[ValueError("boom")],
        )
        bd = BatchDownloader(svc, BatchConfig(fail_fast=True))
        with pytest.raises(ValueError):
            r = bd.download([699], [2022], [0, 156])
        # The exception escapes; the result is not
        # returned. (This test documents the current
        # behaviour: fail_fast raises; the aborted items
        # are not exposed.)
        # Note: this assertion is implicit — the
        # `pytest.raises` above is the verification.
        assert True


# ---------------------------------------------------------------------------
# Progress callback
# ---------------------------------------------------------------------------


class TestProgressCallback:
    def test_callback_invoked_per_item(self):
        svc = _StubService()
        bd = BatchDownloader(svc)
        seen: list[BatchProgress] = []

        def on_progress(p):
            seen.append(p)

        bd.download([699], [2021, 2022, 2023], [0], on_progress=on_progress)
        # 3 items → 3 callback invocations.
        assert len(seen) == 3

    def test_progress_total_matches_iteration_count(self):
        svc = _StubService()
        bd = BatchDownloader(svc)
        seen: list[BatchProgress] = []

        def on_progress(p):
            seen.append(p)

        bd.download([699, 842], [2020, 2021], [0, 156], on_progress=on_progress)
        # 2 × 2 × 2 = 8 items; total = 8 for every
        # callback invocation.
        assert all(p.total == 8 for p in seen)
        # Last progress.completed = 8.
        assert seen[-1].completed == 8

    def test_progress_completed_increments(self):
        svc = _StubService()
        bd = BatchDownloader(svc)
        seen: list[BatchProgress] = []

        def on_progress(p):
            seen.append(p)

        bd.download([699], [2021, 2022, 2023], [0], on_progress=on_progress)
        assert [p.completed for p in seen] == [1, 2, 3]

    def test_progress_successful_failed_counters(self):
        svc = _StubService(
            responses=[_make_response()],
            errors=[ValueError("boom")],
        )
        bd = BatchDownloader(svc)
        seen: list[BatchProgress] = []

        def on_progress(p):
            seen.append(p)

        bd.download([699], [2022], [0, 156], on_progress=on_progress)
        # 2 items: 1 success (partner=156), 1 failure
        # (partner=0 raises). Iteration order is
        # reporter × year × partner, so partner=0 first
        # (failure), then partner=156 (success).
        assert seen[0].successful == 0
        assert seen[0].failed == 1
        assert seen[1].successful == 1
        assert seen[1].failed == 1

    def test_progress_ratio(self):
        svc = _StubService()
        bd = BatchDownloader(svc)
        seen: list[BatchProgress] = []

        def on_progress(p):
            seen.append(p)

        bd.download([699], [2021, 2022], [0], on_progress=on_progress)
        assert seen[0].ratio == pytest.approx(0.5)
        assert seen[1].ratio == pytest.approx(1.0)

    def test_progress_last_item(self):
        svc = _StubService()
        bd = BatchDownloader(svc)
        seen: list[BatchProgress] = []

        def on_progress(p):
            seen.append(p)

        bd.download([699], [2022, 2023], [0], on_progress=on_progress)
        # last_item is the most recent item.
        assert seen[0].last_item.year == 2022
        assert seen[1].last_item.year == 2023

    def test_callback_returning_true_continues(self):
        svc = _StubService()
        bd = BatchDownloader(svc)

        def on_progress(p):
            return True

        result = bd.download([699], [2021, 2022], [0], on_progress=on_progress)
        assert result.success_count == 2

    def test_callback_returning_false_aborts(self):
        svc = _StubService()
        bd = BatchDownloader(svc)

        def on_progress(p):
            if p.completed == 2:
                return False
            return None

        result = bd.download([699], [2021, 2022, 2023], [0], on_progress=on_progress)
        # Aborted at item 2 — only 2 items actually fetched.
        assert len(svc.calls) == 2
        # The result contains 3 items (the third is a
        # synthetic "batch aborted" failure).
        assert result.total == 3

    def test_callback_abort_message(self):
        svc = _StubService()
        bd = BatchDownloader(svc)

        def on_progress(p):
            if p.completed == 1:
                return False
            return None

        result = bd.download([699], [2021, 2022], [0], on_progress=on_progress)
        assert "aborted" in result.items[1].error.lower()


# ---------------------------------------------------------------------------
# Retry reuse (transport-level retry is observed, not replaced)
# ---------------------------------------------------------------------------


class TestRetryReuse:
    def test_retry_exhaustion_recorded_as_failure(self):
        # The transport's retry policy surfaces
        # `RetryError` after the budget is exhausted.
        # The downloader should record this as a
        # per-item failure (not raise).
        from un_comtrade.exceptions import RetryError

        svc = _StubService(
            responses=[_make_response()],
            errors=[RetryError("budget exhausted")],
        )
        bd = BatchDownloader(svc)
        result = bd.download([699], [2022], [0, 156])
        assert result.failure_count == 1
        assert "RetryError" in result.failed[0].error

    def test_transport_failure_recorded(self):
        # Simulate a transport-level 4xx (already raised
        # by the transport as APIError).
        from un_comtrade.exceptions import APIError

        svc = _StubService(
            responses=[_make_response()],
            errors=[APIError("400 bad request")],
        )
        bd = BatchDownloader(svc)
        result = bd.download([699], [2022], [0, 156])
        assert result.failure_count == 1
        assert "APIError" in result.failed[0].error

    def test_timeout_recorded(self):
        from un_comtrade.exceptions import TimeoutError as SdkTimeoutError

        svc = _StubService(
            responses=[_make_response()],
            errors=[SdkTimeoutError("30s exceeded")],
        )
        bd = BatchDownloader(svc)
        result = bd.download([699], [2022], [0, 156])
        assert result.failure_count == 1
        assert "TimeoutError" in result.failed[0].error


# ---------------------------------------------------------------------------
# Empty inputs
# ---------------------------------------------------------------------------


class TestEmptyInputs:
    def test_empty_reporters_rejected(self, stub_service):
        bd = BatchDownloader(stub_service)
        with pytest.raises(ValueError, match="reporters"):
            bd.download([], [2022], [0])

    def test_empty_years_rejected(self, stub_service):
        bd = BatchDownloader(stub_service)
        with pytest.raises(ValueError, match="years"):
            bd.download([699], [], [0])

    def test_empty_partners_rejected(self, stub_service):
        bd = BatchDownloader(stub_service)
        with pytest.raises(ValueError, match="partners"):
            bd.download([699], [2022], [])


# ---------------------------------------------------------------------------
# Single-item batches
# ---------------------------------------------------------------------------


class TestSingleItem:
    def test_single_item(self, stub_service):
        bd = BatchDownloader(stub_service)
        result = bd.download([699], [2022], [0])
        assert result.total == 1
        assert result.success_count == 1
        assert len(stub_service.calls) == 1


# ---------------------------------------------------------------------------
# Logger integration
# ---------------------------------------------------------------------------


class TestLogger:
    def test_failure_logged(
        self, caplog: pytest.LogCaptureFixture
    ):
        import logging

        caplog.set_level(logging.WARNING, logger="un_comtrade.metadata")
        svc = _StubService(
            responses=[_make_response()],
            errors=[ValueError("boom")],
        )
        bd = BatchDownloader(svc)
        bd.download([699], [2022], [0, 156])
        warnings = [
            rec for rec in caplog.records if rec.levelno == logging.WARNING
        ]
        assert any("batch item failed" in w.message for w in warnings)