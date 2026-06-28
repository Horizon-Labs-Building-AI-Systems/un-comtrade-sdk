"""Metadata cache subsystem for the UN Comtrade Python SDK.

This module implements the L3 cache per
`003_ARCHITECTURE.md` §5.3 and `008_METADATA_LAYER_SPEC.md`
§7, bound by ADR-0024:

- Cache lives in the user cache directory (platform
  convention: XDG on Linux, `~/Library/Caches` on macOS,
  `%LOCALAPPDATA%` on Windows).
- Default refresh is manual; automatic refresh is
  reserved for a future task.
- The cache survives process restarts (file
  persistence).
- Trade responses are NEVER cached (ADR-0024 Q22).

The `MetadataCache` is owned by `MetadataService`. The
service checks the cache before issuing upstream calls
and writes results back after a successful fetch.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


__all__ = [
    "DEFAULT_CACHE_DIRECTORY",
    "DEFAULT_LIFETIMES",
    "CacheEntry",
    "MetadataCache",
    "default_cache_directory",
]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: One day in seconds — used for per-day cache lifetimes.
_DAY_SECONDS: int = 24 * 60 * 60

#: Default cache lifetimes per `008_METADATA_LAYER_SPEC.md` §7.4.
#: Stable / static resources: 30 days. Slow-changing
#: resources: 7 days. Operational resources: 1 day.
DEFAULT_LIFETIMES: Mapping[str, int] = {
    "R01": 30 * _DAY_SECONDS,  # list of references (static)
    "R02": 7 * _DAY_SECONDS,   # reporters (slow-changing)
    "R03": 7 * _DAY_SECONDS,   # partners (slow-changing)
    "R04": 7 * _DAY_SECONDS,   # HS combined (versioned; 1-30 day window)
    "R05": 7 * _DAY_SECONDS,   # HS per-edition (versioned)
    "R06": 7 * _DAY_SECONDS,   # SITC (versioned)
    "R07": 7 * _DAY_SECONDS,   # BEC (versioned)
    "R08": 7 * _DAY_SECONDS,   # EBOPS (versioned)
    "R09": 30 * _DAY_SECONDS,  # frequency (static)
    "R10": 30 * _DAY_SECONDS,  # trade flows (static)
    "R11": 7 * _DAY_SECONDS,   # customs procedures (slow-changing)
    "R12": 7 * _DAY_SECONDS,   # transport modes (slow-changing)
    "R13": 7 * _DAY_SECONDS,   # modes of supply (slow-changing)
    "R14": 7 * _DAY_SECONDS,   # quantity units (slow-changing)
    "R15": 1 * _DAY_SECONDS,   # data items (schema; min 1 day)
    "R16": 1 * _DAY_SECONDS,   # data availability (operational)
    "R17": 1 * _DAY_SECONDS,   # publication notes (operational)
}

#: Fallback lifetime for unknown keys — 7 days per the
#: default "slow-changing" tier.
_FALLBACK_LIFETIME: int = 7 * _DAY_SECONDS


# ---------------------------------------------------------------------------
# Default cache directory
# ---------------------------------------------------------------------------


def default_cache_directory() -> Path:
    """Return the platform-default cache directory.

    Resolves per platform conventions:

    - Windows: ``%LOCALAPPDATA%\\un_comtrade`` (or
      ``~\\un_comtrade`` as a fallback).
    - macOS: ``~/Library/Caches/un_comtrade``.
    - Linux / other: ``$XDG_CACHE_HOME/un_comtrade`` or
      ``~/.cache/un_comtrade``.

    The directory is created lazily on first write, not
    on import.
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "un_comtrade"
        return Path.home() / "un_comtrade"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "un_comtrade"
    # Linux and other Unix-like platforms follow XDG.
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "un_comtrade"


#: Default cache directory resolved at import time.
#: Consumers may override via `MetadataCache(cache_dir=...)`.
DEFAULT_CACHE_DIRECTORY: Path = default_cache_directory()


# ---------------------------------------------------------------------------
# Cache entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CacheEntry:
    """A single cache entry.

    `payload` is the opaque metadata payload (typically a
    `dict` from upstream JSON). `fetched_at` is the Unix
    timestamp at which the entry was first cached; this
    drives the time-based expiration policy.
    """

    payload: Any
    fetched_at: float

    def is_expired(
        self, lifetime_seconds: float, *, now: float | None = None
    ) -> bool:
        """Return True if the entry's age exceeds `lifetime_seconds`.

        `now` defaults to `time.time()`. Pass an explicit
        `now` (typically from a `MetadataCache`'s
        injectable clock) for deterministic tests.
        """
        if now is None:
            now = time.time()
        return (now - self.fetched_at) > lifetime_seconds

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-friendly dict."""
        return {"fetched_at": self.fetched_at, "payload": self.payload}


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

#: Pattern used to sanitise cache keys for filenames. Allows
#: alphanumeric, dash, underscore, dot. Anything else is
#: collapsed to a single underscore.
_KEY_SANITISE: re.Pattern[str] = re.compile(r"[^A-Za-z0-9._-]")


class MetadataCache:
    """L3 metadata cache per ADR-0024 and `008_METADATA_LAYER_SPEC.md` §7.

    The cache combines an in-memory dict (per-process) with
    JSON files on disk (shared across processes / survives
    restarts). Every read checks memory first, then falls
    back to disk and hydrates memory on hit.

    Trade responses are never cached (ADR-0024 Q22).
    """

    def __init__(
        self,
        cache_dir: Path | str | None = None,
        *,
        lifetimes: Mapping[str, int] | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        """Construct a metadata cache.

        Parameters
        ----------
        cache_dir
            Directory for persistent JSON files. Defaults
            to `DEFAULT_CACHE_DIRECTORY`. Pass `None` for
            an in-memory-only cache (tests).
        lifetimes
            Optional mapping of resource id (e.g. `"R02"`)
            to lifetime in seconds. Defaults to
            `DEFAULT_LIFETIMES`.
        clock
            Optional callable returning the current Unix
            timestamp. Defaults to `time.time`. Tests may
            inject a fixed clock for deterministic
            expiration behaviour.
        """
        if cache_dir is None:
            self._cache_dir: Path | None = None
        else:
            self._cache_dir = Path(cache_dir)
        self._lifetimes: dict[str, int] = (
            dict(lifetimes) if lifetimes is not None else dict(DEFAULT_LIFETIMES)
        )
        self._clock: Callable[[], float] = clock if clock is not None else time.time
        self._memory: dict[str, CacheEntry] = {}

    # ----- Properties ------------------------------------------------------

    @property
    def cache_dir(self) -> Path | None:
        """The on-disk cache directory, or `None` for in-memory-only."""
        return self._cache_dir

    @property
    def lifetimes(self) -> Mapping[str, int]:
        """A copy of the resource-id to lifetime (seconds) map."""
        return dict(self._lifetimes)

    # ----- Core operations -------------------------------------------------

    def get(self, key: str) -> Any | None:
        """Return the cached payload for `key`, or `None` if absent or expired.

        Returns `None` (cache miss) when:
        - the key is not in memory and not on disk;
        - the entry's age exceeds the configured lifetime.
        """
        entry = self._entry(key)
        if entry is None:
            return None
        lifetime = self._lifetimes.get(key, _FALLBACK_LIFETIME)
        if entry.is_expired(lifetime, now=self._clock()):
            return None
        return entry.payload

    def set(
        self,
        key: str,
        payload: Any,
        *,
        lifetime: int | None = None,
    ) -> None:
        """Store `payload` under `key`.

        Writes to memory immediately and to disk when a
        `cache_dir` is configured. Disk write failures
        are best-effort: the in-memory copy survives and
        the cache remains useful within the process.
        """
        entry = CacheEntry(payload=payload, fetched_at=self._clock())
        self._memory[key] = entry
        if lifetime is not None:
            self._lifetimes[key] = lifetime
        self._save_to_disk(key, entry)

    def is_fresh(self, key: str) -> bool:
        """Return True if the cached entry exists and is not expired."""
        entry = self._entry(key)
        if entry is None:
            return False
        lifetime = self._lifetimes.get(key, _FALLBACK_LIFETIME)
        return not entry.is_expired(lifetime, now=self._clock())

    def validate(self, key: str) -> bool:
        """Validate a cached entry.

        Returns True when the entry exists, decodes cleanly,
        is not expired, and (for list payloads) is non-empty.

        Used by the catalogue fetchers to decide whether
        a refresh is required.
        """
        entry = self._entry(key)
        if entry is None:
            return False
        lifetime = self._lifetimes.get(key, _FALLBACK_LIFETIME)
        if entry.is_expired(lifetime, now=self._clock()):
            return False
        payload = entry.payload
        if isinstance(payload, (list, tuple, set, frozenset)):
            return len(payload) > 0
        return payload is not None

    # ----- Refresh ---------------------------------------------------------

    def refresh(self, key: str) -> bool:
        """Mark `key` as needing a re-fetch from upstream.

        Removes the entry from memory and disk. Returns
        True if the entry existed before the call,
        False otherwise.
        """
        existed = self._key_exists(key)
        self.invalidate(key)
        return existed

    def refresh_all(self) -> int:
        """Invalidate every cached entry (memory + disk).

        Returns the number of unique keys that were
        removed (memory and disk views of the same key
        are counted once).
        """
        memory_keys = set(self._memory.keys())
        disk_keys: set[str] = set()
        if self._cache_dir is not None and self._cache_dir.exists():
            for path in self._cache_dir.glob("*.json"):
                disk_keys.add(path.stem)
        unique = memory_keys | disk_keys
        self.clear()
        return len(unique)

    def prune_stale(self) -> int:
        """Remove every expired entry from memory and disk.

        Returns the number of entries removed.
        """
        now = self._clock()
        stale: set[str] = set()
        for key, entry in list(self._memory.items()):
            lifetime = self._lifetimes.get(key, _FALLBACK_LIFETIME)
            if entry.is_expired(lifetime, now=now):
                stale.add(key)
        if self._cache_dir is not None and self._cache_dir.exists():
            for path in self._cache_dir.glob("*.json"):
                # The disk filename mirrors the sanitised key.
                # We load the entry to check freshness, then
                # invalidate via the original (sanitised) name.
                sanitised = path.stem
                # Reverse-lookup to original key is lossy; we
                # invalidate by the sanitised name (which is also
                # the on-disk file stem).
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    entry = CacheEntry(
                        payload=data["payload"], fetched_at=float(data["fetched_at"])
                    )
                except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError):
                    stale.add(sanitised)
                    continue
                lifetime = self._lifetimes.get(sanitised, _FALLBACK_LIFETIME)
                if entry.is_expired(lifetime, now=now):
                    stale.add(sanitised)
        for k in stale:
            self.invalidate(k)
        return len(stale)

    # ----- Lookup by code -------------------------------------------------

    def lookup_by_code(
        self,
        key: str,
        code: Any,
        *,
        code_field: str = "country_code",
    ) -> Any | None:
        """Return the first cached record whose `code_field` equals `code`.

        The cached payload is expected to be a list of
        records (e.g. a list of `Country` / `Partner` /
        `HSCode` instances). Records may be dataclass
        instances or plain dicts; both are supported.

        Returns `None` on cache miss, expired entry, or
        no matching record.
        """
        payload = self.get(key)
        if not isinstance(payload, list):
            return None
        for record in payload:
            if self._record_field(record, code_field) == code:
                return record
        return None

    # ----- Lookup by name (case-insensitive by default) -------------------

    def lookup_by_name(
        self,
        key: str,
        name: str,
        *,
        name_field: str = "display_name",
        case_sensitive: bool = False,
        exact: bool = True,
    ) -> list[Any]:
        """Return cached records whose `name_field` matches `name`.

        By default the match is case-insensitive and exact
        (whole-string equality). With `exact=False` the
        match becomes a substring search.

        Returns an empty list on cache miss, expired entry,
        or no matching record.
        """
        payload = self.get(key)
        if not isinstance(payload, list):
            return []
        target = name if case_sensitive else name.lower()
        result: list[Any] = []
        for record in payload:
            value = self._record_field(record, name_field)
            if not isinstance(value, str):
                continue
            actual = value if case_sensitive else value.lower()
            if exact:
                if actual == target:
                    result.append(record)
            else:
                if target in actual:
                    result.append(record)
        return result

    # ----- Search (case-insensitive by default) ---------------------------

    def search(
        self,
        key: str,
        query: str,
        *,
        fields: list[str] | None = None,
        case_sensitive: bool = False,
    ) -> list[Any]:
        """Return cached records matching `query` across the payload.

        By default the search is case-insensitive and
        matches `query` as a substring of any string field
        in each record. When `fields` is provided, only
        those fields are searched.

        Returns an empty list on cache miss, expired entry,
        or no matches.
        """
        payload = self.get(key)
        if not isinstance(payload, list):
            return []
        if not query:
            return []
        target = query if case_sensitive else query.lower()
        result: list[Any] = []
        for record in payload:
            for fname, value in self._iter_record_fields(record):
                if fields is not None and fname not in fields:
                    continue
                if not isinstance(value, str):
                    continue
                actual = value if case_sensitive else value.lower()
                if target in actual:
                    result.append(record)
                    break
        return result

    # ----- Internal helpers ------------------------------------------------

    def _key_exists(self, key: str) -> bool:
        """Return True if `key` is in memory or on disk."""
        if key in self._memory:
            return True
        path = self._path_for(key)
        return path is not None and path.exists()

    @staticmethod
    def _record_field(record: Any, field: str) -> Any:
        """Return a named field from a record (dict or object)."""
        if isinstance(record, Mapping):
            return record.get(field)
        return getattr(record, field, None)

    @staticmethod
    def _iter_record_fields(record: Any):
        """Yield (name, value) for each field of a record (dict or object)."""
        if isinstance(record, Mapping):
            yield from record.items()
            return
        # Dataclass / pydantic-style object.
        if hasattr(record, "__dataclass_fields__"):
            for name in record.__dataclass_fields__:
                yield name, getattr(record, name, None)
            return
        # Generic object: iterate over `__dict__`.
        for name, value in vars(record).items():
            yield name, value

    def invalidate(self, key: str) -> None:
        """Remove `key` from memory and disk (if present)."""
        self._memory.pop(key, None)
        path = self._path_for(key)
        if path is not None and path.exists():
            try:
                path.unlink()
            except OSError:
                pass

    def clear(self) -> None:
        """Remove every cached entry from memory and disk."""
        self._memory.clear()
        if self._cache_dir is not None and self._cache_dir.exists():
            for path in self._cache_dir.glob("*.json"):
                try:
                    path.unlink()
                except OSError:
                    pass

    def keys(self) -> list[str]:
        """Return the list of keys currently in memory."""
        return list(self._memory.keys())

    # ----- Internal helpers ------------------------------------------------

    def _entry(self, key: str) -> CacheEntry | None:
        """Return the entry for `key` (memory first, then disk)."""
        entry = self._memory.get(key)
        if entry is not None:
            return entry
        return self._load_from_disk(key)

    def _path_for(self, key: str) -> Path | None:
        """Return the on-disk path for `key`, or `None` if no cache_dir."""
        if self._cache_dir is None:
            return None
        safe = _KEY_SANITISE.sub("_", key)
        return self._cache_dir / f"{safe}.json"

    def _load_from_disk(self, key: str) -> CacheEntry | None:
        """Load an entry from disk and hydrate memory; return None on miss."""
        path = self._path_for(key)
        if path is None or not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            entry = CacheEntry(
                payload=data["payload"], fetched_at=float(data["fetched_at"])
            )
        except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError):
            return None
        self._memory[key] = entry
        return entry

    def _save_to_disk(self, key: str, entry: CacheEntry) -> None:
        """Persist `entry` to disk; best-effort, failures are silent."""
        path = self._path_for(key)
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(entry.to_dict(), default=str),
                encoding="utf-8",
            )
        except OSError:
            # Disk write failures are best-effort: the in-memory
            # copy still serves the current process.
            pass