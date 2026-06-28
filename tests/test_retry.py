"""Unit tests for the transport's retry middleware (built into HttpTransport).

The retry logic lives inside `un_comtrade.transport.HttpTransport`
per ADR-0008 (3 attempts, exponential backoff) and ADR-0022
(retryable error set). These tests exercise the retry behaviour
end-to-end through the public `HttpTransport.request()` /
`.get()` / `.post()` surface.

All tests use a fake sleeper and `httpx.MockTransport` so the
suite is fully deterministic and never hits the network.
"""

from __future__ import annotations

from typing import Callable

import httpx
import pytest

from un_comtrade.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NetworkError,
    RetryError,
)
from un_comtrade.transport import (
    DEFAULT_RETRYABLE_EXCEPTIONS,
    DEFAULT_RETRYABLE_STATUS_CODES,
    HttpResponse,
    HttpTransport,
    RetryPolicy,
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
    """Build a MockTransport handler that drains a pre-built queue.

    Each invocation pops one element. If it's an exception instance
    or class, the handler raises it. If it's an `httpx.Response`,
    it returns it.
    """
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        if not queue:
            raise AssertionError("MockTransport queue exhausted unexpectedly")
        item = queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        if isinstance(item, type) and issubclass(item, BaseException):
            raise item()
        item.request = request
        return item

    return handler


class _RecordingSleeper:
    """Sleeper stub that records each requested sleep duration."""

    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def _transport(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    retry: RetryPolicy | None = None,
    sleeper: Callable[[float], None] | None = None,
) -> HttpTransport:
    """Build an HttpTransport wired to a MockTransport handler."""
    kwargs: dict[str, object] = dict(
        base_url="https://example.org",
        user_agent="ua/1.0",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    if retry is not None:
        kwargs["retry"] = retry
    if sleeper is not None:
        kwargs["sleeper"] = sleeper
    return HttpTransport(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# RetryPolicy
# ---------------------------------------------------------------------------


class TestRetryPolicyDefaults:
    def test_defaults_match_adr0008(self):
        p = RetryPolicy()
        assert p.attempts == 3
        assert p.initial_delay == 1.0
        assert p.multiplier == 2.0
        assert p.max_delay == 60.0

    def test_default_retryable_status_codes(self):
        p = RetryPolicy()
        assert p.retryable_status_codes == DEFAULT_RETRYABLE_STATUS_CODES
        assert p.retryable_status_codes == frozenset({429, 500, 502, 503, 504})

    def test_default_retryable_exceptions_include_timeout(self):
        p = RetryPolicy()
        assert httpx.TimeoutException in p.retryable_exceptions
        assert httpx.ConnectError in p.retryable_exceptions

    def test_retry_error_is_network_error_subclass(self):
        # ADR-0012: RetryError is a NetworkError.
        assert issubclass(RetryError, NetworkError)


class TestRetryPolicyValidation:
    @pytest.mark.parametrize("attempts", [0, -1, -5])
    def test_rejects_attempts_below_one(self, attempts: int):
        with pytest.raises(ValueError, match="attempts"):
            RetryPolicy(attempts=attempts)

    def test_rejects_negative_initial_delay(self):
        with pytest.raises(ValueError, match="initial_delay"):
            RetryPolicy(initial_delay=-0.5)

    def test_rejects_multiplier_below_one(self):
        with pytest.raises(ValueError, match="multiplier"):
            RetryPolicy(multiplier=0.5)

    def test_rejects_max_delay_below_initial(self):
        with pytest.raises(ValueError, match="max_delay"):
            RetryPolicy(initial_delay=10.0, max_delay=5.0)

    def test_frozen_immutable(self):
        p = RetryPolicy()
        with pytest.raises((AttributeError, Exception)):
            p.attempts = 99  # type: ignore[misc]


class TestRetryPolicyScheduling:
    def test_first_attempt_no_delay(self):
        p = RetryPolicy()
        assert p.delay_for_attempt(1) == 0.0

    def test_second_attempt_uses_initial_delay(self):
        p = RetryPolicy()
        assert p.delay_for_attempt(2) == 1.0

    def test_third_attempt_uses_multiplier(self):
        p = RetryPolicy()
        assert p.delay_for_attempt(3) == 2.0

    def test_delay_caps_at_max(self):
        # 10th attempt would be 1 * 2**8 = 256; capped to 60.
        p = RetryPolicy(initial_delay=1.0, multiplier=2.0, max_delay=60.0)
        assert p.delay_for_attempt(10) == 60.0

    def test_custom_multiplier(self):
        p = RetryPolicy(initial_delay=1.0, multiplier=3.0)
        assert p.delay_for_attempt(2) == 1.0
        assert p.delay_for_attempt(3) == 3.0
        assert p.delay_for_attempt(4) == 9.0

    def test_attempts_zero_or_negative_returns_zero(self):
        p = RetryPolicy()
        assert p.delay_for_attempt(0) == 0.0
        assert p.delay_for_attempt(-3) == 0.0


class TestRetryPolicyParseRetryAfter:
    def _response(self, value: str | None) -> HttpResponse:
        return HttpResponse(
            status_code=429,
            body=b"{}",
            headers={"Retry-After": value} if value is not None else {},
            elapsed_seconds=0.0,
            url="https://example.org",
        )

    def test_parses_integer_seconds(self):
        p = RetryPolicy()
        assert p.parse_retry_after(self._response("1")) == 1.0

    def test_parses_decimal_seconds(self):
        p = RetryPolicy()
        assert p.parse_retry_after(self._response("0.5")) == 0.5

    def test_caps_at_max_delay(self):
        p = RetryPolicy(max_delay=5.0)
        assert p.parse_retry_after(self._response("120")) == 5.0

    def test_missing_header_returns_none(self):
        p = RetryPolicy()
        assert p.parse_retry_after(self._response(None)) is None

    def test_http_date_returns_none(self):
        p = RetryPolicy()
        # RFC 7231 HTTP-date form is not supported in MVP.
        assert p.parse_retry_after(
            self._response("Wed, 21 Oct 2015 07:28:00 GMT")
        ) is None

    def test_negative_value_clamped_to_zero(self):
        p = RetryPolicy()
        assert p.parse_retry_after(self._response("-5")) == 0.0


class TestRetryPolicyDecision:
    def test_retryable_response(self):
        p = RetryPolicy()
        assert p.is_retryable_response(HttpResponse(500, b"", {}, 0.0, "u"))
        assert p.is_retryable_response(HttpResponse(429, b"", {}, 0.0, "u"))

    def test_non_retryable_response(self):
        p = RetryPolicy()
        assert not p.is_retryable_response(HttpResponse(200, b"", {}, 0.0, "u"))
        assert not p.is_retryable_response(HttpResponse(400, b"", {}, 0.0, "u"))
        assert not p.is_retryable_response(HttpResponse(404, b"", {}, 0.0, "u"))
        assert not p.is_retryable_response(HttpResponse(422, b"", {}, 0.0, "u"))

    def test_retryable_exception(self):
        p = RetryPolicy()
        assert p.is_retryable_exception(httpx.ConnectError("boom"))
        assert p.is_retryable_exception(httpx.ReadTimeout("boom"))
        assert p.is_retryable_exception(ConnectionError("boom"))

    def test_non_retryable_exception(self):
        p = RetryPolicy()
        assert not p.is_retryable_exception(ValueError("nope"))
        assert not p.is_retryable_exception(KeyError("k"))


# ---------------------------------------------------------------------------
# HttpTransport retry behaviour
# ---------------------------------------------------------------------------


class TestRetryHappyPath:
    def test_single_success_no_retry(self):
        handler = _make_handler(
            [_json_response(200, {"ok": True}), _json_response(200, {"ignored": True})]
        )
        sleeper = _RecordingSleeper()
        t = _transport(handler, sleeper=sleeper)
        try:
            r = t.get("/x")
        finally:
            t.close()
        assert r.status_code == 200
        assert sleeper.calls == []  # never slept

    def test_retries_500_then_succeeds(self):
        handler = _make_handler(
            [
                _json_response(500, {"err": 1}),
                _json_response(500, {"err": 2}),
                _json_response(200, {"ok": True}),
            ]
        )
        sleeper = _RecordingSleeper()
        t = _transport(handler, sleeper=sleeper)
        try:
            r = t.get("/x")
        finally:
            t.close()
        assert r.status_code == 200
        # First sleep = initial_delay (1.0); second = 2.0
        assert sleeper.calls == [1.0, 2.0]


class TestRetryEachRetryableStatus:
    """Validate the per-status-code retry contract from ADR-0022."""

    @pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
    def test_retries_each_documented_status(self, status: int):
        handler = _make_handler(
            [
                _json_response(status, {"err": status}),
                _json_response(200, {"ok": True}),
            ]
        )
        sleeper = _RecordingSleeper()
        t = _transport(handler, sleeper=sleeper)
        try:
            r = t.get("/x")
        finally:
            t.close()
        assert r.status_code == 200
        assert sleeper.calls == [1.0]


class TestRetryExhaustion:
    def test_budget_exhausted_raises_retry_error_with_response(self):
        handler = _make_handler(
            [
                _json_response(500, {"err": 1}),
                _json_response(500, {"err": 2}),
                _json_response(500, {"err": 3}),
            ]
        )
        t = _transport(handler, sleeper=_RecordingSleeper())
        try:
            with pytest.raises(RetryError) as excinfo:
                t.get("/x")
            # No underlying exception (last attempt was a response, not raise).
            assert excinfo.value.__cause__ is None
            assert "500" in str(excinfo.value)
        finally:
            t.close()

    def test_budget_exhausted_on_timeout_raises_retry_error(self):
        # 3 timeouts; the transport translates each into SDK TimeoutError,
        # the retry loop sees SdkTimeoutError (retryable), and the third
        # attempt raises RetryError chained to the last SDK TimeoutError,
        # which itself is chained to the original httpx.ReadTimeout.
        from un_comtrade.exceptions import TimeoutError as SdkTimeoutError

        handler = _make_handler(
            [
                httpx.ReadTimeout("timeout"),
                httpx.ReadTimeout("timeout"),
                httpx.ReadTimeout("timeout"),
            ]
        )
        t = _transport(handler, sleeper=_RecordingSleeper())
        try:
            with pytest.raises(RetryError) as excinfo:
                t.get("/x")
            assert isinstance(excinfo.value.__cause__, SdkTimeoutError)
            assert isinstance(excinfo.value.__cause__.__cause__, httpx.ReadTimeout)
        finally:
            t.close()

    def test_custom_attempts(self):
        # With attempts=2, two consecutive 500s exhaust the budget.
        handler = _make_handler(
            [
                _json_response(500, {"err": 1}),
                _json_response(500, {"err": 2}),
            ]
        )
        sleeper = _RecordingSleeper()
        t = _transport(handler, retry=RetryPolicy(attempts=2), sleeper=sleeper)
        try:
            with pytest.raises(RetryError):
                t.get("/x")
            # One retry -> one sleep at the initial delay.
            assert sleeper.calls == [1.0]
        finally:
            t.close()


class TestRetryNeverOnValidation:
    """ADR-0022: validation errors (4xx other than 429) NEVER retry."""

    @pytest.mark.parametrize("status", [400, 404, 422])
    def test_does_not_retry_validation_responses(self, status: int):
        handler = _make_handler(
            [_json_response(status, {"err": status}), _json_response(200, {"ok": True})]
        )
        sleeper = _RecordingSleeper()
        t = _transport(handler, sleeper=sleeper)
        try:
            r = t.get("/x")
        finally:
            t.close()
        assert r.status_code == status
        assert sleeper.calls == []

    @pytest.mark.parametrize("status", [401, 403])
    def test_does_not_retry_auth_failures(self, status: int):
        # 401 / 403 are translated into SDK exceptions by the transport
        # (per ADR-0012 + ADR-0034). The retry layer must NOT retry on
        # those: AuthenticationError / AuthorizationError are not in
        # the retryable exception set, so they propagate without
        # consuming the budget.
        handler = _make_handler(
            [_json_response(status, {"err": status}), _json_response(200, {"ok": True})]
        )
        sleeper = _RecordingSleeper()
        t = _transport(handler, sleeper=sleeper)
        try:
            with pytest.raises(Exception) as excinfo:
                t.get("/x")
            assert excinfo.value.__cause__ is None
            assert sleeper.calls == []
        finally:
            t.close()

    def test_401_raises_authentication_error(self):
        handler = _make_handler([_json_response(401, {})])
        t = _transport(handler, sleeper=_RecordingSleeper())
        try:
            with pytest.raises(AuthenticationError):
                t.get("/x")
        finally:
            t.close()

    def test_403_raises_authorization_error(self):
        handler = _make_handler([_json_response(403, {})])
        t = _transport(handler, sleeper=_RecordingSleeper())
        try:
            with pytest.raises(AuthorizationError):
                t.get("/x")
        finally:
            t.close()


class TestRetryExceptions:
    def test_non_retryable_exception_propagates(self):
        handler = _make_handler([ValueError("boom")])
        t = _transport(handler, sleeper=_RecordingSleeper())
        try:
            with pytest.raises(ValueError, match="boom"):
                t.get("/x")
        finally:
            t.close()

    def test_timeout_retried_then_succeeds(self):
        handler = _make_handler(
            [httpx.ReadTimeout("first"), _json_response(200, {"ok": True})]
        )
        sleeper = _RecordingSleeper()
        t = _transport(handler, sleeper=sleeper)
        try:
            r = t.get("/x")
        finally:
            t.close()
        assert r.status_code == 200
        assert sleeper.calls == [1.0]

    def test_connection_error_retried(self):
        handler = _make_handler(
            [httpx.ConnectError("dns"), _json_response(200, {"ok": True})]
        )
        sleeper = _RecordingSleeper()
        t = _transport(handler, sleeper=sleeper)
        try:
            r = t.get("/x")
        finally:
            t.close()
        assert r.status_code == 200
        assert sleeper.calls == [1.0]


class TestRetryAfterHeader:
    def test_honours_retry_after_header(self):
        handler = _make_handler(
            [
                _json_response(429, {"err": "rate"}, headers={"Retry-After": "2"}),
                _json_response(200, {"ok": True}),
            ]
        )
        sleeper = _RecordingSleeper()
        t = _transport(handler, sleeper=sleeper)
        try:
            r = t.get("/x")
        finally:
            t.close()
        assert r.status_code == 200
        # Used Retry-After (2.0), not the exponential 1.0.
        assert sleeper.calls == [2.0]

    def test_retry_after_capped_by_max_delay(self):
        handler = _make_handler(
            [
                _json_response(503, {"err": "busy"}, headers={"Retry-After": "120"}),
                _json_response(200, {"ok": True}),
            ]
        )
        sleeper = _RecordingSleeper()
        t = _transport(
            handler,
            retry=RetryPolicy(max_delay=5.0),
            sleeper=sleeper,
        )
        try:
            r = t.get("/x")
        finally:
            t.close()
        assert r.status_code == 200
        # 120 capped to max_delay=5.
        assert sleeper.calls == [5.0]

    def test_exponential_used_when_no_retry_after(self):
        handler = _make_handler(
            [_json_response(500, {"err": 1}), _json_response(200, {"ok": True})]
        )
        sleeper = _RecordingSleeper()
        t = _transport(handler, sleeper=sleeper)
        try:
            r = t.get("/x")
        finally:
            t.close()
        # No Retry-After header -> exponential: 1.0.
        assert sleeper.calls == [1.0]


class TestRetrySurface:
    def test_get_and_post_share_request(self):
        handler = _make_handler(
            [
                _json_response(200, {"ok": 1}),
                _json_response(200, {"ok": 2}),
            ]
        )
        t = _transport(handler, sleeper=_RecordingSleeper())
        try:
            r1 = t.get("/a")
            r2 = t.post("/b")
        finally:
            t.close()
        assert r1.status_code == 200
        assert r2.status_code == 200

    def test_passes_params_and_headers_through(self):
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["params"] = dict(request.url.params)
            captured["headers"] = dict(request.headers)
            return _json_response(200, {})

        t = _transport(handler, sleeper=_RecordingSleeper())
        try:
            t.get("/x", params={"a": "1", "b": "2"}, headers={"X-Test": "v"})
        finally:
            t.close()
        assert captured["params"]["a"] == "1"
        assert captured["params"]["b"] == "2"
        assert captured["headers"]["x-test"] == "v"

    def test_retry_policy_property_exposes_policy(self):
        t = _transport(
            _make_handler([_json_response(200, {})]),
            retry=RetryPolicy(attempts=7),
        )
        try:
            assert t.retry_policy.attempts == 7
        finally:
            t.close()

    def test_default_retry_policy_is_adr0008(self):
        t = _transport(_make_handler([_json_response(200, {})]))
        try:
            assert t.retry_policy.attempts == 3
            assert t.retry_policy.initial_delay == 1.0
            assert t.retry_policy.multiplier == 2.0
            assert t.retry_policy.max_delay == 60.0
        finally:
            t.close()

    def test_sleeper_not_called_when_no_retry(self):
        handler = _make_handler([_json_response(200, {})])
        sleeper = _RecordingSleeper()
        t = _transport(handler, sleeper=sleeper)
        try:
            t.get("/x")
        finally:
            t.close()
        assert sleeper.calls == []


class TestRetryEdgeCases:
    def test_attempts_one_no_retry_response(self):
        # With attempts=1, a retryable response (500) must NOT be
        # retried; it is returned to the caller as-is. RetryError
        # only fires when at least one retry actually happened.
        handler = _make_handler([_json_response(500, {"err": 1})])
        t = _transport(
            handler,
            retry=RetryPolicy(attempts=1),
            sleeper=_RecordingSleeper(),
        )
        try:
            r = t.get("/x")
            assert r.status_code == 500
        finally:
            t.close()

    def test_attempts_one_no_retry_exception(self):
        # With attempts=1, a retryable exception (timeout) must
        # NOT be wrapped in RetryError; it propagates unchanged.
        handler = _make_handler([httpx.ReadTimeout("boom")])
        t = _transport(
            handler,
            retry=RetryPolicy(attempts=1),
            sleeper=_RecordingSleeper(),
        )
        try:
            with pytest.raises(Exception) as excinfo:
                t.get("/x")
            # Translation happened: SDK TimeoutError, not RetryError.
            from un_comtrade.exceptions import (
                TimeoutError as SdkTimeoutError,
                RetryError as SdkRetryError,
            )
            assert isinstance(excinfo.value, SdkTimeoutError)
            assert not isinstance(excinfo.value, SdkRetryError)
        finally:
            t.close()

    def test_multiple_retryable_statuses_in_sequence(self):
        # 429 -> 503 -> 200 (3 attempts total = default budget).
        handler = _make_handler(
            [
                _json_response(429, {}),
                _json_response(503, {}),
                _json_response(200, {"ok": True}),
            ]
        )
        sleeper = _RecordingSleeper()
        t = _transport(handler, sleeper=sleeper)
        try:
            r = t.get("/x")
        finally:
            t.close()
        assert r.status_code == 200
        # 1.0 then 2.0 (exponential; no Retry-After set).
        assert sleeper.calls == [1.0, 2.0]

    def test_max_total_wait_is_within_budget(self):
        # With default policy the total wait time is
        # 1 + 2 = 3 seconds (for 3 attempts that all fail and retry).
        # This documents the ≈7s upper bound from ADR-0008.
        handler = _make_handler(
            [
                _json_response(500, {}),
                _json_response(500, {}),
                _json_response(500, {}),
            ]
        )
        sleeper = _RecordingSleeper()
        t = _transport(handler, sleeper=sleeper)
        try:
            with pytest.raises(RetryError):
                t.get("/x")
            # 1.0 + 2.0 = 3.0 total wait; well under the ≈7s ceiling.
            assert sum(sleeper.calls) <= 7.0
            assert sleeper.calls == [1.0, 2.0]
        finally:
            t.close()