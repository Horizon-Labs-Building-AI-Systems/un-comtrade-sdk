"""Unit tests for the `ComtradeClient` skeleton (P1-010).

The client composes the infrastructure built in P1-001
through P1-008. These tests verify:

- construction with explicit / default configuration,
- configuration injection into the transport,
- dependency graph (transport is built from config),
- lifecycle hooks (`close`, context manager),
- no network I/O at construction time,
- caller-supplied transport override.

No business methods are tested (none exist yet). All
tests use `httpx.MockTransport` so the suite never hits
the network.
"""

from __future__ import annotations

import logging
from typing import Callable

import httpx
import pytest

from un_comtrade.client import ComtradeClient
from un_comtrade.config import (
    DEFAULT_BASE_URL,
    Configuration,
    load_configuration,
)
from un_comtrade.exceptions import ConfigurationError
from un_comtrade.logging import LOGGER_NAMESPACE, LOG_LEVELS
from un_comtrade.transport import (
    HttpTransport,
    RetryPolicy,
    TimeoutConfig,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _json_response(status_code: int, body: object) -> httpx.Response:
    import json as _json

    return httpx.Response(
        status_code=status_code,
        content=_json.dumps(body).encode("utf-8"),
        headers={},
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


def _mock_transport(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    api_key: str | None = None,
) -> HttpTransport:
    """Build a caller-owned HttpTransport wired to a MockTransport.

    When `api_key` is provided, the transport injects the
    subscription-key header on every request — matching
    the behaviour of a transport built by `ComtradeClient`
    from a `Configuration`.
    """
    return HttpTransport(
        base_url="https://example.org",
        user_agent="ua/1.0",
        api_key=api_key,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------


class TestInstantiation:
    def test_default_construction_loads_environment(self, monkeypatch):
        monkeypatch.setenv("UN_COMTRADE_KEY", "env-key-123")
        monkeypatch.setenv("UN_COMTRADE_USER_AGENT", "test-agent/1.0")
        client = ComtradeClient()
        try:
            assert client.config.api_key == "env-key-123"
            assert client.config.user_agent == "test-agent/1.0"
        finally:
            client.close()

    def test_explicit_configuration(self):
        cfg = Configuration(
            base_url="https://api.example.com",
            user_agent="my-app/2.0",
            api_key="explicit-key",
        )
        client = ComtradeClient(cfg)
        try:
            assert client.config is cfg
            assert client.config.api_key == "explicit-key"
        finally:
            client.close()

    def test_default_base_url(self):
        # When no base_url is configured, the default is used.
        client = ComtradeClient()
        try:
            assert client.config.base_url == DEFAULT_BASE_URL
        finally:
            client.close()

    def test_configuration_is_immutable_post_construction(self):
        cfg = Configuration(api_key="x")
        client = ComtradeClient(cfg)
        try:
            # Configuration is a frozen dataclass; mutation raises.
            with pytest.raises((AttributeError, Exception)):
                client.config.api_key = "y"  # type: ignore[misc]
        finally:
            client.close()

    def test_constructor_does_not_perform_network_io(self):
        # Constructing a client must not invoke any handler.
        calls: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return _json_response(200, {"ok": True})

        client = ComtradeClient(transport=_mock_transport(handler))
        try:
            assert calls == []
        finally:
            client.close()


# ---------------------------------------------------------------------------
# Dependency graph
# ---------------------------------------------------------------------------


class TestDependencyGraph:
    def test_transport_built_from_configuration(self):
        cfg = Configuration(
            base_url="https://api.example.com",
            user_agent="integration-test/1.0",
            api_key="key-abc",
        )
        client = ComtradeClient(cfg)
        try:
            t = client.transport
            assert t.base_url == "https://api.example.com"
            assert t.user_agent == "integration-test/1.0"
            assert t.api_key == "key-abc"
        finally:
            client.close()

    def test_transport_retry_policy_matches_configuration(self):
        cfg = Configuration(
            base_url="https://example.org",
            user_agent="ua/1.0",
            max_retries=5,
            initial_backoff_seconds=2.0,
            backoff_multiplier=3.0,
            backoff_cap_seconds=90.0,
        )
        client = ComtradeClient(cfg)
        try:
            rp = client.transport.retry_policy
            assert rp.attempts == 5
            assert rp.initial_delay == 2.0
            assert rp.multiplier == 3.0
            assert rp.max_delay == 90.0
        finally:
            client.close()

    def test_transport_timeout_config_matches_configuration(self):
        cfg = Configuration(
            base_url="https://example.org",
            user_agent="ua/1.0",
            timeout_seconds=45.0,
            metadata_timeout_seconds=20.0,
            download_timeout_seconds=600.0,
        )
        client = ComtradeClient(cfg)
        try:
            tc = client.transport.timeout_config
            assert tc.default == 45.0
            assert tc.metadata == 20.0
            assert tc.large_download == 600.0
        finally:
            client.close()

    def test_default_retry_policy_is_adr0008(self):
        client = ComtradeClient()
        try:
            rp = client.transport.retry_policy
            # ADR-0008: 3 attempts, 1s initial, 2x multiplier, 60s cap.
            assert rp.attempts == 3
            assert rp.initial_delay == 1.0
            assert rp.multiplier == 2.0
            assert rp.max_delay == 60.0
        finally:
            client.close()

    def test_default_timeout_config_is_adr0023(self):
        client = ComtradeClient()
        try:
            tc = client.transport.timeout_config
            # ADR-0023: 30s default, 15s metadata, 300s large_download.
            assert tc.default == 30.0
            assert tc.metadata == 15.0
            assert tc.large_download == 300.0
        finally:
            client.close()

    def test_transport_is_http_transport_instance(self):
        client = ComtradeClient()
        try:
            assert isinstance(client.transport, HttpTransport)
        finally:
            client.close()


# ---------------------------------------------------------------------------
# API key injection
# ---------------------------------------------------------------------------


class TestApiKeyInjection:
    def test_api_key_in_request_when_configured(self):
        cfg = Configuration(
            base_url="https://example.org",
            user_agent="ua/1.0",
            api_key="secret-key",
        )
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(request.headers)
            return _json_response(200, {})

        # Inject a transport (with the same api_key) so we can
        # assert the auth header is present on requests.
        client = ComtradeClient(
            cfg,
            transport=_mock_transport(handler, api_key="secret-key"),
        )
        try:
            client.transport.get("/x")
            assert captured.get("ocp-apim-subscription-key") == "secret-key"
        finally:
            client.close()

    def test_no_api_key_when_unset(self):
        cfg = Configuration(base_url="https://example.org", user_agent="ua/1.0")
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(request.headers)
            return _json_response(200, {})

        client = ComtradeClient(cfg, transport=_mock_transport(handler))
        try:
            client.transport.get("/x")
            assert "ocp-apim-subscription-key" not in captured
        finally:
            client.close()


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_close_releases_owned_transport(self):
        client = ComtradeClient()
        try:
            owned_client = client.transport.client
            assert not owned_client.is_closed
            client.close()
            assert owned_client.is_closed
        finally:
            # Idempotent close.
            client.close()

    def test_close_does_not_close_caller_supplied_transport(self):
        cfg = Configuration(base_url="https://example.org", user_agent="ua/1.0")
        caller_transport = _mock_transport(
            _make_handler([_json_response(200, {})])
        )
        client = ComtradeClient(cfg, transport=caller_transport)
        try:
            assert not caller_transport.client.is_closed
            client.close()
            # Caller-supplied transport must NOT be closed.
            assert not caller_transport.client.is_closed
            # Caller's transport is still usable.
            r = caller_transport.get("https://example.org/x")
            assert r.status_code == 200
        finally:
            caller_transport.close()

    def test_close_is_idempotent(self):
        client = ComtradeClient()
        client.close()
        client.close()  # second call must not raise

    def test_context_manager_closes_owned_transport(self):
        with ComtradeClient() as client:
            owned_client = client.transport.client
            assert not owned_client.is_closed
        assert owned_client.is_closed

    def test_context_manager_returns_client(self):
        with ComtradeClient() as client:
            assert isinstance(client, ComtradeClient)
            assert client.config is not None
            assert client.transport is not None


# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------


class TestLoggingConfiguration:
    def test_log_level_applied_when_sdk_logger_unset(self, monkeypatch):
        # Pre-condition: ensure the SDK logger is NOTSET.
        sdk_logger = logging.getLogger(LOGGER_NAMESPACE)
        previous_level = sdk_logger.level
        sdk_logger.setLevel(logging.NOTSET)
        try:
            cfg = Configuration(
                base_url="https://example.org",
                user_agent="ua/1.0",
                log_level="DEBUG",
            )
            client = ComtradeClient(cfg)
            try:
                assert sdk_logger.level == logging.DEBUG
            finally:
                client.close()
        finally:
            sdk_logger.setLevel(previous_level)

    def test_log_level_not_overridden_when_sdk_logger_set(self):
        # If the consumer already configured the SDK logger, the
        # client must not silently override it.
        sdk_logger = logging.getLogger(LOGGER_NAMESPACE)
        previous_level = sdk_logger.level
        sdk_logger.setLevel(logging.ERROR)
        try:
            cfg = Configuration(
                base_url="https://example.org",
                user_agent="ua/1.0",
                log_level="DEBUG",
            )
            client = ComtradeClient(cfg)
            try:
                assert sdk_logger.level == logging.ERROR
            finally:
                client.close()
        finally:
            sdk_logger.setLevel(previous_level)

    def test_unknown_log_level_rejected_by_configuration(self):
        # Configuration validates log_level upstream; an unknown
        # level never reaches the client. (Defensive fallback in
        # `_configure_logging` exists for future-proofing only.)
        with pytest.raises(ConfigurationError):
            Configuration(
                base_url="https://example.org",
                user_agent="ua/1.0",
                log_level="BOGUS",
            )


# ---------------------------------------------------------------------------
# Configuration integration
# ---------------------------------------------------------------------------


class TestConfigurationIntegration:
    def test_config_property_exposes_configuration(self):
        cfg = Configuration(base_url="https://example.org", user_agent="ua/1.0")
        client = ComtradeClient(cfg)
        try:
            assert client.config is cfg
        finally:
            client.close()

    def test_load_configuration_factory_used_when_none_provided(
        self, monkeypatch
    ):
        monkeypatch.setenv("UN_COMTRADE_KEY", "factory-key")
        client = ComtradeClient()  # no config supplied
        try:
            assert client.config.api_key == "factory-key"
        finally:
            client.close()

    def test_configuration_error_propagates_through_constructor(self):
        # An invalid Configuration (e.g. whitespace api_key) raises
        # ConfigurationError at construction time per ADR-0034.
        with pytest.raises(ConfigurationError):
            ComtradeClient(
                Configuration(
                    base_url="https://example.org",
                    user_agent="ua/1.0",
                    api_key="   ",  # invalid
                )
            )


# ---------------------------------------------------------------------------
# End-to-end smoke (no business methods yet)
# ---------------------------------------------------------------------------


class TestEndToEndSmoke:
    def test_transport_callable_via_client(self):
        cfg = Configuration(
            base_url="https://example.org",
            user_agent="ua/1.0",
            api_key="key",
        )
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(request.headers)
            return _json_response(200, {"ok": True})

        client = ComtradeClient(
            cfg,
            transport=_mock_transport(handler, api_key="key"),
        )
        try:
            r = client.transport.get("/x")
            assert r.status_code == 200
            assert r.json() == {"ok": True}
            assert captured.get("ocp-apim-subscription-key") == "key"
        finally:
            client.close()

    def test_401_raises_authentication_error_via_client(self):
        cfg = Configuration(
            base_url="https://example.org",
            user_agent="ua/1.0",
            api_key="bad-key",
        )
        from un_comtrade.exceptions import AuthenticationError

        handler = _make_handler([_json_response(401, {"err": 1})])
        client = ComtradeClient(cfg, transport=_mock_transport(handler))
        try:
            with pytest.raises(AuthenticationError):
                client.transport.get("/x")
        finally:
            client.close()


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------


class TestModuleExports:
    def test_client_class_exported(self):
        from un_comtrade import client as client_mod
        assert hasattr(client_mod, "ComtradeClient")
        assert client_mod.ComtradeClient is ComtradeClient

    def test_client_in_dunder_all(self):
        from un_comtrade import client as client_mod
        assert "ComtradeClient" in client_mod.__all__