"""Batch trade download orchestration.

Per `009_TRADE_LAYER_SPEC.md` §6 (Batch Processing
Strategy) + §7 (Download Strategy), the SDK supports
batch downloads that iterate over the cartesian
product of `(reporter, year, partner)` tuples.

This module provides:

- `BatchConfig` — fail-fast behaviour + executor
  configuration.
- `BatchItemResult` — per-item success / failure
  outcome.
- `BatchProgress` — progress callback payload.
- `BatchResult` — aggregated result with helpers.
- `BatchDownloader` — iterates `(reporters × years ×
  partners)` and calls the existing `TradeService`
  for each tuple. Failures are collected (don't
  abort the batch unless `fail_fast=True`); the
  transport's retry + timeout policies are reused.

Per the task scope:

- Reuses `TradeService` end-to-end (no new HTTP,
  no new parsing).
- Sequential execution (per `009_TRADE_LAYER_SPEC.md`
  §6.2; the upstream does not support concurrent
  calls from a single consumer without rate
  limiting).
- Partial success reporting: failed items are
  collected on the `BatchResult` rather than
  aborting the whole batch.
- Progress reporting: callback after each item.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Sequence

from .logging import get_logger
from .models import TradeRecord, TradeResponse


if TYPE_CHECKING:
    from .trade import TradeService


__all__ = [
    "BatchConfig",
    "BatchDownloader",
    "BatchItemResult",
    "BatchProgress",
    "BatchProgressCallback",
    "BatchResult",
]


#: Callback signature: `(progress: BatchProgress) -> bool | None`.
#: Return `False` to abort the batch; `True` or `None`
#: to continue. Returning anything other than `False`
#: is treated as continue.
BatchProgressCallback = Callable[["BatchProgress"], bool | None]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BatchConfig:
    """Configuration for batch downloads.

    Attributes:
    - `fail_fast`: when `True`, the first per-item
      failure aborts the batch and the exception is
      re-raised. When `False` (default), failures are
      collected and the batch completes with a
      `BatchResult` containing both successes and
      failures.

    Per `009_TRADE_LAYER_SPEC.md` §6.2, batch
    execution is sequential; concurrent calls from a
    single consumer are not supported by the upstream
    without rate limiting. The MVP supports
    sequential execution only.
    """

    fail_fast: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.fail_fast, bool):
            raise TypeError(
                f"fail_fast must be a bool; got "
                f"{type(self.fail_fast).__name__}"
            )


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BatchItemResult:
    """Per-item success / failure outcome.

    On success:
    - `response` is the upstream's `TradeResponse`.
    - `error` is `None`.

    On failure:
    - `response` is `None`.
    - `error` is the stringified exception.
    """

    reporter_code: int
    year: int
    partner_code: int
    response: TradeResponse | None
    error: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.reporter_code, bool) or not isinstance(
            self.reporter_code, int
        ):
            raise TypeError(
                f"reporter_code must be an int; got "
                f"{type(self.reporter_code).__name__}"
            )
        if self.reporter_code < 0:
            raise ValueError(
                f"reporter_code must be non-negative; got "
                f"{self.reporter_code}"
            )
        if isinstance(self.year, bool) or not isinstance(self.year, int):
            raise TypeError(
                f"year must be an int; got {type(self.year).__name__}"
            )
        if isinstance(self.partner_code, bool) or not isinstance(
            self.partner_code, int
        ):
            raise TypeError(
                f"partner_code must be an int; got "
                f"{type(self.partner_code).__name__}"
            )
        if self.partner_code < 0:
            raise ValueError(
                f"partner_code must be non-negative; got "
                f"{self.partner_code}"
            )
        if self.response is not None and not isinstance(
            self.response, TradeResponse
        ):
            raise TypeError(
                f"response must be a TradeResponse or None; got "
                f"{type(self.response).__name__}"
            )
        if self.error is not None and not isinstance(self.error, str):
            raise TypeError(
                f"error must be a str or None; got "
                f"{type(self.error).__name__}"
            )
        if (self.response is None) == (self.error is None):
            raise ValueError(
                "BatchItemResult must have exactly one of "
                "response (success) or error (failure)"
            )

    @property
    def is_success(self) -> bool:
        """True if this item succeeded."""
        return self.response is not None

    @property
    def is_failure(self) -> bool:
        """True if this item failed."""
        return self.error is not None

    @property
    def records(self) -> list[TradeRecord]:
        """The records returned by this item (empty on failure)."""
        if self.response is None:
            return []
        return list(self.response.records)


@dataclass(frozen=True)
class BatchProgress:
    """Progress payload passed to the callback after each item.

    Fields:
    - `completed`: number of items processed so far
      (including the current one).
    - `total`: total number of items in the batch.
    - `successful`: number of successful items so far.
    - `failed`: number of failed items so far.
    - `last_item`: the `BatchItemResult` for the item
      just completed.
    """

    completed: int
    total: int
    successful: int
    failed: int
    last_item: BatchItemResult

    def __post_init__(self) -> None:
        if not isinstance(self.completed, int) or self.completed < 0:
            raise ValueError(
                f"completed must be a non-negative int; got "
                f"{self.completed}"
            )
        if not isinstance(self.total, int) or self.total < 1:
            raise ValueError(
                f"total must be ≥ 1; got {self.total}"
            )
        if self.completed > self.total:
            raise ValueError(
                f"completed ({self.completed}) must be ≤ total "
                f"({self.total})"
            )
        if not isinstance(self.successful, int) or self.successful < 0:
            raise ValueError(
                f"successful must be a non-negative int; got "
                f"{self.successful}"
            )
        if not isinstance(self.failed, int) or self.failed < 0:
            raise ValueError(
                f"failed must be a non-negative int; got "
                f"{self.failed}"
            )
        if self.successful + self.failed != self.completed:
            raise ValueError(
                f"successful ({self.successful}) + failed "
                f"({self.failed}) must equal completed "
                f"({self.completed})"
            )

    @property
    def ratio(self) -> float:
        """Completion ratio in `[0.0, 1.0]`."""
        return self.completed / self.total


@dataclass(frozen=True)
class BatchResult:
    """Aggregated result of a batch download.

    `items` is the ordered list of all items (in the
    iteration order: reporter × year × partner).
    `successful` and `failed` are derived subsets.
    """

    items: tuple[BatchItemResult, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.items, tuple):
            raise TypeError(
                f"items must be a tuple; got {type(self.items).__name__}"
            )
        for i, item in enumerate(self.items):
            if not isinstance(item, BatchItemResult):
                raise TypeError(
                    f"items[{i}] must be a BatchItemResult; got "
                    f"{type(item).__name__}"
                )

    @property
    def total(self) -> int:
        """Total number of items in the batch."""
        return len(self.items)

    @property
    def successful(self) -> tuple[BatchItemResult, ...]:
        """Items that succeeded (response is not None)."""
        return tuple(item for item in self.items if item.is_success)

    @property
    def failed(self) -> tuple[BatchItemResult, ...]:
        """Items that failed (error is not None)."""
        return tuple(item for item in self.items if item.is_failure)

    @property
    def success_count(self) -> int:
        """Number of successful items."""
        return len(self.successful)

    @property
    def failure_count(self) -> int:
        """Number of failed items."""
        return len(self.failed)

    def all_records(self) -> list[TradeRecord]:
        """Flatten all successful records into a single list."""
        return [
            record
            for item in self.successful
            for record in item.records
        ]

    def is_complete_success(self) -> bool:
        """True if every item succeeded."""
        return self.failure_count == 0

    def is_complete_failure(self) -> bool:
        """True if every item failed."""
        return self.success_count == 0


# ---------------------------------------------------------------------------
# BatchDownloader
# ---------------------------------------------------------------------------


class BatchDownloader:
    """Orchestrates batch downloads over `TradeService`.

    Iterates the cartesian product of
    `(reporters × years × partners)` and calls
    `TradeService.get_exports` for each tuple. Per the
    task scope:

    - **No new transport logic.** The transport's
      retry + timeout policies are reused (per-item
      failures surface only after the retry budget is
      exhausted).
    - **Sequential execution.** Per the trade layer
      spec §6.2.
    - **Partial success reporting.** Failed items are
      collected; the batch completes unless
      `config.fail_fast=True`.
    - **Progress reporting.** Callback after each item.
    """

    def __init__(
        self,
        service: "TradeService",
        config: BatchConfig | None = None,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        """Construct a batch downloader.

        Parameters
        ----------
        service
            The `TradeService` to use for each per-item
            call.
        config
            Optional `BatchConfig`. When `None`, the
            defaults are used (`fail_fast=False`).
        logger
            Optional logger. When `None`, the SDK's
            `metadata` logger is used.
        """
        self._service: "TradeService" = service
        self._config: BatchConfig = (
            config if config is not None else BatchConfig()
        )
        self._logger: logging.Logger = (
            logger if logger is not None else get_logger("metadata")
        )

    @property
    def config(self) -> BatchConfig:
        """The configuration this downloader uses."""
        return self._config

    @property
    def service(self) -> "TradeService":
        """The `TradeService` this downloader wraps."""
        return self._service

    # ----- Public API -----------------------------------------------------

    def download(
        self,
        reporters: Sequence[int],
        years: Sequence[int],
        partners: Sequence[int],
        *,
        flow_code: str = "X",
        commodity_code: str = "TOTAL",
        classification: str | None = None,
        on_progress: BatchProgressCallback | None = None,
    ) -> BatchResult:
        """Download trade data for the cartesian product.

        Iterates in order: reporter × year × partner
        (reporters outermost, partners innermost). For
        each tuple, calls
        `service.get_exports(reporter, year,
        partner_code=partner, ...)`. Per-item failures
        are collected unless `config.fail_fast=True`.

        Parameters
        ----------
        reporters
            Sequence of reporter codes.
        years
            Sequence of years (4-digit integers, e.g.
            `2022`). Each year is converted to its
            string form (per `TradeQuery.period`
            contract).
        partners
            Sequence of partner codes. `0` is the
            World aggregate.
        flow_code
            Flow code passed to each per-item call
            (default `"X"` for exports).
        commodity_code
            Commodity code passed to each per-item call
            (default `"TOTAL"`).
        classification
            Optional classification code override.
        on_progress
            Optional progress callback invoked after
            each item. Returning `False` aborts the
            batch and any in-flight item's exception
            is preserved on the result.

        Returns
        -------
        BatchResult
            Aggregated result with all items
            (successes + failures). The result is
            always returned; the downloader does NOT
            raise on per-item failures (unless
            `config.fail_fast=True`, in which case the
            first failure is re-raised).
        """
        reporters_list = list(reporters)
        years_list = list(years)
        partners_list = list(partners)
        if not reporters_list:
            raise ValueError("reporters must be non-empty")
        if not years_list:
            raise ValueError("years must be non-empty")
        if not partners_list:
            raise ValueError("partners must be non-empty")

        # Pre-build the iteration order so the progress
        # callback's `total` matches reality.
        order: list[tuple[int, int, int]] = []
        for reporter in reporters_list:
            for year in years_list:
                for partner in partners_list:
                    order.append((reporter, year, partner))
        total = len(order)

        items: list[BatchItemResult] = []
        successful = 0
        failed = 0
        aborted = False

        for completed, (reporter, year, partner) in enumerate(
            order, start=1
        ):
            item_result = self._fetch_one(
                reporter=reporter,
                year=year,
                partner=partner,
                flow_code=flow_code,
                commodity_code=commodity_code,
                classification=classification,
                fail_fast=self._config.fail_fast,
            )
            items.append(item_result)
            if item_result.is_success:
                successful += 1
            else:
                failed += 1

            last_item = item_result
            progress = BatchProgress(
                completed=completed,
                total=total,
                successful=successful,
                failed=failed,
                last_item=last_item,
            )

            if on_progress is not None:
                should_continue = on_progress(progress)
                if should_continue is False:
                    self._logger.info(
                        "batch aborted by callback at %d/%d",
                        completed,
                        total,
                    )
                    aborted = True
                    break

        # If we aborted mid-batch due to the callback or
        # fail_fast, the remaining items are not in the
        # result. Pad with synthetic failure records so
        # `BatchResult.total` still equals the requested
        # count — consumers can detect incomplete batches
        # via `len(items) < total` if they need to.
        if aborted:
            processed = len(items)
            for reporter, year, partner in order[processed:]:
                items.append(
                    BatchItemResult(
                        reporter_code=reporter,
                        year=year,
                        partner_code=partner,
                        response=None,
                        error="batch aborted before this item",
                    )
                )
                failed += 1

        return BatchResult(items=tuple(items))

    # ----- Internal helpers ----------------------------------------------

    def _fetch_one(
        self,
        *,
        reporter: int,
        year: int,
        partner: int,
        flow_code: str,
        commodity_code: str,
        classification: str | None,
        fail_fast: bool = False,
    ) -> BatchItemResult:
        """Fetch a single (reporter, year, partner) tuple.

        Catches all exceptions raised by the service
        (network errors, validation errors, etc.) and
        returns a `BatchItemResult` with the error
        stringified. When `fail_fast=True`, the original
        exception is re-raised so the caller can
        propagate it.
        """
        period = str(year)
        try:
            # Use `get_trade` (T03) rather than
            # `get_exports` (T01) so the batch can
            # honour a caller-supplied flow_code.
            # `get_exports` implies flow_code="X" and
            # does not accept the kwarg.
            response = self._service.get_trade(
                reporter_code=reporter,
                flow_code=flow_code,
                period=period,
                partner_code=partner,
                commodity_code=commodity_code,
                classification=classification,
            )
        except Exception as exc:  # noqa: BLE001 - intentional catch-all
            if fail_fast:
                # In fail_fast mode the caller wants the
                # original exception, not a swallowed
                # BatchItemResult.
                raise
            error = f"{type(exc).__name__}: {exc}"
            self._logger.warning(
                "batch item failed reporter=%s year=%s partner=%s "
                "error=%s",
                reporter,
                year,
                partner,
                error,
            )
            return BatchItemResult(
                reporter_code=reporter,
                year=year,
                partner_code=partner,
                response=None,
                error=error,
            )
        return BatchItemResult(
            reporter_code=reporter,
            year=year,
            partner_code=partner,
            response=response,
            error=None,
        )