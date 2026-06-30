"""Storage layer.

The storage layer is the persistence stage of the
SDK. It consumes the canonical dataset produced by
the transformation layer and persists it to a
backend.

Per `012_STORAGE_SPECIFICATION.md`, the SDK supports
five storage targets:

- T01 LOCAL_FILES — local filesystem.
- T02 JSON — JSON files.
- T03 CSV — CSV files.
- T04 PARQUET — Parquet files.
- T05 DUCKDB — embedded analytical database.

This package exposes:

- The framework (in `un_comtrade.storage._base`):
  `StorageBackend`, `StorageConfig`,
  `DatasetMetadata`, `StorageResult`,
  `PartitionStrategy`, the `Storage` Protocol,
  placeholder storages for each backend,
  `StorageRegistry`, `StorageStage`.
- Concrete engines (one per backend module):
  `un_comtrade.storage.parquet` implements the
  Parquet writer with schema + Decimal preservation
  and partitioning. The remaining backends
  (JSON, CSV, DuckDB, LocalFiles) land in later
  tasks.

Public API re-exports keep `from un_comtrade.storage
import X` working for callers that imported the
framework symbols from the original `storage.py`.
"""

from ._base import (
    CSVStorage,
    DatasetMetadata,
    DuckDBStorage,
    JSONStorage,
    LOCAL_FILES_FORMAT,
    LocalFilesStorage,
    CSV_FORMAT,
    JSON_FORMAT,
    PARQUET_FORMAT,
    DUCKDB_FORMAT,
    ParquetStorage,
    PartitionStrategy,
    Storage,
    StorageBackend,
    StorageConfig,
    StorageError,
    StorageRegistry,
    StorageResult,
    StorageStage,
)


__all__ = [
    "CSVStorage",
    "CSVWriter",
    "DatasetMetadata",
    "DatasetUpdater",
    "DuckDBWriter",
    "DuckDBStorage",
    "DuplicatePolicy",
    "JSONStorage",
    "JSONWriter",
    "LOCAL_FILES_FORMAT",
    "LocalFilesStorage",
    "PARQUET_FORMAT",
    "CSV_FORMAT",
    "JSON_FORMAT",
    "DUCKDB_FORMAT",
    "ParquetWriter",
    "ParquetStorage",
    "PartitionStrategy",
    "SchemaIncompatibleError",
    "Storage",
    "StorageBackend",
    "StorageConfig",
    "StorageError",
    "StorageRegistry",
    "StorageResult",
    "StorageStage",
    "UpdateMode",
    "UpdateResult",
    "deduplicate",
    "find_duplicates",
    "verify_schema_compatibility",
    "write_metadata_sidecar",
]


# Importing the parquet + duckdb + file submodules
# triggers the `StorageRegistry._register_defaults()`
# auto-promotion logic (the placeholders are
# replaced by concrete engines when the optional
# dependencies are importable).
try:
    from . import parquet as _parquet  # noqa: F401

    ParquetWriter = _parquet.ParquetWriter
except ImportError:  # pragma: no cover - pyarrow missing
    ParquetWriter = None  # type: ignore[assignment]
    pass

try:
    from . import duckdb as _duckdb  # noqa: F401

    DuckDBWriter = _duckdb.DuckDBWriter
except ImportError:  # pragma: no cover - duckdb missing
    DuckDBWriter = None  # type: ignore[assignment]
    pass

try:
    from . import file as _file  # noqa: F401

    CSVWriter = _file.CSVWriter
    JSONWriter = _file.JSONWriter
    write_metadata_sidecar = _file.write_metadata_sidecar
except ImportError:  # pragma: no cover - stdlib csv missing
    CSVWriter = None  # type: ignore[assignment]
    JSONWriter = None  # type: ignore[assignment]
    write_metadata_sidecar = None  # type: ignore[assignment]
    pass

# Incremental update orchestrator (P5-006). No
# optional dependency — stdlib only.
from .update import (  # noqa: E402
    DatasetUpdater,
    DuplicatePolicy,
    SchemaIncompatibleError,
    UpdateMode,
    UpdateResult,
    deduplicate,
    find_duplicates,
    verify_schema_compatibility,
)