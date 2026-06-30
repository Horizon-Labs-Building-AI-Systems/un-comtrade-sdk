"""Regression tests for the beginner metadata recipes (CB-002).

The recipes live under ``recipes/metadata/``. Each
recipe is a thin wrapper around ``ComtradeClient``; the
tests inject a mock transport so the suite never
touches the network.

The tests are structured as one class per recipe:

- ``TestRecipe01ListCountries``
- ``TestRecipe02ListPartners``
- ``TestRecipe03ListHSCodes``
- ``TestRecipe04SearchHS``
- ``TestRecipe05RefreshMetadata``

Each test invokes the recipe's ``*_demo(client)`` (or
``refresh_metadata_demo(...)``) function directly and
asserts on (a) the captured stdout, and (b) the value
the recipe returns. The recipe's script-level
``main()`` is not exercised here; that path is covered
by the live ``--help`` smoke tests.
"""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Callable

import httpx
import pytest

from un_comtrade import ComtradeClient
from un_comtrade.cache import MetadataCache
from un_comtrade.parser import MetadataParser
from un_comtrade.transport import HttpTransport


# ---------------------------------------------------------------------------
# Path setup — make the recipes importable as a package
# ---------------------------------------------------------------------------

RECIPES_DIR = Path(__file__).resolve().parent.parent / "recipes"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Each recipe is a single .py file. We import them by file path
# using importlib so the recipes can sit outside any package.
import importlib.util


def _load_recipe(name: str):
    spec = importlib.util.spec_from_file_location(
        f"recipe_{name}", RECIPES_DIR / "metadata" / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None, f"Cannot load {name}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# Load the five recipes once at module import. The recipes
# are pure-Python; loading them has no side effects.
RECIPE_01 = _load_recipe("01_list_countries")
RECIPE_02 = _load_recipe("02_list_partners")
RECIPE_03 = _load_recipe("03_list_hs_codes")
RECIPE_04 = _load_recipe("04_search_hs")
RECIPE_05 = _load_recipe("05_refresh_metadata")


# ---------------------------------------------------------------------------
# Mock-transport helpers
# ---------------------------------------------------------------------------


def _load_fixture(name: str) -> object:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def _json_response(body: object, request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        status_code=200,
        content=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        request=request,
    )


def _make_handler(
    payload_map: dict[str, object],
) -> Callable[[httpx.Request], httpx.Response]:
    """Build a mock handler that returns the recorded payload per path."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = str(request.url.path)
        for needle, payload in payload_map.items():
            if needle in path:
                return _json_response(payload, request)
        return httpx.Response(
            status_code=404,
            content=b'{"err": "no mock match"}',
            headers={},
            request=request,
        )

    return handler


def _make_counter_handler(
    payload_map: dict[str, object],
) -> tuple[Callable[[httpx.Request], httpx.Response], Callable[[], int]]:
    """Build a counting mock handler. Returns (handler, call_count_getter)."""
    counter = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        counter["n"] += 1
        return _make_handler(payload_map)(request)

    return handler, lambda: counter["n"]


def _client_for(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    cache=None,
) -> ComtradeClient:
    """Build a ``ComtradeClient`` with a mock transport.

    The quiet parser (``log_skipped=False``) keeps the
    captured stdout free of validation warnings for
    upstream records that fail the ISO-code pattern.
    """
    transport = HttpTransport(
        base_url="https://example.org",
        user_agent="ua/test",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    return ComtradeClient(
        transport=transport,
        parser=MetadataParser(log_skipped=False),
        cache=cache,
    )


# ---------------------------------------------------------------------------
# Recipe 01 — list_countries
# ---------------------------------------------------------------------------


class TestRecipe01ListCountries:
    def test_returns_canonical_country_list(self):
        handler = _make_handler({"Reporters": _load_fixture("reporters.json")})
        client = _client_for(handler)
        try:
            countries = RECIPE_01.list_countries_demo(client)
            assert countries
            # 247 reporters survive validation in the
            # recorded fixture (some are skipped for
            # failing the ISO-code pattern).
            assert len(countries) == 247
            india = next(c for c in countries if c.country_code == 699)
            assert india.display_name == "India"
            assert india.iso_alpha3 == "IND"
        finally:
            client.close()

    def test_prints_summary_lines(self, capsys):
        handler = _make_handler({"Reporters": _load_fixture("reporters.json")})
        client = _client_for(handler)
        try:
            RECIPE_01.list_countries_demo(client)
        finally:
            client.close()
        out = capsys.readouterr().out
        # The recipe prints a headline count, a
        # "First 5:" block, and a "Looking up India"
        # block. Each is a separate assertion so a
        # regression in one section doesn't hide behind
        # the others.
        assert "Total reporter countries: 247" in out
        assert "First 5:" in out
        assert "Looking up India (reporter code 699):" in out
        assert "display_name : India" in out
        assert "iso_alpha3   : IND" in out


# ---------------------------------------------------------------------------
# Recipe 02 — list_partners
# ---------------------------------------------------------------------------


class TestRecipe02ListPartners:
    def test_returns_canonical_partner_list(self):
        handler = _make_handler({"partnerAreas": _load_fixture("partners.json")})
        client = _client_for(handler)
        try:
            partners = RECIPE_02.list_partners_demo(client)
            assert partners
            china = next(p for p in partners if p.country_code == 156)
            assert china.display_name == "China"
            assert china.iso_alpha3 == "CHN"
        finally:
            client.close()

    def test_prints_summary_lines(self, capsys):
        handler = _make_handler({"partnerAreas": _load_fixture("partners.json")})
        client = _client_for(handler)
        try:
            RECIPE_02.list_partners_demo(client)
        finally:
            client.close()
        out = capsys.readouterr().out
        assert "Total partner countries:" in out
        assert "First 5:" in out
        assert "Looking up China (partner code 156):" in out
        assert "display_name : China" in out
        assert "iso_alpha3   : CHN" in out


# ---------------------------------------------------------------------------
# Recipe 03 — list_hs_codes
# ---------------------------------------------------------------------------


class TestRecipe03ListHSCodes:
    def test_returns_hs_codes_for_edition(self):
        handler = _make_handler({"H2022.json": _load_fixture("hs_2022.json")})
        client = _client_for(handler)
        try:
            codes = RECIPE_03.list_hs_codes_demo(client, edition="2022")
            assert codes
            # The recorded fixture has 6940 valid HS
            # codes; any smaller number means an
            # upstream truncation or a parser bug.
            assert len(codes) == 6940
            # Every code is tagged with the requested
            # edition; the parser enforces this invariant.
            assert all(c.edition == "2022" for c in codes)
        finally:
            client.close()

    def test_prints_summary_lines(self, capsys):
        handler = _make_handler({"H2022.json": _load_fixture("hs_2022.json")})
        client = _client_for(handler)
        try:
            RECIPE_03.list_hs_codes_demo(client, edition="2022")
        finally:
            client.close()
        out = capsys.readouterr().out
        assert "Total HS2022 commodity codes: 6940" in out
        assert "First 5:" in out
        assert "Looking up chapter 27" in out
        # The catalogue's first five rows are the
        # TOTAL wildcard and the head of chapter 01
        # (live animals).
        assert "TOTAL" in out
        assert "0101" in out


# ---------------------------------------------------------------------------
# Recipe 04 — search_hs
# ---------------------------------------------------------------------------


class TestRecipe04SearchHS:
    def test_search_returns_canonical_models(self):
        handler = _make_handler({"H2022.json": _load_fixture("hs_2022.json")})
        client = _client_for(handler)
        try:
            results = RECIPE_04.search_hs_demo(
                client, query="electric", edition="2022", limit=5
            )
            assert results
            # The recorded fixture yields 333 matches
            # for the substring "electric" in HS2022;
            # the head of the result is HS code 2716
            # (electrical energy, classified under
            # chapter 27 mineral fuels).
            assert len(results) == 333
            assert results[0].commodity_code == "2716"
        finally:
            client.close()

    def test_search_is_case_insensitive(self):
        handler = _make_handler({"H2022.json": _load_fixture("hs_2022.json")})
        client = _client_for(handler)
        try:
            lower = RECIPE_04.search_hs_demo(
                client, query="horse", edition="2022", limit=20
            )
            upper = RECIPE_04.search_hs_demo(
                client, query="HORSE", edition="2022", limit=20
            )
            # The match is case-insensitive: both queries
            # return the same set of codes.
            assert {c.commodity_code for c in lower} == {
                c.commodity_code for c in upper
            }
        finally:
            client.close()

    def test_search_prints_query_and_matches(self, capsys):
        handler = _make_handler({"H2022.json": _load_fixture("hs_2022.json")})
        client = _client_for(handler)
        try:
            RECIPE_04.search_hs_demo(
                client, query="electric", edition="2022", limit=5
            )
        finally:
            client.close()
        out = capsys.readouterr().out
        assert 'Query: \'electric\'' in out
        assert "(edition=2022, limit=5)" in out
        assert "matches:" in out
        # 2716 (electrical energy) is the first match
        # for the substring "electric" in HS2022.
        assert "2716" in out


# ---------------------------------------------------------------------------
# Recipe 05 — refresh_metadata
# ---------------------------------------------------------------------------


class TestRecipe05RefreshMetadata:
    def test_refresh_invalidates_and_repopulates(self, tmp_path, capsys):
        # The demo takes a client that already has a
        # cache configured. We build a real client with
        # a mock transport and a temp-path cache so the
        # whole flow is exercised offline.
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache = MetadataCache(cache_dir)
        handler, call_count = _make_counter_handler(
            {"Reporters": _load_fixture("reporters.json")}
        )
        client = _client_for(handler, cache=cache)
        try:
            result = RECIPE_05.refresh_metadata_demo(client, resource_id="R02")
        finally:
            client.close()

        # The function returns a snapshot of the
        # observed state. The numbers are deterministic
        # against the recorded fixture.
        assert result["records_cold"] == 247
        assert result["records_warm"] == 247
        assert result["records_refetch"] == 247
        assert result["invalidated"] == 1

        # The cache state is consistent before and
        # after the refresh cycle: R02 is the only
        # key in the cache.
        assert result["keys_after_cold"] == ["R02"]
        assert result["keys_after_warm"] == ["R02"]
        assert result["keys_after_refetch"] == ["R02"]

        # The mock transport was called exactly twice:
        # once for the cold fetch and once for the
        # post-refetch fetch. The warm fetch between
        # them hit the cache and never reached the
        # transport.
        assert call_count() == 2

        # The printed report walks the reader through
        # the four steps.
        out = capsys.readouterr().out
        assert "Step 1: cold fetch" in out
        assert "Step 2: warm fetch" in out
        assert "Step 3: refresh_all()" in out
        assert "Step 4: cold fetch" in out
        assert "247 records returned" in out
        assert "1 key(s) invalidated" in out

    def test_refresh_rejects_unsupported_resource(self, tmp_path):
        """The demo refuses resource ids it does not know how to fetch."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache = MetadataCache(cache_dir)
        handler = _make_handler({})
        client = _client_for(handler, cache=cache)
        try:
            with pytest.raises(ValueError, match="Unsupported resource_id"):
                RECIPE_05.refresh_metadata_demo(client, resource_id="R99")
        finally:
            client.close()

    def test_refresh_requires_cache(self):
        """The demo refuses clients that do not have a cache configured."""
        handler = _make_handler({})
        client = _client_for(handler)  # no cache
        try:
            with pytest.raises(RuntimeError, match="MetadataCache"):
                RECIPE_05.refresh_metadata_demo(client, resource_id="R02")
        finally:
            client.close()
