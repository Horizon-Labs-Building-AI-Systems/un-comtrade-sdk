"""Unit tests for the transport's timeout middleware.

The timeout logic lives inside `un_comtrade.transport.HttpTransport`
per ADR-0023 (30 s default, 15 s metadata, 300 s large_download).
These tests exercise the timeout behaviour end-to-end through the
public `HttpTransport.request()` / `.get()` / `.post()` surface,
plus the `TimeoutConfig` dataclass and per-request `kind` kwarg.

All tests use `httpx.MockTransport` so the suite is fully
deterministic and never hits the network.
"""

from __future__ import annotations

from typing import Callable

import httpx
import pytest

from un_comtrade.exceptions import (
    AuthenticationError,
    NetworkError,
    RetryError,
)
from un_comtrade.transport import (
    HttpResponse,
    HttpTransport,
    RetryPolicy,
    TIMEOUT_CATEGORIES,
    TimeoutConfig,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _json_response(
    status_code: int,
    body: object,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Build an `httpx.Response` for `httpx.MockTransport` handlers."""
    import json as _json

    return httpx.Response(
        status_code=status_code,
        content=_json.dumps(body).encode("utf-8"),
        headers=headers or {},
        request=httpx.Request("GET", "https://example.org/x"),
    )


def _make_handler(
    responses: list[httpx.Response | Exception | type[Exception]],
) -> Callable[[httpx.Request], httpx.Response]:
    """Build a MockTransport handler that drains a pre-built queue."""
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        if not queue:
            raise AssertionError("MockTransport queue exhausted")
        item = queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        if isinstance(item, type) and issubclass(item, BaseException):
            raise item()
        item.request = request
        return item

    return handler


def _transport(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    timeout: TimeoutConfig | None = None,
    retry: RetryPolicy | None = None,
) -> HttpTransport:
    """Build an HttpTransport wired to a MockTransport handler."""
    kwargs: dict[str, object] = dict(
        base_url="https://example.org",
        user_agent="ua/1.0",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    if timeout is not None:
        kwargs["timeout"] = timeout
    if retry is not None:
        kwargs["retry"] = retry
    return HttpTransport(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TimeoutConfig
# ---------------------------------------------------------------------------


class TestTimeoutConfigDefaults:
    def test_defaults_match_adr0023(self):
        c = TimeoutConfig()
        assert c.default == 30.0
        assert c.metadata == 15.0
        assert c.large_download == 300.0

    def test_for_category(self):
        c = TimeoutConfig()
        assert c.for_category("default") == 30.0
        assert c.for_category("metadata") == 15.0
        assert c.for_category("large_download") == 300.0

    def test_categories_constant(self):
        assert TIMEOUT_CATEGORIES == frozenset(
            {"default", "metadata", "large_download"}
        )

    def test_for_category_unknown_raises(self):
        c = TimeoutConfig()
        with pytest.raises(ValueError, match="Unknown"):
            c.for_category("garbage")


class TestTimeoutConfigValidation:
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"default": 0},
            {"default": -1},
            {"metadata": 0},
            {"metadata": -5},
            {"large_download": 0},
        ],
    )
    def test_rejects_non_positive_values(self, kwargs):
        with pytest.raises(ValueError):
            TimeoutConfig(**kwargs)

    def test_frozen_immutable(self):
        c = TimeoutConfig()
        with pytest.raises((AttributeError, Exception)):
            c.default = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Default timeout applied
# ---------------------------------------------------------------------------


class TestDefaultTimeout:
    def test_default_timeout_applied_when_kind_is_default(self):
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["timeout"] = request.extensions.get("timeout")
            return _json_response(200, {})

        rt = _transport(
            handler, timeout=TimeoutConfig(default=12.5)
        )
        try:
            rt.get("/x")
        finally:
            rt.close()
        timeout_obj = captured["timeout"]
        assert timeout_obj is not None
        # httpx stores a single-value timeout across connect/read/write/pool.
        assert float(timeout_obj["connect"]) == pytest.approx(12.5)

    def test_adr0023_default_is_30s(self):
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["timeout"] = request.extensions.get("timeout")
            return _json_response(200, {})

        rt = _transport(handler)  # default config
        try:
            rt.get("/x")
        finally:
            rt.close()
        assert float(captured["timeout"]["connect"]) == pytest.approx(30.0)

    def test_explicit_timeout_overrides_config(self):
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["timeout"] = request.extensions.get("timeout")
            return _json_response(200, {})

        rt = _transport(handler)
        try:
            rt.get("/x", timeout=7.0)
        finally:
            rt.close()
        assert float(captured["timeout"]["connect"]) == pytest.approx(7.0)

    def test_explicit_timeout_overrides_kind(self):
        # Even with kind="metadata", an explicit timeout wins.
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["timeout"] = request.extensions.get("timeout")
            return _json_response(200, {})

        rt = _transport(handler)
        try:
            rt.get("/x", kind="metadata", timeout=2.5)
        finally:
            rt.close()
        assert float(captured["timeout"]["connect"]) == pytest.approx(2.5)


# ---------------------------------------------------------------------------
# Metadata timeout (ADR-0023: 15 s)
# ---------------------------------------------------------------------------


class TestMetadataTimeout:
    def test_metadata_timeout_applied_via_kind(self):
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["timeout"] = request.extensions.get("timeout")
            return _json_response(200, {})

        rt = _transport(handler)
        try:
            rt.get("/x", kind="metadata")
        finally:
            rt.close()
        # ADR-0023 metadata = 15 s
        assert float(captured["timeout"]["connect"]) == pytest.approx(15.0)

    def test_metadata_timeout_explicit_value(self):
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["timeout"] = request.extensions.get("timeout")
            return _json_response(200, {})

        rt = _transport(handler)
        try:
            rt.get("/x", timeout=8.0)  # kind="default" by default
        finally:
            rt.close()
        assert float(captured["timeout"]["connect"]) == pytest.approx(8.0)

    def test_custom_metadata_via_config(self):
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["timeout"] = request.extensions.get("timeout")
            return _json_response(200, {})

        cfg = TimeoutConfig(default=30.0, metadata=10.0, large_download=300.0)
        rt = _transport(handler, timeout=cfg)
        try:
            rt.get("/x", kind="metadata")
        finally:
            rt.close()
        assert float(captured["timeout"]["connect"]) == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# Download / large_download timeout (ADR-0023: 300 s)
# ---------------------------------------------------------------------------


class TestDownloadTimeout:
    def test_large_download_timeout_applied_via_kind(self):
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["timeout"] = request.extensions.get("timeout")
            return _json_response(200, {})

        rt = _transport(handler)
        try:
            rt.get("/x", kind="large_download")
        finally:
            rt.close()
        # ADR-0023 large_download = 300 s
        assert float(captured["timeout"]["connect"]) == pytest.approx(300.0)

    def test_custom_large_download_via_config(self):
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["timeout"] = request.extensions.get("timeout")
            return _json_response(200, {})

        cfg = TimeoutConfig(large_download=900.0)
        rt = _transport(handler, timeout=cfg)
        try:
            rt.get("/x", kind="large_download")
        finally:
            rt.close()
        assert float(captured["timeout"]["connect"]) == pytest.approx(900.0)


# ---------------------------------------------------------------------------
# Timeout exception translation
# ---------------------------------------------------------------------------


class TestTimeoutExceptionTranslation:
    def test_httpx_read_timeout_translates_to_sdk_timeout_error(self):
        # With retries disabled, the translated exception surfaces
        # directly to the caller.
        handler = _make_handler([httpx.ReadTimeout("too slow")])
        rt = _transport(handler, retry=RetryPolicy(attempts=1))
        try:
            with pytest.raises(Exception) as excinfo:
                rt.get("/x")
            # Verify the SDK TimeoutError and that __cause__
            # is the original httpx.TimeoutException.
            from un_comtrade.exceptions import TimeoutError as SdkTimeoutError
            assert isinstance(excinfo.value, SdkTimeoutError)
            assert isinstance(excinfo.value.__cause__, httpx.ReadTimeout)
        finally:
            rt.close()

    def test_httpx_connect_timeout_translates_to_sdk_timeout_error(self):
        handler = _make_handler([httpx.ConnectTimeout("dns slow")])
        rt = _transport(handler, retry=RetryPolicy(attempts=1))
        try:
            from un_comtrade.exceptions import TimeoutError as SdkTimeoutError
            with pytest.raises(SdkTimeoutError) as excinfo:
                rt.get("/x")
            assert isinstance(excinfo.value.__cause__, httpx.ConnectTimeout)
        finally:
            rt.close()

    def test_sdk_timeout_error_is_network_error_subclass(self):
        # ADR-0012: TimeoutError is a NetworkError.
        from un_comtrade.exceptions import TimeoutError as SdkTimeoutError
        assert issubclass(SdkTimeoutError, NetworkError)

    def test_timeout_message_contains_effective_timeout(self):
        handler = _make_handler([httpx.ReadTimeout("too slow")])
        rt = _transport(
            handler,
            timeout=TimeoutConfig(default=12.5),
            retry=RetryPolicy(attempts=1),
        )
        try:
            from un_comtrade.exceptions import TimeoutError as SdkTimeoutError
            with pytest.raises(SdkTimeoutError) as excinfo:
                rt.get("/x")
            assert "12.5" in str(excinfo.value)
        finally:
            rt.close()

    def test_timeout_message_contains_path(self):
        handler = _make_handler([httpx.ReadTimeout("too slow")])
        rt = _transport(handler, retry=RetryPolicy(attempts=1))
        try:
            from un_comtrade.exceptions import TimeoutError as SdkTimeoutError
            with pytest.raises(SdkTimeoutError) as excinfo:
                rt.get("/some/path")
            assert "/some/path" in str(excinfo.value)
        finally:
            rt.close()

    def test_non_timeout_exception_passes_through(self):
        handler = _make_handler([ValueError("nope")])
        rt = _transport(handler)
        try:
            with pytest.raises(ValueError, match="nope"):
                rt.get("/x")
        finally:
            rt.close()


# ---------------------------------------------------------------------------
# Timeout + retry interaction
# ---------------------------------------------------------------------------


class TestTimeoutRetryInteraction:
    def test_translated_timeout_is_retried(self):
        # The transport translates httpx.TimeoutException ->
        # SdkTimeoutError. The retry policy treats SdkTimeoutError
        # as retryable (DEFAULT_RETRYABLE_EXCEPTIONS includes it).
        # So the second attempt succeeds.
        handler = _make_handler(
            [httpx.ReadTimeout("first"), _json_response(200, {"ok": True})]
        )
        rt = _transport(handler)
        try:
            r = rt.get("/x")
        finally:
            rt.close()
        assert r.status_code == 200

    def test_repeated_timeouts_exhaust_with_retry_error(self):
        # Three timeouts -> SDK TimeoutError each time -> retry sees
        # SdkTimeoutError (retryable) -> retries -> budget exhausted
        # -> RetryError chained to the last SdkTimeoutError.
        handler = _make_handler(
            [
                httpx.ReadTimeout("first"),
                httpx.ReadTimeout("second"),
                httpx.ReadTimeout("third"),
            ]
        )
        rt = _transport(handler)
        try:
            from un_comtrade.exceptions import TimeoutError as SdkTimeoutError
            with pytest.raises(RetryError) as excinfo:
                rt.get("/x")
            # The RetryError's __cause__ is the last SDK TimeoutError.
            assert isinstance(excinfo.value.__cause__, SdkTimeoutError)
            # And THAT cause's __cause__ is the original httpx exception.
            assert isinstance(
                excinfo.value.__cause__.__cause__, httpx.ReadTimeout
            )
        finally:
            rt.close()

    def test_auth_exception_not_retried_even_after_timeout(self):
        # 401 raises AuthenticationError immediately; the retry
        # loop must not consume the budget on a non-retryable
        # exception, even if it is wrapped by a timeout in a
        # prior attempt. (Sanity check.)
        handler = _make_handler(
            [httpx.ReadTimeout("first"), _json_response(401, {"err": 1})]
        )
        rt = _transport(handler)
        try:
            with pytest.raises(AuthenticationError):
                rt.get("/x")
        finally:
            rt.close()


# ---------------------------------------------------------------------------
# Surface tests
# ---------------------------------------------------------------------------


class TestTimeoutTransportSurface:
    def test_timeout_config_property_exposes_config(self):
        rt = _transport(
            _make_handler([_json_response(200, {})]),
            timeout=TimeoutConfig(default=99.0),
        )
        try:
            assert rt.timeout_config.default == 99.0
        finally:
            rt.close()

    def test_default_timeout_config_is_adr0023(self):
        rt = _transport(_make_handler([_json_response(200, {})]))
        try:
            assert rt.timeout_config.default == 30.0
            assert rt.timeout_config.metadata == 15.0
            assert rt.timeout_config.large_download == 300.0
        finally:
            rt.close()

    def test_get_and_post_share_request(self):
        handler = _make_handler(
            [
                _json_response(200, {"a": 1}),
                _json_response(200, {"b": 2}),
            ]
        )
        rt = _transport(handler)
        try:
            r1 = rt.get("/a")
            r2 = rt.post("/b")
        finally:
            rt.close()
        assert r1.status_code == 200
        assert r2.status_code == 200

    def test_unknown_kind_rejected(self):
        handler = _make_handler([_json_response(200, {})])
        rt = _transport(handler)
        try:
            with pytest.raises(ValueError, match="Unknown"):
                rt.get("/x", kind="garbage")
        finally:
            rt.close()

    def test_positive_response_unaffected_by_timeout_config(self):
        # Positive control: a successful request still returns an
        # HttpResponse regardless of the timeout configuration.
        rt = _transport(
            _make_handler([_json_response(200, {"ok": True})]),
            timeout=TimeoutConfig(default=5.0),
        )
        try:
            r = rt.get("/x")
        finally:
            rt.close()
        assert r.status_code == 200
        assert r.json() == {"ok": True}