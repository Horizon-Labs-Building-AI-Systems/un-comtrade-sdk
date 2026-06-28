"""HTTP transport layer for the UN Comtrade Python SDK.

This module is the single component permitted to communicate with
the UN Comtrade HTTP API. Per `003_ARCHITECTURE.md`, the transport
layer is the only layer that may issue HTTP requests.

This module implements:

- a single `httpx.Client` per transport instance,
- base URL + path resolution,
- default header injection (`User-Agent`, `Accept`,
  `Ocp-Apim-Subscription-Key` when an API key is configured),
- typed `HttpResponse` wrapper,
- 401 -> `AuthenticationError` and 403 -> `AuthorizationError`
  translation (per ADR-0012 and ADR-0034),
- timeout handling (per ADR-0023):
  - three named categories — default (30 s), metadata (15 s),
    large_download (300 s) — all configurable,
  - per-request override via the `timeout` kwarg,
  - per-request category selection via the `kind` kwarg,
  - `httpx.TimeoutException` -> SDK `TimeoutError` translation
    (the original exception is preserved as `__cause__`),
- retry with exponential backoff (per ADR-0008 and ADR-0022),
  - 3 attempts (initial + 2 retries),
  - 1 s initial delay, 2x multiplier, 60 s cap,
  - retries on timeout / 429 / 500 / 502 / 503 / 504,
  - never retries validation errors (4xx other than 429) or
    auth failures (401 / 403),
  - honours upstream `Retry-After` header (numeric form),
  - raises `RetryError` when the budget is exhausted.

Out of scope for this module:

- caching, logging, circuit-breaking (separate tasks).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

import httpx

from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    RetryError,
    TimeoutError as SdkTimeoutError,
)
from .logging import (
    AUTH_HEADER,
    generate_request_id,
    get_logger,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Default headers attached to every request.
DEFAULT_HEADERS: dict[str, str] = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate",
}

#: HTTP header name carrying the UN Comtrade subscription key.
#: The upstream is fronted by Azure API Management, which uses
#: this header convention. Re-exported for callers that
#: imported it from `transport` directly.
AUTH_HEADER: str = "Ocp-Apim-Subscription-Key"

#: HTTP status codes that signal an authentication failure.
AUTH_FAILURE_STATUSES: frozenset[int] = frozenset({401, 403})

#: HTTP status codes that the SDK retries on.
#: Per ADR-0008 and ADR-0022: timeout, 429, 500, 502, 503, 504.
DEFAULT_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})

#: Exception types that the SDK treats as transient and retries.
#: Maps onto the timeout + connection-drop categories observed by
#: ADR-0008 ("retries on timeout") and ADR-0022 ("Retryable Error
#: Set"). Includes the SDK's `TimeoutError` (a `NetworkError`)
#: because the transport translates `httpx.TimeoutException` into
#: the SDK exception before the retry loop sees it.
DEFAULT_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    SdkTimeoutError,
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
    httpx.RemoteProtocolError,
    ConnectionError,
)


# ---------------------------------------------------------------------------
# Response wrapper
# ---------------------------------------------------------------------------


#: Documented timeout categories (per ADR-0023). Used by
#: `TimeoutConfig.for_category` and accepted by the `kind`
#: parameter on `HttpTransport.request()`.
TIMEOUT_CATEGORIES: frozenset[str] = frozenset(
    {"default", "metadata", "large_download"}
)


@dataclass(frozen=True)
class TimeoutConfig:
    """Per-request timeout categories per ADR-0023.

    Defaults:

    - ``default`` — 30 s for ordinary data calls.
    - ``metadata`` — 15 s for the reference catalogues.
    - ``large_download`` — 300 s for bulk exports.

    All three values are configurable. The categories are
    accessed by name via `for_category()` so call sites
    need not hard-code the durations.
    """

    default: float = 30.0
    metadata: float = 15.0
    large_download: float = 300.0

    def __post_init__(self) -> None:
        for name in ("default", "metadata", "large_download"):
            value = getattr(self, name)
            if value <= 0:
                raise ValueError(
                    f"{name} timeout must be > 0 seconds; got {value}"
                )

    def for_category(self, category: str) -> float:
        """Return the timeout for a named category.

        Unknown categories raise `ValueError`.
        """
        if category not in TIMEOUT_CATEGORIES:
            raise ValueError(
                f"Unknown timeout category {category!r}; "
                f"expected one of {sorted(TIMEOUT_CATEGORIES)}"
            )
        return getattr(self, category)


@dataclass(frozen=True)
class HttpResponse:
    """Typed HTTP response wrapper.

    The transport returns this instead of leaking `httpx.Response` to
    higher layers. Higher layers depend on this stable shape.
    """

    status_code: int
    body: bytes
    headers: Mapping[str, str]
    elapsed_seconds: float
    url: str

    @property
    def is_success(self) -> bool:
        """True for HTTP 2xx."""
        return 200 <= self.status_code < 300

    @property
    def text(self) -> str:
        """Response body decoded as UTF-8 (replacement on errors)."""
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        """Parse the response body as JSON."""
        return json.loads(self.body.decode("utf-8", errors="replace"))


# ---------------------------------------------------------------------------
# Retry policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetryPolicy:
    """Configuration for the transport's retry behaviour.

    Defaults honour ADR-0008 (3 attempts, 1 s initial, 2x
    multiplier, 60 s cap) and ADR-0022 (retryable error set).
    """

    attempts: int = 3
    initial_delay: float = 1.0
    multiplier: float = 2.0
    max_delay: float = 60.0
    retryable_status_codes: frozenset[int] = field(
        default_factory=lambda: DEFAULT_RETRYABLE_STATUS_CODES
    )
    retryable_exceptions: tuple[type[BaseException], ...] = field(
        default_factory=lambda: DEFAULT_RETRYABLE_EXCEPTIONS
    )

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ValueError(
                f"attempts must be >= 1; got {self.attempts}"
            )
        if self.initial_delay < 0:
            raise ValueError(
                f"initial_delay must be >= 0; got {self.initial_delay}"
            )
        if self.multiplier < 1.0:
            raise ValueError(
                f"multiplier must be >= 1.0; got {self.multiplier}"
            )
        if self.max_delay < self.initial_delay:
            raise ValueError(
                f"max_delay ({self.max_delay}) must be "
                f">= initial_delay ({self.initial_delay})"
            )

    # ----- Scheduling ------------------------------------------------------

    def delay_for_attempt(self, attempt: int) -> float:
        """Return the sleep duration before the given attempt number.

        `attempt` is 1-indexed: 1 is the first try (no sleep).
        Subsequent attempts use exponential backoff:
        ``initial_delay * multiplier ** (attempt - 2)``,
        capped at ``max_delay``.
        """
        if attempt <= 1:
            return 0.0
        index = attempt - 2
        base = self.initial_delay * (self.multiplier ** index)
        return min(base, self.max_delay)

    def parse_retry_after(self, response: HttpResponse) -> float | None:
        """Extract a `Retry-After` delay (seconds) from a response.

        Only the integer / float seconds form is supported.
        HTTP-date form is ignored (returns ``None``) and the
        caller falls back to the exponential schedule.
        """
        for key in ("retry-after", "Retry-After"):
            value = response.headers.get(key)
            if value is None:
                continue
            try:
                seconds = float(value)
            except ValueError:
                # HTTP-date form is not supported in MVP.
                return None
            if seconds < 0:
                return 0.0
            return min(seconds, self.max_delay)
        return None

    # ----- Decision --------------------------------------------------------

    def is_retryable_response(self, response: HttpResponse) -> bool:
        """True if a response should trigger another attempt."""
        return response.status_code in self.retryable_status_codes

    def is_retryable_exception(self, exc: BaseException) -> bool:
        """True if an exception should trigger another attempt."""
        return isinstance(exc, self.retryable_exceptions)


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


class HttpTransport:
    """Reusable HTTP transport layer wrapping `httpx.Client`.

    The transport is the only place in the SDK that issues HTTP
    requests. It also handles:

    - API key injection (`Ocp-Apim-Subscription-Key`),
    - 401 / 403 -> `AuthenticationError` / `AuthorizationError`,
    - retry with exponential backoff (3 attempts by default).

    Higher layers (metadata, trade, validation) invoke
    `request()` / `get()` / `post()` on the transport.
    """

    def __init__(
        self,
        *,
        base_url: str,
        user_agent: str,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        default_headers: Mapping[str, str] | None = None,
        follow_redirects: bool = True,
        retry: RetryPolicy | None = None,
        timeout: TimeoutConfig | None = None,
        logger: logging.Logger | None = None,
        security_logger: logging.Logger | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not base_url or not base_url.strip():
            raise ValueError("base_url must be a non-empty string")
        if not (base_url.startswith("http://") or base_url.startswith("https://")):
            raise ValueError(
                f"base_url must start with http:// or https://; got {base_url!r}"
            )
        if not user_agent or not user_agent.strip():
            raise ValueError("user_agent must be a non-empty string")

        # Validate the API key (per ADR-0034 + config.py rules):
        # if a key is provided, it must be a non-empty string.
        if api_key is not None:
            if not isinstance(api_key, str):
                raise TypeError(
                    f"api_key must be a str or None; got {type(api_key).__name__}"
                )
            if not api_key.strip():
                raise ValueError(
                    "api_key, if provided, must be a non-empty string"
                )

        self._base_url = base_url.rstrip("/")
        self._user_agent = user_agent
        self._api_key: str | None = api_key
        self._retry_policy: RetryPolicy = retry if retry is not None else RetryPolicy()
        self._timeout_config: TimeoutConfig = (
            timeout if timeout is not None else TimeoutConfig()
        )
        self._sleeper: Callable[[float], None] = sleeper
        # Loggers per ADR-0025 / spec §6: lifecycle / network for
        # the main flow; security for auth events. Consumers can
        # pass their own loggers to integrate with the host app.
        self._logger: logging.Logger = (
            logger if logger is not None else get_logger("lifecycle")
        )
        self._security_logger: logging.Logger = (
            security_logger
            if security_logger is not None
            else get_logger("security")
        )
        self._network_logger: logging.Logger = get_logger("network")
        self._retry_logger: logging.Logger = get_logger("retry")

        # Default headers attached to every outgoing request.
        # Stored on the instance so they are applied to every request,
        # including those issued via a caller-supplied client (tests).
        self._default_headers: dict[str, str] = dict(DEFAULT_HEADERS)
        self._default_headers["User-Agent"] = user_agent
        if self._api_key is not None:
            self._default_headers[AUTH_HEADER] = self._api_key
        if default_headers:
            self._default_headers.update(default_headers)

        if client is None:
            # httpx.Client is sync per ADR-0018 (async deferred to Phase 2).
            self._client = httpx.Client(
                headers=dict(self._default_headers),
                follow_redirects=follow_redirects,
            )
            self._owns_client = True
        else:
            # Caller-supplied client (used by tests via MockTransport).
            self._client = client
            self._owns_client = False

    # ----- Properties -------------------------------------------------------

    @property
    def base_url(self) -> str:
        """The configured base URL (without trailing slash)."""
        return self._base_url

    @property
    def user_agent(self) -> str:
        """The configured User-Agent string."""
        return self._user_agent

    @property
    def api_key(self) -> str | None:
        """The configured API key, or `None` if no key was set.

        Per ADR-0034 the key is never written to disk; it lives
        only in memory on this transport instance.
        """
        return self._api_key

    @property
    def retry_policy(self) -> RetryPolicy:
        """The active retry policy."""
        return self._retry_policy

    @property
    def timeout_config(self) -> TimeoutConfig:
        """The active timeout configuration."""
        return self._timeout_config

    @property
    def client(self) -> httpx.Client:
        """The underlying `httpx.Client` (for advanced use)."""
        return self._client

    # ----- URL resolution ---------------------------------------------------

    def _resolve_url(self, path: str) -> str:
        """Resolve a path against the base URL.

        If `path` is already an absolute URL (starts with ``http://`` or
        ``https://``), it is returned unchanged. Otherwise it is
        joined onto the base URL.
        """
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path or path == "/":
            return self._base_url
        if path.startswith("/"):
            return f"{self._base_url}{path}"
        return f"{self._base_url}/{path}"

    # ----- Request building -------------------------------------------------

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | httpx.Timeout | None = None,
        kind: str = "default",
    ) -> HttpResponse:
        """Issue an HTTP request with retry and timeout semantics.

        Returns the final `HttpResponse`. Raises `RetryError`
        when the retry budget is exhausted on retryable failures.
        Raises `AuthenticationError` / `AuthorizationError` on
        upstream 401 / 403 (per ADR-0012 and ADR-0034). Raises
        `un_comtrade.TimeoutError` (a `NetworkError`) when a
        single attempt exceeds the effective timeout — the
        original `httpx.TimeoutException` is preserved as
        `__cause__` and the retry loop will still retry it.

        Parameters:

        - `timeout`: explicit timeout override (seconds). When
          `None`, the value is taken from `TimeoutConfig.for_category(kind)`.
        - `kind`: timeout category — `"default"`, `"metadata"`,
          or `"large_download"`. Ignored when `timeout` is given.
        """
        if timeout is None:
            timeout = self._timeout_config.for_category(kind)
        request_id = generate_request_id()
        # Lifecycle: request start at DEBUG (suppressed at default WARNING).
        self._logger.debug(
            "request method=%s path=%s request_id=%s",
            method, path, request_id,
        )
        try:
            response = self._request_with_retry(
                method,
                path,
                params=params,
                headers=headers,
                timeout=timeout,
                request_id=request_id,
            )
        except BaseException:
            # _request_with_retry already logged the failure cause;
            # we add a lifecycle marker so consumers can correlate
            # call boundaries with retries / exceptions.
            self._logger.debug(
                "request failed method=%s path=%s request_id=%s",
                method, path, request_id,
            )
            raise
        # Lifecycle: request end at DEBUG.
        self._logger.debug(
            "response status=%d method=%s path=%s request_id=%s elapsed=%.3fs",
            response.status_code, method, path, request_id, response.elapsed_seconds,
        )
        return response

    def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None,
        headers: Mapping[str, str] | None,
        timeout: float | httpx.Timeout | None,
        request_id: str,
    ) -> HttpResponse:
        attempts = self._retry_policy.attempts
        last_exc: BaseException | None = None
        last_response: HttpResponse | None = None

        for attempt in range(1, attempts + 1):
            # Sleep before attempt > 1.
            if attempt > 1:
                delay = self._next_delay(attempt, last_response)
                if delay > 0:
                    self._sleeper(delay)
                self._retry_logger.warning(
                    "retry attempt=%d method=%s path=%s request_id=%s",
                    attempt, method, path, request_id,
                )

            try:
                response = self._single_request(
                    method,
                    path,
                    params=params,
                    headers=headers,
                    timeout=timeout,
                    request_id=request_id,
                )
            except BaseException as exc:  # noqa: BLE001
                # Every network-level failure is logged at WARNING so
                # consumers see it at the default WARNING level,
                # regardless of whether the exception is retryable.
                self._network_logger.warning(
                    "network error attempt=%d method=%s path=%s "
                    "request_id=%s exc=%r",
                    attempt, method, path, request_id, exc,
                )
                last_exc = exc
                last_response = None
                if not self._retry_policy.is_retryable_exception(exc):
                    raise
                if attempt >= attempts:
                    # No retries left. When the caller configured
                    # `attempts=1` (no retries), propagate the original
                    # exception unchanged. Otherwise wrap in RetryError.
                    if attempts == 1:
                        raise
                    raise RetryError(
                        f"Retry budget exhausted after {attempts} attempts; "
                        f"last error: {exc!r}"
                    ) from exc
                continue

            last_response = response
            last_exc = None

            if not self._retry_policy.is_retryable_response(response):
                return response

            # Retryable response.
            if attempt >= attempts:
                if attempts == 1:
                    # Single attempt, retryable status -> return as-is.
                    return response
                raise RetryError(
                    f"Retry budget exhausted after {attempts} attempts; "
                    f"last status: {response.status_code}"
                )

        # Defensive: the loop always returns or raises.
        raise RetryError("Retry loop terminated unexpectedly")  # pragma: no cover

    def _next_delay(
        self, attempt: int, last_response: HttpResponse | None
    ) -> float:
        """Compute the sleep duration before the upcoming attempt."""
        if last_response is not None:
            retry_after = self._retry_policy.parse_retry_after(last_response)
            if retry_after is not None:
                return retry_after
        return self._retry_policy.delay_for_attempt(attempt)

    def _single_request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None,
        headers: Mapping[str, str] | None,
        timeout: float | httpx.Timeout | None,
        request_id: str,
    ) -> HttpResponse:
        """Issue a single HTTP request without retry.

        Returns an `HttpResponse`. May raise:
        - `un_comtrade.TimeoutError` (a `NetworkError`) when the
          request exceeds the effective timeout. The original
          `httpx.TimeoutException` is preserved as `__cause__`.
        - `AuthenticationError` / `AuthorizationError` on 401/403,
        - other exceptions unchanged.
        """
        url = self._resolve_url(path)
        # Always start from the configured defaults so they apply
        # whether the underlying client was created by this transport
        # or supplied by a caller (e.g. tests).
        merged_headers: dict[str, str] = dict(self._default_headers)
        if headers:
            merged_headers.update(headers)

        t0 = time.monotonic()
        try:
            response = self._client.request(
                method,
                url,
                params=params,
                headers=merged_headers,
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            # Translation only — the network logger emits the WARNING
            # in _request_with_retry (it sees the translated exception
            # when retries are exhausted or when propagation happens).
            raise SdkTimeoutError(
                f"Request to {path!r} exceeded the "
                f"{timeout}s timeout: {exc!r}"
            ) from exc
        elapsed = time.monotonic() - t0

        # Auth translation per ADR-0034 / ADR-0012: surface 401 and
        # 403 as SDK exceptions instead of leaking raw status codes.
        if response.status_code in AUTH_FAILURE_STATUSES:
            self._security_logger.error(
                "auth failure status=%d method=%s path=%s request_id=%s",
                response.status_code, method, path, request_id,
            )
            raise self._auth_error_for(response)

        return HttpResponse(
            status_code=response.status_code,
            body=response.content,
            headers=dict(response.headers),
            elapsed_seconds=elapsed,
            url=str(response.url),
        )

    def _auth_error_for(self, response: httpx.Response) -> Exception:
        """Build the SDK auth exception matching the upstream status."""
        url = str(response.url)
        if response.status_code == 401:
            if self._api_key is None:
                return AuthenticationError(
                    f"401 Unauthorized from {url}: no API key configured. "
                    f"Set the UN_COMTRADE_KEY environment variable or pass "
                    f"api_key to the SDK constructor."
                )
            return AuthenticationError(
                f"401 Unauthorized from {url}: the configured API key "
                f"was rejected by the upstream. Verify your "
                f"UN_COMTRADE_KEY / subscription key."
            )
        if response.status_code == 403:
            # Per ADR-0012 AuthorizationError is a subclass of
            # AuthenticationError; both are caught by except
            # AuthenticationError clauses.
            return AuthorizationError(
                f"403 Forbidden from {url}: the API key is valid but "
                f"does not grant access to this resource."
            )
        # Defensive; AUTH_FAILURE_STATUSES only contains 401/403 today.
        return AuthenticationError(  # pragma: no cover
            f"{response.status_code} auth failure from {url}"
        )

    def get(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | httpx.Timeout | None = None,
        kind: str = "default",
    ) -> HttpResponse:
        """Convenience wrapper for HTTP GET."""
        return self.request(
            "GET",
            path,
            params=params,
            headers=headers,
            timeout=timeout,
            kind=kind,
        )

    def post(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | httpx.Timeout | None = None,
        kind: str = "default",
    ) -> HttpResponse:
        """Convenience wrapper for HTTP POST."""
        return self.request(
            "POST",
            path,
            params=params,
            headers=headers,
            timeout=timeout,
            kind=kind,
        )

    # ----- Lifecycle -------------------------------------------------------

    def close(self) -> None:
        """Close the underlying `httpx.Client` if owned by this transport."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "HttpTransport":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()


__all__ = [
    "AUTH_FAILURE_STATUSES",
    "AUTH_HEADER",
    "DEFAULT_HEADERS",
    "DEFAULT_RETRYABLE_EXCEPTIONS",
    "DEFAULT_RETRYABLE_STATUS_CODES",
    "HttpResponse",
    "HttpTransport",
    "RetryPolicy",
    "TIMEOUT_CATEGORIES",
    "TimeoutConfig",
]