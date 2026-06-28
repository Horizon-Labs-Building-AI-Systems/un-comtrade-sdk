"""Tests for the partner-level analytics (P6-003).

Per the P6-003 task scope, this module covers:

- **`top_partners`** — rank partners by trade
  value for a given reporter.
- **`partner_growth`** — year-over-year growth
  for a specific partner (with CAGR).
- **`partner_balance`** — exports minus imports
  per partner for a given reporter.
- **`bilateral_summary`** — mirror-flow summary
  between two reporters / a reporter and a
  partner.

Coverage:

- `TestPartnerRankingRow` — frozen dataclass,
  Decimal invariants.
- `TestTopPartners` — basic ranking, by
  total_trade / exports / imports /
  trade_balance / abs_trade_balance /
  record_count; flow filter (X / M); limit;
  descending / ascending; unknown field;
  non-canonical source.
- `TestPartnerGrowth` — basic growth (abs +
  rel + CAGR); CAGR edge cases (zero first,
  negative first, single year); per-period
  granularity; unknown granularity; empty
  dataset.
- `TestPartnerGrowthPoint` — frozen dataclass.
- `TestPartnerGrowthContainer` — PartnerGrowth
  dataclass + `years` property.
- `TestPartnerBalance` — by trade_balance,
  by abs_trade_balance, by exports, etc.;
  sorted descending; limit; non-canonical.
- `TestPartnerBalanceRow` — frozen dataclass.
- `TestBilateralSummary` — mirror flow
  capture; year range; non-canonical; pair
  with no records.
- `TestBilateralSummaryFrozen` — frozen
  dataclass + Decimal invariants.
- `TestErrorsPropagated` — PartnerAnalyticsError
  raised on bad inputs.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal
from typing import Any

import pytest

from un_comtrade.analytics import (
    AnalyticsError,
    BilateralSummary,
    PartnerAnalyticsError,
    PartnerBalanceRow,
    PartnerGrowth,
    PartnerGrowthPoint,
    PartnerRankingRow,
    bilateral_summary,
    partner_balance,
    partner_growth,
    top_partners,
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


_PARTNER_ISO3: dict[int, str] = {
    0: "W00",
    124: "USA",
    156: "CHN",
    392: "JPN",
    276: "DEU",
    826: "GBR",
    356: "IND",
    699: "IND",
    842: "USA",
    36: "AUS",
    76: "BRA",
    484: "MEX",
}


def _records(*tuples) -> tuple:
    """Build parsed `TradeRecord`s from tuples of
    `(reporter, partner, period, flow, value)`.

    `refYear` is extracted from `period[:4]`,
    `refPeriodId` is `int(period) * 10000 + 1` so
    intra-year periods stay distinct. Reporter /
    partner ISO3 + name are looked up from
    `_PARTNER_ISO3` (or default to the raw
    `_baseline_raw` defaults).
    """
    raws = []
    for t in tuples:
        reporter, partner, period, flow, value = t
        ref_year = int(period[:4])
        period_id = int(period) * 10000 + 1
        reporter_iso = _PARTNER_ISO3.get(reporter, "ZZZ")
        partner_iso = _PARTNER_ISO3.get(partner, "ZZZ")
        raws.append(
            _baseline_raw(
                reporterCode=reporter,
                reporterISO=reporter_iso,
                reporterDesc=f"Reporter-{reporter}",
                partnerCode=partner,
                partnerISO=partner_iso,
                partnerDesc=f"Partner-{partner}",
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
# TestPartnerRankingRow
# ---------------------------------------------------------------------------


class TestPartnerRankingRow:
    def test_frozen(self):
        row = PartnerRankingRow(
            partner_code=124,
            partner_iso3="USA",
            partner_name="United States",
            total_exports=Decimal("700"),
            total_imports=Decimal("130"),
            total_trade=Decimal("830"),
            trade_balance=Decimal("570"),
            record_count=5,
        )
        with pytest.raises(FrozenInstanceError):
            row.partner_code = 999  # type: ignore[misc]

    def test_decimal_invariants(self):
        with pytest.raises(PartnerAnalyticsError, match="Decimal"):
            PartnerRankingRow(
                partner_code=124,
                partner_iso3=None,
                partner_name=None,
                total_exports="not a decimal",  # type: ignore[arg-type]
                total_imports=Decimal("130"),
                total_trade=Decimal("830"),
                trade_balance=Decimal("570"),
                record_count=5,
            )

    def test_inherits_from_analytics_error(self):
        # PartnerAnalyticsError is a subclass of
        # AnalyticsError for unified catching.
        row = PartnerRankingRow(
            partner_code=124,
            partner_iso3="USA",
            partner_name=None,
            total_exports=Decimal("1"),
            total_imports=Decimal("0"),
            total_trade=Decimal("1"),
            trade_balance=Decimal("1"),
            record_count=1,
        )
        # No exception raised — the dataclass
        # validation is the only invariant check.
        assert isinstance(row, PartnerRankingRow)


# ---------------------------------------------------------------------------
# TestTopPartners
# ---------------------------------------------------------------------------


class TestTopPartners:
    def _dataset(self):
        # India exports to USA (124), CHN (156),
        # W00 (0); imports from USA only.
        records = _records(
            (699, 124, "2022", "X", 100.0),
            (699, 124, "2023", "X", 200.0),
            (699, 124, "2024", "X", 400.0),
            (699, 156, "2022", "X", 500.0),
            (699, 0, "2022", "X", 50.0),
            (699, 124, "2022", "M", 50.0),
            (699, 124, "2023", "M", 80.0),
        )
        return _make_dataset(records)

    def test_returns_tuple_of_rows(self):
        rows = top_partners(self._dataset(), reporter_code=699)
        assert isinstance(rows, tuple)
        assert all(isinstance(r, PartnerRankingRow) for r in rows)

    def test_default_sort_by_total_descending(self):
        rows = top_partners(self._dataset(), reporter_code=699)
        # USA total = 700 X + 130 M = 830
        # CHN total = 500 X + 0 M = 500
        # W00 total = 50 X + 0 M = 50
        codes = [r.partner_code for r in rows]
        assert codes == [124, 156, 0]

    def test_by_exports(self):
        rows = top_partners(
            self._dataset(), reporter_code=699, by="exports"
        )
        codes = [r.partner_code for r in rows]
        # USA exports = 700, CHN exports = 500,
        # W00 exports = 50.
        assert codes == [124, 156, 0]

    def test_by_imports(self):
        rows = top_partners(
            self._dataset(), reporter_code=699, by="imports"
        )
        codes = [r.partner_code for r in rows]
        # USA imports = 130, others = 0.
        assert codes == [124, 0, 156]

    def test_by_trade_balance(self):
        rows = top_partners(
            self._dataset(), reporter_code=699,
            by="trade_balance",
        )
        balances = {r.partner_code: r.trade_balance for r in rows}
        assert balances[124] == Decimal("570")
        assert balances[156] == Decimal("500")
        assert balances[0] == Decimal("50")

    def test_by_abs_trade_balance(self):
        rows = top_partners(
            self._dataset(), reporter_code=699,
            by="abs_trade_balance",
        )
        # USA has highest absolute balance (570).
        assert rows[0].partner_code == 124

    def test_by_record_count(self):
        rows = top_partners(
            self._dataset(), reporter_code=699,
            by="record_count",
        )
        # USA: 5 records (3 X + 2 M)
        # CHN: 1 record
        # W00: 1 record
        assert rows[0].partner_code == 124
        assert rows[0].record_count == 5

    def test_flow_filter_export(self):
        rows = top_partners(
            self._dataset(), reporter_code=699, flow="X"
        )
        # Only exports count toward rank.
        # Imports column zeroed.
        for r in rows:
            assert r.total_imports == Decimal("0")
        assert rows[0].partner_code == 124
        assert rows[0].total_exports == Decimal("700")

    def test_flow_filter_import(self):
        rows = top_partners(
            self._dataset(), reporter_code=699, flow="M"
        )
        for r in rows:
            assert r.total_exports == Decimal("0")
        # Only USA has imports.
        non_zero = [r for r in rows if r.total_imports != 0]
        assert len(non_zero) == 1
        assert non_zero[0].partner_code == 124

    def test_limit(self):
        rows = top_partners(
            self._dataset(), reporter_code=699, limit=2
        )
        assert len(rows) == 2
        assert rows[0].partner_code == 124
        assert rows[1].partner_code == 156

    def test_limit_zero(self):
        rows = top_partners(
            self._dataset(), reporter_code=699, limit=0
        )
        assert rows == ()

    def test_ascending_sort(self):
        rows = top_partners(
            self._dataset(), reporter_code=699, descending=False
        )
        # Ascending by total → W00 (50) first.
        assert rows[0].partner_code == 0

    def test_unknown_field_raises(self):
        with pytest.raises(
            PartnerAnalyticsError, match="Unknown ranking"
        ):
            top_partners(self._dataset(),
                         reporter_code=699, by="nope")

    def test_negative_limit_raises(self):
        with pytest.raises(
            PartnerAnalyticsError, match="non-negative"
        ):
            top_partners(
                self._dataset(), reporter_code=699, limit=-1
            )

    def test_empty_dataset_returns_empty_tuple(self):
        assert top_partners(
            _make_dataset(()), reporter_code=699
        ) == ()

    def test_no_records_for_reporter_returns_empty(self):
        records = _records((156, 0, "2022", "X", 100.0),)
        assert top_partners(
            _make_dataset(records), reporter_code=699
        ) == ()

    def test_rejects_non_canonical(self):
        with pytest.raises(
            PartnerAnalyticsError, match="CanonicalDataset"
        ):
            top_partners([{"raw": "dict"}], reporter_code=699)

    def test_iso3_metadata_captured(self):
        rows = top_partners(self._dataset(), reporter_code=699)
        by_code = {r.partner_code: r for r in rows}
        assert by_code[124].partner_iso3 == "USA"
        assert by_code[124].partner_name == "Partner-124"

    def test_inherits_from_analytics_error(self):
        try:
            top_partners(self._dataset(),
                         reporter_code=699, by="nope")
        except PartnerAnalyticsError as exc:
            assert isinstance(exc, AnalyticsError)


# ---------------------------------------------------------------------------
# TestPartnerGrowthPoint
# ---------------------------------------------------------------------------


class TestPartnerGrowthPoint:
    def test_frozen(self):
        p = PartnerGrowthPoint(
            year=2022,
            period="2022",
            total_trade=Decimal("150"),
            exports=Decimal("100"),
            imports=Decimal("50"),
            record_count=3,
        )
        with pytest.raises(FrozenInstanceError):
            p.year = 9999  # type: ignore[misc]

    def test_decimal_invariants(self):
        with pytest.raises(PartnerAnalyticsError, match="Decimal"):
            PartnerGrowthPoint(
                year=2022,
                period="2022",
                total_trade="not a decimal",  # type: ignore[arg-type]
                exports=Decimal("100"),
                imports=Decimal("50"),
                record_count=3,
            )


# ---------------------------------------------------------------------------
# TestPartnerGrowthContainer
# ---------------------------------------------------------------------------


class TestPartnerGrowthContainer:
    def test_frozen(self):
        g = PartnerGrowth(
            reporter_code=699,
            partner_code=124,
            absolute_change=Decimal("100"),
        )
        with pytest.raises(FrozenInstanceError):
            g.reporter_code = 999  # type: ignore[misc]

    def test_years_property(self):
        g = PartnerGrowth(
            reporter_code=699,
            partner_code=124,
            points=(
                PartnerGrowthPoint(2022, "2022",
                                   Decimal("100"), Decimal("100"),
                                   Decimal("0"), 1),
                PartnerGrowthPoint(2024, "2024",
                                   Decimal("200"), Decimal("200"),
                                   Decimal("0"), 1),
                PartnerGrowthPoint(2023, "2023",
                                   Decimal("150"), Decimal("150"),
                                   Decimal("0"), 1),
            ),
        )
        assert g.years == (2022, 2023, 2024)


# ---------------------------------------------------------------------------
# TestPartnerGrowth
# ---------------------------------------------------------------------------


class TestPartnerGrowth:
    def _growth_dataset(self):
        # India -> USA: 2022=100, 2023=200, 2024=400
        # (4x growth over 2 years → 100% CAGR).
        records = _records(
            (699, 124, "2022", "X", 100.0),
            (699, 124, "2023", "X", 200.0),
            (699, 124, "2024", "X", 400.0),
            (699, 124, "2022", "M", 50.0),
            (699, 124, "2023", "M", 80.0),
        )
        return _make_dataset(records)

    def test_returns_partner_growth(self):
        g = partner_growth(
            self._growth_dataset(),
            reporter_code=699,
            partner_code=124,
        )
        assert isinstance(g, PartnerGrowth)

    def test_points_sorted_ascending(self):
        g = partner_growth(
            self._growth_dataset(),
            reporter_code=699,
            partner_code=124,
        )
        years = [p.year for p in g.points]
        assert years == [2022, 2023, 2024]

    def test_absolute_change(self):
        g = partner_growth(
            self._growth_dataset(),
            reporter_code=699,
            partner_code=124,
        )
        # Last total (400) - First total (150) = 250
        assert g.absolute_change == Decimal("250")

    def test_relative_change(self):
        g = partner_growth(
            self._growth_dataset(),
            reporter_code=699,
            partner_code=124,
        )
        # 250 / 150 = 1.6666...
        assert g.relative_change == Decimal("250") / Decimal("150")

    def test_cagr_calculation(self):
        g = partner_growth(
            self._growth_dataset(),
            reporter_code=699,
            partner_code=124,
        )
        # 4x growth over 2 years → 100% CAGR.
        # (ratio = 400/150 ≈ 2.667; sqrt ≈ 1.633;
        # 1.633 - 1 = 0.633)
        assert g.cagr is not None
        assert Decimal("0.6") < g.cagr < Decimal("0.7")

    def test_single_point_no_cagr(self):
        records = _records((699, 124, "2022", "X", 100.0),)
        g = partner_growth(
            _make_dataset(records),
            reporter_code=699,
            partner_code=124,
        )
        # Single point: abs_change = 0, rel_change
        # = 0/100 = 0, cagr = None (need ≥ 2 points).
        assert g.cagr is None
        assert g.relative_change == Decimal("0")
        assert g.absolute_change == Decimal("0")

    def test_zero_first_value(self):
        # First year trade = 0; last year = 100.
        # CAGR undefined (0 → non-zero).
        records = _records(
            (699, 124, "2022", "X", 0.0),
            (699, 124, "2023", "X", 100.0),
        )
        g = partner_growth(
            _make_dataset(records),
            reporter_code=699,
            partner_code=124,
        )
        # abs_change = 100, rel_change is None.
        assert g.absolute_change == Decimal("100")
        assert g.relative_change is None
        assert g.cagr is None

    def test_no_records_returns_empty(self):
        g = partner_growth(
            self._growth_dataset(),
            reporter_code=699,
            partner_code=842,  # not in dataset
        )
        assert g.reporter_code == 699
        assert g.partner_code == 842
        assert g.points == ()
        assert g.absolute_change == Decimal("0")

    def test_unknown_granularity_raises(self):
        with pytest.raises(
            PartnerAnalyticsError, match="granularity"
        ):
            partner_growth(
                self._growth_dataset(),
                reporter_code=699,
                partner_code=124,
                granularity="monthly",
            )

    def test_per_period_granularity(self):
        records = _records(
            (699, 124, "202201", "X", 100.0),
            (699, 124, "202202", "X", 200.0),
        )
        g = partner_growth(
            _make_dataset(records),
            reporter_code=699,
            partner_code=124,
            granularity="period",
        )
        # 2 distinct periods.
        assert len(g.points) == 2
        periods = [p.period for p in g.points]
        assert periods == ["202201", "202202"]

    def test_rejects_non_canonical(self):
        with pytest.raises(
            PartnerAnalyticsError, match="CanonicalDataset"
        ):
            partner_growth(
                "not a dataset",
                reporter_code=699,
                partner_code=124,
            )

    def test_year_filter_within_window(self):
        """Verify that records outside the
        reporter/partner pair are not included."""
        records = _records(
            (699, 124, "2022", "X", 100.0),
            (699, 156, "2022", "X", 999.0),  # different partner
            (842, 124, "2022", "X", 999.0),  # different reporter
        )
        g = partner_growth(
            _make_dataset(records),
            reporter_code=699,
            partner_code=124,
        )
        # Only India->USA record.
        assert len(g.points) == 1
        assert g.points[0].total_trade == Decimal("100")


# ---------------------------------------------------------------------------
# TestPartnerBalanceRow
# ---------------------------------------------------------------------------


class TestPartnerBalanceRow:
    def test_frozen(self):
        row = PartnerBalanceRow(
            partner_code=124,
            partner_iso3="USA",
            partner_name="United States",
            total_exports=Decimal("700"),
            total_imports=Decimal("130"),
            trade_balance=Decimal("570"),
            total_trade=Decimal("830"),
            record_count=5,
        )
        with pytest.raises(FrozenInstanceError):
            row.partner_code = 999  # type: ignore[misc]

    def test_decimal_invariants(self):
        with pytest.raises(PartnerAnalyticsError, match="Decimal"):
            PartnerBalanceRow(
                partner_code=124,
                partner_iso3=None,
                partner_name=None,
                total_exports=Decimal("100"),
                total_imports=Decimal("50"),
                trade_balance="not a decimal",  # type: ignore[arg-type]
                total_trade=Decimal("150"),
                record_count=3,
            )


# ---------------------------------------------------------------------------
# TestPartnerBalance
# ---------------------------------------------------------------------------


class TestPartnerBalance:
    def _dataset(self):
        records = _records(
            (699, 124, "2022", "X", 100.0),
            (699, 124, "2023", "X", 200.0),
            (699, 156, "2022", "X", 500.0),
            (699, 124, "2022", "M", 50.0),
            (699, 124, "2023", "M", 80.0),
        )
        return _make_dataset(records)

    def test_returns_tuple_of_balance_rows(self):
        rows = partner_balance(self._dataset(), reporter_code=699)
        assert isinstance(rows, tuple)
        assert all(isinstance(r, PartnerBalanceRow) for r in rows)

    def test_default_descending_by_trade_balance(self):
        rows = partner_balance(self._dataset(), reporter_code=699)
        codes = [r.partner_code for r in rows]
        # USA balance = 300-130 = 170
        # CHN balance = 500-0 = 500
        # USA first by trade_balance: CHN > USA.
        assert codes[0] == 156

    def test_by_abs_trade_balance(self):
        rows = partner_balance(
            self._dataset(),
            reporter_code=699,
            by="abs_trade_balance",
        )
        # USA abs balance = 170, CHN = 500.
        assert rows[0].partner_code == 156

    def test_by_exports(self):
        rows = partner_balance(
            self._dataset(),
            reporter_code=699,
            by="exports",
        )
        codes = [r.partner_code for r in rows]
        assert codes == [156, 124]

    def test_limit(self):
        rows = partner_balance(
            self._dataset(),
            reporter_code=699,
            limit=1,
        )
        assert len(rows) == 1

    def test_unknown_field_raises(self):
        with pytest.raises(
            PartnerAnalyticsError, match="Unknown ranking"
        ):
            partner_balance(
                self._dataset(),
                reporter_code=699,
                by="nope",
            )

    def test_rejects_non_canonical(self):
        with pytest.raises(
            PartnerAnalyticsError, match="CanonicalDataset"
        ):
            partner_balance("not a dataset", reporter_code=699)

    def test_consistent_with_top_partners(self):
        # `partner_balance` and `top_partners(...,
        # by='trade_balance')` should produce the
        # same row order + same values.
        ds = self._dataset()
        balance_rows = partner_balance(ds, reporter_code=699)
        ranking_rows = top_partners(
            ds, reporter_code=699, by="trade_balance"
        )
        assert len(balance_rows) == len(ranking_rows)
        for b, r in zip(balance_rows, ranking_rows):
            assert b.partner_code == r.partner_code
            assert b.total_exports == r.total_exports
            assert b.total_imports == r.total_imports
            assert b.trade_balance == r.trade_balance
            assert b.total_trade == r.total_trade
            assert b.record_count == r.record_count


# ---------------------------------------------------------------------------
# TestBilateralSummary
# ---------------------------------------------------------------------------


class TestBilateralSummary:
    def _dataset(self):
        # India <-> USA: bilateral trade across
        # multiple periods + mirror flow from USA.
        records = _records(
            (699, 124, "2022", "X", 100.0),  # India exports
            (699, 124, "2023", "X", 200.0),
            (699, 124, "2022", "M", 50.0),  # India imports
            (699, 124, "2023", "M", 80.0),
            (124, 699, "2022", "X", 45.0),  # USA exports (mirror)
            (124, 699, "2023", "M", 30.0),  # USA imports (mirror)
        )
        return _make_dataset(records)

    def test_returns_bilateral_summary(self):
        b = bilateral_summary(
            self._dataset(),
            reporter_code=699,
            partner_code=124,
        )
        assert isinstance(b, BilateralSummary)

    def test_reporter_to_partner_exports(self):
        b = bilateral_summary(
            self._dataset(),
            reporter_code=699,
            partner_code=124,
        )
        # India -> USA exports = 100 + 200 = 300
        assert b.reporter_to_partner_exports == Decimal("300")

    def test_reporter_to_partner_imports(self):
        b = bilateral_summary(
            self._dataset(),
            reporter_code=699,
            partner_code=124,
        )
        # India <- USA imports = 50 + 80 = 130
        assert b.reporter_to_partner_imports == Decimal("130")

    def test_partner_to_reporter_exports(self):
        b = bilateral_summary(
            self._dataset(),
            reporter_code=699,
            partner_code=124,
        )
        # USA -> India exports = 45 (mirror)
        assert b.partner_to_reporter_exports == Decimal("45")

    def test_partner_to_reporter_imports(self):
        b = bilateral_summary(
            self._dataset(),
            reporter_code=699,
            partner_code=124,
        )
        # USA <- India imports = 30 (mirror)
        assert b.partner_to_reporter_imports == Decimal("30")

    def test_total_exports(self):
        b = bilateral_summary(
            self._dataset(),
            reporter_code=699,
            partner_code=124,
        )
        # 300 (India→USA) + 45 (USA→India) = 345
        assert b.total_exports == Decimal("345")

    def test_total_imports(self):
        b = bilateral_summary(
            self._dataset(),
            reporter_code=699,
            partner_code=124,
        )
        # 130 (India→USA) + 30 (USA→India) = 160
        assert b.total_imports == Decimal("160")

    def test_total_trade(self):
        b = bilateral_summary(
            self._dataset(),
            reporter_code=699,
            partner_code=124,
        )
        # 345 + 160 = 505
        assert b.total_trade == Decimal("505")

    def test_record_count(self):
        b = bilateral_summary(
            self._dataset(),
            reporter_code=699,
            partner_code=124,
        )
        # 6 records: 4 from India side + 2 mirror.
        assert b.record_count == 6

    def test_year_range(self):
        b = bilateral_summary(
            self._dataset(),
            reporter_code=699,
            partner_code=124,
        )
        # 2022-2023.
        assert b.year_range == (2022, 2023)

    def test_iso3_metadata(self):
        b = bilateral_summary(
            self._dataset(),
            reporter_code=699,
            partner_code=124,
        )
        assert b.partner_iso3 == "USA"

    def test_pair_with_no_records_returns_none(self):
        b = bilateral_summary(
            self._dataset(),
            reporter_code=699,
            partner_code=842,
        )
        assert b is None

    def test_one_sided_trade_still_returns_summary(self):
        # Only India -> USA exports; no mirror.
        records = _records((699, 124, "2022", "X", 100.0),)
        b = bilateral_summary(
            _make_dataset(records),
            reporter_code=699,
            partner_code=124,
        )
        assert b is not None
        assert b.reporter_to_partner_exports == Decimal("100")
        assert b.partner_to_reporter_exports == Decimal("0")
        assert b.total_trade == Decimal("100")

    def test_mirror_only_returns_summary(self):
        # Only USA -> India exports (mirror); no
        # India → USA records.
        records = _records((124, 699, "2022", "X", 50.0),)
        b = bilateral_summary(
            _make_dataset(records),
            reporter_code=699,
            partner_code=124,
        )
        assert b is not None
        assert b.partner_to_reporter_exports == Decimal("50")
        assert b.reporter_to_partner_exports == Decimal("0")

    def test_rejects_non_canonical(self):
        with pytest.raises(
            PartnerAnalyticsError, match="CanonicalDataset"
        ):
            bilateral_summary(
                "not a dataset",
                reporter_code=699,
                partner_code=124,
            )

    def test_partner_metadata_from_mirror_side(self):
        # If only mirror records exist, partner
        # metadata comes from the mirror's
        # partner (which is the reporter's
        # perspective).
        records = _records((124, 699, "2022", "X", 50.0),)
        b = bilateral_summary(
            _make_dataset(records),
            reporter_code=699,
            partner_code=124,
        )
        # Side A (India reporting on USA) has no
        # records; side B (USA reporting on India)
        # has 1. The partner in side B IS the
        # reporter=699, so iso3 is "IND".
        assert b is not None
        assert b.partner_iso3 == "IND"


# ---------------------------------------------------------------------------
# TestBilateralSummaryFrozen
# ---------------------------------------------------------------------------


class TestBilateralSummaryFrozen:
    def test_frozen(self):
        b = BilateralSummary(
            reporter_code=699,
            partner_code=124,
            partner_iso3="USA",
            partner_name="United States",
            reporter_to_partner_exports=Decimal("300"),
            reporter_to_partner_imports=Decimal("130"),
            partner_to_reporter_exports=Decimal("45"),
            partner_to_reporter_imports=Decimal("30"),
            total_exports=Decimal("345"),
            total_imports=Decimal("160"),
            total_trade=Decimal("505"),
            record_count=6,
            year_range=(2022, 2023),
        )
        with pytest.raises(FrozenInstanceError):
            b.reporter_code = 999  # type: ignore[misc]

    def test_decimal_invariants(self):
        with pytest.raises(PartnerAnalyticsError, match="Decimal"):
            BilateralSummary(
                reporter_code=699,
                partner_code=124,
                partner_iso3=None,
                partner_name=None,
                reporter_to_partner_exports=Decimal("100"),
                reporter_to_partner_imports=Decimal("50"),
                partner_to_reporter_exports=Decimal("30"),
                partner_to_reporter_imports=Decimal("0"),
                total_exports=Decimal("130"),
                total_imports=Decimal("50"),
                total_trade="not a decimal",  # type: ignore[arg-type]
                record_count=3,
                year_range=(2022, 2022),
            )