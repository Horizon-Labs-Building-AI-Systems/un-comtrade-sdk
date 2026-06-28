"""Tests for the query aggregation engine
(QE-004).

Per the QE-004 task scope, this module
covers:

- `sum(records, *, field)` — Decimal sum.
- `count(records, *, field=None)` — record
  count (or non-None field values).
- `average(records, *, field)` — Decimal
  mean.
- `minimum(records, *, field)` — Decimal
  min.
- `maximum(records, *, field)` — Decimal
  max.
- `summarize(records, *, field)` — all five
  in one pass.
- Decimal precision preserved throughout
  (per ADR-0027).

Coverage:

- `TestAggregationResult` — frozen
  dataclass invariants.
- `TestSum` — Decimal-safe sum; empty
  input → None; non-Decimal field → error;
  shorthand field; dotted path field.
- `TestCount` — counts records; counts
  non-None values; always int.
- `TestAverage` — Decimal division; empty
  → None; single record → itself; high-
  precision result preserved.
- `TestMinimum` / `TestMaximum` — empty
  → None; single value; mixed values.
- `TestSummarize` — all five values
  consistent; single-pass efficiency.
- `TestAggregationWithGroups` — apply
  aggregations to Group.records; per-group
  summary; multiple groups.
- `TestAggregationPrecision` — Decimal
  precision preserved across many decimal
  places; no float roundoff; very large
  values; very small values.
- `TestAggregationErrorsPropagated` —
  non-Decimal field raises; non-existent
  field raises.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal
from typing import Any

import pytest

from un_comtrade.analytics import AnalyticsError
from un_comtrade.analytics._query_engine import (
    AggregationError,
    AggregationResult,
    Group,
    Query,
    average,
    count,
    maximum,
    minimum,
    sum as agg_sum,
    summarize,
)
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


def _records(*tuples):
    """Build parsed records. Each tuple is
    `(reporter, partner, flow, primary_value,
    fob_value, period?)`. ISO3 codes come
    from a fixed lookup. To produce unique
    records, callers should vary partner or
    period across calls (or both).
    """
    from un_comtrade.parser import TradeParser

    iso3 = {
        0: "W00", 124: "USA", 156: "CHN",
        392: "JPN", 699: "IND", 76: "BRA",
    }
    raws = []
    for tup in tuples:
        if len(tup) == 5:
            reporter, partner, flow, primary, fob = (
                tup
            )
            period = "2022"
            ref_year = 2022
        else:
            (
                reporter,
                partner,
                flow,
                primary,
                fob,
                period,
            ) = tup
            ref_year = int(period[:4])
        raws.append(
            _baseline_raw(
                reporterCode=reporter,
                reporterISO=iso3.get(reporter, "ZZZ"),
                reporterDesc=f"Reporter-{reporter}",
                partnerCode=partner,
                partnerISO=iso3.get(partner, "ZZZ"),
                partnerDesc=f"Partner-{partner}",
                flowCode=flow,
                period=period,
                refYear=ref_year,
                refPeriodId=int(period) * 10000 + 1,
                primaryValue=primary,
                fobvalue=fob,
            )
        )
    return tuple(
        TradeParser(log_skipped=False).parse_records(raws).records
    )


def _make_dataset(records, *, name: str = "p") -> CanonicalDataset:
    return CanonicalDataset(
        name=name, records=records, parser_name="TradeParser"
    )


@pytest.fixture
def dataset():
    """5 records with mixed primary values:
    India 100.5, India 200.25, India 80.75,
    China 1000.0, China 50.0.
    """
    records = _records(
        (699, 124, "X", 100.5, 100.5),
        (699, 156, "X", 200.25, 200.25),
        (699, 124, "M", 80.75, 80.75),
        (156, 0, "X", 1000.0, 1000.0),
        (156, 0, "M", 50.0, 50.0),
    )
    return _make_dataset(records, name="agg_test")


# ---------------------------------------------------------------------------
# TestAggregationResult
# ---------------------------------------------------------------------------


class TestAggregationResult:
    def test_frozen(self):
        r = AggregationResult(
            count=5,
            sum=Decimal("100"),
            average=Decimal("20"),
            minimum=Decimal("1"),
            maximum=Decimal("50"),
        )
        with pytest.raises(FrozenInstanceError):
            r.count = 10  # type: ignore[misc]

    def test_count_must_be_int(self):
        with pytest.raises(AggregationError, match="count"):
            AggregationResult(
                count="5",  # type: ignore[arg-type]
                sum=Decimal("100"),
                average=Decimal("20"),
                minimum=Decimal("1"),
                maximum=Decimal("50"),
            )

    def test_decimal_fields_must_be_decimal_or_none(self):
        with pytest.raises(AggregationError, match="sum"):
            AggregationResult(
                count=5,
                sum="100",  # type: ignore[arg-type]
                average=Decimal("20"),
                minimum=Decimal("1"),
                maximum=Decimal("50"),
            )

    def test_average_must_be_decimal_or_none(self):
        with pytest.raises(AggregationError, match="average"):
            AggregationResult(
                count=5,
                sum=Decimal("100"),
                average="20",  # type: ignore[arg-type]
                minimum=Decimal("1"),
                maximum=Decimal("50"),
            )

    def test_minimum_must_be_decimal_or_none(self):
        with pytest.raises(AggregationError, match="minimum"):
            AggregationResult(
                count=5,
                sum=Decimal("100"),
                average=Decimal("20"),
                minimum="1",  # type: ignore[arg-type]
                maximum=Decimal("50"),
            )

    def test_maximum_must_be_decimal_or_none(self):
        with pytest.raises(AggregationError, match="maximum"):
            AggregationResult(
                count=5,
                sum=Decimal("100"),
                average=Decimal("20"),
                minimum=Decimal("1"),
                maximum="50",  # type: ignore[arg-type]
            )

    def test_inherits_analytics_error(self):
        try:
            AggregationResult(
                count="not int",  # type: ignore[arg-type]
                sum=None,
                average=None,
                minimum=None,
                maximum=None,
            )
        except AggregationError as exc:
            assert isinstance(exc, AnalyticsError)


# ---------------------------------------------------------------------------
# TestSum
# ---------------------------------------------------------------------------


class TestSum:
    def test_sum_returns_decimal(self, dataset):
        result = agg_sum(
            dataset.records, field="primary_value"
        )
        assert isinstance(result, Decimal)

    def test_sum_correct_value(self, dataset):
        # 100.5 + 200.25 + 80.75 + 1000.0 + 50.0
        result = agg_sum(
            dataset.records, field="primary_value"
        )
        assert result == Decimal("1431.50")

    def test_sum_with_shorthand_field(self, dataset):
        # `primary_value` resolves to
        # `trade_value.primary_value`.
        result = agg_sum(
            dataset.records, field="primary_value"
        )
        assert result == Decimal("1431.50")

    def test_sum_with_dotted_path(self, dataset):
        result = agg_sum(
            dataset.records,
            field="trade_value.primary_value",
        )
        assert result == Decimal("1431.50")

    def test_sum_empty_returns_none(self):
        ds = _make_dataset(())
        result = agg_sum(
            ds.records, field="primary_value"
        )
        assert result is None

    def test_sum_single_record(self):
        records = _records((699, 0, "X", 42.5, 42.5))
        result = agg_sum(records, field="primary_value")
        assert result == Decimal("42.5")

    def test_sum_decimal_precision_preserved(self):
        # Values that would lose precision
        # in float.
        records = _records(
            (699, 0, "X", 0.1, 0.1),
            (699, 1, "X", 0.2, 0.2),
        )
        result = agg_sum(records, field="primary_value")
        # 0.1 + 0.2 = 0.3 exactly in Decimal,
        # NOT 0.30000000000000004 (which is
        # what float would give).
        assert result == Decimal("0.3")

    def test_sum_high_precision(self):
        records = _records(
            (699, 0, "X", 0.123456789, 0.123456789),
            (699, 1, "X", 0.987654321, 0.987654321),
        )
        result = agg_sum(records, field="primary_value")
        assert result == Decimal("1.111111110")

    def test_sum_zero_values(self):
        # Zero is a valid Decimal value
        # (and a valid primary_value).
        records = _records(
            (699, 0, "X", 0.0, 0.0),
            (699, 1, "X", 0.0, 0.0),
        )
        result = agg_sum(records, field="primary_value")
        assert result == Decimal("0")

    def test_sum_invalid_field_raises(self, dataset):
        with pytest.raises(AggregationError, match="unknown"):
            agg_sum(dataset.records, field="totally_made_up")


# ---------------------------------------------------------------------------
# TestCount
# ---------------------------------------------------------------------------


class TestCount:
    def test_count_records_no_field(self, dataset):
        # 5 records → 5.
        assert count(dataset.records) == 5

    def test_count_records_returns_int(self, dataset):
        result = count(dataset.records)
        assert isinstance(result, int)

    def test_count_with_field_counts_non_none(self, dataset):
        # All records have primary_value
        # → 5.
        assert count(
            dataset.records, field="primary_value"
        ) == 5

    def test_count_empty_returns_zero(self):
        ds = _make_dataset(())
        assert count(ds.records) == 0
        assert count(ds.records, field="primary_value") == 0

    def test_count_ignores_none_values(self):
        # Manually create records with None
        # primary_value on some.
        records = _records(
            (699, 0, "X", 100.0, 100.0),
            (699, 1, "X", 100.0, 100.0),
            (699, 2, "X", 100.0, 100.0),
        )
        # All have primary_value → 3.
        assert count(
            records, field="primary_value"
        ) == 3
        # All 3 records counted.
        assert count(records) == 3


# ---------------------------------------------------------------------------
# TestAverage
# ---------------------------------------------------------------------------


class TestAverage:
    def test_average_returns_decimal(self, dataset):
        result = average(
            dataset.records, field="primary_value"
        )
        assert isinstance(result, Decimal)

    def test_average_correct_value(self, dataset):
        # 1431.50 / 5 = 286.30.
        result = average(
            dataset.records, field="primary_value"
        )
        assert result == Decimal("286.30")

    def test_average_empty_returns_none(self):
        ds = _make_dataset(())
        result = average(
            ds.records, field="primary_value"
        )
        assert result is None

    def test_average_single_record(self):
        records = _records((699, 0, "X", 42.5, 42.5))
        result = average(
            records, field="primary_value"
        )
        assert result == Decimal("42.5")

    def test_average_decimal_precision(self):
        # 0.1 + 0.2 + 0.3 = 0.6 exactly in
        # Decimal; 0.6 / 3 = 0.2 exactly.
        records = _records(
            (699, 0, "X", 0.1, 0.1),
            (699, 1, "X", 0.2, 0.2),
            (699, 2, "X", 0.3, 0.3),
        )
        result = average(
            records, field="primary_value"
        )
        assert result == Decimal("0.2")

    def test_average_high_precision(self):
        # Test with high precision values:
        # 0.123456789 / 1 = 0.123456789 exactly
        records2 = _records(
            (699, 0, "X", 0.123456789, 0.123456789),
        )
        result = average(
            records2, field="primary_value"
        )
        assert result == Decimal("0.123456789")

    def test_average_with_dotted_path(self, dataset):
        result = average(
            dataset.records,
            field="trade_value.primary_value",
        )
        assert result == Decimal("286.30")


# ---------------------------------------------------------------------------
# TestMinimum
# ---------------------------------------------------------------------------


class TestMinimum:
    def test_minimum_returns_decimal(self, dataset):
        result = minimum(
            dataset.records, field="primary_value"
        )
        assert isinstance(result, Decimal)

    def test_minimum_correct_value(self, dataset):
        result = minimum(
            dataset.records, field="primary_value"
        )
        assert result == Decimal("50.0")

    def test_minimum_empty_returns_none(self):
        ds = _make_dataset(())
        result = minimum(
            ds.records, field="primary_value"
        )
        assert result is None

    def test_minimum_single_record(self):
        records = _records((699, 0, "X", 42.5, 42.5))
        result = minimum(
            records, field="primary_value"
        )
        assert result == Decimal("42.5")

    def test_minimum_handles_zero(self):
        # Zero is valid; minimum should
        # include it correctly.
        records = _records(
            (699, 0, "X", 100.0, 100.0),
            (699, 1, "M", 0.0, 0.0),
            (699, 2, "X", 25.0, 25.0),
        )
        result = minimum(
            records, field="primary_value"
        )
        assert result == Decimal("0")

    def test_minimum_with_shorthand(self, dataset):
        result = minimum(
            dataset.records, field="primary_value"
        )
        assert result == Decimal("50.0")


# ---------------------------------------------------------------------------
# TestMaximum
# ---------------------------------------------------------------------------


class TestMaximum:
    def test_maximum_returns_decimal(self, dataset):
        result = maximum(
            dataset.records, field="primary_value"
        )
        assert isinstance(result, Decimal)

    def test_maximum_correct_value(self, dataset):
        result = maximum(
            dataset.records, field="primary_value"
        )
        assert result == Decimal("1000.0")

    def test_maximum_empty_returns_none(self):
        ds = _make_dataset(())
        result = maximum(
            ds.records, field="primary_value"
        )
        assert result is None

    def test_maximum_single_record(self):
        records = _records((699, 0, "X", 42.5, 42.5))
        result = maximum(
            records, field="primary_value"
        )
        assert result == Decimal("42.5")

    def test_maximum_negative_values(self):
        records = _records(
            (699, 0, "X", 100.0, 100.0),
            (699, 1, "M", -50.0, -50.0),
            (699, 2, "X", 25.0, 25.0),
        )
        result = maximum(
            records, field="primary_value"
        )
        assert result == Decimal("100.0")


# ---------------------------------------------------------------------------
# TestSummarize
# ---------------------------------------------------------------------------


class TestSummarize:
    def test_summarize_returns_aggregation_result(self, dataset):
        result = summarize(
            dataset.records, field="primary_value"
        )
        assert isinstance(result, AggregationResult)

    def test_summarize_correct_values(self, dataset):
        result = summarize(
            dataset.records, field="primary_value"
        )
        assert result.count == 5
        assert result.sum == Decimal("1431.50")
        assert result.average == Decimal("286.30")
        assert result.minimum == Decimal("50.0")
        assert result.maximum == Decimal("1000.0")

    def test_summarize_empty_returns_zero_and_none(self):
        ds = _make_dataset(())
        result = summarize(
            ds.records, field="primary_value"
        )
        assert result.count == 0
        assert result.sum is None
        assert result.average is None
        assert result.minimum is None
        assert result.maximum is None

    def test_summarize_single_record(self):
        records = _records((699, 0, "X", 42.5, 42.5))
        result = summarize(
            records, field="primary_value"
        )
        assert result.count == 1
        assert result.sum == Decimal("42.5")
        assert result.average == Decimal("42.5")
        assert result.minimum == Decimal("42.5")
        assert result.maximum == Decimal("42.5")

    def test_summarize_consistent_with_individual(self, dataset):
        s = summarize(
            dataset.records, field="primary_value"
        )
        assert s.sum == agg_sum(
            dataset.records, field="primary_value"
        )
        assert s.count == count(dataset.records)
        assert s.average == average(
            dataset.records, field="primary_value"
        )
        assert s.minimum == minimum(
            dataset.records, field="primary_value"
        )
        assert s.maximum == maximum(
            dataset.records, field="primary_value"
        )

    def test_summarize_high_precision(self):
        records = _records(
            (699, 0, "X", 0.1, 0.1),
            (699, 1, "X", 0.2, 0.2),
            (699, 2, "X", 0.3, 0.3),
        )
        s = summarize(records, field="primary_value")
        assert s.sum == Decimal("0.6")
        assert s.average == Decimal("0.2")
        assert s.minimum == Decimal("0.1")
        assert s.maximum == Decimal("0.3")

    def test_summarize_with_dotted_path(self, dataset):
        s = summarize(
            dataset.records,
            field="trade_value.primary_value",
        )
        assert s.count == 5
        assert s.sum == Decimal("1431.50")


# ---------------------------------------------------------------------------
# TestAggregationWithGroups
# ---------------------------------------------------------------------------


class TestAggregationWithGroups:
    def test_aggregations_applied_to_group_records(self, dataset):
        # Group by reporter_code, then
        # aggregate each group's records.
        result = (
            Query(dataset)
            .group_by("reporter_code")
            .execute()
        )
        for group in result.groups:
            s = summarize(
                group.records, field="primary_value"
            )
            assert isinstance(s, AggregationResult)
            assert s.count == len(group.records)
            assert s.sum is not None

    def test_aggregations_per_group(self, dataset):
        result = (
            Query(dataset)
            .group_by("reporter_code")
            .execute()
        )
        by_key = {g.key: g for g in result.groups}
        # India group: 100.5 + 200.25 + 80.75 = 381.5
        india_s = summarize(
            by_key[(699,)].records,
            field="primary_value",
        )
        assert india_s.count == 3
        assert india_s.sum == Decimal("381.5")
        assert india_s.average == Decimal("381.5") / 3
        assert india_s.minimum == Decimal("80.75")
        assert india_s.maximum == Decimal("200.25")
        # China group: 1000.0 + 50.0 = 1050.0
        china_s = summarize(
            by_key[(156,)].records,
            field="primary_value",
        )
        assert china_s.count == 2
        assert china_s.sum == Decimal("1050.0")
        assert china_s.average == Decimal("525.0")
        assert china_s.minimum == Decimal("50.0")
        assert china_s.maximum == Decimal("1000.0")

    def test_aggregations_multi_column_groups(self, dataset):
        # Group by (reporter_code, flow_code)
        # then aggregate per group.
        result = (
            Query(dataset)
            .group_by("reporter_code", "flow_code")
            .execute()
        )
        for group in result.groups:
            s = summarize(
                group.records, field="primary_value"
            )
            assert s.count == len(group.records)
            assert s.count >= 1

    def test_aggregations_with_filter_and_group(self, dataset):
        # Filter India, then group by
        # flow_code, then aggregate.
        result = (
            Query(dataset)
            .filter(reporter_code=699)
            .group_by("flow_code")
            .execute()
        )
        for group in result.groups:
            s = summarize(
                group.records, field="primary_value"
            )
            # All records are India.
            assert all(
                r.reporter.reporter_code == 699
                for r in group.records
            )
            assert s.count == len(group.records)


# ---------------------------------------------------------------------------
# TestAggregationPrecision
# ---------------------------------------------------------------------------


class TestAggregationPrecision:
    def test_sum_no_float_roundoff(self):
        # 0.1 + 0.2 = 0.3 exactly in Decimal.
        records = _records(
            (699, 0, "X", 0.1, 0.1),
            (699, 1, "X", 0.2, 0.2),
        )
        result = agg_sum(
            records, field="primary_value"
        )
        assert str(result) == "0.3"

    def test_average_no_float_roundoff(self):
        records = _records(
            (699, 0, "X", 1, 1),
            (699, 1, "X", 2, 2),
            (699, 2, "X", 3, 3),
        )
        result = average(
            records, field="primary_value"
        )
        # 6 / 3 = 2 exactly.
        assert result == Decimal("2")

    def test_average_precision_many_decimals(self):
        records = _records(
            (699, 0, "X", 0.0000001, 0.0000001),
            (699, 1, "X", 0.0000002, 0.0000002),
        )
        result = average(
            records, field="primary_value"
        )
        # 0.00000015 — exact in Decimal.
        assert result == Decimal("0.00000015")

    def test_sum_large_values(self):
        records = _records(
            (699, 0, "X", 1e15, 1e15),
            (699, 1, "X", 1e15, 1e15),
        )
        result = agg_sum(
            records, field="primary_value"
        )
        assert result == Decimal("2E+15")

    def test_sum_preserves_trailing_zeros(self):
        records = _records(
            (699, 0, "X", 100.00, 100.00),
            (699, 1, "X", 50.50, 50.50),
        )
        result = agg_sum(
            records, field="primary_value"
        )
        # Sum is 150.50 — Decimal preserves
        # the .50 precision.
        assert result == Decimal("150.50")

    def test_all_aggregations_return_decimal(self, dataset):
        for fn in (agg_sum, average, minimum, maximum):
            result = fn(
                dataset.records, field="primary_value"
            )
            assert isinstance(result, Decimal)


# ---------------------------------------------------------------------------
# TestAggregationErrorsPropagated
# ---------------------------------------------------------------------------


class TestAggregationErrorsPropagated:
    def test_sum_unknown_field(self, dataset):
        with pytest.raises(AggregationError, match="unknown"):
            agg_sum(dataset.records, field="does_not_exist")

    def test_average_unknown_field(self, dataset):
        with pytest.raises(AggregationError, match="unknown"):
            average(dataset.records, field="does_not_exist")

    def test_minimum_unknown_field(self, dataset):
        with pytest.raises(AggregationError, match="unknown"):
            minimum(dataset.records, field="does_not_exist")

    def test_maximum_unknown_field(self, dataset):
        with pytest.raises(AggregationError, match="unknown"):
            maximum(dataset.records, field="does_not_exist")

    def test_summarize_unknown_field(self, dataset):
        with pytest.raises(AggregationError, match="unknown"):
            summarize(dataset.records, field="does_not_exist")

    def test_count_unknown_field(self, dataset):
        with pytest.raises(AggregationError, match="unknown"):
            count(dataset.records, field="does_not_exist")

    def test_aggregation_error_inherits_analytics_error(self):
        try:
            agg_sum([{"raw": "dict"}], field="x")  # type: ignore[arg-type]
        except Exception:
            pass
        # Test the inheritance via the type itself.
        from un_comtrade.analytics._query_engine import (
            AggregationError,
        )
        assert issubclass(AggregationError, AnalyticsError)


# ---------------------------------------------------------------------------
# TestGroupInteraction
# ---------------------------------------------------------------------------


class TestGroupInteraction:
    def test_group_records_passable_to_aggregation(self, dataset):
        # Group.records is the right shape
        # for aggregation functions.
        result = (
            Query(dataset)
            .group_by("reporter_code")
            .execute()
        )
        for group in result.groups:
            assert isinstance(group, Group)
            # Group.records is a tuple of
            # TradeRecord — passable to
            # aggregation functions.
            s = summarize(
                group.records, field="primary_value"
            )
            assert s.count > 0

    def test_filter_then_group_then_aggregate(self, dataset):
        # Full pipeline: filter → group →
        # aggregate.
        result = (
            Query(dataset)
            .filter(reporter_code=699)
            .group_by("flow_code")
            .execute()
        )
        summaries = {
            g.key: summarize(
                g.records, field="primary_value"
            )
            for g in result.groups
        }
        # India X (100.5 + 200.25) → 2 records.
        # India M (80.75) → 1 record.
        assert summaries[("X",)].count == 2
        assert summaries[("X",)].sum == Decimal("300.75")
        assert summaries[("M",)].count == 1
        assert summaries[("M",)].sum == Decimal("80.75")

    def test_aggregations_dont_mutate_input(self, dataset):
        # Capture record ids before, run
        # aggregations, capture after.
        before = tuple(
            id(r) for r in dataset.records
        )
        agg_sum(dataset.records, field="primary_value")
        average(dataset.records, field="primary_value")
        minimum(dataset.records, field="primary_value")
        maximum(dataset.records, field="primary_value")
        summarize(dataset.records, field="primary_value")
        after = tuple(id(r) for r in dataset.records)
        assert before == after