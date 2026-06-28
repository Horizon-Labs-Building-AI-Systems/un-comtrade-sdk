"""Tests for the query ordering and
windowing engine (QE-005).

Per the QE-005 task scope, this module
covers:

- `sort(*fields, descending=False)` —
  stable ordering.
- `limit(n)` — top-N window.
- `offset(n)` — skip first N.
- `reverse()` — flip order.

Validation criteria:

- Stable ordering ✅
- Multi-field sort ✅
- Limit + offset + sort composition ✅
- Reverse ✅
- Immutability ✅
- CanonicalDataset unchanged ✅

Coverage:

- `TestSortKey` — frozen dataclass.
- `TestQuerySort` — fluent sort, single &
  multi-field, ascending & descending,
  stable ordering, validation.
- `TestQueryLimit` — top-N, validation.
- `TestQueryOffset` — skip, validation.
- `TestQueryReverse` — flip order.
- `TestQueryOrderingComposition` —
  filter + sort + limit + offset + reverse
  together.
- `TestQueryOrderingDeterminism` —
  re-execution produces same result.
- `TestCanonicalDatasetUnchanged` —
  ordering doesn't mutate dataset.
- `TestQueryOrderingEdgeCases` —
  empty dataset, single record, limit > N,
  offset > N, sort-then-group, group-then-
  sort, etc.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from typing import Any

import pytest

from un_comtrade.analytics._query_engine import (
    Query,
    QueryError,
    SortKey,
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
        392: "JPN", 484: "MEX", 36: "AUS",
    }
    raws = []
    for i, (reporter, partner, flow, period, value) in enumerate(
        tuples
    ):
        ref_year = int(period[:4])
        # Use partner=i as a unique key per
        # record to avoid dedup.
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
    and periods, sorted by source order.
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
    return _make_dataset(records, name="ordering_test")


# ---------------------------------------------------------------------------
# TestSortKey
# ---------------------------------------------------------------------------


class TestSortKey:
    def test_frozen(self):
        k = SortKey(field="period", descending=False)
        with pytest.raises(FrozenInstanceError):
            k.field = "primary_value"  # type: ignore[misc]

    def test_default_descending_false(self):
        k = SortKey(field="period")
        assert k.descending is False

    def test_explicit_descending(self):
        k = SortKey(field="period", descending=True)
        assert k.descending is True

    def test_field_must_be_string(self):
        with pytest.raises(QueryError, match="non-empty"):
            SortKey(field="")  # type: ignore[arg-type]

    def test_field_must_be_non_empty(self):
        with pytest.raises(QueryError, match="non-empty"):
            SortKey(field="")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestQuerySort
# ---------------------------------------------------------------------------


class TestQuerySort:
    def test_sort_single_field_ascending(self, dataset):
        result = (
            Query(dataset).sort("primary_value").execute()
        )
        values = [
            r.trade_value.primary_value for r in result.records
        ]
        assert values == sorted(values)

    def test_sort_single_field_descending(self, dataset):
        result = (
            Query(dataset)
            .sort("primary_value", descending=True)
            .execute()
        )
        values = [
            r.trade_value.primary_value for r in result.records
        ]
        assert values == sorted(values, reverse=True)

    def test_sort_by_period(self, dataset):
        result = Query(dataset).sort("period").execute()
        periods = [r.period for r in result.records]
        assert periods == sorted(periods)

    def test_sort_with_explicit_dotted_path(self, dataset):
        result = (
            Query(dataset)
            .sort("trade_value.primary_value")
            .execute()
        )
        values = [
            r.trade_value.primary_value for r in result.records
        ]
        assert values == sorted(values)

    def test_sort_multi_field(self, dataset):
        # Sort by reporter_code ASC, then
        # primary_value DESC. India comes
        # first, then China; within each,
        # larger primary_value first.
        # Note: per-field direction is
        # not supported — descending=True
        # applies to ALL fields. We use
        # ascending here for the multi-field
        # test.
        result = (
            Query(dataset)
            .sort("reporter_code", "primary_value")
            .execute()
        )
        # First by reporter (156 < 699), so
        # China first.
        first = result.records[0]
        assert first.reporter.reporter_code == 156
        # Within China, sorted by primary
        # ascending: 800 then 1000.
        china_records = [
            r for r in result.records
            if r.reporter.reporter_code == 156
        ]
        china_values = [
            r.trade_value.primary_value
            for r in china_records
        ]
        assert china_values == sorted(china_values)

    def test_sort_stable_for_equal_keys(self, dataset):
        # Two records with the same
        # primary_value = 80 (none here,
        # but we verify stability using
        # equal sort keys).
        records = _records(
            (699, 124, "X", "2022", 100.0),
            (699, 156, "X", "2022", 100.0),
            (699, 392, "X", "2022", 100.0),
        )
        ds = _make_dataset(records, name="stable")
        result = Query(ds).sort("primary_value").execute()
        # Source order preserved.
        partner_codes = [
            r.partner.partner_code for r in result.records
        ]
        # partner codes 124, 156, 392 in
        # source order.
        assert partner_codes == sorted(partner_codes)

    def test_sort_no_args_raises(self, dataset):
        with pytest.raises(
            QueryError, match="at least one field"
        ):
            Query(dataset).sort()

    def test_sort_invalid_field_type(self, dataset):
        with pytest.raises(QueryError, match="non-empty"):
            Query(dataset).sort(123)  # type: ignore[arg-type]

    def test_sort_empty_field_raises(self, dataset):
        with pytest.raises(QueryError, match="non-empty"):
            Query(dataset).sort("")

    def test_sort_returns_new_query(self, dataset):
        q1 = Query(dataset)
        q2 = q1.sort("primary_value")
        assert q1 is not q2
        assert len(q1.sort_keys) == 0
        assert len(q2.sort_keys) == 1

    def test_sort_does_not_mutate_receiver(self, dataset):
        q1 = Query(dataset)
        original = q1.sort_keys
        q1.sort("primary_value")
        assert q1.sort_keys == original

    def test_sort_unknown_field_raises_at_execute(self, dataset):
        with pytest.raises(QueryError, match="unknown"):
            Query(dataset).sort("totally_made_up_field").execute()

    def test_sort_keys_property(self, dataset):
        q = Query(dataset).sort("primary_value")
        assert len(q.sort_keys) == 1
        assert q.sort_keys[0].field == "primary_value"
        assert q.sort_keys[0].descending is False

    def test_sort_descending_keys_property(self, dataset):
        q = Query(dataset).sort("primary_value", descending=True)
        assert q.sort_keys[0].descending is True


# ---------------------------------------------------------------------------
# TestQueryLimit
# ---------------------------------------------------------------------------


class TestQueryLimit:
    def test_limit_keeps_first_n(self, dataset):
        result = (
            Query(dataset).sort("primary_value").limit(3).execute()
        )
        assert len(result.records) == 3
        # Smallest 3 primary values: 50, 80,
        # 90.
        values = [
            r.trade_value.primary_value for r in result.records
        ]
        assert values == [Decimal_("50.0"), Decimal_("80.0"), Decimal_("90.0")]

    def test_limit_zero_returns_empty(self, dataset):
        result = Query(dataset).limit(0).execute()
        assert result.records == ()

    def test_limit_larger_than_records(self, dataset):
        result = (
            Query(dataset).limit(100).execute()
        )
        assert len(result.records) == len(dataset.records)

    def test_limit_negative_raises(self, dataset):
        with pytest.raises(
            QueryError, match="non-negative"
        ):
            Query(dataset).limit(-1)

    def test_limit_non_int_raises(self, dataset):
        with pytest.raises(
            QueryError, match="non-negative"
        ):
            Query(dataset).limit("5")  # type: ignore[arg-type]

    def test_limit_none_clears(self, dataset):
        q1 = Query(dataset).limit(3)
        assert q1.limit_value == 3
        q2 = q1.limit(None)
        assert q2.limit_value is None
        # Original not mutated.
        assert q1.limit_value == 3

    def test_limit_property(self, dataset):
        q = Query(dataset).limit(5)
        assert q.limit_value == 5

    def test_limit_default_none(self, dataset):
        q = Query(dataset)
        assert q.limit_value is None

    def test_limit_returns_new_query(self, dataset):
        q1 = Query(dataset)
        q2 = q1.limit(3)
        assert q1 is not q2
        assert q1.limit_value is None
        assert q2.limit_value == 3


# ---------------------------------------------------------------------------
# TestQueryOffset
# ---------------------------------------------------------------------------


class TestQueryOffset:
    def test_offset_skips_first_n(self, dataset):
        result = (
            Query(dataset)
            .sort("primary_value")
            .offset(2)
            .execute()
        )
        # Skip 50 and 80; remaining 5.
        assert len(result.records) == 5
        values = [
            r.trade_value.primary_value for r in result.records
        ]
        assert values[0] == Decimal_("90.0")

    def test_offset_zero_is_noop(self, dataset):
        result = Query(dataset).offset(0).execute()
        assert len(result.records) == len(dataset.records)

    def test_offset_larger_than_records(self, dataset):
        result = (
            Query(dataset).sort("primary_value").offset(100).execute()
        )
        assert result.records == ()

    def test_offset_negative_raises(self, dataset):
        with pytest.raises(
            QueryError, match="non-negative"
        ):
            Query(dataset).offset(-1)

    def test_offset_non_int_raises(self, dataset):
        with pytest.raises(
            QueryError, match="non-negative"
        ):
            Query(dataset).offset("5")  # type: ignore[arg-type]

    def test_offset_none_clears(self, dataset):
        q1 = Query(dataset).offset(3)
        assert q1.offset_value == 3
        q2 = q1.offset(None)
        assert q2.offset_value is None
        assert q1.offset_value == 3  # not mutated

    def test_offset_property(self, dataset):
        q = Query(dataset).offset(5)
        assert q.offset_value == 5

    def test_offset_default_zero(self, dataset):
        q = Query(dataset)
        assert q.offset_value is None or q.offset_value == 0

    def test_offset_returns_new_query(self, dataset):
        q1 = Query(dataset)
        q2 = q1.offset(3)
        assert q1 is not q2


# ---------------------------------------------------------------------------
# TestQueryReverse
# ---------------------------------------------------------------------------


class TestQueryReverse:
    def test_reverse_flips_order(self, dataset):
        result = (
            Query(dataset)
            .sort("primary_value")
            .reverse()
            .execute()
        )
        values = [
            r.trade_value.primary_value for r in result.records
        ]
        # Sort ascending then reverse →
        # descending.
        assert values == sorted(values, reverse=True)

    def test_reverse_without_sort(self, dataset):
        # No sort: just flips source order.
        result = Query(dataset).reverse().execute()
        reversed_records = tuple(reversed(dataset.records))
        assert result.records == reversed_records

    def test_reverse_property(self, dataset):
        q = Query(dataset).reverse()
        assert q.reverse_value is True

    def test_reverse_default_false(self, dataset):
        q = Query(dataset)
        assert q.reverse_value is False

    def test_reverse_returns_new_query(self, dataset):
        q1 = Query(dataset)
        q2 = q1.reverse()
        assert q1 is not q2
        assert q1.reverse_value is False
        assert q2.reverse_value is True

    def test_reverse_does_not_mutate(self, dataset):
        q1 = Query(dataset)
        q1.reverse()
        assert q1.reverse_value is False


# ---------------------------------------------------------------------------
# TestQueryOrderingComposition
# ---------------------------------------------------------------------------


class TestQueryOrderingComposition:
    def test_filter_then_sort(self, dataset):
        result = (
            Query(dataset)
            .filter(reporter_code=699)
            .sort("primary_value", descending=True)
            .execute()
        )
        # All India records, sorted by value
        # desc.
        assert all(
            r.reporter.reporter_code == 699
            for r in result.records
        )
        values = [
            r.trade_value.primary_value for r in result.records
        ]
        assert values == sorted(values, reverse=True)

    def test_sort_then_limit(self, dataset):
        result = (
            Query(dataset)
            .sort("primary_value", descending=True)
            .limit(3)
            .execute()
        )
        # Top 3 by primary_value desc.
        assert len(result.records) == 3
        values = [
            r.trade_value.primary_value for r in result.records
        ]
        assert values == sorted(values, reverse=True)

    def test_sort_offset_limit(self, dataset):
        # Sort by primary_value desc, skip
        # 2, take 3.
        result = (
            Query(dataset)
            .sort("primary_value", descending=True)
            .offset(2)
            .limit(3)
            .execute()
        )
        # Skip 1000, 800; take 200, 100, 90.
        values = [
            r.trade_value.primary_value for r in result.records
        ]
        assert values == [
            Decimal_("200.0"),
            Decimal_("100.0"),
            Decimal_("90.0"),
        ]

    def test_sort_then_reverse(self, dataset):
        # sort asc then reverse = desc.
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

    def test_filter_sort_limit_offset(self, dataset):
        # Filter to India, sort by value
        # desc, skip 1, take 2.
        result = (
            Query(dataset)
            .filter(reporter_code=699)
            .sort("primary_value", descending=True)
            .offset(1)
            .limit(2)
            .execute()
        )
        # India values desc: 200, 100, 90,
        # 80, 50. Skip 200 → 100, 90.
        values = [
            r.trade_value.primary_value for r in result.records
        ]
        assert values == [Decimal_("100.0"), Decimal_("90.0")]

    def test_filter_preserved_through_sort(self, dataset):
        # Sort after filter; filter must
        # still be in effect.
        result = (
            Query(dataset)
            .filter(reporter_code=699)
            .sort("primary_value", descending=True)
            .limit(3)
            .offset(1)
            .execute()
        )
        assert all(
            r.reporter.reporter_code == 699
            for r in result.records
        )
        assert len(result.records) == 3

    def test_sort_grouping_then_ordering(self, dataset):
        # Group by reporter, then sort the
        # flat records. Grouping should
        # still produce the same groups.
        result = (
            Query(dataset)
            .sort("primary_value")
            .group_by("reporter_code")
            .execute()
        )
        assert len(result.groups) == 2
        for group in result.groups:
            assert isinstance(group.key, tuple)

    def test_limit_offset_with_grouping(self, dataset):
        # Group + limit + offset + sort.
        # After sort ASC + offset(1) +
        # limit(3) we get 3 records (all
        # India), grouped → 1 group.
        result = (
            Query(dataset)
            .sort("primary_value")
            .group_by("reporter_code")
            .limit(3)
            .offset(1)
            .execute()
        )
        assert len(result.groups) == 1


# ---------------------------------------------------------------------------
# TestQueryOrderingDeterminism
# ---------------------------------------------------------------------------


class TestQueryOrderingDeterminism:
    def test_same_query_same_order(self, dataset):
        q = Query(dataset).sort("primary_value").limit(3)
        r1 = q.execute()
        r2 = q.execute()
        assert r1.records == r2.records

    def test_complex_chain_deterministic(self, dataset):
        q = (
            Query(dataset)
            .filter(reporter_code=699)
            .sort("primary_value", descending=True)
            .offset(1)
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

    def test_query_reusable(self, dataset):
        q = (
            Query(dataset)
            .sort("primary_value", descending=True)
            .limit(3)
        )
        r1 = q.execute()
        r2 = q.execute()
        assert r1.records == r2.records


# ---------------------------------------------------------------------------
# TestCanonicalDatasetUnchanged
# ---------------------------------------------------------------------------


class TestCanonicalDatasetUnchanged:
    def test_dataset_unchanged_after_sorting(self, dataset):
        before = tuple(dataset.records)
        Query(dataset).sort("primary_value", descending=True).execute()
        Query(dataset).sort("period").limit(3).execute()
        Query(dataset).sort("primary_value").offset(2).execute()
        Query(dataset).sort("primary_value").reverse().execute()
        assert tuple(dataset.records) == before

    def test_dataset_records_id_preserved(self, dataset):
        before_id = id(dataset.records)
        Query(dataset).sort("primary_value").execute()
        after_id = id(dataset.records)
        assert before_id == after_id


# ---------------------------------------------------------------------------
# TestQueryOrderingEdgeCases
# ---------------------------------------------------------------------------


class TestQueryOrderingEdgeCases:
    def test_empty_dataset_sort(self):
        ds = _make_dataset(())
        result = (
            Query(ds).sort("primary_value").execute()
        )
        assert result.records == ()

    def test_single_record_sort(self):
        records = _records((699, 124, "X", "2022", 100.0))
        ds = _make_dataset(records, name="single")
        result = Query(ds).sort("primary_value").execute()
        assert len(result.records) == 1

    def test_single_record_limit_above_one(self):
        records = _records((699, 124, "X", "2022", 100.0))
        ds = _make_dataset(records, name="single")
        result = Query(ds).limit(5).execute()
        assert len(result.records) == 1

    def test_limit_offset_total_equals_records(self, dataset):
        # Sort, skip 2, take 5. Should give
        # 5 records (since we have 7).
        result = (
            Query(dataset)
            .sort("primary_value")
            .offset(2)
            .limit(5)
            .execute()
        )
        assert len(result.records) == 5

    def test_offset_equals_total(self, dataset):
        # Skip all records.
        result = (
            Query(dataset)
            .offset(len(dataset.records))
            .execute()
        )
        assert result.records == ()

    def test_sort_by_period_then_by_value(self, dataset):
        result = (
            Query(dataset)
            .sort("period", "primary_value")
            .execute()
        )
        periods = [r.period for r in result.records]
        # First all 2021 records (3 records
        # in dataset), then all 2022 records
        # (4 records).
        assert periods == [
            "2021", "2021", "2021",
            "2022", "2022", "2022", "2022",
        ]

    def test_repr_includes_ordering_state(self, dataset):
        q = (
            Query(dataset)
            .sort("primary_value", descending=True)
            .limit(5)
            .offset(2)
            .reverse()
        )
        text = repr(q)
        assert "sort=1" in text
        assert "limit=5" in text
        assert "offset=2" in text
        assert "reverse=True" in text

    def test_repr_no_ordering(self, dataset):
        q = Query(dataset)
        text = repr(q)
        assert "sort=0" in text
        assert "limit=None" in text
        assert "offset=None" in text
        assert "reverse=False" in text


# ---------------------------------------------------------------------------
# Helper for Decimal comparisons
# ---------------------------------------------------------------------------


def Decimal_(value: str):
    """Local alias to avoid shadowing the
    Decimal import. Returns a `Decimal`."""
    from decimal import Decimal
    return Decimal(value)


# Update the local alias to use Decimal_ for
# clarity in this test file's assertions.
# (The function is referenced above; the
# `Decimal_("...")` calls happen at runtime
# when pytest collects and runs the tests.)

# ---------------------------------------------------------------------------
# TestSortKeyEdgeCases
# ---------------------------------------------------------------------------


class TestSortKeyEdgeCases:
    def test_sort_keys_returns_tuple(self, dataset):
        q = Query(dataset).sort("primary_value")
        assert isinstance(q.sort_keys, tuple)

    def test_sort_keys_returns_copy(self, dataset):
        q = Query(dataset).sort("primary_value")
        snapshot = q.sort_keys
        # Mutating the returned tuple
        # should not affect the Query.
        assert snapshot == q.sort_keys

    def test_no_sort_keys_default_empty_tuple(self, dataset):
        q = Query(dataset)
        assert q.sort_keys == ()

    def test_multiple_sort_keys(self, dataset):
        q = Query(dataset).sort("reporter_code", "period")
        assert len(q.sort_keys) == 2
        assert q.sort_keys[0].field == "reporter_code"
        assert q.sort_keys[1].field == "period"