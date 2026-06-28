"""Tests for the query filtering engine
(QE-002).

Per the QE-002 task scope, this module
covers:

- `FieldPredicate` — atomic predicate
  testing a record field against a value.
- `AndPredicate` / `OrPredicate` /
  `NotPredicate` — composition nodes.
- `Predicate.__call__` — runtime
  evaluation.
- `Predicate.__and__`, `__or__`,
  `__invert__` — composition operators.
- `Query.filter(...)` — fluent filter
  (positional predicate or kwargs).
- `Query.exclude(...)` — fluent exclusion
  (= `.filter(~predicate)`).
- Multiple filters compose.
- Immutable queries (each fluent call
  returns a NEW `Query`).
- Deterministic execution (same input
  yields same output).
- `CanonicalDataset` is never mutated.

Validation criteria (per task spec):

- Multiple filters compose ✅
- Immutable queries ✅
- Deterministic execution ✅
- CanonicalDataset unchanged ✅

Coverage:

- `TestFieldPredicate` — construction,
  field resolution (shorthand + dotted),
  all 8 operators (eq, ne, lt, le, gt, ge,
  in, not_in), invalid operators,
  invalid field paths.
- `TestAndPredicate` / `TestOrPredicate`
  / `TestNotPredicate` — composition
  semantics, validation.
- `TestPredicateComposition` — `&`, `|`,
  `~` operators on `Predicate`.
- `TestQueryFilter` — fluent
  `.filter(predicate)`, `.filter(**kwargs)`,
  multiple filters compose (AND at the
  Query level), immutable queries.
- `TestQueryExclude` — fluent
  `.exclude(...)`, equivalence to
  `.filter(~predicate)`.
- `TestQueryFilterErrorsPropagated` —
  invalid args.
- `TestCanonicalDatasetUnchanged` —
  dataset is read-only after multiple
  queries.
- `TestDeterministicExecution` — same
  query yields same result on repeat.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from typing import Any

import pytest

from un_comtrade.analytics._query_engine import (
    AndPredicate,
    FieldPredicate,
    NotPredicate,
    OrPredicate,
    Predicate,
    Query,
    QueryContext,
    QueryError,
    QueryResult,
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
    `(reporter, partner, flow, period, value)`.
    ISO3 codes come from a fixed lookup.
    """
    from un_comtrade.parser import TradeParser

    iso3 = {
        0: "W00", 124: "USA", 156: "CHN",
        392: "JPN", 699: "IND", 76: "BRA",
    }
    raws = []
    for reporter, partner, flow, period, value in tuples:
        ref_year = int(period[:4])
        raws.append(
            _baseline_raw(
                reporterCode=reporter,
                reporterISO=iso3.get(reporter, "ZZZ"),
                reporterDesc=f"Reporter-{reporter}",
                partnerCode=partner,
                partnerISO=iso3.get(partner, "ZZZ"),
                partnerDesc=f"Partner-{partner}",
                period=period,
                refYear=ref_year,
                refPeriodId=int(period) * 10000 + 1,
                flowCode=flow,
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
    """A canonical test fixture:
    5 India records (3 export, 2 import)
    plus 2 China records (1 export, 1 import).
    """
    records = _records(
        # India, 2022
        (699, 124, "X", "2022", 100.0),
        (699, 156, "X", "2022", 200.0),
        (699, 124, "M", "2022", 80.0),
        # India, 2021
        (699, 124, "X", "2021", 150.0),
        (699, 156, "M", "2021", 90.0),
        # China
        (156, 0, "X", "2022", 1000.0),
        (156, 0, "M", "2022", 500.0),
    )
    return _make_dataset(records, name="filter_test")


# ---------------------------------------------------------------------------
# TestFieldPredicate
# ---------------------------------------------------------------------------


class TestFieldPredicate:
    def test_frozen(self):
        p = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        with pytest.raises(FrozenInstanceError):
            p.value = 156  # type: ignore[misc]

    def test_is_predicate(self):
        p = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        assert isinstance(p, Predicate)

    def test_is_query_expression(self):
        # Predicate subclasses QueryExpression.
        from un_comtrade.analytics._query_engine import (
            QueryExpression,
        )
        p = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        assert isinstance(p, QueryExpression)

    def test_field_must_be_string(self):
        with pytest.raises(QueryError, match="non-empty"):
            FieldPredicate(
                field="",  # type: ignore[arg-type]
                operator="eq",
                value=699,
            )

    def test_unknown_operator_raises(self):
        with pytest.raises(QueryError, match="operator"):
            FieldPredicate(
                field="reporter_code",
                operator="bogus",
                value=699,
            )

    def test_eq_operator(self, dataset):
        p = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        kept = [r for r in dataset.records if p(r)]
        assert all(
            r.reporter.reporter_code == 699 for r in kept
        )
        assert len(kept) == 5

    def test_ne_operator(self, dataset):
        p = FieldPredicate(
            field="reporter_code", operator="ne", value=699
        )
        kept = [r for r in dataset.records if p(r)]
        assert all(
            r.reporter.reporter_code != 699 for r in kept
        )
        assert len(kept) == 2

    def test_lt_operator(self, dataset):
        p = FieldPredicate(
            field="ref_year", operator="lt", value=2022
        )
        kept = [r for r in dataset.records if p(r)]
        assert all(r.ref_year < 2022 for r in kept)
        assert len(kept) == 2  # 2021 records

    def test_le_operator(self, dataset):
        p = FieldPredicate(
            field="ref_year", operator="le", value=2021
        )
        kept = [r for r in dataset.records if p(r)]
        assert all(r.ref_year <= 2021 for r in kept)
        assert len(kept) == 2

    def test_gt_operator(self, dataset):
        p = FieldPredicate(
            field="primary_value", operator="gt", value=100
        )
        kept = [r for r in dataset.records if p(r)]
        assert all(
            r.trade_value.primary_value > 100 for r in kept
        )

    def test_ge_operator(self, dataset):
        p = FieldPredicate(
            field="primary_value", operator="ge", value=100
        )
        kept = [r for r in dataset.records if p(r)]
        assert all(
            r.trade_value.primary_value >= 100 for r in kept
        )

    def test_in_operator(self, dataset):
        p = FieldPredicate(
            field="reporter_code",
            operator="in",
            value=(699, 156),
        )
        kept = [r for r in dataset.records if p(r)]
        assert len(kept) == 7  # all

    def test_in_operator_subset(self, dataset):
        p = FieldPredicate(
            field="reporter_code",
            operator="in",
            value=(699,),
        )
        kept = [r for r in dataset.records if p(r)]
        assert len(kept) == 5

    def test_in_operator_requires_sequence(self, dataset):
        p = FieldPredicate(
            field="reporter_code",
            operator="in",
            value=699,  # not a sequence
        )
        with pytest.raises(QueryError):
            p(dataset.records[0])

    def test_not_in_operator(self, dataset):
        p = FieldPredicate(
            field="reporter_code",
            operator="not_in",
            value=(699,),
        )
        kept = [r for r in dataset.records if p(r)]
        assert all(
            r.reporter.reporter_code != 699 for r in kept
        )
        assert len(kept) == 2

    def test_dotted_path(self, dataset):
        p = FieldPredicate(
            field="flow.flow_code", operator="eq", value="X"
        )
        kept = [r for r in dataset.records if p(r)]
        assert all(r.flow.flow_code == "X" for r in kept)
        assert len(kept) == 4  # 3 India X + 1 China X

    def test_explicit_dotted_path(self, dataset):
        # Even with shorthand map, explicit
        # dotted paths still work.
        p = FieldPredicate(
            field="reporter.reporter_code",
            operator="eq",
            value=699,
        )
        kept = [r for r in dataset.records if p(r)]
        assert len(kept) == 5

    def test_unknown_field_raises(self, dataset):
        p = FieldPredicate(
            field="bogus.nonexistent",
            operator="eq",
            value=1,
        )
        with pytest.raises(QueryError, match="unknown"):
            p(dataset.records[0])

    def test_unknown_top_level_field(self, dataset):
        p = FieldPredicate(
            field="totally_made_up",
            operator="eq",
            value=1,
        )
        with pytest.raises(QueryError):
            p(dataset.records[0])

    def test_incompatible_types_dont_crash(self, dataset):
        # Decimal vs str comparison should not
        # raise; it should return False.
        p = FieldPredicate(
            field="primary_value",
            operator="eq",
            value="not a number",
        )
        assert p(dataset.records[0]) is False


# ---------------------------------------------------------------------------
# TestAndPredicate
# ---------------------------------------------------------------------------


class TestAndPredicate:
    def test_frozen(self):
        a = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        b = FieldPredicate(
            field="flow_code", operator="eq", value="X"
        )
        ap = AndPredicate(a, b)
        with pytest.raises(FrozenInstanceError):
            ap.left = b  # type: ignore[misc]

    def test_requires_predicate_left(self):
        with pytest.raises(QueryError, match="left"):
            AndPredicate(  # type: ignore[arg-type]
                left="not a predicate",
                right=FieldPredicate(
                    field="x", operator="eq", value=1
                ),
            )

    def test_requires_predicate_right(self):
        with pytest.raises(QueryError, match="right"):
            AndPredicate(
                left=FieldPredicate(
                    field="x", operator="eq", value=1
                ),
                right="not a predicate",  # type: ignore[arg-type]
            )

    def test_and_logic(self, dataset):
        p1 = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        p2 = FieldPredicate(
            field="flow_code", operator="eq", value="X"
        )
        ap = AndPredicate(p1, p2)
        kept = [r for r in dataset.records if ap(r)]
        assert all(
            r.reporter.reporter_code == 699
            and r.flow.flow_code == "X"
            for r in kept
        )
        assert len(kept) == 3


# ---------------------------------------------------------------------------
# TestOrPredicate
# ---------------------------------------------------------------------------


class TestOrPredicate:
    def test_or_logic(self, dataset):
        p1 = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        p2 = FieldPredicate(
            field="reporter_code", operator="eq", value=156
        )
        op = OrPredicate(p1, p2)
        kept = [r for r in dataset.records if op(r)]
        assert len(kept) == 7  # all

    def test_requires_predicate_left(self):
        with pytest.raises(QueryError):
            OrPredicate(  # type: ignore[arg-type]
                left="x",
                right=FieldPredicate(
                    field="x", operator="eq", value=1
                ),
            )


# ---------------------------------------------------------------------------
# TestNotPredicate
# ---------------------------------------------------------------------------


class TestNotPredicate:
    def test_not_logic(self, dataset):
        p = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        np = NotPredicate(p)
        kept = [r for r in dataset.records if np(r)]
        assert all(
            r.reporter.reporter_code != 699 for r in kept
        )
        assert len(kept) == 2

    def test_double_negation(self, dataset):
        p = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        nn = NotPredicate(NotPredicate(p))
        kept = [r for r in dataset.records if nn(r)]
        assert all(
            r.reporter.reporter_code == 699 for r in kept
        )
        assert len(kept) == 5


# ---------------------------------------------------------------------------
# TestPredicateComposition
# ---------------------------------------------------------------------------


class TestPredicateComposition:
    def test_and_operator(self, dataset):
        p1 = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        p2 = FieldPredicate(
            field="flow_code", operator="eq", value="X"
        )
        composed = p1 & p2
        assert isinstance(composed, AndPredicate)
        kept = [r for r in dataset.records if composed(r)]
        assert len(kept) == 3

    def test_or_operator(self, dataset):
        p1 = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        p2 = FieldPredicate(
            field="reporter_code", operator="eq", value=156
        )
        composed = p1 | p2
        assert isinstance(composed, OrPredicate)
        kept = [r for r in dataset.records if composed(r)]
        assert len(kept) == 7

    def test_invert_operator(self, dataset):
        p = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        inv = ~p
        assert isinstance(inv, NotPredicate)
        kept = [r for r in dataset.records if inv(r)]
        assert len(kept) == 2

    def test_chained_composition(self, dataset):
        # (reporter=699 AND flow=X) OR
        # reporter=156.
        p1 = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        p2 = FieldPredicate(
            field="flow_code", operator="eq", value="X"
        )
        p3 = FieldPredicate(
            field="reporter_code", operator="eq", value=156
        )
        composed = (p1 & p2) | p3
        kept = [r for r in dataset.records if composed(r)]
        # 3 (India X) + 2 (China) = 5
        assert len(kept) == 5

    def test_complex_composition(self, dataset):
        # NOT (reporter=699 AND ref_year<2022)
        p1 = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        p2 = FieldPredicate(
            field="ref_year", operator="lt", value=2022
        )
        composed = ~(p1 & p2)
        kept = [r for r in dataset.records if composed(r)]
        # All except 2021 India records (2).
        assert len(kept) == 5


# ---------------------------------------------------------------------------
# TestQueryFilter
# ---------------------------------------------------------------------------


class TestQueryFilter:
    def test_kwarg_filter(self, dataset):
        result = Query(dataset).filter(reporter_code=699).execute()
        assert all(
            r.reporter.reporter_code == 699 for r in result.records
        )
        assert len(result.records) == 5

    def test_explicit_predicate_filter(self, dataset):
        p = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        result = Query(dataset).filter(p).execute()
        assert len(result.records) == 5

    def test_multiple_filters_compose(self, dataset):
        # Two .filter() calls — both must
        # match (logical AND at Query level).
        result = (
            Query(dataset)
            .filter(reporter_code=699)
            .filter(flow_code="X")
            .execute()
        )
        assert len(result.records) == 3

    def test_filter_with_dotted_path_predicate(self, dataset):
        p = FieldPredicate(
            field="flow.flow_code", operator="eq", value="X"
        )
        result = Query(dataset).filter(p).execute()
        assert all(
            r.flow.flow_code == "X" for r in result.records
        )
        assert len(result.records) == 4

    def test_kwargs_combined_with_AND(self, dataset):
        # Two kwargs in one call → combined
        # with AND.
        result = (
            Query(dataset)
            .filter(reporter_code=699, flow_code="X")
            .execute()
        )
        assert len(result.records) == 3

    def test_filter_with_composed_predicate(self, dataset):
        p1 = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        p2 = FieldPredicate(
            field="ref_year", operator="lt", value=2022
        )
        result = Query(dataset).filter(p1 & p2).execute()
        assert len(result.records) == 2

    def test_filter_returns_new_query(self, dataset):
        q1 = Query(dataset)
        q2 = q1.filter(reporter_code=699)
        assert q1 is not q2
        # Original q1 has no predicates.
        assert len(q1.predicates) == 0
        assert len(q2.predicates) == 1

    def test_filter_does_not_mutate_receiver(self, dataset):
        q1 = Query(dataset)
        original_predicates = q1.predicates
        q1.filter(reporter_code=699)
        # q1's predicates are unchanged.
        assert q1.predicates == original_predicates
        assert len(q1.predicates) == 0

    def test_filter_with_no_args_raises(self, dataset):
        with pytest.raises(QueryError):
            Query(dataset).filter()

    def test_filter_with_both_positional_and_kwargs_raises(
        self, dataset
    ):
        p = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        with pytest.raises(QueryError):
            Query(dataset).filter(p, reporter_code=699)

    def test_empty_predicate_list_returns_all_records(
        self, dataset
    ):
        # No filter applied → all records.
        result = Query(dataset).execute()
        assert len(result.records) == len(dataset.records)

    def test_predicates_property_returns_tuple(self, dataset):
        q = Query(dataset).filter(reporter_code=699)
        assert isinstance(q.predicates, tuple)

    def test_predicates_property_is_copy(self, dataset):
        q = Query(dataset).filter(reporter_code=699)
        snapshot = q.predicates
        assert snapshot == q.predicates


# ---------------------------------------------------------------------------
# TestQueryExclude
# ---------------------------------------------------------------------------


class TestQueryExclude:
    def test_kwarg_exclude(self, dataset):
        result = (
            Query(dataset).exclude(reporter_code=699).execute()
        )
        assert all(
            r.reporter.reporter_code != 699 for r in result.records
        )
        assert len(result.records) == 2

    def test_explicit_predicate_exclude(self, dataset):
        p = FieldPredicate(
            field="flow_code", operator="eq", value="X"
        )
        result = Query(dataset).exclude(p).execute()
        assert all(
            r.flow.flow_code != "X" for r in result.records
        )
        assert len(result.records) == 3

    def test_exclude_equivalent_to_filter_invert(self, dataset):
        p = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        result_exclude = Query(dataset).exclude(p).execute()
        result_filter = Query(dataset).filter(~p).execute()
        assert (
            result_exclude.records == result_filter.records
        )

    def test_exclude_returns_new_query(self, dataset):
        q1 = Query(dataset)
        q2 = q1.exclude(reporter_code=699)
        assert q1 is not q2
        assert len(q1.predicates) == 0
        assert len(q2.predicates) == 1

    def test_exclude_with_no_args_raises(self, dataset):
        with pytest.raises(QueryError):
            Query(dataset).exclude()


# ---------------------------------------------------------------------------
# TestQueryFilterErrorsPropagated
# ---------------------------------------------------------------------------


class TestQueryFilterErrorsPropagated:
    def test_filter_chained_after_exclude(self, dataset):
        result = (
            Query(dataset)
            .exclude(reporter_code=699)
            .filter(flow_code="X")
            .execute()
        )
        # All China records (2) but flow=X
        # → only 1.
        assert len(result.records) == 1

    def test_exclude_chained_after_filter(self, dataset):
        result = (
            Query(dataset)
            .filter(reporter_code=699)
            .exclude(flow_code="X")
            .execute()
        )
        # All India (5) minus X (3) = 2.
        assert len(result.records) == 2

    def test_filter_and_exclude_with_or(self, dataset):
        # reporter=699 OR reporter=156; then
        # exclude flow=M. Result: all X.
        p1 = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        p2 = FieldPredicate(
            field="reporter_code", operator="eq", value=156
        )
        result = (
            Query(dataset)
            .filter(p1 | p2)
            .exclude(flow_code="M")
            .execute()
        )
        assert all(
            r.flow.flow_code == "X" for r in result.records
        )
        assert len(result.records) == 4  # 3 India X + 1 China X


# ---------------------------------------------------------------------------
# TestCanonicalDatasetUnchanged
# ---------------------------------------------------------------------------


class TestCanonicalDatasetUnchanged:
    def test_dataset_unchanged_after_filter(self, dataset):
        before = tuple(dataset.records)
        Query(dataset).filter(reporter_code=699).execute()
        Query(dataset).exclude(flow_code="X").execute()
        Query(dataset).filter(
            FieldPredicate(
                field="ref_year", operator="eq", value=2022
            )
        ).execute()
        # Same tuple content.
        assert tuple(dataset.records) == before
        assert len(dataset.records) == len(before)

    def test_dataset_records_tuple_same_object(self, dataset):
        # The records tuple identity is
        # preserved (no mutation).
        before_id = id(dataset.records)
        Query(dataset).filter(reporter_code=699).execute()
        after_id = id(dataset.records)
        assert before_id == after_id


# ---------------------------------------------------------------------------
# TestDeterministicExecution
# ---------------------------------------------------------------------------


class TestDeterministicExecution:
    def test_same_query_same_result(self, dataset):
        q = Query(dataset).filter(reporter_code=699)
        r1 = q.execute()
        r2 = q.execute()
        # Records are equal.
        assert r1.records == r2.records
        # Record count is the same.
        assert len(r1.records) == len(r2.records)

    def test_re_execution_independent(self, dataset):
        # Re-execute after first run.
        r1 = Query(dataset).filter(reporter_code=699).execute()
        r2 = Query(dataset).filter(reporter_code=699).execute()
        # Different QueryResult objects
        # (different finished_at timestamps).
        assert r1 is not r2
        # But same record contents.
        assert r1.records == r2.records

    def test_complex_query_deterministic(self, dataset):
        p1 = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        p2 = FieldPredicate(
            field="flow_code", operator="eq", value="X"
        )
        p3 = FieldPredicate(
            field="ref_year", operator="gt", value=2020
        )
        q = Query(dataset).filter((p1 & p2) | ~p3)
        r1 = q.execute()
        r2 = q.execute()
        assert r1.records == r2.records

    def test_query_reusable(self, dataset):
        q = Query(dataset).filter(reporter_code=699)
        # Execute twice — both should work.
        r1 = q.execute()
        r2 = q.execute()
        assert len(r1.records) == len(r2.records)


# ---------------------------------------------------------------------------
# TestQueryFilterCompositionEdgeCases
# ---------------------------------------------------------------------------


class TestQueryFilterCompositionEdgeCases:
    def test_empty_dataset_filter(self):
        ds = _make_dataset(())
        r = Query(ds).filter(reporter_code=699).execute()
        assert r.records == ()

    def test_filter_matching_nothing(self, dataset):
        r = (
            Query(dataset)
            .filter(reporter_code=999)
            .execute()
        )
        assert r.records == ()

    def test_filter_matching_everything(self, dataset):
        r = (
            Query(dataset)
            .filter(ref_year=2022)
            .exclude(ref_year=1999)
            .execute()
        )
        assert len(r.records) == 5  # 2022 records

    def test_multiple_filter_and_predicate_compose(self, dataset):
        # Multiple .filter() calls each
        # append, and an explicit predicate
        # also appends — all must match.
        # India 2022 X = 2 records
        # (124, 156 partners).
        result = (
            Query(dataset)
            .filter(reporter_code=699)        # kwargs
            .filter(flow_code="X")           # kwargs
            .filter(                         # explicit
                FieldPredicate(
                    field="ref_year",
                    operator="eq",
                    value=2022,
                )
            )
            .execute()
        )
        assert len(result.records) == 2

    def test_three_way_or(self, dataset):
        p1 = FieldPredicate(
            field="reporter_code", operator="eq", value=699
        )
        p2 = FieldPredicate(
            field="reporter_code", operator="eq", value=156
        )
        p3 = FieldPredicate(
            field="reporter_code", operator="eq", value=392
        )
        # 3-way OR via chaining.
        composed = p1 | p2 | p3
        kept = [
            r for r in dataset.records if composed(r)
        ]
        assert len(kept) == 7


# ---------------------------------------------------------------------------
# TestQueryContextWithPredicates
# ---------------------------------------------------------------------------


class TestQueryContextWithPredicates:
    def test_result_context_preserves_dataset(self, dataset):
        r = Query(dataset).filter(reporter_code=699).execute()
        assert r.context.dataset is dataset

    def test_result_records_is_tuple(self, dataset):
        r = Query(dataset).filter(reporter_code=699).execute()
        assert isinstance(r.records, tuple)

    def test_result_finished_at_after_started_at(self, dataset):
        r = Query(dataset).filter(reporter_code=699).execute()
        assert (
            r.context.started_at <= r.finished_at
        )

    def test_config_propagates_through_filter(self, dataset):
        q = (
            Query(dataset, config={"trace": True})
            .filter(reporter_code=699)
        )
        r = q.execute()
        assert r.context.config["trace"] is True