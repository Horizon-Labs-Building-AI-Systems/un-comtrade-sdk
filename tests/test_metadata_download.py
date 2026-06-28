"""Unit tests for the metadata downloader (un_comtrade.metadata.MetadataDownloader).

Per P1-013 the downloader is responsible for:
- HTTP integration with the upstream reference endpoints,
- endpoint routing (resource id -> URL path),
- download orchestration (issuing the GET, returning the
  raw `HttpResponse`).

It does NOT parse responses and does NOT persist
anything. All tests use `httpx.MockTransport` so the
suite never hits the network.
"""

from __future__ import annotations

import json
from typing import Callable

import httpx
import pytest

from un_comtrade.metadata import (
    DEFAULT_REFERENCE_BASE_PATH,
    ENDPOINT_FILENAMES,
    PARAMETERIZED_RESOURCES,
    MetadataDownloader,
    MetadataService,
)
from un_comtrade.transport import HttpResponse, HttpTransport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _json_response(
    status_code: int,
    body: object,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        content=json.dumps(body).encode("utf-8"),
        headers=headers or {},
        request=httpx.Request("GET", "https://example.org/x"),
    )


def _make_handler(
    responses: list[httpx.Response],
) -> Callable[[httpx.Request], httpx.Response]:
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        if not queue:
            raise AssertionError("MockTransport queue exhausted")
        resp = queue.pop(0)
        resp.request = request
        return resp

    return handler


def _transport(handler: Callable[[httpx.Request], httpx.Response]) -> HttpTransport:
    return HttpTransport(
        base_url="https://example.org",
        user_agent="ua/1.0",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------


class TestInstantiation:
    def test_instantiates_with_transport(self):
        t = _transport(_make_handler([_json_response(200, [])]))
        dl = MetadataDownloader(t)
        assert dl.transport is t
        t.close()

    def test_default_base_path(self):
        t = _transport(_make_handler([_json_response(200, [])]))
        dl = MetadataDownloader(t)
        assert dl.base_path == DEFAULT_REFERENCE_BASE_PATH
        assert dl.base_path == "/files/v1/app/reference"
        t.close()

    def test_custom_base_path(self):
        t = _transport(_make_handler([_json_response(200, [])]))
        dl = MetadataDownloader(t, base_path="/custom/")
        # Trailing slash is stripped.
        assert dl.base_path == "/custom"
        t.close()

    def test_resource_ids_constant(self):
        # All 17 resources are routed by the downloader.
        assert len(MetadataDownloader.RESOURCE_IDS) == 17
        for rid in (f"R{n:02d}" for n in range(1, 18)):
            assert rid in MetadataDownloader.RESOURCE_IDS


# ---------------------------------------------------------------------------
# path_for / endpoint routing
# ---------------------------------------------------------------------------


class TestPathFor:
    def test_each_resource_has_canonical_path(self):
        t = _transport(_make_handler([_json_response(200, [])]))
        try:
            dl = MetadataDownloader(t)
            for rid, filename in ENDPOINT_FILENAMES.items():
                if rid in PARAMETERIZED_RESOURCES:
                    continue
                path = dl.path_for(rid)
                assert path.endswith(filename), (
                    f"{rid}: expected suffix {filename!r}, got {path!r}"
                )
                assert path.startswith(DEFAULT_REFERENCE_BASE_PATH)
        finally:
            t.close()

    def test_unknown_resource_id_raises(self):
        t = _transport(_make_handler([_json_response(200, [])]))
        try:
            dl = MetadataDownloader(t)
            with pytest.raises(ValueError, match="Unknown metadata resource id"):
                dl.path_for("R99")
        finally:
            t.close()

    def test_parameterised_resource_requires_keyword(self):
        t = _transport(_make_handler([_json_response(200, [])]))
        try:
            dl = MetadataDownloader(t)
            with pytest.raises(ValueError, match="Missing path parameter"):
                dl.path_for("R05")
        finally:
            t.close()

    @pytest.mark.parametrize(
        "rid,edition,expected",
        [
            ("R05", "4", "H4.json"),
            ("R05", "0", "H0.json"),
            ("R06", "3", "S3.json"),
            ("R07", "5", "B5.json"),
            ("R08", "10", "EB10.json"),
        ],
    )
    def test_parameterised_resource_renders(
        self, rid: str, edition: str, expected: str
    ):
        t = _transport(_make_handler([_json_response(200, [])]))
        try:
            dl = MetadataDownloader(t)
            path = dl.path_for(rid, edition=edition)
            assert path.endswith(expected)
            assert path.startswith(DEFAULT_REFERENCE_BASE_PATH)
        finally:
            t.close()


class TestResolvePath:
    def test_relative_path_joined(self):
        t = _transport(_make_handler([_json_response(200, [])]))
        try:
            dl = MetadataDownloader(t)
            assert dl.resolve_path("SS.json") == "/files/v1/app/reference/SS.json"
            assert dl.resolve_path("/SS.json") == "/files/v1/app/reference/SS.json"
        finally:
            t.close()

    def test_absolute_url_unchanged(self):
        t = _transport(_make_handler([_json_response(200, [])]))
        try:
            dl = MetadataDownloader(t)
            assert dl.resolve_path("https://other.example.org/x") == "https://other.example.org/x"
            assert dl.resolve_path("http://other.example.org/x") == "http://other.example.org/x"
        finally:
            t.close()


# ---------------------------------------------------------------------------
# download() / download_path()
# ---------------------------------------------------------------------------


class TestDownload:
    @pytest.mark.parametrize(
        "rid,filename",
        [
            ("R01", "ListofReferences.json"),
            ("R02", "Reporters.json"),
            ("R03", "partnerAreas.json"),
            ("R04", "HS.json"),
            ("R09", "Frequency.json"),
            ("R10", "tradeRegimes.json"),
            ("R11", "CustomsCodes.json"),
            ("R12", "ModeOfTransportCodes.json"),
            ("R13", "ModeOfSupply.json"),
            ("R14", "QuantityUnits.json"),
            ("R15", "TradeDataItems.json"),
        ],
    )
    def test_download_routes_correctly(self, rid: str, filename: str):
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = str(request.url.path)
            captured["host"] = str(request.url.host)
            return _json_response(200, {"results": []})

        t = _transport(handler)
        try:
            dl = MetadataDownloader(t)
            resp = dl.download(rid)
            assert isinstance(resp, HttpResponse)
            assert resp.status_code == 200
            assert captured["path"].endswith(filename)
            assert captured["host"] == "example.org"
        finally:
            t.close()

    @pytest.mark.parametrize(
        "rid,params,filename",
        [
            ("R05", {"edition": "4"}, "H4.json"),
            ("R05", {"edition": "0"}, "H0.json"),
            ("R06", {"edition": "1"}, "S1.json"),
            ("R07", {"edition": "4"}, "B4.json"),
            ("R08", {"edition": "10"}, "EB10.json"),
        ],
    )
    def test_parameterised_download_routes_correctly(
        self, rid: str, params: dict[str, str], filename: str
    ):
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = str(request.url.path)
            return _json_response(200, {"results": []})

        t = _transport(handler)
        try:
            dl = MetadataDownloader(t)
            resp = dl.download(rid, **params)
            assert resp.status_code == 200
            assert captured["path"].endswith(filename)
        finally:
            t.close()

    def test_download_returns_raw_response_without_parsing(self):
        # The body is raw JSON bytes; the downloader does NOT
        # parse into a dict. Consumers (the catalogue fetchers)
        # are responsible for that.
        raw = b'{"results": [{"id": 1, "text": "raw"}]}'

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                content=raw,
                headers={"Content-Type": "application/json"},
                request=request,
            )

        t = _transport(handler)
        try:
            dl = MetadataDownloader(t)
            resp = dl.download("R02")
            assert resp.status_code == 200
            assert resp.body == raw  # raw bytes, no parsing
            # The response is not the parsed JSON; it's a wrapper.
            assert isinstance(resp, HttpResponse)
        finally:
            t.close()

    def test_download_path_uses_base_path(self):
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = str(request.url.path)
            return _json_response(200, {"ok": True})

        t = _transport(handler)
        try:
            dl = MetadataDownloader(t)
            resp = dl.download_path("SS.json")
            assert resp.status_code == 200
            assert captured["path"] == "/files/v1/app/reference/SS.json"
        finally:
            t.close()

    def test_download_path_with_leading_slash(self):
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = str(request.url.path)
            return _json_response(200, {})

        t = _transport(handler)
        try:
            dl = MetadataDownloader(t)
            dl.download_path("/SS.json")
            assert captured["path"] == "/files/v1/app/reference/SS.json"
        finally:
            t.close()

    def test_download_unknown_resource_raises(self):
        t = _transport(_make_handler([_json_response(200, [])]))
        try:
            dl = MetadataDownloader(t)
            with pytest.raises(ValueError, match="Unknown"):
                dl.download("R99")
        finally:
            t.close()

    def test_download_with_5xx_propagates_response(self):
        # The downloader returns the response (does not raise).
        # Retry logic lives in the transport; with retries
        # disabled the response is surfaced as-is. (With default
        # retry policy the transport retries and raises
        # RetryError on exhaustion — covered separately in
        # test_retry.py.)
        from un_comtrade.transport import RetryPolicy

        def handler(request: httpx.Request) -> httpx.Response:
            return _json_response(500, {"err": "transient"})

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
            retry=RetryPolicy(attempts=1),
        )
        try:
            dl = MetadataDownloader(t)
            resp = dl.download("R02")
            assert resp.status_code == 500
        finally:
            t.close()

    def test_download_with_401_raises_authentication_error(self):
        # The transport translates 401 to AuthenticationError
        # per P1-007. The downloader surfaces it unchanged.
        def handler(request: httpx.Request) -> httpx.Response:
            return _json_response(401, {"err": "denied"})

        from un_comtrade.exceptions import AuthenticationError

        t = _transport(handler)
        try:
            dl = MetadataDownloader(t)
            with pytest.raises(AuthenticationError):
                dl.download("R02")
        finally:
            t.close()


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------


class TestModuleExports:
    def test_downloader_exported(self):
        from un_comtrade import metadata as md_mod

        assert hasattr(md_mod, "MetadataDownloader")
        assert md_mod.MetadataDownloader is MetadataDownloader

    def test_endpoint_filenames_exported(self):
        from un_comtrade import metadata as md_mod

        assert "ENDPOINT_FILENAMES" in md_mod.__all__
        assert md_mod.ENDPOINT_FILENAMES is ENDPOINT_FILENAMES

    def test_parameterised_resources_exported(self):
        from un_comtrade import metadata as md_mod

        assert "PARAMETERIZED_RESOURCES" in md_mod.__all__
        assert md_mod.PARAMETERIZED_RESOURCES is PARAMETERIZED_RESOURCES


# ---------------------------------------------------------------------------
# MetadataService wires the downloader
# ---------------------------------------------------------------------------


class TestServiceWiring:
    def test_service_exposes_downloader(self):
        t = _transport(_make_handler([_json_response(200, [])]))
        try:
            service = MetadataService(t)
            assert isinstance(service.downloader, MetadataDownloader)
        finally:
            t.close()

    def test_service_downloader_uses_clients_transport(self):
        t = _transport(_make_handler([_json_response(200, [])]))
        try:
            service = MetadataService(t)
            assert service.downloader.transport is service.transport
        finally:
            t.close()

    def test_service_downloader_uses_service_base_path(self):
        t = _transport(_make_handler([_json_response(200, [])]))
        try:
            service = MetadataService(t, base_path="/custom")
            assert service.downloader.base_path == "/custom"
        finally:
            t.close()

    def test_caller_supplied_downloader_used(self):
        t = _transport(_make_handler([_json_response(200, [])]))
        try:
            custom = MetadataDownloader(t, base_path="/custom-downloader")
            service = MetadataService(t, downloader=custom)
            assert service.downloader is custom
        finally:
            t.close()

    def test_service_download_through_downloader(self):
        # End-to-end: MetadataService -> MetadataDownloader ->
        # transport -> mock response.
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = str(request.url.path)
            return _json_response(200, {"ok": True})

        t = _transport(handler)
        try:
            service = MetadataService(t)
            resp = service.downloader.download("R02")
            assert resp.status_code == 200
            assert captured["path"] == "/files/v1/app/reference/Reporters.json"
        finally:
            t.close()


# ---------------------------------------------------------------------------
# No live API calls
# ---------------------------------------------------------------------------


class TestNoLiveCalls:
    def test_download_does_not_call_outside_mock(self):
        # The downloader goes through the injected transport. With
        # httpx.MockTransport, no real network is hit. We assert
        # this by counting handler invocations across multiple
        # downloads; with no handler the test would fail at the
        # first call.
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return _json_response(200, {})

        t = _transport(handler)
        try:
            dl = MetadataDownloader(t)
            for rid in ("R01", "R02", "R03", "R04", "R09"):
                dl.download(rid)
            assert calls["n"] == 5
        finally:
            t.close()

    def test_construction_does_not_issue_requests(self):
        # Building the downloader must not touch the transport.
        # No call should reach the handler.
        called = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            called["n"] += 1
            return _json_response(200, {})

        t = _transport(handler)
        try:
            MetadataDownloader(t)
            assert called["n"] == 0
        finally:
            t.close()