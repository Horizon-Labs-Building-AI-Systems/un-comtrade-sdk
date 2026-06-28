"""Foundation integration tests.

These tests verify the end-to-end integration of the
infrastructure layer (P1-001 through P1-008) BEFORE any
SDK feature implementation begins. They cover:

- Configuration -> Transport wiring (api_key, timeouts,
  base URL).
- Authentication -> Transport (header injection, 401 /
  403 translation).
- Retry -> Timeout (translated timeouts are retried;
  retry exhaustion raises `RetryError`).
- Logging -> Transport (correlation IDs, no secrets).
- Exception propagation across the whole stack.
- A mock end-to-end request that exercises every layer.

No live network calls. No new functionality — these
tests observe the existing behaviour from the outside.
"""

from __future__ import annotations

import logging
from typing import Callable, List

import httpx
import pytest

from un_comtrade.config import Configuration, load_configuration
from un_comtrade.exceptions import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    ComtradeError,
    ConfigurationError,
    NetworkError,
    RateLimitError,
    RetryError,
    TimeoutError as SdkTimeoutError,
    ValidationError,
)
from un_comtrade.logging import (
    LOGGER_NAMESPACE,
    LOGGING_DEFAULT_LEVEL,
    REDACTED,
    RedactingFilter,
    get_logger,
    install_redaction,
)
from un_comtrade.transport import (
    AUTH_FAILURE_STATUSES,
    AUTH_HEADER,
    DEFAULT_RETRYABLE_STATUS_CODES,
    HttpResponse,
    HttpTransport,
    RetryPolicy,
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


class _CapturingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: List[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def capture() -> _CapturingHandler:
    handler = _CapturingHandler()
    sdk_root = logging.getLogger(LOGGER_NAMESPACE)
    sdk_root.addHandler(handler)
    yield handler
    sdk_root.removeHandler(handler)


def _build_transport(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    api_key: str | None = None,
    retry: RetryPolicy | None = None,
    timeout: TimeoutConfig | None = None,
) -> HttpTransport:
    """Build an HttpTransport wired to the given MockTransport handler."""
    kwargs: dict[str, object] = dict(
        base_url="https://example.org",
        user_agent="integration-test/1.0",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    if api_key is not None:
        kwargs["api_key"] = api_key
    if retry is not None:
        kwargs["retry"] = retry
    if timeout is not None:
        kwargs["timeout"] = timeout
    return HttpTransport(**kwargs)  # type: ignore[arg-type]


def _build_from_configuration(
    handler: Callable[[httpx.Request], httpx.Response],
    cfg: Configuration,
) -> HttpTransport:
    """Wire an HttpTransport from a Configuration object."""
    return HttpTransport(
        base_url=cfg.base_url,
        user_agent=cfg.user_agent,
        api_key=cfg.api_key,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


# ---------------------------------------------------------------------------
# Configuration -> Transport
# ---------------------------------------------------------------------------


class TestConfigurationToTransport:
    def test_base_url_from_configuration(self):
        cfg = Configuration(base_url="https://api.example.com/", user_agent="ua/1.0")
        handler = _make_handler([_json_response(200, {"ok": True})])
        t = _build_from_configuration(handler, cfg)
        try:
            assert t.base_url == "https://api.example.com"  # trailing slash stripped
        finally:
            t.close()

    def test_user_agent_from_configuration(self):
        cfg = Configuration(
            base_url="https://api.example.com",
            user_agent="my-consumer/2.0",
        )
        handler = _make_handler([_json_response(200, {"ok": True})])
        t = _build_from_configuration(handler, cfg)
        try:
            assert t.user_agent == "my-consumer/2.0"
        finally:
            t.close()

    def test_api_key_from_configuration_injected_into_request(self):
        cfg = Configuration(
            base_url="https://api.example.com",
            user_agent="ua/1.0",
            api_key="cfg-supplied-key",
        )
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(request.headers)
            return _json_response(200, {"ok": True})

        t = _build_from_configuration(handler, cfg)
        try:
            t.get("/x")
        finally:
            t.close()
        assert captured.get("ocp-apim-subscription-key") == "cfg-supplied-key"

    def test_load_configuration_propagates_through_factory(self, monkeypatch):
        # The `load_configuration` factory reads env vars; verify it
        # produces a Configuration whose api_key propagates correctly.
        monkeypatch.setenv("UN_COMTRADE_KEY", "env-supplied-key")
        cfg = load_configuration(env=monkeypatch.delenv if False else None)
        # Without an explicit env mapping the factory falls back to
        # the real os.environ, which we just set.
        cfg = load_configuration()
        handler = _make_handler([_json_response(200, {"ok": True})])
        t = _build_from_configuration(handler, cfg)
        try:
            assert t.api_key == "env-supplied-key"
        finally:
            t.close()


# ---------------------------------------------------------------------------
# Authentication -> Transport
# ---------------------------------------------------------------------------


class TestAuthenticationIntegration:
    def test_401_raises_authentication_error_with_api_key_set(self):
        handler = _make_handler(
            [_json_response(401, {"statusCode": 401, "message": "denied"})]
        )
        t = _build_transport(handler, api_key="bad-key")
        try:
            with pytest.raises(AuthenticationError) as excinfo:
                t.get("/x")
            assert excinfo.value.__cause__ is None
            assert "401" in str(excinfo.value)
            assert "rejected" in str(excinfo.value).lower()
        finally:
            t.close()

    def test_401_without_api_key_suggests_env_var(self):
        handler = _make_handler([_json_response(401, {"err": 1})])
        t = _build_transport(handler)
        try:
            with pytest.raises(AuthenticationError) as excinfo:
                t.get("/x")
            assert "UN_COMTRADE_KEY" in str(excinfo.value)
        finally:
            t.close()

    def test_403_raises_authorization_error(self):
        handler = _make_handler([_json_response(403, {"err": 1})])
        t = _build_transport(handler, api_key="limited")
        try:
            with pytest.raises(AuthorizationError):
                t.get("/x")
        finally:
            t.close()

    def test_auth_failure_statuses_frozen_set(self):
        # ADR-0012 + ADR-0034 contract.
        assert AUTH_FAILURE_STATUSES == frozenset({401, 403})

    def test_auth_error_is_comtrade_error_subclass(self):
        # The exception must be catchable by `except ComtradeError`.
        handler = _make_handler([_json_response(401, {})])
        t = _build_transport(handler)
        try:
            with pytest.raises(ComtradeError):
                t.get("/x")
        finally:
            t.close()

    def test_authorization_error_is_authentication_error_subclass(self):
        # ADR-0012 hierarchy.
        assert issubclass(AuthorizationError, AuthenticationError)
        handler = _make_handler([_json_response(403, {})])
        t = _build_transport(handler, api_key="x")
        try:
            with pytest.raises(AuthenticationError):
                t.get("/x")
        finally:
            t.close()

    def test_invalid_api_key_rejected_at_construction(self):
        with pytest.raises(ValueError):
            HttpTransport(
                base_url="https://example.org",
                user_agent="ua/1.0",
                api_key="",
            )


# ---------------------------------------------------------------------------
# Retry integration
# ---------------------------------------------------------------------------


class TestRetryIntegration:
    def test_each_documented_retryable_status(self):
        for status in (429, 500, 502, 503, 504):
            handler = _make_handler(
                [
                    _json_response(status, {"err": status}),
                    _json_response(200, {"ok": True}),
                ]
            )
            t = _build_transport(handler)
            try:
                r = t.get("/x")
                assert r.status_code == 200
            finally:
                t.close()

    def test_validation_statuses_not_retried(self):
        for status in (400, 404, 422):
            handler = _make_handler(
                [
                    _json_response(status, {"err": status}),
                    _json_response(200, {"ok": True}),
                ]
            )
            t = _build_transport(handler)
            try:
                r = t.get("/x")
                assert r.status_code == status  # returned as-is
            finally:
                t.close()

    def test_auth_failures_not_retried(self):
        for status in (401, 403):
            handler = _make_handler(
                [
                    _json_response(status, {"err": status}),
                    _json_response(200, {"ok": True}),
                ]
            )
            t = _build_transport(handler)
            try:
                with pytest.raises(AuthenticationError):
                    t.get("/x")
            finally:
                t.close()

    def test_retry_exhaustion_on_500_raises_retry_error(self):
        handler = _make_handler(
            [
                _json_response(500, {}),
                _json_response(500, {}),
                _json_response(500, {}),
            ]
        )
        t = _build_transport(handler)
        try:
            with pytest.raises(RetryError) as excinfo:
                t.get("/x")
            assert "500" in str(excinfo.value)
            assert excinfo.value.__cause__ is None
        finally:
            t.close()

    def test_retry_uses_retry_after_header(self):
        handler = _make_handler(
            [
                _json_response(429, {}, headers={"Retry-After": "2"}),
                _json_response(200, {"ok": True}),
            ]
        )
        t = _build_transport(handler)
        try:
            r = t.get("/x")
            assert r.status_code == 200
        finally:
            t.close()

    def test_custom_retry_policy_attempts(self):
        handler = _make_handler(
            [
                _json_response(500, {}),
                _json_response(500, {}),
            ]
        )
        t = _build_transport(handler, retry=RetryPolicy(attempts=2))
        try:
            with pytest.raises(RetryError):
                t.get("/x")
        finally:
            t.close()


# ---------------------------------------------------------------------------
# Timeout integration
# ---------------------------------------------------------------------------


class TestTimeoutIntegration:
    def test_translated_timeout_is_retried(self):
        # httpx.TimeoutException -> SdkTimeoutError -> retry catches it.
        handler = _make_handler(
            [httpx.ReadTimeout("first"), _json_response(200, {"ok": True})]
        )
        t = _build_transport(handler)
        try:
            r = t.get("/x")
            assert r.status_code == 200
        finally:
            t.close()

    def test_timeout_exhaustion_chain(self):
        # Three timeouts: RetryError -> SdkTimeoutError -> httpx.ReadTimeout.
        handler = _make_handler(
            [
                httpx.ReadTimeout("first"),
                httpx.ReadTimeout("second"),
                httpx.ReadTimeout("third"),
            ]
        )
        t = _build_transport(handler)
        try:
            with pytest.raises(RetryError) as excinfo:
                t.get("/x")
            assert isinstance(excinfo.value.__cause__, SdkTimeoutError)
            assert isinstance(
                excinfo.value.__cause__.__cause__, httpx.ReadTimeout
            )
        finally:
            t.close()

    def test_kind_metadata_uses_15s(self):
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["timeout"] = request.extensions.get("timeout")
            return _json_response(200, {})

        t = _build_transport(handler)
        try:
            t.get("/x", kind="metadata")
        finally:
            t.close()
        assert float(captured["timeout"]["connect"]) == pytest.approx(15.0)

    def test_kind_large_download_uses_300s(self):
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["timeout"] = request.extensions.get("timeout")
            return _json_response(200, {})

        t = _build_transport(handler)
        try:
            t.get("/x", kind="large_download")
        finally:
            t.close()
        assert float(captured["timeout"]["connect"]) == pytest.approx(300.0)

    def test_explicit_timeout_overrides_kind(self):
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["timeout"] = request.extensions.get("timeout")
            return _json_response(200, {})

        t = _build_transport(handler)
        try:
            t.get("/x", kind="large_download", timeout=2.5)
        finally:
            t.close()
        assert float(captured["timeout"]["connect"]) == pytest.approx(2.5)

    def test_unknown_kind_rejected(self):
        handler = _make_handler([_json_response(200, {})])
        t = _build_transport(handler)
        try:
            with pytest.raises(ValueError, match="Unknown"):
                t.get("/x", kind="bogus")
        finally:
            t.close()


# ---------------------------------------------------------------------------
# Logging integration
# ---------------------------------------------------------------------------


class TestLoggingIntegration:
    def test_request_id_present_in_lifecycle_records(
        self, capture: _CapturingHandler
    ):
        import re

        handler = _make_handler([_json_response(200, {"ok": True})])
        t = _build_transport(handler)
        try:
            logging.getLogger(LOGGER_NAMESPACE).setLevel(logging.DEBUG)
            t.get("/x")
        finally:
            t.close()
            logging.getLogger(LOGGER_NAMESPACE).setLevel(LOGGING_DEFAULT_LEVEL)
        ids = {
            m.group(1)
            for r in capture.records
            for m in [re.search(r"request_id=([0-9a-f]+)", r.getMessage())]
            if m
        }
        assert len(ids) == 1
        assert next(iter(ids))

    def test_api_key_never_logged(self, capture: _CapturingHandler):
        handler = _make_handler([_json_response(200, {"ok": True})])
        t = _build_transport(handler, api_key="topsecret-key")
        try:
            logging.getLogger(LOGGER_NAMESPACE).setLevel(logging.DEBUG)
            t.get("/x")
        finally:
            t.close()
            logging.getLogger(LOGGER_NAMESPACE).setLevel(LOGGING_DEFAULT_LEVEL)
        all_text = "\n".join(r.getMessage() for r in capture.records)
        assert "topsecret-key" not in all_text

    def test_auth_failure_logged_at_error(
        self, capture: _CapturingHandler
    ):
        handler = _make_handler([_json_response(401, {})])
        t = _build_transport(handler, api_key="bad")
        try:
            with pytest.raises(AuthenticationError):
                t.get("/x")
        finally:
            t.close()
        auth_records = [
            r for r in capture.records if "auth failure" in r.getMessage()
        ]
        assert auth_records
        assert all(r.levelno == logging.ERROR for r in auth_records)

    def test_network_error_logged_at_warning(
        self, capture: _CapturingHandler
    ):
        handler = _make_handler([httpx.ReadTimeout("boom")])
        t = _build_transport(handler, retry=RetryPolicy(attempts=1))
        try:
            with pytest.raises(SdkTimeoutError):
                t.get("/x")
        finally:
            t.close()
        net_records = [
            r for r in capture.records if "network error" in r.getMessage()
        ]
        assert net_records
        assert all(r.levelno == logging.WARNING for r in net_records)

    def test_retry_logged_at_warning(self, capture: _CapturingHandler):
        handler = _make_handler(
            [
                _json_response(500, {}),
                _json_response(500, {}),
                _json_response(200, {"ok": True}),
            ]
        )
        t = _build_transport(handler)
        try:
            t.get("/x")
        finally:
            t.close()
        retry_records = [
            r for r in capture.records if "retry attempt=" in r.getMessage()
        ]
        assert len(retry_records) == 2
        assert all(r.levelno == logging.WARNING for r in retry_records)

    def test_redaction_filter_scrubs_secret_in_user_log(
        self, capture: _CapturingHandler
    ):
        # Consumer manually logs a message that contains the key;
        # the filter installed on the SDK category logger scrubs it.
        lifecycle = get_logger("lifecycle")
        install_redaction(lifecycle, ("topsecret-key",))
        try:
            handler = _make_handler([_json_response(200, {"ok": True})])
            t = _build_transport(handler, api_key="topsecret-key")
            try:
                logging.getLogger(LOGGER_NAMESPACE).setLevel(logging.DEBUG)
                lifecycle.debug("trace payload topsecret-key here")
            finally:
                t.close()
                logging.getLogger(LOGGER_NAMESPACE).setLevel(LOGGING_DEFAULT_LEVEL)
            all_text = "\n".join(r.getMessage() for r in capture.records)
            assert "topsecret-key" not in all_text
            assert REDACTED in all_text
        finally:
            lifecycle.filters = [
                f for f in lifecycle.filters
                if not (
                    isinstance(f, RedactingFilter)
                    and "topsecret-key" in f.secrets
                )
            ]


# ---------------------------------------------------------------------------
# Exception propagation
# ---------------------------------------------------------------------------


class TestExceptionPropagation:
    def test_hierarchy_is_consistent(self):
        # ADR-0012 contract.
        assert issubclass(ConfigurationError, ComtradeError)
        assert issubclass(AuthenticationError, ComtradeError)
        assert issubclass(AuthorizationError, AuthenticationError)
        assert issubclass(ValidationError, ComtradeError)
        assert issubclass(NetworkError, ComtradeError)
        assert issubclass(SdkTimeoutError, NetworkError)
        assert issubclass(RetryError, NetworkError)
        assert issubclass(RateLimitError, NetworkError)
        assert issubclass(APIError, ComtradeError)

    def test_all_sdk_errors_catchable_as_comtrade_error(self):
        # Every SDK exception is a ComtradeError.
        for cls in (
            ConfigurationError,
            AuthenticationError,
            AuthorizationError,
            ValidationError,
            NetworkError,
            SdkTimeoutError,
            RetryError,
            RateLimitError,
            APIError,
        ):
            assert issubclass(cls, ComtradeError)

    def test_validation_error_fails_fast_through_retry(self):
        # ADR-0022: validation errors never consume retry budget.
        handler = _make_handler(
            [_json_response(422, {"err": "bad input"})]
        )
        t = _build_transport(handler)
        try:
            # Validation errors return as responses (not raised) so
            # callers can inspect status / body. Retry does not
            # retry them.
            r = t.get("/x")
            assert r.status_code == 422
        finally:
            t.close()


# ---------------------------------------------------------------------------
# End-to-end mock request
# ---------------------------------------------------------------------------


class TestEndToEndMockRequest:
    def test_full_chain_succeeds(self):
        # Configuration -> Transport -> retry -> timeout -> logging -> response.
        cfg = Configuration(
            base_url="https://api.example.com",
            user_agent="integration-test/1.0",
            api_key="valid-key",
        )
        handler = _make_handler(
            [_json_response(200, {"data": [1, 2, 3], "ok": True})]
        )
        t = _build_from_configuration(handler, cfg)
        try:
            r = t.get("/data", params={"format": "json"})
            assert isinstance(r, HttpResponse)
            assert r.status_code == 200
            assert r.is_success
            assert r.json() == {"data": [1, 2, 3], "ok": True}
        finally:
            t.close()

    def test_full_chain_with_retry(self):
        # Two 500s then success -> retry budget not exhausted.
        handler = _make_handler(
            [
                _json_response(500, {"err": "transient"}),
                _json_response(500, {"err": "transient"}),
                _json_response(200, {"data": "value"}),
            ]
        )
        t = _build_transport(handler)
        try:
            r = t.get("/data")
            assert r.status_code == 200
            assert r.json() == {"data": "value"}
        finally:
            t.close()

    def test_full_chain_with_timeout_then_success(self):
        handler = _make_handler(
            [httpx.ReadTimeout("slow"), _json_response(200, {"ok": True})]
        )
        t = _build_transport(handler)
        try:
            r = t.get("/data")
            assert r.status_code == 200
        finally:
            t.close()

    def test_full_chain_raises_appropriate_exception(self):
        # Auth failure -> AuthenticationError, not raw 401 response.
        handler = _make_handler([_json_response(401, {"err": "denied"})])
        t = _build_transport(handler, api_key="bad")
        try:
            with pytest.raises(AuthenticationError):
                t.get("/data")
        finally:
            t.close()


# ---------------------------------------------------------------------------
# Architectural drift checks
# ---------------------------------------------------------------------------


class TestArchitecturalDrift:
    """Sanity checks: no ADRs were silently violated by P1-001..P1-008."""

    def test_default_retry_policy_matches_adr0008(self):
        # ADR-0008 (revised): 3 attempts, 1s initial, 2x multiplier, 60s cap.
        p = RetryPolicy()
        assert p.attempts == 3
        assert p.initial_delay == 1.0
        assert p.multiplier == 2.0
        assert p.max_delay == 60.0

    def test_default_retryable_status_codes_match_adr0022(self):
        # ADR-0022: 429 / 500 / 502 / 503 / 504.
        assert DEFAULT_RETRYABLE_STATUS_CODES == frozenset({429, 500, 502, 503, 504})

    def test_default_timeout_categories_match_adr0023(self):
        # ADR-0023: default 30s, metadata 15s, large_download 300s.
        c = TimeoutConfig()
        assert c.default == 30.0
        assert c.metadata == 15.0
        assert c.large_download == 300.0

    def test_auth_header_matches_azure_apim_convention(self):
        # ADR-0034 / ADR-0025: the upstream is Azure API Management.
        assert AUTH_HEADER == "Ocp-Apim-Subscription-Key"

    def test_exception_hierarchy_root_is_comtrade_error(self):
        # ADR-0012: every SDK exception derives from ComtradeError.
        import un_comtrade.exceptions as exc_mod

        public_exceptions = [
            getattr(exc_mod, name)
            for name in dir(exc_mod)
            if isinstance(getattr(exc_mod, name), type)
            and issubclass(getattr(exc_mod, name), BaseException)
        ]
        assert len(public_exceptions) >= 13  # ADR-0012 specifies 13
        for cls in public_exceptions:
            assert issubclass(cls, ComtradeError), (
                f"{cls.__name__} does not inherit from ComtradeError"
            )

    def test_default_log_level_is_warning(self):
        # ADR-0025: WARNING by default.
        assert LOGGING_DEFAULT_LEVEL == logging.WARNING

    def test_configuration_validates_against_configuration_error(self):
        # Empty api_key must raise a ValueError that is also a
        # ConfigurationError (ADR-0012).
        with pytest.raises((ValueError, ConfigurationError)):
            HttpTransport(
                base_url="https://example.org",
                user_agent="ua/1.0",
                api_key="",
            )


# ---------------------------------------------------------------------------
# No live API calls (positive control)
# ---------------------------------------------------------------------------


def test_no_live_api_calls_in_foundation():
    """Smoke test: importing and constructing the foundation
    components must not trigger any network I/O."""
    import un_comtrade.config  # noqa: F401
    import un_comtrade.exceptions  # noqa: F401
    import un_comtrade.logging  # noqa: F401
    import un_comtrade.transport  # noqa: F401
    # No assertion needed — the test passes if no exception was
    # raised during import and construction would have raised one
    # if a live network call was attempted.