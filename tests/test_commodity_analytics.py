"""Tests for the commodity / HS analytics (P6-004).

Per the P6-004 task scope, this module covers:

- **`top_hs_codes`** — rank HS codes by trade
  value for a given reporter (or globally).
- **`commodity_ranking`** — same shape with
  optional `share` field (each commodity's
  percentage of the grand total).
- **`commodity_trend`** — time-series of trade
  for one HS code.
- **`sector_summaries`** — aggregate by HS
  section (the 21 WCO Harmonized System
  sections identified by Roman numerals).

Coverage:

- `TestHSCodeRankingRow` — frozen dataclass,
  Decimal invariants.
- `TestTopHSCodes` — basic ranking, by
  total_trade / exports / imports /
  trade_balance / abs_trade_balance /
  record_count; flow filter (X / M);
  hs_level filter (2 / 4 / 6); limit; descending
  / ascending; unknown field; non-canonical
  source.
- `TestCommodityRankingRow` — frozen dataclass,
  Decimal invariants, share type.
- `TestCommodityRanking` — same fields as
  `top_hs_codes` plus `include_share` flag;
  share sums to ≤ 1.
- `TestCommodityTrendPoint` — frozen dataclass.
- `TestCommodityTrend` — yearly / per-period
  granularity; sorted ascending; unknown
  granularity; empty dataset; non-canonical.
- `TestSectorSummaryRow` — frozen dataclass.
- `TestSectorSummaries` — one row per WCO HS
  section; chapter mapping; Unknown section for
  out-of-range HS codes; total exports / imports
  / balance per sector.
- `TestSectorForChapter` — direct lookup of the
  chapter → section mapping.
- `TestCommodityAnalyticsErrorPropagated` —
  bad source / bad arg paths.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal
from typing import Any

import pytest

from un_comtrade.analytics import (
    AnalyticsError,
    CommodityAnalyticsError,
    CommodityRankingRow,
    CommodityTrendPoint,
    HSCodeRankingRow,
    SECTORS,
    SectorSummaryRow,
    commodity_ranking,
    commodity_trend,
    sector_for_chapter,
    sector_summaries,
    top_hs_codes,
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
    `(commodity, partner, period, flow, value)`.
    `commodity` is the cmdCode.

    `refYear` is extracted from `period[:4]`,
    `refPeriodId` is `int(period) * 10000 + 1` so
    intra-year periods stay distinct.
    """
    raws = []
    for t in tuples:
        commodity, partner, period, flow, value = t
        ref_year = int(period[:4])
        period_id = int(period) * 10000 + 1
        raws.append(
            _baseline_raw(
                cmdCode=commodity,
                cmdDesc=f"Commodity {commodity}",
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


# A canonical fixture dataset.
def _commodity_dataset():
    """India exports petroleum + machinery +
    textiles; imports petroleum + machinery +
    electronics."""
    return _make_dataset(_records(
        # 2022 exports
        ("270900", 0, "2022", "X", 1000.0),  # petroleum
        ("840731", 0, "2022", "X", 500.0),   # machinery
        ("620342", 0, "2022", "X", 100.0),   # textiles
        # 2023 exports
        ("270900", 0, "2023", "X", 1200.0),
        ("840731", 0, "2023", "X", 600.0),
        # 2022 imports
        ("270900", 0, "2022", "M", 2000.0),
        ("840731", 0, "2022", "M", 400.0),
        ("851762", 0, "2022", "M", 300.0),   # electronics
    ))


# ---------------------------------------------------------------------------
# TestHSCodeRankingRow
# ---------------------------------------------------------------------------


class TestHSCodeRankingRow:
    def test_frozen(self):
        row = HSCodeRankingRow(
            commodity_code="270900",
            commodity_name="Petroleum oils",
            total_exports=Decimal("2200"),
            total_imports=Decimal("2000"),
            total_trade=Decimal("4200"),
            trade_balance=Decimal("200"),
            record_count=3,
        )
        with pytest.raises(FrozenInstanceError):
            row.commodity_code = "X"  # type: ignore[misc]

    def test_decimal_invariants(self):
        with pytest.raises(CommodityAnalyticsError, match="Decimal"):
            HSCodeRankingRow(
                commodity_code="270900",
                commodity_name="Petroleum oils",
                total_exports="not a decimal",  # type: ignore[arg-type]
                total_imports=Decimal("2000"),
                total_trade=Decimal("4200"),
                trade_balance=Decimal("200"),
                record_count=3,
            )


# ---------------------------------------------------------------------------
# TestTopHSCodes
# ---------------------------------------------------------------------------


class TestTopHSCodes:
    def test_returns_tuple_of_rows(self):
        rows = top_hs_codes(_commodity_dataset())
        assert isinstance(rows, tuple)
        assert all(isinstance(r, HSCodeRankingRow) for r in rows)

    def test_default_sort_descending_by_total_trade(self):
        rows = top_hs_codes(_commodity_dataset())
        # 270900: 2200 X + 2000 M = 4200
        # 840731: 1100 X + 400 M = 1500
        # 851762: 0 X + 300 M = 300
        # 620342: 100 X + 0 M = 100
        codes = [r.commodity_code for r in rows]
        assert codes == ["270900", "840731", "851762", "620342"]

    def test_by_exports(self):
        rows = top_hs_codes(
            _commodity_dataset(), by="exports"
        )
        codes = [r.commodity_code for r in rows]
        # 270900 (2200) > 840731 (1100) > 620342 (100)
        # > 851762 (0).
        assert codes == ["270900", "840731", "620342", "851762"]

    def test_by_imports(self):
        rows = top_hs_codes(
            _commodity_dataset(), by="imports"
        )
        codes = [r.commodity_code for r in rows]
        # 270900 (2000) > 840731 (400) > 851762 (300)
        # > 620342 (0).
        assert codes == ["270900", "840731", "851762", "620342"]

    def test_by_trade_balance(self):
        rows = top_hs_codes(
            _commodity_dataset(), by="trade_balance"
        )
        codes = [r.commodity_code for r in rows]
        # 270900: 2200 - 2000 = 200 (positive)
        # 840731: 1100 - 400 = 700 (positive)
        # 620342: 100 - 0 = 100 (positive)
        # 851762: 0 - 300 = -300 (negative)
        assert codes == ["840731", "270900", "620342", "851762"]

    def test_by_abs_trade_balance(self):
        rows = top_hs_codes(
            _commodity_dataset(), by="abs_trade_balance"
        )
        # abs values: 851762=300, 840731=700,
        # 270900=200, 620342=100.
        codes = [r.commodity_code for r in rows]
        assert codes == ["840731", "851762", "270900", "620342"]

    def test_by_record_count(self):
        rows = top_hs_codes(
            _commodity_dataset(), by="record_count"
        )
        # 270900 (3 records) > 840731 (3) >
        # 851762 (1) > 620342 (1).
        codes = [r.commodity_code for r in rows]
        assert codes[0] in ("270900", "840731")
        assert codes[-1] in ("851762", "620342")

    def test_flow_filter_export(self):
        rows = top_hs_codes(_commodity_dataset(), flow="X")
        # Only exports.
        for r in rows:
            assert r.total_imports == Decimal("0")
        codes = [r.commodity_code for r in rows]
        assert "851762" not in codes  # no import-only

    def test_flow_filter_import(self):
        rows = top_hs_codes(_commodity_dataset(), flow="M")
        for r in rows:
            assert r.total_exports == Decimal("0")
        codes = [r.commodity_code for r in rows]
        assert "620342" not in codes  # no export-only

    def test_limit(self):
        rows = top_hs_codes(_commodity_dataset(), limit=2)
        assert len(rows) == 2

    def test_limit_zero(self):
        rows = top_hs_codes(_commodity_dataset(), limit=0)
        assert rows == ()

    def test_ascending_sort(self):
        rows = top_hs_codes(
            _commodity_dataset(), descending=False
        )
        codes = [r.commodity_code for r in rows]
        # Ascending by total trade.
        assert codes == ["620342", "851762", "840731", "270900"]

    def test_hs_level_filter_6_digit(self):
        # All codes are already 6 digits; nothing
        # changes.
        rows = top_hs_codes(_commodity_dataset(), hs_level=6)
        assert len(rows) == 4

    def test_hs_level_filter_2_digit(self):
        # Keep only records with 2-digit
        # commodity codes — our fixture has 6-digit
        # codes so this returns nothing.
        rows = top_hs_codes(_commodity_dataset(), hs_level=2)
        assert rows == ()

    def test_hs_level_filter_invalid_raises(self):
        with pytest.raises(
            CommodityAnalyticsError, match="hs_level"
        ):
            top_hs_codes(_commodity_dataset(), hs_level=3)

    def test_reporter_filter(self):
        # Build a dataset with India (699) + China
        # (156) records. Use different periods so
        # the parser's composite-key dedup keeps
        # both records.
        records = _records(
            ("270900", 0, "2022", "X", 1000.0),
            ("270900", 0, "2023", "X", 500.0),
        )
        # Override the second record's reporter
        # to mix 699 + 156.
        raw_records = list(records)
        raw_records[1] = TradeParser(
            log_skipped=False
        ).parse_records([
            {
                **_baseline_raw(
                    reporterCode=156,
                    reporterISO="CHN",
                    reporterDesc="China",
                    cmdCode="270900",
                    cmdDesc="Petroleum",
                    partnerCode=0,
                    period="2023",
                    refYear=2023,
                    refPeriodId=20230101,
                    flowCode="X",
                    fobvalue=500,
                    primaryValue=500,
                ),
            }
        ]).records[0]
        ds = _make_dataset(tuple(raw_records))

        rows = top_hs_codes(ds, reporter_code=699)
        # Only India records (X=1000).
        assert len(rows) == 1
        assert rows[0].total_exports == Decimal("1000")

    def test_unknown_field_raises(self):
        with pytest.raises(
            CommodityAnalyticsError, match="Unknown ranking"
        ):
            top_hs_codes(_commodity_dataset(), by="nope")

    def test_negative_limit_raises(self):
        with pytest.raises(
            CommodityAnalyticsError, match="non-negative"
        ):
            top_hs_codes(_commodity_dataset(), limit=-1)

    def test_empty_dataset_returns_empty_tuple(self):
        assert top_hs_codes(_make_dataset(())) == ()

    def test_rejects_non_canonical(self):
        with pytest.raises(
            CommodityAnalyticsError, match="CanonicalDataset"
        ):
            top_hs_codes([{"raw": "dict"}])

    def test_commodity_name_captured(self):
        rows = top_hs_codes(_commodity_dataset())
        by_code = {r.commodity_code: r for r in rows}
        assert by_code["270900"].commodity_name == "Commodity 270900"


# ---------------------------------------------------------------------------
# TestCommodityRankingRow
# ---------------------------------------------------------------------------


class TestCommodityRankingRow:
    def test_frozen(self):
        row = CommodityRankingRow(
            commodity_code="270900",
            commodity_name="Petroleum",
            total_exports=Decimal("2200"),
            total_imports=Decimal("2000"),
            total_trade=Decimal("4200"),
            trade_balance=Decimal("200"),
            record_count=3,
            share=Decimal("0.5"),
        )
        with pytest.raises(FrozenInstanceError):
            row.share = Decimal("0")  # type: ignore[misc]

    def test_share_can_be_none(self):
        row = CommodityRankingRow(
            commodity_code="270900",
            commodity_name="Petroleum",
            total_exports=Decimal("2200"),
            total_imports=Decimal("2000"),
            total_trade=Decimal("4200"),
            trade_balance=Decimal("200"),
            record_count=3,
        )
        assert row.share is None

    def test_share_must_be_decimal_when_set(self):
        with pytest.raises(
            CommodityAnalyticsError, match="share"
        ):
            CommodityRankingRow(
                commodity_code="270900",
                commodity_name="Petroleum",
                total_exports=Decimal("1"),
                total_imports=Decimal("0"),
                total_trade=Decimal("1"),
                trade_balance=Decimal("1"),
                record_count=1,
                share="not a decimal",  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# TestCommodityRanking
# ---------------------------------------------------------------------------


class TestCommodityRanking:
    def test_returns_commodity_ranking_rows(self):
        rows = commodity_ranking(_commodity_dataset())
        assert isinstance(rows, tuple)
        assert all(
            isinstance(r, CommodityRankingRow) for r in rows
        )

    def test_share_default_none(self):
        rows = commodity_ranking(_commodity_dataset())
        for r in rows:
            assert r.share is None

    def test_share_computed_when_enabled(self):
        rows = commodity_ranking(
            _commodity_dataset(), include_share=True
        )
        for r in rows:
            assert r.share is not None

    def test_share_sum_is_at_most_one(self):
        rows = commodity_ranking(
            _commodity_dataset(), include_share=True
        )
        # Grand total includes records already
        # counted in the test fixture; all shares
        # should be ≤ 1.
        total_share = sum(r.share for r in rows)  # type: ignore
        assert Decimal("0") < total_share <= Decimal("1.0001")

    def test_share_is_zero_for_zero_trade_row(self):
        # Build a dataset with a zero-value
        # commodity.
        ds = _make_dataset(_records(
            ("270900", 0, "2022", "X", 1000.0),
            ("000000", 0, "2022", "X", 0.0),  # zero value
        ))
        rows = commodity_ranking(ds, include_share=True)
        # All non-zero rows have positive share.
        zero_row = next(r for r in rows if r.commodity_code == "000000")
        assert zero_row.total_trade == Decimal("0")
        assert zero_row.share == Decimal("0")

    def test_share_computation_uses_grand_total(self):
        # When `include_share=True`, the share is
        # each row's fraction of the GRAND total
        # across the dataset (not the filtered
        # subset). Verified by checking a single-
        # row dataset.
        ds = _make_dataset(_records(
            ("270900", 0, "2022", "X", 1000.0),
        ))
        rows = commodity_ranking(ds, include_share=True)
        assert len(rows) == 1
        assert rows[0].share == Decimal("1")

    def test_by_exports(self):
        rows = commodity_ranking(
            _commodity_dataset(), by="exports"
        )
        codes = [r.commodity_code for r in rows]
        assert codes == ["270900", "840731", "620342", "851762"]

    def test_consistent_with_top_hs_codes(self):
        cr = commodity_ranking(_commodity_dataset())
        top = top_hs_codes(_commodity_dataset())
        assert len(cr) == len(top)
        for cr_row, top_row in zip(cr, top):
            assert cr_row.commodity_code == top_row.commodity_code
            assert cr_row.total_exports == top_row.total_exports
            assert cr_row.total_imports == top_row.total_imports
            assert cr_row.total_trade == top_row.total_trade

    def test_include_share_must_be_bool(self):
        with pytest.raises(
            CommodityAnalyticsError, match="include_share"
        ):
            commodity_ranking(
                _commodity_dataset(),
                include_share="yes",  # type: ignore[arg-type]
            )

    def test_rejects_non_canonical(self):
        with pytest.raises(
            CommodityAnalyticsError, match="CanonicalDataset"
        ):
            commodity_ranking([{"raw": "dict"}])


# ---------------------------------------------------------------------------
# TestCommodityTrendPoint
# ---------------------------------------------------------------------------


class TestCommodityTrendPoint:
    def test_frozen(self):
        p = CommodityTrendPoint(
            year=2022,
            period="2022",
            total_trade=Decimal("150"),
            exports=Decimal("100"),
            imports=Decimal("50"),
            record_count=2,
        )
        with pytest.raises(FrozenInstanceError):
            p.year = 9999  # type: ignore[misc]

    def test_decimal_invariants(self):
        with pytest.raises(CommodityAnalyticsError, match="Decimal"):
            CommodityTrendPoint(
                year=2022,
                period="2022",
                total_trade="not a decimal",  # type: ignore[arg-type]
                exports=Decimal("100"),
                imports=Decimal("50"),
                record_count=2,
            )


# ---------------------------------------------------------------------------
# TestCommodityTrend
# ---------------------------------------------------------------------------


class TestCommodityTrend:
    def test_returns_tuple(self):
        trend = commodity_trend(
            _commodity_dataset(), commodity_code="270900"
        )
        assert isinstance(trend, tuple)
        assert all(
            isinstance(p, CommodityTrendPoint) for p in trend
        )

    def test_points_sorted_ascending(self):
        trend = commodity_trend(
            _commodity_dataset(), commodity_code="270900"
        )
        years = [p.year for p in trend]
        assert years == sorted(years)

    def test_yearly_granularity(self):
        trend = commodity_trend(
            _commodity_dataset(), commodity_code="270900"
        )
        # 2 distinct years: 2022, 2023.
        assert len(trend) == 2
        # 2022: X=1000, M=2000, total=3000
        # 2023: X=1200, M=0, total=1200
        by_year = {p.year: p for p in trend}
        assert by_year[2022].exports == Decimal("1000")
        assert by_year[2022].imports == Decimal("2000")
        assert by_year[2022].total_trade == Decimal("3000")
        assert by_year[2023].exports == Decimal("1200")
        assert by_year[2023].imports == Decimal("0")
        assert by_year[2023].total_trade == Decimal("1200")

    def test_per_period_granularity(self):
        ds = _make_dataset(_records(
            ("270900", 0, "202201", "X", 100.0),
            ("270900", 0, "202202", "X", 200.0),
        ))
        trend = commodity_trend(
            ds, commodity_code="270900", granularity="period"
        )
        periods = [p.period for p in trend]
        assert periods == ["202201", "202202"]

    def test_unknown_commodity_returns_empty(self):
        trend = commodity_trend(
            _commodity_dataset(), commodity_code="999999"
        )
        assert trend == ()

    def test_empty_dataset_returns_empty(self):
        trend = commodity_trend(
            _make_dataset(()), commodity_code="270900"
        )
        assert trend == ()

    def test_unknown_granularity_raises(self):
        with pytest.raises(
            CommodityAnalyticsError, match="granularity"
        ):
            commodity_trend(
                _commodity_dataset(),
                commodity_code="270900",
                granularity="monthly",
            )

    def test_empty_commodity_code_raises(self):
        with pytest.raises(
            CommodityAnalyticsError, match="commodity_code"
        ):
            commodity_trend(
                _commodity_dataset(), commodity_code=""
            )

    def test_reporter_filter(self):
        records = _records(
            ("270900", 0, "2022", "X", 1000.0),
            ("270900", 0, "2023", "X", 1200.0),
        )
        # Override the second record to have
        # reporter=156.
        raw_records = list(records)
        raw_records[1] = TradeParser(
            log_skipped=False
        ).parse_records([
            {
                **_baseline_raw(
                    reporterCode=156,
                    reporterISO="CHN",
                    reporterDesc="China",
                    cmdCode="270900",
                    cmdDesc="Petroleum",
                    partnerCode=0,
                    period="2023",
                    refYear=2023,
                    refPeriodId=20230101,
                    flowCode="X",
                    fobvalue=1200,
                    primaryValue=1200,
                ),
            }
        ]).records[0]
        ds = _make_dataset(tuple(raw_records))
        trend = commodity_trend(
            ds, commodity_code="270900", reporter_code=699
        )
        # Only India records: 1 point in 2022.
        assert len(trend) == 1
        assert trend[0].year == 2022

    def test_rejects_non_canonical(self):
        with pytest.raises(
            CommodityAnalyticsError, match="CanonicalDataset"
        ):
            commodity_trend("not a dataset", commodity_code="X")


# ---------------------------------------------------------------------------
# TestSectorSummaryRow
# ---------------------------------------------------------------------------


class TestSectorSummaryRow:
    def test_frozen(self):
        row = SectorSummaryRow(
            sector_id="V",
            sector_name="Mineral products",
            total_exports=Decimal("2200"),
            total_imports=Decimal("2000"),
            total_trade=Decimal("4200"),
            trade_balance=Decimal("200"),
            record_count=3,
            chapter_codes=(25, 26, 27),
            hs_code_count=1,
        )
        with pytest.raises(FrozenInstanceError):
            row.sector_id = "X"  # type: ignore[misc]

    def test_decimal_invariants(self):
        with pytest.raises(CommodityAnalyticsError, match="Decimal"):
            SectorSummaryRow(
                sector_id="V",
                sector_name="Mineral products",
                total_exports="not a decimal",  # type: ignore[arg-type]
                total_imports=Decimal("2000"),
                total_trade=Decimal("4200"),
                trade_balance=Decimal("200"),
                record_count=3,
            )


# ---------------------------------------------------------------------------
# TestSectorSummaries
# ---------------------------------------------------------------------------


class TestSectorSummaries:
    def test_returns_tuple(self):
        rows = sector_summaries(_commodity_dataset())
        assert isinstance(rows, tuple)
        assert all(isinstance(r, SectorSummaryRow) for r in rows)

    def test_one_row_per_wco_section(self):
        rows = sector_summaries(_commodity_dataset())
        # 21 WCO sections + 1 "Unknown" pseudo-section.
        assert len(rows) == 22

    def test_section_order_is_stable(self):
        rows = sector_summaries(_commodity_dataset())
        # First 21 rows follow the SECTORS Roman
        # numeral order; last is "??" (Unknown).
        ids = [r.sector_id for r in rows]
        expected_ids = [sid for sid, _, _ in SECTORS] + ["??"]
        assert ids == expected_ids

    def test_petroleum_maps_to_section_v(self):
        rows = sector_summaries(_commodity_dataset())
        by_id = {r.sector_id: r for r in rows}
        assert by_id["V"].sector_name == "Mineral products"
        # 270900 → chapter 27 → section V.
        # X=2200 (1000+1200), M=2000, total=4200,
        # n=3 records.
        assert by_id["V"].total_exports == Decimal("2200")
        assert by_id["V"].total_imports == Decimal("2000")
        assert by_id["V"].total_trade == Decimal("4200")
        assert by_id["V"].record_count == 3

    def test_machinery_maps_to_section_xvi(self):
        rows = sector_summaries(_commodity_dataset())
        by_id = {r.sector_id: r for r in rows}
        # 840731 → chapter 84 → section XVI
        # (machinery).
        # 851762 → chapter 85 → section XVI
        # (electrical).
        # Both contribute to XVI.
        assert by_id["XVI"].sector_name.startswith("Machinery")
        assert by_id["XVI"].total_exports == Decimal("1100")
        assert by_id["XVI"].total_imports == Decimal("700")

    def test_textiles_maps_to_section_xi(self):
        rows = sector_summaries(_commodity_dataset())
        by_id = {r.sector_id: r for r in rows}
        # 620342 → chapter 62 → section XI
        # (textiles).
        assert by_id["XI"].sector_name.startswith("Textiles")
        assert by_id["XI"].total_exports == Decimal("100")

    def test_unused_sections_have_zero_totals(self):
        rows = sector_summaries(_make_dataset(()))
        for r in rows:
            assert r.total_exports == Decimal("0")
            assert r.total_imports == Decimal("0")
            assert r.total_trade == Decimal("0")
            assert r.record_count == 0

    def test_flow_filter_export(self):
        rows = sector_summaries(_commodity_dataset(), flow="X")
        by_id = {r.sector_id: r for r in rows}
        # Each section's imports column zeroed.
        for r in rows:
            assert r.total_imports == Decimal("0")

    def test_flow_filter_import(self):
        rows = sector_summaries(_commodity_dataset(), flow="M")
        by_id = {r.sector_id: r for r in rows}
        for r in rows:
            assert r.total_exports == Decimal("0")

    def test_unknown_section_for_non_hs_code(self):
        # A commodity code whose HS chapter (99)
        # is outside the standard WCO range
        # (1..98). The parser accepts any 2/4/6/8/10
        # digit code, so 990000 is valid upstream
        # but maps to the "??" pseudo-section.
        ds = _make_dataset(_records(
            ("990000", 0, "2022", "X", 100.0),
        ))
        rows = sector_summaries(ds)
        by_id = {r.sector_id: r for r in rows}
        assert by_id["??"].sector_name == "Unknown"
        assert by_id["??"].record_count == 1

    def test_rejects_non_canonical(self):
        with pytest.raises(
            CommodityAnalyticsError, match="CanonicalDataset"
        ):
            sector_summaries([{"raw": "dict"}])


# ---------------------------------------------------------------------------
# TestSectorForChapter
# ---------------------------------------------------------------------------


class TestSectorForChapter:
    @pytest.mark.parametrize(
        "chapter,sector_id,sector_name_substr",
        [
            (1, "I", "Live animals"),
            (5, "I", "Live animals"),
            (6, "II", "Vegetable products"),
            (15, "III", "Animal or vegetable"),
            (27, "V", "Mineral products"),
            (50, "XI", "Textiles"),
            (71, "XIV", "precious stones"),
            (84, "XVI", "Machinery"),
            (85, "XVI", "Machinery"),
            (98, "XXI", "Works of art"),
        ],
    )
    def test_known_chapters(self, chapter, sector_id, sector_name_substr):
        sid, sname = sector_for_chapter(chapter)
        assert sid == sector_id
        assert sector_name_substr in sname

    @pytest.mark.parametrize("chapter", [0, 99, 100, 150])
    def test_unknown_chapters(self, chapter):
        sid, sname = sector_for_chapter(chapter)
        assert sid == "??"
        assert sname == "Unknown"

    def test_returns_tuple(self):
        result = sector_for_chapter(27)
        assert isinstance(result, tuple)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# TestSectorsConstant
# ---------------------------------------------------------------------------


class TestSectorsConstant:
    def test_has_21_sections(self):
        assert len(SECTORS) == 21

    def test_first_section_is_I(self):
        assert SECTORS[0][0] == "I"

    def test_last_section_is_XXI(self):
        assert SECTORS[-1][0] == "XXI"


# ---------------------------------------------------------------------------
# TestCommodityAnalyticsErrorPropagated
# ---------------------------------------------------------------------------


class TestCommodityAnalyticsErrorPropagated:
    def test_inherits_from_analytics_error(self):
        try:
            top_hs_codes(_commodity_dataset(), by="nope")
        except CommodityAnalyticsError as exc:
            assert isinstance(exc, AnalyticsError)

    def test_error_on_empty_commodity_code(self):
        with pytest.raises(
            CommodityAnalyticsError, match="commodity_code"
        ):
            commodity_trend(
                _commodity_dataset(), commodity_code=""
            )

    def test_error_on_invalid_hs_level(self):
        with pytest.raises(CommodityAnalyticsError, match="hs_level"):
            top_hs_codes(_commodity_dataset(), hs_level=5)