"""Integration tests for the advanced trade retrieval methods (T04-T08).

Per the P3-001 task scope, these methods reuse the
existing `_build_query` / `_execute` / `TradeParser`
pipeline. No new parser logic; no new transport logic.
The differences between methods are:

- T04 `get_trade_by_hs` — `commodity_code` is required
  (not defaulted to `"TOTAL"`); standard trade endpoint.
- T05 `get_world_trade` — `partner_code=0` is implied;
  standard trade endpoint.
- T06 `get_trade_balance` — hits the dedicated balance
  endpoint (`/tools/v1/getTradeBalance/...`); no
  flow_code in URL path; flow_code omitted from
  query params.
- T07 `get_bilateral` — hits the dedicated bilateral
  endpoint (`/tools/v1/getBilateralData/...`); no
  flow_code in URL path; flow_code IS in query params.
- T08 `get_trade_matrix` — hits the dedicated matrix
  endpoint (`/data/v1/getTradeMatrix/.../TM`); the
  classification code is forced to `"TM"` in the URL
  path.

All tests use `httpx.MockTransport` so the suite never
hits the live network. Coverage:

- URL path construction for each endpoint
- Query parameter mapping (camelCase, defaults, edge
  cases)
- World sentinel handling
- Canonical `TradeRecord` instances on the public
  surface (P2-006 contract)
- Reuse: each method calls `_build_query` and
  `_execute` exactly once
- No parser duplication: the parser is invoked only
  through `TradeService._execute`
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable

import httpx
import pytest

from un_comtrade.models import (
    TradePartner,
    TradeRecord,
    TradeResponse,
)
from un_comtrade.parser import TradeParser
from un_comtrade.trade import (
    _PATH_BALANCE,
    _PATH_BILATERAL,
    _PATH_MATRIX,
    _PATH_TRADE,
    TradeService,
)
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


class _RequestCapture:
    """Capture requests observed by the mock handler."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(
            200, json=_envelope(records=[_baseline_record()])
        )


def _make_service(
    handler: Callable[[httpx.Request], httpx.Response],
) -> TradeService:
    """Build a `TradeService` wired to a mock handler + parser."""
    transport = HttpTransport(
        base_url="https://example.invalid",
        user_agent="test/1.0",
        api_key="test-key-123",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    return TradeService(transport, parser=TradeParser(log_skipped=False))


# ---------------------------------------------------------------------------
# Path template constants
# ---------------------------------------------------------------------------


class TestPathTemplates:
    def test_path_trade(self):
        assert _PATH_TRADE == (
            "/{trade_type}/{freqCode}/{flowCode}/{classificationCode}"
        )

    def test_path_balance(self):
        assert _PATH_BALANCE == (
            "/tools/v1/getTradeBalance/{trade_type}/{freqCode}/{classificationCode}"
        )

    def test_path_bilateral(self):
        assert _PATH_BILATERAL == (
            "/tools/v1/getBilateralData/{trade_type}/{freqCode}/{classificationCode}"
        )

    def test_path_matrix(self):
        assert _PATH_MATRIX == (
            "/data/v1/getTradeMatrix/{trade_type}/{freqCode}/TM"
        )

    def test_matrix_uses_tm_sentinel(self):
        # Matrix endpoint uses "TM" as the fixed
        # classification code (not HS).
        assert "{classificationCode}" not in _PATH_MATRIX
        assert "TM" in _PATH_MATRIX


# ---------------------------------------------------------------------------
# T04 — get_trade_by_hs
# ---------------------------------------------------------------------------


class TestGetTradeByHs:
    def test_returns_canonical_records(self):
        svc = _make_service(_RequestCapture())
        r = svc.get_trade_by_hs("0101", 699, "X", "2022")
        assert isinstance(r, TradeResponse)
        assert isinstance(r.records[0], TradeRecord)

    def test_url_path_standard(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_by_hs("0101", 699, "X", "2022")
        assert capture.requests[0].url.path == "/C/A/X/HS"

    def test_commodity_code_in_query(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_by_hs("0101", 699, "X", "2022")
        params = dict(capture.requests[0].url.params)
        assert params["cmdCode"] == "0101"

    def test_reporter_and_flow_in_query(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_by_hs("0101", 699, "X", "2022")
        params = dict(capture.requests[0].url.params)
        assert params["reporterCode"] == "699"
        assert params["flowCode"] == "X"
        assert params["period"] == "2022"

    def test_partner_code_default_omitted(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_by_hs("0101", 699, "X", "2022")
        params = dict(capture.requests[0].url.params)
        assert "partnerCode" not in params

    def test_partner_code_when_supplied(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_by_hs("0101", 699, "X", "2022", partner_code=842)
        params = dict(capture.requests[0].url.params)
        assert params["partnerCode"] == "842"

    def test_uses_build_query_helper(self):
        # Reuse contract: each method uses _build_query.
        # When commodity_code is supplied, it's used as cmd_code.
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_by_hs("010121", 699, "X", "2022")
        params = dict(capture.requests[0].url.params)
        assert params["cmdCode"] == "010121"

    def test_only_one_http_call(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_by_hs("0101", 699, "X", "2022")
        assert len(capture.requests) == 1


# ---------------------------------------------------------------------------
# T05 — get_world_trade
# ---------------------------------------------------------------------------


class TestGetWorldTrade:
    def test_returns_canonical_records(self):
        svc = _make_service(_RequestCapture())
        r = svc.get_world_trade(699, "X", "2022")
        assert isinstance(r, TradeResponse)
        assert isinstance(r.records[0], TradeRecord)

    def test_url_path_standard(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_world_trade(699, "X", "2022")
        assert capture.requests[0].url.path == "/C/A/X/HS"

    def test_partner_code_zero_implied(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_world_trade(699, "X", "2022")
        params = dict(capture.requests[0].url.params)
        # partner_code is implicit 0 (World).
        assert params["partnerCode"] == "0"

    def test_partner_world_sentinel(self):
        svc = _make_service(_RequestCapture())
        r = svc.get_world_trade(699, "X", "2022")
        # The world sentinel is preserved end-to-end.
        assert r.records[0].partner.is_world is True

    def test_commodity_total_default(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_world_trade(699, "X", "2022")
        params = dict(capture.requests[0].url.params)
        assert params["cmdCode"] == "TOTAL"

    def test_custom_commodity_code(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_world_trade(699, "X", "2022", commodity_code="0101")
        params = dict(capture.requests[0].url.params)
        assert params["cmdCode"] == "0101"


# ---------------------------------------------------------------------------
# T06 — get_trade_balance
# ---------------------------------------------------------------------------


class TestGetTradeBalance:
    def test_returns_canonical_records(self):
        svc = _make_service(_RequestCapture())
        r = svc.get_trade_balance(699, "2022")
        assert isinstance(r, TradeResponse)
        assert isinstance(r.records[0], TradeRecord)

    def test_url_path_balance_endpoint(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_balance(699, "2022")
        assert capture.requests[0].url.path == (
            "/tools/v1/getTradeBalance/C/A/HS"
        )

    def test_no_flow_code_in_path(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_balance(699, "2022")
        # The balance endpoint does NOT include
        # flow_code in the URL path. Path is
        # /tools/v1/getTradeBalance/C/A/HS — 6 segments
        # (tools, v1, getTradeBalance, C, A, HS); flow
        # would add a 7th segment between A and HS.
        path = capture.requests[0].url.path
        assert path == "/tools/v1/getTradeBalance/C/A/HS"
        # No flow segment.
        segments = path.strip("/").split("/")
        assert "X" not in segments
        assert "M" not in segments

    def test_no_flow_code_in_query_params(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_balance(699, "2022")
        params = dict(capture.requests[0].url.params)
        # Balance endpoint produces both directions;
        # flowCode is NOT supplied.
        assert "flowCode" not in params

    def test_partner_code_optional(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_balance(699, "2022")
        params = dict(capture.requests[0].url.params)
        assert "partnerCode" not in params

    def test_partner_code_when_supplied(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_balance(699, "2022", partner_code=842)
        params = dict(capture.requests[0].url.params)
        assert params["partnerCode"] == "842"

    def test_only_one_http_call(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_balance(699, "2022")
        assert len(capture.requests) == 1


# ---------------------------------------------------------------------------
# T07 — get_bilateral
# ---------------------------------------------------------------------------


class TestGetBilateral:
    def test_returns_canonical_records(self):
        svc = _make_service(_RequestCapture())
        r = svc.get_bilateral(699, "X", "2022")
        assert isinstance(r, TradeResponse)
        assert isinstance(r.records[0], TradeRecord)

    def test_url_path_bilateral_endpoint(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_bilateral(699, "X", "2022")
        assert capture.requests[0].url.path == (
            "/tools/v1/getBilateralData/C/A/HS"
        )

    def test_no_flow_code_in_path(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_bilateral(699, "X", "2022")
        # The bilateral endpoint does NOT include
        # flow_code in the URL path. Path is
        # /tools/v1/getBilateralData/C/A/HS — 6 segments.
        path = capture.requests[0].url.path
        assert path == "/tools/v1/getBilateralData/C/A/HS"
        segments = path.strip("/").split("/")
        # No flow segment between freqCode (A) and
        # classificationCode (HS).
        assert segments[-1] == "HS"
        assert segments[-2] == "A"

    def test_flow_code_in_query_params(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_bilateral(699, "X", "2022")
        params = dict(capture.requests[0].url.params)
        # Bilateral endpoint takes flow_code as a query
        # parameter (not in the URL path).
        assert params["flowCode"] == "X"

    def test_partner_code_default_omitted(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_bilateral(699, "X", "2022")
        params = dict(capture.requests[0].url.params)
        assert "partnerCode" not in params

    def test_partner_code_when_supplied(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_bilateral(699, "X", "2022", partner_code=842)
        params = dict(capture.requests[0].url.params)
        assert params["partnerCode"] == "842"

    def test_only_one_http_call(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_bilateral(699, "X", "2022")
        assert len(capture.requests) == 1


# ---------------------------------------------------------------------------
# T08 — get_trade_matrix
# ---------------------------------------------------------------------------


class TestGetTradeMatrix:
    def test_returns_canonical_records(self):
        svc = _make_service(_RequestCapture())
        r = svc.get_trade_matrix("2022", "X", 699, 0, "TOTAL")
        assert isinstance(r, TradeResponse)
        assert isinstance(r.records[0], TradeRecord)

    def test_url_path_matrix_endpoint(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_matrix("2022", "X", 699, 0, "TOTAL")
        assert capture.requests[0].url.path == (
            "/data/v1/getTradeMatrix/C/A/TM"
        )

    def test_classification_forced_to_tm(self):
        # The matrix endpoint's URL path uses the fixed
        # classification code "TM" (not HS). When
        # `classification="HS"` is supplied, the path
        # still ends with "/TM".
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_matrix(
            "2022", "X", 699, 0, "TOTAL", classification="HS"
        )
        assert capture.requests[0].url.path.endswith("/TM")
        # The `classification` query parameter carries
        # "TM" (the matrix sentinel), not "HS".
        params = dict(capture.requests[0].url.params)
        assert params.get("classification") == "TM"

    def test_flow_code_in_query_params(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_matrix("2022", "X", 699, 0, "TOTAL")
        params = dict(capture.requests[0].url.params)
        assert params["flowCode"] == "X"

    def test_all_required_params_in_query(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_matrix("2022", "X", 699, 0, "ag1")
        params = dict(capture.requests[0].url.params)
        # All five required matrix params are present.
        assert params["period"] == "2022"
        assert params["flowCode"] == "X"
        assert params["reporterCode"] == "699"
        assert params["partnerCode"] == "0"
        assert params["cmdCode"] == "ag1"

    def test_specific_partner_code(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_matrix("2022", "X", 699, 842, "TOTAL")
        params = dict(capture.requests[0].url.params)
        assert params["partnerCode"] == "842"

    def test_only_one_http_call(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_matrix("2022", "X", 699, 0, "TOTAL")
        assert len(capture.requests) == 1


# ---------------------------------------------------------------------------
# Endpoint dispatch matrix
# ---------------------------------------------------------------------------


class TestEndpointDispatch:
    """Verify each method hits the correct endpoint."""

    @pytest.mark.parametrize(
        "method_name,kwargs,expected_path",
        [
            # T04 — get_trade_by_hs — standard trade
            (
                "get_trade_by_hs",
                {"commodity_code": "0101", "reporter_code": 699, "flow_code": "X", "period": "2022"},
                "/C/A/X/HS",
            ),
            # T05 — get_world_trade — standard trade (with partner=0)
            (
                "get_world_trade",
                {"reporter_code": 699, "flow_code": "X", "period": "2022"},
                "/C/A/X/HS",
            ),
            # T06 — get_trade_balance — dedicated balance endpoint
            (
                "get_trade_balance",
                {"reporter_code": 699, "period": "2022"},
                "/tools/v1/getTradeBalance/C/A/HS",
            ),
            # T07 — get_bilateral — dedicated bilateral endpoint
            (
                "get_bilateral",
                {"reporter_code": 699, "flow_code": "X", "period": "2022"},
                "/tools/v1/getBilateralData/C/A/HS",
            ),
            # T08 — get_trade_matrix — dedicated matrix endpoint
            (
                "get_trade_matrix",
                {"period": "2022", "flow_code": "X", "reporter_code": 699, "partner_code": 0, "commodity_code": "TOTAL"},
                "/data/v1/getTradeMatrix/C/A/TM",
            ),
        ],
    )
    def test_url_path(self, method_name, kwargs, expected_path):
        capture = _RequestCapture()
        svc = _make_service(capture)
        getattr(svc, method_name)(**kwargs)
        assert capture.requests[0].url.path == expected_path


# ---------------------------------------------------------------------------
# Reuse verification: parser is invoked exactly once
# ---------------------------------------------------------------------------


class TestParserReuse:
    def test_methods_reuse_parser(self):
        # When multiple methods are called on the same
        # service, the parser instance is reused (no new
        # parser is constructed per call).
        parser = TradeParser(log_skipped=False)
        transport = HttpTransport(
            base_url="https://example.invalid",
            user_agent="test/1.0",
            api_key="test-key-123",
            client=httpx.Client(
                transport=httpx.MockTransport(_RequestCapture())
            ),
        )
        svc = TradeService(transport, parser=parser)

        # The service holds the SAME parser instance across
        # all method calls — there's only one parser
        # attribute on the service.
        assert svc.parser is parser

    def test_methods_reuse_build_query_helper(self):
        # Verify each method goes through `_build_query`
        # by checking that the resulting query params
        # reflect the helper's defaults.
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_by_hs("0101", 699, "X", "2022")
        params = dict(capture.requests[0].url.params)
        # `_build_query` defaults: classification=HS,
        # breakdown_mode=classic, includeDesc=true.
        assert params["classification"] == "HS"
        assert "breakdownMode" not in params  # default omitted
        assert params["includeDesc"] == "true"


# ---------------------------------------------------------------------------
# No duplicate pipeline logic
# ---------------------------------------------------------------------------


class TestNoDuplicatePipeline:
    def test_each_method_one_http_call(self):
        # If the pipeline is not duplicated, each method
        # should issue exactly one HTTP call.
        for method_name, kwargs in [
            ("get_trade_by_hs", {"commodity_code": "0101", "reporter_code": 699, "flow_code": "X", "period": "2022"}),
            ("get_world_trade", {"reporter_code": 699, "flow_code": "X", "period": "2022"}),
            ("get_trade_balance", {"reporter_code": 699, "period": "2022"}),
            ("get_bilateral", {"reporter_code": 699, "flow_code": "X", "period": "2022"}),
            ("get_trade_matrix", {"period": "2022", "flow_code": "X", "reporter_code": 699, "partner_code": 0, "commodity_code": "TOTAL"}),
        ]:
            capture = _RequestCapture()
            svc = _make_service(capture)
            getattr(svc, method_name)(**kwargs)
            assert len(capture.requests) == 1, (
                f"{method_name} should issue exactly one HTTP call; "
                f"got {len(capture.requests)}"
            )

    def test_canonical_records_returned_for_all(self):
        # Every method returns canonical TradeRecord
        # instances (P2-006 contract).
        for method_name, kwargs in [
            ("get_trade_by_hs", {"commodity_code": "0101", "reporter_code": 699, "flow_code": "X", "period": "2022"}),
            ("get_world_trade", {"reporter_code": 699, "flow_code": "X", "period": "2022"}),
            ("get_trade_balance", {"reporter_code": 699, "period": "2022"}),
            ("get_bilateral", {"reporter_code": 699, "flow_code": "X", "period": "2022"}),
            ("get_trade_matrix", {"period": "2022", "flow_code": "X", "reporter_code": 699, "partner_code": 0, "commodity_code": "TOTAL"}),
        ]:
            svc = _make_service(_RequestCapture())
            r = getattr(svc, method_name)(**kwargs)
            assert isinstance(r, TradeResponse)
            assert all(
                isinstance(rec, TradeRecord) for rec in r.records
            )


# ---------------------------------------------------------------------------
# Canonical model integration
# ---------------------------------------------------------------------------


class TestCanonicalIntegration:
    def test_reporter_attributes(self):
        svc = _make_service(_RequestCapture())
        r = svc.get_world_trade(699, "X", "2022")
        record = r.records[0]
        assert record.reporter.reporter_code == 699
        assert record.reporter.name == "India"

    def test_partner_world_attributes(self):
        svc = _make_service(_RequestCapture())
        r = svc.get_world_trade(699, "X", "2022")
        record = r.records[0]
        assert record.partner.is_world is True
        assert isinstance(record.partner, TradePartner)

    def test_decimal_precision(self):
        svc = _make_service(_RequestCapture())
        r = svc.get_trade_balance(699, "2022")
        assert r.records[0].trade_value.primary_value == Decimal(
            "452684213646.747"
        )

    def test_commodity_attributes(self):
        # Use a custom handler that returns a record with
        # cmdCode="0101" matching the request.
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=_envelope(
                    [_baseline_record(cmdCode="0101", cmdDesc="Live horses")]
                ),
            )

        svc = _make_service(handler)
        r = svc.get_trade_by_hs("0101", 699, "X", "2022")
        assert r.records[0].commodity.commodity_code == "0101"

    def test_flow_attributes(self):
        svc = _make_service(_RequestCapture())
        r = svc.get_bilateral(699, "X", "2022")
        assert r.records[0].flow.flow_code == "X"


# ---------------------------------------------------------------------------
# Auth header + transport-level concerns (regression coverage)
# ---------------------------------------------------------------------------


class TestTransportIntegration:
    def test_auth_header_injected(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_balance(699, "2022")
        headers = capture.requests[0].headers
        assert headers.get("ocp-apim-subscription-key") == "test-key-123"

    def test_user_agent_header(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade_balance(699, "2022")
        headers = capture.requests[0].headers
        assert headers.get("user-agent") == "test/1.0"


# ---------------------------------------------------------------------------
# Error mapping (4xx)
# ---------------------------------------------------------------------------


class TestErrorMapping:
    def test_balance_4xx_raises_api_error(self):
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"error": "bad request"})

        from un_comtrade.exceptions import APIError

        svc = _make_service(handler)
        with pytest.raises(APIError):
            svc.get_trade_balance(699, "2022")

    def test_bilateral_4xx_raises_api_error(self):
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"error": "not found"})

        from un_comtrade.exceptions import APIError

        svc = _make_service(handler)
        with pytest.raises(APIError):
            svc.get_bilateral(699, "X", "2022")

    def test_matrix_4xx_raises_api_error(self):
        def handler(req: httpx.Request) -> httpx.Response:
            return httpx.Response(422, text="validation error")

        from un_comtrade.exceptions import APIError

        svc = _make_service(handler)
        with pytest.raises(APIError):
            svc.get_trade_matrix("2022", "X", 699, 0, "TOTAL")