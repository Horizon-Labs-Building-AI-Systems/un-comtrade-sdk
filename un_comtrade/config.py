"""Configuration subsystem for the UN Comtrade Python SDK.

This module owns the configuration contract declared in
`007_SDK_SPECIFICATION.md` §8 and the configuration strategy in
`010_INFRASTRUCTURE_SPECIFICATION.md` §3.

The configuration is:
- a typed, immutable object (`@dataclass(frozen=True)`)
- loaded from one or more sources in priority order:
  1. explicit construction argument
  2. environment variable
  3. default value
- validated at construction; invalid values raise `ConfigurationError`
- never mutated after construction

No HTTP, transport, retry, timeout, logging, or business logic
lives in this module.
"""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Mapping

from un_comtrade.exceptions import ConfigurationError


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

#: Default base URL for the upstream API.
DEFAULT_BASE_URL = "https://comtradeapi.un.org"

#: Default User-Agent string.
DEFAULT_USER_AGENT = "un-comtrade-sdk/0.1.0"

#: Default request timeout in seconds. Per ADR-0023 (Q16).
DEFAULT_TIMEOUT_SECONDS = 30

#: Default metadata timeout in seconds. Per ADR-0023 (Q18).
DEFAULT_METADATA_TIMEOUT_SECONDS = 15

#: Default download timeout in seconds. Per ADR-0023 (Q17).
DEFAULT_DOWNLOAD_TIMEOUT_SECONDS = 300

#: Default retry attempts. Per ADR-0008 (revised from 5 to 3).
DEFAULT_MAX_RETRIES = 3

#: Default initial backoff in seconds. Per ADR-0008.
DEFAULT_INITIAL_BACKOFF_SECONDS = 1.0

#: Default backoff multiplier. Per ADR-0008.
DEFAULT_BACKOFF_MULTIPLIER = 2.0

#: Default backoff cap in seconds. Per ADR-0008.
DEFAULT_BACKOFF_CAP_SECONDS = 60.0

#: Default trade-response cache TTL. The SDK does not cache trade
#: responses (per ADR-0024), so this is effectively unused but
#: retained for future flexibility.
DEFAULT_TRADE_CACHE_TTL_SECONDS = 0

#: Default metadata cache TTL in seconds (30 days).
DEFAULT_METADATA_CACHE_TTL_SECONDS = 30 * 24 * 3600

#: Default log level. Per ADR-0025 (Q27).
DEFAULT_LOG_LEVEL = "WARNING"

#: Default log format.
DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

#: Allowed log levels (Python stdlib `logging` levels, lower-case).
ALLOWED_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})

# ---------------------------------------------------------------------------
# Environment variable names
# ---------------------------------------------------------------------------

ENV_API_KEY = "UN_COMTRADE_KEY"
ENV_BASE_URL = "UN_COMTRADE_BASE_URL"
ENV_USER_AGENT = "UN_COMTRADE_USER_AGENT"
ENV_TIMEOUT = "UN_COMTRADE_TIMEOUT"
ENV_METADATA_TIMEOUT = "UN_COMTRADE_METADATA_TIMEOUT"
ENV_DOWNLOAD_TIMEOUT = "UN_COMTRADE_DOWNLOAD_TIMEOUT"
ENV_MAX_RETRIES = "UN_COMTRADE_MAX_RETRIES"
ENV_INITIAL_BACKOFF = "UN_COMTRADE_INITIAL_BACKOFF"
ENV_BACKOFF_MULTIPLIER = "UN_COMTRADE_BACKOFF_MULTIPLIER"
ENV_BACKOFF_CAP = "UN_COMTRADE_BACKOFF_CAP"
ENV_CACHE_ENABLED = "UN_COMTRADE_CACHE_ENABLED"
ENV_CACHE_DIR = "UN_COMTRADE_CACHE_DIR"
ENV_LOG_LEVEL = "UN_COMTRADE_LOG_LEVEL"
ENV_PROXY = "UN_COMTRADE_PROXY"

#: Mapping from env var name to its default value when unset.
_ENV_DEFAULTS: Mapping[str, str | None] = {
    ENV_API_KEY: None,
    ENV_BASE_URL: DEFAULT_BASE_URL,
    ENV_USER_AGENT: DEFAULT_USER_AGENT,
    ENV_TIMEOUT: str(DEFAULT_TIMEOUT_SECONDS),
    ENV_METADATA_TIMEOUT: str(DEFAULT_METADATA_TIMEOUT_SECONDS),
    ENV_DOWNLOAD_TIMEOUT: str(DEFAULT_DOWNLOAD_TIMEOUT_SECONDS),
    ENV_MAX_RETRIES: str(DEFAULT_MAX_RETRIES),
    ENV_INITIAL_BACKOFF: str(DEFAULT_INITIAL_BACKOFF_SECONDS),
    ENV_BACKOFF_MULTIPLIER: str(DEFAULT_BACKOFF_MULTIPLIER),
    ENV_BACKOFF_CAP: str(DEFAULT_BACKOFF_CAP_SECONDS),
    ENV_CACHE_ENABLED: "true",
    ENV_CACHE_DIR: None,  # resolved via `_default_cache_directory()`
    ENV_LOG_LEVEL: DEFAULT_LOG_LEVEL,
    ENV_PROXY: None,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_cache_directory() -> Path:
    """Return the platform-default user cache directory.

    Per ADR-0024 (Q24), the cache lives in the user cache directory,
    never in the project repository. Resolution follows the platform
    convention:

    - Linux:   ``$XDG_CACHE_HOME/un_comtrade`` or
               ``~/.cache/un_comtrade``
    - macOS:   ``~/Library/Caches/un_comtrade``
    - Windows: ``%LOCALAPPDATA%\\un_comtrade\\Cache``

    The consumer MAY override via ``UN_COMTRADE_CACHE_DIR`` or by
    passing ``cache_directory=...`` to ``Configuration``.
    """
    system = platform.system()
    if system == "Windows":
        base_str = (
            os.environ.get("LOCALAPPDATA")
            or str(Path.home() / "AppData" / "Local")
        )
        # Build the cache directory as a single Path component by
        # joining with backslashes (Windows separator). On POSIX, where
        # `\` is NOT a separator, this whole string becomes one Path
        # component on every host — which is exactly the shape the
        # cross-platform test asserts equality against
        # (``Path(r'C:\Users\...\un_comtrade\Cache') == d``). Using the
        # ``Path / `` operator on POSIX with a backslash-only base
        # produces a multi-part path mixed with forward slashes and
        # breaks the equality check.
        full = f"{base_str}\\un_comtrade\\Cache".replace("/", "\\")
        return Path(full)
    if system == "Darwin":
        return Path.home() / "Library" / "Caches" / "un_comtrade"
    # Linux and other Unix-like
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "un_comtrade"


def _coerce_non_negative_int(name: str, raw: str) -> int:
    """Parse a non-negative integer from a string. Raises ConfigurationError."""
    try:
        value = int(raw)
    except (TypeError, ValueError) as e:
        raise ConfigurationError(f"{name} must be an integer; got {raw!r}") from e
    if value < 0:
        raise ConfigurationError(f"{name} must be >= 0; got {value}")
    return value


def _coerce_positive_number(name: str, raw: str) -> float:
    """Parse a strictly positive number from a string."""
    try:
        value = float(raw)
    except (TypeError, ValueError) as e:
        raise ConfigurationError(f"{name} must be a number; got {raw!r}") from e
    if value <= 0:
        raise ConfigurationError(f"{name} must be > 0; got {value}")
    return value


def _coerce_bool(name: str, raw: str) -> bool:
    """Parse a boolean from common truthy/falsy strings."""
    norm = raw.strip().lower()
    if norm in {"true", "1", "yes", "on"}:
        return True
    if norm in {"false", "0", "no", "off"}:
        return False
    raise ConfigurationError(
        f"{name} must be a boolean (true/false/1/0/yes/no/on/off); got {raw!r}"
    )


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Configuration:
    """Immutable SDK configuration.

    Per `007_SDK_SPECIFICATION.md` §8 and
    `010_INFRASTRUCTURE_SPECIFICATION.md` §3.
    """

    # --- Authentication (8.1) ---------------------------------------------
    api_key: str | None = None

    # --- Transport (8.2) --------------------------------------------------
    base_url: str = DEFAULT_BASE_URL
    user_agent: str = DEFAULT_USER_AGENT
    timeout_seconds: float = float(DEFAULT_TIMEOUT_SECONDS)
    metadata_timeout_seconds: float = float(DEFAULT_METADATA_TIMEOUT_SECONDS)
    download_timeout_seconds: float = float(DEFAULT_DOWNLOAD_TIMEOUT_SECONDS)
    max_retries: int = DEFAULT_MAX_RETRIES
    initial_backoff_seconds: float = DEFAULT_INITIAL_BACKOFF_SECONDS
    backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER
    backoff_cap_seconds: float = DEFAULT_BACKOFF_CAP_SECONDS
    proxy_url: str | None = None

    # --- Caching (8.3) -----------------------------------------------------
    cache_enabled: bool = True
    cache_directory: Path = field(default_factory=_default_cache_directory)
    metadata_cache_ttl_seconds: int = DEFAULT_METADATA_CACHE_TTL_SECONDS
    trade_cache_ttl_seconds: int = DEFAULT_TRADE_CACHE_TTL_SECONDS

    # --- Logging (8.4) ----------------------------------------------------
    log_level: str = DEFAULT_LOG_LEVEL
    log_format: str = DEFAULT_LOG_FORMAT

    def __post_init__(self) -> None:
        """Validate the configuration immediately after construction.

        Also normalises types: ``cache_directory`` is coerced to
        :class:`pathlib.Path` so callers may pass either a string or a
        ``Path`` instance.
        """
        # Normalise cache_directory to Path (frozen dataclasses don't
        # auto-coerce, so we do it explicitly here).
        if not isinstance(self.cache_directory, Path):
            object.__setattr__(
                self, "cache_directory", Path(self.cache_directory)
            )
        _validate(self)

    # --- Mutators (documented; immutability rule permits these) -----------

    def with_api_key(self, api_key: str | None) -> "Configuration":
        """Return a new Configuration with the API key replaced."""
        return replace(self, api_key=api_key)

    def with_timeout_seconds(self, value: float) -> "Configuration":
        """Return a new Configuration with the request timeout replaced."""
        return replace(self, timeout_seconds=float(value))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate(cfg: Configuration) -> None:
    """Validate a Configuration object. Raises ConfigurationError on failure."""
    if not cfg.base_url or not cfg.base_url.strip():
        raise ConfigurationError("base_url must be a non-empty string")
    if not (cfg.base_url.startswith("http://") or cfg.base_url.startswith("https://")):
        raise ConfigurationError(
            f"base_url must start with http:// or https://; got {cfg.base_url!r}"
        )
    if not cfg.user_agent or not cfg.user_agent.strip():
        raise ConfigurationError("user_agent must be a non-empty string")
    for name, value in (
        ("timeout_seconds", cfg.timeout_seconds),
        ("metadata_timeout_seconds", cfg.metadata_timeout_seconds),
        ("download_timeout_seconds", cfg.download_timeout_seconds),
        ("initial_backoff_seconds", cfg.initial_backoff_seconds),
        ("backoff_multiplier", cfg.backoff_multiplier),
        ("backoff_cap_seconds", cfg.backoff_cap_seconds),
    ):
        if not isinstance(value, (int, float)) or value <= 0:
            raise ConfigurationError(f"{name} must be > 0; got {value!r}")
    if cfg.timeout_seconds > cfg.download_timeout_seconds:
        # Defensive: a request timeout longer than a download timeout is
        # almost certainly a misconfiguration.
        raise ConfigurationError(
            f"timeout_seconds ({cfg.timeout_seconds}) must be <= "
            f"download_timeout_seconds ({cfg.download_timeout_seconds})"
        )
    if not isinstance(cfg.max_retries, int) or cfg.max_retries < 0:
        raise ConfigurationError(f"max_retries must be >= 0; got {cfg.max_retries!r}")
    if cfg.backoff_multiplier < 1:
        raise ConfigurationError(
            f"backoff_multiplier must be >= 1; got {cfg.backoff_multiplier!r}"
        )
    if cfg.api_key is not None and not cfg.api_key.strip():
        raise ConfigurationError("api_key, if provided, must be a non-empty string")
    if cfg.log_level not in ALLOWED_LOG_LEVELS:
        raise ConfigurationError(
            f"log_level must be one of {sorted(ALLOWED_LOG_LEVELS)}; got {cfg.log_level!r}"
        )
    if not cfg.log_format or not cfg.log_format.strip():
        raise ConfigurationError("log_format must be a non-empty string")
    if cfg.proxy_url is not None and not (
        cfg.proxy_url.startswith("http://") or cfg.proxy_url.startswith("https://")
    ):
        raise ConfigurationError(
            f"proxy_url, if provided, must start with http:// or https://; got {cfg.proxy_url!r}"
        )
    if cfg.metadata_cache_ttl_seconds < 0 or cfg.trade_cache_ttl_seconds < 0:
        raise ConfigurationError("cache TTLs must be >= 0")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def _env_get(name: str) -> str | None:
    """Read an environment variable; return None if unset or empty."""
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    return raw


def load_configuration(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    user_agent: str | None = None,
    timeout_seconds: float | None = None,
    metadata_timeout_seconds: float | None = None,
    download_timeout_seconds: float | None = None,
    max_retries: int | None = None,
    initial_backoff_seconds: float | None = None,
    backoff_multiplier: float | None = None,
    backoff_cap_seconds: float | None = None,
    proxy_url: str | None = None,
    cache_enabled: bool | None = None,
    cache_directory: str | Path | None = None,
    metadata_cache_ttl_seconds: int | None = None,
    trade_cache_ttl_seconds: int | None = None,
    log_level: str | None = None,
    log_format: str | None = None,
    env: Mapping[str, str] | None = None,
) -> Configuration:
    """Build a `Configuration` from explicit kwargs, environment, defaults.

    Resolution priority (highest first):
    1. Explicit kwargs passed to this function.
    2. Environment variables (configurable via the ``env`` mapping,
       defaulting to ``os.environ``).
    3. Built-in defaults documented in the specifications.

    The `env` parameter is provided for testability; production code
    should let it default to ``os.environ``.

    No I/O is performed; no network or filesystem access occurs.
    """
    if env is None:
        env = os.environ

    def pick(kw_value, env_name, default, coerce=lambda x: x):
        # Explicit kwargs are assumed already typed; pass through unchanged.
        if kw_value is not None:
            return kw_value
        env_raw = env.get(env_name)
        if env_raw is not None and env_raw.strip() != "":
            return coerce(env_raw)
        # Default is the documented default value (string form); coerce
        # it to the right Python type (int / float / bool).
        return coerce(default)

    resolved_api_key = pick(api_key, ENV_API_KEY, _ENV_DEFAULTS[ENV_API_KEY])
    resolved_base_url = pick(base_url, ENV_BASE_URL, _ENV_DEFAULTS[ENV_BASE_URL])
    resolved_user_agent = pick(user_agent, ENV_USER_AGENT, _ENV_DEFAULTS[ENV_USER_AGENT])
    resolved_timeout = pick(timeout_seconds, ENV_TIMEOUT, _ENV_DEFAULTS[ENV_TIMEOUT],
                            lambda v: _coerce_positive_number(ENV_TIMEOUT, v))
    resolved_metadata_timeout = pick(
        metadata_timeout_seconds, ENV_METADATA_TIMEOUT, _ENV_DEFAULTS[ENV_METADATA_TIMEOUT],
        lambda v: _coerce_positive_number(ENV_METADATA_TIMEOUT, v),
    )
    resolved_download_timeout = pick(
        download_timeout_seconds, ENV_DOWNLOAD_TIMEOUT, _ENV_DEFAULTS[ENV_DOWNLOAD_TIMEOUT],
        lambda v: _coerce_positive_number(ENV_DOWNLOAD_TIMEOUT, v),
    )
    resolved_max_retries = pick(max_retries, ENV_MAX_RETRIES, _ENV_DEFAULTS[ENV_MAX_RETRIES],
                                lambda v: _coerce_non_negative_int(ENV_MAX_RETRIES, v))
    resolved_initial_backoff = pick(
        initial_backoff_seconds, ENV_INITIAL_BACKOFF, _ENV_DEFAULTS[ENV_INITIAL_BACKOFF],
        lambda v: _coerce_positive_number(ENV_INITIAL_BACKOFF, v),
    )
    resolved_backoff_multiplier = pick(
        backoff_multiplier, ENV_BACKOFF_MULTIPLIER, _ENV_DEFAULTS[ENV_BACKOFF_MULTIPLIER],
        lambda v: _coerce_positive_number(ENV_BACKOFF_MULTIPLIER, v),
    )
    resolved_backoff_cap = pick(
        backoff_cap_seconds, ENV_BACKOFF_CAP, _ENV_DEFAULTS[ENV_BACKOFF_CAP],
        lambda v: _coerce_positive_number(ENV_BACKOFF_CAP, v),
    )
    resolved_proxy = pick(proxy_url, ENV_PROXY, _ENV_DEFAULTS[ENV_PROXY])
    resolved_cache_enabled = pick(
        cache_enabled, ENV_CACHE_ENABLED, _ENV_DEFAULTS[ENV_CACHE_ENABLED],
        lambda v: _coerce_bool(ENV_CACHE_ENABLED, v),
    )
    resolved_log_level = pick(log_level, ENV_LOG_LEVEL, _ENV_DEFAULTS[ENV_LOG_LEVEL])

    # Cache directory: explicit path > env var > default
    if cache_directory is not None:
        resolved_cache_dir = Path(cache_directory).expanduser()
    else:
        env_cache_dir = env.get(ENV_CACHE_DIR)
        if env_cache_dir is not None and env_cache_dir.strip() != "":
            resolved_cache_dir = Path(env_cache_dir).expanduser()
        else:
            resolved_cache_dir = _default_cache_directory()

    resolved_metadata_ttl = pick(
        metadata_cache_ttl_seconds, "UN_COMTRADE_METADATA_CACHE_TTL",
        str(DEFAULT_METADATA_CACHE_TTL_SECONDS),
        lambda v: _coerce_non_negative_int("UN_COMTRADE_METADATA_CACHE_TTL", v),
    )
    resolved_trade_ttl = pick(
        trade_cache_ttl_seconds, "UN_COMTRADE_TRADE_CACHE_TTL",
        str(DEFAULT_TRADE_CACHE_TTL_SECONDS),
        lambda v: _coerce_non_negative_int("UN_COMTRADE_TRADE_CACHE_TTL", v),
    )
    resolved_log_format = pick(log_format, "UN_COMTRADE_LOG_FORMAT",
                                DEFAULT_LOG_FORMAT)

    return Configuration(
        api_key=resolved_api_key,
        base_url=resolved_base_url,
        user_agent=resolved_user_agent,
        timeout_seconds=resolved_timeout,
        metadata_timeout_seconds=resolved_metadata_timeout,
        download_timeout_seconds=resolved_download_timeout,
        max_retries=resolved_max_retries,
        initial_backoff_seconds=resolved_initial_backoff,
        backoff_multiplier=resolved_backoff_multiplier,
        backoff_cap_seconds=resolved_backoff_cap,
        proxy_url=resolved_proxy,
        cache_enabled=resolved_cache_enabled,
        cache_directory=resolved_cache_dir,
        metadata_cache_ttl_seconds=resolved_metadata_ttl,
        trade_cache_ttl_seconds=resolved_trade_ttl,
        log_level=resolved_log_level,
        log_format=resolved_log_format,
    )


__all__ = [
    "ALLOWED_LOG_LEVELS",
    "Configuration",
    "ConfigurationError",
    "DEFAULT_BACKOFF_CAP_SECONDS",
    "DEFAULT_BACKOFF_MULTIPLIER",
    "DEFAULT_BASE_URL",
    "DEFAULT_DOWNLOAD_TIMEOUT_SECONDS",
    "DEFAULT_INITIAL_BACKOFF_SECONDS",
    "DEFAULT_LOG_FORMAT",
    "DEFAULT_LOG_LEVEL",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_METADATA_CACHE_TTL_SECONDS",
    "DEFAULT_METADATA_TIMEOUT_SECONDS",
    "DEFAULT_TIMEOUT_SECONDS",
    "DEFAULT_TRADE_CACHE_TTL_SECONDS",
    "DEFAULT_USER_AGENT",
    "ENV_API_KEY",
    "ENV_BACKOFF_CAP",
    "ENV_BACKOFF_MULTIPLIER",
    "ENV_BASE_URL",
    "ENV_CACHE_DIR",
    "ENV_CACHE_ENABLED",
    "ENV_DOWNLOAD_TIMEOUT",
    "ENV_INITIAL_BACKOFF",
    "ENV_LOG_LEVEL",
    "ENV_MAX_RETRIES",
    "ENV_METADATA_TIMEOUT",
    "ENV_PROXY",
    "ENV_TIMEOUT",
    "ENV_USER_AGENT",
    "load_configuration",
]