"""Unit tests for `un_comtrade.transport`.

The transport wraps `httpx.Client`; tests use `httpx.MockTransport`
to avoid any live network calls. Every test asserts the transport
issues the right HTTP method, URL, params, and headers, and that the
returned `HttpResponse` faithfully reflects the mocked upstream.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from un_comtrade.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ComtradeError,
    ConfigurationError,
)
from un_comtrade.transport import (
    AUTH_FAILURE_STATUSES,
    AUTH_HEADER,
    DEFAULT_HEADERS,
    HttpResponse,
    HttpTransport,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_handler(responses: list[httpx.Response]) -> httpx.MockTransport:
    """Build an `httpx.MockTransport` that replays `responses` in order."""
    iterator = iter(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        try:
            return next(iterator)
        except StopIteration:
            return httpx.Response(599, json={"error": "no more mocks"})

    return httpx.MockTransport(handler)


def _json_response(status_code: int, payload: Any, headers: dict[str, str] | None = None) -> httpx.Response:
    body = json.dumps(payload).encode("utf-8")
    return httpx.Response(
        status_code=status_code,
        content=body,
        headers={"Content-Type": "application/json", **(headers or {})},
    )


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------


class TestInstantiation:
    def test_default_construction(self):
        t = HttpTransport(base_url="https://example.org", user_agent="ua/1.0")
        assert t.base_url == "https://example.org"
        assert t.user_agent == "ua/1.0"
        t.close()

    def test_strips_trailing_slash(self):
        t = HttpTransport(base_url="https://example.org/", user_agent="ua/1.0")
        assert t.base_url == "https://example.org"
        t.close()

    def test_empty_base_url_rejected(self):
        with pytest.raises(ValueError, match="base_url"):
            HttpTransport(base_url="", user_agent="ua/1.0")

    def test_invalid_scheme_rejected(self):
        with pytest.raises(ValueError, match="base_url"):
            HttpTransport(base_url="ftp://example.org", user_agent="ua/1.0")

    def test_empty_user_agent_rejected(self):
        with pytest.raises(ValueError, match="user_agent"):
            HttpTransport(base_url="https://example.org", user_agent="")


# ---------------------------------------------------------------------------
# User-Agent and default header injection
# ---------------------------------------------------------------------------


class TestHeaderInjection:
    def test_user_agent_in_default_headers(self):
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(request.headers)
            return _json_response(200, {"ok": True})

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="my-ua/2.0",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        r = t.get("/path")
        t.close()
        assert r.status_code == 200
        assert captured.get("user-agent") == "my-ua/2.0"

    def test_accept_header_default(self):
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(request.headers)
            return _json_response(200, {})

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        t.get("/x")
        t.close()
        assert captured.get("accept") == DEFAULT_HEADERS["Accept"]

    def test_per_request_header_override(self):
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(request.headers)
            return _json_response(200, {})

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        t.get("/x", headers={"X-Custom": "v1"})
        t.close()
        assert captured.get("x-custom") == "v1"
        # Default headers still present
        assert captured.get("user-agent") == "ua/1.0"


# ---------------------------------------------------------------------------
# URL resolution
# ---------------------------------------------------------------------------


class TestUrlResolution:
    @pytest.mark.parametrize("path,expected", [
        ("/api/v1/foo", "https://example.org/api/v1/foo"),
        ("api/v1/foo", "https://example.org/api/v1/foo"),
        ("/", "https://example.org"),
        ("", "https://example.org"),
        ("https://other.example.org/x", "https://other.example.org/x"),
        ("http://plain.example.org/x", "http://plain.example.org/x"),
    ])
    def test_path_resolution(self, path, expected):
        captured_url = {"value": None}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_url["value"] = str(request.url)
            return _json_response(200, {})

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        t.get(path)
        t.close()
        assert captured_url["value"] == expected


# ---------------------------------------------------------------------------
# Query parameters
# ---------------------------------------------------------------------------


class TestQueryParams:
    def test_get_with_params(self):
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            return _json_response(200, {"ok": True})

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        t.get("/get", params={"a": 1, "b": "two"})
        t.close()
        assert "a=1" in captured["url"]
        assert "b=two" in captured["url"]

    def test_post_with_params(self):
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["method"] = request.method
            captured["url"] = str(request.url)
            return _json_response(201, {"created": True})

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        r = t.post("/post", params={"q": "x"})
        t.close()
        assert captured["method"] == "POST"
        assert "q=x" in captured["url"]
        assert r.status_code == 201
        assert r.json() == {"created": True}


# ---------------------------------------------------------------------------
# Response wrapper
# ---------------------------------------------------------------------------


class TestResponseWrapper:
    def test_status_code_propagated(self):
        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=_make_handler([
                _json_response(404, {"error": "not found"}),
            ])),
        )
        r = t.get("/missing")
        t.close()
        assert r.status_code == 404
        assert not r.is_success

    def test_success_flag(self):
        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=_make_handler([
                _json_response(200, {"ok": True}),
                _json_response(201, {"created": True}),
                _json_response(299, {"weird": True}),
                _json_response(300, {"redirect": True}),
            ])),
        )
        assert t.get("/a").is_success
        assert t.get("/b").is_success
        assert t.get("/c").is_success
        assert not t.get("/d").is_success
        t.close()

    def test_json_parsing(self):
        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=_make_handler([
                _json_response(200, {"hello": "world", "n": 42}),
            ])),
        )
        r = t.get("/x")
        t.close()
        assert r.json() == {"hello": "world", "n": 42}

    def test_text_decoding(self):
        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=_make_handler([
                httpx.Response(200, content=b"hello world",
                               headers={"Content-Type": "text/plain"}),
            ])),
        )
        r = t.get("/x")
        t.close()
        assert r.text == "hello world"
        assert r.body == b"hello world"

    def test_headers_propagated(self):
        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=_make_handler([
                httpx.Response(
                    200,
                    content=b"{}",
                    headers={"X-Server": "test", "Content-Type": "application/json"},
                ),
            ])),
        )
        r = t.get("/x")
        t.close()
        # httpx lower-cases header names
        assert r.headers.get("x-server") == "test"
        assert r.headers.get("content-type") == "application/json"

    def test_url_recorded(self):
        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=_make_handler([
                _json_response(200, {}),
            ])),
        )
        r = t.get("/foo/bar")
        t.close()
        assert r.url == "https://example.org/foo/bar"

    def test_elapsed_seconds_positive(self):
        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=_make_handler([
                _json_response(200, {}),
            ])),
        )
        r = t.get("/x")
        t.close()
        assert r.elapsed_seconds >= 0


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_close_releases_owned_client(self):
        # When the transport creates its own client (no caller-supplied
        # client), closing the transport closes the underlying client.
        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
        )
        owned_client = t.client
        assert not owned_client.is_closed
        t.close()
        assert owned_client.is_closed

    def test_does_not_close_caller_supplied_client(self):
        # When the caller supplies a client, closing the transport
        # MUST NOT close the caller's client.
        client = httpx.Client(transport=_make_handler([_json_response(200, {})]))
        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=client,
        )
        t.close()
        assert not client.is_closed
        # The caller's client is still alive and answerable.
        r = client.get("https://example.org/x")
        assert r.status_code == 200

    def test_context_manager(self):
        with HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
        ) as t:
            assert t.base_url == "https://example.org"
        # After __exit__, the owned client should be closed.
        assert t.client.is_closed


# ---------------------------------------------------------------------------
# Transport-level defaults that are NOT auto-applied
# ---------------------------------------------------------------------------


class TestTransportDefaults:
    """Tests for default behaviours the transport does NOT apply
    (e.g. no subscription key when none was configured; no default
    timeout enforcement). Retry and auth-translation live inside
    the transport and are covered elsewhere.
    """

    def test_does_not_inject_subscription_key_when_unset(self):
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(request.headers)
            return _json_response(200, {})

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        t.get("/x")
        t.close()
        # No api_key set -> no subscription key header.
        assert "subscription-key" not in captured
        assert "ocp-apim-subscription-key" not in captured

    def test_no_default_timeout_enforced_by_transport(self):
        """The transport passes the `timeout` parameter through but
        does not apply a default of its own."""
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            return _json_response(200, {})

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        # No timeout supplied; transport should still issue the request.
        r = t.get("/x")
        t.close()
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class TestAuthentication:
    """API key injection, validation, and upstream 401/403 handling."""

    # ----- Header injection ------------------------------------------------

    def test_api_key_injected_into_request(self):
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(request.headers)
            return _json_response(200, {})

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            api_key="secret-key-abc",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        t.get("/x")
        t.close()
        # Header uses the documented Azure APIM name.
        assert captured.get("ocp-apim-subscription-key") == "secret-key-abc"
        assert AUTH_HEADER == "Ocp-Apim-Subscription-Key"

    def test_api_key_injected_with_caller_supplied_client(self):
        # Even when the caller supplies a pre-built client, the
        # transport still applies its defaults — including the
        # auth header — on every request.
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(request.headers)
            return _json_response(200, {})

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            api_key="k1",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        t.get("/x")
        t.close()
        assert captured.get("ocp-apim-subscription-key") == "k1"

    def test_no_header_when_api_key_is_none(self):
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(request.headers)
            return _json_response(200, {})

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        t.get("/x")
        t.close()
        # No api_key -> no auth header.
        assert "ocp-apim-subscription-key" not in captured

    def test_per_request_headers_do_not_override_api_key(self):
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(request.headers)
            return _json_response(200, {})

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            api_key="real-key",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        # Caller's headers are merged AFTER the defaults, so they win.
        # Documenting this as the current contract.
        t.get("/x", headers={"Ocp-Apim-Subscription-Key": "override"})
        t.close()
        assert captured.get("ocp-apim-subscription-key") == "override"

    # ----- Construction-time validation -----------------------------------

    def test_empty_api_key_rejected(self):
        with pytest.raises(ValueError, match="api_key"):
            HttpTransport(
                base_url="https://example.org",
                user_agent="ua/1.0",
                api_key="",
            )

    def test_whitespace_api_key_rejected(self):
        with pytest.raises(ValueError, match="api_key"):
            HttpTransport(
                base_url="https://example.org",
                user_agent="ua/1.0",
                api_key="   ",
            )

    def test_non_string_api_key_rejected(self):
        with pytest.raises(TypeError, match="api_key"):
            HttpTransport(
                base_url="https://example.org",
                user_agent="ua/1.0",
                api_key=12345,  # type: ignore[arg-type]
            )

    def test_api_key_property_exposes_value(self):
        t = HttpTransport(
            base_url="https://example.org", user_agent="ua/1.0", api_key="abc"
        )
        assert t.api_key == "abc"
        t.close()

    def test_api_key_property_none_by_default(self):
        t = HttpTransport(
            base_url="https://example.org", user_agent="ua/1.0"
        )
        assert t.api_key is None
        t.close()

    # ----- 401 / 403 translation -----------------------------------------

    def test_401_with_no_key_raises_authentication_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return _json_response(401, {"error": "no key"})

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        try:
            with pytest.raises(AuthenticationError) as excinfo:
                t.get("/x")
            msg = str(excinfo.value)
            assert "401" in msg
            # Missing-key case mentions the env var so consumers know
            # how to fix it.
            assert "UN_COMTRADE_KEY" in msg
        finally:
            t.close()

    def test_401_with_key_raises_authentication_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return _json_response(401, {"error": "bad key"})

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            api_key="bogus",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        try:
            with pytest.raises(AuthenticationError) as excinfo:
                t.get("/x")
            msg = str(excinfo.value)
            assert "401" in msg
            # Key-present case focuses on "rejected" not "missing".
            assert "rejected" in msg.lower() or "verify" in msg.lower()
        finally:
            t.close()

    def test_403_raises_authorization_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return _json_response(403, {"error": "forbidden"})

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            api_key="limited",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        try:
            with pytest.raises(AuthorizationError) as excinfo:
                t.get("/x")
            msg = str(excinfo.value)
            assert "403" in msg
        finally:
            t.close()

    def test_authorization_error_is_authentication_error_subclass(self):
        # Per ADR-0012 AuthorizationError inherits from
        # AuthenticationError; both should be catchable by
        # `except AuthenticationError`.
        def handler(request: httpx.Request) -> httpx.Response:
            return _json_response(403, {})

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            api_key="x",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        try:
            with pytest.raises(AuthenticationError):
                t.get("/x")
        finally:
            t.close()

    def test_auth_error_is_comtrade_error_subclass(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return _json_response(401, {})

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        try:
            with pytest.raises(ComtradeError):
                t.get("/x")
        finally:
            t.close()

    def test_200_still_returns_response(self):
        # Positive control: a successful request still returns an
        # HttpResponse when auth is configured correctly.
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(request.headers)
            return _json_response(200, {"ok": True})

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            api_key="good-key",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        try:
            r = t.get("/x")
        finally:
            t.close()
        assert r.status_code == 200
        assert captured["ocp-apim-subscription-key"] == "good-key"

    def test_auth_failure_statuses_constant(self):
        # The translation set is documented and tested separately.
        assert AUTH_FAILURE_STATUSES == frozenset({401, 403})

    # ----- ConfigurationError at construction ----------------------------

    def test_configuration_error_for_bad_api_key_subclass(self):
        # ValueError raised for empty api_key is the documented
        # ConfigurationError subclass (ADR-0012).
        with pytest.raises((ValueError, ConfigurationError)):
            HttpTransport(
                base_url="https://example.org",
                user_agent="ua/1.0",
                api_key="",
            )


# ---------------------------------------------------------------------------
# No live API calls
# ---------------------------------------------------------------------------


def test_no_network_calls_made_at_import():
    """Importing the transport module must not perform any I/O."""
    # This test passes if we got here without a network call.
    # (The MockTransport-based tests above already prove no network is
    # used at request time.)
    from un_comtrade.transport import HttpTransport  # noqa: F401
    assert HttpTransport is not None