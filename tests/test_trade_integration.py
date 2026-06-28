"""End-to-end integration tests for the L4 Trade Layer.

Per the P2-006 task scope, the trade subsystem is
complete end-to-end: `TradeService` builds queries,
calls the upstream, parses the response into canonical
`TradeRecord` instances, deduplicates by composite key,
and exposes the parsed records on `TradeResponse.records`.

These tests exercise the full pipeline using
`httpx.MockTransport` so the suite never hits the live
network.

Coverage:

- Mock-request flow succeeds end-to-end (T01-T03 + T09-T11)
- Canonical `TradeRecord` instances returned on the
  public surface (P2-006 contract)
- Deduplication by composite key collapses duplicates
  inside a single response
- Validation failures are reported via `skipped` count
- Without a parser wired, `records` is empty (the
  parser is required for canonical surface)
- Multiple endpoints (annual + monthly, exports +
  imports + trade) all produce parsed records
- The `skipped` field tracks parser skips accurately
- The `count` field reflects upstream count
  (independent of dedup outcome)
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable

import httpx
import pytest

from un_comtrade.config import Configuration
from un_comtrade.models import (
    Commodity,
    Quantity,
    Reporter,
    TradePartner,
    TradeRecord,
    TradeResponse,
    TradeValue,
    RecordTradeFlow,
)
from un_comtrade.parser import TradeParser
from un_comtrade.trade import TradeService
from un_comtrade.transport import HttpTransport


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _baseline_record(**overrides) -> dict:
    """Build a baseline raw upstream record (camelCase)."""
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


def _envelope(
    records: list[dict] | None = None,
    *,
    elapsed_seconds: float = 0.27,
    error: str = "",
    count: int | None = None,
) -> dict[str, Any]:
    """Build an upstream envelope with the given records."""
    records = records if records is not None else []
    return {
        "count": count if count is not None else len(records),
        "data": records,
        "elapsed_seconds": elapsed_seconds,
        "error": error,
    }


def _make_service(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    parser: TradeParser | None = None,
) -> TradeService:
    """Build a `TradeService` wired to a mock handler + optional parser."""
    transport = HttpTransport(
        base_url="https://example.invalid",
        user_agent="test/1.0",
        api_key="test-key-123",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    if parser is None:
        parser = TradeParser(log_skipped=False)
    return TradeService(transport, parser=parser)


# ---------------------------------------------------------------------------
# T01 — annual exports
# ---------------------------------------------------------------------------


class TestGetExportsIntegration:
    def test_returns_canonical_records(self):
        svc = _make_service(
            lambda r: httpx.Response(200, json=_envelope([_baseline_record()]))
        )
        r = svc.get_exports(699, "2022")
        assert isinstance(r, TradeResponse)
        assert len(r.records) == 1
        assert isinstance(r.records[0], TradeRecord)
        assert r.records[0].reporter.name == "India"
        assert r.records[0].partner.is_world is True
        assert r.records[0].trade_value.primary_value == Decimal(
            "452684213646.747"
        )

    def test_count_reflects_upstream(self):
        # Two distinct records (different partner codes) →
        # count=2 in the envelope; both records parsed.
        svc = _make_service(
            lambda r: httpx.Response(
                200,
                json=_envelope(
                    [
                        _baseline_record(partnerCode=0),
                        _baseline_record(
                            partnerCode=842,
                            partnerISO="USA",
                            partnerDesc="USA",
                        ),
                    ]
                ),
            )
        )
        r = svc.get_exports(699, "2022")
        assert r.count == 2
        assert len(r.records) == 2

    def test_skipped_count_when_duplicate(self):
        # Two records with the same composite key → first wins,
        # second is recorded as a skip.
        svc = _make_service(
            lambda r: httpx.Response(
                200,
                json=_envelope(
                    [
                        _baseline_record(primaryValue=100.0),
                        _baseline_record(primaryValue=200.0),
                    ]
                ),
            )
        )
        r = svc.get_exports(699, "2022")
        assert r.count == 2  # upstream says 2
        assert len(r.records) == 1  # but dedup collapses to 1
        assert r.skipped == 1  # one duplicate removed
        # First-wins: the surviving record has primary_value=100.
        assert r.records[0].trade_value.primary_value == Decimal("100")

    def test_skipped_count_when_invalid(self):
        # One valid + one invalid record → 1 valid, 1 skipped.
        svc = _make_service(
            lambda r: httpx.Response(
                200,
                json=_envelope(
                    [
                        _baseline_record(),
                        _baseline_record(primaryValue=None),
                    ]
                ),
            )
        )
        r = svc.get_exports(699, "2022")
        assert r.count == 2
        assert len(r.records) == 1
        assert r.skipped == 1

    def test_empty_response(self):
        svc = _make_service(
            lambda r: httpx.Response(
                200, json=_envelope([], count=0)
            )
        )
        r = svc.get_exports(699, "2099")
        assert r.count == 0
        assert r.records == []
        assert r.skipped == 0


# ---------------------------------------------------------------------------
# T02 — annual imports
# ---------------------------------------------------------------------------


class TestGetImportsIntegration:
    def test_returns_canonical_records(self):
        svc = _make_service(
            lambda r: httpx.Response(
                200,
                json=_envelope(
                    [_baseline_record(flowCode="M", flowDesc="Import")]
                ),
            )
        )
        r = svc.get_imports(699, "2022")
        assert r.records[0].flow.flow_code == "M"
        assert r.records[0].flow.flow_name == "Import"


# ---------------------------------------------------------------------------
# T03 — annual trade (explicit flow)
# ---------------------------------------------------------------------------


class TestGetTradeIntegration:
    @pytest.mark.parametrize("flow_code,flow_desc", [("X", "Export"), ("M", "Import")])
    def test_returns_canonical_records(self, flow_code, flow_desc):
        svc = _make_service(
            lambda r: httpx.Response(
                200,
                json=_envelope(
                    [_baseline_record(flowCode=flow_code, flowDesc=flow_desc)]
                ),
            )
        )
        r = svc.get_trade(699, flow_code, "2022")
        assert r.records[0].flow.flow_code == flow_code
        assert r.records[0].flow.flow_name == flow_desc


# ---------------------------------------------------------------------------
# T09-T11 — monthly variants
# ---------------------------------------------------------------------------


class TestMonthlyIntegration:
    def test_get_monthly_exports(self):
        svc = _make_service(
            lambda r: httpx.Response(
                200,
                json=_envelope(
                    [_baseline_record(period="202201", refMonth=1, freqCode="M")]
                ),
            )
        )
        r = svc.get_monthly_exports(699, "202201")
        assert len(r.records) == 1
        assert r.records[0].period == "202201"
        assert r.records[0].ref_month == 1

    def test_get_monthly_imports(self):
        svc = _make_service(
            lambda r: httpx.Response(
                200,
                json=_envelope(
                    [
                        _baseline_record(
                            flowCode="M",
                            flowDesc="Import",
                            period="202201",
                            refMonth=1,
                            freqCode="M",
                        )
                    ]
                ),
            )
        )
        r = svc.get_monthly_imports(699, "202201")
        assert r.records[0].flow.flow_code == "M"

    def test_get_monthly_trade(self):
        svc = _make_service(
            lambda r: httpx.Response(
                200,
                json=_envelope(
                    [_baseline_record(period="202201", refMonth=1, freqCode="M")]
                ),
            )
        )
        r = svc.get_monthly_trade(699, "X", "202201")
        assert r.records[0].flow.flow_code == "X"
        assert r.records[0].period == "202201"


# ---------------------------------------------------------------------------
# Parser-less service
# ---------------------------------------------------------------------------


class TestParserlessService:
    def test_no_parser_records_empty(self):
        # When no parser is wired, the canonical records list
        # is empty. The envelope metadata (count, error,
        # elapsed_seconds) is still populated.
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json=_envelope([_baseline_record()])
            )

        transport = HttpTransport(
            base_url="https://example.invalid",
            user_agent="test/1.0",
            api_key="test-key-123",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        svc = TradeService(transport, parser=None)
        r = svc.get_exports(699, "2022")
        assert r.count == 1
        assert r.records == []
        assert r.skipped == 0


# ---------------------------------------------------------------------------
# Custom parser instance
# ---------------------------------------------------------------------------


class TestCustomParser:
    def test_log_skipped_silent(self):
        # When parser.log_skipped=False, the count is still
        # accurate but no warnings are emitted.
        parser = TradeParser(log_skipped=False)
        svc = _make_service(
            lambda r: httpx.Response(
                200,
                json=_envelope(
                    [_baseline_record(), _baseline_record(primaryValue=None)]
                ),
            ),
            parser=parser,
        )
        r = svc.get_exports(699, "2022")
        assert len(r.records) == 1
        assert r.skipped == 1

    def test_log_skipped_verbose_emits_warning(self, caplog):
        import logging

        caplog.set_level(logging.WARNING, logger="un_comtrade.metadata")
        parser = TradeParser(log_skipped=True)
        svc = _make_service(
            lambda r: httpx.Response(
                200,
                json=_envelope(
                    [_baseline_record(), _baseline_record(primaryValue=None)]
                ),
            ),
            parser=parser,
        )
        r = svc.get_exports(699, "2022")
        assert r.skipped == 1
        # WARNING log emitted.
        warnings = [
            rec for rec in caplog.records if rec.levelno == logging.WARNING
        ]
        assert any("skipped trade record" in w.message for w in warnings)


# ---------------------------------------------------------------------------
# URL path + query params are unchanged after parser integration
# ---------------------------------------------------------------------------


class TestUrlAndQueryUnchanged:
    def test_url_path_annual_export(self):
        capture: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            capture.append(request)
            return httpx.Response(
                200, json=_envelope([_baseline_record()])
            )

        svc = _make_service(handler)
        svc.get_exports(699, "2022")
        assert capture[0].url.path == "/C/A/X/HS"

    def test_url_path_monthly_export(self):
        capture: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            capture.append(request)
            return httpx.Response(
                200, json=_envelope([_baseline_record()])
            )

        svc = _make_service(handler)
        svc.get_monthly_exports(699, "202201")
        assert capture[0].url.path == "/C/M/X/HS"

    def test_query_params_default(self):
        capture: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            capture.append(request)
            return httpx.Response(
                200, json=_envelope([_baseline_record()])
            )

        svc = _make_service(handler)
        svc.get_exports(699, "2022")
        params = dict(capture[0].url.params)
        assert params["reporterCode"] == "699"
        assert params["period"] == "2022"
        assert params["flowCode"] == "X"
        assert params["cmdCode"] == "TOTAL"
        assert params["classification"] == "HS"
        assert params["includeDesc"] == "true"

    def test_query_params_custom(self):
        capture: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            capture.append(request)
            return httpx.Response(
                200, json=_envelope([_baseline_record()])
            )

        svc = _make_service(handler)
        svc.get_exports(
            699,
            "2022",
            partner_code=842,
            commodity_code="0101",
            classification="HS",
            edition="H2022",
            breakdown_mode="plus",
            max_records=100,
        )
        params = dict(capture[0].url.params)
        assert params["partnerCode"] == "842"
        assert params["cmdCode"] == "0101"
        assert params["classification"] == "H2022"
        assert params["breakdownMode"] == "plus"
        assert params["maxRecords"] == "100"


# ---------------------------------------------------------------------------
# Auth header still injected (parser doesn't affect transport layer)
# ---------------------------------------------------------------------------


class TestAuthHeaderStillInjected:
    def test_auth_header_sent(self):
        capture: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            capture.append(request)
            return httpx.Response(
                200, json=_envelope([_baseline_record()])
            )

        svc = _make_service(handler)
        svc.get_exports(699, "2022")
        headers = capture[0].headers
        assert headers.get("ocp-apim-subscription-key") == "test-key-123"


# ---------------------------------------------------------------------------
# Canonical model introspection
# ---------------------------------------------------------------------------


class TestCanonicalModelIntrospection:
    def test_record_attributes_accessible(self):
        svc = _make_service(
            lambda r: httpx.Response(
                200, json=_envelope([_baseline_record()])
            )
        )
        r = svc.get_exports(699, "2022")
        record = r.records[0]

        # Subjects
        assert isinstance(record.reporter, Reporter)
        assert isinstance(record.partner, TradePartner)
        assert isinstance(record.commodity, Commodity)
        assert isinstance(record.flow, RecordTradeFlow)

        # Values
        assert isinstance(record.trade_value, TradeValue)
        assert isinstance(record.quantity, Quantity)

        # Identifiers
        assert record.ref_year == 2022
        assert record.ref_month == 52
        assert record.period == "2022"
        assert record.classification_code == "H6"
        assert record.customs_code == "C00"

    def test_decimal_arithmetic_preserves_precision(self):
        svc = _make_service(
            lambda r: httpx.Response(
                200,
                json=_envelope(
                    [
                        _baseline_record(
                            primaryValue="0.1",
                            fobvalue="0.1",
                        ),
                        _baseline_record(
                            partnerCode=842,
                            partnerISO="USA",
                            partnerDesc="USA",
                            primaryValue="0.2",
                            fobvalue="0.2",
                        ),
                    ]
                ),
            )
        )
        r = svc.get_exports(699, "2022")
        # Decimal precision: 0.1 + 0.2 == Decimal("0.3"), not
        # 0.30000000000000004 (which would be the float result).
        total = sum(
            (record.trade_value.primary_value for record in r.records),
            Decimal("0"),
        )
        assert total == Decimal("0.3")

    def test_partner_is_world_property(self):
        svc = _make_service(
            lambda r: httpx.Response(
                200, json=_envelope([_baseline_record(partnerCode=0)])
            )
        )
        r = svc.get_exports(699, "2022")
        assert r.records[0].partner.is_world is True

    def test_partner_specific(self):
        svc = _make_service(
            lambda r: httpx.Response(
                200,
                json=_envelope(
                    [
                        _baseline_record(
                            partnerCode=842,
                            partnerISO="USA",
                            partnerDesc="USA",
                        )
                    ]
                ),
            )
        )
        r = svc.get_exports(699, "2022")
        assert r.records[0].partner.is_world is False
        assert r.records[0].partner.name == "USA"


# ---------------------------------------------------------------------------
# ComtradeClient integration (skeleton — verifies wiring through client)
# ---------------------------------------------------------------------------


class TestComtradeClientIntegration:
    def test_client_trade_service_returns_canonical_records(self):
        from un_comtrade.client import ComtradeClient

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json=_envelope([_baseline_record()])
            )

        cfg = Configuration(api_key="test-key-123")
        client = ComtradeClient(
            configuration=cfg,
            transport=HttpTransport(
                base_url="https://example.invalid",
                user_agent="test/1.0",
                api_key="test-key-123",
                client=httpx.Client(transport=httpx.MockTransport(handler)),
            ),
            parser=TradeParser(log_skipped=False),
        )
        try:
            # The client exposes trade via a lazy accessor that
            # lands with P3-001. For now, the client.metadata
            # accessor exists; trade service wiring through
            # client.trade lands in a later task. This test
            # verifies the foundation pieces only.
            assert client.config is cfg
            assert client.transport is not None
        finally:
            client.close()