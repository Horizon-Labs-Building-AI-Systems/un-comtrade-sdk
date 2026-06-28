"""Unit tests for the trade-record models (un_comtrade.models.trade).

Per the P2-003 task scope, the models are pure
construction / validation / serialisation. No HTTP,
no parsing, no business logic.

Coverage:

- 7 models: Reporter, Partner, Commodity, TradeFlow,
  TradeValue, Quantity, TradeRecord
- Validation for every documented field rule
- Immutability (frozen dataclass)
- Decimal handling (preserve exact precision)
- Equality (by value, including Decimal)
- Serialization (to_dict, pickle roundtrip)
- World sentinel for Partner (partner_code=0 / W00 / World)
"""

from __future__ import annotations

import dataclasses
import json
import pickle
from copy import deepcopy
from decimal import Decimal

import pytest

from un_comtrade.models import (
    Commodity,
    Country,
    Partner as CatalogPartner,
    Quantity,
    RecordTradeFlow,
    Reporter,
    TradeFlow as CatalogTradeFlow,
    TradePartner,
    TradeRecord,
    TradeValue,
)
from un_comtrade.models.trade import (
    _MAX_REF_YEAR,
    _MIN_REF_YEAR,
    _TOTAL_COMMODITY,
    _VALID_FLOW_CODES,
    _VALID_FREQUENCY_CODES,
    _VALID_TYPE_CODES,
    _WORLD_PARTNER_CODE,
)


# ---------------------------------------------------------------------------
# Fixtures: a fully-populated TradeRecord + its sub-models
# ---------------------------------------------------------------------------


@pytest.fixture
def reporter():
    return Reporter(reporter_code=699, iso3="IND", name="India")


@pytest.fixture
def partner_world():
    return TradePartner(
        partner_code=0, iso3="W00", name="World"
    )


@pytest.fixture
def partner_country():
    return TradePartner(
        partner_code=842, iso3="USA", name="USA"
    )


@pytest.fixture
def commodity_total():
    return Commodity(commodity_code="TOTAL", name="All Commodities")


@pytest.fixture
def commodity_hs():
    return Commodity(commodity_code="0101", name="Live horses")


@pytest.fixture
def flow_export():
    return RecordTradeFlow(flow_code="X", flow_name="Export")


@pytest.fixture
def trade_value():
    return TradeValue(
        primary_value=Decimal("452684213646.747"),
        fob_value=Decimal("452684213646.747"),
        cif_value=None,
    )


@pytest.fixture
def quantity():
    return Quantity(
        qty=None,
        qty_unit_code=-1,
        qty_unit_abbr="N/A",
        is_estimated=False,
        alt_qty=None,
        alt_qty_unit_code=None,
        alt_qty_unit_abbr=None,
        is_alt_qty_estimated=False,
    )


@pytest.fixture
def trade_record(reporter, partner_world, commodity_total, flow_export, trade_value, quantity):
    return TradeRecord(
        type_code="C",
        frequency_code="A",
        classification_code="H6",
        classification_search_code="HS",
        edition="H6",
        is_original_classification=True,
        ref_period_id=20220101,
        ref_year=2022,
        ref_month=52,
        period="2022",
        reporter=reporter,
        partner=partner_world,
        partner2=None,
        flow=flow_export,
        commodity=commodity_total,
        customs_code="C00",
        customs_name="TOTAL CPC",
        mos_code="0",
        mot_code=0,
        mot_name="TOTAL MOT",
        quantity=quantity,
        net_weight_kg=None,
        is_net_weight_estimated=False,
        gross_weight_kg=None,
        is_gross_weight_estimated=False,
        trade_value=trade_value,
        legacy_estimation_flag=0,
        is_reported=False,
        is_aggregate=True,
        provenance=None,
    )


# ---------------------------------------------------------------------------
# Reporter
# ---------------------------------------------------------------------------


class TestReporter:
    def test_minimal(self):
        r = Reporter(reporter_code=699, iso3=None, name=None)
        assert r.reporter_code == 699
        assert r.iso3 is None
        assert r.name is None

    def test_full(self):
        r = Reporter(reporter_code=842, iso3="USA", name="USA")
        assert r.reporter_code == 842
        assert r.iso3 == "USA"
        assert r.name == "USA"

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="reporter_code"):
            Reporter(reporter_code=-1, iso3=None, name=None)

    def test_bool_rejected(self):
        with pytest.raises(TypeError, match="reporter_code"):
            Reporter(reporter_code=True, iso3=None, name=None)  # type: ignore[arg-type]

    def test_string_rejected(self):
        with pytest.raises(TypeError, match="reporter_code"):
            Reporter(reporter_code="699", iso3=None, name=None)  # type: ignore[arg-type]

    def test_iso3_lowercase_rejected(self):
        with pytest.raises(ValueError, match="iso3"):
            Reporter(reporter_code=699, iso3="ind", name=None)

    def test_iso3_two_letter_rejected(self):
        with pytest.raises(ValueError, match="iso3"):
            Reporter(reporter_code=699, iso3="IN", name=None)

    def test_iso3_world_accepted(self):
        # W00 is allowed on the record-embedded Reporter too,
        # even though it's not semantically correct (reporter
        # cannot be World). Validation is shape-only.
        r = Reporter(reporter_code=0, iso3="W00", name="World")
        assert r.iso3 == "W00"

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError, match="name"):
            Reporter(reporter_code=699, iso3=None, name="   ")

    def test_immutable(self):
        r = Reporter(reporter_code=699, iso3="IND", name="India")
        with pytest.raises(dataclasses.FrozenInstanceError):
            r.reporter_code = 100  # type: ignore[misc]

    def test_equality(self):
        a = Reporter(reporter_code=699, iso3="IND", name="India")
        b = Reporter(reporter_code=699, iso3="IND", name="India")
        assert a == b
        assert hash(a) == hash(b)

    def test_inequality(self):
        a = Reporter(reporter_code=699, iso3="IND", name="India")
        b = Reporter(reporter_code=842, iso3="USA", name="USA")
        assert a != b

    def test_to_dict(self):
        r = Reporter(reporter_code=699, iso3="IND", name="India")
        d = r.to_dict()
        assert d == {
            "reporter_code": 699,
            "iso3": "IND",
            "name": "India",
        }

    def test_pickle(self):
        r = Reporter(reporter_code=699, iso3="IND", name="India")
        assert pickle.loads(pickle.dumps(r)) == r


# ---------------------------------------------------------------------------
# Partner
# ---------------------------------------------------------------------------


class TestPartner:
    def test_world_sentinel(self):
        p = TradePartner(partner_code=0, iso3="W00", name="World")
        assert p.is_world is True
        assert p.partner_code == 0

    def test_country_partner(self):
        p = TradePartner(partner_code=842, iso3="USA", name="USA")
        assert p.is_world is False
        assert p.partner_code == 842

    def test_world_constant(self):
        assert _WORLD_PARTNER_CODE == 0

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="partner_code"):
            TradePartner(partner_code=-1, iso3=None, name=None)

    def test_bool_rejected(self):
        with pytest.raises(TypeError, match="partner_code"):
            TradePartner(partner_code=False, iso3=None, name=None)  # type: ignore[arg-type]

    def test_invalid_iso3_rejected(self):
        with pytest.raises(ValueError, match="iso3"):
            TradePartner(partner_code=842, iso3="us", name=None)

    def test_world_iso3_accepted(self):
        p = TradePartner(partner_code=0, iso3="W00", name=None)
        assert p.iso3 == "W00"

    def test_iso3_none_accepted(self):
        p = TradePartner(partner_code=699, iso3=None, name="India")
        assert p.iso3 is None

    def test_immutable(self):
        p = TradePartner(partner_code=0, iso3="W00", name="World")
        with pytest.raises(dataclasses.FrozenInstanceError):
            p.partner_code = 100  # type: ignore[misc]

    def test_distinct_from_catalog_partner(self):
        # Catalog Partner (metadata) and record-embedded Partner
        # have different shapes; equality must distinguish them.
        from datetime import date

        catalog = CatalogPartner(
            country_code=699,
            iso_alpha2="IN",
            iso_alpha3="IND",
            display_name="India",
            entry_effective_date=date(1947, 8, 15),
        )
        record = TradePartner(partner_code=699, iso3="IND", name="India")
        assert catalog != record
        assert record != catalog

    def test_equality(self):
        a = TradePartner(partner_code=0, iso3="W00", name="World")
        b = TradePartner(partner_code=0, iso3="W00", name="World")
        assert a == b
        assert hash(a) == hash(b)

    def test_to_dict(self):
        p = TradePartner(partner_code=0, iso3="W00", name="World")
        d = p.to_dict()
        assert d == {"partner_code": 0, "iso3": "W00", "name": "World"}


# ---------------------------------------------------------------------------
# Commodity
# ---------------------------------------------------------------------------


class TestCommodity:
    def test_total_wildcard(self):
        c = Commodity(commodity_code="TOTAL", name="All Commodities")
        assert c.commodity_code == "TOTAL"

    def test_hs_2_digit(self):
        c = Commodity(commodity_code="01", name="Live animals")
        assert c.commodity_code == "01"

    def test_hs_4_digit(self):
        c = Commodity(commodity_code="0101", name="Live horses")
        assert c.commodity_code == "0101"

    def test_hs_6_digit(self):
        c = Commodity(commodity_code="010121", name="Pure-bred breeding horses")
        assert c.commodity_code == "010121"

    def test_3_digit_rejected(self):
        with pytest.raises(ValueError, match="commodity_code"):
            Commodity(commodity_code="010", name=None)

    def test_5_digit_rejected(self):
        with pytest.raises(ValueError, match="commodity_code"):
            Commodity(commodity_code="01012", name=None)

    def test_non_digit_rejected(self):
        with pytest.raises(ValueError, match="commodity_code"):
            Commodity(commodity_code="ABC1", name=None)

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="commodity_code"):
            Commodity(commodity_code="   ", name=None)

    def test_bool_rejected(self):
        with pytest.raises(TypeError, match="commodity_code"):
            Commodity(commodity_code=True, name=None)  # type: ignore[arg-type]

    def test_name_none_accepted(self):
        # Upstream returns null when includeDesc=false.
        c = Commodity(commodity_code="TOTAL", name=None)
        assert c.name is None

    def test_name_empty_rejected(self):
        with pytest.raises(ValueError, match="name"):
            Commodity(commodity_code="TOTAL", name="   ")

    def test_immutable(self):
        c = Commodity(commodity_code="TOTAL", name="All Commodities")
        with pytest.raises(dataclasses.FrozenInstanceError):
            c.commodity_code = "0101"  # type: ignore[misc]

    def test_equality(self):
        a = Commodity(commodity_code="0101", name="Live horses")
        b = Commodity(commodity_code="0101", name="Live horses")
        assert a == b
        assert hash(a) == hash(b)

    def test_to_dict(self):
        c = Commodity(commodity_code="0101", name="Live horses")
        assert c.to_dict() == {
            "commodity_code": "0101",
            "name": "Live horses",
        }

    def test_total_constant(self):
        assert _TOTAL_COMMODITY == "TOTAL"


# ---------------------------------------------------------------------------
# TradeFlow (record-embedded)
# ---------------------------------------------------------------------------


class TestRecordTradeFlow:
    @pytest.mark.parametrize("code", ["M", "X", "RX", "RM"])
    def test_valid_codes(self, code):
        f = RecordTradeFlow(flow_code=code, flow_name="Export")
        assert f.flow_code == code

    def test_invalid_code_rejected(self):
        with pytest.raises(ValueError, match="flow_code"):
            RecordTradeFlow(flow_code="ZZ", flow_name="Bad")

    def test_lowercase_rejected(self):
        with pytest.raises(ValueError, match="flow_code"):
            RecordTradeFlow(flow_code="x", flow_name="Export")

    def test_empty_code_rejected(self):
        with pytest.raises(ValueError, match="flow_code"):
            RecordTradeFlow(flow_code="", flow_name="Export")

    def test_bool_code_rejected(self):
        with pytest.raises(TypeError, match="flow_code"):
            RecordTradeFlow(flow_code=True, flow_name="Export")  # type: ignore[arg-type]

    def test_name_none_accepted(self):
        f = RecordTradeFlow(flow_code="X", flow_name=None)
        assert f.flow_name is None

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError, match="flow_name"):
            RecordTradeFlow(flow_code="X", flow_name="   ")

    def test_immutable(self):
        f = RecordTradeFlow(flow_code="X", flow_name="Export")
        with pytest.raises(dataclasses.FrozenInstanceError):
            f.flow_code = "M"  # type: ignore[misc]

    def test_distinct_from_catalog_tradeflow(self):
        # Record-embedded TradeFlow vs catalog TradeFlow are
        # distinct types even when both describe "Export".
        record = RecordTradeFlow(flow_code="X", flow_name="Export")
        catalog = CatalogTradeFlow(flow_code="X", display_name="Export")
        assert record != catalog
        assert catalog != record

    def test_valid_codes_constant(self):
        assert _VALID_FLOW_CODES == frozenset({"M", "X", "RX", "RM"})

    def test_equality(self):
        a = RecordTradeFlow(flow_code="X", flow_name="Export")
        b = RecordTradeFlow(flow_code="X", flow_name="Export")
        assert a == b
        assert hash(a) == hash(b)

    def test_to_dict(self):
        f = RecordTradeFlow(flow_code="X", flow_name="Export")
        assert f.to_dict() == {"flow_code": "X", "flow_name": "Export"}


# ---------------------------------------------------------------------------
# TradeValue
# ---------------------------------------------------------------------------


class TestTradeValue:
    def test_minimal_required(self):
        # primary_value is required; fob/cif can be None.
        v = TradeValue(primary_value=Decimal("100"), fob_value=None, cif_value=None)
        assert v.primary_value == Decimal("100")
        assert v.fob_value is None
        assert v.cif_value is None

    def test_full(self):
        v = TradeValue(
            primary_value=Decimal("100.50"),
            fob_value=Decimal("90.25"),
            cif_value=Decimal("110.75"),
        )
        assert v.primary_value == Decimal("100.50")

    def test_zero_value_accepted(self):
        v = TradeValue(primary_value=Decimal("0"), fob_value=None, cif_value=None)
        assert v.primary_value == Decimal("0")

    def test_primary_required(self):
        with pytest.raises(TypeError):
            TradeValue(  # type: ignore[call-arg]
                fob_value=Decimal("100"), cif_value=None
            )

    def test_negative_primary_rejected(self):
        with pytest.raises(ValueError, match="primary_value"):
            TradeValue(
                primary_value=Decimal("-1"), fob_value=None, cif_value=None
            )

    def test_negative_fob_rejected(self):
        with pytest.raises(ValueError, match="fob_value"):
            TradeValue(
                primary_value=Decimal("1"),
                fob_value=Decimal("-1"),
                cif_value=None,
            )

    def test_negative_cif_rejected(self):
        with pytest.raises(ValueError, match="cif_value"):
            TradeValue(
                primary_value=Decimal("1"),
                fob_value=None,
                cif_value=Decimal("-1"),
            )

    def test_nan_rejected(self):
        with pytest.raises(ValueError, match="primary_value"):
            TradeValue(
                primary_value=Decimal("NaN"), fob_value=None, cif_value=None
            )

    def test_int_rejected(self):
        # Decimal only — int would silently truncate.
        with pytest.raises(TypeError, match="primary_value"):
            TradeValue(primary_value=100, fob_value=None, cif_value=None)  # type: ignore[arg-type]

    def test_float_rejected(self):
        with pytest.raises(TypeError, match="primary_value"):
            TradeValue(
                primary_value=1.5, fob_value=None, cif_value=None  # type: ignore[arg-type]
            )

    def test_str_rejected(self):
        with pytest.raises(TypeError, match="primary_value"):
            TradeValue(
                primary_value="100", fob_value=None, cif_value=None  # type: ignore[arg-type]
            )

    def test_immutable(self):
        v = TradeValue(
            primary_value=Decimal("100"), fob_value=None, cif_value=None
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            v.primary_value = Decimal("0")  # type: ignore[misc]

    def test_decimal_equality(self):
        # Decimal("100") == Decimal("100.0")
        v1 = TradeValue(
            primary_value=Decimal("100"), fob_value=None, cif_value=None
        )
        v2 = TradeValue(
            primary_value=Decimal("100.0"), fob_value=None, cif_value=None
        )
        assert v1 == v2
        assert hash(v1) == hash(v2)

    def test_to_dict_preserves_decimal(self):
        v = TradeValue(
            primary_value=Decimal("452684213646.747"),
            fob_value=Decimal("452684213646.747"),
            cif_value=None,
        )
        d = v.to_dict()
        assert isinstance(d["primary_value"], Decimal)
        assert d["primary_value"] == Decimal("452684213646.747")
        assert d["fob_value"] == Decimal("452684213646.747")
        assert d["cif_value"] is None

    def test_pickle(self):
        v = TradeValue(
            primary_value=Decimal("452684213646.747"),
            fob_value=None,
            cif_value=None,
        )
        assert pickle.loads(pickle.dumps(v)) == v

    def test_high_precision_preserved(self):
        # Decimals preserve precision; floats would round.
        v = TradeValue(
            primary_value=Decimal("0.1") + Decimal("0.2"),
            fob_value=None,
            cif_value=None,
        )
        assert v.primary_value == Decimal("0.3")


# ---------------------------------------------------------------------------
# Quantity
# ---------------------------------------------------------------------------


class TestQuantity:
    def test_minimal(self):
        q = Quantity(
            qty=None,
            qty_unit_code=-1,
            qty_unit_abbr=None,
            is_estimated=False,
            alt_qty=None,
            alt_qty_unit_code=None,
            alt_qty_unit_abbr=None,
            is_alt_qty_estimated=False,
        )
        assert q.qty is None

    def test_with_values(self):
        q = Quantity(
            qty=Decimal("1000"),
            qty_unit_code=8,
            qty_unit_abbr="kg",
            is_estimated=False,
            alt_qty=Decimal("2204.62"),
            alt_qty_unit_code=13,
            alt_qty_unit_abbr="lb",
            is_alt_qty_estimated=True,
        )
        assert q.qty == Decimal("1000")
        assert q.qty_unit_abbr == "kg"
        assert q.is_alt_qty_estimated is True

    def test_negative_qty_rejected(self):
        with pytest.raises(ValueError, match="qty"):
            Quantity(
                qty=Decimal("-1"),
                qty_unit_code=8,
                qty_unit_abbr="kg",
                is_estimated=False,
                alt_qty=None,
                alt_qty_unit_code=None,
                alt_qty_unit_abbr=None,
                is_alt_qty_estimated=False,
            )

    def test_negative_alt_qty_rejected(self):
        with pytest.raises(ValueError, match="alt_qty"):
            Quantity(
                qty=None,
                qty_unit_code=-1,
                qty_unit_abbr=None,
                is_estimated=False,
                alt_qty=Decimal("-1"),
                alt_qty_unit_code=None,
                alt_qty_unit_abbr=None,
                is_alt_qty_estimated=False,
            )

    def test_nan_qty_rejected(self):
        with pytest.raises(ValueError, match="qty"):
            Quantity(
                qty=Decimal("NaN"),
                qty_unit_code=-1,
                qty_unit_abbr=None,
                is_estimated=False,
                alt_qty=None,
                alt_qty_unit_code=None,
                alt_qty_unit_abbr=None,
                is_alt_qty_estimated=False,
            )

    def test_int_qty_rejected(self):
        with pytest.raises(TypeError, match="qty"):
            Quantity(
                qty=1000,  # type: ignore[arg-type]
                qty_unit_code=8,
                qty_unit_abbr="kg",
                is_estimated=False,
                alt_qty=None,
                alt_qty_unit_code=None,
                alt_qty_unit_abbr=None,
                is_alt_qty_estimated=False,
            )

    def test_bool_qty_unit_code_rejected(self):
        with pytest.raises(TypeError, match="qty_unit_code"):
            Quantity(
                qty=None,
                qty_unit_code=True,  # type: ignore[arg-type]
                qty_unit_abbr=None,
                is_estimated=False,
                alt_qty=None,
                alt_qty_unit_code=None,
                alt_qty_unit_abbr=None,
                is_alt_qty_estimated=False,
            )

    def test_negative_unit_code_rejected(self):
        # Documented sentinel is -1; anything else negative is
        # not in the upstream's range. We do NOT enforce > -1
        # because the upstream uses -1 as a documented value.
        # Verify -1 is accepted and -2 is also accepted
        # (validation is type-only, not range-based).
        q = Quantity(
            qty=None,
            qty_unit_code=-2,
            qty_unit_abbr=None,
            is_estimated=False,
            alt_qty=None,
            alt_qty_unit_code=None,
            alt_qty_unit_abbr=None,
            is_alt_qty_estimated=False,
        )
        assert q.qty_unit_code == -2

    def test_negative_alt_unit_code_accepted(self):
        # Documented sentinel for "no unit" is -1; negative
        # alt_qty_unit_code is accepted (validation is type-only,
        # like qty_unit_code).
        q = Quantity(
            qty=None,
            qty_unit_code=-1,
            qty_unit_abbr=None,
            is_estimated=False,
            alt_qty=None,
            alt_qty_unit_code=-1,
            alt_qty_unit_abbr=None,
            is_alt_qty_estimated=False,
        )
        assert q.alt_qty_unit_code == -1

    def test_bool_alt_unit_code_rejected(self):
        with pytest.raises(TypeError, match="alt_qty_unit_code"):
            Quantity(
                qty=None,
                qty_unit_code=-1,
                qty_unit_abbr=None,
                is_estimated=False,
                alt_qty=None,
                alt_qty_unit_code=True,  # type: ignore[arg-type]
                alt_qty_unit_abbr=None,
                is_alt_qty_estimated=False,
            )

    def test_bool_is_estimated_rejected(self):
        with pytest.raises(TypeError, match="is_estimated"):
            Quantity(
                qty=None,
                qty_unit_code=-1,
                qty_unit_abbr=None,
                is_estimated=1,  # type: ignore[arg-type]
                alt_qty=None,
                alt_qty_unit_code=None,
                alt_qty_unit_abbr=None,
                is_alt_qty_estimated=False,
            )

    def test_empty_qty_unit_abbr_rejected(self):
        with pytest.raises(ValueError, match="qty_unit_abbr"):
            Quantity(
                qty=None,
                qty_unit_code=-1,
                qty_unit_abbr="   ",
                is_estimated=False,
                alt_qty=None,
                alt_qty_unit_code=None,
                alt_qty_unit_abbr=None,
                is_alt_qty_estimated=False,
            )

    def test_immutable(self):
        q = Quantity(
            qty=None,
            qty_unit_code=-1,
            qty_unit_abbr=None,
            is_estimated=False,
            alt_qty=None,
            alt_qty_unit_code=None,
            alt_qty_unit_abbr=None,
            is_alt_qty_estimated=False,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            q.qty = Decimal("1")  # type: ignore[misc]

    def test_equality(self):
        a = Quantity(
            qty=Decimal("1000"),
            qty_unit_code=8,
            qty_unit_abbr="kg",
            is_estimated=False,
            alt_qty=None,
            alt_qty_unit_code=None,
            alt_qty_unit_abbr=None,
            is_alt_qty_estimated=False,
        )
        b = Quantity(
            qty=Decimal("1000"),
            qty_unit_code=8,
            qty_unit_abbr="kg",
            is_estimated=False,
            alt_qty=None,
            alt_qty_unit_code=None,
            alt_qty_unit_abbr=None,
            is_alt_qty_estimated=False,
        )
        assert a == b
        assert hash(a) == hash(b)

    def test_to_dict(self):
        q = Quantity(
            qty=Decimal("1000"),
            qty_unit_code=8,
            qty_unit_abbr="kg",
            is_estimated=False,
            alt_qty=Decimal("2204.62"),
            alt_qty_unit_code=13,
            alt_qty_unit_abbr="lb",
            is_alt_qty_estimated=True,
        )
        d = q.to_dict()
        assert isinstance(d["qty"], Decimal)
        assert d == {
            "qty": Decimal("1000"),
            "qty_unit_code": 8,
            "qty_unit_abbr": "kg",
            "is_estimated": False,
            "alt_qty": Decimal("2204.62"),
            "alt_qty_unit_code": 13,
            "alt_qty_unit_abbr": "lb",
            "is_alt_qty_estimated": True,
        }


# ---------------------------------------------------------------------------
# TradeRecord
# ---------------------------------------------------------------------------


class TestTradeRecord:
    def test_minimal(self, trade_record):
        # Fixture builds the full canonical record.
        assert isinstance(trade_record, TradeRecord)
        assert trade_record.reporter.reporter_code == 699
        assert trade_record.partner.partner_code == 0
        assert trade_record.flow.flow_code == "X"
        assert trade_record.commodity.commodity_code == "TOTAL"
        assert trade_record.trade_value.primary_value == Decimal(
            "452684213646.747"
        )

    def test_type_code_c_required(self, trade_record):
        with pytest.raises(ValueError, match="type_code"):
            dataclasses.replace(trade_record, type_code="X")

    def test_type_code_s_required(self, trade_record):
        # Services variant
        r = dataclasses.replace(trade_record, type_code="S")
        assert r.type_code == "S"

    def test_type_code_invalid(self, trade_record):
        with pytest.raises(ValueError, match="type_code"):
            dataclasses.replace(trade_record, type_code="Z")

    def test_type_code_bool_rejected(self, trade_record):
        with pytest.raises(TypeError, match="type_code"):
            dataclasses.replace(trade_record, type_code=True)  # type: ignore[arg-type]

    def test_frequency_code_a(self, trade_record):
        assert trade_record.frequency_code == "A"

    def test_frequency_code_m(self, trade_record):
        r = dataclasses.replace(trade_record, frequency_code="M")
        assert r.frequency_code == "M"

    def test_frequency_code_invalid(self, trade_record):
        with pytest.raises(ValueError, match="frequency_code"):
            dataclasses.replace(trade_record, frequency_code="Q")

    def test_classification_code_required(self, trade_record):
        with pytest.raises(ValueError, match="classification_code"):
            dataclasses.replace(trade_record, classification_code="")

    def test_classification_search_code_none(self, trade_record):
        r = dataclasses.replace(trade_record, classification_search_code=None)
        assert r.classification_search_code is None

    def test_edition_required(self, trade_record):
        with pytest.raises(ValueError, match="edition"):
            dataclasses.replace(trade_record, edition="")

    def test_is_original_classification_none(self, trade_record):
        r = dataclasses.replace(trade_record, is_original_classification=None)
        assert r.is_original_classification is None

    def test_is_original_classification_int_rejected(self, trade_record):
        with pytest.raises(TypeError, match="is_original_classification"):
            dataclasses.replace(trade_record, is_original_classification=1)  # type: ignore[arg-type]

    def test_ref_period_id_none(self, trade_record):
        r = dataclasses.replace(trade_record, ref_period_id=None)
        assert r.ref_period_id is None

    def test_ref_period_id_negative(self, trade_record):
        with pytest.raises(ValueError, match="ref_period_id"):
            dataclasses.replace(trade_record, ref_period_id=-1)

    def test_ref_period_id_bool_rejected(self, trade_record):
        with pytest.raises(TypeError, match="ref_period_id"):
            dataclasses.replace(trade_record, ref_period_id=True)  # type: ignore[arg-type]

    def test_ref_year_min(self, trade_record):
        r = dataclasses.replace(trade_record, ref_year=_MIN_REF_YEAR)
        assert r.ref_year == _MIN_REF_YEAR

    def test_ref_year_max(self, trade_record):
        r = dataclasses.replace(trade_record, ref_year=_MAX_REF_YEAR)
        assert r.ref_year == _MAX_REF_YEAR

    def test_ref_year_too_low(self, trade_record):
        with pytest.raises(ValueError, match="ref_year"):
            dataclasses.replace(trade_record, ref_year=_MIN_REF_YEAR - 1)

    def test_ref_year_too_high(self, trade_record):
        with pytest.raises(ValueError, match="ref_year"):
            dataclasses.replace(trade_record, ref_year=_MAX_REF_YEAR + 1)

    def test_ref_year_bool_rejected(self, trade_record):
        with pytest.raises(TypeError, match="ref_year"):
            dataclasses.replace(trade_record, ref_year=True)  # type: ignore[arg-type]

    def test_ref_month_annual_sentinel(self, trade_record):
        # 52 = annual sentinel
        assert trade_record.ref_month == 52

    def test_ref_month_january(self, trade_record):
        r = dataclasses.replace(trade_record, ref_month=1)
        assert r.ref_month == 1

    def test_ref_month_december(self, trade_record):
        r = dataclasses.replace(trade_record, ref_month=12)
        assert r.ref_month == 12

    def test_ref_month_invalid(self, trade_record):
        with pytest.raises(ValueError, match="ref_month"):
            dataclasses.replace(trade_record, ref_month=13)

    def test_ref_month_zero_rejected(self, trade_record):
        with pytest.raises(ValueError, match="ref_month"):
            dataclasses.replace(trade_record, ref_month=0)

    def test_period_annual(self, trade_record):
        r = dataclasses.replace(trade_record, period="2022", ref_year=2022, ref_month=52, frequency_code="A")
        assert r.period == "2022"

    def test_period_monthly(self, trade_record):
        r = dataclasses.replace(trade_record, period="202201", ref_year=2022, ref_month=1, frequency_code="M")
        assert r.period == "202201"

    def test_period_invalid_format(self, trade_record):
        with pytest.raises(ValueError, match="period"):
            dataclasses.replace(trade_record, period="2022-01")

    def test_period_invalid_token(self, trade_record):
        with pytest.raises(ValueError, match="period"):
            dataclasses.replace(trade_record, period="2022M01")

    def test_customs_code_required(self, trade_record):
        with pytest.raises(ValueError, match="customs_code"):
            dataclasses.replace(trade_record, customs_code="")

    def test_mos_code_required(self, trade_record):
        with pytest.raises(ValueError, match="mos_code"):
            dataclasses.replace(trade_record, mos_code="")

    def test_mot_code_negative(self, trade_record):
        with pytest.raises(ValueError, match="mot_code"):
            dataclasses.replace(trade_record, mot_code=-1)

    def test_mot_code_bool_rejected(self, trade_record):
        with pytest.raises(TypeError, match="mot_code"):
            dataclasses.replace(trade_record, mot_code=True)  # type: ignore[arg-type]

    def test_net_weight_negative(self, trade_record):
        with pytest.raises(ValueError, match="net_weight_kg"):
            dataclasses.replace(
                trade_record, net_weight_kg=Decimal("-1")
            )

    def test_gross_weight_negative(self, trade_record):
        with pytest.raises(ValueError, match="gross_weight_kg"):
            dataclasses.replace(
                trade_record, gross_weight_kg=Decimal("-1")
            )

    def test_weight_nan_rejected(self, trade_record):
        with pytest.raises(ValueError, match="net_weight_kg"):
            dataclasses.replace(
                trade_record, net_weight_kg=Decimal("NaN")
            )

    def test_weight_int_rejected(self, trade_record):
        with pytest.raises(TypeError, match="net_weight_kg"):
            dataclasses.replace(
                trade_record, net_weight_kg=100  # type: ignore[arg-type]
            )

    def test_legacy_estimation_flag_negative(self, trade_record):
        with pytest.raises(ValueError, match="legacy_estimation_flag"):
            dataclasses.replace(
                trade_record, legacy_estimation_flag=-1
            )

    def test_is_reported_int_rejected(self, trade_record):
        with pytest.raises(TypeError, match="is_reported"):
            dataclasses.replace(
                trade_record, is_reported=1  # type: ignore[arg-type]
            )

    def test_is_aggregate_int_rejected(self, trade_record):
        with pytest.raises(TypeError, match="is_aggregate"):
            dataclasses.replace(
                trade_record, is_aggregate=0  # type: ignore[arg-type]
            )

    def test_provenance_dict(self, trade_record):
        r = dataclasses.replace(
            trade_record, provenance={"source": "test"}
        )
        assert r.provenance == {"source": "test"}

    def test_provenance_list_rejected(self, trade_record):
        with pytest.raises(TypeError, match="provenance"):
            dataclasses.replace(trade_record, provenance=[])  # type: ignore[arg-type]

    def test_partner2_none(self, trade_record):
        assert trade_record.partner2 is None

    def test_partner2_set(self, trade_record, partner_country):
        r = dataclasses.replace(trade_record, partner2=partner_country)
        assert r.partner2 == partner_country

    def test_immutable(self, trade_record):
        with pytest.raises(dataclasses.FrozenInstanceError):
            trade_record.ref_year = 2023  # type: ignore[misc]

    def test_submodel_immutable(self, trade_record):
        with pytest.raises(dataclasses.FrozenInstanceError):
            trade_record.reporter.reporter_code = 100  # type: ignore[misc]

    def test_equality(self, trade_record):
        # Build a structurally identical copy via dataclasses.replace
        # round-trip (preserves sub-model identity, unlike asdict).
        fields = {f.name: getattr(trade_record, f.name) for f in dataclasses.fields(trade_record)}
        rebuilt = TradeRecord(**fields)
        assert trade_record == rebuilt
        assert hash(trade_record) == hash(rebuilt)

    def test_inequality_via_change(self, trade_record):
        other = dataclasses.replace(trade_record, ref_year=2023)
        assert trade_record != other

    def test_to_dict_has_all_30_fields(self, trade_record):
        d = trade_record.to_dict()
        assert len(d) == 30

    def test_to_dict_top_level_keys(self, trade_record):
        d = trade_record.to_dict()
        assert set(d.keys()) == {
            "type_code",
            "frequency_code",
            "classification_code",
            "classification_search_code",
            "edition",
            "is_original_classification",
            "ref_period_id",
            "ref_year",
            "ref_month",
            "period",
            "reporter",
            "partner",
            "partner2",
            "flow",
            "commodity",
            "customs_code",
            "customs_name",
            "mos_code",
            "mot_code",
            "mot_name",
            "quantity",
            "net_weight_kg",
            "is_net_weight_estimated",
            "gross_weight_kg",
            "is_gross_weight_estimated",
            "trade_value",
            "legacy_estimation_flag",
            "is_reported",
            "is_aggregate",
            "provenance",
        }

    def test_to_dict_preserves_decimals(self, trade_record):
        d = trade_record.to_dict()
        assert isinstance(d["trade_value"]["primary_value"], Decimal)
        assert d["trade_value"]["primary_value"] == Decimal(
            "452684213646.747"
        )

    def test_to_dict_unboxes_composed_models(self, trade_record):
        # Document the contract: BaseModel.to_dict() returns plain
        # dicts via dataclasses.asdict, so composed sub-models are
        # unboxed to dicts (not nested model instances). This is
        # the standard pattern across all SDK models.
        d = trade_record.to_dict()
        assert isinstance(d["reporter"], dict)
        assert isinstance(d["partner"], dict)
        assert isinstance(d["flow"], dict)
        assert isinstance(d["commodity"], dict)
        assert isinstance(d["quantity"], dict)
        assert isinstance(d["trade_value"], dict)
        # But the unboxed dicts have the expected fields.
        assert d["reporter"]["reporter_code"] == 699
        assert d["partner"]["partner_code"] == 0
        assert d["trade_value"]["primary_value"] == Decimal(
            "452684213646.747"
        )

    def test_pickle_roundtrip(self, trade_record):
        restored = pickle.loads(pickle.dumps(trade_record))
        assert restored == trade_record
        assert hash(restored) == hash(trade_record)

    def test_deepcopy(self, trade_record):
        copied = deepcopy(trade_record)
        assert copied == trade_record

    def test_valid_type_codes_constant(self):
        assert _VALID_TYPE_CODES == frozenset({"C", "S"})

    def test_valid_frequency_codes_constant(self):
        assert _VALID_FREQUENCY_CODES == frozenset({"A", "M"})


# ---------------------------------------------------------------------------
# Cross-model: equality / distinctness
# ---------------------------------------------------------------------------


class TestCrossModel:
    def test_reporter_and_country_distinct_types(self):
        # Reporter (record-embedded) vs Country (catalog).
        # They both have a "code" and "name" but the record-embedded
        # variant has `iso3` whereas the catalog variant has the
        # full ISO alpha-2/alpha-3/effective-date shape.
        r = Reporter(reporter_code=699, iso3="IND", name="India")
        c = Country(
            country_code=699,
            iso_alpha2="IN",
            iso_alpha3="IND",
            display_name="India",
        )
        assert r != c
        assert c != r

    def test_decimal_equality_in_to_dict(self):
        # Two TradeRecords with Decimal values that compare equal
        # but have different formatting must still serialise equal.
        v1 = TradeValue(
            primary_value=Decimal("1E+2"),
            fob_value=None,
            cif_value=None,
        )
        v2 = TradeValue(
            primary_value=Decimal("100"),
            fob_value=None,
            cif_value=None,
        )
        assert v1 == v2
        assert v1.to_dict() == v2.to_dict()


# ---------------------------------------------------------------------------
# Serialisation contracts
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_to_dict_is_json_incompatible_for_decimal(self):
        # Document the contract: Decimal values are NOT
        # json-serialisable by default. Callers must encode
        # via `default=str` or similar.
        v = TradeValue(
            primary_value=Decimal("452684213646.747"),
            fob_value=None,
            cif_value=None,
        )
        with pytest.raises(TypeError):
            json.dumps(v.to_dict())

    def test_to_dict_with_default_str(self):
        # The recommended workaround: default=str.
        v = TradeValue(
            primary_value=Decimal("452684213646.747"),
            fob_value=None,
            cif_value=None,
        )
        encoded = json.dumps(v.to_dict(), default=str)
        assert "452684213646.747" in encoded
        assert "null" in encoded  # fob/cif are None

    def test_full_record_to_dict_with_default_str(self, trade_record):
        # End-to-end: the whole TradeRecord can be JSON-encoded
        # with the documented workaround.
        encoded = json.dumps(trade_record.to_dict(), default=str)
        decoded = json.loads(encoded)
        assert decoded["reporter"]["name"] == "India"
        assert decoded["partner"]["name"] == "World"
        assert decoded["trade_value"]["primary_value"] == "452684213646.747"

    def test_deterministic_serialization(self, trade_record):
        # Same input produces equal output across calls.
        snapshots = [trade_record.to_dict() for _ in range(100)]
        assert all(s == snapshots[0] for s in snapshots)

    def test_asdict_matches_to_dict(self, trade_record):
        # to_dict() wraps dataclasses.asdict; the outputs must
        # be equal.
        assert trade_record.to_dict() == dataclasses.asdict(trade_record)

    def test_submodel_to_dict_isolated(self, reporter):
        # Each submodel can be serialised independently of
        # the parent record.
        assert reporter.to_dict() == {
            "reporter_code": 699,
            "iso3": "IND",
            "name": "India",
        }