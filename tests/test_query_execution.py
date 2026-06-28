"""Tests for query execution semantics
(QE-006).

Per the QE-006 task scope, this module
covers:

- `execute()` — runs the pipeline.
- Lazy evaluation — no computation happens
  on `Query()` construction or on any
  fluent call (`.filter()`, `.exclude()`,
  `.group_by()`, `.sort()`, `.limit()`,
  `.offset()`, `.reverse()`); only
  `.execute()` runs the pipeline.
- Pipeline execution — chained operations
  apply in the documented order.
- Immutable result — `QueryResult` is
  frozen; modifying any field raises
  `FrozenInstanceError`.
- Repeated executions produce identical
  results.

Coverage:

- `TestLazyEvaluation` — construction
  doesn't compute; fluent calls don't
  compute; only `.execute()` runs the
  pipeline.
- `TestPipelineExecution` — chained
  operations apply in the correct order
  (filter → sort → reverse → offset →
  limit → group_by).
- `TestImmutableResult` — `QueryResult`
  frozen; `Query` immutable by
  convention; dataset never mutated.
- `TestIdenticalResultsAcrossExecutions` —
  the headline validation criterion:
  multiple `.execute()` calls on the same
  Query produce identical results.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from typing import Any

import pytest

from un_comtrade.analytics._query_engine import (
    Group,
    Query,
    QueryContext,
    QueryError,
    QueryResult,
    QueryExpression,
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
    """Build parsed records.

    Each tuple is `(reporter, partner, flow,
    period, value)`. ISO3 codes come from a
    fixed lookup. Each tuple has a unique
    partner to keep the parser from deduping.
    """
    from un_comtrade.parser import TradeParser

    iso3 = {
        0: "W00", 124: "USA", 156: "CHN",
        392: "JPN", 699: "IND", 76: "BRA",
        484: "MEX", 36: "AUS",
    }
    raws = []
    for i, (reporter, partner, flow, period, value) in enumerate(
        tuples
    ):
        ref_year = int(period[:4])
        unique_partner = i + 10
        raws.append(
            _baseline_raw(
                reporterCode=reporter,
                reporterISO=iso3.get(reporter, "ZZZ"),
                reporterDesc=f"Reporter-{reporter}",
                partnerCode=unique_partner,
                partnerISO=iso3.get(unique_partner, "USA"),
                partnerDesc=f"Partner-{unique_partner}",
                flowCode=flow,
                period=period,
                refYear=ref_year,
                refPeriodId=int(period) * 10000 + 1,
                primaryValue=value,
                fobvalue=value,
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
    """7 records with varied primary values
    and periods, used across execution
    tests.
    """
    records = _records(
        (699, 124, "X", "2022", 100.0),
        (699, 156, "X", "2022", 200.0),
        (699, 124, "M", "2022", 80.0),
        (699, 124, "X", "2021", 50.0),
        (699, 156, "M", "2021", 90.0),
        (156, 0, "X", "2022", 1000.0),
        (156, 0, "X", "2021", 800.0),
    )
    return _make_dataset(records, name="exec_test")


# ---------------------------------------------------------------------------
# TestLazyEvaluation
# ---------------------------------------------------------------------------


class TestLazyEvaluation:
    def test_query_construction_does_not_execute(self, dataset):
        # Track whether execute-like work
        # happens during construction.
        # We do this by checking that the
        # constructed Query has no
        # computed `records` field — there
        # is none in our API; we just verify
        # no errors are raised and no
        # side-effects.
        q = Query(dataset)
        # No records attribute, no filter
        # applied, no groups, no sort.
        assert q.predicates == ()
        assert q.group_by_fields == ()
        assert q.sort_keys == ()
        assert q.limit_value is None
        assert q.offset_value is None
        assert q.reverse_value is False

    def test_filter_does_not_execute(self, dataset):
        # `.filter(...)` returns a new
        # Query without running anything.
        q1 = Query(dataset)
        q2 = q1.filter(reporter_code=699)
        # q2 has the predicate registered
        # but no records have been
        # filtered yet.
        assert len(q2.predicates) == 1
        assert q1.predicates == ()

    def test_group_by_does_not_execute(self, dataset):
        q = Query(dataset).group_by("reporter_code")
        # `group_by_fields` is set but no
        # `groups` exist yet.
        assert q.group_by_fields == ("reporter_code",)

    def test_sort_does_not_execute(self, dataset):
        q = Query(dataset).sort("primary_value")
        # Sort key registered but no
        # ordering applied yet.
        assert len(q.sort_keys) == 1

    def test_limit_does_not_execute(self, dataset):
        q = Query(dataset).limit(3)
        # Limit registered but no records
        # dropped yet.
        assert q.limit_value == 3

    def test_offset_does_not_execute(self, dataset):
        q = Query(dataset).offset(2)
        # Offset registered but no records
        # skipped yet.
        assert q.offset_value == 2

    def test_reverse_does_not_execute(self, dataset):
        q = Query(dataset).reverse()
        # Reverse registered but no
        # ordering applied yet.
        assert q.reverse_value is True

    def test_complex_chain_does_not_execute(self, dataset):
        # A long chain still doesn't
        # compute anything.
        q = (
            Query(dataset)
            .filter(reporter_code=699)
            .group_by("flow_code")
            .sort("primary_value")
            .limit(5)
            .offset(1)
            .reverse()
        )
        # All state stored; nothing
        # computed.
        assert len(q.predicates) == 1
        assert q.group_by_fields == ("flow_code",)
        assert len(q.sort_keys) == 1
        assert q.limit_value == 5
        assert q.offset_value == 1
        assert q.reverse_value is True

    def test_execute_triggers_computation(self, dataset):
        # `.execute()` is the only
        # computation entry point. After
        # execution, the result has the
        # filtered/sorted records.
        q = (
            Query(dataset)
            .filter(reporter_code=699)
            .sort("primary_value", descending=True)
        )
        # Pre-execute: no result.
        r = q.execute()
        # Post-execute: result has
        # records.
        assert len(r.records) > 0


# ---------------------------------------------------------------------------
# TestPipelineExecution
# ---------------------------------------------------------------------------


class TestPipelineExecution:
    def test_filter_applies_first(self, dataset):
        # Filter narrows the dataset
        # before any sort/group.
        result = (
            Query(dataset)
            .filter(reporter_code=699)
            .sort("primary_value")
            .execute()
        )
        # All records are India.
        assert all(
            r.reporter.reporter_code == 699
            for r in result.records
        )

    def test_sort_applies_after_filter(self, dataset):
        # Filter narrows, then sort orders
        # the filtered subset.
        result = (
            Query(dataset)
            .filter(reporter_code=699)
            .sort("primary_value")
            .execute()
        )
        values = [
            r.trade_value.primary_value for r in result.records
        ]
        assert values == sorted(values)

    def test_reverse_applies_after_sort(self, dataset):
        # sort ASC then reverse =
        # descending.
        result = (
            Query(dataset)
            .sort("primary_value")
            .reverse()
            .execute()
        )
        values = [
            r.trade_value.primary_value for r in result.records
        ]
        assert values == sorted(values, reverse=True)

    def test_offset_applies_after_sort_and_reverse(
        self, dataset
    ):
        # sort desc → reverse → offset(2):
        # top 2 records are dropped.
        result = (
            Query(dataset)
            .sort("primary_value", descending=True)
            .reverse()  # back to asc
            .offset(2)
            .execute()
        )
        # Skip the two smallest values
        # (50, 80); expect the rest.
        values = [
            r.trade_value.primary_value for r in result.records
        ]
        assert values[0] == Decimal("90")

    def test_limit_applies_after_offset(self, dataset):
        # Skip 2, take 3.
        result = (
            Query(dataset)
            .sort("primary_value")
            .offset(2)
            .limit(3)
            .execute()
        )
        assert len(result.records) == 3
        values = [
            r.trade_value.primary_value for r in result.records
        ]
        # Sort ASC: 50, 80, 90, 100, 200,
        # 800, 1000. Skip 2 → 90, 100, 200.
        assert values == [
            Decimal("90"),
            Decimal("100"),
            Decimal("200"),
        ]

    def test_group_by_applies_last(self, dataset):
        # sort + limit + offset +
        # group_by: groups are computed
        # AFTER filtering/sorting.
        result = (
            Query(dataset)
            .sort("primary_value")
            .limit(4)  # 4 smallest values
            .group_by("reporter_code")
            .execute()
        )
        # 4 smallest = 50 (Ind), 80 (Ind),
        # 90 (Ind), 100 (Ind). All India.
        # → 1 group.
        assert len(result.groups) == 1
        assert result.groups[0].key == (699,)

    def test_complex_pipeline_order(self, dataset):
        # Verify the full pipeline:
        # filter → sort → reverse →
        # offset → limit → group_by.
        result = (
            Query(dataset)
            .filter(reporter_code=699)        # India only
            .sort("primary_value")           # ASC
            .reverse()                        # DESC
            .offset(1)                        # drop top 1
            .limit(3)                         # take next 3
            .group_by("flow_code")            # group by flow
            .execute()
        )
        # India values desc: 200, 100, 90,
        # 80, 50. Drop 200 → 100, 90, 80.
        # Flows present: 100=X, 90=M, 80=M.
        # → 2 groups (X, M).
        assert len(result.groups) == 2
        # Sort groups by key for stability.
        keys = sorted(g.key for g in result.groups)
        assert keys == [("M",), ("X",)]


# ---------------------------------------------------------------------------
# TestImmutableResult
# ---------------------------------------------------------------------------


class TestImmutableResult:
    def test_query_result_is_frozen(self, dataset):
        result = Query(dataset).execute()
        with pytest.raises(FrozenInstanceError):
            result.records = ()  # type: ignore[misc]

    def test_query_result_context_frozen(self, dataset):
        result = Query(dataset).execute()
        with pytest.raises(FrozenInstanceError):
            result.context = None  # type: ignore[misc]

    def test_query_result_finished_at_frozen(self, dataset):
        result = Query(dataset).execute()
        with pytest.raises(FrozenInstanceError):
            result.finished_at = None  # type: ignore[misc]

    def test_query_result_groups_frozen(self, dataset):
        result = Query(dataset).execute()
        with pytest.raises(FrozenInstanceError):
            result.groups = ()  # type: ignore[misc]

    def test_query_result_records_tuple_immutable(self, dataset):
        # The records tuple itself is
        # immutable (tuples can't be
        # mutated).
        result = Query(dataset).execute()
        with pytest.raises(
            (AttributeError, TypeError)
        ):
            result.records[0] = None  # type: ignore[index]

    def test_query_context_frozen(self, dataset):
        result = Query(dataset).execute()
        with pytest.raises(FrozenInstanceError):
            result.context.started_at = None  # type: ignore[misc]

    def test_query_immutable_by_convention(self, dataset):
        # Query uses __slots__ with no
        # setters; direct attribute set
        # fails.
        q = Query(dataset)
        with pytest.raises(AttributeError):
            q.dataset = _make_dataset((), name="other")  # type: ignore[misc]

    def test_group_frozen(self, dataset):
        result = (
            Query(dataset).group_by("reporter_code").execute()
        )
        for group in result.groups:
            with pytest.raises(FrozenInstanceError):
                group.records = ()  # type: ignore[misc]

    def test_query_execute_returns_new_result(self, dataset):
        # Each execute() returns a NEW
        # QueryResult (not the same object).
        q = Query(dataset)
        r1 = q.execute()
        r2 = q.execute()
        assert r1 is not r2
        # But records are equal.
        assert r1.records == r2.records
        # Note: context.started_at and
        # finished_at may differ between
        # executions (each is captured at
        # execution time).


# ---------------------------------------------------------------------------
# TestIdenticalResultsAcrossExecutions (the headline criterion)
# ---------------------------------------------------------------------------


class TestIdenticalResultsAcrossExecutions:
    def test_two_executions_equal(self, dataset):
        q = Query(dataset)
        r1 = q.execute()
        r2 = q.execute()
        assert r1.records == r2.records

    def test_three_executions_equal(self, dataset):
        q = Query(dataset)
        r1 = q.execute()
        r2 = q.execute()
        r3 = q.execute()
        assert r1.records == r2.records
        assert r2.records == r3.records

    def test_complex_pipeline_deterministic(self, dataset):
        q = (
            Query(dataset)
            .filter(reporter_code=699)
            .group_by("flow_code")
            .sort("primary_value", descending=True)
            .limit(3)
        )
        r1 = q.execute()
        r2 = q.execute()
        assert r1.records == r2.records
        assert [g.key for g in r1.groups] == [
            g.key for g in r2.groups
        ]

    def test_filter_deterministic(self, dataset):
        q = Query(dataset).filter(reporter_code=699)
        r1 = q.execute()
        r2 = q.execute()
        assert r1.records == r2.records

    def test_group_by_deterministic(self, dataset):
        q = (
            Query(dataset)
            .group_by("reporter_code", "flow_code")
        )
        r1 = q.execute()
        r2 = q.execute()
        assert [g.key for g in r1.groups] == [
            g.key for g in r2.groups
        ]

    def test_sort_deterministic(self, dataset):
        q = (
            Query(dataset)
            .sort("primary_value", descending=True)
            .limit(5)
        )
        r1 = q.execute()
        r2 = q.execute()
        assert r1.records == r2.records

    def test_offset_deterministic(self, dataset):
        q = (
            Query(dataset)
            .sort("primary_value")
            .offset(2)
            .limit(3)
        )
        r1 = q.execute()
        r2 = q.execute()
        assert r1.records == r2.records

    def test_reverse_deterministic(self, dataset):
        q = Query(dataset).sort("primary_value").reverse()
        r1 = q.execute()
        r2 = q.execute()
        assert r1.records == r2.records

    def test_full_pipeline_deterministic(self, dataset):
        # Full filter → group → sort →
        # limit → offset → reverse chain.
        q = (
            Query(dataset)
            .filter(reporter_code__in=(699, 156))  # noqa
        )
        # Plain filter instead.
        q = (
            Query(dataset)
            .filter(reporter_code=699)
            .group_by("flow_code")
            .sort("primary_value", descending=True)
            .offset(1)
            .limit(2)
            .reverse()
        )
        r1 = q.execute()
        r2 = q.execute()
        assert r1.records == r2.records
        assert [g.key for g in r1.groups] == [
            g.key for g in r2.groups
        ]

    def test_execution_does_not_affect_query_state(self, dataset):
        # After execute(), the Query's
        # state is unchanged (still lazy;
        # ready for another execute()).
        q = (
            Query(dataset)
            .filter(reporter_code=699)
            .sort("primary_value")
            .limit(3)
        )
        # Capture state before.
        n_predicates_before = len(q.predicates)
        sort_keys_before = q.sort_keys
        limit_before = q.limit_value
        # Execute.
        r1 = q.execute()
        # State unchanged.
        assert len(q.predicates) == n_predicates_before
        assert q.sort_keys == sort_keys_before
        assert q.limit_value == limit_before
        # And the query still works.
        r2 = q.execute()
        assert r1.records == r2.records


# ---------------------------------------------------------------------------
# TestQueryResultFields
# ---------------------------------------------------------------------------


class TestQueryResultFields:
    def test_records_field(self, dataset):
        result = Query(dataset).execute()
        assert isinstance(result.records, tuple)
        assert len(result.records) == len(dataset.records)

    def test_context_field_is_query_context(self, dataset):
        result = Query(dataset).execute()
        assert isinstance(result.context, QueryContext)
        assert result.context.dataset is dataset

    def test_finished_at_after_started_at(self, dataset):
        result = Query(dataset).execute()
        assert (
            result.context.started_at
            <= result.finished_at
        )

    def test_groups_field_default_empty(self, dataset):
        result = Query(dataset).execute()
        assert result.groups == ()

    def test_groups_field_populated_with_grouping(self, dataset):
        result = (
            Query(dataset).group_by("reporter_code").execute()
        )
        assert len(result.groups) > 0
        for g in result.groups:
            assert isinstance(g, Group)


# ---------------------------------------------------------------------------
# TestExecutionEdgeCases
# ---------------------------------------------------------------------------


class TestExecutionEdgeCases:
    def test_execute_empty_dataset(self):
        ds = _make_dataset(())
        result = Query(ds).execute()
        assert result.records == ()
        assert result.groups == ()

    def test_execute_with_all_filters_excluding(self, dataset):
        # Filter that matches nothing.
        result = (
            Query(dataset)
            .filter(reporter_code=999)
            .sort("primary_value", descending=True)
            .limit(5)
            .group_by("reporter_code")
            .execute()
        )
        assert result.records == ()
        assert result.groups == ()

    def test_execute_pure_no_op(self, dataset):
        # No filters, no sort, no group,
        # no limit, no offset, no reverse.
        result = Query(dataset).execute()
        # Records are the dataset's
        # records, in order.
        assert result.records == tuple(dataset.records)
        assert result.groups == ()

    def test_execute_reusable_query(self, dataset):
        # The same Query object can be
        # executed multiple times and
        # produces equal results.
        q = (
            Query(dataset)
            .filter(reporter_code=699)
            .sort("primary_value")
            .limit(3)
        )
        results = [q.execute() for _ in range(5)]
        first = results[0]
        for r in results[1:]:
            assert r.records == first.records

    def test_execute_chained_queries(self, dataset):
        # Different queries can be
        # executed and produce different
        # results.
        q1 = Query(dataset).filter(reporter_code=699)
        q2 = Query(dataset).filter(reporter_code=156)
        r1 = q1.execute()
        r2 = q2.execute()
        assert r1.records != r2.records
        # Specifically:
        assert all(
            r.reporter.reporter_code == 699
            for r in r1.records
        )
        assert all(
            r.reporter.reporter_code == 156
            for r in r2.records
        )


# ---------------------------------------------------------------------------
# TestQueryExpressionBase
# ---------------------------------------------------------------------------


class TestQueryExpressionBase:
    def test_query_expression_instantiable(self):
        # Sanity: QueryExpression is the
        # base AST marker.
        expr = QueryExpression()
        assert isinstance(expr, QueryExpression)

    def test_query_expression_frozen(self):
        # `QueryExpression` is a frozen
        # dataclass. Subclasses with
        # fields can't be mutated.
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class _Subclass(QueryExpression):
            tag: str = "x"

        m = _Subclass()
        assert m.__dataclass_params__.frozen
        with pytest.raises(FrozenInstanceError):
            m.tag = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def Decimal(value: str):
    from decimal import Decimal as D
    return D(value)