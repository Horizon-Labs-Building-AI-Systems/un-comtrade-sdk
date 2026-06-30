"""Storage Layer Foundation.

The storage layer is the **persistence stage** of
the SDK (per `012_STORAGE_SPECIFICATION.md` and the
ETL Review Report). It consumes the canonical
dataset produced by the transformation layer and
persists it to a backend.

Per the P5-001 task scope:

- **Storage interface only** — no concrete storage
  engines (no file writes, no database connections).
  The five SDK-shipped backends are placeholder
  classes that raise `NotImplementedError`.
- **Consumes `CanonicalDataset` only** — the storage
  layer rejects raw API responses, raw upstream
  dicts, parser outputs, and any other non-canonical
  shape. This is enforced by `StorageStage.store()`
  and is verified by `tests/test_storage.py`.
- **Pluggable** — concrete backends are registered
  via `StorageRegistry.register()`. The SDK ships
  with five defaults (`LOCAL_FILES`, `JSON`, `CSV`,
  `PARQUET`, `DUCKDB`).
- **Deterministic partitioning** — the partition
  strategy computes file paths from the dataset's
  records in a deterministic order (per
  `012_STORAGE_SPECIFICATION.md` §6 + ADR-0029).

The five documented targets (`012_STORAGE_SPECIFICATION.md`
§3) — LOCAL_FILES / JSON / CSV / PARQUET / DUCKDB —
are exposed as `StorageBackend` enum values. Each
target ships as a placeholder that raises
`NotImplementedError`. Concrete engines land in
later tasks.

The storage layer integrates with the ETL pipeline
via a new `StageKind.STORAGE` (added in P5-001). The
storage stage is the LAST stage in a typical
pipeline: Extract → Validate → Transform → Export →
Storage.
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
    Sequence,
    runtime_checkable,
)

from ..etl import PipelineContext, StageKind
from ..exceptions import ComtradeError
from ..logging import get_logger


if TYPE_CHECKING:
    from ..transform import CanonicalDataset


__all__ = [
    "CSVStorage",
    "DatasetMetadata",
    "DuckDBStorage",
    "JSONStorage",
    "LOCAL_FILES_FORMAT",
    "LocalFilesStorage",
    "PARQUET_FORMAT",
    "CSV_FORMAT",
    "JSON_FORMAT",
    "DUCKDB_FORMAT",
    "PartitionStrategy",
    "ParquetStorage",
    "Storage",
    "StorageBackend",
    "StorageConfig",
    "StorageError",
    "StorageRegistry",
    "StorageResult",
    "StorageStage",
]


_logger = get_logger("lifecycle")


# Format sentinel values (mirror of export.py).
LOCAL_FILES_FORMAT: str = "local_files"
CSV_FORMAT: str = "csv"
JSON_FORMAT: str = "json"
PARQUET_FORMAT: str = "parquet"
DUCKDB_FORMAT: str = "duckdb"


# ---------------------------------------------------------------------------
# StorageBackend
# ---------------------------------------------------------------------------


class StorageBackend(str, Enum):
    """The five documented storage backends.

    Per `012_STORAGE_SPECIFICATION.md` §3, the SDK
    supports the following targets in the MVP:

    - **T01 LOCAL_FILES** — local filesystem (zero
      external dependencies; single-process).
    - **T02 JSON** — JSON files (human-readable;
      metadata catalogues; small trade datasets).
    - **T03 CSV** — CSV files (tabular interchange;
      hand-off to analysts).
    - **T04 PARQUET** — Parquet files (columnar
      analytics; large datasets; data lake
      ingestion).
    - **T05 DUCKDB** — embedded analytical DB
      (local SQL queries; single-machine warehouse).

    All five ship as placeholders that raise
    `NotImplementedError`. Concrete engines land in
    later tasks.
    """

    LOCAL_FILES = LOCAL_FILES_FORMAT
    JSON = JSON_FORMAT
    CSV = CSV_FORMAT
    PARQUET = PARQUET_FORMAT
    DUCKDB = DUCKDB_FORMAT

    @property
    def file_extension(self) -> str:
        """Default file extension for this backend.

        `LOCAL_FILES` has no fixed extension (returns
        an empty string); callers pick per-format
        extensions.
        """
        return {
            StorageBackend.LOCAL_FILES: "",
            StorageBackend.JSON: ".json",
            StorageBackend.CSV: ".csv",
            StorageBackend.PARQUET: ".parquet",
            StorageBackend.DUCKDB: ".duckdb",
        }[self]

    @property
    def is_engine(self) -> bool:
        """`True` for every backend (LOCAL_FILES is also
        an engine — local filesystem writes)."""
        return True


# ---------------------------------------------------------------------------
# StorageError + StorageConfig + DatasetMetadata + StorageResult
# ---------------------------------------------------------------------------


class StorageError(ComtradeError):
    """Raised when a storage operation fails.

    Distinct from the `NotImplementedError` raised by
    the placeholder storages: `StorageError` signals
    that a concrete storage was used but failed (e.g.
    the destination was unwritable, the schema was
    incompatible, etc.).
    """


@dataclass(frozen=True)
class StorageConfig:
    """Configuration for a storage operation.

    Parameters
    ----------
    root
        The root directory / database path. For
        `LOCAL_FILES` / `JSON` / `CSV` / `PARQUET`,
        this is the directory the dataset is written
        into. For `DUCKDB`, this is the database
        file path.
    partition_strategy
        The partition strategy to apply. Default is
        `PartitionStrategy.default()` (the
        `(reporter, year, frequency)` strategy per
        ADR-0029).
    overwrite
        When `True`, an existing dataset at the
        same destination is overwritten. When
        `False` (default), the storage fails with
        `StorageError` if the destination already
        exists. (Engines land in later tasks.)
    compression
        Compression codec name. Must be supported by
        the chosen backend. Defaults to `"none"` so
        that all backends work out of the box.
        Parquet/DuckDB accept `"snappy"`,
        `"gzip"`, `"zstd"`, `"brotli"` etc. via
        pyarrow/duckdb. CSV/JSON only accept
        `"none"` or `"gzip"` (P5-004).
    table_name
        For DuckDB: the target table name. Default
        `"trade_records"`.
    metadata
        Free-form metadata map (per-call additions).
    """

    root: str
    partition_strategy: "PartitionStrategy | None" = None
    overwrite: bool = False
    compression: str = "none"
    table_name: str = "trade_records"
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DatasetMetadata:
    """Provenance metadata about a stored dataset.

    Parameters
    ----------
    dataset_name
        The name of the stored dataset (matches
        `CanonicalDataset.name`).
    schema_version
        The schema version of the canonical entity
        (matches `CanonicalDataset.schema_version`).
    parser_name
        The parser used to produce the records.
    record_count
        Number of records in the dataset.
    skipped
        Number of records skipped during parsing.
    duplicates_removed
        Number of duplicates removed during the
        transformation layer's latest-wins dedup.
    source_count
        Number of raw records the transformer
        received as input.
    extracted_at
        UTC timestamp the dataset was produced.
    stored_at
        UTC timestamp the dataset was stored.
    partition_keys
        Tuple of partition keys the dataset was
        partitioned under (one per record set).
    backend
        The storage backend used.
    destination
        The destination URI / file path / database
        identifier.
    extra
        Free-form metadata (per-backend additions).
    """

    dataset_name: str
    schema_version: str
    parser_name: str
    record_count: int
    skipped: int
    duplicates_removed: int
    source_count: int
    extracted_at: datetime | None
    stored_at: datetime
    partition_keys: tuple[tuple[Any, ...], ...]
    backend: StorageBackend
    destination: str
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StorageResult:
    """Outcome of a storage operation.

    Parameters
    ----------
    backend
        The backend used.
    destination
        The destination URI / file path / database
        identifier. For partitioned stores, this is
        the root; the `partitions` map lists the
        individual partition paths.
    metadata
        The full `DatasetMetadata` describing the
        stored dataset.
    partitions
        Mapping of `partition_key -> list[str]`
        (paths under the partition). For a single-
        partition dataset, this is a one-entry map.
    byte_size
        Total bytes written (for file-based
        backends); `None` for `DUCKDB`.
    """

    backend: StorageBackend
    destination: str
    metadata: DatasetMetadata
    partitions: Mapping[tuple[Any, ...], tuple[str, ...]] = field(
        default_factory=dict
    )
    byte_size: int | None = None

    @property
    def record_count(self) -> int:
        return self.metadata.record_count

    @property
    def empty(self) -> bool:
        return self.metadata.record_count == 0


# ---------------------------------------------------------------------------
# PartitionStrategy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PartitionStrategy:
    """Deterministic partitioning strategy.

    Per ADR-0029 + `012_STORAGE_SPECIFICATION.md` §6,
    the SDK's default partition key is
    `(reporter, year, frequency)`. Each `TradeRecord`
    in the canonical dataset maps to exactly one
    partition; multiple records sharing the same
    key land in the same partition.

    The strategy is **deterministic**: given the same
    record set, it produces the same partition paths.
    Order is preserved (sorted lexicographically by
    partition key) so that re-runs produce stable
    output.

    Parameters
    ----------
    name
        Strategy name (e.g. `"default"` for
        `(reporter, year, frequency)`, `"none"` for a
        single-partition dataset).
    extract
        Callable that takes a record and returns a
        hashable partition key. The default extractor
        pulls `(reporter.reporter_code, ref_year,
        frequency_code)` from each record (the ADR-0029
        contract).
    path_template
        A `str.format` template for the file path
        within a partition. Defaults to
        `"{key_0}/{key_1}/{key_2}/{dataset_name}{ext}"`
        (Hive-style partitioning by the default
        `(reporter, year, frequency)` extract).
        Tokens available: `dataset_name`, `backend`,
        `ext`, plus positional `_0.._N` and
        `key_0..key_N` from the partition key tuple.
    """

    name: str
    extract: Callable[[Any], tuple]
    path_template: str = (
        "{key_0}/{key_1}/{key_2}/{dataset_name}{ext}"
    )

    @staticmethod
    def default() -> "PartitionStrategy":
        """Default `(reporter, year, frequency)`
        strategy per ADR-0029."""
        def _extract(record: Any) -> tuple:
            reporter = getattr(record, "reporter", None)
            reporter_code = (
                getattr(reporter, "reporter_code", None) if reporter else None
            )
            ref_year = getattr(record, "ref_year", None)
            frequency_code = getattr(record, "frequency_code", None)
            return (reporter_code, ref_year, frequency_code)

        return PartitionStrategy(
            name="default",
            extract=_extract,
            path_template=(
                "{key_0}/{key_1}/{key_2}/{dataset_name}{ext}"
            ),
        )

    @staticmethod
    def none() -> "PartitionStrategy":
        """Single-partition strategy (no partitioning).
        All records share a single key `("all",)` and
        the file lands directly under the storage
        root, e.g. `root/{dataset_name}{ext}`."""
        def _extract(record: Any) -> tuple:
            return ("all",)

        return PartitionStrategy(
            name="none",
            extract=_extract,
            path_template="{dataset_name}{ext}",
        )

    def partition_records(
        self,
        records: Sequence[Any],
    ) -> dict[tuple, list[Any]]:
        """Group records by partition key.

        Returns a dict keyed by the partition key
        (preserving insertion order — first record's
        key is first). Records sharing the same key
        land in the same list.
        """
        groups: dict[tuple, list[Any]] = {}
        for record in records:
            key = self.extract(record)
            groups.setdefault(key, []).append(record)
        return groups

    def partition_paths(
        self,
        dataset_name: str,
        backend: StorageBackend,
    ) -> dict[tuple, str]:
        """Return a deterministic path for each
        partition key the strategy can produce.

        This helper pre-computes the path *template*
        for each known partition key. Concrete storages
        receive the keys + paths and decide whether
        to materialise them (the placeholder storages
        raise `NotImplementedError`).
        """
        # The placeholder storages don't have access
        # to records at config time, so the caller
        # supplies the keys after parsing. This
        # helper formats a single path from a key.
        return {}

    def format_path(
        self,
        dataset_name: str,
        backend: StorageBackend,
        key: tuple,
    ) -> str:
        """Format a path for a single partition key.

        The path uses the `path_template` with the
        backend's file extension appended (unless the
        template already includes an extension).

        The `key` is a tuple of positional fields. Each
        element is exposed to the template under the
        positional name `_0`, `_1`, `_2`, ...
        plus a convenience `key_0`, `key_1`, ...
        alias. Named field mapping is intentionally not
        done here — the extract callable is responsible
        for returning a tuple with the desired order.
        """
        ext = backend.file_extension
        template = self.path_template
        # Build the keyword mapping: dataset_name,
        # backend, ext, plus positional _0.._N from the
        # partition key tuple.
        fmt_kwargs: dict[str, Any] = {
            "dataset_name": dataset_name,
            "backend": backend.value,
            "ext": ext,
        }
        for idx, value in enumerate(key):
            fmt_kwargs[f"_{idx}"] = value
            fmt_kwargs[f"key_{idx}"] = value
        rendered = template.format(**fmt_kwargs)
        if ext and not rendered.endswith(ext):
            rendered = rendered + ext
        return rendered

    def partition_key(self, record: Any) -> tuple:
        """Return the partition key for a single
        record (shortcut for `extract(record)`)."""
        return self.extract(record)


# ---------------------------------------------------------------------------
# Storage Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class Storage(Protocol):
    """Protocol every concrete storage backend
    implements.

    A storage:
    - Knows its `backend`.
    - Accepts a `CanonicalDataset` (and rejects raw
      upstream payloads).
    - Writes the dataset's records to the configured
      destination using the supplied partition
      strategy.
    - Returns a `StorageResult` describing what was
      produced.
    - Reloads a previously persisted dataset via
      `read(config)` and returns it as a
      `CanonicalDataset`.

    Per `012_STORAGE_SPECIFICATION.md` §11
    (Retrieval Strategy), the storage layer is the
    source of the dataset that the analytics layer
    consumes; `read()` is the contract that every
    concrete backend implements.
    """

    backend: StorageBackend

    def store(
        self,
        dataset: "CanonicalDataset",
        config: StorageConfig,
    ) -> StorageResult: ...

    def read(
        self,
        config: StorageConfig,
    ) -> "CanonicalDataset": ...


# ---------------------------------------------------------------------------
# Placeholder storages (interfaces only; no engines)
# ---------------------------------------------------------------------------


class _PlaceholderStorage:
    """Base for the five engine-backed storages.

    Subclasses set `backend`. The `store` method
    raises `NotImplementedError` — concrete engines
    land in later tasks.

    NOT an `abc.ABC` (similar rationale as
    `_PlaceholderExporter` in `export.py`): the five
    placeholders share a single raise message; an ABC
    would require each subclass to override with its
    own raise, duplicating the message.
    """

    backend: StorageBackend  # subclasses set this

    def store(
        self,
        dataset: "CanonicalDataset",
        config: StorageConfig,
    ) -> StorageResult:
        """Engine-specific persistence — implemented
        in a later task. The MVP raises
        `NotImplementedError` so consumers know the
        hook is reserved but the engine has not
        landed yet."""
        raise NotImplementedError(
            f"{type(self).__name__}.store is not yet implemented. "
            f"Engine for {self.backend.value!r} lands in a later task."
        )

    def read(
        self,
        config: StorageConfig,
    ) -> "CanonicalDataset":
        """Engine-specific retrieval — implemented in
        a later task.

        Per `012_STORAGE_SPECIFICATION.md` §11, the
        retrieval is on-demand. The MVP raises
        `NotImplementedError` so consumers know the
        hook is reserved but the engine has not
        landed yet. Concrete engines (CSV / JSON /
        Parquet / DuckDB) implement `read()` in their
        respective modules.
        """
        raise NotImplementedError(
            f"{type(self).__name__}.read is not yet implemented. "
            f"Engine for {self.backend.value!r} lands in a later task."
        )


@dataclass(frozen=True)
class LocalFilesStorage(_PlaceholderStorage):
    """Placeholder LOCAL_FILES storage (T01).

    The MVP raises `NotImplementedError` from `store`.
    The engine (Python `pathlib` + Parquet/JSON
    serialization) lands in a later task.
    """

    backend: StorageBackend = StorageBackend.LOCAL_FILES


@dataclass(frozen=True)
class JSONStorage(_PlaceholderStorage):
    """Placeholder JSON storage (T02)."""

    backend: StorageBackend = StorageBackend.JSON


@dataclass(frozen=True)
class CSVStorage(_PlaceholderStorage):
    """Placeholder CSV storage (T03)."""

    backend: StorageBackend = StorageBackend.CSV


@dataclass(frozen=True)
class ParquetStorage(_PlaceholderStorage):
    """Placeholder Parquet storage (T04)."""

    backend: StorageBackend = StorageBackend.PARQUET


@dataclass(frozen=True)
class DuckDBStorage(_PlaceholderStorage):
    """Placeholder DuckDB storage (T05)."""

    backend: StorageBackend = StorageBackend.DUCKDB


# ---------------------------------------------------------------------------
# StorageRegistry
# ---------------------------------------------------------------------------


class StorageRegistry:
    """Registry mapping `StorageBackend` → `Storage`.

    The SDK ships with five built-in registrations:

    - `LOCAL_FILES` → `LocalFilesStorage`
    - `JSON` → `JSONStorage`
    - `CSV` → `CSVStorage`
    - `PARQUET` → `ParquetStorage`
    - `DUCKDB` → `DuckDBStorage`

    All five are placeholders that raise
    `NotImplementedError`. Consumers can:

    - `register(backend, storage)` to install a
      concrete storage over a placeholder.
    - `get(backend)` to look up the registered
      storage.

    The registry is a plain object; callers can hold
    their own registry and pass it to
    `StorageStage`.
    """

    def __init__(
        self,
        *,
        storages: Mapping[StorageBackend, "Storage"] | None = None,
    ) -> None:
        self._storages: dict[StorageBackend, Storage] = {}
        self._register_defaults()
        if storages:
            for backend, storage in storages.items():
                self.register(backend, storage)

    def _register_defaults(self) -> None:
        """Register the SDK's built-in storages.

        The PARQUET placeholder is replaced by the
        concrete `ParquetWriter` (from
        `un_comtrade.storage.parquet`) when pyarrow
        is importable. The DUCKDB placeholder is
        replaced by the concrete `DuckDBWriter`
        when duckdb is importable. The JSON and CSV
        placeholders are replaced by the concrete
        `JSONWriter` / `CSVWriter` (from
        `un_comtrade.storage.file`). LocalFiles
        remains a placeholder until its engine lands.
        """
        self._storages[StorageBackend.LOCAL_FILES] = LocalFilesStorage()
        self._storages[StorageBackend.JSON] = JSONStorage()
        self._storages[StorageBackend.CSV] = CSVStorage()
        self._storages[StorageBackend.PARQUET] = ParquetStorage()
        self._storages[StorageBackend.DUCKDB] = DuckDBStorage()
        # Auto-promote placeholders when concrete
        # engines are importable. The imports are
        # wrapped in try/except so the storage
        # framework remains importable without
        # optional dependencies.
        try:
            from . import parquet as _parquet  # type: ignore[import-not-found]

            self._storages[StorageBackend.PARQUET] = (
                _parquet.ParquetWriter()
            )
        except ImportError:
            pass
        except Exception:  # pragma: no cover - defensive
            pass
        try:
            from . import duckdb as _duckdb  # type: ignore[import-not-found]

            self._storages[StorageBackend.DUCKDB] = (
                _duckdb.DuckDBWriter()
            )
        except ImportError:
            pass
        except Exception:  # pragma: no cover - defensive
            pass
        try:
            from . import file as _file  # type: ignore[import-not-found]

            self._storages[StorageBackend.JSON] = (
                _file.JSONWriter()
            )
            self._storages[StorageBackend.CSV] = (
                _file.CSVWriter()
            )
        except ImportError:
            pass
        except Exception:  # pragma: no cover - defensive
            pass

    def register(
        self,
        backend: StorageBackend,
        storage: "Storage",
    ) -> None:
        """Register (or replace) the storage for
        `backend`."""
        if not isinstance(backend, StorageBackend):
            raise TypeError(
                f"backend must be StorageBackend; got "
                f"{type(backend).__name__}"
            )
        if not hasattr(storage, "backend") or not callable(
            getattr(storage, "store", None)
        ):
            raise TypeError(
                f"storage must have a 'backend' attribute and a "
                f"'store' callable; got {type(storage).__name__}"
            )
        self._storages[backend] = storage

    def get(self, backend: StorageBackend) -> "Storage":
        """Return the registered storage for `backend`.

        Raises `StorageError` if no storage is
        registered for the requested backend.
        """
        try:
            return self._storages[backend]
        except KeyError as exc:
            raise StorageError(
                f"No storage registered for backend {backend.value!r}"
            ) from exc

    def supported_backends(self) -> tuple[StorageBackend, ...]:
        """Return the backends this registry knows about."""
        return tuple(self._storages.keys())

    def unregister(self, backend: StorageBackend) -> None:
        """Remove the storage for `backend`.

        Raises `StorageError` if no storage is
        registered.
        """
        if backend not in self._storages:
            raise StorageError(
                f"No storage registered for backend {backend.value!r}"
            )
        del self._storages[backend]

    # ----- File-system convenience ---------------------------------------

    #: Mapping of file-suffix → ``StorageBackend`` used by
    #: :meth:`open`. Keys are lowercased suffixes (including
    #: the leading dot). Multiple suffixes map to the same
    #: backend (``.pq`` and ``.parquet``, ``.ddb`` and ``.duckdb``).
    _EXTENSION_BACKEND: Mapping[str, "StorageBackend"] = {
        ".csv": StorageBackend.CSV,
        ".json": StorageBackend.JSON,
        ".parquet": StorageBackend.PARQUET,
        ".pq": StorageBackend.PARQUET,
        ".duckdb": StorageBackend.DUCKDB,
        ".ddb": StorageBackend.DUCKDB,
    }

    @staticmethod
    def _detect_backend(path: "Path") -> "StorageBackend":
        """Map ``path`` to a :class:`StorageBackend`.

        Resolution order:

        1. If ``path`` is a directory, scan for a file with
           a known suffix and use the first match.
        2. If ``path`` is a file with a known suffix, use the
           suffix.
        3. Otherwise, fall back to ``DUCKDB``.
        """
        from pathlib import Path as _Path

        p = _Path(path)
        if p.is_dir():
            for child in sorted(p.iterdir()):
                suffix = child.suffix.lower()
                if suffix in StorageRegistry._EXTENSION_BACKEND:
                    return StorageRegistry._EXTENSION_BACKEND[suffix]
            return StorageBackend.DUCKDB
        suffix = p.suffix.lower()
        if suffix in StorageRegistry._EXTENSION_BACKEND:
            return StorageRegistry._EXTENSION_BACKEND[suffix]
        if not suffix:
            return StorageBackend.DUCKDB
        raise StorageError(
            f"unsupported dataset extension {suffix!r}; "
            f"expected one of "
            f"{sorted(StorageRegistry._EXTENSION_BACKEND)}"
        )

    def open(
        self,
        uri: str | "Path",
        *,
        table_name: str = "trade_records",
        overwrite: bool = False,
        compression: str = "none",
    ) -> "CanonicalDataset":
        """Load a :class:`CanonicalDataset` from a previously-
        persisted file via the public Storage API.

        The backend is auto-detected from the file extension
        (``.csv`` / ``.json`` / ``.parquet`` / ``.duckdb``).
        A directory path is supported (scanned for the first
        known file type — the convention used by
        :class:`ParquetWriter`).

        Parameters
        ----------
        uri
            Path to a stored dataset. The extension
            determines the backend.
        table_name
            For DuckDB: the table to read from.
            Default ``"trade_records"``.
        overwrite
            Forwarded to ``StorageConfig`` (currently unused
            by reads).
        compression
            Forwarded to ``StorageConfig`` (currently unused
            by reads).

        Returns
        -------
        CanonicalDataset
            The deserialised dataset.

        Raises
        ------
        StorageError
            When ``uri`` does not exist, the extension is
            unsupported, or the backend cannot read the file.
        """
        from pathlib import Path as _Path

        p = _Path(uri)
        if not p.exists():
            raise StorageError(
                f"dataset path does not exist: {p}"
            )
        backend = self._detect_backend(p)
        storage = self.get(backend)
        config = StorageConfig(
            root=str(p),
            overwrite=overwrite,
            compression=compression,
            table_name=table_name,
        )
        return storage.read(config)


# ---------------------------------------------------------------------------
# StorageStage
# ---------------------------------------------------------------------------


class StorageStage:
    """The storage stage for an `ETLPipeline`.

    Implements the `StageKind.STORAGE` slot in the
    pipeline. On `__call__(source, context)`:

    1. **Validates the source is a
       `CanonicalDataset`**. Raw upstream payloads,
       parser outputs, and any other non-canonical
       shape are rejected with `StorageError`.
    2. Looks up the storage for `backend` via the
       registry (default registry if none supplied).
    3. Invokes `storage.store(dataset, config)`.
    4. Returns the resulting `StorageResult` so the
       pipeline's caller can inspect it.
    5. Records the storage on the
       `PipelineContext`.

    Construction::

        stage = StorageStage(backend=StorageBackend.PARQUET)
        # OR with a custom registry + config:
        stage = StorageStage(
            backend=StorageBackend.PARQUET,
            registry=my_registry,
            config=StorageConfig(
                root="/data/trade",
                partition_strategy=PartitionStrategy.default(),
            ),
        )

    Plug into an `ETLPipeline`::

        pipeline = ETLPipeline(
            name="trade_ingest",
            stages=(
                StageSpec(name="extract", ...),
                StageSpec(name="transform", ...),
                StageSpec(name="export", ...),
                StageSpec(
                    name="store",
                    kind=StageKind.STORAGE,
                    factory=lambda ctx: StorageStage(
                        backend=StorageBackend.PARQUET
                    ),
                ),
            ),
        )
    """

    def __init__(
        self,
        backend: StorageBackend = StorageBackend.PARQUET,
        *,
        registry: StorageRegistry | None = None,
        config: StorageConfig | None = None,
    ) -> None:
        if not isinstance(backend, StorageBackend):
            raise TypeError(
                f"backend must be StorageBackend; got "
                f"{type(backend).__name__}"
            )
        self._backend = backend
        self._registry = (
            registry if registry is not None else StorageRegistry()
        )
        self._config = config

    @property
    def backend(self) -> StorageBackend:
        """The storage backend this stage uses."""
        return self._backend

    @property
    def registry(self) -> StorageRegistry:
        """The storage registry this stage uses."""
        return self._registry

    @property
    def config(self) -> StorageConfig | None:
        """The default config for this stage."""
        return self._config

    @property
    def name(self) -> str:
        """Stage identifier (`store_parquet` /
        `store_csv` / etc.)."""
        return f"store_{self._backend.value}"

    @property
    def kind(self) -> StageKind:
        """Always `StageKind.STORAGE`."""
        return StageKind.STORAGE

    def __call__(
        self,
        source: Any,
        context: PipelineContext,
    ) -> StorageResult:
        """Dispatch the source dataset to the
        configured storage.

        Parameters
        ----------
        source
            A `CanonicalDataset` (per the P4-003
            transformation layer contract).
        context
            The shared `PipelineContext`. The
            storage stage records `records_out`
            (the dataset count) and any errors.

        Returns
        -------
        StorageResult
            The result of the storage.

        Raises
        ------
        StorageError
            If the source is not a `CanonicalDataset`
            (raw upstream payloads, parser outputs,
            etc. are rejected) or no storage is
            registered for the configured backend.
        """
        # Local import to avoid circular dependency
        # (transform.py imports models; we import
        # transform.py here for type checks).
        from ..transform import CanonicalDataset

        if not isinstance(source, CanonicalDataset):
            raise StorageError(
                f"StorageStage source must be a CanonicalDataset; "
                f"got {type(source).__name__}"
            )

        try:
            storage = self._registry.get(self._backend)
        except StorageError as exc:
            context.error(str(exc))
            raise

        # Default config if none supplied. Use the
        # default partition strategy (ADR-0029).
        config = self._config
        if config is None:
            config = StorageConfig(
                root="./un_comtrade_data",
                partition_strategy=PartitionStrategy.default(),
            )

        try:
            result = storage.store(source, config)
        except NotImplementedError as exc:
            context.error(str(exc))
            raise StorageError(
                f"Storage for {self._backend.value!r} is a "
                f"placeholder; engine not yet implemented: {exc}"
            ) from exc

        context.records_out = result.record_count
        _logger.debug(
            "StorageStage stored %d records to %s in %s backend",
            result.record_count,
            result.destination,
            self._backend.value,
        )
        return result

    def __repr__(self) -> str:
        return (
            f"StorageStage(backend={self._backend.value!r}, "
            f"registry={'custom' if self._registry else 'default'})"
        )