"""Configuration loading for the CLI.

This module wraps the public
:func:`un_comtrade.config.load_configuration` and
adds CLI-specific overrides:

- An explicit ``--api-key`` flag (overrides the
  ``UN_COMTRADE_KEY`` env var).
- An explicit ``--log-level`` flag (overrides the
  ``UN_COMTRADE_LOG_LEVEL`` env var).
- An explicit ``--output-format`` flag (does not
  flow into the SDK Configuration; it's a CLI-
  only setting).

The CLI never reaches into
:mod:`un_comtrade.config` private internals; it
uses the public ``load_configuration`` factory
plus its own override layer.
"""

from __future__ import annotations

from typing import Any
from un_comtrade.config import (
    Configuration,
    load_configuration,
)
from un_comtrade.logging import LOG_LEVELS
from un_comtrade.cli.utils.exceptions import (
    CLIConfigurationError,
)


#: Output formats supported by the CLI. The
#: formatters live in
#: :mod:`un_comtrade.cli.formatting` and are
#: registered in that package's
#: ``__init__.py``. ``json`` is the default;
#: ``table`` / ``csv`` / ``markdown`` / ``text``
#: are alternative renderings chosen via
#: ``--output-format``.
OUTPUT_FORMATS: tuple[str, ...] = (
    "json",
    "table",
    "csv",
    "markdown",
    "text",
)


def _validate_log_level(level: str) -> str:
    """Normalise a log-level string. Raises
    :class:`CLIConfigurationError` on an
    unknown level.
    """
    normalised = level.strip().upper()
    if normalised not in LOG_LEVELS:
        raise CLIConfigurationError(
            f"unknown log level {level!r}; "
            f"expected one of {sorted(LOG_LEVELS)}"
        )
    return normalised


def _validate_output_format(fmt: str) -> str:
    """Normalise an output-format string. Raises
    :class:`CLIConfigurationError` on an
    unknown format.
    """
    normalised = fmt.strip().lower()
    if normalised not in OUTPUT_FORMATS:
        raise CLIConfigurationError(
            f"unknown output format {fmt!r}; "
            f"expected one of {OUTPUT_FORMATS}"
        )
    return normalised


def load_cli_configuration(
    *,
    api_key: str | None = None,
    log_level: str | None = None,
    base_url: str | None = None,
    timeout: float | None = None,
) -> Configuration:
    """Load the SDK :class:`Configuration` from
    the environment, applying CLI-side overrides
    on top.

    Parameters
    ----------
    api_key
        Override for the subscription key. When
        supplied, this takes precedence over the
        ``UN_COMTRADE_KEY`` env var.
    log_level
        Override for the log level. When supplied,
        this takes precedence over the
        ``UN_COMTRADE_LOG_LEVEL`` env var.
    base_url
        Override for the upstream base URL.
    timeout
        Override for the per-request timeout
        (seconds).

    Returns
    -------
    Configuration
        A frozen :class:`Configuration` with all
        overrides applied.

    Raises
    ------
    CLIConfigurationError
        When an override value is invalid (unknown
        log level, malformed URL, etc.).
    """
    cfg = load_configuration()

    # Apply overrides by reconstructing the
    # Configuration via `dataclasses.replace`. The
    # Configuration is frozen, so we cannot
    # mutate it in place.
    from dataclasses import replace
    overrides: dict[str, Any] = {}
    if api_key is not None:
        overrides["api_key"] = api_key
    if log_level is not None:
        overrides["log_level"] = _validate_log_level(log_level)
    if base_url is not None:
        overrides["base_url"] = base_url
    if timeout is not None:
        if timeout <= 0:
            raise CLIConfigurationError(
                f"timeout must be positive; got {timeout}"
            )
        overrides["timeout_seconds"] = timeout
    if overrides:
        cfg = replace(cfg, **overrides)
    return cfg


__all__ = [
    "OUTPUT_FORMATS",
    "load_cli_configuration",
]