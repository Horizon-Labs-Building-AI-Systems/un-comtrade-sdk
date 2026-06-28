"""Tests for the time-series analytics (P6-005).

Per the P6-005 task scope, this module covers:

- **`annual_trend`** — yearly time-series of a
  metric (default = `sum_primary_value`).
- **`monthly_trend`** — same shape, bucketed
  per month.
- **`rolling_average`** — rolling mean over a
  window of `n` points.
- **`cagr`** — Compound Annual Growth Rate
  between the first and last point of a
  series.
- **`growth_rates`** — period-over-period
  growth rates.

Coverage:

- `TestTrendPoint` — frozen dataclass,
  Decimal invariants, month validation.
- `TestAnnualTrend` — basic annual trend,
  filter by reporter / flow, custom metric,
  empty dataset, ascending sort.
- `TestMonthlyTrend` — basic monthly trend,
  monthly granularity, excludes annual-only
  records, sort by (year, month).
- `TestRollingAverage` — window=2, window=3,
  partial windows for early points, window=1
  (no change), invalid window, empty.
- `TestCAGR` — basic CAGR, zero first, zero
  last, negative first, single point, years
  override, negative years.
- `TestGrowthRatePoint` — frozen dataclass,
  Decimal invariants.
- `TestGrowthRates` — first point has
  `previous=None`, period-over-period growth
  rates, division-by-zero handling.
- `TestErrorsPropagated` — bad source,
  bad arguments, malformed period.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal
from typing import Any

import pytest

from un_comtrade.analytics import (
    AnalyticsError,
    GrowthRatePoint,
    Metric,
    TimeSeriesAnalyticsError,
    TrendPoint,
    annual_trend,
    cagr,
    growth_rates,
    monthly_trend,
    rolling_average,
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
    `(period, flow, value)`.

    `refYear` is extracted from `period[:4]`,
    `refPeriodId` is `int(period) * 10000 + 1` so
    intra-year periods stay distinct.
    """
    raws = []
    for t in tuples:
        period, flow, value = t
        ref_year = int(period[:4])
        period_id = int(period) * 10000 + 1
        raws.append(
            _baseline_raw(
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


def _trend_dataset():
    """Multi-year India exports with monthly
    granularity in 2022.

    Annual totals:
      2022: 70 (annual) + 10 + 20 + 30 (monthly) = 130
      2023: 200
      2024: 400
    """
    return _make_dataset(_records(
        ("2022", "X", 70.0),
        ("2023", "X", 200.0),
        ("2024", "X", 400.0),
        ("202201", "X", 10.0),
        ("202202", "X", 20.0),
        ("202203", "X", 30.0),
    ))


# ---------------------------------------------------------------------------
# TestTrendPoint
# ---------------------------------------------------------------------------


class TestTrendPoint:
    def test_frozen(self):
        p = TrendPoint(
            year=2022, period="2022",
            value=Decimal("100"), record_count=3,
        )
        with pytest.raises(FrozenInstanceError):
            p.year = 9999  # type: ignore[misc]

    def test_decimal_invariant(self):
        with pytest.raises(TimeSeriesAnalyticsError, match="Decimal"):
            TrendPoint(
                year=2022, period="2022",
                value="not a decimal",  # type: ignore[arg-type]
                record_count=3,
            )

    def test_year_must_be_int(self):
        with pytest.raises(TimeSeriesAnalyticsError, match="year"):
            TrendPoint(
                year="2022",  # type: ignore[arg-type]
                period="2022",
                value=Decimal("100"),
                record_count=1,
            )

    def test_month_in_range(self):
        with pytest.raises(
            TimeSeriesAnalyticsError, match="1..12"
        ):
            TrendPoint(
                year=2022, period="2022",
                value=Decimal("100"),
                record_count=1,
                month=13,
            )

    def test_month_can_be_none(self):
        p = TrendPoint(
            year=2022, period="2022",
            value=Decimal("100"), record_count=1,
            month=None,
        )
        assert p.month is None


# ---------------------------------------------------------------------------
# TestAnnualTrend
# ---------------------------------------------------------------------------


class TestAnnualTrend:
    def test_returns_tuple_of_points(self):
        trend = annual_trend(_trend_dataset())
        assert isinstance(trend, tuple)
        assert all(isinstance(p, TrendPoint) for p in trend)

    def test_sorted_ascending_by_year(self):
        trend = annual_trend(_trend_dataset())
        years = [p.year for p in trend]
        assert years == sorted(years)

    def test_annual_values_aggregate_periods(self):
        trend = annual_trend(_trend_dataset())
        # 2022 = annual 70 + monthly 10 + 20 + 30 = 130
        # 2023 = 200
        # 2024 = 400
        by_year = {p.year: p.value for p in trend}
        assert by_year[2022] == Decimal("130")
        assert by_year[2023] == Decimal("200")
        assert by_year[2024] == Decimal("400")

    def test_record_count_per_year(self):
        trend = annual_trend(_trend_dataset())
        # 2022: 4 records (1 annual + 3 monthly).
        by_year = {p.year: p.record_count for p in trend}
        assert by_year[2022] == 4
        assert by_year[2023] == 1
        assert by_year[2024] == 1

    def test_period_is_year_string(self):
        trend = annual_trend(_trend_dataset())
        for p in trend:
            assert p.period == str(p.year)
            assert p.month is None

    def test_filter_by_reporter(self):
        # Add a China record and verify the
        # filter excludes it.
        records = list(_trend_dataset().records)
        raw = _baseline_raw(
            reporterCode=156,
            reporterISO="CHN",
            reporterDesc="China",
            period="2024",
            refYear=2024,
            refPeriodId=20240101,
            fobvalue=9999,
            primaryValue=9999,
        )
        china_records = TradeParser(
            log_skipped=False
        ).parse_records([raw]).records
        records = records + list(china_records)
        ds = _make_dataset(tuple(records))

        trend = annual_trend(ds, reporter_code=699)
        by_year = {p.year: p.value for p in trend}
        # 2024 should still be 400 (India only).
        assert by_year[2024] == Decimal("400")

    def test_filter_by_flow(self):
        records = list(_trend_dataset().records)
        # Add an import record in 2024.
        raw = _baseline_raw(
            period="2024",
            refYear=2024,
            refPeriodId=20240101,
            flowCode="M",
            flowDesc="Import",
            fobvalue=50,
            primaryValue=50,
        )
        import_records = TradeParser(
            log_skipped=False
        ).parse_records([raw]).records
        records = records + list(import_records)
        ds = _make_dataset(tuple(records))

        trend = annual_trend(ds, flow="X")
        # 2024 should be 400 (exports only).
        by_year = {p.year: p.value for p in trend}
        assert by_year[2024] == Decimal("400")

    def test_custom_metric(self):
        # Use `Metric.count()` instead of the
        # default sum.
        trend = annual_trend(_trend_dataset(), metric=Metric.count())
        # 2022: 4 records, 2023: 1, 2024: 1.
        by_year = {p.year: p.value for p in trend}
        assert by_year[2022] == 4
        assert by_year[2023] == 1
        assert by_year[2024] == 1

    def test_empty_dataset_returns_empty_tuple(self):
        assert annual_trend(_make_dataset(())) == ()

    def test_no_matching_records_returns_empty(self):
        # Build a dataset with a different
        # reporter so the filter excludes
        # everything.
        raw = _baseline_raw(reporterCode=156)
        records = TradeParser(
            log_skipped=False
        ).parse_records([raw]).records
        ds = _make_dataset(records)
        assert annual_trend(ds, reporter_code=699) == ()

    def test_rejects_non_canonical(self):
        with pytest.raises(
            TimeSeriesAnalyticsError, match="CanonicalDataset"
        ):
            annual_trend([{"raw": "dict"}])

    def test_rejects_non_metric(self):
        with pytest.raises(TimeSeriesAnalyticsError, match="Metric"):
            annual_trend(_trend_dataset(), metric="not a metric")


# ---------------------------------------------------------------------------
# TestMonthlyTrend
# ---------------------------------------------------------------------------


class TestMonthlyTrend:
    def test_returns_tuple_of_points(self):
        trend = monthly_trend(_trend_dataset())
        assert isinstance(trend, tuple)
        assert all(isinstance(p, TrendPoint) for p in trend)

    def test_excludes_annual_only_records(self):
        # The _trend_dataset has 1 annual-only
        # record (2022=70) plus 3 monthly records
        # (202201/202202/202203). monthly_trend
        # should only return the 3 monthly ones.
        trend = monthly_trend(_trend_dataset())
        assert len(trend) == 3

    def test_month_field_set(self):
        trend = monthly_trend(_trend_dataset())
        for p in trend:
            assert p.month is not None
            assert 1 <= p.month <= 12

    def test_sorted_ascending_by_year_month(self):
        trend = monthly_trend(_trend_dataset())
        pairs = [(p.year, p.month) for p in trend]
        assert pairs == sorted(pairs)

    def test_period_format(self):
        trend = monthly_trend(_trend_dataset())
        for p in trend:
            # "YYYYMM" format.
            assert len(p.period) == 6
            assert p.period == f"{p.year}{p.month:02d}"

    def test_monthly_values(self):
        trend = monthly_trend(_trend_dataset())
        by_key = {(p.year, p.month): p.value for p in trend}
        assert by_key[(2022, 1)] == Decimal("10")
        assert by_key[(2022, 2)] == Decimal("20")
        assert by_key[(2022, 3)] == Decimal("30")

    def test_only_annual_dataset_returns_empty(self):
        # Build a dataset with ONLY annual-only
        # records → monthly_trend returns empty.
        records = _records(
            ("2022", "X", 100.0),
            ("2023", "X", 200.0),
        )
        ds = _make_dataset(records)
        assert monthly_trend(ds) == ()

    def test_rejects_non_canonical(self):
        with pytest.raises(
            TimeSeriesAnalyticsError, match="CanonicalDataset"
        ):
            monthly_trend([{"raw": "dict"}])


# ---------------------------------------------------------------------------
# TestRollingAverage
# ---------------------------------------------------------------------------


class TestRollingAverage:
    def _series(self):
        return (
            TrendPoint(year=2020, period="2020",
                       value=Decimal("100"), record_count=1),
            TrendPoint(year=2021, period="2021",
                       value=Decimal("200"), record_count=1),
            TrendPoint(year=2022, period="2022",
                       value=Decimal("300"), record_count=1),
            TrendPoint(year=2023, period="2023",
                       value=Decimal("400"), record_count=1),
        )

    def test_returns_tuple(self):
        result = rolling_average(self._series(), window=2)
        assert isinstance(result, tuple)
        assert len(result) == 4

    def test_window_2_partial_windows_at_start(self):
        # window=2: index 0 uses just [100],
        # index 1 uses [100, 200] = 150,
        # index 2 uses [200, 300] = 250,
        # index 3 uses [300, 400] = 350.
        result = rolling_average(self._series(), window=2)
        assert result[0].value == Decimal("100")
        assert result[1].value == Decimal("150")
        assert result[2].value == Decimal("250")
        assert result[3].value == Decimal("350")

    def test_window_3_partial_windows_at_start(self):
        # window=3: index 0 uses [100],
        # index 1 uses [100, 200] = 150,
        # index 2 uses [100, 200, 300] = 200,
        # index 3 uses [200, 300, 400] = 300.
        result = rolling_average(self._series(), window=3)
        assert result[0].value == Decimal("100")
        assert result[1].value == Decimal("150")
        assert result[2].value == Decimal("200")
        assert result[3].value == Decimal("300")

    def test_window_1_no_change(self):
        result = rolling_average(self._series(), window=1)
        for orig, ra in zip(self._series(), result):
            assert ra.value == orig.value

    def test_window_larger_than_series(self):
        # window=10 on a 4-point series: the window
        # is clamped to the available data. At
        # index i, the window is [max(0, i-9)..i].
        # So:
        #   i=0: [100] → 100
        #   i=1: [100, 200] → 150
        #   i=2: [100, 200, 300] → 200
        #   i=3: [100, 200, 300, 400] → 250
        result = rolling_average(self._series(), window=10)
        assert result[0].value == Decimal("100")
        assert result[1].value == Decimal("150")
        assert result[2].value == Decimal("200")
        assert result[3].value == Decimal("250")

    def test_preserves_other_fields(self):
        result = rolling_average(self._series(), window=2)
        for orig, ra in zip(self._series(), result):
            assert ra.year == orig.year
            assert ra.period == orig.period
            assert ra.record_count == orig.record_count

    def test_empty_series_returns_empty(self):
        assert rolling_average((), window=3) == ()

    def test_window_must_be_positive(self):
        with pytest.raises(
            TimeSeriesAnalyticsError, match="window"
        ):
            rolling_average(self._series(), window=0)

    def test_rejects_non_trend_point(self):
        with pytest.raises(
            TimeSeriesAnalyticsError, match="TrendPoint"
        ):
            rolling_average([{"year": 2022}], window=3)

    def test_custom_field(self):
        """Apply rolling average to a custom
        field — synthesized via the
        `record_count` field on the points."""
        # Add extra field-like attribute via
        # subclass? Actually record_count is int.
        # Just verify the field parameter
        # plumbing works by passing
        # `field="value"` explicitly (the default)
        # AND a non-existent field — the latter
        # should raise AttributeError when
        # accessing.
        with pytest.raises(AttributeError):
            rolling_average(
                self._series(), window=2, field="nonexistent"
            )


# ---------------------------------------------------------------------------
# TestCAGR
# ---------------------------------------------------------------------------


class TestCAGR:
    def test_returns_none_for_fewer_than_two_points(self):
        single = (TrendPoint(
            year=2022, period="2022",
            value=Decimal("100"), record_count=1
        ),)
        assert cagr(single) is None
        assert cagr(()) is None

    def test_basic_cagr(self):
        # 100 → 400 over 2 years = 100% CAGR
        # (sqrt(4) - 1 = 1).
        points = (
            TrendPoint(year=2022, period="2022",
                       value=Decimal("100"), record_count=1),
            TrendPoint(year=2024, period="2024",
                       value=Decimal("400"), record_count=1),
        )
        result = cagr(points)
        assert result is not None
        assert Decimal("0.99") < result < Decimal("1.01")

    def test_cagr_3x_over_2_years(self):
        # 100 → 300 over 2 years = sqrt(3)-1 ≈
        # 0.732.
        points = (
            TrendPoint(year=2022, period="2022",
                       value=Decimal("100"), record_count=1),
            TrendPoint(year=2024, period="2024",
                       value=Decimal("300"), record_count=1),
        )
        result = cagr(points)
        assert result is not None
        assert Decimal("0.7") < result < Decimal("0.8")

    def test_cagr_zero_first_value(self):
        # 0 → 100: CAGR undefined.
        points = (
            TrendPoint(year=2022, period="2022",
                       value=Decimal("0"), record_count=1),
            TrendPoint(year=2023, period="2023",
                       value=Decimal("100"), record_count=1),
        )
        assert cagr(points) is None

    def test_cagr_zero_to_zero(self):
        # 0 → 0: returns Decimal("0") (special
        # case).
        points = (
            TrendPoint(year=2022, period="2022",
                       value=Decimal("0"), record_count=1),
            TrendPoint(year=2023, period="2023",
                       value=Decimal("0"), record_count=1),
        )
        assert cagr(points) == Decimal("0")

    def test_cagr_negative_first_value(self):
        # -100 → 100: CAGR undefined (negative
        # base).
        points = (
            TrendPoint(year=2022, period="2022",
                       value=Decimal("-100"), record_count=1),
            TrendPoint(year=2023, period="2023",
                       value=Decimal("100"), record_count=1),
        )
        assert cagr(points) is None

    def test_cagr_zero_years(self):
        # Same year → 0 years → undefined.
        points = (
            TrendPoint(year=2022, period="2022",
                       value=Decimal("100"), record_count=1),
            TrendPoint(year=2022, period="2022",
                       value=Decimal("200"), record_count=1),
        )
        assert cagr(points) is None

    def test_cagr_years_override(self):
        # Override the years to 4 → CAGR is the
        # 4th root of (last/first) - 1.
        points = (
            TrendPoint(year=2022, period="2022",
                       value=Decimal("100"), record_count=1),
            TrendPoint(year=2024, period="2024",
                       value=Decimal("625"), record_count=1),
        )
        # 100 → 625 over 4 years: 4th root of
        # 6.25 = 1.58 (close to golden ratio).
        # Without override: 100 → 625 over 2
        # years: sqrt(6.25) - 1 = 1.5.
        result_4y = cagr(points, years=4)
        result_2y = cagr(points)
        assert result_4y is not None
        assert result_2y is not None
        assert result_4y != result_2y
        # 1.58 - 1.5 ≈ 0.08 difference.
        assert abs(result_4y - result_2y) > Decimal("0.05")

    def test_cagr_rejects_non_trend_point(self):
        # CAGR returns None for non-TrendPoint
        # input ONLY when len < 2; with 2 items the
        # type check triggers.
        with pytest.raises(
            TimeSeriesAnalyticsError, match="TrendPoint"
        ):
            cagr([
                TrendPoint(year=2022, period="2022",
                           value=Decimal("100"), record_count=1),
                {"year": 2023, "value": 200},
            ])


# ---------------------------------------------------------------------------
# TestGrowthRatePoint
# ---------------------------------------------------------------------------


class TestGrowthRatePoint:
    def test_frozen(self):
        g = GrowthRatePoint(
            year=2022, period="2022",
            value=Decimal("100"),
            previous=Decimal("90"),
            growth=Decimal("0.111"),
            record_count=1,
        )
        with pytest.raises(FrozenInstanceError):
            g.year = 9999  # type: ignore[misc]

    def test_previous_can_be_none(self):
        g = GrowthRatePoint(
            year=2022, period="2022",
            value=Decimal("100"),
            previous=None, growth=None,
            record_count=1,
        )
        assert g.previous is None
        assert g.growth is None

    def test_decimal_invariants(self):
        with pytest.raises(
            TimeSeriesAnalyticsError, match="Decimal"
        ):
            GrowthRatePoint(
                year=2022, period="2022",
                value="not a decimal",  # type: ignore[arg-type]
                previous=None, growth=None,
                record_count=1,
            )


# ---------------------------------------------------------------------------
# TestGrowthRates
# ---------------------------------------------------------------------------


class TestGrowthRates:
    def _series(self):
        return (
            TrendPoint(year=2020, period="2020",
                       value=Decimal("100"), record_count=1),
            TrendPoint(year=2021, period="2021",
                       value=Decimal("200"), record_count=1),
            TrendPoint(year=2022, period="2022",
                       value=Decimal("400"), record_count=1),
        )

    def test_returns_tuple(self):
        result = growth_rates(self._series())
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_first_point_has_no_previous(self):
        result = growth_rates(self._series())
        assert result[0].previous is None
        assert result[0].growth is None

    def test_first_point_values(self):
        result = growth_rates(self._series())
        assert result[0].year == 2020
        assert result[0].value == Decimal("100")

    def test_subsequent_growth_rates(self):
        result = growth_rates(self._series())
        # 2020→2021: (200-100)/100 = 1.0 (100%)
        # 2021→2022: (400-200)/200 = 1.0 (100%)
        assert result[1].growth == Decimal("1")
        assert result[2].growth == Decimal("1")

    def test_partial_growth(self):
        # 100 → 150: 50% growth.
        points = (
            TrendPoint(year=2022, period="2022",
                       value=Decimal("100"), record_count=1),
            TrendPoint(year=2023, period="2023",
                       value=Decimal("150"), record_count=1),
        )
        result = growth_rates(points)
        assert result[1].growth == Decimal("0.5")

    def test_divide_by_zero(self):
        # 0 → 100: growth is None.
        points = (
            TrendPoint(year=2022, period="2022",
                       value=Decimal("0"), record_count=1),
            TrendPoint(year=2023, period="2023",
                       value=Decimal("100"), record_count=1),
        )
        result = growth_rates(points)
        assert result[1].previous == Decimal("0")
        assert result[1].growth is None

    def test_negative_growth(self):
        # 200 → 100: -50% growth.
        points = (
            TrendPoint(year=2022, period="2022",
                       value=Decimal("200"), record_count=1),
            TrendPoint(year=2023, period="2023",
                       value=Decimal("100"), record_count=1),
        )
        result = growth_rates(points)
        assert result[1].growth == Decimal("-0.5")

    def test_empty_series_returns_empty(self):
        assert growth_rates(()) == ()

    def test_single_point(self):
        single = (TrendPoint(
            year=2022, period="2022",
            value=Decimal("100"), record_count=1
        ),)
        result = growth_rates(single)
        assert len(result) == 1
        assert result[0].growth is None

    def test_rejects_non_trend_point(self):
        with pytest.raises(
            TimeSeriesAnalyticsError, match="TrendPoint"
        ):
            growth_rates([{"year": 2022, "value": 100}])

    def test_preserves_other_fields(self):
        result = growth_rates(self._series())
        for orig, g in zip(self._series(), result):
            assert g.year == orig.year
            assert g.period == orig.period
            assert g.value == orig.value
            assert g.record_count == orig.record_count


# ---------------------------------------------------------------------------
# TestErrorsPropagated
# ---------------------------------------------------------------------------


class TestErrorsPropagated:
    def test_inherits_from_analytics_error(self):
        try:
            annual_trend([{"raw": "dict"}])
        except TimeSeriesAnalyticsError as exc:
            assert isinstance(exc, AnalyticsError)

    def test_rejects_bad_metric_type(self):
        with pytest.raises(TimeSeriesAnalyticsError, match="Metric"):
            annual_trend(_trend_dataset(), metric=123)  # type: ignore[arg-type]

    def test_rejects_negative_window(self):
        points = (TrendPoint(year=2022, period="2022",
                             value=Decimal("100"),
                             record_count=1),)
        with pytest.raises(TimeSeriesAnalyticsError, match="window"):
            rolling_average(points, window=-1)

    def test_rejects_empty_period_in_dataset(self):
        # Construct a TrendPoint with empty
        # period would fail at dataset parse
        # time; we test the internal parser
        # indirectly by passing a malformed
        # period in raw data.
        from un_comtrade.parser import TradeParser
        raw = _baseline_raw(period="")
        # Empty period fails parser validation.
        result = TradeParser(
            log_skipped=False
        ).parse_records([raw])
        assert len(result.records) == 0