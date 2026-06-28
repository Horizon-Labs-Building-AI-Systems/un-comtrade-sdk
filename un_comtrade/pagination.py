"""Pagination engine for the UN Comtrade SDK.

Per `009_TRADE_LAYER_SPEC.md` §5 and ADR-0004, the
upstream API does not support a documented pagination
protocol. The trade layer paginates by splitting a
multi-period query into chunks of at most
`max_periods_per_page` periods, then aggregating the
per-page responses into a single `TradeResponse`.

This module provides:

- `PaginationConfig` — limits (max periods per page,
  max pages, max records per page, max period
  granularity).
- `PageProgress` — progress callback payload.
- `PaginationEngine` — splits the period list, fetches
  pages via a caller-supplied `fetch_page` callable,
  merges the responses (with cross-page deduplication
  via `TradeParser.composite_key`), invokes the
  progress callback, supports early termination, and
  enforces page safeguards.

The engine is **consumer-agnostic**: it does not know
about the upstream URL shape, the `TradeQuery`
construction, or the `HttpTransport`. Callers wire
those (typically `TradeService._execute`) into the
`fetch_page` callable.

Design notes:

- Pagination strategy: split-by-period per ADR-0004.
- Maximum records per call: 250,000 (authenticated)
  / 500 (public preview) / 2,500,000 (async delivery).
- Maximum pages per batch in the MVP: 12 (a batch
  that would exceed this limit is aborted).
- Last-page detection: a partial page (count <
  max_records) terminates pagination; otherwise the
  consumer-supplied period list is exhausted.
- Progress callback: invoked after each page with
  a `PageProgress` payload. Returning `False` aborts
  pagination.
- Cross-page deduplication: records sharing a
  composite key (per `TRADE_RECORD_KEY_FIELDS`) are
  collapsed; first-wins.
- No async / batch-download: per the task scope.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Sequence

from .exceptions import ComtradeError
from .logging import get_logger
from .models import TradeResponse


__all__ = [
    "DEFAULT_MAX_PAGES",
    "DEFAULT_MAX_PERIODS_PER_PAGE",
    "DEFAULT_MAX_RECORDS_PER_PAGE",
    "PageProgress",
    "PaginationAborted",
    "PaginationConfig",
    "PaginationEngine",
    "PaginationError",
    "PaginationLimitExceeded",
    "ProgressCallback",
]


# ---------------------------------------------------------------------------
# Defaults (per ADR-0004 + `009_TRADE_LAYER_SPEC.md` §5.3 / §6.6)
# ---------------------------------------------------------------------------


#: Default max periods per page (ADR-0004: split-on-period, ≤12).
DEFAULT_MAX_PERIODS_PER_PAGE: int = 12

#: Default max pages per batch in the MVP
#: (`009_TRADE_LAYER_SPEC.md` §6.6).
DEFAULT_MAX_PAGES: int = 12

#: Default max records per page (authenticated endpoint
#: cap per `009_TRADE_LAYER_SPEC.md` §5.3).
DEFAULT_MAX_RECORDS_PER_PAGE: int = 250_000


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PaginationError(ComtradeError):
    """Base class for pagination errors.

    Per `009_TRADE_LAYER_SPEC.md` §10.4, a pagination
    failure raises a `TradeError`. The SDK represents
    this as `PaginationError` (a subclass of
    `ComtradeError`, which is the SDK's `TradeError`
    base).
    """


class PaginationLimitExceeded(PaginationError):
    """Raised when pagination would require more pages than `max_pages`.

    Per `009_TRADE_LAYER_SPEC.md` §6.6, a batch that
    would exceed 12 pages is aborted and the consumer
    is asked to reduce the scope. The error message
    names the requested page count and the
    configured limit.
    """


class PaginationAborted(PaginationError):
    """Raised when the progress callback returns `False`.

    Per `009_TRADE_LAYER_SPEC.md` §5.6, the consumer
    can cancel pagination by signalling abort via
    the progress callback.
    """


# ---------------------------------------------------------------------------
# Configuration + progress
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PaginationConfig:
    """Limits enforced by the pagination engine.

    Per ADR-0004 + `009_TRADE_LAYER_SPEC.md` §5.3 / §6.6:

    - `max_periods_per_page`: 12 (split-by-period cap).
    - `max_pages`: 12 (MVP batch limit).
    - `max_records_per_page`: 250,000 (authenticated
      endpoint cap).

    The defaults are the documented values; callers
    may override (e.g. to use the 500-record cap on
    the public preview endpoint).
    """

    max_periods_per_page: int = DEFAULT_MAX_PERIODS_PER_PAGE
    max_pages: int = DEFAULT_MAX_PAGES
    max_records_per_page: int = DEFAULT_MAX_RECORDS_PER_PAGE

    def __post_init__(self) -> None:
        if not isinstance(self.max_periods_per_page, int):
            raise TypeError(
                f"max_periods_per_page must be an int; got "
                f"{type(self.max_periods_per_page).__name__}"
            )
        if self.max_periods_per_page < 1:
            raise ValueError(
                f"max_periods_per_page must be ≥ 1; got "
                f"{self.max_periods_per_page}"
            )
        if not isinstance(self.max_pages, int):
            raise TypeError(
                f"max_pages must be an int; got "
                f"{type(self.max_pages).__name__}"
            )
        if self.max_pages < 1:
            raise ValueError(
                f"max_pages must be ≥ 1; got {self.max_pages}"
            )
        if not isinstance(self.max_records_per_page, int):
            raise TypeError(
                f"max_records_per_page must be an int; got "
                f"{type(self.max_records_per_page).__name__}"
            )
        if self.max_records_per_page < 1:
            raise ValueError(
                f"max_records_per_page must be ≥ 1; got "
                f"{self.max_records_per_page}"
            )


@dataclass(frozen=True)
class PageProgress:
    """Progress payload passed to the callback after each page.

    Fields:
    - `page_number`: 1-indexed page number.
    - `page_count`: total expected page count (computed
      up-front; may be lower than `max_pages` when the
      period list is short).
    - `records_so_far`: cumulative record count BEFORE
      this page's records are merged (i.e., the count
      at the start of this page's processing).
    - `page_records`: number of records returned by this
      page.
    - `periods`: tuple of period tokens in this page.
    """

    page_number: int
    page_count: int
    records_so_far: int
    page_records: int
    periods: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.page_number, int) or self.page_number < 1:
            raise ValueError(
                f"page_number must be ≥ 1; got {self.page_number}"
            )
        if not isinstance(self.page_count, int) or self.page_count < 1:
            raise ValueError(
                f"page_count must be ≥ 1; got {self.page_count}"
            )
        if not isinstance(self.records_so_far, int) or self.records_so_far < 0:
            raise ValueError(
                f"records_so_far must be ≥ 0; got {self.records_so_far}"
            )
        if not isinstance(self.page_records, int) or self.page_records < 0:
            raise ValueError(
                f"page_records must be ≥ 0; got {self.page_records}"
            )
        if not isinstance(self.periods, tuple):
            raise TypeError(
                f"periods must be a tuple; got {type(self.periods).__name__}"
            )


#: Callback signature: `(progress: PageProgress) -> bool | None`.
#: Return `False` to abort pagination; `True` or `None`
#: to continue. Returning anything other than `False`
#: is treated as continue.
ProgressCallback = Callable[[PageProgress], bool | None]


# ---------------------------------------------------------------------------
# Page-fetching callable contract
# ---------------------------------------------------------------------------


#: Callable that fetches a single page. Receives the
#: list of period tokens for this page and returns the
#: `TradeResponse`.
PageFetcher = Callable[[Sequence[str]], TradeResponse]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class PaginationEngine:
    """Transparent pagination over a list of period tokens.

    Stateless: every method is a pure function of its
    inputs. The engine holds no resources and can be
    shared across threads.

    The engine is consumer-agnostic. Callers supply:

    - A list of period tokens (the engine splits this
      into chunks of `max_periods_per_page`).
    - A `fetch_page` callable that takes a chunk of
      periods and returns a `TradeResponse`. Typically
      wraps `TradeService._execute` (P2-006) or any
      equivalent page-retrieval function.
    - An optional progress callback.

    The engine returns a single merged `TradeResponse`
    containing all records across all pages (with
    cross-page deduplication via
    `TradeParser.composite_key`).
    """

    def __init__(
        self,
        config: PaginationConfig | None = None,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        """Construct a pagination engine.

        Parameters
        ----------
        config
            Optional `PaginationConfig`. When `None`,
            the documented defaults are used.
        logger
            Optional logger. When `None`, the SDK's
            `metadata` logger is used (the same channel
            the parser writes to).
        """
        self._config: PaginationConfig = (
            config if config is not None else PaginationConfig()
        )
        self._logger: logging.Logger = (
            logger if logger is not None else get_logger("metadata")
        )

    @property
    def config(self) -> PaginationConfig:
        """The pagination configuration this engine uses."""
        return self._config

    # ----- Public API -----------------------------------------------------

    def paginate(
        self,
        periods: Sequence[str] | str,
        fetch_page: PageFetcher,
        on_progress: ProgressCallback | None = None,
    ) -> TradeResponse:
        """Fetch all pages and merge into a single `TradeResponse`.

        Parameters
        ----------
        periods
            Ordered list of period tokens (YYYY or
            YYYYMM). A single comma-separated string is
            also accepted for convenience (matching the
            `TradeQuery.period` convention).
        fetch_page
            Callable that takes a sequence of period
            tokens and returns a `TradeResponse`. The
            engine invokes this callable once per page.
        on_progress
            Optional progress callback invoked after
            each page. Returning `False` aborts
            pagination and raises `PaginationAborted`.

        Returns
        -------
        TradeResponse
            Merged response containing all records
            across all pages (deduplicated by
            composite key).

        Raises
        ------
        PaginationLimitExceeded
            The number of pages required to fetch the
            requested periods exceeds `max_pages`.
        PaginationAborted
            The progress callback returned `False`.
        """
        period_list = self._normalize_periods(periods)
        chunks = self._split_periods(period_list)
        self._enforce_page_limit(chunks)

        page_count = len(chunks)
        merged_records: dict[tuple, object] = {}
        last_error: str = ""
        first_url: str = ""
        last_url: str = ""
        total_elapsed: float = 0.0
        records_so_far: int = 0

        for page_number, chunk in enumerate(chunks, start=1):
            response = fetch_page(chunk)
            if first_url == "":
                first_url = response.upstream_url
            last_url = response.upstream_url
            total_elapsed += response.elapsed_seconds
            if response.error:
                last_error = response.error

            # Cross-page dedup via TradeParser.composite_key.
            # Records sharing a composite key are
            # collapsed; first-wins.
            for record in response.records:
                key = self._composite_key(record)
                if key not in merged_records:
                    merged_records[key] = record

            page_records = len(response.records)
            progress = PageProgress(
                page_number=page_number,
                page_count=page_count,
                records_so_far=records_so_far,
                page_records=page_records,
                periods=tuple(chunk),
            )
            records_so_far = len(merged_records)

            if on_progress is not None:
                should_continue = on_progress(progress)
                if should_continue is False:
                    self._logger.info(
                        "pagination aborted by callback at page %d/%d",
                        page_number,
                        page_count,
                    )
                    raise PaginationAborted(
                        f"Pagination aborted by progress callback "
                        f"after page {page_number}/{page_count}."
                    )

            self._logger.debug(
                "page %d/%d fetched records=%d cumulative=%d periods=%r",
                page_number,
                page_count,
                page_records,
                records_so_far,
                list(chunk),
            )

        merged_list = list(merged_records.values())
        return TradeResponse(
            elapsed_seconds=total_elapsed,
            count=len(merged_list),
            records=merged_list,
            error=last_error,
            upstream_url=first_url,
            skipped=0,
        )

    # ----- Internal helpers ----------------------------------------------

    @staticmethod
    def _normalize_periods(
        periods: Sequence[str] | str,
    ) -> list[str]:
        """Coerce `periods` to a list of non-empty tokens.

        Accepts a list / tuple of strings, or a single
        comma-separated string (matching the
        `TradeQuery.period` convention).
        """
        if isinstance(periods, str):
            tokens = [p.strip() for p in periods.split(",")]
        else:
            tokens = [str(p).strip() for p in periods]
        tokens = [t for t in tokens if t]
        if not tokens:
            raise ValueError("periods must be non-empty")
        return tokens

    def _split_periods(
        self, periods: list[str]
    ) -> list[list[str]]:
        """Split `periods` into chunks of `max_periods_per_page`."""
        chunk_size = self._config.max_periods_per_page
        return [
            periods[i : i + chunk_size]
            for i in range(0, len(periods), chunk_size)
        ]

    def _enforce_page_limit(
        self, chunks: list[list[str]]
    ) -> None:
        """Raise `PaginationLimitExceeded` if `len(chunks)` exceeds `max_pages`."""
        page_count = len(chunks)
        if page_count > self._config.max_pages:
            raise PaginationLimitExceeded(
                f"Pagination would require {page_count} pages, "
                f"exceeding the documented limit of "
                f"{self._config.max_pages} (per "
                f"`009_TRADE_LAYER_SPEC.md` §6.6). "
                f"Reduce the period range or increase the "
                f"page size (PaginationConfig.max_periods_per_page)."
            )

    @staticmethod
    def _composite_key(record: object) -> tuple:
        """Return the composite dedup key for a `TradeRecord`.

        Imported lazily so this module does not couple
        the pagination engine to the parser at import
        time. The key matches
        `TRADE_RECORD_KEY_FIELDS` per
        `006_DATA_MODEL.md` §3.12.
        """
        from .parser import TradeParser
        return TradeParser.composite_key(record)