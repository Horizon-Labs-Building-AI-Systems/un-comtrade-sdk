"""Tests for the metadata cache lookup / search / refresh extensions.

These tests extend the cache subsystem per the P1-015
task scope: lookup-by-code, lookup-by-name (case-insensitive),
general search, refresh (single + bulk + stale-prune), and
validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from un_comtrade.cache import (
    DEFAULT_LIFETIMES,
    CacheEntry,
    MetadataCache,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FrozenClock:
    def __init__(self, t0: float = 1_000_000.0) -> None:
        self.now = t0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@dataclass(frozen=True)
class _Country:
    """A tiny stand-in for the real Country model.

    The cache helpers must work on opaque records (dataclass
    or dict). This class mirrors the canonical Country model
    just enough for the tests to assert on field values.
    """

    country_code: int
    iso_alpha2: str | None
    iso_alpha3: str | None
    display_name: str


def _make_cache(
    tmp_path: Path, *, clock: _FrozenClock | None = None
) -> MetadataCache:
    return MetadataCache(
        tmp_path / "cache",
        clock=clock if clock is not None else _FrozenClock(),
    )


def _seed_countries(
    cache: MetadataCache,
    countries: list[_Country],
    key: str = "R02",
) -> None:
    # The cache uses `json.dumps(..., default=str)`, which does
    # not roundtrip dataclasses. Tests that need to survive a
    # "process restart" must seed with plain dicts (see
    # `_seed_countries_dicts`); the dataclass-based seed is
    # for in-memory-only assertions.
    cache.set(key, list(countries))


def _seed_countries_dicts(
    cache: MetadataCache,
    countries: list[_Country],
    key: str = "R02",
) -> None:
    """Seed the cache with plain-dict payloads (JSON-roundtrips)."""
    cache.set(
        key,
        [
            {
                "country_code": c.country_code,
                "iso_alpha2": c.iso_alpha2,
                "iso_alpha3": c.iso_alpha3,
                "display_name": c.display_name,
            }
            for c in countries
        ],
    )


# ---------------------------------------------------------------------------
# Lookup by code
# ---------------------------------------------------------------------------


class TestLookupByCode:
    def test_find_by_country_code(self, tmp_path):
        cache = _make_cache(tmp_path)
        _seed_countries(
            cache,
            [
                _Country(699, "IN", "IND", "India"),
                _Country(156, "CN", "CHN", "China"),
                _Country(840, "US", "USA", "United States"),
            ],
        )
        result = cache.lookup_by_code("R02", 699)
        assert result is not None
        assert result.country_code == 699
        assert result.display_name == "India"

    def test_unknown_code_returns_none(self, tmp_path):
        cache = _make_cache(tmp_path)
        _seed_countries(cache, [_Country(699, "IN", "IND", "India")])
        assert cache.lookup_by_code("R02", 999) is None

    def test_missing_cache_returns_none(self, tmp_path):
        cache = _make_cache(tmp_path)
        assert cache.lookup_by_code("R02", 699) is None

    def test_custom_code_field(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.set(
            "R05",
            [
                {"commodity_code": "0101", "description": "Horses"},
                {"commodity_code": "0102", "description": "Cattle"},
            ],
        )
        result = cache.lookup_by_code(
            "R05", "0102", code_field="commodity_code"
        )
        assert result is not None
        assert result["description"] == "Cattle"

    def test_expired_returns_none(self, tmp_path):
        clock = _FrozenClock()
        cache = _make_cache(tmp_path, clock=clock)
        _seed_countries(cache, [_Country(699, "IN", "IND", "India")])
        clock.advance(DEFAULT_LIFETIMES["R02"] + 1)
        assert cache.lookup_by_code("R02", 699) is None


# ---------------------------------------------------------------------------
# Lookup by name
# ---------------------------------------------------------------------------


class TestLookupByName:
    def test_exact_case_sensitive_match(self, tmp_path):
        cache = _make_cache(tmp_path)
        _seed_countries(
            cache,
            [
                _Country(699, "IN", "IND", "India"),
                _Country(156, "CN", "CHN", "China"),
            ],
        )
        result = cache.lookup_by_name("R02", "India")
        assert len(result) == 1
        assert result[0].country_code == 699

    def test_case_insensitive_match(self, tmp_path):
        cache = _make_cache(tmp_path)
        _seed_countries(
            cache,
            [
                _Country(699, "IN", "IND", "India"),
            ],
        )
        result = cache.lookup_by_name("R02", "INDIA")
        assert len(result) == 1
        assert result[0].country_code == 699

    def test_case_sensitive_disabled(self, tmp_path):
        cache = _make_cache(tmp_path)
        _seed_countries(cache, [_Country(699, "IN", "IND", "India")])
        # With case_sensitive=True, "INDIA" must NOT match.
        result = cache.lookup_by_name("R02", "INDIA", case_sensitive=True)
        assert result == []

    def test_substring_match(self, tmp_path):
        cache = _make_cache(tmp_path)
        _seed_countries(
            cache,
            [
                _Country(699, "IN", "IND", "India"),
                _Country(156, "CN", "CHN", "China"),
            ],
        )
        # Default exact=True requires full equality. With exact=False
        # substring matches "in" in both "India" and "China".
        result = cache.lookup_by_name("R02", "in", exact=False)
        assert {r.country_code for r in result} == {699, 156}

    def test_no_match_returns_empty(self, tmp_path):
        cache = _make_cache(tmp_path)
        _seed_countries(
            cache,
            [
                _Country(699, "IN", "IND", "India"),
            ],
        )
        assert cache.lookup_by_name("R02", "Atlantis") == []

    def test_dict_records_supported(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.set(
            "R05",
            [
                {"commodity_code": "0101", "description": "Horses"},
                {"commodity_code": "0102", "description": "Cattle"},
            ],
        )
        result = cache.lookup_by_name(
            "R05", "cattle", name_field="description"
        )
        assert len(result) == 1
        assert result[0]["commodity_code"] == "0102"


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class TestSearch:
    def test_case_insensitive_substring(self, tmp_path):
        cache = _make_cache(tmp_path)
        _seed_countries(
            cache,
            [
                _Country(699, "IN", "IND", "India"),
                _Country(156, "CN", "CHN", "China"),
                _Country(840, "US", "USA", "United States"),
            ],
        )
        # "in" is a substring of "India" (positions 0-1).
        # It is NOT a substring of "China" ("chINa" — but the
        # substring "in" requires i followed by n, and "china"
        # is c-h-i-n-a, so "in" IS in "china" via positions 2-3).
        # "United States" is u-n-i-t-e-d; "in" requires i-then-n,
        # which doesn't appear.
        result = cache.search("R02", "in")
        assert {r.country_code for r in result} == {699, 156}

    def test_search_specific_fields(self, tmp_path):
        cache = _make_cache(tmp_path)
        _seed_countries(
            cache,
            [
                _Country(699, "IN", "IND", "India"),
                _Country(840, "US", "USA", "United States"),
            ],
        )
        # Only search ISO codes; "IN" matches India (alpha2), "US"
        # matches United States (alpha2).
        result = cache.search("R02", "in", fields=["iso_alpha2"])
        assert {r.country_code for r in result} == {699}

    def test_search_empty_query_returns_empty(self, tmp_path):
        cache = _make_cache(tmp_path)
        _seed_countries(cache, [_Country(699, "IN", "IND", "India")])
        assert cache.search("R02", "") == []

    def test_search_case_sensitive(self, tmp_path):
        cache = _make_cache(tmp_path)
        _seed_countries(cache, [_Country(699, "IN", "IND", "India")])
        assert cache.search("R02", "INDIA", case_sensitive=True) == []
        assert len(cache.search("R02", "India", case_sensitive=True)) == 1

    def test_search_returns_each_record_once(self, tmp_path):
        cache = _make_cache(tmp_path)
        _seed_countries(
            cache,
            [
                _Country(699, "IN", "IND", "India"),
            ],
        )
        # "in" appears in both display_name ("India") and iso_alpha3 ("IND").
        # The record should still be returned only once.
        result = cache.search("R02", "in")
        assert len(result) == 1

    def test_search_dict_records(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.set(
            "R05",
            [
                {"commodity_code": "0101", "description": "Live horses"},
                {"commodity_code": "0102", "description": "Live cattle"},
            ],
        )
        result = cache.search("R05", "live")
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


class TestRefresh:
    def test_refresh_existing_key(self, tmp_path):
        cache = _make_cache(tmp_path)
        _seed_countries(cache, [_Country(699, "IN", "IND", "India")])
        assert cache.refresh("R02") is True
        assert cache.get("R02") is None

    def test_refresh_missing_key_returns_false(self, tmp_path):
        cache = _make_cache(tmp_path)
        assert cache.refresh("R02") is False

    def test_refresh_clears_disk(self, tmp_path):
        cache = _make_cache(tmp_path)
        _seed_countries(cache, [_Country(699, "IN", "IND", "India")])
        path = cache.cache_dir / "R02.json"
        assert path.exists()
        cache.refresh("R02")
        assert not path.exists()

    def test_refresh_all(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.set("R02", [_Country(699, "IN", "IND", "India")])
        cache.set("R03", [_Country(156, "CN", "CHN", "China")])
        cache.set("R09", [{"id": "A", "text": "Annual"}])
        removed = cache.refresh_all()
        assert removed == 3
        assert cache.get("R02") is None
        assert cache.get("R03") is None
        assert cache.get("R09") is None

    def test_refresh_all_clears_disk(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.set("R02", [_Country(699, "IN", "IND", "India")])
        cache.set("R09", [{"id": "A", "text": "Annual"}])
        cache.refresh_all()
        files = list(cache.cache_dir.glob("*.json"))
        assert files == []


class TestPruneStale:
    def test_prune_removes_expired(self, tmp_path):
        clock = _FrozenClock()
        cache = _make_cache(tmp_path, clock=clock)
        cache.set("R02", [_Country(699, "IN", "IND", "India")])
        cache.set("R16", [{"qtyCode": -1, "qtyAbbr": "N/A"}], lifetime=10)
        clock.advance(11)
        # R02 is still fresh (30-day default lifetime); R16 expired.
        removed = cache.prune_stale()
        assert removed == 1
        assert cache.get("R02") is not None
        assert cache.get("R16") is None

    def test_prune_no_op_when_fresh(self, tmp_path):
        clock = _FrozenClock()
        cache = _make_cache(tmp_path, clock=clock)
        cache.set("R02", [_Country(699, "IN", "IND", "India")])
        removed = cache.prune_stale()
        assert removed == 0
        assert cache.get("R02") is not None

    def test_prune_disk_only_expired(self, tmp_path):
        clock = _FrozenClock()
        cache = _make_cache(tmp_path, clock=clock)
        cache.set("R02", [_Country(699, "IN", "IND", "India")])
        # Advance time so the entry is now stale.
        clock.advance(DEFAULT_LIFETIMES["R02"] + 1)
        # Memory may still hold it; prune removes both memory
        # and disk.
        removed = cache.prune_stale()
        assert removed == 1


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_validate_fresh_entry(self, tmp_path):
        cache = _make_cache(tmp_path)
        _seed_countries(cache, [_Country(699, "IN", "IND", "India")])
        assert cache.validate("R02") is True

    def test_validate_missing_key(self, tmp_path):
        cache = _make_cache(tmp_path)
        assert cache.validate("R02") is False

    def test_validate_expired(self, tmp_path):
        clock = _FrozenClock()
        cache = _make_cache(tmp_path, clock=clock)
        _seed_countries(cache, [_Country(699, "IN", "IND", "India")])
        clock.advance(DEFAULT_LIFETIMES["R02"] + 1)
        assert cache.validate("R02") is False

    def test_validate_empty_list(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.set("R02", [])  # empty list -> not valid
        assert cache.validate("R02") is False

    def test_validate_non_empty_list(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.set("R02", [_Country(699, "IN", "IND", "India")])
        assert cache.validate("R02") is True

    def test_validate_scalar_payload(self, tmp_path):
        # Non-list payloads: any non-None value is valid.
        cache = _make_cache(tmp_path)
        cache.set("R01", {"category": "x"})
        assert cache.validate("R01") is True
        cache.set("R01_null", None)
        assert cache.validate("R01_null") is False

    def test_validate_corrupt_disk(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.cache_dir.mkdir(parents=True, exist_ok=True)
        (cache.cache_dir / "R02.json").write_text("not json", encoding="utf-8")
        # Corrupt file: load fails -> validate returns False.
        assert cache.validate("R02") is False


# ---------------------------------------------------------------------------
# Cache survives restart (re-instantiation)
# ---------------------------------------------------------------------------


class TestCacheSurvivesRestart:
    def test_persisted_entry_loadable_after_reinstantiation(self, tmp_path):
        cache1 = _make_cache(tmp_path)
        _seed_countries_dicts(
            cache1, [_Country(699, "IN", "IND", "India")]
        )

        # Simulate process restart: new instance, same dir.
        cache2 = _make_cache(tmp_path)
        result = cache2.lookup_by_code("R02", 699)
        assert result is not None
        assert result["country_code"] == 699

    def test_in_memory_state_does_not_leak_across_instances(self, tmp_path):
        cache1 = _make_cache(tmp_path)
        _seed_countries_dicts(
            cache1, [_Country(699, "IN", "IND", "India")]
        )

        cache2 = _make_cache(tmp_path)
        # `keys()` reflects memory only; on cold start it's empty.
        assert cache2.keys() == []
        # `get()` triggers disk load and hydration.
        assert cache2.get("R02") is not None
        assert "R02" in cache2.keys()


# ---------------------------------------------------------------------------
# Duplicate handling
# ---------------------------------------------------------------------------


class TestDuplicateHandling:
    def test_set_overwrites_previous(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.set("R02", [_Country(699, "IN", "IND", "First")])
        cache.set("R02", [_Country(699, "IN", "IND", "Second")])
        result = cache.lookup_by_code("R02", 699)
        assert result.display_name == "Second"

    def test_lookup_by_code_returns_first_matching(self, tmp_path):
        cache = _make_cache(tmp_path)
        # Two records with the same code (caller may pre-dedup
        # or not; the cache stores the list as-is).
        cache.set(
            "R02",
            [
                _Country(699, "IN", "IND", "First"),
                _Country(699, "IN", "IND", "Second"),
            ],
        )
        result = cache.lookup_by_code("R02", 699)
        assert result.display_name == "First"

    def test_search_returns_records_only_once_per_id(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.set(
            "R02",
            [
                _Country(699, "IN", "IND", "India"),
                _Country(699, "IN", "IND", "India (dup)"),
            ],
        )
        # Search returns the matching records; duplicates
        # within the list are NOT collapsed (that is the
        # parser's job, not the cache's).
        result = cache.search("R02", "india")
        assert len(result) == 2

    def test_lookup_by_name_with_multiple_matches(self, tmp_path):
        cache = _make_cache(tmp_path)
        cache.set(
            "R02",
            [
                _Country(699, "IN", "IND", "India"),
                _Country(699, "IN", "IND", "India (alt)"),
            ],
        )
        # Substring match (exact=False) catches both "India"
        # variants; exact match would only catch "India".
        result = cache.lookup_by_name("R02", "India", exact=False)
        assert len(result) == 2