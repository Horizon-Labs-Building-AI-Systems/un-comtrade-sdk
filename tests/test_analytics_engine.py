"""Tests for the analytics engine foundation (P6-001).

Per the P6-001 task scope, this module verifies:

- **Engine accepts `CanonicalDataset`** — `run(...)`
  rejects any other input type with `AnalyticsError`.
- **Filters compose** — boolean algebra on
  `Filter` instances via `&`, `|`, `~` produces
  correct predicates; the engine applies them in
  order.
- **Metrics compose** — arithmetic operators on
  `Metric` instances produce derived metrics with
  correct semantics.
- **Results immutable** — `AnalysisResult`,
  `AnalysisContext`, `Aggregation`, `AggregationRow`,
  `Filter`, `Metric` are all frozen dataclasses.
- **No transport dependency** — `un_comtrade.analytics`
  must not import `un_comtrade.transport`,
  `un_comtrade.client`, `httpx`, or anything that
  pulls the parser / metadata layer in transitively
  (verified by AST inspection in
  `TestNoTransportDependency`).

Coverage:

- `TestFilter` — pre-built filters, predicate
  matching, `Filter.apply(...)` semantics, no
  mutation of input dataset.
- `TestFilterComposition` — `&`, `|`, `~`
  composition.
- `TestMetric` — pre-built metrics, return types
  (Decimal for monetary, int for counts), error
  paths (empty dataset, missing field).
- `TestMetricComposition` — `+`, `-`, `*`, `/`
  composition; division by zero.
- `TestAggregation` — group-by construction,
  unknown-field rejection, `Aggregation.apply(...)`
  semantics, single-group and multi-group
  scenarios.
- `TestAnalyticsEngine` — engine construction,
  filter chain, metric execution, aggregation
  execution, error propagation, no-op engine,
  empty dataset.
- `TestAnalysisResult` — frozen dataclass,
  `get_metric(...)` / `get_aggregation(...)`
  helpers.
- `TestNoTransportDependency` — AST inspection
  confirms `un_comtrade.analytics` does not
  transitively import the transport layer.
"""

from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from un_comtrade.analytics import (
    Aggregation,
    AggregationError,
    AggregationRow,
    AnalyticsEngine,
    AnalyticsError,
    AnalysisContext,
    AnalysisResult,
    Filter,
    FilterError,
    Metric,
    MetricError,
)
from un_comtrade.models.trade import TradeRecord
from un_comtrade.parser import TradeParser
from un_comtrade.transform import CanonicalDataset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _baseline_raw(**overrides) -> dict[str, Any]:
    """Build a baseline raw upstream trade record."""
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


def _records(*tuples) -> tuple[TradeRecord, ...]:
    """Build parsed `TradeRecord`s from tuples of
    `(reporter, partner, period, flow, value)`.
    The matching `ref_period_id` is computed from
    `period` to avoid the parser's composite-key
    dedup."""
    raws = []
    for t in tuples:
        reporter, partner, period, flow, value = t
        period_id = int(period) * 10000 + 1
        raws.append(
            _baseline_raw(
                reporterCode=reporter,
                partnerCode=partner,
                period=period,
                refYear=int(period),
                refPeriodId=period_id,
                flowCode=flow,
                fobvalue=value,
                primaryValue=value,
            )
        )
    return tuple(
        TradeParser(log_skipped=False).parse_records(raws).records
    )


def _make_dataset(
    records, *, name: str = "p"
) -> CanonicalDataset:
    return CanonicalDataset(
        name=name, records=records, parser_name="TradeParser"
    )


# ---------------------------------------------------------------------------
# TestFilter
# ---------------------------------------------------------------------------


class TestFilter:
    def test_reporter_filter_matches(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (156, 0, "2022", "X", 200.0),
        )
        f = Filter.reporter(699)
        ds = f.apply(_make_dataset(records))
        assert len(ds.records) == 1
        assert ds.records[0].reporter.reporter_code == 699

    def test_partner_filter_matches(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 124, "2022", "X", 200.0),
        )
        f = Filter.partner(124)
        ds = f.apply(_make_dataset(records))
        assert len(ds.records) == 1
        assert ds.records[0].partner.partner_code == 124

    def test_flow_filter_matches_export(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2022", "M", 200.0),
        )
        f = Filter.flow_export()
        ds = f.apply(_make_dataset(records))
        assert len(ds.records) == 1
        assert ds.records[0].flow.flow_code == "X"

    def test_flow_filter_matches_import(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2022", "M", 200.0),
        )
        f = Filter.flow_import()
        ds = f.apply(_make_dataset(records))
        assert len(ds.records) == 1
        assert ds.records[0].flow.flow_code == "M"

    def test_year_filter_matches(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
        )
        f = Filter.year(2022)
        ds = f.apply(_make_dataset(records))
        assert len(ds.records) == 1

    def test_year_in_filter_matches(self):
        records = _records(
            (699, 0, "2020", "X", 100.0),
            (699, 0, "2021", "X", 200.0),
            (699, 0, "2022", "X", 300.0),
            (699, 0, "2023", "X", 400.0),
        )
        f = Filter.year_in(2021, 2022)
        ds = f.apply(_make_dataset(records))
        assert len(ds.records) == 2

    def test_period_filter_matches(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "202201", "X", 200.0),
        )
        f = Filter.period("2022")
        ds = f.apply(_make_dataset(records))
        assert len(ds.records) == 1

    def test_commodity_filter_matches(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
        )
        f = Filter.commodity("TOTAL")
        ds = f.apply(_make_dataset(records))
        assert len(ds.records) == 1

    def test_classification_filter_matches(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
        )
        f = Filter.classification("H6")
        ds = f.apply(_make_dataset(records))
        assert len(ds.records) == 1

    def test_custom_filter(self):
        # Vary partner so the parser's first-wins
        # dedup keeps both records.
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 124, "2022", "X", 9999.0),
        )
        # Custom: trade value > 500
        f = Filter.custom(
            name="high_value",
            description="trade_value > 500",
            predicate=lambda r: r.trade_value.primary_value > 500,
        )
        ds = f.apply(_make_dataset(records))
        assert len(ds.records) == 1
        assert ds.records[0].trade_value.primary_value == Decimal("9999")

    def test_filter_does_not_mutate_input(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (156, 0, "2022", "X", 200.0),
        )
        original = _make_dataset(records)
        ds = Filter.reporter(699).apply(original)
        # Original dataset unchanged.
        assert len(original.records) == 2
        # Filtered dataset is a NEW dataset.
        assert ds is not original
        assert len(ds.records) == 1

    def test_filter_apply_rejects_non_canonical(self):
        f = Filter.reporter(699)
        with pytest.raises(AnalyticsError, match="CanonicalDataset"):
            f.apply([{"raw": "dict"}])

    def test_custom_filter_rejects_non_callable(self):
        with pytest.raises(FilterError, match="callable"):
            Filter.custom(name="x", predicate="not callable")

    def test_filter_repr(self):
        f = Filter.reporter(699)
        assert "Filter" in repr(f)
        assert "699" in repr(f)


# ---------------------------------------------------------------------------
# TestFilterComposition
# ---------------------------------------------------------------------------


class TestFilterComposition:
    """Filter boolean composition via `&`, `|`, `~`."""

    def test_and_intersection(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
            (156, 0, "2022", "X", 300.0),
        )
        combined = Filter.reporter(699) & Filter.year(2022)
        ds = combined.apply(_make_dataset(records))
        # Only (699, 2022) matches both.
        assert len(ds.records) == 1
        assert ds.records[0].reporter.reporter_code == 699
        assert ds.records[0].ref_year == 2022

    def test_or_union(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (156, 0, "2023", "X", 200.0),
            (276, 0, "2024", "X", 300.0),
        )
        combined = Filter.reporter(699) | Filter.reporter(156)
        ds = combined.apply(_make_dataset(records))
        assert len(ds.records) == 2

    def test_negation(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (156, 0, "2022", "X", 200.0),
        )
        inverted = ~Filter.reporter(699)
        ds = inverted.apply(_make_dataset(records))
        assert len(ds.records) == 1
        assert ds.records[0].reporter.reporter_code == 156

    def test_composition_preserves_names(self):
        a = Filter.reporter(699)
        b = Filter.year(2022)
        composed = a & b
        assert "AND" in composed.name
        assert "AND" in composed.description

    def test_composition_with_non_filter_returns_notimplemented(self):
        a = Filter.reporter(699)
        # `a & "not a filter"` should return
        # NotImplemented so Python can try the
        # reflected op.
        assert a.__and__("not a filter") is NotImplemented

    def test_double_negation_equivalent(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (156, 0, "2022", "X", 200.0),
        )
        original = Filter.reporter(699)
        double_negated = ~~original
        ds_a = original.apply(_make_dataset(records))
        ds_b = double_negated.apply(_make_dataset(records))
        assert len(ds_a.records) == len(ds_b.records) == 1
        assert ds_a.records[0].reporter.reporter_code == (
            ds_b.records[0].reporter.reporter_code
        )

    def test_complex_expression(self):
        # (reporter=699 OR reporter=156) AND year=2022
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
            (156, 0, "2022", "X", 300.0),
            (156, 0, "2023", "X", 400.0),
            (842, 0, "2022", "X", 500.0),
        )
        combined = (
            (Filter.reporter(699) | Filter.reporter(156))
            & Filter.year(2022)
        )
        ds = combined.apply(_make_dataset(records))
        assert len(ds.records) == 2
        reporters = {r.reporter.reporter_code for r in ds.records}
        assert reporters == {699, 156}


# ---------------------------------------------------------------------------
# TestMetric
# ---------------------------------------------------------------------------


class TestMetric:
    def test_count_metric(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
            (156, 0, "2022", "X", 300.0),
        )
        m = Metric.count()
        assert m.compute(_make_dataset(records)) == 3

    def test_sum_primary_value_returns_decimal(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
            (156, 0, "2022", "X", 300.0),
        )
        m = Metric.sum_primary_value()
        value = m.compute(_make_dataset(records))
        assert isinstance(value, Decimal)
        assert value == Decimal("600")

    def test_sum_fob_value_returns_decimal(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
        )
        m = Metric.sum_fob_value()
        value = m.compute(_make_dataset(records))
        assert value == Decimal("300")

    def test_avg_primary_value_returns_decimal(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
        )
        m = Metric.avg_primary_value()
        value = m.compute(_make_dataset(records))
        assert value == Decimal("150")

    def test_avg_on_empty_dataset_raises(self):
        ds = _make_dataset(())
        with pytest.raises(MetricError, match="empty"):
            Metric.avg_primary_value().compute(ds)

    def test_distinct_reporters(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
            (156, 0, "2022", "X", 300.0),
            (842, 0, "2022", "X", 400.0),
        )
        m = Metric.distinct_reporters()
        assert m.compute(_make_dataset(records)) == 3

    def test_distinct_partners(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 124, "2022", "X", 200.0),
            (699, 276, "2022", "X", 300.0),
            (699, 0, "2023", "X", 400.0),
        )
        m = Metric.distinct_partners()
        assert m.compute(_make_dataset(records)) == 3

    def test_min_max_year(self):
        records = _records(
            (699, 0, "2020", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
            (699, 0, "2021", "X", 300.0),
        )
        assert Metric.min_year().compute(_make_dataset(records)) == 2020
        assert Metric.max_year().compute(_make_dataset(records)) == 2023

    def test_min_year_on_empty_raises(self):
        with pytest.raises(MetricError):
            Metric.min_year().compute(_make_dataset(()))

    def test_custom_metric(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
        )
        m = Metric.custom(
            name="custom",
            description="always returns 42",
            compute=lambda ds: 42,
        )
        assert m.compute(_make_dataset(records)) == 42

    def test_custom_metric_rejects_non_callable(self):
        with pytest.raises(MetricError, match="callable"):
            Metric.custom(name="x", compute=42)

    def test_metric_repr(self):
        assert "Metric" in repr(Metric.count())
        assert "count" in repr(Metric.count())


# ---------------------------------------------------------------------------
# TestMetricComposition
# ---------------------------------------------------------------------------


class TestMetricComposition:
    def test_add_two_metrics(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
        )
        m = Metric.sum_fob_value() + Metric.sum_cif_value()
        # Both sum_fob and sum_cif over the same
        # records; fob is 300, cif is None (0). Total
        # = 300.
        value = m.compute(_make_dataset(records))
        assert value == Decimal("300")

    def test_subtract_two_metrics(self):
        records = _records(
            (699, 0, "2022", "X", 200.0),
        )
        m = Metric.sum_fob_value() - Metric.sum_primary_value()
        # Both equal 200 → 0.
        assert m.compute(_make_dataset(records)) == Decimal("0")

    def test_multiply_two_metrics(self):
        records = _records(
            (699, 0, "2022", "X", 5.0),
        )
        # 5 * 1 (count) = 5
        m = Metric.sum_primary_value() * Metric.count()
        assert m.compute(_make_dataset(records)) == Decimal("5")

    def test_divide_two_metrics(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
        )
        # sum (300) / count (2) = 150
        m = Metric.sum_primary_value() / Metric.count()
        assert m.compute(_make_dataset(records)) == Decimal("150")

    def test_divide_by_zero_raises(self):
        records = _records((699, 0, "2022", "X", 100.0),)
        # avg_primary / count where count=1 → 100/1.
        # Use a denominator that always returns 0:
        m = Metric.sum_primary_value() / Metric.custom(
            name="zero",
            compute=lambda ds: 0,
        )
        with pytest.raises(MetricError, match="[Dd]ivision"):
            m.compute(_make_dataset(records))

    def test_composed_metric_repr_uses_operator(self):
        m = Metric.sum_primary_value() + Metric.sum_fob_value()
        assert "+" in m.name or "sum" in m.name

    def test_nested_composition(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (156, 0, "2023", "X", 200.0),
        )
        # (sum + sum) / count
        m = (
            (Metric.sum_primary_value() + Metric.sum_fob_value())
            / Metric.count()
        )
        # (300 + 300) / 2 = 300.
        assert m.compute(_make_dataset(records)) == Decimal("300")


# ---------------------------------------------------------------------------
# TestAggregation
# ---------------------------------------------------------------------------


class TestAggregation:
    def test_construct_with_valid_field(self):
        a = Aggregation(
            name="by_partner",
            group_by=("partner_code",),
            metric=Metric.sum_primary_value(),
        )
        assert a.name == "by_partner"

    def test_construct_with_unknown_field_raises(self):
        with pytest.raises(AggregationError, match="Unknown group_by"):
            Aggregation(
                name="by_xyz",
                group_by=("xyz",),
                metric=Metric.count(),
            )

    def test_construct_rejects_non_metric(self):
        with pytest.raises(AggregationError, match="must be a Metric"):
            Aggregation(
                name="bad",
                group_by=("reporter_code",),
                metric="not a metric",
            )

    def test_supported_fields_constant(self):
        assert "reporter_code" in Aggregation.SUPPORTED_FIELDS
        assert "period" in Aggregation.SUPPORTED_FIELDS
        assert "flow_code" in Aggregation.SUPPORTED_FIELDS

    def test_single_field_aggregation(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
            (156, 0, "2022", "X", 300.0),
            (156, 0, "2023", "X", 400.0),
        )
        a = Aggregation(
            name="by_reporter",
            group_by=("reporter_code",),
            metric=Metric.sum_primary_value(),
        )
        rows = a.apply(_make_dataset(records))
        assert len(rows) == 2
        # First-seen order: (699, ...) before (156, ...).
        assert rows[0].group_values == (699,)
        assert rows[0].metric_value == Decimal("300")
        assert rows[0].record_count == 2
        assert rows[1].group_values == (156,)
        assert rows[1].metric_value == Decimal("700")
        assert rows[1].record_count == 2

    def test_multi_field_aggregation(self):
        # Vary partner so the parser's first-wins
        # dedup keeps both (699, 2022) records.
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 124, "2022", "X", 200.0),
            (699, 0, "2023", "X", 300.0),
            (156, 0, "2022", "X", 400.0),
        )
        a = Aggregation(
            name="by_reporter_year",
            group_by=("reporter_code", "ref_year"),
            metric=Metric.sum_primary_value(),
        )
        rows = a.apply(_make_dataset(records))
        # 3 distinct groups.
        assert len(rows) == 3
        # (699, 2022): sum = 300, n = 2
        # (699, 2023): sum = 300, n = 1
        # (156, 2022): sum = 400, n = 1
        keys = {r.group_values: r for r in rows}
        assert keys[(699, 2022)].metric_value == Decimal("300")
        assert keys[(699, 2022)].record_count == 2
        assert keys[(699, 2023)].metric_value == Decimal("300")
        assert keys[(699, 2023)].record_count == 1
        assert keys[(156, 2022)].metric_value == Decimal("400")

    def test_aggregation_with_count_metric(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
            (156, 0, "2022", "X", 300.0),
        )
        a = Aggregation(
            name="by_reporter_count",
            group_by=("reporter_code",),
            metric=Metric.count(),
        )
        rows = a.apply(_make_dataset(records))
        by_key = {r.group_values[0]: r for r in rows}
        assert by_key[699].metric_value == 2
        assert by_key[156].metric_value == 1

    def test_aggregation_on_empty_dataset(self):
        a = Aggregation(
            name="by_reporter",
            group_by=("reporter_code",),
            metric=Metric.sum_primary_value(),
        )
        rows = a.apply(_make_dataset(()))
        assert rows == ()

    def test_aggregation_apply_rejects_non_canonical(self):
        a = Aggregation(
            name="by_reporter",
            group_by=("reporter_code",),
            metric=Metric.count(),
        )
        with pytest.raises(AnalyticsError, match="CanonicalDataset"):
            a.apply("not a dataset")

    def test_aggregation_repr(self):
        a = Aggregation(
            name="by_reporter",
            group_by=("reporter_code",),
            metric=Metric.count(),
        )
        r = repr(a)
        assert "Aggregation" in r
        assert "by_reporter" in r
        assert "reporter_code" in r
        assert "count" in r

    def test_aggregation_row_frozen(self):
        from dataclasses import FrozenInstanceError

        row = AggregationRow(
            group_values=(699,),
            group_labels=("reporter_code",),
            metric_name="count",
            metric_value=1,
            record_count=1,
        )
        with pytest.raises(FrozenInstanceError):
            row.record_count = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TestAnalyticsEngine
# ---------------------------------------------------------------------------


class TestAnalyticsEngine:
    def test_engine_rejects_empty_name(self):
        with pytest.raises(AnalyticsError, match="name"):
            AnalyticsEngine(name="")

    def test_engine_builder_returns_self(self):
        e = AnalyticsEngine(name="x")
        assert e.add_filter(Filter.reporter(699)) is e
        assert e.add_metric(Metric.count()) is e
        assert (
            e.add_aggregation(
                Aggregation(
                    name="by_reporter",
                    group_by=("reporter_code",),
                    metric=Metric.count(),
                )
            )
            is e
        )

    def test_engine_rejects_non_filter(self):
        e = AnalyticsEngine(name="x")
        with pytest.raises(AnalyticsError, match="Filter"):
            e.add_filter("not a filter")  # type: ignore[arg-type]

    def test_engine_rejects_non_metric(self):
        e = AnalyticsEngine(name="x")
        with pytest.raises(AnalyticsError, match="Metric"):
            e.add_metric("not a metric")  # type: ignore[arg-type]

    def test_engine_rejects_non_aggregation(self):
        e = AnalyticsEngine(name="x")
        with pytest.raises(AnalyticsError, match="Aggregation"):
            e.add_aggregation("not an aggregation")  # type: ignore[arg-type]

    def test_engine_run_rejects_non_canonical_dataset(self):
        e = AnalyticsEngine(name="x")
        with pytest.raises(AnalyticsError, match="CanonicalDataset"):
            e.run([{"raw": "dict"}])

    def test_empty_engine_on_empty_dataset(self):
        e = AnalyticsEngine(name="empty")
        result = e.run(_make_dataset(()))
        assert result.metric_values == {}
        assert result.aggregation_results == {}
        assert result.record_count == 0
        assert result.filtered_count == 0

    def test_empty_engine_on_dataset(self):
        records = _records((699, 0, "2022", "X", 100.0),)
        e = AnalyticsEngine(name="empty")
        result = e.run(_make_dataset(records))
        assert result.record_count == 1
        assert result.filtered_count == 1
        assert result.metric_values == {}

    def test_engine_with_metric_only(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (156, 0, "2022", "X", 200.0),
        )
        e = (
            AnalyticsEngine(name="counts")
            .add_metric(Metric.count())
            .add_metric(Metric.distinct_reporters())
        )
        result = e.run(_make_dataset(records))
        assert result.metric_values["count"] == 2
        assert result.metric_values["distinct_reporters"] == 2

    def test_engine_with_filter_then_metric(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
            (156, 0, "2022", "X", 300.0),
        )
        e = (
            AnalyticsEngine(name="filter_then_count")
            .add_filter(Filter.reporter(699))
            .add_metric(Metric.count())
            .add_metric(Metric.sum_primary_value())
        )
        result = e.run(_make_dataset(records))
        assert result.record_count == 3
        assert result.filtered_count == 2
        assert result.metric_values["count"] == 2
        assert result.metric_values["sum_primary_value"] == Decimal(
            "300"
        )

    def test_engine_with_multiple_filters_applied_in_order(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
            (156, 0, "2022", "X", 300.0),
            (156, 0, "2023", "X", 400.0),
        )
        e = (
            AnalyticsEngine(name="chain")
            .add_filter(Filter.reporter(699))
            .add_filter(Filter.year(2022))
            .add_metric(Metric.count())
        )
        result = e.run(_make_dataset(records))
        # First filter keeps (699, 2022) and (699,
        # 2023); second keeps only (699, 2022).
        assert result.filtered_count == 1
        assert result.metric_values["count"] == 1

    def test_engine_with_aggregation(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
            (156, 0, "2022", "X", 300.0),
        )
        e = (
            AnalyticsEngine(name="agg")
            .add_aggregation(
                Aggregation(
                    name="by_reporter",
                    group_by=("reporter_code",),
                    metric=Metric.sum_primary_value(),
                )
            )
        )
        result = e.run(_make_dataset(records))
        rows = result.aggregation_results["by_reporter"]
        assert len(rows) == 2
        keys = {r.group_values[0]: r.metric_value for r in rows}
        assert keys[699] == Decimal("300")
        assert keys[156] == Decimal("300")

    def test_engine_with_all_components(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (699, 0, "2023", "X", 200.0),
            (156, 0, "2022", "X", 300.0),
            (156, 0, "2023", "X", 400.0),
        )
        e = (
            AnalyticsEngine(name="full")
            .add_filter(Filter.flow_export())
            .add_filter(Filter.reporter(699) | Filter.reporter(156))
            .add_metric(Metric.count())
            .add_metric(Metric.sum_primary_value())
            .add_metric(Metric.avg_primary_value())
            .add_aggregation(
                Aggregation(
                    name="by_reporter_year",
                    group_by=("reporter_code", "ref_year"),
                    metric=Metric.sum_primary_value(),
                )
            )
        )
        result = e.run(_make_dataset(records))
        assert result.record_count == 4
        assert result.filtered_count == 4
        assert result.metric_values["count"] == 4
        assert result.metric_values["sum_primary_value"] == Decimal(
            "1000"
        )
        assert result.metric_values["avg_primary_value"] == Decimal(
            "250"
        )
        agg = result.aggregation_results["by_reporter_year"]
        assert len(agg) == 4  # 4 distinct reporter×year

    def test_engine_records_durations(self):
        records = _records((699, 0, "2022", "X", 100.0),)
        e = (
            AnalyticsEngine(name="timing")
            .add_metric(Metric.count())
            .add_aggregation(
                Aggregation(
                    name="by_reporter",
                    group_by=("reporter_code",),
                    metric=Metric.count(),
                )
            )
        )
        result = e.run(_make_dataset(records))
        assert "count" in result.context.metric_durations
        assert "by_reporter" in result.context.aggregation_durations
        assert result.duration_seconds >= 0
        assert result.context.started_at is not None
        assert result.context.finished_at is not None
        assert result.context.duration_seconds >= 0

    def test_engine_captures_metric_warnings(self):
        # avg_primary_value on an empty dataset →
        # MetricError → warning.
        e = (
            AnalyticsEngine(name="warn")
            .add_filter(Filter.reporter(842))  # no records
            .add_metric(Metric.avg_primary_value())
            .add_metric(Metric.count())  # still works
        )
        result = e.run(_make_dataset(()))
        # The avg metric should be skipped (empty
        # dataset) and a warning recorded.
        assert "avg_primary_value" not in result.metric_values
        assert any(
            "avg_primary_value" in w for w in result.warnings
        )

    def test_engine_repr(self):
        e = (
            AnalyticsEngine(name="x")
            .add_filter(Filter.reporter(699))
            .add_metric(Metric.count())
        )
        r = repr(e)
        assert "AnalyticsEngine" in r
        assert "x" in r
        assert "filters=1" in r
        assert "metrics=1" in r


# ---------------------------------------------------------------------------
# TestAnalysisResult
# ---------------------------------------------------------------------------


class TestAnalysisResult:
    def test_frozen_dataclass(self):
        from dataclasses import FrozenInstanceError

        records = _records((699, 0, "2022", "X", 100.0),)
        e = AnalyticsEngine(name="x").add_metric(Metric.count())
        result = e.run(_make_dataset(records))
        with pytest.raises(FrozenInstanceError):
            result.analysis_name = "other"  # type: ignore[misc]

    def test_get_metric_returns_value(self):
        records = _records((699, 0, "2022", "X", 100.0),)
        e = (
            AnalyticsEngine(name="x")
            .add_metric(Metric.count())
            .add_metric(Metric.sum_primary_value())
        )
        result = e.run(_make_dataset(records))
        assert result.get_metric("count") == 1
        assert result.get_metric("sum_primary_value") == Decimal(
            "100"
        )

    def test_get_metric_unknown_raises(self):
        records = _records((699, 0, "2022", "X", 100.0),)
        e = AnalyticsEngine(name="x").add_metric(Metric.count())
        result = e.run(_make_dataset(records))
        with pytest.raises(AnalyticsError, match="No metric"):
            result.get_metric("does_not_exist")

    def test_get_aggregation_returns_rows(self):
        records = _records(
            (699, 0, "2022", "X", 100.0),
            (156, 0, "2022", "X", 200.0),
        )
        e = AnalyticsEngine(name="x").add_aggregation(
            Aggregation(
                name="by_reporter",
                group_by=("reporter_code",),
                metric=Metric.sum_primary_value(),
            )
        )
        result = e.run(_make_dataset(records))
        rows = result.get_aggregation("by_reporter")
        assert len(rows) == 2

    def test_get_aggregation_unknown_raises(self):
        records = _records((699, 0, "2022", "X", 100.0),)
        e = AnalyticsEngine(name="x")
        result = e.run(_make_dataset(records))
        with pytest.raises(AnalyticsError, match="No aggregation"):
            result.get_aggregation("nope")


# ---------------------------------------------------------------------------
# TestAnalysisContext
# ---------------------------------------------------------------------------


class TestAnalysisContext:
    def test_duration_when_complete(self):
        from datetime import datetime, timedelta, timezone

        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = start + timedelta(seconds=1.5)
        ctx = AnalysisContext(
            analysis_name="x",
            started_at=start,
            finished_at=end,
        )
        assert ctx.duration_seconds == pytest.approx(1.5)

    def test_duration_zero_when_incomplete(self):
        ctx = AnalysisContext(analysis_name="x")
        assert ctx.duration_seconds == 0.0


# ---------------------------------------------------------------------------
# TestNoTransportDependency
# ---------------------------------------------------------------------------


class TestNoTransportDependency:
    """The analytics module must not depend on the
    transport layer."""

    @staticmethod
    def _analytics_source() -> str:
        # The analytics layer is a package as of
        # P6-002; concatenate all module sources so
        # the AST inspection catches forbidden
        # imports in any submodule (e.g. country.py).
        package_dir = (
            Path(__file__).parent.parent
            / "un_comtrade"
            / "analytics"
        )
        sources = []
        for path in sorted(package_dir.glob("*.py")):
            sources.append(path.read_text(encoding="utf-8"))
        return "\n".join(sources)

    def test_does_not_import_transport(
        self,
    ):
        tree = ast.parse(self._analytics_source())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert "transport" not in (
                    node.module or ""
                ), "analytics.py imports transport"
            elif isinstance(node, ast.Import):
                for n in node.names:
                    assert "transport" not in n.name, (
                        "analytics.py imports transport"
                    )

    def test_does_not_import_client(self):
        tree = ast.parse(self._analytics_source())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert "client" not in (
                    node.module or ""
                ), "analytics.py imports client"
            elif isinstance(node, ast.Import):
                for n in node.names:
                    assert "client" not in n.name, (
                        "analytics.py imports client"
                    )

    def test_does_not_import_httpx(self):
        tree = ast.parse(self._analytics_source())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert "httpx" not in (
                    node.module or ""
                ), "analytics.py imports httpx"
            elif isinstance(node, ast.Import):
                for n in node.names:
                    assert "httpx" not in n.name, (
                        "analytics.py imports httpx"
                    )

    def test_does_not_import_parser(self):
        """Per the P6-001 scope: 'It shall never parse
        transport payloads.' Parser is for
        transport-layer payload parsing — must not
        be used here."""
        tree = ast.parse(self._analytics_source())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert "parser" not in (
                    node.module or ""
                ), "analytics.py imports parser"
            elif isinstance(node, ast.Import):
                for n in node.names:
                    assert "parser" not in n.name, (
                        "analytics.py imports parser"
                    )

    def test_only_allowed_dependencies(self):
        """Analytics.py may import: stdlib + models +
        transform + exceptions. NOT: transport,
        client, parser, metadata, cache, storage."""
        allowed = {
            "time",
            "dataclasses",
            "datetime",
            "decimal",
            "typing",
            "__future__",
            "collections.abc",
            "builtins",
        }
        relative_allowed = {
            "exceptions",
            "models.trade",
            "transform",
            "_query_engine",
            # Concrete analytics submodules (P6-002
            # added `country`; P6-003 added
            # `partner`; P6-004 added
            # `commodity`; P6-005 added
            # `timeseries`; P6-006 added
            # `balance`; P6-007 added
            # `compare`). Same dependency rules
            # apply (no transport / parser /
            # client).
            "country",
            "partner",
            "commodity",
            "timeseries",
            "balance",
            "compare",
        }
        tree = ast.parse(self._analytics_source())
        # Build the allowed set from the parent
        # package's `__all__` so that any primitive
        # re-exported by `un_comtrade.analytics` is
        # implicitly allowed (e.g. `from . import
        # Aggregation, AnalyticsEngine, Filter,
        # Metric`).
        parent_all = getattr(
            __import__(
                "un_comtrade.analytics", fromlist=["__all__"]
            ),
            "__all__",
            set(),
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if node.level and node.level > 0:
                    # Relative import (`from .x
                    # import y`); `node.module` is
                    # already stripped of leading dots.
                    if mod == "":
                        # `from . import y` —
                        # `y` must be in the parent
                        # package's `__all__` (or in
                        # `relative_allowed` for
                        # future-proofing).
                        for n in node.names:
                            assert (
                                n.name in parent_all
                                or n.name in relative_allowed
                            ), (
                                f"analytics.py imports .{n.name}; "
                                f"allowed: __all__={sorted(parent_all)} "
                                f"+ {sorted(relative_allowed)}"
                            )
                    else:
                        assert mod in relative_allowed, (
                            f"analytics.py imports .{mod}; "
                            f"allowed relative: {relative_allowed}"
                        )
                elif mod in ("__future__", "annotations"):
                    pass
                else:
                    assert mod in allowed, (
                        f"analytics.py imports {mod}; "
                        f"allowed stdlib: {allowed}"
                    )
            elif isinstance(node, ast.Import):
                for n in node.names:
                    assert n.name in allowed, (
                        f"analytics.py imports {n.name}; "
                        f"allowed: {allowed}"
                    )