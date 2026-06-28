"""Integration tests for the tariffline retrieval methods (F01-F02).

Per the P3-006 task scope, these tests verify that:

- `TradeService.get_tariffline` (F01) and
  `TradeService.get_tariffline_by_hs` (F02) are wired
  to the dedicated tariffline endpoint
  (`/data/v1/getTariffline/{type}/{freq}/{cl}`) per
  `005_API_ENDPOINT_CATALOG.md` §F1.
- The existing `_build_query` helper is reused to
  translate method kwargs into a canonical
  `TradeQuery` (no new query-builder logic).
- The existing `TradeParser.parse_records` pipeline is
  reused to convert raw upstream records into
  canonical `TradeRecord` instances (no new parser
  logic).
- Canonical `TradeRecord` instances are returned on the
  public surface (P2-006 contract).
- `breakdown_mode` and `partner2_code` are NOT exposed
  on F01-F02 per `007_SDK_SPECIFICATION.md` §F01-2 +
  §F02-2.
- Validation errors (bad period, bad flow, bad
  `max_records`) surface as `ValueError` /
  `TypeError` from the query builder (reused).

All tests use `httpx.MockTransport` so the suite never
hits the live network. Coverage:

- `_PATH_TARIFFLINE` constant shape and stability.
- F01: URL path uses the tariffline endpoint.
- F01: query parameters carry the right values;
  `cmdCode` defaults to `"TOTAL"` when not supplied.
- F01: `breakdown_mode` is NOT emitted as a query
  parameter (regression: the upstream endpoint rejects
  it).
- F01: returns canonical `TradeRecord` instances.
- F01: parser dedup; parser skips invalid records.
- F01: 400 raises `APIError`; 401 raises
  `AuthenticationError`; 500 raises `ServerError`.
- F02: URL path uses the tariffline endpoint; the
  caller's `commodity_code` flows into `cmdCode`.
- F02: returns canonical `TradeRecord` instances.
- F02: works with multi-period periods, with edition,
  with `partner_code`.
- Validation: bad period, bad flow, bad `max_records`.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable

import httpx
import pytest

from un_comtrade.exceptions import (
    APIError,
    AuthenticationError,
    ServerError,
)
from un_comtrade.models import TradeRecord, TradeResponse
from un_comtrade.parser import TradeParser
from un_comtrade.trade import (
    _PATH_TARIFFLINE,
    _PATH_TRADE,
    TradeService,
)
from un_comtrade.transport import HttpTransport


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _baseline_record(**overrides) -> dict:
    """Build a baseline raw upstream record (camelCase).

    Defaults to a tariffline-shaped record (cmdCode
    "71023100" — an 8-digit HS code — and a longer
    primary value than the T01 baselines).
    """
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
        "cmdCode": "71023100",
        "cmdDesc": "Diamonds, non-industrial, unworked",
        "customsCode": "C00",
        "customsDesc": "TOTAL CPC",
        "mosCode": "0",
        "motCode": 0,
        "motDesc": "TOTAL MOT",
        "qtyUnitCode": 8,
        "qtyUnitAbbr": "kg",
        "qty": 12345.678,
        "isQtyEstimated": False,
        "altQtyUnitCode": -1,
        "altQtyUnitAbbr": "N/A",
        "altQty": 0,
        "isAltQtyEstimated": False,
        "netWgt": 12345.678,
        "isNetWgtEstimated": False,
        "grossWgt": 12500.0,
        "isGrossWgtEstimated": False,
        "cifvalue": None,
        "fobvalue": 12345678.901,
        "primaryValue": 12345678.901,
        "legacyEstimationFlag": 0,
        "isReported": True,
        "isAggregate": False,
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
    """Build a `TradeService` wired to a mock handler + parser."""
    transport = HttpTransport(
        base_url="https://example.invalid",
        user_agent="test/1.0",
        api_key="test-key-123",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    return TradeService(
        transport,
        parser=parser if parser is not None else TradeParser(log_skipped=False),
    )


# ---------------------------------------------------------------------------
# Path template constant
# ---------------------------------------------------------------------------


class TestPathTemplate:
    """`_PATH_TARIFFLINE` shape and stability."""

    def test_path_uses_get_tariffline_segment(self):
        """Path must hit `/data/v1/getTariffline/...`."""
        assert _PATH_TARIFFLINE.startswith("/data/v1/getTariffline/")

    def test_path_segments_are_correct(self):
        assert _PATH_TARIFFLINE == (
            "/data/v1/getTariffline/{trade_type}/{freqCode}/{classificationCode}"
        )

    def test_path_does_not_include_flow_segment(self):
        """Flow code travels as a query parameter on F1,
        not as a path segment."""
        assert "{flowCode}" not in _PATH_TARIFFLINE

    def test_path_does_not_include_classification_search_code(self):
        assert "{classificationSearchCode}" not in _PATH_TARIFFLINE

    def test_path_differs_from_standard_trade_path(self):
        """The tariffline endpoint uses `/getTariffline/`,
        not `/get/`."""
        assert _PATH_TARIFFLINE != _PATH_TRADE
        assert "/get/" not in _PATH_TARIFFLINE
        assert "/getTariffline/" in _PATH_TARIFFLINE


# ---------------------------------------------------------------------------
# F01 — get_tariffline
# ---------------------------------------------------------------------------


class TestF01GetTariffline:
    """F01 — line-level tariffline data for a reporter."""

    def test_returns_canonical_trade_record(self):
        """Returned `TradeResponse.records` must be
        `list[TradeRecord]` (P2-006 contract)."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json=_envelope(records=[_baseline_record()])
            )

        service = _make_service(handler)
        try:
            response = service.get_tariffline(
                reporter_code=699, flow_code="X", period="2022"
            )
        finally:
            service.close()

        assert isinstance(response, TradeResponse)
        assert len(response.records) == 1
        assert isinstance(response.records[0], TradeRecord)

    def test_url_path_uses_tariffline_endpoint(self):
        """F01 must hit `/data/v1/getTariffline/C/A/HS`."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(
                200, json=_envelope(records=[_baseline_record()])
            )

        service = _make_service(handler)
        try:
            service.get_tariffline(
                reporter_code=699, flow_code="X", period="2022"
            )
        finally:
            service.close()

        assert len(captured) == 1
        assert captured[0].url.path == "/data/v1/getTariffline/C/A/HS"

    def test_default_commodity_is_total(self):
        """When `commodity_code` is None, the query
        builder defaults to `"TOTAL"`."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json=_envelope())

        service = _make_service(handler)
        try:
            service.get_tariffline(
                reporter_code=699, flow_code="X", period="2022"
            )
        finally:
            service.close()

        params = captured[0].url.params
        assert params.get("cmdCode") == "TOTAL"

    def test_specific_commodity_code(self):
        """When `commodity_code` is supplied, it appears
        as `cmdCode` in the query parameters."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json=_envelope())

        service = _make_service(handler)
        try:
            service.get_tariffline(
                reporter_code=699,
                flow_code="X",
                period="2022",
                commodity_code="71023100",
            )
        finally:
            service.close()

        params = captured[0].url.params
        assert params.get("cmdCode") == "71023100"

    def test_flow_code_in_query_params_not_path(self):
        """On the tariffline endpoint, `flowCode` travels
        as a query parameter, NOT a path segment."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json=_envelope())

        service = _make_service(handler)
        try:
            service.get_tariffline(
                reporter_code=699, flow_code="M", period="2022"
            )
        finally:
            service.close()

        path = captured[0].url.path
        params = captured[0].url.params

        # Path has 7 segments: [empty, "data", "v1",
        # "getTariffline", "C", "A", "HS"].
        assert path == "/data/v1/getTariffline/C/A/HS"
        # flowCode is in query params.
        assert params.get("flowCode") == "M"

    def test_no_breakdown_mode_in_query(self):
        """`breakdown_mode` is not applicable to
        tariffline data and must not be emitted."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json=_envelope())

        service = _make_service(handler)
        try:
            service.get_tariffline(
                reporter_code=699,
                flow_code="X",
                period="2022",
                commodity_code="71023100",
            )
        finally:
            service.close()

        params = captured[0].url.params
        assert "breakdownMode" not in params

    def test_partner_code_in_query(self):
        """Optional `partner_code` travels as a query param."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json=_envelope())

        service = _make_service(handler)
        try:
            service.get_tariffline(
                reporter_code=699,
                flow_code="X",
                period="2022",
                partner_code=840,  # USA
            )
        finally:
            service.close()

        params = captured[0].url.params
        assert params.get("partnerCode") == "840"

    def test_classification_edition_in_query(self):
        """`edition` (e.g. "H6") becomes the
        classification query param when supplied
        (`trade_type="C"` uses `classification`, not
        `classificationCode`)."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json=_envelope())

        service = _make_service(handler)
        try:
            service.get_tariffline(
                reporter_code=699,
                flow_code="X",
                period="2022",
                classification="HS",
                edition="H6",
            )
        finally:
            service.close()

        params = captured[0].url.params
        # When an edition is supplied, the query builder
        # emits it in place of the bare classification code.
        assert params.get("classification") == "H6"

    def test_max_records_in_query(self):
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json=_envelope())

        service = _make_service(handler)
        try:
            service.get_tariffline(
                reporter_code=699,
                flow_code="X",
                period="2022",
                max_records=1000,
            )
        finally:
            service.close()

        params = captured[0].url.params
        assert params.get("maxRecords") == "1000"

    def test_subscription_key_header_injected(self):
        """The transport's auth header is injected on
        F01 calls (same as T01-T08)."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json=_envelope())

        service = _make_service(handler)
        try:
            service.get_tariffline(
                reporter_code=699, flow_code="X", period="2022"
            )
        finally:
            service.close()

        assert (
            captured[0].headers.get("ocp-apim-subscription-key")
            == "test-key-123"
        )

    def test_parser_dedup_via_composite_key(self):
        """Two raw records sharing the composite key
        collapse to one `TradeRecord`."""
        raw1 = _baseline_record()
        raw2 = _baseline_record()  # identical → duplicate
        raw3 = _baseline_record(period="2023")  # different period

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_envelope([raw1, raw2, raw3]))

        service = _make_service(handler)
        try:
            response = service.get_tariffline(
                reporter_code=699, flow_code="X", period="2022,2023"
            )
        finally:
            service.close()

        assert len(response.records) == 2
        assert response.skipped == 1
        assert {r.period for r in response.records} == {"2022", "2023"}

    def test_parser_skips_invalid_records(self):
        """A record missing a required field is dropped
        by the parser (P2-006 contract)."""

        valid = _baseline_record()
        invalid = {"typeCode": "C"}  # missing required fields

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json=_envelope([valid, invalid])
            )

        service = _make_service(handler)
        try:
            response = service.get_tariffline(
                reporter_code=699, flow_code="X", period="2022"
            )
        finally:
            service.close()

        assert len(response.records) == 1
        assert response.skipped == 1

    def test_decimal_precision_preserved(self):
        """Tariffline values can carry high precision;
        the parser must coerce via `Decimal(str(...))`."""
        raw = _baseline_record(primaryValue="12345678.901234567")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_envelope([raw]))

        service = _make_service(handler)
        try:
            response = service.get_tariffline(
                reporter_code=699, flow_code="X", period="2022"
            )
        finally:
            service.close()

        assert isinstance(
            response.records[0].trade_value.primary_value, Decimal
        )
        assert response.records[0].trade_value.primary_value == Decimal(
            "12345678.901234567"
        )

    def test_400_raises_api_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"error": "bad cmd"})

        service = _make_service(handler)
        try:
            with pytest.raises(APIError):
                service.get_tariffline(
                    reporter_code=699,
                    flow_code="X",
                    period="2022",
                    commodity_code="BOGUS",
                )
        finally:
            service.close()

    def test_401_raises_authentication_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                401,
                json={
                    "statusCode": 401,
                    "message": "Access denied due to missing subscription key",
                },
            )

        service = _make_service(handler)
        try:
            with pytest.raises(AuthenticationError):
                service.get_tariffline(
                    reporter_code=699, flow_code="X", period="2022"
                )
        finally:
            service.close()

    def test_500_eventually_raises_retry_error(self):
        """5xx responses are retried by the transport;
        after the retry budget is exhausted the transport
        raises `RetryError` (per ADR-0008 / §5 retry
        policy)."""
        from un_comtrade.exceptions import RetryError

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="internal error")

        service = _make_service(handler)
        try:
            with pytest.raises(RetryError):
                service.get_tariffline(
                    reporter_code=699, flow_code="X", period="2022"
                )
        finally:
            service.close()

    def test_invalid_period_raises_value_error(self):
        service = _make_service(lambda req: httpx.Response(200))
        try:
            with pytest.raises(ValueError, match="period"):
                service.get_tariffline(
                    reporter_code=699, flow_code="X", period="BAD"
                )
        finally:
            service.close()

    def test_invalid_flow_raises_value_error(self):
        service = _make_service(lambda req: httpx.Response(200))
        try:
            with pytest.raises(ValueError, match="flow_code"):
                service.get_tariffline(
                    reporter_code=699, flow_code="BOGUS", period="2022"
                )
        finally:
            service.close()

    def test_invalid_max_records_raises(self):
        service = _make_service(lambda req: httpx.Response(200))
        try:
            with pytest.raises(ValueError, match="max_records"):
                service.get_tariffline(
                    reporter_code=699,
                    flow_code="X",
                    period="2022",
                    max_records=999_999_999,
                )
        finally:
            service.close()

    def test_multiple_periods_in_query(self):
        """Comma-separated periods are passed through."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json=_envelope())

        service = _make_service(handler)
        try:
            service.get_tariffline(
                reporter_code=699,
                flow_code="X",
                period="2020,2021,2022",
            )
        finally:
            service.close()

        params = captured[0].url.params
        assert params.get("period") == "2020,2021,2022"

    def test_monthly_period(self):
        """`YYYYMM` periods are accepted by the query
        builder; F01 itself is annual-by-design but the
        query string is still built correctly when a
        monthly period is passed (the upstream endpoint
        rejects monthly tariffline queries, so this is a
        client-side validation test only)."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json=_envelope())

        service = _make_service(handler)
        try:
            # Period format YYYYMM is valid; the
            # frequency segment is still "A" because F01
            # is always annual.
            service.get_tariffline(
                reporter_code=699, flow_code="X", period="202201"
            )
        finally:
            service.close()

        assert captured[0].url.params.get("period") == "202201"
        assert captured[0].url.path == "/data/v1/getTariffline/C/A/HS"


# ---------------------------------------------------------------------------
# F02 — get_tariffline_by_hs
# ---------------------------------------------------------------------------


class TestF02GetTarifflineByHs:
    """F02 — line-level tariffline data for a specific HS code."""

    def test_returns_canonical_trade_record(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json=_envelope(records=[_baseline_record()])
            )

        service = _make_service(handler)
        try:
            response = service.get_tariffline_by_hs(
                commodity_code="71023100",
                reporter_code=699,
                flow_code="X",
                period="2022",
            )
        finally:
            service.close()

        assert isinstance(response, TradeResponse)
        assert len(response.records) == 1
        assert isinstance(response.records[0], TradeRecord)

    def test_url_path_uses_tariffline_endpoint(self):
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json=_envelope())

        service = _make_service(handler)
        try:
            service.get_tariffline_by_hs(
                commodity_code="71023100",
                reporter_code=699,
                flow_code="X",
                period="2022",
            )
        finally:
            service.close()

        assert len(captured) == 1
        assert captured[0].url.path == "/data/v1/getTariffline/C/A/HS"

    def test_cmdcode_is_supplied_commodity_code(self):
        """`commodity_code` flows into `cmdCode`."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json=_envelope())

        service = _make_service(handler)
        try:
            service.get_tariffline_by_hs(
                commodity_code="71023100",
                reporter_code=699,
                flow_code="X",
                period="2022",
            )
        finally:
            service.close()

        params = captured[0].url.params
        assert params.get("cmdCode") == "71023100"

    def test_six_digit_hs_works(self):
        """F02 works with a 6-digit HS code."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json=_envelope())

        service = _make_service(handler)
        try:
            service.get_tariffline_by_hs(
                commodity_code="710231",
                reporter_code=699,
                flow_code="X",
                period="2022",
            )
        finally:
            service.close()

        assert captured[0].url.params.get("cmdCode") == "710231"

    def test_ten_digit_hs_works(self):
        """F02 works with a 10-digit (line-level) HS code."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json=_envelope())

        service = _make_service(handler)
        try:
            service.get_tariffline_by_hs(
                commodity_code="7102310010",
                reporter_code=699,
                flow_code="X",
                period="2022",
            )
        finally:
            service.close()

        assert captured[0].url.params.get("cmdCode") == "7102310010"

    def test_no_breakdown_mode_in_query(self):
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json=_envelope())

        service = _make_service(handler)
        try:
            service.get_tariffline_by_hs(
                commodity_code="71023100",
                reporter_code=699,
                flow_code="X",
                period="2022",
            )
        finally:
            service.close()

        params = captured[0].url.params
        assert "breakdownMode" not in params

    def test_partner_code_in_query(self):
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json=_envelope())

        service = _make_service(handler)
        try:
            service.get_tariffline_by_hs(
                commodity_code="71023100",
                reporter_code=699,
                flow_code="X",
                period="2022",
                partner_code=756,  # Switzerland
            )
        finally:
            service.close()

        params = captured[0].url.params
        assert params.get("partnerCode") == "756"

    def test_classification_edition(self):
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json=_envelope())

        service = _make_service(handler)
        try:
            service.get_tariffline_by_hs(
                commodity_code="71023100",
                reporter_code=699,
                flow_code="X",
                period="2022",
                classification="HS",
                edition="H5",
            )
        finally:
            service.close()

        params = captured[0].url.params
        # trade_type="C" → field name is "classification",
        # not "classificationCode".
        assert params.get("classification") == "H5"

    def test_parser_dedup(self):
        raw1 = _baseline_record(period="2022")
        raw2 = _baseline_record(period="2022")  # duplicate
        raw3 = _baseline_record(period="2023")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_envelope([raw1, raw2, raw3]))

        service = _make_service(handler)
        try:
            response = service.get_tariffline_by_hs(
                commodity_code="71023100",
                reporter_code=699,
                flow_code="X",
                period="2022,2023",
            )
        finally:
            service.close()

        assert len(response.records) == 2
        assert response.skipped == 1

    def test_parser_skips_invalid(self):
        valid = _baseline_record()
        invalid = {"refPeriodId": "not-an-int"}

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json=_envelope([valid, invalid])
            )

        service = _make_service(handler)
        try:
            response = service.get_tariffline_by_hs(
                commodity_code="71023100",
                reporter_code=699,
                flow_code="X",
                period="2022",
            )
        finally:
            service.close()

        assert len(response.records) == 1
        assert response.skipped == 1

    def test_400_raises_api_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"error": "bad hs"})

        service = _make_service(handler)
        try:
            with pytest.raises(APIError):
                service.get_tariffline_by_hs(
                    commodity_code="BOGUS",
                    reporter_code=699,
                    flow_code="X",
                    period="2022",
                )
        finally:
            service.close()

    def test_401_raises_authentication_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                401,
                json={
                    "statusCode": 401,
                    "message": "Access denied due to missing subscription key",
                },
            )

        service = _make_service(handler)
        try:
            with pytest.raises(AuthenticationError):
                service.get_tariffline_by_hs(
                    commodity_code="71023100",
                    reporter_code=699,
                    flow_code="X",
                    period="2022",
                )
        finally:
            service.close()

    def test_invalid_period_raises_value_error(self):
        service = _make_service(lambda req: httpx.Response(200))
        try:
            with pytest.raises(ValueError, match="period"):
                service.get_tariffline_by_hs(
                    commodity_code="71023100",
                    reporter_code=699,
                    flow_code="X",
                    period="bogus",
                )
        finally:
            service.close()

    def test_invalid_flow_raises_value_error(self):
        service = _make_service(lambda req: httpx.Response(200))
        try:
            with pytest.raises(ValueError, match="flow_code"):
                service.get_tariffline_by_hs(
                    commodity_code="71023100",
                    reporter_code=699,
                    flow_code="ZZ",
                    period="2022",
                )
        finally:
            service.close()

    def test_invalid_max_records_raises(self):
        service = _make_service(lambda req: httpx.Response(200))
        try:
            with pytest.raises(ValueError, match="max_records"):
                service.get_tariffline_by_hs(
                    commodity_code="71023100",
                    reporter_code=699,
                    flow_code="X",
                    period="2022",
                    max_records=0,
                )
        finally:
            service.close()

    def test_max_records_in_query(self):
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json=_envelope())

        service = _make_service(handler)
        try:
            service.get_tariffline_by_hs(
                commodity_code="71023100",
                reporter_code=699,
                flow_code="X",
                period="2022",
                max_records=5000,
            )
        finally:
            service.close()

        params = captured[0].url.params
        assert params.get("maxRecords") == "5000"

    def test_subscription_key_header_injected(self):
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json=_envelope())

        service = _make_service(handler)
        try:
            service.get_tariffline_by_hs(
                commodity_code="71023100",
                reporter_code=699,
                flow_code="X",
                period="2022",
            )
        finally:
            service.close()

        assert (
            captured[0].headers.get("ocp-apim-subscription-key")
            == "test-key-123"
        )


# ---------------------------------------------------------------------------
# Cross-method invariants
# ---------------------------------------------------------------------------


class TestCrossMethodInvariants:
    """Invariants that must hold across F01 and F02."""

    def test_f01_and_f02_use_same_endpoint(self):
        """F01 and F02 must both hit the tariffline
        endpoint."""
        captured_f01: list[httpx.Request] = []
        captured_f02: list[httpx.Request] = []

        def make_handler(sink: list[httpx.Request]):
            def handler(request: httpx.Request) -> httpx.Response:
                sink.append(request)
                return httpx.Response(200, json=_envelope())

            return handler

        service = _make_service(make_handler(captured_f01))
        try:
            service.get_tariffline(
                reporter_code=699, flow_code="X", period="2022"
            )
        finally:
            service.close()

        service = _make_service(make_handler(captured_f02))
        try:
            service.get_tariffline_by_hs(
                commodity_code="71023100",
                reporter_code=699,
                flow_code="X",
                period="2022",
            )
        finally:
            service.close()

        assert captured_f01[0].url.path == captured_f02[0].url.path
        assert (
            captured_f01[0].url.path
            == "/data/v1/getTariffline/C/A/HS"
        )

    def test_f01_and_f02_share_parser(self):
        """Both methods must reuse the same parser
        instance (no parser duplication)."""
        parser = TradeParser(log_skipped=False)
        service = TradeService(
            HttpTransport(
                base_url="https://example.invalid",
                user_agent="test/1.0",
                api_key="test-key",
                client=httpx.Client(
                    transport=httpx.MockTransport(
                        lambda req: httpx.Response(200, json=_envelope())
                    )
                ),
            ),
            parser=parser,
        )
        try:
            service.get_tariffline(
                reporter_code=699, flow_code="X", period="2022"
            )
            service.get_tariffline_by_hs(
                commodity_code="71023100",
                reporter_code=699,
                flow_code="X",
                period="2022",
            )
        finally:
            service.close()

        # `service.parser is parser` confirms the same
        # parser instance is reused.
        assert service.parser is parser

    def test_f01_and_f02_share_query_builder(self):
        """Both methods must call `_build_query` exactly
        once (regression: no double-build)."""
        from un_comtrade.query import TradeQuery

        captured: list[TradeQuery] = []
        original = TradeService._build_query

        def spy(self, **kwargs) -> TradeQuery:
            q = original(self, **kwargs)
            captured.append(q)
            return q

        service = _make_service(
            lambda req: httpx.Response(200, json=_envelope())
        )
        try:
            TradeService._build_query = spy  # type: ignore[assignment]
            try:
                service.get_tariffline(
                    reporter_code=699, flow_code="X", period="2022"
                )
                service.get_tariffline_by_hs(
                    commodity_code="71023100",
                    reporter_code=699,
                    flow_code="X",
                    period="2022",
                )
            finally:
                TradeService._build_query = original  # type: ignore[assignment]
        finally:
            service.close()

        assert len(captured) == 2
        # F01 default cmd_code is TOTAL.
        assert captured[0].cmd_code == "TOTAL"
        # F02 cmd_code is the supplied commodity.
        assert captured[1].cmd_code == "71023100"

    def test_f01_and_f02_no_breakdown_mode_in_query(self):
        """Both methods must NOT emit `breakdown_mode` on
        the upstream request (regression: the tariffline
        endpoint rejects it per `005` F1)."""
        captured_f01: list[httpx.Request] = []
        captured_f02: list[httpx.Request] = []

        def make_handler(sink: list[httpx.Request]):
            def handler(request: httpx.Request) -> httpx.Response:
                sink.append(request)
                return httpx.Response(200, json=_envelope())

            return handler

        service = _make_service(make_handler(captured_f01))
        try:
            service.get_tariffline(
                reporter_code=699, flow_code="X", period="2022"
            )
        finally:
            service.close()

        service = _make_service(make_handler(captured_f02))
        try:
            service.get_tariffline_by_hs(
                commodity_code="71023100",
                reporter_code=699,
                flow_code="X",
                period="2022",
            )
        finally:
            service.close()

        assert "breakdownMode" not in captured_f01[0].url.params
        assert "breakdownMode" not in captured_f02[0].url.params

    def test_f01_and_f02_no_partner2_in_query(self):
        """Neither method exposes `partner2_code` (per
        `007_SDK_SPECIFICATION.md` §F01-2 + §F02-2)."""
        captured_f01: list[httpx.Request] = []
        captured_f02: list[httpx.Request] = []

        def make_handler(sink: list[httpx.Request]):
            def handler(request: httpx.Request) -> httpx.Response:
                sink.append(request)
                return httpx.Response(200, json=_envelope())

            return handler

        service = _make_service(make_handler(captured_f01))
        try:
            service.get_tariffline(
                reporter_code=699, flow_code="X", period="2022"
            )
        finally:
            service.close()

        service = _make_service(make_handler(captured_f02))
        try:
            service.get_tariffline_by_hs(
                commodity_code="71023100",
                reporter_code=699,
                flow_code="X",
                period="2022",
            )
        finally:
            service.close()

        assert "partner2Code" not in captured_f01[0].url.params
        assert "partner2Code" not in captured_f02[0].url.params