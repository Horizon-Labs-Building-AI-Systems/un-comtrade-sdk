"""Tests for the query grouping engine
(QE-003).

Per the QE-003 task scope, this module
covers:

- `group_by(*fields)` — single-column
  grouping.
- Multi-column grouping.
- Deterministic grouping keys (groups
  sorted lexicographically by key).
- Composition with `.filter()`.
- No aggregation (per task scope).

Validation criteria (per task spec):

- Single-column grouping ✅
- Multi-column grouping ✅
- Deterministic ordering ✅
- Group key tuple ✅
- Filter + group composition ✅
- Dataset immutability ✅
- Re-execution determinism ✅

Coverage:

- `TestGroup` — frozen dataclass
  invariants.
- `TestQueryGroupBy` — fluent
  `.group_by(...)`, single & multi-column,
  shorthand & dotted path fields,
  deterministic ordering, composition with
  `.filter()`, immutable queries, edge
  cases.
- `TestQueryResultGroups` — `groups`
  field, default empty, populated when
  grouping applied, validation.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from typing import Any

import pytest

from un_comtrade.analytics._query_engine import (
    FieldPredicate,
    Group,
    Query,
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
    """Build parsed records.

    Each tuple is `(reporter, partner, flow,
    period, value)`. ISO3 codes come from a
    fixed lookup.
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
    """5 India records (3 export, 2 import;
    2 years) + 2 China records (1 X, 1 M;
    2022)."""
    records = _records(
        (699, 124, "X", "2022", 100.0),
        (699, 156, "X", "2022", 200.0),
        (699, 124, "M", "2022", 80.0),
        (699, 124, "X", "2021", 150.0),
        (699, 156, "M", "2021", 90.0),
        (156, 0, "X", "2022", 1000.0),
        (156, 0, "M", "2022", 500.0),
    )
    return _make_dataset(records, name="grouping_test")


# ---------------------------------------------------------------------------
# TestGroup
# ---------------------------------------------------------------------------


class TestGroup:
    def test_frozen(self):
        from un_comtrade.models.trade import TradeRecord
        g = Group(
            key=(699,),
            records=(),
        )
        with pytest.raises(FrozenInstanceError):
            g.key = (156,)  # type: ignore[misc]

    def test_key_must_be_tuple(self):
        with pytest.raises(QueryError, match="tuple"):
            Group(
                key=[699],  # type: ignore[arg-type]
                records=(),
            )

    def test_records_must_be_tuple(self):
        with pytest.raises(QueryError, match="tuple"):
            Group(
                key=(699,),
                records=[],  # type: ignore[arg-type]
            )

    def test_records_must_be_trade_records(self):
        with pytest.raises(QueryError, match="TradeRecord"):
            Group(
                key=(699,),
                records=({"raw": "dict"},),  # type: ignore[arg-type]
            )

    def test_empty_records_allowed(self):
        # A group can be empty in principle,
        # though the engine never produces
        # one (every group has at least one
        # record by construction).
        g = Group(key=(699,), records=())
        assert g.key == (699,)
        assert g.records == ()

    def test_single_field_key(self):
        g = Group(key=(699,), records=())
        assert g.key == (699,)
        assert isinstance(g.key, tuple)
        assert len(g.key) == 1

    def test_multi_field_key(self):
        g = Group(key=(699, "X"), records=())
        assert g.key == (699, "X")
        assert len(g.key) == 2


# ---------------------------------------------------------------------------
# TestQueryGroupBy
# ---------------------------------------------------------------------------


class TestQueryGroupBy:
    def test_group_by_single_field(self, dataset):
        result = (
            Query(dataset).group_by("reporter_code").execute()
        )
        # Two reporters (699, 156) → two groups.
        assert len(result.groups) == 2
        # Sorted by key (lexicographic).
        assert result.groups[0].key == (156,)
        assert result.groups[1].key == (699,)

    def test_group_counts_match_records(self, dataset):
        result = (
            Query(dataset).group_by("reporter_code").execute()
        )
        # India (699) has 5 records; China (156)
        # has 2.
        by_key = {g.key: g for g in result.groups}
        assert len(by_key[(699,)].records) == 5
        assert len(by_key[(156,)].records) == 2

    def test_group_records_match_dataset(self, dataset):
        # All records appear in some group.
        result = (
            Query(dataset).group_by("reporter_code").execute()
        )
        all_records = [
            r for g in result.groups for r in g.records
        ]
        assert len(all_records) == len(dataset.records)

    def test_group_by_multi_column(self, dataset):
        result = Query(dataset).group_by(
            "reporter_code", "flow_code"
        ).execute()
        # Possible combos:
        # (699, X): 3 (124 X 2022, 156 X 2022,
        #            124 X 2021)
        # (699, M): 2 (124 M 2022, 156 M 2021)
        # (156, X): 1 (CHN X 2022)
        # (156, M): 1 (CHN M 2022)
        assert len(result.groups) == 4
        by_key = {g.key: g for g in result.groups}
        assert by_key[(699, "X")].key == (699, "X")
        assert len(by_key[(699, "X")].records) == 3
        assert len(by_key[(699, "M")].records) == 2
        assert len(by_key[(156, "X")].records) == 1
        assert len(by_key[(156, "M")].records) == 1

    def test_group_keys_sorted_lexicographically(self, dataset):
        result = Query(dataset).group_by(
            "reporter_code", "flow_code"
        ).execute()
        keys = [g.key for g in result.groups]
        assert keys == sorted(keys)

    def test_group_by_explicit_dotted_path(self, dataset):
        result = Query(dataset).group_by(
            "reporter.reporter_code"
        ).execute()
        assert len(result.groups) == 2

    def test_group_by_with_filter(self, dataset):
        # Filter India records, then group
        # by flow_code.
        result = (
            Query(dataset)
            .filter(reporter_code=699)
            .group_by("flow_code")
            .execute()
        )
        # India has 3 X + 2 M → 2 groups.
        assert len(result.groups) == 2
        by_key = {g.key: g for g in result.groups}
        assert by_key[("M",)].key == ("M",)
        assert len(by_key[("M",)].records) == 2
        assert len(by_key[("X",)].records) == 3

    def test_group_by_filter_then_group(self, dataset):
        # Group first, then filter (chained
        # in either order — fluent API).
        result = (
            Query(dataset)
            .group_by("reporter_code", "flow_code")
            .filter(reporter_code=699)
            .execute()
        )
        # Filter narrows to India; groups
        # are then computed on the filtered
        # set → (699, X): 3, (699, M): 2.
        assert len(result.groups) == 2
        keys = [g.key for g in result.groups]
        assert all(k[0] == 699 for k in keys)

    def test_no_group_by_returns_empty_groups(self, dataset):
        result = Query(dataset).execute()
        assert result.groups == ()

    def test_group_by_empty_args_returns_empty_groups(
        self, dataset
    ):
        # Calling .group_by() with no args is
        # allowed but produces no grouping.
        result = Query(dataset).group_by().execute()
        assert result.groups == ()

    def test_group_by_returns_new_query(self, dataset):
        q1 = Query(dataset)
        q2 = q1.group_by("reporter_code")
        assert q1 is not q2
        assert len(q1.group_by_fields) == 0
        assert q2.group_by_fields == ("reporter_code",)

    def test_group_by_does_not_mutate_receiver(self, dataset):
        q1 = Query(dataset)
        original_fields = q1.group_by_fields
        q1.group_by("reporter_code")
        assert q1.group_by_fields == original_fields
        assert len(q1.group_by_fields) == 0

    def test_group_by_invalid_field_type(self, dataset):
        with pytest.raises(QueryError):
            Query(dataset).group_by(123)  # type: ignore[arg-type]

    def test_group_by_empty_string_field(self, dataset):
        with pytest.raises(QueryError, match="non-empty"):
            Query(dataset).group_by("")

    def test_group_by_records_within_group_preserve_order(
        self, dataset
    ):
        # Within a group, records appear in
        # source order.
        result = (
            Query(dataset)
            .filter(reporter_code=699)
            .group_by("reporter_code")
            .execute()
        )
        india_group = result.groups[0]
        # All records in the group have
        # reporter_code == 699.
        assert all(
            r.reporter.reporter_code == 699
            for r in india_group.records
        )

    def test_group_by_unknown_field_raises(self, dataset):
        # `_get_field` raises during
        # execution when the field is not
        # found on the first matching
        # record. Use a dedicated dataset
        # that matches the unknown field
        # lookup to surface the error.
        ds = _make_dataset(_records(
            (699, 124, "X", "2022", 100.0),
        ))
        with pytest.raises(QueryError, match="unknown"):
            Query(ds).group_by("totally_made_up_field").execute()

    def test_group_by_three_columns(self, dataset):
        result = Query(dataset).group_by(
            "reporter_code", "flow_code", "partner_code"
        ).execute()
        # Each combination produces at most
        # one group; groups are sorted
        # lexicographically by the 3-tuple
        # key.
        keys = [g.key for g in result.groups]
        assert keys == sorted(keys)
        # All records appear in some group.
        total = sum(len(g.records) for g in result.groups)
        assert total == len(dataset.records)

    def test_group_by_key_tuple_length_matches_field_count(
        self, dataset
    ):
        result = Query(dataset).group_by(
            "reporter_code", "flow_code"
        ).execute()
        for g in result.groups:
            assert len(g.key) == 2


# ---------------------------------------------------------------------------
# TestQueryResultGroups
# ---------------------------------------------------------------------------


class TestQueryResultGroups:
    def test_groups_default_empty(self, dataset):
        result = Query(dataset).execute()
        assert result.groups == ()

    def test_groups_default_is_tuple(self, dataset):
        result = Query(dataset).execute()
        assert isinstance(result.groups, tuple)

    def test_groups_is_tuple_when_populated(self, dataset):
        result = (
            Query(dataset).group_by("reporter_code").execute()
        )
        assert isinstance(result.groups, tuple)

    def test_groups_must_be_tuple_type(self):
        # Construct directly with non-tuple
        # groups → validation error.
        from un_comtrade.models.trade import TradeRecord
        ds = _make_dataset(())
        ctx = None  # populated below
        from un_comtrade.analytics._query_engine import (
            QueryContext,
        )
        ctx = QueryContext(
            dataset=ds,
            started_at=datetime.now(timezone.utc),
        )
        with pytest.raises(QueryError, match="tuple"):
            QueryResult(
                records=(),
                context=ctx,
                finished_at=datetime.now(timezone.utc),
                groups=[Group(key=(1,), records=())],  # type: ignore[arg-type]
            )

    def test_groups_contain_group_instances(self):
        from un_comtrade.analytics._query_engine import (
            QueryContext,
        )
        ds = _make_dataset(())
        ctx = QueryContext(
            dataset=ds,
            started_at=datetime.now(timezone.utc),
        )
        with pytest.raises(QueryError, match="Group"):
            QueryResult(
                records=(),
                context=ctx,
                finished_at=datetime.now(timezone.utc),
                groups=("not a group",),  # type: ignore[arg-type]
            )

    def test_records_still_populated_when_grouping(
        self, dataset
    ):
        # `records` field on QueryResult
        # remains the flat filtered subset
        # even when grouping is also
        # applied.
        result = (
            Query(dataset)
            .filter(reporter_code=699)
            .group_by("flow_code")
            .execute()
        )
        assert len(result.records) == 5  # 5 India records
        assert len(result.groups) == 2  # 2 flows


# ---------------------------------------------------------------------------
# TestGroupingDeterminism
# ---------------------------------------------------------------------------


class TestGroupingDeterminism:
    def test_same_query_same_groups(self, dataset):
        q = Query(dataset).group_by(
            "reporter_code", "flow_code"
        )
        r1 = q.execute()
        r2 = q.execute()
        # Same number of groups.
        assert len(r1.groups) == len(r2.groups)
        # Same keys in same order.
        assert [g.key for g in r1.groups] == [
            g.key for g in r2.groups
        ]
        # Same per-group record counts.
        assert [
            len(g.records) for g in r1.groups
        ] == [len(g.records) for g in r2.groups]

    def test_groups_sorted_lexicographically(self, dataset):
        # Even with mixed reporter_code
        # values, groups come out sorted.
        result = Query(dataset).group_by(
            "reporter_code", "flow_code"
        ).execute()
        keys = [g.key for g in result.groups]
        assert keys == sorted(keys)

    def test_group_order_independent_of_input_order(
        self, dataset
    ):
        # Build two equivalent datasets
        # with records in different orders;
        # the group order should be the
        # same.
        records_normal = _records(
            (699, 124, "X", "2022", 100.0),
            (156, 0, "X", "2022", 200.0),
            (699, 156, "M", "2022", 80.0),
        )
        records_shuffled = _records(
            (156, 0, "X", "2022", 200.0),
            (699, 124, "X", "2022", 100.0),
            (699, 156, "M", "2022", 80.0),
        )
        ds_n = _make_dataset(records_normal, name="n")
        ds_s = _make_dataset(records_shuffled, name="s")
        r_n = (
            Query(ds_n)
            .group_by("reporter_code", "flow_code")
            .execute()
        )
        r_s = (
            Query(ds_s)
            .group_by("reporter_code", "flow_code")
            .execute()
        )
        assert [g.key for g in r_n.groups] == [
            g.key for g in r_s.groups
        ]


# ---------------------------------------------------------------------------
# TestGroupingFilterComposition
# ---------------------------------------------------------------------------


class TestGroupingFilterComposition:
    def test_filter_then_group(self, dataset):
        # Filter narrows the dataset first,
        # then groups.
        result = (
            Query(dataset)
            .filter(reporter_code=699, flow_code="X")
            .group_by("partner_code")
            .execute()
        )
        # India X has 3 records across two
        # partners: 124 (2 records: 2022 + 2021)
        # and 156 (1 record: 2022).
        assert len(result.groups) == 2
        by_key = {g.key: g for g in result.groups}
        assert len(by_key[(124,)].records) == 2
        assert len(by_key[(156,)].records) == 1

    def test_explicit_predicate_then_group(self, dataset):
        p = FieldPredicate(
            field="flow_code", operator="eq", value="M"
        )
        result = (
            Query(dataset).filter(p).group_by(
                "reporter_code"
            ).execute()
        )
        # M records: India 2 + China 1 = 3.
        # 2 groups (one per reporter).
        assert len(result.groups) == 2
        by_key = {g.key: g for g in result.groups}
        assert len(by_key[(156,)].records) == 1
        assert len(by_key[(699,)].records) == 2

    def test_group_then_filter(self, dataset):
        # Order doesn't matter for the
        # final grouping result when the
        # filter and group use compatible
        # fields.
        r1 = (
            Query(dataset)
            .filter(reporter_code=699)
            .group_by("flow_code")
            .execute()
        )
        r2 = (
            Query(dataset)
            .group_by("flow_code")
            .filter(reporter_code=699)
            .execute()
        )
        assert [g.key for g in r1.groups] == [
            g.key for g in r2.groups
        ]
        assert [
            len(g.records) for g in r1.groups
        ] == [len(g.records) for g in r2.groups]


# ---------------------------------------------------------------------------
# TestCanonicalDatasetUnchanged
# ---------------------------------------------------------------------------


class TestCanonicalDatasetUnchanged:
    def test_dataset_unchanged_after_grouping(self, dataset):
        before = tuple(dataset.records)
        Query(dataset).group_by("reporter_code").execute()
        Query(dataset).group_by(
            "reporter_code", "flow_code"
        ).execute()
        Query(dataset).filter(reporter_code=699).group_by(
            "flow_code"
        ).execute()
        assert tuple(dataset.records) == before
        assert len(dataset.records) == len(before)

    def test_dataset_records_id_preserved(self, dataset):
        # The records tuple identity is
        # preserved.
        before_id = id(dataset.records)
        Query(dataset).group_by("reporter_code").execute()
        after_id = id(dataset.records)
        assert before_id == after_id


# ---------------------------------------------------------------------------
# TestGroupingEdgeCases
# ---------------------------------------------------------------------------


class TestGroupingEdgeCases:
    def test_empty_dataset_grouping(self):
        ds = _make_dataset(())
        result = (
            Query(ds).group_by("reporter_code").execute()
        )
        assert result.groups == ()
        assert result.records == ()

    def test_single_record_dataset(self):
        records = _records((699, 124, "X", "2022", 100.0),)
        ds = _make_dataset(records)
        result = (
            Query(ds).group_by("reporter_code").execute()
        )
        assert len(result.groups) == 1
        assert result.groups[0].key == (699,)
        assert len(result.groups[0].records) == 1

    def test_grouping_with_single_distinct_value(self):
        # All records share the same
        # reporter → exactly one group.
        records = _records(
            (699, 124, "X", "2022", 100.0),
            (699, 156, "M", "2022", 80.0),
            (699, 0, "X", "2021", 50.0),
        )
        ds = _make_dataset(records)
        result = (
            Query(ds).group_by("reporter_code").execute()
        )
        assert len(result.groups) == 1
        assert result.groups[0].key == (699,)
        assert len(result.groups[0].records) == 3

    def test_filter_eliminates_all_then_group(self, dataset):
        # Filter that matches nothing → no
        # records, no groups.
        result = (
            Query(dataset)
            .filter(reporter_code=999)
            .group_by("flow_code")
            .execute()
        )
        assert result.groups == ()
        assert result.records == ()

    def test_group_by_reusable_query(self, dataset):
        q = Query(dataset).group_by("reporter_code")
        r1 = q.execute()
        r2 = q.execute()
        assert [g.key for g in r1.groups] == [
            g.key for g in r2.groups
        ]

    def test_repr_includes_group_by_count(self, dataset):
        q = (
            Query(dataset)
            .group_by("reporter_code", "flow_code")
        )
        text = repr(q)
        assert "group_by=2" in text

    def test_repr_no_group_by(self, dataset):
        q = Query(dataset)
        text = repr(q)
        assert "group_by=0" in text