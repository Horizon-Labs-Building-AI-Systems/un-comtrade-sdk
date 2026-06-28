"""Tests for the country-level analytics (P6-002).

Per the P6-002 task scope, this module covers:

- **`total_imports`** — sum of imports for a
  reporter (with optional year filter).
- **`total_exports`** — sum of exports for a
  reporter (with optional year filter).
- **`country_ranking`** — rank reporters by
  total trade / exports / imports / balance /
  record count.
- **`country_summary`** — one-stop per-reporter
  summary (totals, balance, partner count,
  year range).
- **`country_trend`** — exports / imports /
  balance over time (yearly or per-period).

Coverage:

- `TestTotalImports` — basic, with reporter
  filter, with year filter, with years tuple,
  no matching records, mutual exclusion,
  bad source type.
- `TestTotalExports` — mirror of `total_imports`.
- `TestCountryRanking` — by total / exports /
  imports / balance / record_count, with flow
  filter, with limit, ascending / descending,
  unknown field, empty dataset.
- `TestCountryRankingRow` — frozen dataclass,
  Decimal invariants.
- `TestCountrySummary` — exports + imports +
  balance + trade + partner_count + year_range,
  unknown reporter returns `None`.
- `TestCountrySummaryFrozen` — frozen dataclass.
- `TestCountryTrend` — yearly granularity,
  per-period granularity, empty dataset,
  unknown granularity, ascending sort.
- `TestCountryTrendPoint` — frozen dataclass.
- `TestInputsRejected` — non-canonical dataset
  source for each function.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal
from typing import Any

import pytest

from un_comtrade.analytics import (
    CountryAnalyticsError,
    CountryRankingRow,
    CountrySummary,
    CountryTrend,
    CountryTrendPoint,
    country_ranking,
    country_summary,
    country_trend,
    total_exports,
    total_imports,
)
from un_comtrade.parser import TradeParser
from un_comtrade.transform import CanonicalDataset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _baseline_raw(**overrides) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "typeCode": "C",
        "freqCode": "A",
        "classificationCode": "H6",
        "classificationSearchCode": "HS",
        "isOriginalClassification": True,
        "refPeriodId": 20220101,
        "refYear": 2022,
        "refMonth": 52,
        "period": "2022",
        "reporterCode": 699,
        "reporterISO": "IND",
        "reporterDesc": "India",
        "flowCode": "X",
        "flowDesc": "Export",
        "partnerCode": 0,
        "partnerISO": "W00",
        "partnerDesc": "World",
        "partner2Code": 0,
        "partner2ISO": "W00",
        "partner2Desc": "World",
        "cmdCode": "TOTAL",
        "cmdDesc": "All Commodities",
        "customsCode": "C00",
        "customsDesc": "TOTAL CPC",
        "mosCode": "0",
        "motCode": 0,
        "motDesc": "TOTAL MOT",
        "qtyUnitCode": -1,
        "qtyUnitAbbr": "N/A",
        "qty": 0,
        "isQtyEstimated": False,
        "altQtyUnitCode": -1,
        "altQtyUnitAbbr": "N/A",
        "altQty": 0,
        "isAltQtyEstimated": False,
        "netWgt": 0,
        "isNetWgtEstimated": True,
        "grossWgt": 0,
        "isGrossWgtEstimated": False,
        "cifvalue": None,
        "fobvalue": 100.0,
        "primaryValue": 100.0,
        "legacyEstimationFlag": 0,
        "isReported": False,
        "isAggregate": True,
    }
    raw.update(overrides)
    return raw


def _records(*tuples) -> tuple:
    """Build parsed `TradeRecord`s from tuples of
    `(reporter, partner, period, flow, value)`.
    Vary `period` / `partner` per tuple so the
    parser's composite-key dedup keeps all rows.

    `refYear` is extracted from the first 4 chars
    of `period` (the parser validates it to be
    within 1900..2100), and `refPeriodId` is
    computed as `int(period) * 10000 + 1` so that
    intra-year periods like "202201" and "202202"
    get distinct `ref_period_id`s and therefore
    distinct composite keys.
    """
    raws = []
    for t in tuples:
        reporter, partner, period, flow, value = t
        ref_year = int(period[:4])
        period_id = int(period) * 10000 + 1
        raws.append(
            _baseline_raw(
                reporterCode=reporter,
                partnerCode=partner,
                period=period,
                refYear=ref_year,
                refPeriodId=period_id,
                flowCode=flow,
                fobvalue=value,
                primaryValue=value,
            )
        )
    return tuple(
        TradeParser(log_skipped=False).parse_records(raws).records
    )


def _make_dataset(records, *, name: str = "p") -> CanonicalDataset:
    return CanonicalDataset(
        name=name, records=records, parser_name="TradeParser"
    )


# ---------------------------------------------------------------------------
# TestTotalImports
# ---------------------------------------------------------------------------


class TestTotalImports:
    def test_returns_decimal(self):
        records = _records((699, 0, "2022", "M", 100.0),)
        value = total_imports(_make_dataset(records))
        assert isinstance(value, Decimal)
        assert value == Decimal("100")

    def test_filters_by_flow(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2022", "M", 50.0),
        )
        # Only the import record contributes.
        assert total_imports(_make_dataset(records)) == Decimal("50")

    def test_filters_by_reporter(self):
        records = _records(
            (699, 0, "2022", "M", 100.0),
            (156, 0, "2022", "M", 200.0),
        )
        assert total_imports(
            _make_dataset(records), reporter_code=699
        ) == Decimal("100")

    def test_filters_by_year(self):
        records = _records(
            (699, 0, "2022", "M", 100.0),
            (699, 0, "2023", "M", 200.0),
        )
        assert total_imports(
            _make_dataset(records), year=2022
        ) == Decimal("100")
        assert total_imports(
            _make_dataset(records), year=2023
        ) == Decimal("200")

    def test_filters_by_years_tuple(self):
        records = _records(
            (699, 0, "2020", "M", 100.0),
            (699, 0, "2021", "M", 200.0),
            (699, 0, "2022", "M", 300.0),
            (699, 0, "2023", "M", 400.0),
        )
        assert total_imports(
            _make_dataset(records), years=(2021, 2022)
        ) == Decimal("500")

    def test_year_and_years_mutually_exclusive(self):
        records = _records((699, 0, "2022", "M", 100.0),)
        with pytest.raises(
            CountryAnalyticsError, match="mutually exclusive"
        ):
            total_imports(
                _make_dataset(records),
                year=2022,
                years=(2021, 2022),
            )

    def test_no_matching_records_returns_zero(self):
        records = _records((699, 0, "2022", "X", 100.0),)
        # No import records → Decimal("0").
        assert total_imports(_make_dataset(records)) == Decimal("0")

    def test_empty_dataset_returns_zero(self):
        assert total_imports(_make_dataset(())) == Decimal("0")

    def test_rejects_non_canonical(self):
        with pytest.raises(CountryAnalyticsError, match="CanonicalDataset"):
            total_imports([{"raw": "dict"}])


# ---------------------------------------------------------------------------
# TestTotalExports
# ---------------------------------------------------------------------------


class TestTotalExports:
    def test_returns_decimal(self):
        records = _records((699, 0, "2022", "X", 100.0),)
        assert total_exports(_make_dataset(records)) == Decimal("100")

    def test_filters_by_flow(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2022", "M", 50.0),
        )
        assert total_exports(_make_dataset(records)) == Decimal("100")

    def test_filters_by_reporter(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (156, 0, "2022", "X", 200.0),
        )
        assert total_exports(
            _make_dataset(records), reporter_code=699
        ) == Decimal("100")

    def test_year_filter(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
        )
        assert total_exports(
            _make_dataset(records), years=(2023,)
        ) == Decimal("200")

    def test_year_and_years_mutually_exclusive(self):
        records = _records((699, 0, "2022", "X", 100.0),)
        with pytest.raises(
            CountryAnalyticsError, match="mutually exclusive"
        ):
            total_exports(
                _make_dataset(records),
                year=2022,
                years=(2022,),
            )

    def test_no_matching_records_returns_zero(self):
        records = _records((699, 0, "2022", "M", 100.0),)
        assert total_exports(_make_dataset(records)) == Decimal("0")

    def test_rejects_non_canonical(self):
        with pytest.raises(CountryAnalyticsError, match="CanonicalDataset"):
            total_exports("not a dataset")


# ---------------------------------------------------------------------------
# TestCountryRankingRow
# ---------------------------------------------------------------------------


class TestCountryRankingRow:
    def test_frozen(self):
        row = CountryRankingRow(
            reporter_code=699,
            reporter_iso3="IND",
            reporter_name="India",
            total_exports=Decimal("100"),
            total_imports=Decimal("50"),
            total_trade_value=Decimal("150"),
            trade_balance=Decimal("50"),
            record_count=4,
        )
        with pytest.raises(FrozenInstanceError):
            row.reporter_code = 999  # type: ignore[misc]

    def test_decimal_invariants(self):
        with pytest.raises(CountryAnalyticsError, match="Decimal"):
            CountryRankingRow(
                reporter_code=699,
                reporter_iso3=None,
                reporter_name=None,
                total_exports="not a decimal",  # type: ignore[arg-type]
                total_imports=Decimal("50"),
                total_trade_value=Decimal("150"),
                trade_balance=Decimal("50"),
                record_count=4,
            )

    def test_balance_consistency(self):
        row = CountryRankingRow(
            reporter_code=699,
            reporter_iso3="IND",
            reporter_name="India",
            total_exports=Decimal("100"),
            total_imports=Decimal("30"),
            total_trade_value=Decimal("130"),
            trade_balance=Decimal("70"),
            record_count=4,
        )
        # Balance = exports - imports.
        assert row.trade_balance == (
            row.total_exports - row.total_imports
        )
        # Total trade = exports + imports.
        assert row.total_trade_value == (
            row.total_exports + row.total_imports
        )


# ---------------------------------------------------------------------------
# TestCountryRanking
# ---------------------------------------------------------------------------


class TestCountryRanking:
    def _two_country_dataset(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
            (699, 0, "2022", "M", 50.0),
            (156, 0, "2022", "X", 400.0),
            (156, 0, "2022", "M", 150.0),
        )
        return _make_dataset(records)

    def test_returns_tuple(self):
        result = country_ranking(self._two_country_dataset())
        assert isinstance(result, tuple)
        assert all(isinstance(r, CountryRankingRow) for r in result)

    def test_default_sort_descending_by_total(self):
        rows = country_ranking(self._two_country_dataset())
        # India (699) total = 100+200+50 = 350
        # China (156) total = 400+150 = 550
        # Default: descending → China first.
        assert rows[0].reporter_code == 156
        assert rows[1].reporter_code == 699

    def test_by_exports(self):
        rows = country_ranking(self._two_country_dataset(), by="exports")
        # India exports = 300, China exports = 400
        assert rows[0].reporter_code == 156
        assert rows[1].reporter_code == 699

    def test_by_imports(self):
        rows = country_ranking(self._two_country_dataset(), by="imports")
        # China imports = 150, India imports = 50
        assert rows[0].reporter_code == 156
        assert rows[1].reporter_code == 699

    def test_by_trade_balance(self):
        rows = country_ranking(
            self._two_country_dataset(), by="trade_balance"
        )
        # China balance = 400-150 = 250
        # India balance = 300-50 = 250
        # Equal — but the sort is stable.
        balances = {r.reporter_code: r.trade_balance for r in rows}
        assert balances[699] == Decimal("250")
        assert balances[156] == Decimal("250")

    def test_by_record_count(self):
        rows = country_ranking(
            self._two_country_dataset(), by="record_count"
        )
        # India = 3 records, China = 2 records.
        assert rows[0].reporter_code == 699
        assert rows[0].record_count == 3

    def test_ascending_sort(self):
        rows = country_ranking(
            self._two_country_dataset(), descending=False
        )
        # Ascending by total → India first (350 <
        # 550).
        assert rows[0].reporter_code == 699
        assert rows[1].reporter_code == 156

    def test_flow_filter_export(self):
        rows = country_ranking(
            self._two_country_dataset(), flow="X"
        )
        # Only exports count toward the rank value.
        # India exports = 300, China exports = 400.
        assert rows[0].reporter_code == 156
        assert rows[0].total_exports == Decimal("400")
        # Imports are zeroed when flow="X".
        assert rows[0].total_imports == Decimal("0")

    def test_flow_filter_import(self):
        rows = country_ranking(
            self._two_country_dataset(), flow="M"
        )
        # Only imports count toward the rank value.
        # India imports = 50, China imports = 150.
        assert rows[0].reporter_code == 156
        assert rows[0].total_imports == Decimal("150")
        assert rows[0].total_exports == Decimal("0")

    def test_limit(self):
        rows = country_ranking(
            self._two_country_dataset(), limit=1
        )
        assert len(rows) == 1
        assert rows[0].reporter_code == 156

    def test_limit_zero(self):
        rows = country_ranking(
            self._two_country_dataset(), limit=0
        )
        assert rows == ()

    def test_empty_dataset_returns_empty_tuple(self):
        assert country_ranking(_make_dataset(())) == ()

    def test_unknown_field_raises(self):
        with pytest.raises(CountryAnalyticsError, match="Unknown ranking"):
            country_ranking(self._two_country_dataset(), by="nope")

    def test_negative_limit_raises(self):
        with pytest.raises(CountryAnalyticsError, match="non-negative"):
            country_ranking(self._two_country_dataset(), limit=-1)

    def test_rejects_non_canonical(self):
        with pytest.raises(CountryAnalyticsError, match="CanonicalDataset"):
            country_ranking([{"raw": "dict"}])

    def test_iso3_metadata_captured(self):
        rows = country_ranking(self._two_country_dataset())
        by_code = {r.reporter_code: r for r in rows}
        assert by_code[699].reporter_iso3 == "IND"
        assert by_code[699].reporter_name == "India"


# ---------------------------------------------------------------------------
# TestCountrySummary
# ---------------------------------------------------------------------------


class TestCountrySummary:
    def _dataset(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
            (699, 0, "2022", "M", 50.0),
            (699, 124, "2022", "X", 300.0),
            (156, 0, "2022", "X", 400.0),
        )
        return _make_dataset(records)

    def test_returns_country_summary(self):
        s = country_summary(self._dataset(), 699)
        assert isinstance(s, CountrySummary)

    def test_exports_imports_balance(self):
        s = country_summary(self._dataset(), 699)
        # India exports = 100 + 200 + 300 = 600
        # India imports = 50
        # Balance = 550
        # Total trade = 650
        assert s.total_exports == Decimal("600")
        assert s.total_imports == Decimal("50")
        assert s.trade_balance == Decimal("550")
        assert s.total_trade == Decimal("650")

    def test_partner_count(self):
        s = country_summary(self._dataset(), 699)
        # Two distinct partners (0, 124).
        assert s.partner_count == 2

    def test_record_count(self):
        s = country_summary(self._dataset(), 699)
        assert s.record_count == 4

    def test_year_range(self):
        s = country_summary(self._dataset(), 699)
        # 2022, 2022, 2022, 2023 → range (2022, 2023)
        assert s.year_range == (2022, 2023)

    def test_iso3_metadata(self):
        s = country_summary(self._dataset(), 699)
        assert s.reporter_iso3 == "IND"
        assert s.reporter_name == "India"

    def test_unknown_reporter_returns_none(self):
        assert country_summary(self._dataset(), 842) is None

    def test_single_record_year_range(self):
        records = _records((699, 0, "2022", "X", 100.0),)
        s = country_summary(_make_dataset(records), 699)
        assert s.year_range == (2022, 2022)

    def test_rejects_non_canonical(self):
        with pytest.raises(CountryAnalyticsError, match="CanonicalDataset"):
            country_summary("not a dataset", 699)


# ---------------------------------------------------------------------------
# TestCountrySummaryFrozen
# ---------------------------------------------------------------------------


class TestCountrySummaryFrozen:
    def test_frozen(self):
        s = CountrySummary(
            reporter_code=699,
            reporter_iso3="IND",
            reporter_name="India",
            total_exports=Decimal("100"),
            total_imports=Decimal("50"),
            total_trade=Decimal("150"),
            trade_balance=Decimal("50"),
            partner_count=2,
            record_count=4,
            year_range=(2022, 2023),
        )
        with pytest.raises(FrozenInstanceError):
            s.reporter_code = 999  # type: ignore[misc]

    def test_decimal_invariants(self):
        with pytest.raises(CountryAnalyticsError, match="Decimal"):
            CountrySummary(
                reporter_code=699,
                reporter_iso3=None,
                reporter_name=None,
                total_exports="not a decimal",  # type: ignore[arg-type]
                total_imports=Decimal("50"),
                total_trade=Decimal("150"),
                trade_balance=Decimal("50"),
                partner_count=2,
                record_count=4,
                year_range=(2022, 2023),
            )


# ---------------------------------------------------------------------------
# TestCountryTrend
# ---------------------------------------------------------------------------


class TestCountryTrend:
    def _dataset(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
            (699, 0, "2022", "M", 50.0),
            (699, 124, "2022", "X", 300.0),
            (699, 0, "2023", "M", 75.0),
        )
        return _make_dataset(records)

    def test_returns_country_trend(self):
        t = country_trend(self._dataset(), 699)
        assert isinstance(t, CountryTrend)

    def test_yearly_granularity_one_point_per_year(self):
        t = country_trend(self._dataset(), 699)
        # 2 distinct years (2022, 2023) → 2 points.
        assert len(t.points) == 2
        years = sorted(p.year for p in t.points)
        assert years == [2022, 2023]

    def test_yearly_points_sorted(self):
        t = country_trend(self._dataset(), 699)
        # Ascending by (year, period).
        pairs = [(p.year, p.period) for p in t.points]
        assert pairs == sorted(pairs)

    def test_yearly_2022_point(self):
        t = country_trend(self._dataset(), 699)
        p_2022 = next(p for p in t.points if p.year == 2022)
        # 2022: X = 100 + 300 = 400, M = 50
        assert p_2022.exports == Decimal("400")
        assert p_2022.imports == Decimal("50")
        assert p_2022.total_trade == Decimal("450")
        assert p_2022.trade_balance == Decimal("350")
        assert p_2022.record_count == 3

    def test_yearly_2023_point(self):
        t = country_trend(self._dataset(), 699)
        p_2023 = next(p for p in t.points if p.year == 2023)
        # 2023: X = 200, M = 75
        assert p_2023.exports == Decimal("200")
        assert p_2023.imports == Decimal("75")
        assert p_2023.trade_balance == Decimal("125")
        assert p_2023.record_count == 2

    def test_per_period_granularity(self):
        # Different periods within the same year.
        records = _records(
            (699, 0, "202201", "X", 100.0),
            (699, 0, "202202", "X", 200.0),
            (699, 0, "202201", "M", 50.0),
        )
        t = country_trend(
            _make_dataset(records), 699, granularity="period"
        )
        # Two periods → 2 points.
        assert len(t.points) == 2
        periods = sorted(p.period for p in t.points)
        assert periods == ["202201", "202202"]

    def test_unknown_granularity_raises(self):
        with pytest.raises(
            CountryAnalyticsError, match="granularity"
        ):
            country_trend(self._dataset(), 699, granularity="daily")

    def test_unknown_reporter_returns_empty_trend(self):
        t = country_trend(self._dataset(), 842)
        assert isinstance(t, CountryTrend)
        assert t.reporter_code == 842
        assert t.points == ()

    def test_empty_dataset_returns_empty_trend(self):
        t = country_trend(_make_dataset(()), 699)
        assert t.points == ()

    def test_trend_years_property(self):
        t = country_trend(self._dataset(), 699)
        assert t.years == (2022, 2023)

    def test_trend_total_exports_property(self):
        t = country_trend(self._dataset(), 699)
        # Sum of all point exports: 400 + 200 = 600
        assert t.total_exports == Decimal("600")

    def test_trend_total_imports_property(self):
        t = country_trend(self._dataset(), 699)
        # Sum of all point imports: 50 + 75 = 125
        assert t.total_imports == Decimal("125")

    def test_trend_total_trade_property(self):
        t = country_trend(self._dataset(), 699)
        assert t.total_trade == Decimal("725")

    def test_rejects_non_canonical(self):
        with pytest.raises(CountryAnalyticsError, match="CanonicalDataset"):
            country_trend("not a dataset", 699)


# ---------------------------------------------------------------------------
# TestCountryTrendPoint
# ---------------------------------------------------------------------------


class TestCountryTrendPoint:
    def test_frozen(self):
        p = CountryTrendPoint(
            year=2022,
            period="2022",
            exports=Decimal("100"),
            imports=Decimal("50"),
            total_trade=Decimal("150"),
            trade_balance=Decimal("50"),
            record_count=3,
        )
        with pytest.raises(FrozenInstanceError):
            p.year = 9999  # type: ignore[misc]

    def test_decimal_invariants(self):
        with pytest.raises(CountryAnalyticsError, match="Decimal"):
            CountryTrendPoint(
                year=2022,
                period="2022",
                exports="not a decimal",  # type: ignore[arg-type]
                imports=Decimal("50"),
                total_trade=Decimal("150"),
                trade_balance=Decimal("50"),
                record_count=3,
            )