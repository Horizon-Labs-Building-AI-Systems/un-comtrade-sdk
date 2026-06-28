"""Logging subsystem for the UN Comtrade Python SDK.

This module is the single point of contact between the SDK
and the Python standard library `logging` framework. It
provides:

- a logger factory (`get_logger`) returning namespaced
  `logging.Logger` instances;
- a request-id generator for correlation across retry
  attempts and downstream logs;
- a `LogContext` dataclass describing the structured
  record shape expected by the infrastructure
  specification;
- a `RedactingFilter` that scrubs known secrets from log
  records as a defence-in-depth measure.

Per ADR-0025 and `010_INFRASTRUCTURE_SPEC.md` §6:

- The default level is `WARNING`.
- HTTP request details are logged only at `DEBUG`.
- API keys are always redacted from log records.
- Sensitive material (subscription key, full URL with
  key in query, env vars, paths, args) is never logged.
- A single request_id correlates all records emitted
  during one top-level call.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


#: Root namespace for all SDK loggers. Consumers may
#: configure logging under this prefix to control SDK
#: verbosity (e.g. ``logging.getLogger("un_comtrade").setLevel(logging.DEBUG)``).
LOGGER_NAMESPACE: str = "un_comtrade"

#: Default log level per ADR-0025 (Q27): WARNING.
#:
#: F-003 (2026-06-28) closed the audit-flagged
#: collision with ``un_comtrade.config.DEFAULT_LOG_LEVEL``
#: by exposing the logging-side integer under the
#: unique name ``LOGGING_DEFAULT_LEVEL``. The
#: deprecated alias that briefly bridged the
#: v1.0.0 → v1.0.1 transition has been removed;
#: callers must use ``LOGGING_DEFAULT_LEVEL``.
LOGGING_DEFAULT_LEVEL: int = logging.WARNING

#: HTTP header that carries the subscription key. The
#: redaction filter scrubs this header's value wherever
#: it appears in a log message.
AUTH_HEADER: str = "Ocp-Apim-Subscription-Key"

#: Query parameter that may also carry a key on the
#: legacy preview endpoint. Redacted from log records.
AUTH_QUERY_PARAM: str = "subscription-key"

#: Documented log categories per infrastructure spec §6.2.
LOG_CATEGORIES: frozenset[str] = frozenset(
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

#: Placeholder substituted in place of a redacted secret.
REDACTED: str = "[REDACTED]"


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------


def get_logger(category: str) -> logging.Logger:
    """Return the SDK logger for the given category.

    Logger names follow the convention
    ``un_comtrade.<category>`` so consumers can configure
    them via the standard ``logging`` API. Unknown
    categories raise ``ValueError``.
    """
    if category not in LOG_CATEGORIES:
        raise ValueError(
            f"Unknown log category {category!r}; "
            f"expected one of {sorted(LOG_CATEGORIES)}"
        )
    return logging.getLogger(f"{LOGGER_NAMESPACE}.{category}")


# ---------------------------------------------------------------------------
# Request correlation
# ---------------------------------------------------------------------------


def generate_request_id() -> str:
    """Return a fresh request correlation ID.

    The ID is a UUID4 hex string. The same ID is shared
    across every log record emitted during one top-level
    ``HttpTransport.request()`` call, including any
    retry attempts.
    """
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Structured context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LogContext:
    """Structured log record per spec §6.4.

    Fields mirror the documented shape:

    - `timestamp` (ISO-8601 UTC, computed at access time).
    - `level` (string, e.g. ``"DEBUG"``).
    - `category` (string from `LOG_CATEGORIES`).
    - `request_id` (correlation ID from `generate_request_id`).
    - `message` (human-readable summary).
    - `context` (operation-specific dict; MUST NOT contain
      secrets, full URLs with embedded keys, env vars, or
      consumer paths).
    """

    level: str
    category: str
    request_id: str
    message: str
    context: Mapping[str, Any] = field(default_factory=dict)

    @property
    def timestamp(self) -> str:
        """ISO-8601 UTC timestamp captured at access time."""
        return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------


class RedactingFilter(logging.Filter):
    """Logging filter that scrubs secrets from log records.

    Applied to SDK loggers so any log message or argument
    that contains one of the configured secrets is
    replaced with the ``REDACTED`` placeholder. This is a
    defence-in-depth measure; the SDK also avoids logging
    sensitive material at the source.
    """

    def __init__(self, secrets: tuple[str, ...] = ()) -> None:
        super().__init__()
        # Drop empty / None values to avoid spurious matches.
        self._secrets: tuple[str, ...] = tuple(
            s for s in secrets if isinstance(s, str) and s
        )

    @property
    def secrets(self) -> tuple[str, ...]:
        """Return the secrets currently registered for redaction."""
        return self._secrets

    def filter(self, record: logging.LogRecord) -> bool:
        """Return True (always pass) after scrubbing the message."""
        if not self._secrets:
            return True
        # `getMessage()` resolves the format string against args.
        msg = record.getMessage()
        for secret in self._secrets:
            if secret in msg:
                msg = msg.replace(secret, REDACTED)
        # Replace the record's message; drop args to avoid
        # double-formatting surprises if a consumer reads
        # `record.msg` directly.
        record.msg = msg
        record.args = ()
        return True


def install_redaction(
    logger: logging.Logger,
    secrets: tuple[str, ...],
) -> RedactingFilter:
    """Attach a `RedactingFilter` to `logger` for the given secrets.

    Returns the filter so callers can remove it later if needed.
    The filter is idempotent on the same secret set: removing
    and re-installing with the same set does not stack
    duplicates.
    """
    flt = RedactingFilter(secrets)
    logger.addFilter(flt)
    return flt


__all__ = [
    "AUTH_HEADER",
    "AUTH_QUERY_PARAM",
    "LOGGER_NAMESPACE",
    "LOG_CATEGORIES",
    "LOG_LEVELS",
    "LOGGING_DEFAULT_LEVEL",
    "LogContext",
    "REDACTED",
    "RedactingFilter",
    "generate_request_id",
    "get_logger",
    "install_redaction",
]

#: Convenient mapping for callers that prefer level names.
LOG_LEVELS: Mapping[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}