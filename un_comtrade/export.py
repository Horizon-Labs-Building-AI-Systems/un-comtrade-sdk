"""Export framework for the ETL pipeline.

The export framework is the **abstraction layer** for
the export stage of the ETL pipeline (per
`011_ETL_SPECIFICATION.md` §9 + §12 and
`012_STORAGE_SPECIFICATION.md` §3 + §10). It defines:

- **`ExportFormat`** — the four documented output
  formats (CSV, JSON, Parquet, DuckDB) plus the
  default `CANONICAL` (in-memory Python objects).
- **`Exporter`** — the protocol every concrete
  exporter implements.
- **`ExportResult`** — the outcome of an export.
- **Placeholder exporters** — abstract base classes
  for CSV / JSON / Parquet / DuckDB that raise
  `NotImplementedError`. Concrete implementations
  land in later tasks.
- **`ExportStage`** — implements the
  `ExportStage` protocol from `un_comtrade.etl`,
  dispatches a `CanonicalDataset` to the right
  exporter by format, and emits an `ExportResult`.
- **`ExporterRegistry`** — plug-in registry that
  maps an `ExportFormat` to an `Exporter`
  instance. Consumers register their own
  exporters; the SDK ships with placeholders.

Per the P4-004 task scope:

- **Interfaces only** for CSV / JSON / Parquet /
  DuckDB. No actual storage engines (no `pandas`,
  no `pyarrow`, no `duckdb` calls). The four
  placeholders raise `NotImplementedError("...")`
  so consumers know the SDK has the hook but the
  engine lands in a later task.
- The `CANONICAL` exporter IS implemented (it just
  returns the records in-memory; no engine needed).
- Plugs into `ETLPipeline` as the `EXPORT` stage.
- Composes the transformation layer's
  `CanonicalDataset` (per P4-003).

The framework is intentionally thin: it provides
the contract, the registry, the placeholder
classes, and the dispatcher. Concrete engines are
out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Mapping,
    Protocol,
    runtime_checkable,
)

from .etl import ExportStage, PipelineContext, StageKind
from .exceptions import ComtradeError
from .logging import get_logger


if TYPE_CHECKING:
    from .transform import CanonicalDataset


__all__ = [
    "CANONICAL_FORMAT",
    "CSVExporter",
    "DuckDBExporter",
    "ExportError",
    "ExportFormat",
    "ExportOptions",
    "ExportResult",
    "ExportStageImpl",
    "Exporter",
    "ExporterRegistry",
    "JSONExporter",
    "ParquetExporter",
]


_logger = get_logger("lifecycle")


#: The default export format (canonical Python objects;
#: no engine needed).
CANONICAL_FORMAT: str = "canonical"


# ---------------------------------------------------------------------------
# ExportFormat
# ---------------------------------------------------------------------------


class ExportFormat(str, Enum):
    """The documented output formats of the export stage.

    Per `012_STORAGE_SPECIFICATION.md` §3 the SDK
    supports four storage targets (JSON, CSV, Parquet,
    DuckDB) plus the in-memory `CANONICAL` shape (the
    default).

    The MVP does NOT implement CSV / JSON / Parquet /
    DuckDB engines — those land in later tasks. The
    `CANONICAL` format IS implemented (returns the
    records in-memory; no engine needed).
    """

    CANONICAL = CANONICAL_FORMAT
    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"
    DUCKDB = "duckdb"

    @property
    def file_extension(self) -> str:
        """Default file extension for this format.

        `CANONICAL` has no file (it's in-memory) and
        returns an empty string.
        """
        return {
            ExportFormat.CANONICAL: "",
            ExportFormat.CSV: ".csv",
            ExportFormat.JSON: ".json",
            ExportFormat.PARQUET: ".parquet",
            ExportFormat.DUCKDB: ".duckdb",
        }[self]

    @property
    def is_engine(self) -> bool:
        """`True` when this format requires an actual
        storage engine (CSV / JSON / Parquet / DuckDB).

        `CANONICAL` returns `False` because it has no
        engine; it's the in-memory default.
        """
        return self is not ExportFormat.CANONICAL


# ---------------------------------------------------------------------------
# ExportError + ExportResult + ExportOptions
# ---------------------------------------------------------------------------


class ExportError(ComtradeError):
    """Raised when an export operation fails.

    Distinct from the `NotImplementedError` raised by
    the placeholder exporters (CSV / JSON / Parquet /
    DuckDB): an `ExportError` signals that a concrete
    exporter was used but failed (e.g. the destination
    was unwritable, the schema was incompatible, etc.).
    """


@dataclass(frozen=True)
class ExportOptions:
    """Per-export options (key/value mapping).

    Concrete exporters read options they understand
    and ignore the rest. Documented option keys:

    - `destination` (str | Path) — the destination
      URI / file path / database identifier.
    - `compression` (str) — for Parquet: `"snappy"`
      (default), `"gzip"`, `"brotli"`, `"zstd"`.
    - `partition_by` (list[str]) — for Parquet /
      DuckDB: partition columns.
    - `table_name` (str) — for DuckDB: target table
      name (default `"trade_records"`).
    - `mode` (str) — for DuckDB: `"append"` (default)
      or `"replace"`.
    - `indent` (int) — for JSON: pretty-print indent
      level (default `None`, i.e. compact).
    """

    values: Mapping[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)


@dataclass(frozen=True)
class ExportResult:
    """Outcome of an export operation.

    Parameters
    ----------
    format
        The export format that produced this result.
    destination
        The destination URI / file path / database
        identifier. For `CANONICAL`, this is
        `"<in-memory>"`.
    record_count
        Number of records exported.
    byte_size
        Number of bytes written (for file-based
        formats); `None` for `CANONICAL`.
    exported_at
        UTC timestamp the export completed.
    metadata
        Free-form metadata map (per-exporter
        additions, e.g. partition paths, file
        sizes, table names).
    """

    format: ExportFormat
    destination: str
    record_count: int
    byte_size: int | None
    exported_at: datetime
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def empty(self) -> bool:
        """True when no records were exported."""
        return self.record_count == 0


# ---------------------------------------------------------------------------
# Exporter Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class Exporter(Protocol):
    """Protocol every concrete exporter implements.

    An exporter:
    - Knows its `format`.
    - Validates the destination is acceptable.
    - Writes the dataset's records to the destination.
    - Returns an `ExportResult` describing what was
      produced.

    Concrete exporters land in later tasks. The SDK
    ships with placeholder implementations that raise
    `NotImplementedError` so consumers know the hook
    is reserved.
    """

    format: ExportFormat

    def export(
        self,
        dataset: "CanonicalDataset",
        options: ExportOptions | None = None,
    ) -> ExportResult: ...


# ---------------------------------------------------------------------------
# Canonical Exporter (in-memory; the only one
# implemented in this task)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CanonicalExporter:
    """The default exporter: emit canonical Python objects.

    No engine is required. The exporter returns the
    records in-memory along with provenance metadata.
    This is the default `ExportStageImpl.format` —
    callers that don't override format get
    `CANONICAL`.

    Implements the `Exporter` protocol.
    """

    format: ExportFormat = ExportFormat.CANONICAL

    def export(
        self,
        dataset: "CanonicalDataset",
        options: ExportOptions | None = None,
    ) -> ExportResult:
        """Return the canonical records in-memory.

        No actual storage engine is invoked.
        `byte_size` is `None` (no bytes written).
        """
        opts = options or ExportOptions()
        destination = opts.get("destination", "<in-memory>")
        return ExportResult(
            format=self.format,
            destination=str(destination),
            record_count=dataset.count,
            byte_size=None,
            exported_at=datetime.now(timezone.utc),
            metadata={
                "schema_version": dataset.schema_version,
                "parser_name": dataset.parser_name,
                "skipped": dataset.skipped,
                "duplicates_removed": dataset.duplicates_removed,
                "source_count": dataset.source_count,
            },
        )


# ---------------------------------------------------------------------------
# Placeholder exporters (interfaces only; no engines)
# ---------------------------------------------------------------------------


class _PlaceholderExporter:
    """Base for the four engine-backed exporters.

    Subclasses MUST set `format`. The `export` method
    raises `NotImplementedError` — concrete engines
    land in later tasks.

    This is NOT an ABC (`abc.ABC`) because the four
    placeholders share a single `export` implementation
    (the raise); an ABC would require each subclass to
    override `export` with its own raise, duplicating
    the message. A regular base class keeps the
    behaviour DRY.
    """

    format: ExportFormat  # subclasses set this

    def export(
        self,
        dataset: "CanonicalDataset",
        options: ExportOptions | None = None,
    ) -> ExportResult:
        """Engine-specific export — implemented in a
        later task. The MVP raises `NotImplementedError`
        so consumers know the hook is reserved but the
        engine has not landed yet."""
        raise NotImplementedError(
            f"{type(self).__name__}.export is not yet implemented. "
            f"Engine for {self.format.value!r} lands in a later task."
        )


@dataclass(frozen=True)
class CSVExporter(_PlaceholderExporter):
    """Placeholder CSV exporter.

    The MVP raises `NotImplementedError` from `export`.
    The engine (Python `csv` module or `pandas.to_csv`)
    lands in a later task.
    """

    format: ExportFormat = ExportFormat.CSV


@dataclass(frozen=True)
class JSONExporter(_PlaceholderExporter):
    """Placeholder JSON exporter.

    The MVP raises `NotImplementedError` from `export`.
    The engine (Python `json` module or
    `pandas.to_json`) lands in a later task.
    """

    format: ExportFormat = ExportFormat.JSON


@dataclass(frozen=True)
class ParquetExporter(_PlaceholderExporter):
    """Placeholder Parquet exporter.

    The MVP raises `NotImplementedError` from `export`.
    The engine (PyArrow or pandas+pyarrow) lands in a
    later task.
    """

    format: ExportFormat = ExportFormat.PARQUET


@dataclass(frozen=True)
class DuckDBExporter(_PlaceholderExporter):
    """Placeholder DuckDB exporter.

    The MVP raises `NotImplementedError` from `export`.
    The engine (DuckDB Python client) lands in a later
    task.
    """

    format: ExportFormat = ExportFormat.DUCKDB


# ---------------------------------------------------------------------------
# ExporterRegistry
# ---------------------------------------------------------------------------


class ExporterRegistry:
    """Registry mapping `ExportFormat` → `Exporter`.

    The SDK ships with five built-in registrations:

    - `ExportFormat.CANONICAL` → `CanonicalExporter`
      (functional).
    - `ExportFormat.CSV` → `CSVExporter` (placeholder).
    - `ExportFormat.JSON` → `JSONExporter` (placeholder).
    - `ExportFormat.PARQUET` → `ParquetExporter`
      (placeholder).
    - `ExportFormat.DUCKDB` → `DuckDBExporter`
      (placeholder).

    Consumers can:

    - `register(format, exporter)` to install a
      concrete exporter over a placeholder.
    - `register(factory)` to install a custom exporter
      for a new format.
    - `get(format)` to look up the registered exporter.

    The registry is a plain object; it does NOT use a
    global singleton. Callers can hold their own
    registry and pass it to `ExportStageImpl`.
    """

    def __init__(
        self,
        *,
        exporters: Mapping[ExportFormat, "Exporter"] | None = None,
    ) -> None:
        self._exporters: dict[ExportFormat, Exporter] = {}
        # Register the SDK-shipped defaults.
        self._register_defaults()
        # Caller-supplied overrides take precedence.
        if exporters:
            for fmt, exporter in exporters.items():
                self.register(fmt, exporter)

    def _register_defaults(self) -> None:
        """Register the SDK's built-in exporters."""
        self._exporters[ExportFormat.CANONICAL] = CanonicalExporter()
        self._exporters[ExportFormat.CSV] = CSVExporter()
        self._exporters[ExportFormat.JSON] = JSONExporter()
        self._exporters[ExportFormat.PARQUET] = ParquetExporter()
        self._exporters[ExportFormat.DUCKDB] = DuckDBExporter()

    def register(
        self,
        fmt: ExportFormat,
        exporter: "Exporter",
    ) -> None:
        """Register (or replace) the exporter for `fmt`."""
        if not isinstance(fmt, ExportFormat):
            raise TypeError(
                f"fmt must be ExportFormat; got {type(fmt).__name__}"
            )
        if not hasattr(exporter, "format") or not callable(
            getattr(exporter, "export", None)
        ):
            raise TypeError(
                f"exporter must have a 'format' attribute and an "
                f"'export' callable; got {type(exporter).__name__}"
            )
        self._exporters[fmt] = exporter

    def get(self, fmt: ExportFormat) -> "Exporter":
        """Return the registered exporter for `fmt`.

        Raises `ExportError` if no exporter is
        registered for the requested format.
        """
        try:
            return self._exporters[fmt]
        except KeyError as exc:
            raise ExportError(
                f"No exporter registered for format {fmt.value!r}"
            ) from exc

    def supported_formats(self) -> tuple[ExportFormat, ...]:
        """Return the formats this registry knows about."""
        return tuple(self._exporters.keys())

    def unregister(self, fmt: ExportFormat) -> None:
        """Remove the exporter for `fmt`.

        Raises `ExportError` if no exporter is
        registered for `fmt`.
        """
        if fmt not in self._exporters:
            raise ExportError(
                f"No exporter registered for format {fmt.value!r}"
            )
        del self._exporters[fmt]


# ---------------------------------------------------------------------------
# ExportStageImpl
# ---------------------------------------------------------------------------


class ExportStageImpl:
    """The export stage for an `ETLPipeline`.

    Implements the `ExportStage` protocol from
    `un_comtrade.etl` (`name` + `kind=StageKind.EXPORT` +
    callable).

    On `__call__(source, context)`:
    1. Validates the source is a `CanonicalDataset`.
    2. Looks up the exporter for `format` via the
       registry (default registry if none supplied).
    3. Invokes the exporter's `export(dataset, options)`
       method.
    4. Returns the resulting `ExportResult` so the
       pipeline's caller can inspect it.
    5. Records the export on the `PipelineContext`.

    Construction::

        stage = ExportStageImpl(format=ExportFormat.CANONICAL)
        # OR with a custom registry:
        stage = ExportStageImpl(
            format=ExportFormat.PARQUET,
            registry=my_registry,
        )
        # OR with per-call options:
        stage = ExportStageImpl(
            format=ExportFormat.PARQUET,
            options=ExportOptions(
                values={"destination": "/tmp/trade.parquet"}
            ),
        )

    Plug into an `ETLPipeline`::

        pipeline = ETLPipeline(
            name="trade_ingest",
            stages=(
                StageSpec(name="extract", ...),
                StageSpec(name="transform", ...),
                StageSpec(
                    name="export",
                    kind=StageKind.EXPORT,
                    factory=lambda ctx: ExportStageImpl(
                        format=ExportFormat.CANONICAL
                    ),
                ),
            ),
        )
    """

    def __init__(
        self,
        format: ExportFormat = ExportFormat.CANONICAL,
        *,
        registry: ExporterRegistry | None = None,
        options: ExportOptions | None = None,
    ) -> None:
        if not isinstance(format, ExportFormat):
            raise TypeError(
                f"format must be ExportFormat; got "
                f"{type(format).__name__}"
            )
        self._format = format
        self._registry = registry if registry is not None else ExporterRegistry()
        self._options = options

    @property
    def format(self) -> ExportFormat:
        """The export format this stage dispatches to."""
        return self._format

    @property
    def registry(self) -> ExporterRegistry:
        """The exporter registry this stage uses."""
        return self._registry

    @property
    def options(self) -> ExportOptions | None:
        """The default options for this stage."""
        return self._options

    @property
    def name(self) -> str:
        """Stage identifier (`export_canonical` /
        `export_csv` / etc.)."""
        return f"export_{self._format.value}"

    @property
    def kind(self) -> StageKind:
        """Always `StageKind.EXPORT`."""
        return StageKind.EXPORT

    def __call__(
        self,
        source: Any,
        context: PipelineContext,
    ) -> ExportResult:
        """Dispatch the source dataset to the configured
        exporter.

        Parameters
        ----------
        source
            A `CanonicalDataset` (per the P4-003
            transformation layer contract).
        context
            The shared `PipelineContext`. The export
            stage records `records_out` (the dataset
            count) and any errors.

        Returns
        -------
        ExportResult
            The result of the export.

        Raises
        ------
        ExportError
            If the source is not a `CanonicalDataset`
            or no exporter is registered for the
            configured format.
        """
        # Local import to avoid circular dependency
        # (transform.py imports models; we import
        # transform.py here for type checks).
        from .transform import CanonicalDataset

        if not isinstance(source, CanonicalDataset):
            raise ExportError(
                f"ExportStageImpl source must be a CanonicalDataset; "
                f"got {type(source).__name__}"
            )

        try:
            exporter = self._registry.get(self._format)
        except ExportError as exc:
            context.error(str(exc))
            raise

        # Per-call options take precedence; the
        # stage's default options are the fallback.
        options = self._options or ExportOptions()

        try:
            result = exporter.export(source, options)
        except NotImplementedError as exc:
            context.error(str(exc))
            raise ExportError(
                f"Exporter for {self._format.value!r} is a "
                f"placeholder; engine not yet implemented: {exc}"
            ) from exc

        context.records_out = result.record_count
        _logger.debug(
            "ExportStageImpl exported %d records to %s in %s format",
            result.record_count,
            result.destination,
            self._format.value,
        )
        return result

    def __repr__(self) -> str:
        return (
            f"ExportStageImpl(format={self._format.value!r}, "
            f"registry={'custom' if self._registry else 'default'})"
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def detect_format_from_path(path: str) -> ExportFormat | None:
    """Return the export format implied by a file path's
    extension, or `None` when the extension is unknown.

    The mapping is:

    - `.csv` → `ExportFormat.CSV`
    - `.json` → `ExportFormat.JSON`
    - `.parquet` → `ExportFormat.PARQUET`
    - `.duckdb` → `ExportFormat.DUCKDB`

    Files without a recognised extension return `None`
    (the caller decides the format explicitly).
    """
    if not path:
        return None
    lower = path.lower()
    for fmt in (
        ExportFormat.CSV,
        ExportFormat.JSON,
        ExportFormat.PARQUET,
        ExportFormat.DUCKDB,
    ):
        if lower.endswith(fmt.file_extension):
            return fmt
    return None