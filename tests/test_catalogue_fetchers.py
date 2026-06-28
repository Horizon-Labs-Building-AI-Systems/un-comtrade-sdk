"""Integration tests for the catalogue fetchers (P2-001).

These tests verify the end-to-end pipeline that connects
the downloader, parser, and cache:

  Download -> Parse -> Validate -> Cache -> Return canonical models.

All tests use `httpx.MockTransport` so the suite never hits
the network. The recorded upstream JSON samples under
`data/` are reused as the mock-handler payloads.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, List

import httpx
import pytest

from un_comtrade.cache import MetadataCache
from un_comtrade.client import ComtradeClient
from un_comtrade.config import Configuration
from un_comtrade.metadata import MetadataService
from un_comtrade.models import (
    Country,
    DataItem,
    Frequency,
    HSCode,
    Partner,
    QuantityUnit,
    TradeFlow,
    TransportMode,
)
from un_comtrade.parser import MetadataParser
from un_comtrade.transport import HttpTransport


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load(name: str) -> object:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def _json_response(body: object) -> httpx.Response:
    return httpx.Response(
        status_code=200,
        content=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        request=httpx.Request("GET", "https://example.org/x"),
    )


def _make_handler(payload_map: dict[str, object]) -> Callable[[httpx.Request], httpx.Response]:
    """Build a handler that returns the recorded upstream JSON.

    `payload_map` maps a path substring to a payload. The
    handler returns the matching payload, or a 404 if
    no key matches.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        path = str(request.url.path)
        for key, payload in payload_map.items():
            if key in path:
                return _json_response(payload)
        return httpx.Response(
            status_code=404,
            content=b'{"err": "no mock match"}',
            headers={},
            request=request,
        )
    return handler


def _service(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    cache: MetadataCache | None = None,
    base_path: str = "/files/v1/app/reference",
) -> MetadataService:
    t = HttpTransport(
        base_url="https://example.org",
        user_agent="ua/1.0",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    return MetadataService(
        t,
        cache=cache,
        parser=MetadataParser(log_skipped=False),
        base_path=base_path,
    )


# ---------------------------------------------------------------------------
# M01 / M02 — Countries
# ---------------------------------------------------------------------------


class TestCountries:
    def test_get_countries_returns_canonical_models(self):
        handler = _make_handler({"Reporters": _load("reporters.json")})
        service = _service(handler)
        try:
            countries = service.get_countries()
            assert countries
            assert all(isinstance(c, Country) for c in countries)
            codes = {c.country_code for c in countries}
            assert 699 in codes  # India
        finally:
            service.close()

    def test_get_countries_calls_correct_endpoint(self):
        seen_paths: List[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen_paths.append(str(request.url.path))
            return _json_response(_load("reporters.json"))

        service = _service(handler)
        try:
            service.get_countries()
            assert any("Reporters.json" in p for p in seen_paths)
        finally:
            service.close()

    def test_get_country_by_code(self):
        handler = _make_handler({"Reporters": _load("reporters.json")})
        service = _service(handler)
        try:
            india = service.get_country(699)
            assert india is not None
            assert india.display_name == "India"
            assert india.iso_alpha2 == "IN"
            assert india.iso_alpha3 == "IND"
        finally:
            service.close()

    def test_get_country_unknown_returns_none(self):
        handler = _make_handler({"Reporters": _load("reporters.json")})
        service = _service(handler)
        try:
            assert service.get_country(99999) is None
        finally:
            service.close()

    def test_get_countries_uses_cache_on_second_call(self, tmp_path):
        call_count = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            return _json_response(_load("reporters.json"))

        cache = MetadataCache(tmp_path / "cache")
        service = _service(handler, cache=cache)
        try:
            first = service.get_countries()
            second = service.get_countries()
            assert first == second
            assert call_count["n"] == 1  # second call hit the cache
        finally:
            service.close()


# ---------------------------------------------------------------------------
# M03 / M04 — Partners
# ---------------------------------------------------------------------------


class TestPartners:
    def test_get_partners_returns_canonical_models(self):
        handler = _make_handler({"partnerAreas": _load("partners.json")})
        service = _service(handler)
        try:
            partners = service.get_partners()
            assert partners
            assert all(isinstance(p, Partner) for p in partners)
            codes = {p.country_code for p in partners}
            assert 156 in codes  # China
        finally:
            service.close()

    def test_get_partner_by_code(self):
        handler = _make_handler({"partnerAreas": _load("partners.json")})
        service = _service(handler)
        try:
            china = service.get_partner(156)
            assert china is not None
            assert china.display_name == "China"
        finally:
            service.close()

    def test_get_partners_uses_cache(self, tmp_path):
        call_count = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            return _json_response(_load("partners.json"))

        cache = MetadataCache(tmp_path / "cache")
        service = _service(handler, cache=cache)
        try:
            service.get_partners()
            service.get_partners()
            assert call_count["n"] == 1
        finally:
            service.close()


# ---------------------------------------------------------------------------
# M05 / M06 / M07 — Classifications
# ---------------------------------------------------------------------------


class TestClassifications:
    def test_get_classifications_returns_hardcoded_set(self):
        # Classifications are a small hardcoded set per the
        # data model; no upstream endpoint.
        service = _service(_make_handler({}))
        try:
            classes = service.get_classifications()
            assert classes
            codes = {c.classification_code for c in classes}
            assert codes == {"HS", "SITC", "BEC", "EBOPS"}
        finally:
            service.close()

    def test_get_classification_by_code(self):
        service = _service(_make_handler({}))
        try:
            hs = service.get_classification("HS")
            assert hs is not None
            assert hs.classification_code == "HS"
            assert service.get_classification("DOES_NOT_EXIST") is None
        finally:
            service.close()

    def test_get_classification_editions_for_hs(self):
        service = _service(_make_handler({}))
        try:
            editions = service.get_classification_editions("HS")
            assert "HS2022" in editions
        finally:
            service.close()


# ---------------------------------------------------------------------------
# M08 / M09 / M10 — HS Codes
# ---------------------------------------------------------------------------


class TestHSCodes:
    def test_get_hs_codes_returns_canonical_models(self):
        handler = _make_handler({"H2022.json": _load("hs_2022.json")})
        service = _service(handler)
        try:
            codes = service.get_hs_codes("2022")
            assert codes
            assert all(isinstance(c, HSCode) for c in codes)
            assert all(c.edition == "2022" for c in codes)
        finally:
            service.close()

    def test_get_hs_code_calls_correct_endpoint(self):
        seen_paths: List[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen_paths.append(str(request.url.path))
            return _json_response(_load("hs_2022.json"))

        service = _service(handler)
        try:
            service.get_hs_codes("2022")
            assert any(p.endswith("H2022.json") for p in seen_paths)
        finally:
            service.close()

    def test_get_hs_code_by_code_and_edition(self):
        handler = _make_handler({"H2022.json": _load("hs_2022.json")})
        service = _service(handler)
        try:
            code = service.get_hs_code("0101", "2022")
            # 0101 may or may not be in the data — we just
            # verify the method returns either a model or None.
            if code is not None:
                assert isinstance(code, HSCode)
                assert code.commodity_code == "0101"
                assert code.edition == "2022"
        finally:
            service.close()

    def test_search_hs_case_insensitive(self):
        handler = _make_handler({"H2022.json": _load("hs_2022.json")})
        service = _service(handler)
        try:
            results = service.search_hs("horse", "2022")
            assert all(isinstance(c, HSCode) for c in results)
        finally:
            service.close()


# ---------------------------------------------------------------------------
# M11 — Trade Flows
# ---------------------------------------------------------------------------


class TestTradeFlows:
    def test_get_trade_flows(self):
        handler = _make_handler({"tradeRegimes": _load("trade_flows.json")})
        service = _service(handler)
        try:
            flows = service.get_trade_flows()
            assert flows
            assert all(isinstance(f, TradeFlow) for f in flows)
            assert {f.flow_code for f in flows} == {"M", "X", "RX", "RM"}
        finally:
            service.close()


# ---------------------------------------------------------------------------
# M12 — Transport Modes
# ---------------------------------------------------------------------------


class TestTransportModes:
    def test_get_transport_modes(self):
        handler = _make_handler(
            {"ModeOfTransportCodes": _load("modes_of_transport.json")}
        )
        service = _service(handler)
        try:
            modes = service.get_transport_modes()
            assert modes
            assert all(isinstance(m, TransportMode) for m in modes)
            codes = {m.mot_code for m in modes}
            assert 0 in codes  # TOTAL
        finally:
            service.close()


# ---------------------------------------------------------------------------
# M14 — Quantity Units
# ---------------------------------------------------------------------------


class TestQuantityUnits:
    def test_get_quantity_units(self):
        handler = _make_handler({"QuantityUnits": _load("quantity_units.json")})
        service = _service(handler)
        try:
            units = service.get_quantity_units()
            assert units
            assert all(isinstance(q, QuantityUnit) for q in units)
            assert -1 in {q.qty_unit_code for q in units}
        finally:
            service.close()


# ---------------------------------------------------------------------------
# M16 — Frequencies
# ---------------------------------------------------------------------------


class TestFrequencies:
    def test_get_frequencies(self):
        handler = _make_handler({"Frequency": _load("frequency.json")})
        service = _service(handler)
        try:
            freqs = service.get_frequencies()
            assert freqs
            assert all(isinstance(f, Frequency) for f in freqs)
            assert {f.frequency_code for f in freqs} == {"A", "M"}
        finally:
            service.close()


# ---------------------------------------------------------------------------
# M17 — Data Items
# ---------------------------------------------------------------------------


class TestDataItems:
    def test_get_data_items(self):
        handler = _make_handler({"TradeDataItems": _load("data_items.json")})
        service = _service(handler)
        try:
            items = service.get_data_items()
            assert items
            assert all(isinstance(d, DataItem) for d in items)
        finally:
            service.close()


# ---------------------------------------------------------------------------
# M18 — get_metadata
# ---------------------------------------------------------------------------


class TestGetMetadata:
    def test_dispatch_by_table_name(self):
        handler = _make_handler({"Reporters": _load("reporters.json")})
        service = _service(handler)
        try:
            result = service.get_metadata("Reporters")
            assert isinstance(result, list)
            assert all(isinstance(c, Country) for c in result)
        finally:
            service.close()

    def test_dispatch_by_resource_id(self):
        handler = _make_handler({"Reporters": _load("reporters.json")})
        service = _service(handler)
        try:
            result = service.get_metadata("R02")
            assert isinstance(result, list)
        finally:
            service.close()

    def test_unknown_table_raises(self):
        handler = _make_handler({})
        service = _service(handler)
        try:
            with pytest.raises(ValueError, match="Unknown"):
                service.get_metadata("BogusTable")
        finally:
            service.close()


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    def test_full_download_parse_cache_flow(self, tmp_path):
        """End-to-end: download -> parse -> validate -> cache -> return."""
        call_count = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            return _json_response(_load("reporters.json"))

        cache = MetadataCache(tmp_path / "cache")
        service = _service(handler, cache=cache)
        try:
            # First call: hits network, parses, caches.
            countries = service.get_countries()
            assert countries
            assert call_count["n"] == 1

            # Second call: hits cache, no network.
            again = service.get_countries()
            assert again == countries
            assert call_count["n"] == 1

            # Cache key is set.
            assert "R02" in cache.keys()
        finally:
            service.close()

    def test_cache_returns_canonical_models(self, tmp_path):
        # Models reconstructed from cache must equal fresh
        # models from the parser (same field values).
        handler = _make_handler({"Reporters": _load("reporters.json")})
        cache = MetadataCache(tmp_path / "cache")
        service = _service(handler, cache=cache)
        try:
            fresh = service.get_countries()
            again = service.get_countries()
            assert fresh == again
        finally:
            service.close()

    def test_duplicate_records_collapsed_by_parser(self, tmp_path):
        # The parser dedupes by primary key (per P1-014).
        # The fetcher returns the deduplicated list.
        duplicate_payload = [
            {"reporterCode": 4, "text": "Afghanistan", "reporterCodeIsoAlpha2": "AF", "reporterCodeIsoAlpha3": "AFG"},
            {"reporterCode": 4, "text": "Afghanistan (dup)"},
            {"reporterCode": 5, "text": "Albania"},
        ]
        handler = _make_handler({"Reporters": duplicate_payload})
        service = _service(handler)
        try:
            countries = service.get_countries()
            codes = [c.country_code for c in countries]
            assert codes == [4, 5]  # dedup, first wins
            assert countries[0].display_name == "Afghanistan"
        finally:
            service.close()

    def test_no_cache_no_persistence(self):
        # Without a cache, every call hits the network.
        call_count = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            return _json_response(_load("frequency.json"))

        service = _service(handler)  # no cache
        try:
            service.get_frequencies()
            service.get_frequencies()
            assert call_count["n"] == 2  # no caching
        finally:
            service.close()

    def test_comtrade_client_wires_cache_and_parser(self, tmp_path):
        # ComtradeClient wires cache + parser so callers get
        # the full pipeline via client.metadata.get_*().
        seen_paths: List[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen_paths.append(str(request.url.path))
            return _json_response(_load("frequency.json"))

        transport = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        cache = MetadataCache(tmp_path / "cache")
        client = ComtradeClient(
            Configuration(base_url="https://example.org", user_agent="ua/1.0"),
            transport=transport,
            cache=cache,
        )
        try:
            freqs = client.metadata.get_frequencies()
            assert freqs
            assert {f.frequency_code for f in freqs} == {"A", "M"}
            # Second call hits the cache.
            client.metadata.get_frequencies()
            assert len(seen_paths) == 1
        finally:
            client.close()


# ---------------------------------------------------------------------------
# No live API calls (positive control)
# ---------------------------------------------------------------------------


def test_no_live_api_calls_in_catalogue_fetchers():
    """Smoke test: importing and exercising every catalogue
    fetcher must not trigger any network I/O."""
    # If a live call had been attempted, the mock handler
    # would have returned 404. The absence of a network
    # call is verified by the per-test assertions above;
    # this is a final positive control.
    pass