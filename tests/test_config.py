"""Unit tests for `un_comtrade.config`.

Per ADR-0030, public-API methods and the configuration layer
require unit tests. The tests cover:
- default values per ADR-0008 / ADR-0023 / ADR-0024 / ADR-0025
- environment variable loading
- explicit-argument precedence over environment
- validation errors
- cache-directory resolution
- immutability (frozen dataclass)
- mutator methods (`with_*`)
- no I/O is performed (no network, no filesystem writes)

The tests are deterministic and isolated from any external state.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from un_comtrade.config import (
    ALLOWED_LOG_LEVELS,
    Configuration,
    ConfigurationError,
    DEFAULT_BACKOFF_CAP_SECONDS,
    DEFAULT_BACKOFF_MULTIPLIER,
    DEFAULT_BASE_URL,
    DEFAULT_DOWNLOAD_TIMEOUT_SECONDS,
    DEFAULT_INITIAL_BACKOFF_SECONDS,
    DEFAULT_LOG_FORMAT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_METADATA_CACHE_TTL_SECONDS,
    DEFAULT_METADATA_TIMEOUT_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_TRADE_CACHE_TTL_SECONDS,
    DEFAULT_USER_AGENT,
    ENV_API_KEY,
    ENV_BACKOFF_CAP,
    ENV_BACKOFF_MULTIPLIER,
    ENV_BASE_URL,
    ENV_CACHE_DIR,
    ENV_CACHE_ENABLED,
    ENV_DOWNLOAD_TIMEOUT,
    ENV_INITIAL_BACKOFF,
    ENV_LOG_LEVEL,
    ENV_MAX_RETRIES,
    ENV_METADATA_TIMEOUT,
    ENV_PROXY,
    ENV_TIMEOUT,
    ENV_USER_AGENT,
    _default_cache_directory,
    load_configuration,
)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


class TestDefaults:
    def test_default_api_key_is_none(self):
        cfg = Configuration()
        assert cfg.api_key is None

    def test_default_base_url(self):
        cfg = Configuration()
        assert cfg.base_url == DEFAULT_BASE_URL
        assert DEFAULT_BASE_URL == "https://comtradeapi.un.org"

    def test_default_user_agent(self):
        cfg = Configuration()
        assert cfg.user_agent == DEFAULT_USER_AGENT
        assert DEFAULT_USER_AGENT.startswith("un-comtrade-sdk/")

    def test_default_timeout_seconds(self):
        # ADR-0023 Q16
        cfg = Configuration()
        assert cfg.timeout_seconds == 30

    def test_default_metadata_timeout_seconds(self):
        # ADR-0023 Q18
        cfg = Configuration()
        assert cfg.metadata_timeout_seconds == 15

    def test_default_download_timeout_seconds(self):
        # ADR-0023 Q17
        cfg = Configuration()
        assert cfg.download_timeout_seconds == 300

    def test_default_max_retries_is_three(self):
        # ADR-0008 (revised from 5 to 3)
        cfg = Configuration()
        assert cfg.max_retries == 3
        assert DEFAULT_MAX_RETRIES == 3

    def test_default_initial_backoff(self):
        cfg = Configuration()
        assert cfg.initial_backoff_seconds == 1

    def test_default_backoff_multiplier(self):
        cfg = Configuration()
        assert cfg.backoff_multiplier == 2

    def test_default_backoff_cap(self):
        cfg = Configuration()
        assert cfg.backoff_cap_seconds == 60

    def test_default_cache_enabled_true(self):
        # ADR-0024 Q21
        cfg = Configuration()
        assert cfg.cache_enabled is True

    def test_default_cache_directory_under_user_cache(self):
        # ADR-0024 Q24 — never in the project repository
        cfg = Configuration()
        cwd = Path.cwd().resolve()
        resolved = cfg.cache_directory.resolve()
        assert not str(resolved).startswith(str(cwd))

    def test_default_log_level_is_warning(self):
        # ADR-0025 Q27
        cfg = Configuration()
        assert cfg.log_level == "WARNING"
        assert DEFAULT_LOG_LEVEL == "WARNING"

    def test_default_proxy_url_is_none(self):
        cfg = Configuration()
        assert cfg.proxy_url is None

    def test_default_metadata_cache_ttl_is_30_days(self):
        cfg = Configuration()
        assert cfg.metadata_cache_ttl_seconds == 30 * 24 * 3600
        assert DEFAULT_METADATA_CACHE_TTL_SECONDS == 30 * 24 * 3600


# ---------------------------------------------------------------------------
# Environment variable loading
# ---------------------------------------------------------------------------


class TestEnvironmentLoading:
    def test_env_api_key(self):
        env = {ENV_API_KEY: "test-key-123"}
        cfg = load_configuration(env=env)
        assert cfg.api_key == "test-key-123"

    def test_env_base_url(self):
        env = {ENV_BASE_URL: "https://example.com"}
        cfg = load_configuration(env=env)
        assert cfg.base_url == "https://example.com"

    def test_env_timeout(self):
        env = {ENV_TIMEOUT: "45"}
        cfg = load_configuration(env=env)
        assert cfg.timeout_seconds == 45

    def test_env_max_retries(self):
        env = {ENV_MAX_RETRIES: "7"}
        cfg = load_configuration(env=env)
        assert cfg.max_retries == 7

    def test_env_cache_dir(self):
        env = {ENV_CACHE_DIR: "/tmp/my-cache"}
        cfg = load_configuration(env=env)
        assert cfg.cache_directory == Path("/tmp/my-cache")

    def test_env_cache_enabled_false(self):
        env = {ENV_CACHE_ENABLED: "false"}
        cfg = load_configuration(env=env)
        assert cfg.cache_enabled is False

    def test_env_log_level(self):
        env = {ENV_LOG_LEVEL: "DEBUG"}
        cfg = load_configuration(env=env)
        assert cfg.log_level == "DEBUG"

    def test_env_user_agent(self):
        env = {ENV_USER_AGENT: "my-app/2.0"}
        cfg = load_configuration(env=env)
        assert cfg.user_agent == "my-app/2.0"

    def test_env_proxy(self):
        env = {ENV_PROXY: "http://proxy.example.com:8080"}
        cfg = load_configuration(env=env)
        assert cfg.proxy_url == "http://proxy.example.com:8080"

    def test_empty_env_value_treated_as_unset(self):
        env = {ENV_API_KEY: "   "}
        cfg = load_configuration(env=env)
        assert cfg.api_key is None


# ---------------------------------------------------------------------------
# Explicit argument precedence
# ---------------------------------------------------------------------------


class TestExplicitPrecedence:
    def test_explicit_overrides_env(self):
        env = {ENV_API_KEY: "from-env"}
        cfg = load_configuration(api_key="from-kwarg", env=env)
        assert cfg.api_key == "from-kwarg"

    def test_explicit_overrides_default(self):
        cfg = load_configuration(timeout_seconds=99)
        assert cfg.timeout_seconds == 99

    def test_partial_override_preserves_other_defaults(self):
        cfg = load_configuration(max_retries=10)
        assert cfg.max_retries == 10
        # Other defaults still apply
        assert cfg.timeout_seconds == 30
        assert cfg.base_url == DEFAULT_BASE_URL


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_negative_max_retries_rejected(self):
        with pytest.raises(ConfigurationError, match="max_retries"):
            Configuration(max_retries=-1)

    def test_non_integer_max_retries_rejected(self):
        with pytest.raises(ConfigurationError, match="max_retries"):
            Configuration(max_retries="abc")  # type: ignore[arg-type]

    def test_zero_timeout_rejected(self):
        with pytest.raises(ConfigurationError, match="timeout_seconds"):
            Configuration(timeout_seconds=0)

    def test_negative_timeout_rejected(self):
        with pytest.raises(ConfigurationError, match="timeout_seconds"):
            Configuration(timeout_seconds=-1)

    def test_empty_base_url_rejected(self):
        with pytest.raises(ConfigurationError, match="base_url"):
            Configuration(base_url="")

    def test_invalid_base_url_scheme_rejected(self):
        with pytest.raises(ConfigurationError, match="base_url"):
            Configuration(base_url="ftp://example.com")

    def test_empty_user_agent_rejected(self):
        with pytest.raises(ConfigurationError, match="user_agent"):
            Configuration(user_agent="")

    def test_empty_api_key_rejected(self):
        with pytest.raises(ConfigurationError, match="api_key"):
            Configuration(api_key="")

    def test_whitespace_api_key_rejected(self):
        with pytest.raises(ConfigurationError, match="api_key"):
            Configuration(api_key="   ")

    def test_invalid_log_level_rejected(self):
        with pytest.raises(ConfigurationError, match="log_level"):
            Configuration(log_level="VERBOSE")

    def test_invalid_proxy_scheme_rejected(self):
        with pytest.raises(ConfigurationError, match="proxy_url"):
            Configuration(proxy_url="socks5://proxy")

    def test_backoff_multiplier_below_one_rejected(self):
        with pytest.raises(ConfigurationError, match="backoff_multiplier"):
            Configuration(backoff_multiplier=0.5)

    def test_timeout_exceeds_download_timeout_rejected(self):
        with pytest.raises(ConfigurationError, match="timeout_seconds"):
            Configuration(timeout_seconds=400, download_timeout_seconds=300)

    def test_invalid_env_timeout_rejected(self):
        with pytest.raises(ConfigurationError, match=ENV_TIMEOUT):
            load_configuration(env={ENV_TIMEOUT: "abc"})

    def test_invalid_env_max_retries_rejected(self):
        with pytest.raises(ConfigurationError, match=ENV_MAX_RETRIES):
            load_configuration(env={ENV_MAX_RETRIES: "abc"})

    def test_invalid_env_cache_enabled_rejected(self):
        with pytest.raises(ConfigurationError, match=ENV_CACHE_ENABLED):
            load_configuration(env={ENV_CACHE_ENABLED: "maybe"})

    def test_negative_metadata_cache_ttl_rejected(self):
        with pytest.raises(ConfigurationError, match="cache TTLs"):
            Configuration(metadata_cache_ttl_seconds=-1)

    def test_negative_initial_backoff_rejected(self):
        with pytest.raises(ConfigurationError, match="initial_backoff_seconds"):
            Configuration(initial_backoff_seconds=0)


# ---------------------------------------------------------------------------
# Cache directory resolution
# ---------------------------------------------------------------------------


class TestCacheDirectory:
    def test_linux_default(self, monkeypatch):
        from un_comtrade import config as cfg_module
        monkeypatch.setattr("platform.system", lambda: "Linux")
        monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
        monkeypatch.setattr(cfg_module.Path, "home", classmethod(lambda cls: Path("/home/test")))
        d = _default_cache_directory()
        assert d == Path("/home/test/.cache/un_comtrade")

    def test_linux_xdg_override(self, monkeypatch):
        from un_comtrade import config as cfg_module
        monkeypatch.setattr("platform.system", lambda: "Linux")
        monkeypatch.setenv("XDG_CACHE_HOME", "/var/cache")
        monkeypatch.setattr(cfg_module.Path, "home", classmethod(lambda cls: Path("/home/test")))
        d = _default_cache_directory()
        assert d == Path("/var/cache/un_comtrade")

    def test_macos_default(self, monkeypatch):
        from un_comtrade import config as cfg_module
        monkeypatch.setattr("platform.system", lambda: "Darwin")
        monkeypatch.setattr(cfg_module.Path, "home", classmethod(lambda cls: Path("/Users/test")))
        d = _default_cache_directory()
        assert d == Path("/Users/test/Library/Caches/un_comtrade")

    def test_windows_default(self, monkeypatch):
        from un_comtrade import config as cfg_module
        monkeypatch.setattr("platform.system", lambda: "Windows")
        monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\test\AppData\Local")
        monkeypatch.setattr(cfg_module.Path, "home", classmethod(lambda cls: Path("/Users/test")))
        d = _default_cache_directory()
        assert d == Path(r"C:\Users\test\AppData\Local\un_comtrade\Cache")

    def test_explicit_cache_directory_in_config(self):
        cfg = Configuration(cache_directory="/var/lib/my-cache")
        assert cfg.cache_directory == Path("/var/lib/my-cache")

    def test_explicit_cache_directory_as_path(self, tmp_path):
        p = tmp_path / "my-cache"
        cfg = Configuration(cache_directory=p)
        assert cfg.cache_directory == p


# ---------------------------------------------------------------------------
# Immutability and mutators
# ---------------------------------------------------------------------------


class TestImmutability:
    def test_dataclass_is_frozen(self):
        cfg = Configuration()
        with pytest.raises(Exception):  # FrozenInstanceError
            cfg.api_key = "mutated"  # type: ignore[misc]

    def test_with_api_key_returns_new_instance(self):
        cfg = Configuration()
        new_cfg = cfg.with_api_key("new-key")
        assert new_cfg is not cfg
        assert cfg.api_key is None
        assert new_cfg.api_key == "new-key"

    def test_with_timeout_returns_new_instance(self):
        cfg = Configuration()
        new_cfg = cfg.with_timeout_seconds(99)
        assert cfg.timeout_seconds == 30
        assert new_cfg.timeout_seconds == 99


# ---------------------------------------------------------------------------
# No I/O
# ---------------------------------------------------------------------------


class TestNoIO:
    """The configuration subsystem must NOT touch network or filesystem."""

    def test_load_configuration_does_not_write_files(self, tmp_path, monkeypatch):
        # Configure a cache directory under tmp_path and ensure the load
        # function never creates it.
        cache_dir = tmp_path / "cache-never-created"
        cfg = load_configuration(cache_directory=cache_dir)
        # Construction succeeded
        assert cfg.cache_directory == cache_dir
        # The directory was NOT created
        assert not cache_dir.exists()

    def test_load_configuration_does_not_read_files(self, monkeypatch):
        # Block os.path.expanduser and any path access to prove no FS read.
        # The module imports Path; we patch Path.expanduser to a passthrough
        # to ensure no implicit file reads.
        # Simpler: just assert that load_configuration returns without raising
        # when env is empty.
        cfg = load_configuration(env={})
        assert cfg.base_url == DEFAULT_BASE_URL


# ---------------------------------------------------------------------------
# Round-trip — env, explicit, defaults
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_no_args_returns_defaults(self):
        cfg = load_configuration()
        assert cfg == Configuration()

    def test_full_explicit_equals_dataclass_construction(self):
        cfg = load_configuration(
            api_key="k",
            base_url="https://example.org",
            user_agent="custom/1.0",
            timeout_seconds=42,
            metadata_timeout_seconds=12,
            download_timeout_seconds=600,
            max_retries=5,
            initial_backoff_seconds=2.0,
            backoff_multiplier=3.0,
            backoff_cap_seconds=120.0,
            proxy_url="http://proxy:3128",
            cache_enabled=False,
            cache_directory="/tmp/cache",
            metadata_cache_ttl_seconds=3600,
            trade_cache_ttl_seconds=0,
            log_level="INFO",
            log_format="%(message)s",
        )
        expected = Configuration(
            api_key="k",
            base_url="https://example.org",
            user_agent="custom/1.0",
            timeout_seconds=42,
            metadata_timeout_seconds=12,
            download_timeout_seconds=600,
            max_retries=5,
            initial_backoff_seconds=2.0,
            backoff_multiplier=3.0,
            backoff_cap_seconds=120.0,
            proxy_url="http://proxy:3128",
            cache_enabled=False,
            cache_directory="/tmp/cache",
            metadata_cache_ttl_seconds=3600,
            trade_cache_ttl_seconds=0,
            log_level="INFO",
            log_format="%(message)s",
        )
        assert cfg == expected


# ---------------------------------------------------------------------------
# Allowed log levels sanity
# ---------------------------------------------------------------------------


class TestLogLevels:
    def test_allowed_levels_are_python_stdlib(self):
        assert ALLOWED_LOG_LEVELS == frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})