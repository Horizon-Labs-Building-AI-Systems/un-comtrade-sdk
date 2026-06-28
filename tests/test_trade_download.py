"""Integration tests for annual + monthly trade retrieval.

Per the P2-005 task scope, the trade methods
(`get_exports`, `get_imports`, `get_trade` +
`get_monthly_*` variants) are wired end-to-end:
they build a `TradeQuery`, build the URL path,
issue a GET via the `HttpTransport`, validate the
response envelope, and return a canonical
`TradeResponse`.

No pagination. No batch downloads. No record-level
parsing — records are passed through as raw upstream
dicts.

All tests use `httpx.MockTransport` so the suite never
hits the upstream network. The tests assert:

- URL path construction (`/{trade_type}/{freqCode}/{flowCode}/{classificationCode}`)
- Query parameter mapping (camelCase, period format,
  reporter / partner / cmd code, breakdown mode,
  includeDesc default)
- Annual vs monthly frequency selection
- World sentinel handling (`partner_code=0`)
- TradeValue default classification (HS) and
  default breakdown mode (classic)
- Edition override
- Response envelope validation (count, elapsed_seconds,
  error, records, upstream_url)
- Non-2xx upstream mapping (4xx -> APIError, 5xx ->
  ServerError; auth 401/403 already raised by transport)
- Malformed JSON -> SerializationError
- Empty results (count=0, records=[])
"""

from __future__ import annotations

import json
from typing import Any, Callable

import httpx
import pytest

from un_comtrade.config import Configuration
from un_comtrade.exceptions import (
    APIError,
    SerializationError,
    ServerError,
)
from un_comtrade.models import TradeResponse
from un_comtrade.trade import TradeService
from un_comtrade.transport import HttpTransport


# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def configuration() -> Configuration:
    return Configuration(api_key="test-key-123")


def _make_transport(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    api_key: str = "test-key-123",
) -> HttpTransport:
    """Build an `HttpTransport` backed by an `httpx.MockTransport` handler."""
    return HttpTransport(
        base_url="https://example.invalid",
        user_agent="test/1.0",
        api_key=api_key,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def _make_service(handler: Callable[[httpx.Request], httpx.Response]) -> TradeService:
    """Build a `TradeService` wired to a mock handler.

    A default `TradeParser` is injected so the response
    records are returned as canonical `TradeRecord`
    instances (the P2-006 contract). Tests that want
    raw-dict behavior can pass `parser=None` explicitly
    via the constructor.
    """
    from un_comtrade.parser import TradeParser
    return TradeService(_make_transport(handler), parser=TradeParser())


def _ok_payload(records: list[dict[str, Any]] | None = None, **overrides) -> dict[str, Any]:
    """Build a canned upstream success envelope."""
    payload: dict[str, Any] = {
        "count": len(records) if records is not None else 0,
        "data": records if records is not None else [],
        "elapsed_seconds": 0.27,
        "error": "",
    }
    payload.update(overrides)
    return payload


def _canned_record(
    *,
    reporter_code: int = 699,
    partner_code: int = 0,
    flow_code: str = "X",
    cmd_code: str = "TOTAL",
    period: str = "2022",
    primary_value: float | None = 452684213646.747,
) -> dict[str, Any]:
    """Build a single canned upstream record (raw, camelCase)."""
    return {
        "typeCode": "C",
        "freqCode": "A",
        "refPeriodId": 20220101,
        "refYear": 2022,
        "refMonth": 52,
        "period": period,
        "reporterCode": reporter_code,
        "reporterISO": "IND",
        "reporterDesc": "India",
        "flowCode": flow_code,
        "flowDesc": "Export",
        "partnerCode": partner_code,
        "partnerISO": "W00" if partner_code == 0 else "USA",
        "partnerDesc": "World" if partner_code == 0 else "USA",
        "classificationCode": "H6",
        "classificationSearchCode": "HS",
        "cmdCode": cmd_code,
        "cmdDesc": "All Commodities",
        "aggrLevel": 0,
        "isLeaf": False,
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
        "fobvalue": primary_value,
        "primaryValue": primary_value,
        "legacyEstimationFlag": 0,
        "isReported": False,
        "isAggregate": True,
    }


class _RequestCapture:
    """Capture requests observed by the mock handler."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, json=_ok_payload(records=[_canned_record()]))


# ---------------------------------------------------------------------------
# T01 — get_exports
# ---------------------------------------------------------------------------


class TestGetExports:
    def test_returns_trade_response(self):
        svc = _make_service(
            lambda r: httpx.Response(200, json=_ok_payload(records=[_canned_record()]))
        )
        r = svc.get_exports(699, "2022")
        assert isinstance(r, TradeResponse)

    def test_url_path_annual_export(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_exports(699, "2022")
        path = capture.requests[0].url.path
        assert path == "/C/A/X/HS"

    def test_query_params(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_exports(699, "2022")
        params = dict(capture.requests[0].url.params)
        assert params["reporterCode"] == "699"
        assert params["period"] == "2022"
        assert params["flowCode"] == "X"
        assert params["cmdCode"] == "TOTAL"
        assert params["classification"] == "HS"
        # default includeDesc
        assert params["includeDesc"] == "true"

    def test_count_matches_records(self):
        # Two records with different partner codes (distinct
        # composite keys) — both should survive dedup.
        svc = _make_service(
            lambda r: httpx.Response(
                200,
                json=_ok_payload(
                    records=[
                        _canned_record(partner_code=0),
                        _canned_record(partner_code=842),
                    ]
                ),
            )
        )
        r = svc.get_exports(699, "2022")
        assert r.count == 2
        # Canonical surface: records is list[TradeRecord]
        # (P2-006).
        assert len(r.records) == 2
        from un_comtrade.models import TradeRecord
        assert all(isinstance(rec, TradeRecord) for rec in r.records)

    def test_records_are_canonical_trade_records(self):
        svc = _make_service(
            lambda r: httpx.Response(200, json=_ok_payload(records=[_canned_record()]))
        )
        r = svc.get_exports(699, "2022")
        # P2-006: records are TradeRecord instances, not
        # raw dicts. Access via attribute, not subscript.
        from decimal import Decimal
        from un_comtrade.models import TradeRecord
        assert isinstance(r.records[0], TradeRecord)
        assert r.records[0].reporter.reporter_code == 699
        assert r.records[0].trade_value.primary_value == Decimal(
            "452684213646.747"
        )

    def test_upstream_url_propagated(self):
        svc = _make_service(
            lambda r: httpx.Response(
                200,
                json=_ok_payload(records=[_canned_record()]),
                # Note: the URL on the response is the URL the
                # httpx.Client saw (with query string).
            )
        )
        r = svc.get_exports(699, "2022")
        assert r.upstream_url.startswith("https://example.invalid/C/A/X/HS")

    def test_elapsed_seconds_parsed(self):
        svc = _make_service(
            lambda r: httpx.Response(
                200, json=_ok_payload(records=[_canned_record()], elapsed_seconds=1.23)
            )
        )
        r = svc.get_exports(699, "2022")
        assert r.elapsed_seconds == 1.23

    def test_empty_result(self):
        svc = _make_service(
            lambda r: httpx.Response(
                200, json=_ok_payload(records=[], count=0)
            )
        )
        r = svc.get_exports(699, "2099")
        assert r.count == 0
        assert r.records == []
        assert r.error == ""


# ---------------------------------------------------------------------------
# T02 — get_imports
# ---------------------------------------------------------------------------


class TestGetImports:
    def test_url_path_annual_import(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_imports(699, "2022")
        path = capture.requests[0].url.path
        assert path == "/C/A/M/HS"

    def test_flow_code_m(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_imports(699, "2022")
        params = dict(capture.requests[0].url.params)
        assert params["flowCode"] == "M"


# ---------------------------------------------------------------------------
# T03 — get_trade (explicit flow)
# ---------------------------------------------------------------------------


class TestGetTrade:
    @pytest.mark.parametrize("flow", ["M", "X", "RX", "RM"])
    def test_url_path_explicit_flow(self, flow):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade(699, flow, "2022")
        path = capture.requests[0].url.path
        assert path == f"/C/A/{flow}/HS"

    def test_period_passed_through(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade(699, "X", "2022,2023")
        params = dict(capture.requests[0].url.params)
        assert params["period"] == "2022,2023"


# ---------------------------------------------------------------------------
# T09-T11 — monthly variants
# ---------------------------------------------------------------------------


class TestGetMonthlyExports:
    def test_url_path_monthly_export(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_monthly_exports(699, "202201")
        path = capture.requests[0].url.path
        assert path == "/C/M/X/HS"

    def test_period_yyyymm(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_monthly_exports(699, "202201")
        params = dict(capture.requests[0].url.params)
        assert params["period"] == "202201"

    def test_multiple_months(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_monthly_exports(699, "202201,202202,202203")
        params = dict(capture.requests[0].url.params)
        assert params["period"] == "202201,202202,202203"


class TestGetMonthlyImports:
    def test_url_path_monthly_import(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_monthly_imports(699, "202201")
        path = capture.requests[0].url.path
        assert path == "/C/M/M/HS"


class TestGetMonthlyTrade:
    def test_url_path_monthly_trade(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_monthly_trade(699, "X", "202201")
        path = capture.requests[0].url.path
        assert path == "/C/M/X/HS"

    def test_explicit_flow(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_monthly_trade(699, "M", "202201")
        path = capture.requests[0].url.path
        assert path == "/C/M/M/HS"


# ---------------------------------------------------------------------------
# Annual vs monthly dispatch
# ---------------------------------------------------------------------------


class TestFrequencyDispatch:
    def test_annual_methods_use_A(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_exports(699, "2022")
        assert "/C/A/" in capture.requests[0].url.path

    def test_monthly_methods_use_M(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_monthly_exports(699, "202201")
        assert "/C/M/" in capture.requests[0].url.path

    def test_get_trade_uses_A(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_trade(699, "X", "2022")
        assert "/C/A/" in capture.requests[0].url.path

    def test_get_monthly_trade_uses_M(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_monthly_trade(699, "X", "202201")
        assert "/C/M/" in capture.requests[0].url.path


# ---------------------------------------------------------------------------
# Defaults (classification, breakdown mode, includeDesc)
# ---------------------------------------------------------------------------


class TestDefaults:
    def test_default_classification_hs(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_exports(699, "2022")
        params = dict(capture.requests[0].url.params)
        assert params["classification"] == "HS"

    def test_default_breakdown_classic(self):
        # Per TradeQuery.to_query_params contract, the
        # default breakdown mode ("classic") is OMITTED
        # from the query string. Only non-default values
        # are emitted.
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_exports(699, "2022")
        params = dict(capture.requests[0].url.params)
        assert "breakdownMode" not in params

    def test_default_include_desc_true(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_exports(699, "2022")
        params = dict(capture.requests[0].url.params)
        assert params["includeDesc"] == "true"

    def test_custom_classification(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_exports(699, "2022", classification="SITC")
        params = dict(capture.requests[0].url.params)
        assert params["classification"] == "SITC"
        # path uses the explicit classification
        assert capture.requests[0].url.path.endswith("/SITC")

    def test_custom_breakdown_mode(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_exports(699, "2022", breakdown_mode="plus")
        params = dict(capture.requests[0].url.params)
        assert params["breakdownMode"] == "plus"

    def test_max_records(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_exports(699, "2022", max_records=100)
        params = dict(capture.requests[0].url.params)
        assert params["maxRecords"] == "100"

    def test_service_level_defaults_override(self):
        # Service-level default_classification="SITC" should be
        # used when the method doesn't override.
        capture = _RequestCapture()
        transport = _make_transport(capture)
        svc = TradeService(
            transport,
            default_classification="SITC",
            default_breakdown_mode="plus",
        )
        svc.get_exports(699, "2022")
        params = dict(capture.requests[0].url.params)
        assert params["classification"] == "SITC"
        assert params["breakdownMode"] == "plus"
        assert capture.requests[0].url.path.endswith("/SITC")


# ---------------------------------------------------------------------------
# Edition override (classification edition)
# ---------------------------------------------------------------------------


class TestEditionOverride:
    def test_edition_replaces_classification_value(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_exports(699, "2022", classification="HS", edition="H2022")
        params = dict(capture.requests[0].url.params)
        # Edition overrides the classification value in the same field.
        assert params["classification"] == "H2022"
        # Path uses the edition.
        assert capture.requests[0].url.path.endswith("/H2022")


# ---------------------------------------------------------------------------
# World sentinel (partner_code=0)
# ---------------------------------------------------------------------------


class TestWorldSentinel:
    def test_default_partner_code_is_absent(self):
        # When partner_code is None (default), the upstream
        # parameter partnerCode is omitted from the query
        # string (per TradeQuery.to_query_params contract).
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_exports(699, "2022")
        params = dict(capture.requests[0].url.params)
        assert "partnerCode" not in params

    def test_world_partner_zero_in_payload(self):
        # When partner_code=0 is supplied, the upstream
        # receives partnerCode=0.
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_exports(699, "2022", partner_code=0)
        params = dict(capture.requests[0].url.params)
        assert params["partnerCode"] == "0"

    def test_specific_partner(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_exports(699, "2022", partner_code=842)
        params = dict(capture.requests[0].url.params)
        assert params["partnerCode"] == "842"


# ---------------------------------------------------------------------------
# Commodity code
# ---------------------------------------------------------------------------


class TestCommodityCode:
    def test_total_default(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_exports(699, "2022")
        params = dict(capture.requests[0].url.params)
        assert params["cmdCode"] == "TOTAL"

    def test_specific_hs_code(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_exports(699, "2022", commodity_code="0101")
        params = dict(capture.requests[0].url.params)
        assert params["cmdCode"] == "0101"


# ---------------------------------------------------------------------------
# Response envelope validation
# ---------------------------------------------------------------------------


class TestResponseEnvelope:
    def test_count_zero_records_empty(self):
        svc = _make_service(
            lambda r: httpx.Response(
                200,
                json={
                    "count": 0,
                    "data": [],
                    "elapsed_seconds": 0.0,
                    "error": "",
                },
            )
        )
        r = svc.get_exports(699, "2099")
        assert r.count == 0
        assert r.records == []
        assert r.elapsed_seconds == 0.0

    def test_elapsed_seconds_int(self):
        svc = _make_service(
            lambda r: httpx.Response(
                200, json=_ok_payload(records=[_canned_record()], elapsed_seconds=0)
            )
        )
        r = svc.get_exports(699, "2022")
        # Upstream may return int; we coerce to float.
        assert r.elapsed_seconds == 0

    def test_elapsed_seconds_missing(self):
        # Missing elapsed_seconds -> defaults to 0.
        svc = _make_service(
            lambda r: httpx.Response(
                200,
                json={"count": 0, "data": [], "error": ""},
            )
        )
        r = svc.get_exports(699, "2022")
        assert r.elapsed_seconds == 0.0

    def test_error_message_propagated(self):
        svc = _make_service(
            lambda r: httpx.Response(
                200, json=_ok_payload(records=[], error="No data available")
            )
        )
        r = svc.get_exports(699, "2099")
        assert r.error == "No data available"

    def test_data_field_renamed_to_records(self):
        svc = _make_service(
            lambda r: httpx.Response(
                200,
                json=_ok_payload(
                    records=[
                        _canned_record(partner_code=0),
                        _canned_record(partner_code=842),
                    ]
                ),
            )
        )
        r = svc.get_exports(699, "2022")
        # Canonical name is `records`, not `data`. Records
        # are TradeRecord instances (P2-006).
        from un_comtrade.models import TradeRecord
        assert len(r.records) == 2
        assert all(isinstance(rec, TradeRecord) for rec in r.records)


# ---------------------------------------------------------------------------
# Error mapping (4xx, 5xx, malformed JSON)
# ---------------------------------------------------------------------------


class TestErrorMapping:
    def test_400_raises_api_error(self):
        svc = _make_service(
            lambda r: httpx.Response(400, json={"error": "bad request"})
        )
        with pytest.raises(APIError) as excinfo:
            svc.get_exports(699, "2022")
        assert excinfo.value.status_code == 400
        assert "bad request" in (excinfo.value.response_body or "")

    def test_404_raises_api_error(self):
        svc = _make_service(
            lambda r: httpx.Response(404, json={"error": "not found"})
        )
        with pytest.raises(APIError) as excinfo:
            svc.get_exports(699, "2022")
        assert excinfo.value.status_code == 404

    def test_422_raises_api_error(self):
        svc = _make_service(
            lambda r: httpx.Response(422, text="validation error")
        )
        with pytest.raises(APIError) as excinfo:
            svc.get_exports(699, "2022")
        assert excinfo.value.status_code == 422

    def test_500_retried_then_raises_retry_error(self):
        # The transport retries 5xx per ADR-0022 + ADR-0008
        # (3 attempts, exponential backoff). When the
        # retry budget is exhausted, the transport raises
        # `RetryError`. The service propagates this
        # unchanged.
        from un_comtrade.exceptions import RetryError

        svc = _make_service(
            lambda r: httpx.Response(500, text="internal error")
        )
        with pytest.raises(RetryError):
            svc.get_exports(699, "2022")

    def test_502_retried_then_raises_retry_error(self):
        from un_comtrade.exceptions import RetryError

        svc = _make_service(
            lambda r: httpx.Response(502, text="bad gateway")
        )
        with pytest.raises(RetryError):
            svc.get_exports(699, "2022")

    def test_500_with_retries_disabled_raises_server_error(self):
        # When the transport's retry policy is set to
        # `attempts=1`, 5xx surfaces as a ServerError
        # because the retry loop is bypassed.
        from un_comtrade.transport import HttpTransport, RetryPolicy

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="internal error")

        transport = HttpTransport(
            base_url="https://example.invalid",
            user_agent="test/1.0",
            api_key="test-key",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
            retry=RetryPolicy(attempts=1),
        )
        svc = TradeService(transport)
        with pytest.raises(ServerError) as excinfo:
            svc.get_exports(699, "2022")
        assert excinfo.value.status_code == 500

    def test_malformed_json_raises_serialization_error(self):
        svc = _make_service(
            lambda r: httpx.Response(200, content=b"not json {{{")
        )
        with pytest.raises(SerializationError):
            svc.get_exports(699, "2022")

    def test_json_array_not_object_raises_serialization_error(self):
        svc = _make_service(
            lambda r: httpx.Response(200, content=b"[1, 2, 3]")
        )
        with pytest.raises(SerializationError):
            svc.get_exports(699, "2022")

    def test_invalid_count_raises_serialization_error(self):
        svc = _make_service(
            lambda r: httpx.Response(
                200, json={"count": "not an int", "data": [], "error": ""}
            )
        )
        with pytest.raises(SerializationError):
            svc.get_exports(699, "2022")

    def test_invalid_elapsed_raises_serialization_error(self):
        svc = _make_service(
            lambda r: httpx.Response(
                200,
                json={"count": 0, "data": [], "elapsed_seconds": "abc", "error": ""},
            )
        )
        with pytest.raises(SerializationError):
            svc.get_exports(699, "2022")


# ---------------------------------------------------------------------------
# URL construction specifics
# ---------------------------------------------------------------------------


class TestUrlConstruction:
    @pytest.mark.parametrize(
        "method_name,kwargs,expected_path",
        [
            ("get_exports", {"reporter_code": 699, "period": "2022"}, "/C/A/X/HS"),
            ("get_imports", {"reporter_code": 699, "period": "2022"}, "/C/A/M/HS"),
            ("get_trade", {"reporter_code": 699, "flow_code": "X", "period": "2022"}, "/C/A/X/HS"),
            ("get_trade", {"reporter_code": 699, "flow_code": "M", "period": "2022"}, "/C/A/M/HS"),
            ("get_monthly_exports", {"reporter_code": 699, "period": "202201"}, "/C/M/X/HS"),
            ("get_monthly_imports", {"reporter_code": 699, "period": "202201"}, "/C/M/M/HS"),
            ("get_monthly_trade", {"reporter_code": 699, "flow_code": "X", "period": "202201"}, "/C/M/X/HS"),
        ],
    )
    def test_url_path(self, method_name, kwargs, expected_path):
        capture = _RequestCapture()
        svc = _make_service(capture)
        getattr(svc, method_name)(**kwargs)
        assert capture.requests[0].url.path == expected_path


# ---------------------------------------------------------------------------
# TradeResponse model integration
# ---------------------------------------------------------------------------


class TestResponseModel:
    def test_response_is_frozen(self):
        r = TradeResponse(
            elapsed_seconds=0.1,
            count=1,
            records=[{}],
            upstream_url="https://example/",
        )
        import dataclasses
        with pytest.raises(dataclasses.FrozenInstanceError):
            r.count = 5  # type: ignore[misc]

    def test_negative_elapsed_rejected(self):
        with pytest.raises(ValueError, match="elapsed_seconds"):
            TradeResponse(elapsed_seconds=-0.1, count=0, records=[])

    def test_negative_count_rejected(self):
        with pytest.raises(ValueError, match="count"):
            TradeResponse(elapsed_seconds=0.0, count=-1, records=[])

    def test_records_default_empty_list(self):
        r = TradeResponse(elapsed_seconds=0.0, count=0)
        assert r.records == []
        assert r.error == ""
        assert r.upstream_url == ""

    def test_pickle_roundtrip(self):
        r = TradeResponse(
            elapsed_seconds=0.1,
            count=1,
            records=[{"a": 1}],
            error="",
            upstream_url="https://example/",
        )
        import pickle
        restored = pickle.loads(pickle.dumps(r))
        assert restored == r


# ---------------------------------------------------------------------------
# HTTP-level integration
# ---------------------------------------------------------------------------


class TestHttpIntegration:
    def test_auth_header_sent(self):
        # The transport injects the Ocp-Apim-Subscription-Key
        # header; verify it reaches the upstream.
        capture = _RequestCapture()
        transport = _make_transport(capture, api_key="my-secret-key")
        svc = TradeService(transport)
        svc.get_exports(699, "2022")
        headers = capture.requests[0].headers
        assert headers.get("ocp-apim-subscription-key") == "my-secret-key"

    def test_user_agent_sent(self):
        capture = _RequestCapture()
        transport = _make_transport(capture)
        svc = TradeService(transport)
        svc.get_exports(699, "2022")
        headers = capture.requests[0].headers
        assert headers.get("user-agent") == "test/1.0"

    def test_only_one_http_call(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        svc.get_exports(699, "2022")
        assert len(capture.requests) == 1


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class TestExecuteHelper:
    def test_execute_invalid_frequency_rejected(self):
        svc = _make_service(
            lambda r: httpx.Response(200, json=_ok_payload(records=[]))
        )
        from un_comtrade.query import TradeQuery
        query = TradeQuery(reporter_code=699, period="2022")
        with pytest.raises(ValueError, match="frequency"):
            svc._execute(query, frequency="Q")  # type: ignore[arg-type]

    def test_execute_invalid_trade_type_rejected(self):
        svc = _make_service(
            lambda r: httpx.Response(200, json=_ok_payload(records=[]))
        )
        from un_comtrade.query import TradeQuery
        query = TradeQuery(reporter_code=699, period="2022")
        with pytest.raises(ValueError, match="trade_type"):
            svc._execute(query, frequency="A", trade_type="X")  # type: ignore[arg-type]

    def test_execute_uses_default_freqcode_a(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        from un_comtrade.query import TradeQuery
        query = TradeQuery(reporter_code=699, period="2022", flow_code="X")
        svc._execute(query, frequency="A")
        assert capture.requests[0].url.path == "/C/A/X/HS"

    def test_execute_uses_default_freqcode_m(self):
        capture = _RequestCapture()
        svc = _make_service(capture)
        from un_comtrade.query import TradeQuery
        query = TradeQuery(reporter_code=699, period="202201", flow_code="X")
        svc._execute(query, frequency="M")
        assert capture.requests[0].url.path == "/C/M/X/HS"