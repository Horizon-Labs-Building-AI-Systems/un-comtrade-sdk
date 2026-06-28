"""Tests for the trade-balance analytics (P6-006).

Per the P6-006 task scope, this module covers:

- **`country_balance`** — exports minus
  imports aggregated per reporter (country).
- **`partner_trade_balance`** — exports minus
  imports aggregated per partner for one
  reporter.
- **`commodity_balance`** — exports minus
  imports aggregated per commodity (HS code).
- **`global_balance`** — global trade balance
  across ALL reporters / partners /
  commodities.

Coverage:

- `TestBalanceSummary` — frozen dataclass,
  Decimal invariants.
- `TestCountryBalanceRow` — frozen dataclass.
- `TestPartnerBalanceRow` — frozen dataclass.
- `TestCommodityBalanceRow` — frozen dataclass.
- `TestCountryBalance` — basic balance
  computation, per-country breakdown, filter
  by reporter, descending / ascending, limit,
  non-canonical source.
- `TestPartnerTradeBalance` — per-partner balance
  for one reporter; partner metadata capture;
  ISO3 + name capture.
- `TestCommodityBalance` — per-commodity
  balance (global by default; reporter filter
  optional); descending / ascending; limit.
- `TestGlobalBalance` — single BalanceSummary
  for the whole dataset; empty dataset returns
  all-zero summary; balance = exports - imports.
- `TestBalanceErrorsPropagated` — bad source,
  negative limit, non-canonical source.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal
from typing import Any

import pytest

from un_comtrade.analytics import (
    AnalyticsError,
    BalanceAnalyticsError,
    BalanceSummary,
    CommodityBalanceRow,
    CountryBalanceRow,
    PartnerBalanceRow,
    commodity_balance,
    country_balance,
    global_balance,
    partner_trade_balance,
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
    `(reporter, partner, period, flow,
    commodity, value)`. ISO3 metadata is
    derived from a fixed lookup.
    """
    iso3 = {
        0: "W00", 124: "USA", 156: "CHN", 392: "JPN",
        699: "IND", 842: "USA", 36: "AUS", 76: "BRA",
        484: "MEX",
    }
    raws = []
    for t in tuples:
        reporter, partner, period, flow, commodity, value = t
        ref_year = int(period[:4])
        period_id = int(period) * 10000 + 1
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
                refPeriodId=period_id,
                flowCode=flow,
                cmdCode=commodity,
                cmdDesc=f"Commodity {commodity}",
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


def _balance_dataset():
    """India exports petroleum + machinery +
    textiles; imports petroleum + machinery +
    electronics; CHN exports to W00.

    India (699):
      270900 (petroleum): X=200, M=80
      840731 (machinery): X=100, M=50
      620342 (textiles):   X=300, M=0
      851762 (telecom):    X=0,   M=200
    China (156):
      TOTAL:              X=1000, M=0
    """
    return _make_dataset(_records(
        (699, 124, "2022", "X", "270900", 200.0),
        (699, 124, "2022", "X", "840731", 100.0),
        (699, 124, "2022", "M", "270900", 80.0),
        (699, 124, "2022", "M", "840731", 50.0),
        (699, 156, "2022", "X", "620342", 300.0),
        (699, 156, "2022", "M", "840731", 200.0),
        (699, 0, "2022", "M", "851762", 200.0),
        (156, 0, "2022", "X", "TOTAL", 1000.0),
    ))


# ---------------------------------------------------------------------------
# TestBalanceSummary
# ---------------------------------------------------------------------------


class TestBalanceSummary:
    def test_frozen(self):
        s = BalanceSummary(
            total_exports=Decimal("100"),
            total_imports=Decimal("50"),
            trade_balance=Decimal("50"),
            total_trade=Decimal("150"),
            record_count=3,
        )
        with pytest.raises(FrozenInstanceError):
            s.total_exports = Decimal("0")  # type: ignore[misc]

    def test_decimal_invariants(self):
        with pytest.raises(BalanceAnalyticsError, match="Decimal"):
            BalanceSummary(
                total_exports="not a decimal",  # type: ignore[arg-type]
                total_imports=Decimal("50"),
                trade_balance=Decimal("50"),
                total_trade=Decimal("150"),
                record_count=3,
            )

    def test_balance_equals_exports_minus_imports(self):
        s = BalanceSummary(
            total_exports=Decimal("100"),
            total_imports=Decimal("30"),
            trade_balance=Decimal("70"),
            total_trade=Decimal("130"),
            record_count=3,
        )
        assert s.trade_balance == (
            s.total_exports - s.total_imports
        )
        assert s.total_trade == (
            s.total_exports + s.total_imports
        )


# ---------------------------------------------------------------------------
# TestCountryBalanceRow
# ---------------------------------------------------------------------------


class TestCountryBalanceRow:
    def test_frozen(self):
        row = CountryBalanceRow(
            reporter_code=699,
            reporter_iso3="IND",
            reporter_name="India",
            total_exports=Decimal("600"),
            total_imports=Decimal("330"),
            trade_balance=Decimal("270"),
            total_trade=Decimal("930"),
            record_count=7,
        )
        with pytest.raises(FrozenInstanceError):
            row.reporter_code = 999  # type: ignore[misc]

    def test_decimal_invariants(self):
        with pytest.raises(BalanceAnalyticsError, match="Decimal"):
            CountryBalanceRow(
                reporter_code=699,
                reporter_iso3=None,
                reporter_name=None,
                total_exports=Decimal("100"),
                total_imports=Decimal("50"),
                trade_balance="not a decimal",  # type: ignore[arg-type]
                total_trade=Decimal("150"),
                record_count=3,
            )


# ---------------------------------------------------------------------------
# TestPartnerBalanceRow
# ---------------------------------------------------------------------------


class TestPartnerBalanceRow:
    def test_frozen(self):
        row = PartnerBalanceRow(
            partner_code=124,
            partner_iso3="USA",
            partner_name="United States",
            total_exports=Decimal("300"),
            total_imports=Decimal("130"),
            trade_balance=Decimal("170"),
            total_trade=Decimal("430"),
            record_count=4,
        )
        with pytest.raises(FrozenInstanceError):
            row.partner_code = 999  # type: ignore[misc]

    def test_decimal_invariants(self):
        # `PartnerBalanceRow` is shared with
        # `partner.py` (P6-003) — it raises
        # `PartnerAnalyticsError` (a subclass of
        # `AnalyticsError`, but not
        # `BalanceAnalyticsError`). The parent
        # class `AnalyticsError` is checked here.
        from un_comtrade.analytics.partner import (
            PartnerAnalyticsError,
        )
        with pytest.raises(PartnerAnalyticsError, match="Decimal"):
            PartnerBalanceRow(
                partner_code=124,
                partner_iso3=None,
                partner_name=None,
                total_exports=Decimal("100"),
                total_imports="not a decimal",  # type: ignore[arg-type]
                trade_balance=Decimal("50"),
                total_trade=Decimal("150"),
                record_count=3,
            )


# ---------------------------------------------------------------------------
# TestCommodityBalanceRow
# ---------------------------------------------------------------------------


class TestCommodityBalanceRow:
    def test_frozen(self):
        row = CommodityBalanceRow(
            commodity_code="270900",
            commodity_name="Petroleum",
            total_exports=Decimal("200"),
            total_imports=Decimal("80"),
            trade_balance=Decimal("120"),
            total_trade=Decimal("280"),
            record_count=2,
        )
        with pytest.raises(FrozenInstanceError):
            row.commodity_code = "X"  # type: ignore[misc]

    def test_decimal_invariants(self):
        with pytest.raises(BalanceAnalyticsError, match="Decimal"):
            CommodityBalanceRow(
                commodity_code="270900",
                commodity_name=None,
                total_exports=Decimal("100"),
                total_imports=Decimal("50"),
                trade_balance=Decimal("50"),
                total_trade="not a decimal",  # type: ignore[arg-type]
                record_count=3,
            )


# ---------------------------------------------------------------------------
# TestCountryBalance
# ---------------------------------------------------------------------------


class TestCountryBalance:
    def test_returns_tuple_of_country_balance_rows(self):
        rows = country_balance(_balance_dataset())
        assert isinstance(rows, tuple)
        assert all(
            isinstance(r, CountryBalanceRow) for r in rows
        )

    def test_per_country_breakdown(self):
        rows = country_balance(_balance_dataset())
        # India (699): X=600, M=530, balance=70
        # China (156): X=1000, M=0, balance=1000
        by_code = {r.reporter_code: r for r in rows}
        assert by_code[699].total_exports == Decimal("600")
        assert by_code[699].total_imports == Decimal("530")
        assert by_code[699].trade_balance == Decimal("70")
        assert by_code[156].total_exports == Decimal("1000")
        assert by_code[156].trade_balance == Decimal("1000")

    def test_default_descending_by_balance(self):
        rows = country_balance(_balance_dataset())
        # China (1000) first, India (70) second.
        assert rows[0].reporter_code == 156
        assert rows[1].reporter_code == 699

    def test_filter_by_reporter_returns_single_row(self):
        rows = country_balance(
            _balance_dataset(), reporter_code=699
        )
        assert len(rows) == 1
        assert rows[0].reporter_code == 699

    def test_filter_by_unknown_reporter_returns_empty(self):
        assert country_balance(
            _balance_dataset(), reporter_code=842
        ) == ()

    def test_ascending_sort(self):
        rows = country_balance(
            _balance_dataset(), descending=False
        )
        # India (270) first, China (1000) second.
        assert rows[0].reporter_code == 699
        assert rows[1].reporter_code == 156

    def test_limit(self):
        rows = country_balance(_balance_dataset(), limit=1)
        assert len(rows) == 1

    def test_limit_zero(self):
        rows = country_balance(_balance_dataset(), limit=0)
        assert rows == ()

    def test_empty_dataset_returns_empty_tuple(self):
        assert country_balance(_make_dataset(())) == ()

    def test_negative_limit_raises(self):
        with pytest.raises(
            BalanceAnalyticsError, match="non-negative"
        ):
            country_balance(_balance_dataset(), limit=-1)

    def test_rejects_non_canonical(self):
        with pytest.raises(
            BalanceAnalyticsError, match="CanonicalDataset"
        ):
            country_balance([{"raw": "dict"}])

    def test_iso3_metadata_captured(self):
        rows = country_balance(_balance_dataset())
        by_code = {r.reporter_code: r for r in rows}
        assert by_code[699].reporter_iso3 == "IND"
        assert by_code[156].reporter_iso3 == "CHN"


# ---------------------------------------------------------------------------
# TestPartnerTradeBalance
# ---------------------------------------------------------------------------


class TestPartnerTradeBalance:
    def test_returns_tuple_of_partner_trade_balance_rows(self):
        rows = partner_trade_balance(
            _balance_dataset(), reporter_code=699
        )
        assert isinstance(rows, tuple)
        assert all(
            isinstance(r, PartnerBalanceRow) for r in rows
        )

    def test_india_partner_trade_balance(self):
        rows = partner_trade_balance(
            _balance_dataset(), reporter_code=699
        )
        by_code = {r.partner_code: r for r in rows}
        # USA (124): X=300 (200+100), M=130 (80+50),
        # balance=170.
        assert by_code[124].total_exports == Decimal("300")
        assert by_code[124].total_imports == Decimal("130")
        assert by_code[124].trade_balance == Decimal("170")
        # China (156): X=300, M=200, balance=100.
        assert by_code[156].total_exports == Decimal("300")
        assert by_code[156].total_imports == Decimal("200")
        assert by_code[156].trade_balance == Decimal("100")
        # World (0): X=0, M=200 (electronics),
        # balance=-200.
        assert by_code[0].total_exports == Decimal("0")
        assert by_code[0].total_imports == Decimal("200")
        assert by_code[0].trade_balance == Decimal("-200")

    def test_default_descending_by_balance(self):
        rows = partner_trade_balance(
            _balance_dataset(), reporter_code=699
        )
        # USA (+170) → China (+100) → World (-200).
        codes = [r.partner_code for r in rows]
        assert codes == [124, 156, 0]

    def test_ascending(self):
        rows = partner_trade_balance(
            _balance_dataset(),
            reporter_code=699,
            descending=False,
        )
        # World (-200) first.
        assert rows[0].partner_code == 0

    def test_filter_by_reporter(self):
        # Different reporter (156, China) →
        # different balance breakdown.
        rows = partner_trade_balance(
            _balance_dataset(), reporter_code=156
        )
        # China only exports to W00 (1000).
        assert len(rows) == 1
        assert rows[0].partner_code == 0
        assert rows[0].total_exports == Decimal("1000")

    def test_unknown_reporter_returns_empty(self):
        assert partner_trade_balance(
            _balance_dataset(), reporter_code=842
        ) == ()

    def test_limit(self):
        rows = partner_trade_balance(
            _balance_dataset(), reporter_code=699, limit=2
        )
        assert len(rows) == 2

    def test_negative_limit_raises(self):
        with pytest.raises(
            BalanceAnalyticsError, match="non-negative"
        ):
            partner_trade_balance(
                _balance_dataset(),
                reporter_code=699,
                limit=-1,
            )

    def test_rejects_non_canonical(self):
        with pytest.raises(
            BalanceAnalyticsError, match="CanonicalDataset"
        ):
            partner_trade_balance(
                [{"raw": "dict"}], reporter_code=699
            )

    def test_iso3_metadata_captured(self):
        rows = partner_trade_balance(
            _balance_dataset(), reporter_code=699
        )
        by_code = {r.partner_code: r for r in rows}
        assert by_code[124].partner_iso3 == "USA"
        assert by_code[156].partner_iso3 == "CHN"


# ---------------------------------------------------------------------------
# TestCommodityBalance
# ---------------------------------------------------------------------------


class TestCommodityBalance:
    def test_returns_tuple_of_commodity_balance_rows(self):
        rows = commodity_balance(_balance_dataset())
        assert isinstance(rows, tuple)
        assert all(
            isinstance(r, CommodityBalanceRow) for r in rows
        )

    def test_global_commodity_balance(self):
        rows = commodity_balance(_balance_dataset())
        by_code = {r.commodity_code: r for r in rows}
        # 270900: India X=200, M=80; balance=120.
        assert by_code["270900"].total_exports == Decimal("200")
        assert by_code["270900"].total_imports == Decimal("80")
        assert by_code["270900"].trade_balance == Decimal("120")
        # 840731: India X=100, M=50; CHN X=0, M=0;
        # India X=100, M=50 → balance=50.
        # Wait: India exports 100 to USA, imports 50
        # from USA, plus China imports 200 from
        # China. So 840731 has India X=100, India
        # M=50+200=250, China X=0, M=0.
        # Total: X=100, M=250, balance=-150.
        assert by_code["840731"].total_exports == Decimal("100")
        assert by_code["840731"].total_imports == Decimal("250")
        assert by_code["840731"].trade_balance == Decimal("-150")

    def test_filter_by_reporter(self):
        rows = commodity_balance(_balance_dataset(),
                                reporter_code=699)
        # India only: no China records.
        by_code = {r.commodity_code: r for r in rows}
        assert "TOTAL" not in by_code  # TOTAL was China-only
        assert by_code["840731"].total_imports == Decimal("250")
        # China imports of 840731 (200) ARE India
        # imports (reporter=699, partner=156), so
        # included.

    def test_default_descending_by_balance(self):
        rows = commodity_balance(_balance_dataset())
        # TOTAL (1000) > 620342 (300) > 270900 (120)
        # > 851762 (-200) > 840731 (-150).
        codes = [r.commodity_code for r in rows]
        assert codes[0] == "TOTAL"
        assert codes[-1] == "851762"

    def test_ascending(self):
        rows = commodity_balance(
            _balance_dataset(), descending=False
        )
        # Worst balance first (851762).
        assert rows[0].commodity_code == "851762"

    def test_limit(self):
        rows = commodity_balance(_balance_dataset(), limit=2)
        assert len(rows) == 2

    def test_negative_limit_raises(self):
        with pytest.raises(
            BalanceAnalyticsError, match="non-negative"
        ):
            commodity_balance(_balance_dataset(), limit=-1)

    def test_rejects_non_canonical(self):
        with pytest.raises(
            BalanceAnalyticsError, match="CanonicalDataset"
        ):
            commodity_balance([{"raw": "dict"}])

    def test_iso3_metadata_captured(self):
        rows = commodity_balance(
            _balance_dataset(), reporter_code=699
        )
        by_code = {r.commodity_code: r for r in rows}
        assert by_code["270900"].commodity_name == (
            "Commodity 270900"
        )

    def test_empty_dataset_returns_empty(self):
        assert commodity_balance(_make_dataset(())) == ()


# ---------------------------------------------------------------------------
# TestGlobalBalance
# ---------------------------------------------------------------------------


class TestGlobalBalance:
    def test_returns_balance_summary(self):
        g = global_balance(_balance_dataset())
        assert isinstance(g, BalanceSummary)

    def test_total_exports(self):
        g = global_balance(_balance_dataset())
        # India X=600 + China X=1000 = 1600
        assert g.total_exports == Decimal("1600")

    def test_total_imports(self):
        g = global_balance(_balance_dataset())
        # India M=530 + China M=0 = 530
        assert g.total_imports == Decimal("530")

    def test_trade_balance(self):
        g = global_balance(_balance_dataset())
        # 1600 - 530 = 1070
        assert g.trade_balance == Decimal("1070")

    def test_total_trade(self):
        g = global_balance(_balance_dataset())
        # 1600 + 530 = 2130
        assert g.total_trade == Decimal("2130")

    def test_record_count(self):
        g = global_balance(_balance_dataset())
        assert g.record_count == 8

    def test_empty_dataset_returns_zero_summary(self):
        g = global_balance(_make_dataset(()))
        assert g.total_exports == Decimal("0")
        assert g.total_imports == Decimal("0")
        assert g.trade_balance == Decimal("0")
        assert g.total_trade == Decimal("0")
        assert g.record_count == 0

    def test_only_exports_dataset(self):
        ds = _make_dataset(_records(
            (699, 0, "2022", "X", "TOTAL", 500.0),
        ))
        g = global_balance(ds)
        assert g.total_exports == Decimal("500")
        assert g.total_imports == Decimal("0")
        assert g.trade_balance == Decimal("500")

    def test_only_imports_dataset(self):
        ds = _make_dataset(_records(
            (699, 0, "2022", "M", "TOTAL", 300.0),
        ))
        g = global_balance(ds)
        assert g.total_exports == Decimal("0")
        assert g.total_imports == Decimal("300")
        assert g.trade_balance == Decimal("-300")

    def test_balance_consistency(self):
        # Total balance = total exports - total imports.
        g = global_balance(_balance_dataset())
        assert g.trade_balance == (
            g.total_exports - g.total_imports
        )
        assert g.total_trade == (
            g.total_exports + g.total_imports
        )

    def test_rejects_non_canonical(self):
        with pytest.raises(
            BalanceAnalyticsError, match="CanonicalDataset"
        ):
            global_balance([{"raw": "dict"}])


# ---------------------------------------------------------------------------
# TestBalanceErrorsPropagated
# ---------------------------------------------------------------------------


class TestBalanceErrorsPropagated:
    def test_inherits_from_analytics_error(self):
        try:
            country_balance([{"raw": "dict"}])
        except BalanceAnalyticsError as exc:
            assert isinstance(exc, AnalyticsError)

    def test_country_negative_limit(self):
        with pytest.raises(
            BalanceAnalyticsError, match="non-negative"
        ):
            country_balance(_balance_dataset(), limit=-1)

    def test_partner_trade_negative_limit(self):
        with pytest.raises(
            BalanceAnalyticsError, match="non-negative"
        ):
            partner_trade_balance(
                _balance_dataset(),
                reporter_code=699,
                limit=-1,
            )

    def test_commodity_negative_limit(self):
        with pytest.raises(
            BalanceAnalyticsError, match="non-negative"
        ):
            commodity_balance(_balance_dataset(), limit=-1)

    def test_all_functions_reject_non_canonical(self):
        for fn, args in [
            (country_balance, {}),
            (partner_trade_balance, {"reporter_code": 699}),
            (commodity_balance, {}),
            (global_balance, {}),
        ]:
            with pytest.raises(
                BalanceAnalyticsError, match="CanonicalDataset"
            ):
                fn([{"raw": "dict"}], **args)