"""Primary entry point for the UN Comtrade Python SDK.

This module defines `ComtradeClient`, the single object
consumers instantiate directly per the SDK specification
(§2.1). The client composes the infrastructure built in
P1-001 through P1-008 and exposes lifecycle hooks for
clean shutdown.

FC-001 (ComtradeClient public facade) extends the client
with the four top-level service facades called out by the
CLI Contract Verification (docs/033):

- ``client.metadata``  — `MetadataService`
- ``client.trade``     — `TradeService`
- ``client.analytics`` — `AnalyticsEngine`
- ``client.etl``       — `ETLFacade`
- ``client.storage``   — `StorageRegistry`

Each service is constructed lazily on first access and
shares the client's configuration and transport where
applicable. No service is duplicated: re-accessing the
same property returns the same instance.

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
    earlier Phase 1 tasks and the public service facades
    added in FC-001. It owns one `HttpTransport` instance
    for the lifetime of the client.

    Public service accessors (all lazy, all singletons
    per-client):

    - ``client.metadata``  — reference catalogue service
      (`MetadataService`).
    - ``client.trade``     — trade-data service
      (`TradeService`).
    - ``client.analytics`` — analytics engine
      (`AnalyticsEngine`).
    - ``client.etl``       — ETL pipeline factory
      (`ETLFacade`).
    - ``client.storage``   — storage registry
      (`StorageRegistry`).

    Usage::

        from un_comtrade import ComtradeClient
        from un_comtrade.config import Configuration

        cfg = Configuration(api_key="...")
        with ComtradeClient(cfg) as client:
            countries = client.metadata.get_countries()
            exports = client.trade.get_exports(699, "2022")
            summary = client.analytics.country_summary(
                dataset, reporter_code=699,
            )
            pipeline = client.etl.pipeline("ingest", stages)
            pipeline.run(source)
            dataset = client.storage.open("data.parquet")

    Or, for the convenience of letting the SDK load the
    configuration from environment variables::

        client = ComtradeClient()  # reads UN_COMTRADE_KEY etc.
    """

    def __init__(
        self,
        configuration: Configuration | str | None = None,
        *,
        transport: HttpTransport | None = None,
        metadata_service: MetadataService | None = None,
        cache: MetadataCache | None = None,
        parser: MetadataParser | None = None,
        trade_service: "TradeService | None" = None,
        analytics_engine: "AnalyticsEngine | None" = None,
        etl_facade: "ETLFacade | None" = None,
        storage_registry: "StorageRegistry | None" = None,
    ) -> None:
        """Construct a client.

        Parameters
        ----------
        configuration
            Optional `Configuration` instance, or the
            string ``"api_key=..."`` shortcut for tests.
            When ``None``, ``load_configuration()`` is
            called to read from environment variables
            (and defaults). Per spec §2.2, the
            configuration is treated as immutable after
            construction.
        transport
            Optional pre-built `HttpTransport`. When
            `None`, the client builds one from the
            configuration (recommended for most uses).
            When supplied, the caller retains ownership
            — `close()` will not close it. This is
            primarily useful for tests that inject
            `httpx.MockTransport`-backed transports.
        metadata_service
            Optional pre-built `MetadataService`. When
            `None`, the client constructs one lazily on
            first access to `client.metadata`. When
            supplied, the caller retains ownership.
        cache
            Optional pre-built `MetadataCache`. When
            `None`, the client constructs a default
            platform-default cache lazily when the
            metadata service is first built. Pass
            `cache=None` explicitly to disable caching.
        parser
            Optional pre-built `MetadataParser`. When
            `None`, the client constructs a default
            `MetadataParser` lazily when the metadata
            service is first built.
        trade_service
            Optional pre-built `TradeService`. When
            `None`, the client builds one on first access
            to `client.trade` (sharing its `transport`
            and `configuration`).
        analytics_engine
            Optional pre-built `AnalyticsEngine`. When
            `None`, the client builds one on first access
            to `client.analytics`.
        etl_facade
            Optional pre-built `ETLFacade`. When `None`,
            the client builds one on first access to
            `client.etl`.
        storage_registry
            Optional pre-built `StorageRegistry`. When
            `None`, the client builds a default
            `StorageRegistry` on first access to
            `client.storage`.
        """
        # Allow the string shortcut `ComtradeClient(api_key="...")`
        # for ergonomics; resolve it to a `Configuration` before
        # the rest of the constructor runs.
        if isinstance(configuration, str):
            configuration = Configuration(api_key=configuration)
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

        # FC-001: additional service facades. Each is lazily
        # constructed on first access and shared across all
        # subsequent accesses (singleton per-client).
        self._trade_service: "TradeService | None" = trade_service
        self._analytics_engine: "AnalyticsEngine | None" = analytics_engine
        self._etl_facade: "ETLFacade | None" = etl_facade
        self._storage_registry: "StorageRegistry | None" = storage_registry

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

    @property
    def trade(self) -> "TradeService":
        """The trade-data service owned by this client.

        Constructed lazily on first access. The service
        shares this client's ``transport`` and
        ``configuration`` (per the FC-001 contract); it
        does **not** take ownership of the transport.
        """
        if self._trade_service is None:
            from .parser import TradeParser
            from .trade import TradeService

            self._trade_service = TradeService(
                transport=self._transport,
                configuration=self._config,
                parser=TradeParser(),
            )
        return self._trade_service

    @property
    def analytics(self) -> "AnalyticsEngine":
        """The analytics engine owned by this client.

        Constructed lazily on first access. The engine
        receives a small mapping of the client's
        configuration so it can surface SDK-wide
        settings (e.g. log level) on its results.
        """
        if self._analytics_engine is None:
            from .analytics import AnalyticsEngine

            self._analytics_engine = AnalyticsEngine(
                name="comtrade",
                config={
                    "log_level": self._config.log_level,
                    "schema_version": "1.0.0",
                },
            )
        return self._analytics_engine

    @property
    def etl(self) -> "ETLFacade":
        """The ETL pipeline facade owned by this client.

        Constructed lazily on first access. The facade
        injects a small mapping of this client's
        configuration into every pipeline it builds
        via ``ETLFacade.pipeline(...)``.
        """
        if self._etl_facade is None:
            from .etl import ETLFacade

            self._etl_facade = ETLFacade(configuration={
                "log_level": self._config.log_level,
                "base_url": self._config.base_url,
            })
        return self._etl_facade

    @property
    def storage(self) -> "StorageRegistry":
        """The storage registry owned by this client.

        Constructed lazily on first access. The
        registry is a thin wrapper over the five SDK
        backends; ``client.storage.open(uri)`` is the
        public read path.
        """
        if self._storage_registry is None:
            from .storage._base import StorageRegistry

            self._storage_registry = StorageRegistry()
        return self._storage_registry

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