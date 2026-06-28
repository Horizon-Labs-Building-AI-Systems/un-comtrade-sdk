"""Dataset loading for the CLI.

The analytics commands operate on a
:class:`un_comtrade.transform.CanonicalDataset`
previously persisted via the SDK's Storage layer.
This helper:

1. Detects the storage backend from a file
   extension (``.csv`` → CSV, ``.json`` → JSON,
   ``.parquet`` → Parquet, ``.duckdb`` → DuckDB,
   no extension → DuckDB by default).
2. Calls the corresponding backend's public
   ``read(config) -> CanonicalDataset`` method.
3. Surfaces a clean error if the file does not
   exist or the format is unsupported.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

from un_comtrade.storage import (
    StorageBackend,
    StorageConfig,
    StorageRegistry,
)
from un_comtrade.cli.utils.exceptions import (
    CLIConfigurationError,
)


#: Mapping of file-suffix → StorageBackend.
#: Keys are lowercased suffixes (including the
#: leading dot). Multiple suffixes map to the
#: same backend.
_EXTENSION_BACKEND = {
    ".csv": StorageBackend.CSV,
    ".json": StorageBackend.JSON,
    ".parquet": StorageBackend.PARQUET,
    ".pq": StorageBackend.PARQUET,
    ".duckdb": StorageBackend.DUCKDB,
    ".ddb": StorageBackend.DUCKDB,
}


def _detect_backend(path: Path) -> StorageBackend:
    """Map ``path`` to a :class:`StorageBackend`.

    Resolution order:

    1. If ``path`` is a file with a known suffix
       (``.csv``, ``.json``, ``.parquet``,
       ``.duckdb``), the suffix determines the
       backend.
    2. If ``path`` is a DIRECTORY, scan it for
       files with a known suffix and use the
       first match. This is what
       ``ParquetWriter.read`` expects (the
       writer stores the file inside a directory
       whose name is the configured ``root``).
    3. Otherwise, fall back to DuckDB.
    """
    if path.is_dir():
        # Directory: scan for the first known
        # file type.
        for child in sorted(path.iterdir()):
            suffix = child.suffix.lower()
            if suffix in _EXTENSION_BACKEND:
                return _EXTENSION_BACKEND[suffix]
        # No recognised files in the directory.
        return StorageBackend.DUCKDB
    # Path is a file (or doesn't exist yet —
    # the caller checks existence).
    suffix = path.suffix.lower()
    if suffix in _EXTENSION_BACKEND:
        return _EXTENSION_BACKEND[suffix]
    if not suffix:
        return StorageBackend.DUCKDB
    raise CLIConfigurationError(
        f"unsupported dataset extension {suffix!r}; "
        f"expected one of {sorted(_EXTENSION_BACKEND)}"
    )


def load_dataset(path: str | Path) -> Tuple:
    """Load a :class:`CanonicalDataset` from a
    previously-stored file via the public Storage
    API.

    Parameters
    ----------
    path
        Path to a stored dataset. The extension
        determines the backend.

    Returns
    -------
    CanonicalDataset
        The deserialised dataset.

    Raises
    ------
    CLIConfigurationError
        When the path does not exist, the
        extension is unsupported, or the backend
        cannot read the file.
    """
    p = Path(path)
    if not p.exists():
        raise CLIConfigurationError(
            f"dataset file does not exist: {p}"
        )
    backend = _detect_backend(p)
    storage = StorageRegistry().get(backend)
    if storage is None:
        raise CLIConfigurationError(
            f"storage backend {backend.name!r} is not "
            f"available; install the optional "
            f"dependency (e.g. `pip install "
            f"un-comtrade-sdk[{backend.name.lower()}]`)"
        )
    config = StorageConfig(root=str(p))
    try:
        return storage.read(config)
    except Exception as exc:
        # The Storage layer raises a variety of
        # exception types (StorageError,
        # OSError, ...); normalise them.
        raise CLIConfigurationError(
            f"failed to read dataset {p}: {exc}"
        ) from exc


__all__ = ["load_dataset"]