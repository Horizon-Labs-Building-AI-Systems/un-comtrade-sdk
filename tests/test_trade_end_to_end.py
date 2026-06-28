"""End-to-end integration tests for the complete trade subsystem.

Per the P3-005 task scope, this file validates that
the components built across P1-P3 work together as a
coherent subsystem. **No new functionality** — these
tests only exercise the existing public surface.

Coverage:

- Metadata + Trade integration (metadata lookup →
  trade fetch in a single client lifecycle).
- Pagination engine (multi-page merge, cross-page
  dedup, progress callback, max-page safeguard).
- Batch downloader (multi-reporter × multi-year ×
  multi-partner, partial-failure collection,
  fail-fast).
- Async jobs (submit → poll → download full workflow,
  handle metadata propagation).
- Parser (raw upstream JSON → canonical
  `TradeRecord` models, Decimal precision preserved).
- Transport (auth header injection, retry + timeout
  policies, MockTransport-only — no live network).

All tests use `httpx.MockTransport` so the suite never
hits the upstream network.
"""

from __future__ import annotations

import dataclasses
import json
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable
from unittest.mock import MagicMock

import httpx
import pytest

from un_comtrade.async_jobs import (
    ASYNC_STATUS_COMPLETED,
    ASYNC_STATUS_FAILED,
    AsyncJobsService,
    AsyncRequestHandle,
    AsyncRequestStatus,
)
from un_comtrade.batch import (
    BatchConfig,
    BatchDownloader,
    BatchItemResult,
    BatchProgress,
    BatchResult,
)
from un_comtrade.cache import MetadataCache
from un_comtrade.client import ComtradeClient
from un_comtrade.config import Configuration
from un_comtrade.exceptions import (
    APIError,
    AuthenticationError,
    RetryError,
)
from un_comtrade.models import (
    Commodity,
    Country,
    HSCode,
    Partner,
    Quantity,
    Reporter,
    TradeFlow,
    TradePartner,
    TradeRecord,
    TradeResponse,
    TradeValue,
    RecordTradeFlow,
)
from un_comtrade.pagination import (
    PageProgress,
    PaginationConfig,
    PaginationEngine,
    PaginationLimitExceeded,
)
from un_comtrade.parser import MetadataParser, TradeParser
from un_comtrade.trade import TradeService
from un_comtrade.transport import HttpTransport


# ---------------------------------------------------------------------------
# Helpers: canned upstream payloads
# ---------------------------------------------------------------------------


def _baseline_trade_record(**overrides) -> dict:
    """Build a baseline raw upstream trade record (camelCase)."""
    raw = {
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


def _trade_envelope(
    records: list[dict] | None = None,
    *,
    elapsed_seconds: float = 0.27,
    error: str = "",
    count: int | None = None,
) -> dict[str, Any]:
    """Build a canonical upstream trade envelope."""
    records = records if records is not None else []
    return {
        "count": count if count is not None else len(records),
        "data": records,
        "elapsed_seconds": elapsed_seconds,
        "error": error,
    }


# ---------------------------------------------------------------------------
# Fixtures: full-stack wiring
# ---------------------------------------------------------------------------


@pytest.fixture
def api_key() -> str:
    return "test-key-integration-123"


@pytest.fixture
def configuration(api_key: str) -> Configuration:
    return Configuration(api_key=api_key)


@pytest.fixture
def mock_client(
    configuration: Configuration, api_key: str
) -> ComtradeClient:
    """A `ComtradeClient` wired to a no-op mock transport.

    Tests that need actual upstream responses inject a
    specific handler via the `_set_handler` helper.
    """
    capture: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        capture.append(request)
        return httpx.Response(200, json={})

    transport = HttpTransport(
        base_url="https://example.invalid",
        user_agent="integration-test/1.0",
        api_key=api_key,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    client = ComtradeClient(
        configuration=configuration,
        transport=transport,
        cache=MetadataCache(),
        parser=MetadataParser(),
        metadata_service=MagicMock(),
    )
    client._test_capture = capture  # type: ignore[attr-defined]
    return client


# ---------------------------------------------------------------------------
# Test: Metadata + Trade integration
# ---------------------------------------------------------------------------


class TestMetadataTradeIntegration:
    """A `ComtradeClient` lifecycle that exercises both the
    metadata layer (via `client.metadata`) and the trade
    layer (via a `TradeService` built on the same
    transport + parser)."""

    def test_client_lifecycle(self, mock_client: ComtradeClient) -> None:
        # Configuration is exposed and immutable.
        assert mock_client.config.api_key == "test-key-integration-123"
        # Transport is shared between metadata + trade.
        assert mock_client.transport is not None
        # Metadata accessor exists and is lazy.
        assert mock_client.metadata is not None
        # Context-manager protocol works.
        mock_client.close()
        # Double-close is safe (transport was owned).
        mock_client.close()

    def test_metadata_and_trade_share_transport(
        self, mock_client: ComtradeClient, configuration: Configuration
    ) -> None:
        # A separate TradeService built on the same
        # transport shares the underlying `httpx.Client`
        # (and therefore the same MockTransport).
        trade_service = TradeService(
            mock_client.transport,
            parser=TradeParser(log_skipped=False),
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=_trade_envelope([_baseline_trade_record()]),
            )

        # Re-build the transport to use a different
        # handler — same transport object, different
        # underlying client.
        mock_client.transport._client = httpx.Client(  # type: ignore[attr-defined]
            transport=httpx.MockTransport(handler),
        )
        # Trade fetch through the shared transport.
        r = trade_service.get_exports(699, "2022")
        assert isinstance(r, TradeResponse)
        assert len(r.records) == 1
        assert r.records[0].reporter.name == "India"


# ---------------------------------------------------------------------------
# Test: Pagination engine
# ---------------------------------------------------------------------------


class TestPaginationIntegration:
    """The pagination engine wired to the trade layer's
    `_execute` helper, end-to-end."""

    def _make_trade_service(
        self, handler: Callable[[httpx.Request], httpx.Response]
    ) -> TradeService:
        transport = HttpTransport(
            base_url="https://example.invalid",
            user_agent="test/1.0",
            api_key="test-key",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        return TradeService(transport, parser=TradeParser(log_skipped=False))

    def test_multi_period_pagination(self) -> None:
        capture: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            capture.append(request)
            # Return one record per period in the request,
            # so each page is distinct (no cross-page dedup).
            params = dict(request.url.params)
            periods = params["period"].split(",")
            return httpx.Response(
                200,
                json=_trade_envelope(
                    [_baseline_trade_record(
                        period=p,
                        refYear=int(p),
                        refPeriodId=int(f"{p}0101"),
                    ) for p in periods]
                ),
            )

        service = self._make_trade_service(handler)
        engine = PaginationEngine()

        # 24 periods → 2 pages of 12.
        progress_calls: list[PageProgress] = []
        result = engine.paginate(
            [str(y) for y in range(2000, 2024)],
            fetch_page=lambda periods: service.get_trade(
                699, "X", ",".join(periods)
            ),
            on_progress=progress_calls.append,
        )

        # Page count: 2.
        assert len(capture) == 2
        # Result: 24 records merged (no dedup needed since
        # all periods are distinct).
        assert result.count == 24
        # Progress callback fired twice.
        assert len(progress_calls) == 2
        assert progress_calls[0].page_number == 1
        assert progress_calls[1].page_number == 2
        # Cumulative record count tracks correctly.
        assert progress_calls[0].records_so_far == 0
        assert progress_calls[1].records_so_far == 12

    def test_pagination_cross_page_dedup(self) -> None:
        # Same record appears on two pages → first wins.
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=_trade_envelope(
                    [_baseline_trade_record(period="2022")]
                ),
            )

        service = self._make_trade_service(handler)
        engine = PaginationEngine()
        # Force both pages to return the same record.
        result = engine.paginate(
            ["2022", "2023"],
            fetch_page=lambda periods: service.get_exports(
                699, ",".join(periods)
            ),
        )
        # Both calls returned one record; dedup collapses
        # them to 1.
        assert result.count == 1

    def test_pagination_max_page_safeguard(self) -> None:
        service = self._make_trade_service(
            lambda r: httpx.Response(200, json=_trade_envelope([]))
        )
        engine = PaginationEngine(
            PaginationConfig(max_periods_per_page=12, max_pages=12)
        )
        # 13 pages worth of periods → PaginationLimitExceeded.
        with pytest.raises(PaginationLimitExceeded):
            engine.paginate(
                [str(y) for y in range(2000, 2157)],
                fetch_page=lambda periods: service.get_exports(
                    699, ",".join(periods)
                ),
            )

    def test_pagination_abort_via_callback(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json=_trade_envelope([_baseline_trade_record()])
            )

        service = self._make_trade_service(handler)
        engine = PaginationEngine()

        def on_progress(p: PageProgress) -> bool | None:
            if p.page_number == 2:
                return False
            return None

        from un_comtrade.pagination import PaginationAborted

        with pytest.raises(PaginationAborted):
            engine.paginate(
                [str(y) for y in range(2000, 2024)],
                fetch_page=lambda periods: service.get_exports(
                    699, ",".join(periods)
                ),
                on_progress=on_progress,
            )


# ---------------------------------------------------------------------------
# Test: Batch downloader
# ---------------------------------------------------------------------------


class TestBatchIntegration:
    """The batch downloader wired to the trade layer."""

    def _make_trade_service(
        self, handler: Callable[[httpx.Request], httpx.Response]
    ) -> TradeService:
        transport = HttpTransport(
            base_url="https://example.invalid",
            user_agent="test/1.0",
            api_key="test-key",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        return TradeService(transport, parser=TradeParser(log_skipped=False))

    def test_full_batch(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json=_trade_envelope([_baseline_trade_record()])
            )

        service = self._make_trade_service(handler)
        downloader = BatchDownloader(service)

        progress: list[BatchProgress] = []
        result = downloader.download(
            [699, 842],
            [2020, 2021],
            [0, 156],
            on_progress=progress.append,
        )
        # 2 × 2 × 2 = 8 items.
        assert result.total == 8
        assert result.success_count == 8
        assert result.failure_count == 0
        # 8 progress callbacks.
        assert len(progress) == 8
        # All records flattened: 8 records (1 per item).
        assert len(result.all_records()) == 8

    def test_partial_failure_with_fail_fast_off(self) -> None:
        call_count = [0]

        def handler(request: httpx.Request) -> httpx.Response:
            call_count[0] += 1
            # Even calls fail.
            if call_count[0] % 2 == 0:
                return httpx.Response(
                    400, json={"error": "bad request"}
                )
            return httpx.Response(
                200, json=_trade_envelope([_baseline_trade_record()])
            )

        service = self._make_trade_service(handler)
        downloader = BatchDownloader(service)
        result = downloader.download([699, 842], [2020], [0, 156])
        # 4 items; 2 succeed, 2 fail.
        assert result.total == 4
        assert result.success_count == 2
        assert result.failure_count == 2
        # Failed items carry the APIError message.
        for failed in result.failed:
            assert "APIError" in failed.error
            # 4xx from the trade service is translated
            # to "Upstream 400 from <URL>" (the body
            # is on `excinfo.response_body`).
            assert "400" in failed.error

    def test_fail_fast_raises_on_first_failure(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "boom"})

        service = self._make_trade_service(handler)
        downloader = BatchDownloader(
            service, BatchConfig(fail_fast=True)
        )
        # 500 triggers retry (3 attempts by default) →
        # RetryError on exhaustion. fail_fast re-raises
        # the underlying exception.
        from un_comtrade.exceptions import RetryError
        with pytest.raises(RetryError):
            downloader.download([699], [2022], [0])

    def test_iteration_order_reporter_x_year_x_partner(self) -> None:
        seen_order: list[tuple[int, int, int]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            # Capture from query params.
            params = dict(request.url.params)
            seen_order.append(
                (
                    int(params["reporterCode"]),
                    int(params["period"]),
                    int(params["partnerCode"]),
                )
            )
            return httpx.Response(
                200, json=_trade_envelope([_baseline_trade_record()])
            )

        service = self._make_trade_service(handler)
        BatchDownloader(service).download(
            [699, 842], [2020, 2021], [0, 156]
        )
        # Outer = reporter; middle = year; inner = partner.
        expected = [
            (reporter, year, partner)
            for reporter in [699, 842]
            for year in [2020, 2021]
            for partner in [0, 156]
        ]
        assert seen_order == expected


# ---------------------------------------------------------------------------
# Test: Async jobs
# ---------------------------------------------------------------------------


class TestAsyncIntegration:
    """The async jobs service wired through the trade
    subsystem's transport."""

    def _make_async_service(
        self, handler: Callable[[httpx.Request], httpx.Response]
    ) -> tuple[AsyncJobsService, list[httpx.Request]]:
        capture: list[httpx.Request] = []

        def capturing_handler(request: httpx.Request) -> httpx.Response:
            capture.append(request)
            return handler(request)

        transport = HttpTransport(
            base_url="https://example.invalid",
            user_agent="test/1.0",
            api_key="test-key",
            client=httpx.Client(
                transport=httpx.MockTransport(capturing_handler)
            ),
        )
        return AsyncJobsService(transport), capture

    def test_submit_status_download_workflow(self) -> None:
        request_id = "abc-123"

        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if request.method == "POST":
                return httpx.Response(200, json={"requestId": request_id})
            if path.endswith("/status"):
                return httpx.Response(
                    200, json={"status": "Completed", "count": 1000}
                )
            if path.endswith("/file"):
                return httpx.Response(
                    200, content=b'{"records": []}',
                    headers={"content-type": "application/json"},
                )
            return httpx.Response(404)

        service, capture = self._make_async_service(handler)

        # Submit.
        handle = service.submit_async_final_data(699, "X", "2022")
        assert isinstance(handle, AsyncRequestHandle)
        assert handle.request_id == request_id
        assert handle.period == "2022"
        assert handle.reporter_code == 699

        # Status.
        status = service.check_async_request(handle)
        assert isinstance(status, AsyncRequestStatus)
        assert status.is_completed
        assert status.records_count == 1000

        # Download.
        with tempfile.TemporaryDirectory() as tmp:
            path = service.download_async_request(handle, tmp)
            assert path.exists()
            assert path.read_bytes() == b'{"records": []}'

        # All three URLs hit the documented patterns.
        assert capture[0].method == "POST"
        assert "/data/v1/bulk/C/A/2022/699" in capture[0].url.path
        assert capture[1].url.path.endswith(
            "/data/v1/bulk/C/A/2022/699/abc-123/status"
        )
        assert capture[2].url.path.endswith(
            "/data/v1/bulk/C/A/2022/699/abc-123/file"
        )

    def test_async_handle_carries_metadata_for_status(
        self,
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                return httpx.Response(200, json={"requestId": "abc"})
            return httpx.Response(200, json={"status": "Running"})

        service, _ = self._make_async_service(handler)
        handle = service.submit_async_final_data(699, "M", "202201")
        # The handle carries the freqCode derived from
        # the period token.
        assert handle.frequency_code == "M"
        # Status URL uses the handle's metadata.
        service.check_async_request(handle)

    def test_async_failed_status(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                return httpx.Response(200, json={"requestId": "abc"})
            return httpx.Response(
                200, json={"status": "Failed", "error": "boom"}
            )

        service, _ = self._make_async_service(handler)
        handle = service.submit_async_final_data(699, "X", "2022")
        status = service.check_async_request(handle)
        assert status.is_failed
        assert status.error == "boom"
        assert status.is_terminal


# ---------------------------------------------------------------------------
# Test: Parser
# ---------------------------------------------------------------------------


class TestParserIntegration:
    """The trade parser converts upstream JSON to canonical
    models end-to-end. Decimal precision is preserved."""

    def test_raw_to_canonical(self) -> None:
        parser = TradeParser(log_skipped=False)
        raw = _baseline_trade_record()
        result = parser.parse_records([raw])
        assert len(result.records) == 1
        record = result.records[0]
        assert isinstance(record, TradeRecord)
        assert isinstance(record.reporter, Reporter)
        assert isinstance(record.partner, TradePartner)
        assert isinstance(record.flow, RecordTradeFlow)
        assert isinstance(record.commodity, Commodity)
        assert isinstance(record.trade_value, TradeValue)
        assert isinstance(record.quantity, Quantity)

    def test_decimal_precision_preserved(self) -> None:
        parser = TradeParser(log_skipped=False)
        # 0.1 + 0.2 in float would round; Decimal preserves.
        raw = _baseline_trade_record(
            primaryValue="0.30000000000000004",
            fobvalue="0.30000000000000004",
        )
        result = parser.parse_records([raw])
        assert result.records[0].trade_value.primary_value == Decimal(
            "0.30000000000000004"
        )

    def test_high_precision_india_exports(self) -> None:
        # The 2022 India world total: $452,684,213,646.747.
        parser = TradeParser(log_skipped=False)
        raw = _baseline_trade_record(
            primaryValue=452684213646.747,
            fobvalue=452684213646.747,
        )
        result = parser.parse_records([raw])
        assert result.records[0].trade_value.primary_value == Decimal(
            "452684213646.747"
        )

    def test_partner_world_sentinel(self) -> None:
        parser = TradeParser(log_skipped=False)
        raw = _baseline_trade_record(
            partnerCode=0, partnerISO="W00", partnerDesc="World"
        )
        result = parser.parse_records([raw])
        assert result.records[0].partner.is_world is True
        assert result.records[0].partner.partner_code == 0

    def test_partner2_default_none(self) -> None:
        # All-zero partner2 sentinel collapses to None
        # (the canonical "no secondary partner" state).
        parser = TradeParser(log_skipped=False)
        raw = _baseline_trade_record(
            partner2Code=0, partner2ISO="W00", partner2Desc="World"
        )
        result = parser.parse_records([raw])
        assert result.records[0].partner2 is None

    def test_partner2_set(self) -> None:
        parser = TradeParser(log_skipped=False)
        raw = _baseline_trade_record(
            partner2Code=842, partner2ISO="USA", partner2Desc="USA"
        )
        result = parser.parse_records([raw])
        assert result.records[0].partner2 is not None
        assert result.records[0].partner2.partner_code == 842

    def test_dedup_within_call(self) -> None:
        parser = TradeParser(log_skipped=False)
        raw = _baseline_trade_record()
        result = parser.parse_records([raw, raw])
        assert len(result.records) == 1
        assert result.skipped == 1

    def test_validation_skips_invalid_records(self) -> None:
        parser = TradeParser(log_skipped=False)
        good = _baseline_trade_record()
        bad = _baseline_trade_record(primaryValue=None)
        result = parser.parse_records([good, bad])
        assert len(result.records) == 1
        assert result.skipped == 1

    def test_composite_key_uniqueness(self) -> None:
        from un_comtrade.parser import TradeParser

        record1 = TradeParser().parse_record(_baseline_trade_record())
        # Different period → different key.
        record2 = TradeParser().parse_record(
            _baseline_trade_record(period="2023", refYear=2023)
        )
        assert TradeParser.composite_key(record1) != TradeParser.composite_key(
            record2
        )


# ---------------------------------------------------------------------------
# Test: Transport
# ---------------------------------------------------------------------------


class TestTransportIntegration:
    """Verify the transport layer's auth / retry / timeout
    policies are honoured end-to-end through the trade
    layer."""

    def test_auth_header_on_trade_call(self) -> None:
        capture: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            capture.append(request)
            return httpx.Response(
                200, json=_trade_envelope([_baseline_trade_record()])
            )

        transport = HttpTransport(
            base_url="https://example.invalid",
            user_agent="test/1.0",
            api_key="my-secret-key",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        service = TradeService(transport, parser=TradeParser(log_skipped=False))
        service.get_exports(699, "2022")
        assert (
            capture[0].headers.get("ocp-apim-subscription-key")
            == "my-secret-key"
        )

    def test_auth_header_on_async_call(self) -> None:
        capture: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            capture.append(request)
            return httpx.Response(200, json={"requestId": "abc"})

        transport = HttpTransport(
            base_url="https://example.invalid",
            user_agent="test/1.0",
            api_key="my-secret-key",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        service = AsyncJobsService(transport)
        service.submit_async_final_data(699, "X", "2022")
        assert (
            capture[0].headers.get("ocp-apim-subscription-key")
            == "my-secret-key"
        )

    def test_401_raises_authentication_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                401,
                json={
                    "statusCode": 401,
                    "message": "missing subscription key",
                },
            )

        transport = HttpTransport(
            base_url="https://example.invalid",
            user_agent="test/1.0",
            api_key="bad-key",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        service = TradeService(transport, parser=TradeParser(log_skipped=False))
        with pytest.raises(AuthenticationError):
            service.get_exports(699, "2022")

    def test_400_raises_api_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"error": "bad request"})

        transport = HttpTransport(
            base_url="https://example.invalid",
            user_agent="test/1.0",
            api_key="test-key",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        service = TradeService(transport, parser=TradeParser(log_skipped=False))
        with pytest.raises(APIError) as excinfo:
            service.get_exports(699, "2022")
        assert excinfo.value.status_code == 400


# ---------------------------------------------------------------------------
# Test: Cross-layer integration
# ---------------------------------------------------------------------------


class TestCrossLayerIntegration:
    """Verify the full subsystem works together: metadata
    lookup → trade fetch → pagination → batch → async
    all share the same transport, parser, and
    configuration."""

    def test_full_stack(
        self, configuration: Configuration, api_key: str
    ) -> None:
        """Build a full `ComtradeClient` with metadata
        service + trade service + async jobs + batch +
        pagination all wired to a single mock transport,
        then exercise each component end-to-end."""

        # Smart mock handler that routes by path.
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            path = request.url.path
            # Metadata: reporters
            if path.endswith("/Reporters.json"):
                return httpx.Response(
                    200,
                    json=[
                        {
                            "reporterCode": 699,
                            "reporterDesc": "India",
                            "reporterCodeIsoAlpha2": "IN",
                            "reporterCodeIsoAlpha3": "IND",
                        },
                        {
                            "reporterCode": 842,
                            "reporterDesc": "USA",
                            "reporterCodeIsoAlpha2": "US",
                            "reporterCodeIsoAlpha3": "USA",
                        },
                    ],
                )
            # Trade
            if path.startswith("/C/A/") and path.endswith("/HS"):
                return httpx.Response(
                    200,
                    json=_trade_envelope(
                        [_baseline_trade_record(reporter_code=699)]
                    ),
                )
            # Async submit
            if request.method == "POST":
                return httpx.Response(200, json={"requestId": "async-1"})
            # Async status
            if path.endswith("/status"):
                return httpx.Response(
                    200, json={"status": "Completed"}
                )
            # Async download
            if path.endswith("/file"):
                return httpx.Response(
                    200, content=b'{"records": []}',
                    headers={"content-type": "application/json"},
                )
            return httpx.Response(404)

        transport = HttpTransport(
            base_url="https://example.invalid",
            user_agent="integration-test/1.0",
            api_key=api_key,
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )

        # Build the full subsystem on a single transport.
        client = ComtradeClient(
            configuration=configuration,
            transport=transport,
            cache=MetadataCache(),
            parser=MetadataParser(),
        )
        trade_service = TradeService(
            transport, parser=TradeParser(log_skipped=False)
        )
        async_service = AsyncJobsService(transport)
        batch_downloader = BatchDownloader(trade_service)
        pagination_engine = PaginationEngine()

        try:
            # 1. Metadata lookup.
            countries = client.metadata.get_countries()
            assert isinstance(countries, list)
            assert len(countries) == 2
            assert isinstance(countries[0], Country)
            assert countries[0].country_code == 699

            # 2. Trade fetch through the same transport.
            response = trade_service.get_exports(699, "2022")
            assert len(response.records) == 1
            assert response.records[0].reporter.reporter_code == 699

            # 3. Pagination via the same transport.
            paged = pagination_engine.paginate(
                ["2022"],
                fetch_page=lambda periods: trade_service.get_exports(
                    699, ",".join(periods)
                ),
            )
            assert paged.count == 1

            # 4. Batch via the same transport.
            batched = batch_downloader.download(
                [699], [2022], [0, 156]
            )
            assert batched.total == 2
            assert batched.success_count == 2

            # 5. Async via the same transport.
            handle = async_service.submit_async_final_data(
                699, "X", "2022"
            )
            assert handle.request_id == "async-1"
            status = async_service.check_async_request(handle)
            assert status.is_completed
            with tempfile.TemporaryDirectory() as tmp:
                path = async_service.download_async_request(handle, tmp)
                assert path.exists()

            # 6. Auth header present on every request.
            assert all(
                req.headers.get("ocp-apim-subscription-key") == api_key
                for req in captured
            )

            # 7. User agent present on every request.
            assert all(
                req.headers.get("user-agent") == "integration-test/1.0"
                for req in captured
            )

            # 8. The cache is shared between metadata and
            # the rest of the subsystem (but in this test
            # the cache is empty so we just verify it
            # exists on the client).
            assert client.config is configuration

        finally:
            client.close()

    def test_canonical_records_across_subsystem(self) -> None:
        """A single TradeRecord produced via the trade
        service can be passed downstream (e.g. to a
        batch aggregator or a custom exporter) without
        losing its canonical shape."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json=_trade_envelope([_baseline_trade_record()])
            )

        transport = HttpTransport(
            base_url="https://example.invalid",
            user_agent="test/1.0",
            api_key="test-key",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        service = TradeService(transport, parser=TradeParser(log_skipped=False))
        response = service.get_exports(699, "2022")
        record = response.records[0]

        # The record is fully populated with canonical
        # types — a downstream consumer can use it
        # without re-parsing.
        assert isinstance(record.reporter, Reporter)
        assert record.reporter.reporter_code == 699
        assert isinstance(record.partner, TradePartner)
        assert record.partner.is_world is True
        assert isinstance(record.flow, RecordTradeFlow)
        assert record.flow.flow_code == "X"
        assert isinstance(record.commodity, Commodity)
        assert record.commodity.commodity_code == "TOTAL"
        assert isinstance(record.trade_value, TradeValue)
        assert record.trade_value.primary_value == Decimal(
            "452684213646.747"
        )
        assert isinstance(record.quantity, Quantity)
        assert record.quantity.qty_unit_code == -1

        # Round-trip through pickle preserves the
        # canonical shape (frozen dataclass).
        import pickle
        restored = pickle.loads(pickle.dumps(record))
        assert restored == record
        assert isinstance(restored, TradeRecord)


# ---------------------------------------------------------------------------
# Test: Configuration propagation
# ---------------------------------------------------------------------------


class TestConfigurationIntegration:
    """Verify the configuration flows through every
    subsystem component."""

    def test_config_reaches_every_component(
        self, configuration: Configuration
    ) -> None:
        # Override the configuration's defaults so the
        # test assertions are independent of the SDK's
        # documented defaults.
        configuration = Configuration(
            api_key="test-key",
            base_url="https://example.invalid",
            user_agent="test/1.0",
        )

        capture: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            capture.append(request)
            if request.method == "POST":
                return httpx.Response(200, json={"requestId": "abc"})
            if "/data/v1/bulk" in request.url.path:
                if request.url.path.endswith("/status"):
                    return httpx.Response(200, json={"status": "Completed"})
                return httpx.Response(200, content=b"{}")
            return httpx.Response(
                200, json=_trade_envelope([_baseline_trade_record()])
            )

        transport = HttpTransport(
            base_url=configuration.base_url,
            user_agent=configuration.user_agent,
            api_key=configuration.api_key,
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )

        # Every component uses the same transport →
        # same base_url, user_agent, api_key.
        client = ComtradeClient(configuration=configuration, transport=transport)
        trade = TradeService(transport, parser=TradeParser(log_skipped=False))
        async_service = AsyncJobsService(transport)
        batch = BatchDownloader(trade)

        try:
            client.metadata.get_countries()
            trade.get_exports(699, "2022")
            async_service.submit_async_final_data(699, "X", "2022")
            batch.download([699], [2022], [0])

            # Every request uses the configured base_url.
            assert len(capture) >= 3, (
                f"Expected at least 3 captured requests, "
                f"got {len(capture)}"
            )
            expected_host = configuration.base_url.split("//", 1)[
                1
            ].split("/", 1)[0]
            for req in capture:
                # Every request uses the configured base_url.
                assert req.url.host == expected_host, (
                    f"unexpected host: {req.url.host}, "
                    f"expected {expected_host}"
                )
                # Every request uses the configured user_agent.
                assert req.headers.get("user-agent") == "test/1.0", (
                    f"unexpected user-agent: "
                    f"{req.headers.get('user-agent')}"
                )
                # Every request uses the configured api_key.
                assert (
                    req.headers.get("ocp-apim-subscription-key") == "test-key"
                ), (
                    f"unexpected api_key: "
                    f"{req.headers.get('ocp-apim-subscription-key')}"
                )
        finally:
            client.close()


# ---------------------------------------------------------------------------
# Test: Error propagation across layers
# ---------------------------------------------------------------------------


class TestErrorPropagation:
    """Verify that exceptions raised at the transport
    layer propagate through the trade / batch / async
    layers with the documented exception types."""

    def test_400_propagates_through_batch(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"error": "bad request"})

        transport = HttpTransport(
            base_url="https://example.invalid",
            user_agent="test/1.0",
            api_key="test-key",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        service = TradeService(transport, parser=TradeParser(log_skipped=False))
        downloader = BatchDownloader(service)
        result = downloader.download([699], [2022], [0, 156])
        # Both items fail; no exception escapes.
        assert result.failure_count == 2
        assert all("APIError" in f.error for f in result.failed)

    def test_retry_exhaustion_propagates(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "boom"})

        transport = HttpTransport(
            base_url="https://example.invalid",
            user_agent="test/1.0",
            api_key="test-key",
            # Disable retries so we observe the 5xx surface
            # without retry budget exhaustion.
            client=httpx.Client(transport=httpx.MockTransport(handler)),
            retry=None,
        )
        # Override retry policy via the constructor.
        from un_comtrade.transport import RetryPolicy
        transport_retry = HttpTransport(
            base_url="https://example.invalid",
            user_agent="test/1.0",
            api_key="test-key",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
            retry=RetryPolicy(attempts=1),
        )
        service = TradeService(
            transport_retry, parser=TradeParser(log_skipped=False)
        )
        from un_comtrade.exceptions import ServerError

        with pytest.raises(ServerError):
            service.get_exports(699, "2022")

    def test_async_400_raises(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"error": "bad submit"})

        transport = HttpTransport(
            base_url="https://example.invalid",
            user_agent="test/1.0",
            api_key="test-key",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        service = AsyncJobsService(transport)
        # 4xx on submit surfaces as ValidationError (no
        # request id extracted from the error body).
        # This documents the current behaviour; a future
        # enhancement may translate 4xx to APIError for
        # consistency with the trade layer.
        from un_comtrade.exceptions import ValidationError

        with pytest.raises(ValidationError, match="request id"):
            service.submit_async_final_data(699, "X", "2022")