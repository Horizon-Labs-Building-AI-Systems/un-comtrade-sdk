"""SDK exception hierarchy.

This module is the single source of truth for every exception
type raised by the SDK, per Architecture Freeze Question / ADR-0012
(SDK Error Hierarchy: 13 Exception Types).

The hierarchy:

    ComtradeError                          ← base
    ├── ConfigurationError                  ← invalid config
    ├── AuthenticationError                 ← missing / malformed API key
    │   └── AuthorizationError              ← key rejected (401/403)
    ├── ValidationError                     ← bad parameter / payload
    ├── NetworkError                        ← DNS, TLS, connection
    │   ├── TimeoutError                    ← request timed out
    │   ├── RetryError                      ← retry budget exhausted
    │   └── RateLimitError                  ← upstream 429
    ├── SerializationError                  ← JSON / Decimal / Parquet
    ├── APIError                            ← upstream 4xx
    │   └── ServerError                      ← upstream 5xx
    └── UnknownError                        ← unclassified

All exceptions:
- inherit from `ComtradeError`,
- have a docstring,
- accept an optional `cause` (preserved via `__cause__`),
- stringify their message via `str()`.
"""

from __future__ import annotations

from typing import Any


class ComtradeError(Exception):
    """Base class for every SDK-raised exception.

    Catching this class catches every exception the SDK can raise.
    Consumers SHOULD prefer catching more specific subclasses.
    """


class ConfigurationError(ComtradeError, ValueError):
    """Raised when the configuration is invalid at construction time.

    Per `010_INFRASTRUCTURE_SPECIFICATION.md` §3.5, the configuration
    is validated at construction. An invalid configuration raises
    `ConfigurationError` before the first call is issued.
    """


class AuthenticationError(ComtradeError):
    """Raised when authentication is missing or malformed.

    Examples: no API key configured; key not a string; key on a
    non-authenticated endpoint.
    """


class AuthorizationError(AuthenticationError):
    """Raised when the upstream rejects the supplied credentials.

    Typical upstream statuses: HTTP 401 (Unauthenticated) or
    HTTP 403 (Forbidden).
    """


class ValidationError(ComtradeError, ValueError):
    """Raised when a request parameter or payload fails validation.

    Examples: invalid country code; invalid period; invalid flow
    code; invalid reporter / partner combination.
    """


class NetworkError(ComtradeError):
    """Raised when a network-level failure occurs.

    Examples: DNS resolution failure; TLS handshake failure;
    connection refused; connection reset; read error.
    """


class TimeoutError(NetworkError):
    """Raised when a request exceeds its configured timeout.

    The underlying `httpx.TimeoutException` is preserved as `__cause__`
    for diagnostics.
    """


class RetryError(NetworkError):
    """Raised when the retry budget is exhausted on a retryable failure.

    Per ADR-0008, the default retry budget is 3 attempts.
    """


class RateLimitError(NetworkError):
    """Raised when the upstream signals HTTP 429 (rate limit exceeded).

    Per ADR-0035 the upstream returns `Retry-After: 1` on 429; the
    SDK honours this header before raising `RateLimitError`.
    """


class SerializationError(ComtradeError):
    """Raised when serialisation or deserialisation fails.

    Examples: invalid JSON in the upstream response; cannot decode
    a numeric field into `Decimal`; cannot encode a record to Parquet.
    """


class APIError(ComtradeError):
    """Raised for upstream 4xx responses that are not auth or rate-limit.

    Examples: HTTP 400 (bad request); HTTP 404 (not found);
    HTTP 422 (unprocessable entity).
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: str | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
        if cause is not None:
            self.__cause__ = cause


class ServerError(APIError):
    """Raised for upstream 5xx responses.

    Typical upstream statuses: HTTP 500 (Internal Server Error),
    HTTP 502 (Bad Gateway), HTTP 503 (Service Unavailable),
    HTTP 504 (Gateway Timeout).
    """


class UnknownError(ComtradeError):
    """Raised for unclassified failures.

    Used as the catch-all when no other exception category applies.
    """


__all__ = [
    "APIError",
    "AuthenticationError",
    "AuthorizationError",
    "ComtradeError",
    "ConfigurationError",
    "NetworkError",
    "RateLimitError",
    "RetryError",
    "SerializationError",
    "ServerError",
    "TimeoutError",
    "UnknownError",
    "ValidationError",
]