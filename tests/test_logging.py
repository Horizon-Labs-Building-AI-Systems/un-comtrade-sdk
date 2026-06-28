"""Unit tests for the SDK logging subsystem.

Covers:

- the logger factory (`get_logger`),
- the request-id generator,
- the structured `LogContext` dataclass,
- the `RedactingFilter` and `install_redaction` helper,
- end-to-end emission of request / response / retry /
  auth / network records through `HttpTransport`.

All tests use the standard library `logging` and a
capturing handler — no live network calls.
"""

from __future__ import annotations

import logging
from typing import Callable, List

import httpx
import pytest

from un_comtrade.logging import (
    AUTH_HEADER,
    AUTH_QUERY_PARAM,
    LOGGER_NAMESPACE,
    LOG_CATEGORIES,
    LOG_LEVELS,
    LOGGING_DEFAULT_LEVEL,
    LogContext,
    REDACTED,
    RedactingFilter,
    generate_request_id,
    get_logger,
    install_redaction,
)
from un_comtrade.transport import HttpTransport, RetryPolicy


# ---------------------------------------------------------------------------
# Capturing handler
# ---------------------------------------------------------------------------


class _CapturingHandler(logging.Handler):
    """Logging handler that records every emitted record."""

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: List[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def capture() -> _CapturingHandler:
    """Return a capturing handler and wire it to the SDK root.

    The handler accepts DEBUG records; tests that want to see
    DEBUG-level output must temporarily set the SDK root level
    to DEBUG themselves. Default WARNING level is preserved.
    """
    handler = _CapturingHandler()
    sdk_root = logging.getLogger(LOGGER_NAMESPACE)
    sdk_root.addHandler(handler)
    yield handler
    sdk_root.removeHandler(handler)


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


def _transport(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    api_key: str | None = None,
    retry: RetryPolicy | None = None,
) -> HttpTransport:
    kwargs: dict[str, object] = dict(
        base_url="https://example.org",
        user_agent="ua/1.0",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    if api_key is not None:
        kwargs["api_key"] = api_key
    if retry is not None:
        kwargs["retry"] = retry
    return HttpTransport(**kwargs)  # type: ignore[arg-type]


def _format(record: logging.LogRecord) -> str:
    """Return the formatted message for a record."""
    return record.getMessage()


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------


class TestLoggerFactory:
    def test_get_logger_returns_namespaced_logger(self):
        logger = get_logger("lifecycle")
        assert logger.name == f"{LOGGER_NAMESPACE}.lifecycle"
        assert isinstance(logger, logging.Logger)

    def test_get_logger_each_category(self):
        for cat in LOG_CATEGORIES:
            assert get_logger(cat).name == f"{LOGGER_NAMESPACE}.{cat}"

    def test_get_logger_unknown_category_raises(self):
        with pytest.raises(ValueError, match="Unknown"):
            get_logger("not-a-category")

    def test_get_logger_returns_same_instance(self):
        # logging.getLogger is idempotent on name.
        assert get_logger("lifecycle") is get_logger("lifecycle")


class TestLogCategoriesAndLevels:
    def test_categories_constant(self):
        assert LOG_CATEGORIES == frozenset(
            {
                "lifecycle",
                "retry",
                "cache",
                "validation",
                "network",
                "upstream",
                "security",
                "metadata",
            }
        )

    def test_default_level_is_warning(self):
        # ADR-0025: default WARNING.
        assert LOGGING_DEFAULT_LEVEL == logging.WARNING

    def test_log_levels_mapping(self):
        assert LOG_LEVELS["DEBUG"] == logging.DEBUG
        assert LOG_LEVELS["INFO"] == logging.INFO
        assert LOG_LEVELS["WARNING"] == logging.WARNING
        assert LOG_LEVELS["ERROR"] == logging.ERROR
        assert LOG_LEVELS["CRITICAL"] == logging.CRITICAL


# ---------------------------------------------------------------------------
# Request ID
# ---------------------------------------------------------------------------


class TestRequestId:
    def test_is_string(self):
        rid = generate_request_id()
        assert isinstance(rid, str)
        assert len(rid) > 0

    def test_unique_per_call(self):
        ids = {generate_request_id() for _ in range(100)}
        assert len(ids) == 100

    def test_is_uuid4_hex(self):
        rid = generate_request_id()
        # UUID4 hex is 32 chars; matches a fixed pattern.
        assert len(rid) == 32
        int(rid, 16)  # raises if not hex


# ---------------------------------------------------------------------------
# LogContext
# ---------------------------------------------------------------------------


class TestLogContext:
    def test_fields(self):
        ctx = LogContext(
            level="DEBUG",
            category="lifecycle",
            request_id="abc",
            message="hello",
            context={"k": "v"},
        )
        assert ctx.level == "DEBUG"
        assert ctx.category == "lifecycle"
        assert ctx.request_id == "abc"
        assert ctx.message == "hello"
        assert dict(ctx.context) == {"k": "v"}

    def test_default_context_is_empty(self):
        ctx = LogContext(
            level="INFO",
            category="lifecycle",
            request_id="x",
            message="hi",
        )
        assert dict(ctx.context) == {}

    def test_timestamp_is_iso8601(self):
        ctx = LogContext(
            level="INFO",
            category="lifecycle",
            request_id="x",
            message="hi",
        )
        ts = ctx.timestamp
        # Parses back; ISO-8601 with timezone offset.
        from datetime import datetime
        parsed = datetime.fromisoformat(ts)
        assert parsed.tzinfo is not None

    def test_frozen_immutable(self):
        ctx = LogContext(
            level="INFO",
            category="lifecycle",
            request_id="x",
            message="hi",
        )
        with pytest.raises((AttributeError, Exception)):
            ctx.level = "ERROR"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------


class TestRedactingFilter:
    def test_no_secrets_passes_through(self):
        flt = RedactingFilter()
        rec = logging.LogRecord(
            "x", logging.INFO, "/", 1, "hello world", None, None
        )
        assert flt.filter(rec) is True
        assert _format(rec) == "hello world"

    def test_redacts_secret_in_message(self):
        flt = RedactingFilter(secrets=("super-secret",))
        rec = logging.LogRecord(
            "x", logging.INFO, "/", 1,
            "got key super-secret from upstream", None, None,
        )
        flt.filter(rec)
        assert "super-secret" not in _format(rec)
        assert REDACTED in _format(rec)

    def test_redacts_multiple_secrets(self):
        flt = RedactingFilter(secrets=("alpha", "beta"))
        rec = logging.LogRecord(
            "x", logging.INFO, "/", 1,
            "alpha then beta", None, None,
        )
        flt.filter(rec)
        msg = _format(rec)
        assert "alpha" not in msg
        assert "beta" not in msg
        assert msg == f"{REDACTED} then {REDACTED}"

    def test_drops_empty_and_non_string_secrets(self):
        flt = RedactingFilter(secrets=("", None, "real"))  # type: ignore[arg-type]
        assert flt.secrets == ("real",)

    def test_args_dropped_after_filter(self):
        # `record.args` is cleared so a consumer that reads
        # `record.msg` does not see the original args.
        flt = RedactingFilter(secrets=("topsecret",))
        rec = logging.LogRecord(
            "x", logging.INFO, "/", 1,
            "header=%s", ("topsecret",), None,
        )
        flt.filter(rec)
        assert rec.args == ()
        assert "topsecret" not in _format(rec)

    def test_auth_header_constant(self):
        # The transport and logging modules agree on the header name.
        assert AUTH_HEADER == "Ocp-Apim-Subscription-Key"

    def test_auth_query_param_constant(self):
        assert AUTH_QUERY_PARAM == "subscription-key"


class TestInstallRedaction:
    def test_attach_returns_filter(self):
        logger = logging.getLogger("test_install_redaction")
        flt = install_redaction(logger, ("secret",))
        assert isinstance(flt, RedactingFilter)
        assert flt in logger.filters

    def test_redaction_works_after_install(self, caplog):
        logger = logging.getLogger("test_install_redaction_apply")
        logger.setLevel(logging.DEBUG)
        install_redaction(logger, ("topsecret",))
        with caplog.at_level(logging.DEBUG, logger="test_install_redaction_apply"):
            logger.info("payload topsecret here")
        # caplog captures the unfiltered message; the filter mutates
        # the record before the caplog handler fires in this test
        # setup, so we instead verify by checking the filter directly.
        flt = next(
            f for f in logger.filters if isinstance(f, RedactingFilter)
        )
        rec = logging.LogRecord(
            "test_install_redaction_apply",
            logging.INFO,
            "/",
            1,
            "payload topsecret here",
            None,
            None,
        )
        flt.filter(rec)
        assert "topsecret" not in _format(rec)


# ---------------------------------------------------------------------------
# End-to-end: transport logging
# ---------------------------------------------------------------------------


class TestTransportRequestLogging:
    def test_request_logged_at_debug(self, capture: _CapturingHandler):
        handler = _make_handler([_json_response(200, {"ok": True})])
        t = _transport(handler)
        try:
            # Bump SDK logger level to DEBUG so the capture sees it.
            logging.getLogger(LOGGER_NAMESPACE).setLevel(logging.DEBUG)
            t.get("/x")
        finally:
            t.close()
            logging.getLogger(LOGGER_NAMESPACE).setLevel(LOGGING_DEFAULT_LEVEL)
        msgs = [_format(r) for r in capture.records]
        # Lifecycle start + end.
        assert any("request method=GET" in m and "/x" in m for m in msgs)
        assert any("response status=200" in m for m in msgs)

    def test_request_logged_at_debug_for_post(self, capture: _CapturingHandler):
        handler = _make_handler([_json_response(200, {"ok": True})])
        t = _transport(handler)
        try:
            logging.getLogger(LOGGER_NAMESPACE).setLevel(logging.DEBUG)
            t.post("/y")
        finally:
            t.close()
            logging.getLogger(LOGGER_NAMESPACE).setLevel(LOGGING_DEFAULT_LEVEL)
        msgs = [_format(r) for r in capture.records]
        assert any("request method=POST" in m for m in msgs)

    def test_request_id_correlates_records(self, capture: _CapturingHandler):
        handler = _make_handler([_json_response(200, {"ok": True})])
        t = _transport(handler)
        try:
            logging.getLogger(LOGGER_NAMESPACE).setLevel(logging.DEBUG)
            t.get("/x")
        finally:
            t.close()
            logging.getLogger(LOGGER_NAMESPACE).setLevel(LOGGING_DEFAULT_LEVEL)
        # All records emitted during this call share a request_id.
        ids = {
            r.getMessage().split("request_id=")[-1].split()[0].rstrip(",")
            for r in capture.records
            if "request_id=" in r.getMessage()
        }
        assert len(ids) == 1
        assert next(iter(ids)) != ""


class TestTransportLogLevels:
    def test_default_warning_suppresses_request_log(self, capture: _CapturingHandler):
        # Default WARNING level; request/response logs at DEBUG should
        # not be emitted to the capturing handler.
        handler = _make_handler([_json_response(200, {"ok": True})])
        t = _transport(handler)
        try:
            t.get("/x")
        finally:
            t.close()
        msgs = [_format(r) for r in capture.records]
        assert not any("request method=" in m for m in msgs)
        assert not any("response status=" in m for m in msgs)

    def test_network_error_logged_at_warning(self, capture: _CapturingHandler):
        handler = _make_handler([httpx.ReadTimeout("boom")])
        t = _transport(handler, retry=RetryPolicy(attempts=1))
        try:
            with pytest.raises(Exception):
                t.get("/x")
        finally:
            t.close()
        msgs = [_format(r) for r in capture.records]
        assert any("network error" in m for m in msgs)
        # The network error log is at WARNING level.
        levels = [
            r.levelno for r in capture.records if "network error" in _format(r)
        ]
        assert levels == [logging.WARNING]

    def test_auth_failure_logged_at_error(self, capture: _CapturingHandler):
        handler = _make_handler([_json_response(401, {"err": 1})])
        t = _transport(handler)
        try:
            with pytest.raises(Exception):
                t.get("/x")
        finally:
            t.close()
        msgs = [_format(r) for r in capture.records]
        assert any("auth failure" in m for m in msgs)
        levels = [
            r.levelno for r in capture.records if "auth failure" in _format(r)
        ]
        assert levels == [logging.ERROR]

    def test_retry_logged_at_warning(self, capture: _CapturingHandler):
        # Three 500s -> two retry warnings (attempts 2 and 3) before
        # exhaustion.
        handler = _make_handler(
            [
                _json_response(500, {}),
                _json_response(500, {}),
                _json_response(500, {}),
            ]
        )
        t = _transport(handler)
        try:
            with pytest.raises(Exception):
                t.get("/x")
        finally:
            t.close()
        retry_msgs = [
            r for r in capture.records if "retry attempt=" in _format(r)
        ]
        assert len(retry_msgs) == 2
        assert all(r.levelno == logging.WARNING for r in retry_msgs)


class TestApiKeyRedaction:
    def test_api_key_never_logged_at_default_level(
        self, capture: _CapturingHandler
    ):
        handler = _make_handler([_json_response(200, {"ok": True})])
        t = _transport(handler, api_key="super-secret-key")
        try:
            t.get("/x")
        finally:
            t.close()
        # Even with redaction, no log should ever contain the key.
        all_text = "\n".join(_format(r) for r in capture.records)
        assert "super-secret-key" not in all_text

    def test_api_key_not_logged_at_debug_level(self, capture: _CapturingHandler):
        handler = _make_handler([_json_response(200, {"ok": True})])
        t = _transport(handler, api_key="super-secret-key")
        try:
            logging.getLogger(LOGGER_NAMESPACE).setLevel(logging.DEBUG)
            t.get("/x")
        finally:
            t.close()
            logging.getLogger(LOGGER_NAMESPACE).setLevel(LOGGING_DEFAULT_LEVEL)
        all_text = "\n".join(_format(r) for r in capture.records)
        assert "super-secret-key" not in all_text

    def test_redaction_filter_blocks_key_in_message(
        self, capture: _CapturingHandler
    ):
        # Install the filter on the actual category logger that
        # the SDK uses, then verify a synthetic log through that
        # logger is scrubbed.
        lifecycle_logger = get_logger("lifecycle")
        install_redaction(lifecycle_logger, ("super-secret-key",))
        try:
            handler = _make_handler([_json_response(200, {"ok": True})])
            t = _transport(handler, api_key="super-secret-key")
            try:
                logging.getLogger(LOGGER_NAMESPACE).setLevel(logging.DEBUG)
                t.get("/x")
                # A synthetic log message through the same logger.
                lifecycle_logger.debug(
                    "trace includes super-secret-key for diagnostics"
                )
            finally:
                t.close()
                logging.getLogger(LOGGER_NAMESPACE).setLevel(LOGGING_DEFAULT_LEVEL)
            all_text = "\n".join(_format(r) for r in capture.records)
            assert "super-secret-key" not in all_text
            assert REDACTED in all_text
        finally:
            # Remove the filter we installed.
            lifecycle_logger.filters = [
                f for f in lifecycle_logger.filters
                if not (
                    isinstance(f, RedactingFilter)
                    and "super-secret-key" in f.secrets
                )
            ]


class TestFullUrlRedaction:
    def test_response_url_not_logged(self, capture: _CapturingHandler):
        # The response URL (which could contain a subscription-key
        # query param if a caller uses the legacy preview endpoint)
        # must never appear in a log record. Only the path is logged.
        handler = _make_handler(
            [
                _json_response(
                    200,
                    {"ok": True},
                    headers={"Location": "https://example.org/x?subscription-key=ZZZ"},
                )
            ]
        )
        t = _transport(handler)
        try:
            logging.getLogger(LOGGER_NAMESPACE).setLevel(logging.DEBUG)
            t.get("/x")
        finally:
            t.close()
            logging.getLogger(LOGGER_NAMESPACE).setLevel(LOGGING_DEFAULT_LEVEL)
        all_text = "\n".join(_format(r) for r in capture.records)
        assert "ZZZ" not in all_text


class TestExceptionLogging:
    def test_timeout_logged_at_warning(self, capture: _CapturingHandler):
        handler = _make_handler([httpx.ReadTimeout("boom")])
        t = _transport(handler, retry=RetryPolicy(attempts=1))
        try:
            with pytest.raises(Exception):
                t.get("/x")
        finally:
            t.close()
        network_msgs = [
            r for r in capture.records if "network error" in _format(r)
        ]
        assert network_msgs
        assert all(r.levelno == logging.WARNING for r in network_msgs)

    def test_auth_failure_logged(self, capture: _CapturingHandler):
        handler = _make_handler([_json_response(401, {"err": 1})])
        t = _transport(handler)
        try:
            with pytest.raises(Exception):
                t.get("/x")
        finally:
            t.close()
        security_msgs = [
            r for r in capture.records if "auth failure" in _format(r)
        ]
        assert security_msgs
        assert all(r.levelno == logging.ERROR for r in security_msgs)

    def test_retry_exhaustion_logged(self, capture: _CapturingHandler):
        handler = _make_handler(
            [
                _json_response(500, {}),
                _json_response(500, {}),
                _json_response(500, {}),
            ]
        )
        t = _transport(handler)
        try:
            with pytest.raises(Exception):
                t.get("/x")
        finally:
            t.close()
        # Two retry attempts logged at WARNING.
        retry_msgs = [
            r for r in capture.records if "retry attempt=" in _format(r)
        ]
        assert len(retry_msgs) == 2


class TestNoDuplicateLogs:
    def test_no_duplicate_request_log(self, capture: _CapturingHandler):
        handler = _make_handler([_json_response(200, {"ok": True})])
        t = _transport(handler)
        try:
            logging.getLogger(LOGGER_NAMESPACE).setLevel(logging.DEBUG)
            t.get("/x")
        finally:
            t.close()
            logging.getLogger(LOGGER_NAMESPACE).setLevel(LOGGING_DEFAULT_LEVEL)
        # Exactly one request-start and one response-end log.
        starts = [r for r in capture.records if "request method=" in _format(r)]
        ends = [r for r in capture.records if "response status=" in _format(r)]
        assert len(starts) == 1
        assert len(ends) == 1

    def test_no_duplicate_retry_log(self, capture: _CapturingHandler):
        # 500 -> 500 -> 200: two retry logs (one for each retry attempt).
        handler = _make_handler(
            [
                _json_response(500, {}),
                _json_response(500, {}),
                _json_response(200, {"ok": True}),
            ]
        )
        t = _transport(handler)
        try:
            t.get("/x")
        finally:
            t.close()
        retry_msgs = [
            r for r in capture.records if "retry attempt=" in _format(r)
        ]
        assert len(retry_msgs) == 2

    def test_no_log_after_close(self, capture: _CapturingHandler):
        handler = _make_handler([_json_response(200, {"ok": True})])
        t = _transport(handler)
        t.close()
        # Calling close should not emit a log record.
        after_close = list(capture.records)
        assert all(
            "request method=" not in _format(r)
            and "response status=" not in _format(r)
            for r in after_close
        )


class TestConsumerLoggerOverride:
    def test_consumer_can_pass_own_logger(self, capture: _CapturingHandler):
        # Consumer supplies a custom logger; the transport should
        # use it instead of the default.
        my_logger = logging.getLogger("my.test.logger")
        my_logger.setLevel(logging.DEBUG)
        handler = _make_handler([_json_response(200, {"ok": True})])
        # Configure handler so we can capture the consumer's log.
        my_capture = _CapturingHandler()
        my_logger.addHandler(my_capture)
        try:
            t = HttpTransport(
                base_url="https://example.org",
                user_agent="ua/1.0",
                client=httpx.Client(transport=httpx.MockTransport(handler)),
                logger=my_logger,
            )
            try:
                t.get("/x")
            finally:
                t.close()
        finally:
            my_logger.removeHandler(my_capture)
        msgs = [_format(r) for r in my_capture.records]
        assert any("request method=GET" in m for m in msgs)
        assert any("response status=200" in m for m in msgs)