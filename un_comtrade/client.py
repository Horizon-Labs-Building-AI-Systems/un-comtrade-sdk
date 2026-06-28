"""Primary entry point for the UN Comtrade Python SDK.

This module defines `ComtradeClient`, the single object
consumers instantiate directly per the SDK specification
(§2.1). The client composes the infrastructure built in
P1-001 through P1-008 and exposes lifecycle hooks for
clean shutdown.

In Phase 1 (this task) the client is a SKELETON: it
holds the configuration, builds the transport, and
provides lifecycle methods. It does NOT yet expose any
metadata or trade methods — those land in later phases
per `IMPLEMENTATION_ROADMAP.md`.

Per spec §2.2:

- The constructor accepts a `Configuration` object.
- The constructor does NOT perform network I/O. The first
  network call happens when a business method is invoked.
- The configuration is treated as immutable post-
  construction (mutator methods on `Configuration` return
  new instances).
"""

from __future__ import annotations

import logging
from typing import Optional

from .cache import MetadataCache
from .config import Configuration, load_configuration
from .logging import (
    LOGGER_NAMESPACE,
    LOG_LEVELS,
    LOGGING_DEFAULT_LEVEL,
)
from .metadata import MetadataService
from .parser import MetadataParser
from .transport import (
    HttpTransport,
    RetryPolicy,
    TimeoutConfig,
)


__all__ = ["ComtradeClient"]


class ComtradeClient:
    """Primary entry point for the UN Comtrade Python SDK.

    The client composes the infrastructure layers built in
    earlier Phase 1 tasks. It owns one `HttpTransport`
    instance for the lifetime of the client. Higher-level
    methods (metadata / trade) will be added in subsequent
    phases.

    Usage::

        from un_comtrade import ComtradeClient
        from un_comtrade.config import Configuration

        cfg = Configuration(api_key="...")
        with ComtradeClient(cfg) as client:
            ...  # future metadata / trade methods

    Or, for the convenience of letting the SDK load the
    configuration from environment variables::

        client = ComtradeClient()  # reads UN_COMTRADE_KEY etc.
    """

    def __init__(
        self,
        configuration: Configuration | None = None,
        *,
        transport: HttpTransport | None = None,
        metadata_service: MetadataService | None = None,
        cache: MetadataCache | None = None,
        parser: MetadataParser | None = None,
    ) -> None:
        """Construct a client.

        Parameters
        ----------
        configuration
            Optional `Configuration` instance. When `None`,
            `load_configuration()` is called to read from
            environment variables (and defaults). Per spec
            §2.2, the configuration is treated as immutable
            after construction.
        transport
            Optional pre-built `HttpTransport`. When `None`,
            the client builds one from the configuration
            (recommended for most uses). When supplied, the
            caller retains ownership — `close()` will not
            close it. This is primarily useful for tests
            that inject `httpx.MockTransport`-backed
            transports.
        metadata_service
            Optional pre-built `MetadataService`. When `None`,
            the client constructs one lazily on first access
            to `client.metadata`. When supplied, the caller
            retains ownership.
        cache
            Optional pre-built `MetadataCache`. When `None`,
            the client constructs a default platform-default
            cache lazily when the metadata service is first
            built. Pass `cache=None` explicitly to disable
            caching.
        parser
            Optional pre-built `MetadataParser`. When `None`,
            the client constructs a default `MetadataParser`
            lazily when the metadata service is first built.
        """
        self._config: Configuration = (
            configuration if configuration is not None else load_configuration()
        )

        # Configure the SDK logger level from the configuration
        # unless the consumer has already set it explicitly.
        self._configure_logging(self._config.log_level)

        if transport is not None:
            self._transport: HttpTransport = transport
            self._owns_transport: bool = False
        else:
            self._transport = HttpTransport(
                base_url=self._config.base_url,
                user_agent=self._config.user_agent,
                api_key=self._config.api_key,
                retry=self._build_retry_policy(self._config),
                timeout=self._build_timeout_config(self._config),
            )
            self._owns_transport = True

        # MetadataService is wired lazily so its construction
        # cost (and the cache + parser import chains) is paid
        # only on first use. The service is owned by the client.
        self._metadata_service: MetadataService | None = metadata_service
        self._metadata_cache = cache
        self._metadata_parser = parser

    # ----- Properties -----------------------------------------------------

    @property
    def config(self) -> Configuration:
        """The immutable configuration this client was built from."""
        return self._config

    @property
    def transport(self) -> HttpTransport:
        """The HTTP transport used by the client.

        Exposed for advanced consumers (e.g. diagnostics).
        Future business methods will not require callers
        to interact with the transport directly.
        """
        return self._transport

    @property
    def metadata(self) -> MetadataService:
        """The metadata service owned by this client.

        Constructed lazily on first access. The client
        retains ownership — the service is closed when
        `client.close()` runs (no-op for the current
        skeleton; cache lifecycle will land with the
        cache subsystem).
        """
        if self._metadata_service is None:
            self._metadata_service = MetadataService(
                self._transport,
                cache=self._metadata_cache,
                parser=self._metadata_parser,
            )
        return self._metadata_service

    # ----- Lifecycle ------------------------------------------------------

    def close(self) -> None:
        """Release the transport's underlying resources.

        Closes the transport only when the client owns it
        (the default). When a caller-supplied transport
        was injected via the constructor, the caller
        retains ownership and is responsible for closing
        it.

        Safe to call multiple times.
        """
        if self._owns_transport:
            self._transport.close()

    def __enter__(self) -> "ComtradeClient":
        """Enter the context manager; returns the client."""
        return self

    def __exit__(self, *exc_info: object) -> None:
        """Exit the context manager; closes the owned transport."""
        self.close()

    # ----- Internal helpers -----------------------------------------------

    @staticmethod
    def _build_retry_policy(config: Configuration) -> RetryPolicy:
        """Translate configuration fields into a `RetryPolicy`.

        The configuration field `max_retries` denotes the
        total number of attempts (matching the ADR-0008
        default of 3) and maps directly to
        `RetryPolicy.attempts`.
        """
        return RetryPolicy(
            attempts=config.max_retries,
            initial_delay=config.initial_backoff_seconds,
            multiplier=config.backoff_multiplier,
            max_delay=config.backoff_cap_seconds,
        )

    @staticmethod
    def _build_timeout_config(config: Configuration) -> TimeoutConfig:
        """Translate configuration fields into a `TimeoutConfig`."""
        return TimeoutConfig(
            default=config.timeout_seconds,
            metadata=config.metadata_timeout_seconds,
            large_download=config.download_timeout_seconds,
        )

    @staticmethod
    def _configure_logging(level_name: str) -> None:
        """Apply the configured log level to the SDK logger namespace.

        Honours the consumer's explicit choice when they
        have already set the SDK logger level via the
        standard `logging` API; only adjusts the level
        when it is currently unset.
        """
        sdk_logger = logging.getLogger(LOGGER_NAMESPACE)
        if sdk_logger.level != logging.NOTSET:
            return
        level = LOG_LEVELS.get(level_name.upper(), LOGGING_DEFAULT_LEVEL)
        sdk_logger.setLevel(level)