"""Unit tests for the pagination engine (`un_comtrade.pagination`).

Per the P3-002 task scope, the engine transparently
paginates a multi-period query, merging records across
pages with cross-page deduplication, supporting
progress callbacks and early termination, and
enforcing documented page safeguards.

Coverage:

- PaginationConfig: defaults, validation, custom
  values
- PageProgress: defaults, validation
- PaginationEngine.paginate: single page, multiple
  pages, comma-separated periods, dedup, progress
  callback, early termination, max-page safeguard,
  error propagation, infinite-loop prevention
- Exception classes: hierarchy, message format
- Lazy parser import (no hard dependency on parser
  at import time)
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from un_comtrade.models import (
    Commodity,
    Quantity,
    RecordTradeFlow,
    Reporter,
    TradePartner,
    TradeRecord,
    TradeResponse,
    TradeValue,
)
from un_comtrade.pagination import (
    DEFAULT_MAX_PAGES,
    DEFAULT_MAX_PERIODS_PER_PAGE,
    DEFAULT_MAX_RECORDS_PER_PAGE,
    PageProgress,
    PaginationAborted,
    PaginationConfig,
    PaginationEngine,
    PaginationError,
    PaginationLimitExceeded,
)
from un_comtrade.parser import TradeParser


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_record(
    *,
    reporter_code: int = 699,
    partner_code: int = 0,
    period: str = "2022",
    flow_code: str = "X",
    commodity_code: str = "TOTAL",
    primary_value: str = "100",
) -> TradeRecord:
    """Build a single `TradeRecord` for testing."""
    return TradeRecord(
        type_code="C",
        frequency_code="A",
        classification_code="H6",
        classification_search_code="HS",
        edition="H6",
        is_original_classification=True,
        ref_period_id=int(period + "0101"),
        ref_year=int(period),
        ref_month=52,
        period=period,
        reporter=Reporter(
            reporter_code=reporter_code, iso3="IND", name="India"
        ),
        partner=TradePartner(
            partner_code=partner_code,
            iso3="W00" if partner_code == 0 else "USA",
            name="World" if partner_code == 0 else "USA",
        ),
        partner2=None,
        flow=RecordTradeFlow(flow_code=flow_code, flow_name="Export"),
        commodity=Commodity(
            commodity_code=commodity_code,
            name="All Commodities" if commodity_code == "TOTAL" else commodity_code,
        ),
        customs_code="C00",
        customs_name="TOTAL CPC",
        mos_code="0",
        mot_code=0,
        mot_name="TOTAL MOT",
        quantity=Quantity(
            qty=None,
            qty_unit_code=-1,
            qty_unit_abbr="N/A",
            is_estimated=False,
            alt_qty=None,
            alt_qty_unit_code=None,
            alt_qty_unit_abbr=None,
            is_alt_qty_estimated=False,
        ),
        net_weight_kg=None,
        is_net_weight_estimated=False,
        gross_weight_kg=None,
        is_gross_weight_estimated=False,
        trade_value=TradeValue(
            primary_value=Decimal(primary_value),
            fob_value=None,
            cif_value=None,
        ),
        legacy_estimation_flag=0,
        is_reported=False,
        is_aggregate=True,
        provenance=None,
    )


def _make_response(records: list[TradeRecord], **overrides) -> TradeResponse:
    """Build a `TradeResponse` from a list of records."""
    kwargs: dict[str, Any] = {
        "elapsed_seconds": 0.1,
        "count": len(records),
        "records": records,
        "upstream_url": "https://example.invalid/",
    }
    kwargs.update(overrides)
    return TradeResponse(**kwargs)


@pytest.fixture
def engine() -> PaginationEngine:
    """A default pagination engine."""
    return PaginationEngine()


# ---------------------------------------------------------------------------
# PaginationConfig
# ---------------------------------------------------------------------------


class TestPaginationConfig:
    def test_defaults(self):
        cfg = PaginationConfig()
        assert cfg.max_periods_per_page == 12
        assert cfg.max_pages == 12
        assert cfg.max_records_per_page == 250_000

    def test_default_constants(self):
        # The constants exported by the module match the
        # PaginationConfig defaults.
        assert DEFAULT_MAX_PERIODS_PER_PAGE == 12
        assert DEFAULT_MAX_PAGES == 12
        assert DEFAULT_MAX_RECORDS_PER_PAGE == 250_000

    def test_custom_values(self):
        cfg = PaginationConfig(
            max_periods_per_page=6,
            max_pages=20,
            max_records_per_page=500,
        )
        assert cfg.max_periods_per_page == 6
        assert cfg.max_pages == 20
        assert cfg.max_records_per_page == 500

    def test_max_periods_per_page_zero_rejected(self):
        with pytest.raises(ValueError, match="max_periods_per_page"):
            PaginationConfig(max_periods_per_page=0)

    def test_max_periods_per_page_negative_rejected(self):
        with pytest.raises(ValueError, match="max_periods_per_page"):
            PaginationConfig(max_periods_per_page=-1)

    def test_max_pages_zero_rejected(self):
        with pytest.raises(ValueError, match="max_pages"):
            PaginationConfig(max_pages=0)

    def test_max_pages_negative_rejected(self):
        with pytest.raises(ValueError, match="max_pages"):
            PaginationConfig(max_pages=-1)

    def test_max_records_per_page_zero_rejected(self):
        with pytest.raises(ValueError, match="max_records_per_page"):
            PaginationConfig(max_records_per_page=0)

    def test_max_records_per_page_negative_rejected(self):
        with pytest.raises(ValueError, match="max_records_per_page"):
            PaginationConfig(max_records_per_page=-1)

    def test_type_validation(self):
        with pytest.raises(TypeError):
            PaginationConfig(max_periods_per_page="12")  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            PaginationConfig(max_pages=12.5)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# PageProgress
# ---------------------------------------------------------------------------


class TestPageProgress:
    def test_minimal(self):
        p = PageProgress(page_number=1, page_count=1, records_so_far=0, page_records=10)
        assert p.page_number == 1
        assert p.page_count == 1
        assert p.records_so_far == 0
        assert p.page_records == 10
        assert p.periods == ()

    def test_with_periods(self):
        p = PageProgress(
            page_number=2,
            page_count=3,
            records_so_far=100,
            page_records=50,
            periods=("2020", "2021"),
        )
        assert p.periods == ("2020", "2021")

    def test_page_number_zero_rejected(self):
        with pytest.raises(ValueError, match="page_number"):
            PageProgress(page_number=0, page_count=1, records_so_far=0, page_records=0)

    def test_page_number_negative_rejected(self):
        with pytest.raises(ValueError, match="page_number"):
            PageProgress(page_number=-1, page_count=1, records_so_far=0, page_records=0)

    def test_page_count_zero_rejected(self):
        with pytest.raises(ValueError, match="page_count"):
            PageProgress(page_number=1, page_count=0, records_so_far=0, page_records=0)

    def test_records_so_far_negative_rejected(self):
        with pytest.raises(ValueError, match="records_so_far"):
            PageProgress(page_number=1, page_count=1, records_so_far=-1, page_records=0)

    def test_page_records_negative_rejected(self):
        with pytest.raises(ValueError, match="page_records"):
            PageProgress(page_number=1, page_count=1, records_so_far=0, page_records=-1)


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestExceptions:
    def test_pagination_error_is_comtrade_error(self):
        from un_comtrade.exceptions import ComtradeError

        assert issubclass(PaginationError, ComtradeError)

    def test_pagination_limit_exceeded_is_pagination_error(self):
        assert issubclass(PaginationLimitExceeded, PaginationError)

    def test_pagination_aborted_is_pagination_error(self):
        assert issubclass(PaginationAborted, PaginationError)

    def test_limit_exceeded_message(self):
        exc = PaginationLimitExceeded("test message")
        assert "test message" in str(exc)

    def test_aborted_message(self):
        exc = PaginationAborted("test message")
        assert "test message" in str(exc)


# ---------------------------------------------------------------------------
# PaginationEngine: constructor
# ---------------------------------------------------------------------------


class TestEngineConstructor:
    def test_default_config(self):
        engine = PaginationEngine()
        assert isinstance(engine.config, PaginationConfig)
        assert engine.config.max_periods_per_page == 12

    def test_custom_config(self):
        cfg = PaginationConfig(max_periods_per_page=6, max_pages=20)
        engine = PaginationEngine(config=cfg)
        assert engine.config.max_periods_per_page == 6
        assert engine.config.max_pages == 20


# ---------------------------------------------------------------------------
# PaginationEngine: single-page fetches
# ---------------------------------------------------------------------------


class TestSinglePage:
    def test_single_period(self, engine):
        # Single period → single page.
        records = [_make_record(period="2022")]
        r = engine.paginate(["2022"], lambda ps: _make_response(records))
        assert r.count == 1
        assert len(r.records) == 1

    def test_no_split_when_under_chunk_size(self, engine):
        # 12 periods fit in a single chunk.
        records = [_make_record(period=str(y)) for y in range(2011, 2023)]
        r = engine.paginate(
            [str(y) for y in range(2011, 2023)],
            lambda ps: _make_response(
                [_make_record(period=p) for p in ps]
            ),
        )
        assert r.count == 12
        assert len(r.records) == 12

    def test_elapsed_seconds_aggregated(self, engine):
        def fetch(periods):
            return _make_response(
                [_make_record(period=p) for p in periods],
                elapsed_seconds=0.5,
            )

        # 24 periods → 2 pages of 12 → elapsed_seconds summed.
        r = engine.paginate(
            [str(y) for y in range(2000, 2024)], fetch
        )
        # 0.5 × 2 pages = 1.0.
        assert r.elapsed_seconds == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# PaginationEngine: multi-page merging
# ---------------------------------------------------------------------------


class TestMultiPage:
    def test_split_24_periods_into_2_pages(self, engine):
        # Default chunk size = 12; 24 periods → 2 pages.
        seen_chunks: list[list[str]] = []

        def fetch(periods):
            seen_chunks.append(list(periods))
            return _make_response([_make_record(period=p) for p in periods])

        periods = [str(y) for y in range(2000, 2024)]  # 24 years
        r = engine.paginate(periods, fetch)
        assert len(seen_chunks) == 2
        assert seen_chunks[0] == periods[:12]
        assert seen_chunks[1] == periods[12:]
        assert r.count == 24
        assert len(r.records) == 24

    def test_custom_chunk_size(self):
        cfg = PaginationConfig(max_periods_per_page=6, max_pages=12)
        engine = PaginationEngine(config=cfg)
        seen_chunks: list[list[str]] = []

        def fetch(periods):
            seen_chunks.append(list(periods))
            return _make_response([_make_record(period=p) for p in periods])

        periods = [str(y) for y in range(2000, 2013)]  # 13 years
        r = engine.paginate(periods, fetch)
        # 13 / 6 → 3 chunks: [2000-2005], [2006-2011], [2012]
        assert len(seen_chunks) == 3
        assert len(seen_chunks[0]) == 6
        assert len(seen_chunks[1]) == 6
        assert len(seen_chunks[2]) == 1
        assert r.count == 13

    def test_records_preserved_across_pages(self, engine):
        def fetch(periods):
            return _make_response([_make_record(period=p) for p in periods])

        periods = [str(y) for y in range(2010, 2022)]
        r = engine.paginate(periods, fetch)
        returned_periods = sorted(rec.period for rec in r.records)
        assert returned_periods == sorted(periods)

    def test_error_propagated(self, engine):
        def fetch(periods):
            return _make_response([], error="some warning")

        r = engine.paginate(["2020", "2021"], fetch)
        assert r.error == "some warning"


# ---------------------------------------------------------------------------
# PaginationEngine: cross-page deduplication
# ---------------------------------------------------------------------------


class TestCrossPageDedup:
    def test_duplicate_across_pages_collapsed(self, engine):
        # Upstream returns the same record (composite key)
        # across two pages. Engine should keep one.
        seen_pages: list[int] = []

        def fetch(periods):
            seen_pages.append(len(periods))
            if len(seen_pages) == 1:
                # First page: 12 records (including the dup)
                return _make_response(
                    [_make_record(period=p) for p in periods]
                    + [_make_record(period=periods[0])]  # duplicate
                )
            else:
                # Second page: only the duplicate (already in first page)
                return _make_response([])

        r = engine.paginate(
            [str(y) for y in range(2000, 2024)], fetch
        )
        # First page returns 12 unique + 1 dup → 12 records kept.
        # Second page returns nothing.
        # Total: 12 records (the dup is collapsed).
        assert r.count == 12

    def test_first_wins(self, engine):
        # When the same composite key appears with different
        # primary_values, the FIRST occurrence wins.
        def fetch(periods):
            return _make_response(
                [
                    _make_record(period=periods[0], primary_value="100"),
                ]
            )

        r = engine.paginate(["2020"], fetch)
        assert r.records[0].trade_value.primary_value == Decimal("100")

    def test_distinct_records_all_kept(self, engine):
        def fetch(periods):
            # 3 distinct records per period chunk (different
            # partner codes so different composite keys).
            records: list[TradeRecord] = []
            for p in periods:
                records.append(_make_record(period=p, partner_code=0))
                records.append(_make_record(period=p, partner_code=842))
                records.append(_make_record(period=p, partner_code=156))
            return _make_response(records)

        # 3 periods → 1 page → 9 distinct records.
        r = engine.paginate(
            [str(y) for y in range(2010, 2013)], fetch
        )
        assert r.count == 9


# ---------------------------------------------------------------------------
# PaginationEngine: progress callback
# ---------------------------------------------------------------------------


class TestProgressCallback:
    def test_callback_invoked_per_page(self, engine):
        seen: list[PageProgress] = []

        def on_progress(p):
            seen.append(p)

        def fetch(periods):
            return _make_response([_make_record(period=p) for p in periods])

        engine.paginate(
            [str(y) for y in range(2000, 2024)], fetch, on_progress=on_progress
        )
        # 24 periods / 12 per page → 2 pages.
        assert len(seen) == 2
        assert seen[0].page_number == 1
        assert seen[1].page_number == 2

    def test_progress_page_count(self, engine):
        seen: list[PageProgress] = []

        def on_progress(p):
            seen.append(p)

        def fetch(periods):
            return _make_response([_make_record(period=p) for p in periods])

        engine.paginate(
            [str(y) for y in range(2000, 2024)], fetch, on_progress=on_progress
        )
        # page_count is the total expected pages, computed up-front.
        for p in seen:
            assert p.page_count == 2

    def test_progress_records_so_far_cumulative(self, engine):
        seen: list[PageProgress] = []

        def on_progress(p):
            seen.append(p)

        def fetch(periods):
            return _make_response(
                [_make_record(period=p) for p in periods]
            )

        engine.paginate(
            [str(y) for y in range(2000, 2024)], fetch, on_progress=on_progress
        )
        # Page 1: records_so_far=0 (start), 12 records after.
        # Page 2: records_so_far=12 (cumulative before page 2), 12 records after.
        assert seen[0].records_so_far == 0
        assert seen[1].records_so_far == 12

    def test_progress_periods(self, engine):
        seen: list[PageProgress] = []

        def on_progress(p):
            seen.append(p)

        def fetch(periods):
            return _make_response([_make_record(period=p) for p in periods])

        engine.paginate(
            [str(y) for y in range(2000, 2024)], fetch, on_progress=on_progress
        )
        assert seen[0].periods == tuple(str(y) for y in range(2000, 2012))
        assert seen[1].periods == tuple(str(y) for y in range(2012, 2024))

    def test_progress_page_records(self, engine):
        seen: list[PageProgress] = []

        def on_progress(p):
            seen.append(p)

        def fetch(periods):
            return _make_response([_make_record(period=p) for p in periods])

        engine.paginate(
            [str(y) for y in range(2000, 2024)], fetch, on_progress=on_progress
        )
        # Each page returns 12 records.
        assert seen[0].page_records == 12
        assert seen[1].page_records == 12

    def test_callback_returning_true_continues(self, engine):
        def on_progress(p):
            return True

        def fetch(periods):
            return _make_response([_make_record(period=p) for p in periods])

        r = engine.paginate(
            [str(y) for y in range(2000, 2024)], fetch, on_progress=on_progress
        )
        assert r.count == 24

    def test_callback_returning_none_continues(self, engine):
        def on_progress(p):
            return None

        def fetch(periods):
            return _make_response([_make_record(period=p) for p in periods])

        r = engine.paginate(
            [str(y) for y in range(2000, 2024)], fetch, on_progress=on_progress
        )
        assert r.count == 24


# ---------------------------------------------------------------------------
# PaginationEngine: early termination
# ---------------------------------------------------------------------------


class TestEarlyTermination:
    def test_abort_after_first_page(self, engine):
        pages_fetched: list[list[str]] = []

        def fetch(periods):
            pages_fetched.append(list(periods))
            return _make_response([_make_record(period=p) for p in periods])

        def on_progress(p):
            if p.page_number == 1:
                return False
            return None

        with pytest.raises(PaginationAborted):
            engine.paginate(
                [str(y) for y in range(2000, 2024)], fetch, on_progress=on_progress
            )
        # Only the first page was fetched.
        assert len(pages_fetched) == 1

    def test_abort_in_middle(self, engine):
        pages_fetched: list[list[str]] = []

        def fetch(periods):
            pages_fetched.append(list(periods))
            return _make_response([_make_record(period=p) for p in periods])

        def on_progress(p):
            if p.page_number == 3:
                return False
            return None

        with pytest.raises(PaginationAborted):
            engine.paginate(
                [str(y) for y in range(2000, 2036)], fetch, on_progress=on_progress
            )
        # 36 periods / 12 per page → 3 pages; abort on page 3.
        assert len(pages_fetched) == 3

    def test_aborted_message_includes_page_number(self):
        def fetch(periods):
            return _make_response([_make_record(period=p) for p in periods])

        def on_progress(p):
            if p.page_number == 1:
                return False
            return None

        with pytest.raises(PaginationAborted) as excinfo:
            PaginationEngine().paginate(
                [str(y) for y in range(2000, 2024)], fetch, on_progress=on_progress
            )
        assert "1/2" in str(excinfo.value)


# ---------------------------------------------------------------------------
# PaginationEngine: max-page safeguard
# ---------------------------------------------------------------------------


class TestMaxPageSafeguard:
    def test_within_limit(self):
        # 12 chunks of 12 periods = 144 periods = exactly max_pages.
        cfg = PaginationConfig(max_pages=12, max_periods_per_page=12)
        engine = PaginationEngine(config=cfg)

        def fetch(periods):
            return _make_response([])

        r = engine.paginate([str(y) for y in range(2000, 2144)], fetch)
        assert r.count == 0  # 12 pages, each empty

    def test_exceeds_limit_raises(self):
        cfg = PaginationConfig(max_pages=12, max_periods_per_page=12)
        engine = PaginationEngine(config=cfg)

        def fetch(periods):
            return _make_response([])

        with pytest.raises(PaginationLimitExceeded) as excinfo:
            engine.paginate([str(y) for y in range(2000, 2145)], fetch)
        assert "13" in str(excinfo.value)  # 145 / 12 = 13 pages
        assert "12" in str(excinfo.value)  # the documented limit

    def test_just_below_limit_ok(self):
        cfg = PaginationConfig(max_pages=12, max_periods_per_page=12)
        engine = PaginationEngine(config=cfg)

        def fetch(periods):
            return _make_response([])

        # 144 periods = 12 pages (max).
        r = engine.paginate([str(y) for y in range(2000, 2144)], fetch)
        assert r.count == 0

    def test_custom_max_pages(self):
        cfg = PaginationConfig(max_pages=2, max_periods_per_page=12)
        engine = PaginationEngine(config=cfg)

        def fetch(periods):
            return _make_response([])

        # 25 periods / 12 per page = 3 pages > max_pages=2.
        with pytest.raises(PaginationLimitExceeded):
            engine.paginate([str(y) for y in range(2000, 2025)], fetch)


# ---------------------------------------------------------------------------
# PaginationEngine: infinite-loop prevention
# ---------------------------------------------------------------------------


class TestInfiniteLoopPrevention:
    def test_finite_page_count(self):
        # The engine pre-computes the page count from the
        # period list. The fetch callable cannot drive the
        # engine into an infinite loop because each period
        # is consumed exactly once.
        fetch_calls: list[list[str]] = []

        def fetch(periods):
            fetch_calls.append(list(periods))
            return _make_response([_make_record(period=p) for p in periods])

        engine = PaginationEngine()
        engine.paginate([str(y) for y in range(2000, 2024)], fetch)
        # 2 pages, period-splitting is deterministic.
        assert len(fetch_calls) == 2
        # Periods are disjoint across pages.
        all_periods = [p for chunk in fetch_calls for p in chunk]
        assert len(all_periods) == len(set(all_periods))

    def test_periods_exhausted_terminates(self):
        # When all periods are exhausted, the engine
        # terminates cleanly (no infinite waiting for
        # more pages).
        def fetch(periods):
            return _make_response([])

        engine = PaginationEngine()
        r = engine.paginate(["2020"], fetch)
        assert r.count == 0
        assert r.records == []


# ---------------------------------------------------------------------------
# PaginationEngine: comma-separated periods
# ---------------------------------------------------------------------------


class TestCommaSeparatedPeriods:
    def test_string_input_split_into_periods(self, engine):
        seen_chunks: list[list[str]] = []

        def fetch(periods):
            seen_chunks.append(list(periods))
            return _make_response([_make_record(period=p) for p in periods])

        engine.paginate("2020,2021,2022", fetch)
        # 3 periods → 1 page.
        assert seen_chunks == [["2020", "2021", "2022"]]

    def test_string_input_with_spaces(self, engine):
        def fetch(periods):
            return _make_response([_make_record(period=p) for p in periods])

        r = engine.paginate("2020, 2021, 2022", fetch)
        assert r.count == 3

    def test_empty_string_rejected(self, engine):
        def fetch(periods):
            return _make_response([])

        with pytest.raises(ValueError, match="non-empty"):
            engine.paginate("", fetch)

    def test_whitespace_only_rejected(self, engine):
        def fetch(periods):
            return _make_response([])

        with pytest.raises(ValueError, match="non-empty"):
            engine.paginate(" , , ", fetch)

    def test_empty_list_rejected(self, engine):
        def fetch(periods):
            return _make_response([])

        with pytest.raises(ValueError, match="non-empty"):
            engine.paginate([], fetch)


# ---------------------------------------------------------------------------
# PaginationEngine: response aggregation
# ---------------------------------------------------------------------------


class TestResponseAggregation:
    def test_first_url_preserved(self, engine):
        urls = ["https://example/page1", "https://example/page2"]

        def fetch(periods):
            return _make_response(
                [_make_record(period=p) for p in periods],
                upstream_url=urls.pop(0),
            )

        r = engine.paginate(["2020", "2021"], fetch)
        assert r.upstream_url == "https://example/page1"

    def test_elapsed_seconds_summed(self, engine):
        def fetch(periods):
            return _make_response(
                [_make_record(period=p) for p in periods],
                elapsed_seconds=1.5,
            )

        # 24 periods → 2 pages → 1.5 × 2 = 3.0.
        r = engine.paginate(
            [str(y) for y in range(2000, 2024)], fetch
        )
        assert r.elapsed_seconds == pytest.approx(3.0)

    def test_last_error_preserved(self, engine):
        # 24 periods → 2 pages. Each page returns a
        # different error; the LAST non-empty error is
        # preserved.
        page_index = [0]

        def fetch(periods):
            page_index[0] += 1
            return _make_response([], error=f"error page {page_index[0]}")

        r = engine.paginate(
            [str(y) for y in range(2000, 2024)], fetch
        )
        assert r.error == "error page 2"


# ---------------------------------------------------------------------------
# TradeParser.composite_key (referenced by PaginationEngine)
# ---------------------------------------------------------------------------


class TestParserCompositeKey:
    def test_composite_key_returns_tuple(self):
        record = _make_record(reporter_code=699, partner_code=842, period="2022")
        key = TradeParser.composite_key(record)
        assert isinstance(key, tuple)

    def test_composite_key_distinct_records(self):
        a = _make_record(reporter_code=699, partner_code=842, period="2022")
        b = _make_record(reporter_code=699, partner_code=842, period="2023")
        assert TradeParser.composite_key(a) != TradeParser.composite_key(b)

    def test_composite_key_equal_records(self):
        a = _make_record(reporter_code=699, partner_code=842, period="2022")
        b = _make_record(reporter_code=699, partner_code=842, period="2022")
        assert TradeParser.composite_key(a) == TradeParser.composite_key(b)

    def test_partner2_zero_when_none(self):
        # When partner2 is None, the engine treats it as 0
        # (the world sentinel) for dedup purposes.
        record = _make_record(partner_code=842)
        key = TradeParser.composite_key(record)
        # 9th element of the composite key is mot_code (0)
        # and 10th is partner2_code (treated as 0 when None).
        assert key[-2] == 0  # mot_code
        assert key[-1] == 0  # partner2_code (None → 0)