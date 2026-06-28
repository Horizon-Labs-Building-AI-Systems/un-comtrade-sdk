"""Extract layer for the ETL pipeline.

The extract layer is the **first concrete stage** of
the ETL pipeline (per `011_ETL_SPECIFICATION.md` §2 +
§12). It consumes the SDK's high-level services
(`MetadataService`, `TradeService`,
`BatchDownloader`) and produces the raw records that
flow into the validate / transform / export stages.

Per the P4-002 task scope:

- **Reuses** `MetadataService`, `TradeService`,
  `BatchDownloader`. No new HTTP, no new parsing, no
  new validation.
- **No transformation** — extractors return raw
  records as they came out of the SDK (canonical
  metadata models, `TradeRecord` instances, or
  `BatchResult.all_records`). The validate + transform
  stages are responsible for any field mapping or
  normalisation.
- **No normalisation** — the canonical records are
  already in their final shape (per P2-003 trade
  models); no further normalisation is applied here.
- **No persistence** — extractors return in-memory
  records only.

Three extractors are exposed:

1. **`MetadataExtractor`** — wraps a single
   `MetadataService` method (e.g. `get_countries`,
   `get_partners`) and returns the canonical metadata
   models.
2. **`TradeExtractor`** — wraps a single
   `TradeService` method (e.g. `get_exports`,
   `get_trade_by_hs`) and returns the canonical
   `TradeRecord` list.
3. **`BatchExtractor`** — wraps a `BatchDownloader`
   `download(...)` call and returns the union of all
   successful records from the resulting `BatchResult`.

Each extractor conforms to the `ExtractStage`
protocol defined in `un_comtrade.etl`:

- `name` (str): the stage identifier within a
  pipeline.
- `kind` (`StageKind`): always `StageKind.EXTRACT`.
- `__call__(source, context) -> list[record]`: invoke
  the wrapped SDK call and return the raw records.

The `source` argument is accepted for protocol
compatibility with `ETLPipeline.run(source)`. Two
modes are supported:

- **Configured mode (default)** — the source argument
  is ignored; the extractor uses its constructor-
  supplied method + kwargs.
- **Callable source** — when `source` is a callable
  `(service) -> response`, the extractor invokes it
  with its SDK service and uses the result. This lets
  callers override the extraction at run time without
  rebuilding the extractor.
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Sequence,
)

from .etl import ExtractStage, PipelineContext, StageKind
from .logging import get_logger


if TYPE_CHECKING:
    from .batch import BatchDownloader, BatchResult
    from .metadata import MetadataService
    from .trade import TradeResponse, TradeService


__all__ = [
    "BatchExtractor",
    "MetadataExtractor",
    "TradeExtractor",
]


_logger = get_logger("lifecycle")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coerce_records(result: Any) -> list[Any]:
    """Coerce a SDK call result into a list of records.

    - `TradeResponse` → `list(response.records)`.
    - `BatchResult` → `list(result.all_records)`.
    - list-like (already iterable of records) →
      `list(result)`.
    - Anything else → wrapped in a single-element list.

    The helper is intentionally permissive so callers
    can wrap any SDK method that returns either a
    `TradeResponse`, a `BatchResult`, a list, or a
    tuple of records.
    """
    if result is None:
        return []
    # TradeResponse — has `.records` attribute (list of
    # canonical TradeRecord instances per P2-006).
    records = getattr(result, "records", None)
    if isinstance(records, list):
        return list(records)
    # BatchResult — has `.all_records` (property or
    # method). Resolve via attribute access (which
    # invokes the descriptor protocol for properties).
    all_records = getattr(result, "all_records", None)
    if isinstance(all_records, (list, tuple)):
        return list(all_records)
    if callable(all_records) and not isinstance(all_records, property):
        # It's a zero-arg method, not a property.
        return list(all_records())
    # Already a list / tuple.
    if isinstance(result, (list, tuple)):
        return list(result)
    # Single record-like value.
    return [result]


# ---------------------------------------------------------------------------
# MetadataExtractor
# ---------------------------------------------------------------------------


class MetadataExtractor:
    """Extract metadata reference catalogues via MetadataService.

    Wraps a single `MetadataService` method (e.g.
    `get_countries`, `get_partners`, `get_hs_codes`)
    and returns the canonical metadata models.

    Usage::

        extractor = MetadataExtractor(
            metadata_service=service,
            method_name="get_countries",
        )
        records = extractor(source=None, context=ctx)

        # With kwargs (e.g. for `get_hs_codes(edition=...)`)
        extractor = MetadataExtractor(
            metadata_service=service,
            method_name="get_hs_codes",
            edition="H6",
        )

    Plug into an `ETLPipeline` as a stage via
    `StageSpec(name=extractor.name, kind=StageKind.EXTRACT,
    factory=lambda ctx: extractor)`.
    """

    def __init__(
        self,
        metadata_service: "MetadataService",
        method_name: str,
        **method_kwargs: Any,
    ) -> None:
        if not isinstance(method_name, str) or not method_name.strip():
            raise ValueError(
                f"method_name must be a non-empty string; got "
                f"{method_name!r}"
            )
        if not hasattr(metadata_service, method_name):
            raise ValueError(
                f"MetadataService has no method {method_name!r}"
            )
        if not callable(getattr(metadata_service, method_name)):
            raise ValueError(
                f"MetadataService.{method_name!r} is not callable"
            )
        self._metadata_service = metadata_service
        self._method_name = method_name
        self._method_kwargs = dict(method_kwargs)

    @property
    def metadata_service(self) -> "MetadataService":
        """The wrapped `MetadataService`."""
        return self._metadata_service

    @property
    def method_name(self) -> str:
        """The wrapped `MetadataService` method name."""
        return self._method_name

    @property
    def method_kwargs(self) -> dict[str, Any]:
        """The kwargs forwarded to the wrapped method
        (a copy; mutating it does NOT affect the extractor)."""
        return dict(self._method_kwargs)

    @property
    def name(self) -> str:
        """Stage identifier (e.g. `extract_metadata_get_countries`)."""
        return f"extract_metadata_{self._method_name}"

    @property
    def kind(self) -> StageKind:
        """Always `StageKind.EXTRACT`."""
        return StageKind.EXTRACT

    def __call__(
        self,
        source: Any,
        context: PipelineContext,
    ) -> list[Any]:
        """Invoke the wrapped `MetadataService` method.

        `source` modes:
        - `callable` → invoked as `source(metadata_service)`
          and the result is coerced into a list.
        - anything else (incl. `None`) → the constructor-
          supplied method + kwargs are used.

        Records-out is recorded on the `PipelineContext`.
        """
        if callable(source):
            result = source(self._metadata_service)
        else:
            method = getattr(self._metadata_service, self._method_name)
            result = method(**self._method_kwargs)

        records = _coerce_records(result)
        context.records_in += len(records)
        context.records_out += len(records)
        _logger.debug(
            "MetadataExtractor %s produced %d records",
            self._method_name,
            len(records),
        )
        return records

    def __repr__(self) -> str:
        return (
            f"MetadataExtractor(method_name={self._method_name!r}, "
            f"kwargs={self._method_kwargs!r})"
        )


# ---------------------------------------------------------------------------
# TradeExtractor
# ---------------------------------------------------------------------------


class TradeExtractor:
    """Extract trade data via TradeService.

    Wraps a single `TradeService` method (e.g.
    `get_exports`, `get_trade_by_hs`, `get_tariffline`)
    and returns the canonical `TradeRecord` list.

    Usage::

        extractor = TradeExtractor(
            trade_service=service,
            method_name="get_exports",
            reporter_code=699,
            period="2022",
        )
        records = extractor(source=None, context=ctx)

    Plug into an `ETLPipeline` as a stage via
    `StageSpec(name=extractor.name, kind=StageKind.EXTRACT,
    factory=lambda ctx: extractor)`.
    """

    def __init__(
        self,
        trade_service: "TradeService",
        method_name: str,
        **method_kwargs: Any,
    ) -> None:
        if not isinstance(method_name, str) or not method_name.strip():
            raise ValueError(
                f"method_name must be a non-empty string; got "
                f"{method_name!r}"
            )
        if not hasattr(trade_service, method_name):
            raise ValueError(
                f"TradeService has no method {method_name!r}"
            )
        if not callable(getattr(trade_service, method_name)):
            raise ValueError(
                f"TradeService.{method_name!r} is not callable"
            )
        self._trade_service = trade_service
        self._method_name = method_name
        self._method_kwargs = dict(method_kwargs)

    @property
    def trade_service(self) -> "TradeService":
        """The wrapped `TradeService`."""
        return self._trade_service

    @property
    def method_name(self) -> str:
        """The wrapped `TradeService` method name."""
        return self._method_name

    @property
    def method_kwargs(self) -> dict[str, Any]:
        """The kwargs forwarded to the wrapped method."""
        return dict(self._method_kwargs)

    @property
    def name(self) -> str:
        """Stage identifier (e.g. `extract_trade_get_exports`)."""
        return f"extract_trade_{self._method_name}"

    @property
    def kind(self) -> StageKind:
        """Always `StageKind.EXTRACT`."""
        return StageKind.EXTRACT

    def __call__(
        self,
        source: Any,
        context: PipelineContext,
    ) -> list[Any]:
        """Invoke the wrapped `TradeService` method.

        `source` modes:
        - `callable` → invoked as `source(trade_service)`
          and the result (typically a `TradeResponse`)
          is coerced into a list of records.
        - anything else (incl. `None`) → the constructor-
          supplied method + kwargs are used.

        Records-out is recorded on the `PipelineContext`.
        """
        if callable(source):
            result = source(self._trade_service)
        else:
            method = getattr(self._trade_service, self._method_name)
            result = method(**self._method_kwargs)

        records = _coerce_records(result)
        context.records_in += len(records)
        context.records_out += len(records)
        _logger.debug(
            "TradeExtractor %s produced %d records",
            self._method_name,
            len(records),
        )
        return records

    def __repr__(self) -> str:
        return (
            f"TradeExtractor(method_name={self._method_name!r}, "
            f"kwargs={self._method_kwargs!r})"
        )


# ---------------------------------------------------------------------------
# BatchExtractor
# ---------------------------------------------------------------------------


class BatchExtractor:
    """Extract batch trade data via BatchDownloader.

    Wraps a single `BatchDownloader.download(...)` call
    and returns the union of all successful records from
    the resulting `BatchResult`. Failed items are NOT
    re-raised by the extractor (the batch downloader's
    `fail_fast` already controls that behaviour); the
    extractor's contract is "return what we got, log
    what we lost".

    Parameters
    ----------
    batch_downloader
        The `BatchDownloader` to drive.
    reporters
        Sequence of reporter codes (e.g. `[699, 156]`).
    years
        Sequence of years (e.g. `[2020, 2021, 2022]`).
    partners
        Sequence of partner codes (e.g. `[0, 156, 840]`).
    flow_code
        Flow code passed to the batch downloader
        (default `"X"`).
    commodity_code
        Commodity code passed to the batch downloader
        (default `"TOTAL"`).
    classification
        Optional classification code override.
    on_progress
        Optional progress callback forwarded to the
        batch downloader.

    Usage::

        extractor = BatchExtractor(
            batch_downloader=downloader,
            reporters=[699],
            years=[2020, 2021, 2022],
            partners=[0],
        )
        records = extractor(source=None, context=ctx)

    Plug into an `ETLPipeline` as a stage via
    `StageSpec(name=extractor.name, kind=StageKind.EXTRACT,
    factory=lambda ctx: extractor)`.
    """

    def __init__(
        self,
        batch_downloader: "BatchDownloader",
        reporters: Sequence[int],
        years: Sequence[int],
        partners: Sequence[int],
        *,
        flow_code: str = "X",
        commodity_code: str = "TOTAL",
        classification: str | None = None,
        on_progress: Callable[..., bool | None] | None = None,
    ) -> None:
        self._batch_downloader = batch_downloader
        # Normalise sequences to tuples (frozen-friendly).
        self._reporters: tuple[int, ...] = tuple(reporters)
        self._years: tuple[int, ...] = tuple(years)
        self._partners: tuple[int, ...] = tuple(partners)
        self._flow_code = flow_code
        self._commodity_code = commodity_code
        self._classification = classification
        self._on_progress = on_progress

    @property
    def batch_downloader(self) -> "BatchDownloader":
        """The wrapped `BatchDownloader`."""
        return self._batch_downloader

    @property
    def reporters(self) -> tuple[int, ...]:
        """Reporter codes (tuple, frozen)."""
        return self._reporters

    @property
    def years(self) -> tuple[int, ...]:
        """Years (tuple, frozen)."""
        return self._years

    @property
    def partners(self) -> tuple[int, ...]:
        """Partner codes (tuple, frozen)."""
        return self._partners

    @property
    def flow_code(self) -> str:
        """Flow code passed to the batch downloader."""
        return self._flow_code

    @property
    def commodity_code(self) -> str:
        """Commodity code passed to the batch downloader."""
        return self._commodity_code

    @property
    def classification(self) -> str | None:
        """Optional classification override."""
        return self._classification

    @property
    def on_progress(self) -> Callable[..., bool | None] | None:
        """Optional progress callback."""
        return self._on_progress

    @property
    def name(self) -> str:
        """Stage identifier (`extract_batch`)."""
        return "extract_batch"

    @property
    def kind(self) -> StageKind:
        """Always `StageKind.EXTRACT`."""
        return StageKind.EXTRACT

    def __call__(
        self,
        source: Any,
        context: PipelineContext,
    ) -> list[Any]:
        """Invoke `BatchDownloader.download(...)`.

        `source` modes:
        - `callable` → invoked as `source(batch_downloader)`
          and the result (a `BatchResult`) is coerced
          into a list of records.
        - anything else (incl. `None`) → the constructor-
          supplied reporters / years / partners are
          used.

        Failed items are recorded as a warning on the
        `PipelineContext` (the extractor does NOT raise;
        the batch downloader's `fail_fast` already
        controls that behaviour).
        """
        if callable(source):
            result = source(self._batch_downloader)
        else:
            kwargs: dict[str, Any] = {
                "reporters": self._reporters,
                "years": self._years,
                "partners": self._partners,
                "flow_code": self._flow_code,
                "commodity_code": self._commodity_code,
            }
            if self._classification is not None:
                kwargs["classification"] = self._classification
            if self._on_progress is not None:
                kwargs["on_progress"] = self._on_progress
            result = self._batch_downloader.download(**kwargs)

        records = _coerce_records(result)

        # Surface failed items as a warning.
        failed = getattr(result, "failed", None)
        if failed:
            failed_count = (
                len(failed) if hasattr(failed, "__len__") else None
            )
            if failed_count:
                context.warn(
                    f"BatchExtractor: {failed_count} item(s) failed"
                )

        context.records_in += len(records)
        context.records_out += len(records)
        _logger.debug(
            "BatchExtractor produced %d records (reporters=%d, "
            "years=%d, partners=%d)",
            len(records),
            len(self._reporters),
            len(self._years),
            len(self._partners),
        )
        return records

    def __repr__(self) -> str:
        return (
            f"BatchExtractor(reporters={self._reporters!r}, "
            f"years={self._years!r}, partners={self._partners!r})"
        )


#: Default names used by the module's public surface.
EXTRACTOR_NAMES: frozenset[str] = frozenset(
    {
        "MetadataExtractor",
        "TradeExtractor",
        "BatchExtractor",
    }
)


# ---------------------------------------------------------------------------
# TYPE_CHECKING block (resolved at runtime via __getattr__)
# ---------------------------------------------------------------------------