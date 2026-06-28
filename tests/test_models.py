"""Unit tests for the metadata models (un_comtrade.models).

Per the task scope (P1-011) these tests verify models
only: immutability, validation, equality, serialization.
No transport or metadata download.
"""

from __future__ import annotations

import copy
import pickle
from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from un_comtrade.models import (
    Classification,
    Country,
    Frequency,
    HSCode,
    Partner,
    TradeFlow,
    TransportMode,
)
from un_comtrade.models._base import BaseModel


# ---------------------------------------------------------------------------
# Country
# ---------------------------------------------------------------------------


class TestCountry:
    def test_minimal_construction(self):
        c = Country(
            country_code=699,
            iso_alpha2="IN",
            iso_alpha3="IND",
            display_name="India",
        )
        assert c.country_code == 699
        assert c.iso_alpha2 == "IN"
        assert c.iso_alpha3 == "IND"
        assert c.display_name == "India"
        assert c.entry_effective_date is None
        assert c.entry_expired_date is None

    def test_full_construction(self):
        c = Country(
            country_code=699,
            iso_alpha2="IN",
            iso_alpha3="IND",
            display_name="India",
            entry_effective_date=date(1947, 8, 15),
            entry_expired_date=None,
        )
        assert c.entry_effective_date == date(1947, 8, 15)

    def test_immutable(self):
        c = Country(
            country_code=699,
            iso_alpha2="IN",
            iso_alpha3="IND",
            display_name="India",
        )
        with pytest.raises(FrozenInstanceError):
            c.country_code = 100  # type: ignore[misc]

    def test_negative_country_code_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            Country(
                country_code=-1,
                iso_alpha2="IN",
                iso_alpha3="IND",
                display_name="India",
            )

    def test_non_int_country_code_rejected(self):
        with pytest.raises(TypeError, match="int"):
            Country(
                country_code="699",  # type: ignore[arg-type]
                iso_alpha2="IN",
                iso_alpha3="IND",
                display_name="India",
            )

    def test_bool_country_code_rejected(self):
        # bool is a subclass of int but is semantically wrong.
        with pytest.raises(TypeError, match="int"):
            Country(
                country_code=True,  # type: ignore[arg-type]
                iso_alpha2="IN",
                iso_alpha3="IND",
                display_name="India",
            )

    def test_invalid_iso_alpha2_rejected(self):
        with pytest.raises(ValueError, match="iso_alpha2"):
            Country(
                country_code=699,
                iso_alpha2="india",  # lowercase
                iso_alpha3="IND",
                display_name="India",
            )

    def test_short_iso_alpha2_rejected(self):
        with pytest.raises(ValueError, match="iso_alpha2"):
            Country(
                country_code=699,
                iso_alpha2="I",
                iso_alpha3="IND",
                display_name="India",
            )

    def test_invalid_iso_alpha3_rejected(self):
        with pytest.raises(ValueError, match="iso_alpha3"):
            Country(
                country_code=699,
                iso_alpha2="IN",
                iso_alpha3="india",  # lowercase
                display_name="India",
            )

    def test_empty_display_name_rejected(self):
        with pytest.raises(ValueError, match="display_name"):
            Country(
                country_code=699,
                iso_alpha2="IN",
                iso_alpha3="IND",
                display_name="",
            )

    def test_whitespace_display_name_rejected(self):
        with pytest.raises(ValueError, match="display_name"):
            Country(
                country_code=699,
                iso_alpha2="IN",
                iso_alpha3="IND",
                display_name="   ",
            )

    def test_expired_before_effective_rejected(self):
        with pytest.raises(ValueError, match="entry_expired_date"):
            Country(
                country_code=699,
                iso_alpha2="IN",
                iso_alpha3="IND",
                display_name="India",
                entry_effective_date=date(2022, 1, 1),
                entry_expired_date=date(2021, 1, 1),
            )

    def test_expired_equal_to_effective_rejected(self):
        # Same day counts as "not later".
        with pytest.raises(ValueError, match="entry_expired_date"):
            Country(
                country_code=699,
                iso_alpha2="IN",
                iso_alpha3="IND",
                display_name="India",
                entry_effective_date=date(2022, 1, 1),
                entry_expired_date=date(2022, 1, 1),
            )

    def test_valid_window_accepted(self):
        c = Country(
            country_code=699,
            iso_alpha2="IN",
            iso_alpha3="IND",
            display_name="India",
            entry_effective_date=date(2022, 1, 1),
            entry_expired_date=date(2023, 1, 1),
        )
        assert c.entry_expired_date == date(2023, 1, 1)

    def test_equality_on_field_values(self):
        a = Country(699, "IN", "IND", "India")
        b = Country(699, "IN", "IND", "India")
        c = Country(100, "US", "USA", "United States")
        assert a == b
        assert a != c

    def test_hashable(self):
        c = Country(699, "IN", "IND", "India")
        # Should not raise; frozen dataclasses are hashable by default.
        assert hash(c) is not None
        assert {c} == {Country(699, "IN", "IND", "India")}

    def test_to_dict(self):
        c = Country(
            country_code=699,
            iso_alpha2="IN",
            iso_alpha3="IND",
            display_name="India",
        )
        d = c.to_dict()
        assert d == {
            "country_code": 699,
            "iso_alpha2": "IN",
            "iso_alpha3": "IND",
            "display_name": "India",
            "entry_effective_date": None,
            "entry_expired_date": None,
        }

    def test_to_dict_with_dates(self):
        c = Country(
            country_code=699,
            iso_alpha2="IN",
            iso_alpha3="IND",
            display_name="India",
            entry_effective_date=date(1947, 8, 15),
        )
        d = c.to_dict()
        assert d["entry_effective_date"] == date(1947, 8, 15)

    def test_pickle_roundtrip(self):
        c = Country(699, "IN", "IND", "India")
        restored = pickle.loads(pickle.dumps(c))
        assert restored == c

    def test_copy_preserves_equality(self):
        c = Country(699, "IN", "IND", "India")
        assert copy.copy(c) == c
        assert copy.deepcopy(c) == c


# ---------------------------------------------------------------------------
# Partner
# ---------------------------------------------------------------------------


class TestPartner:
    def test_construction(self):
        p = Partner(
            country_code=156,
            iso_alpha2="CN",
            iso_alpha3="CHN",
            display_name="China",
        )
        assert p.country_code == 156
        assert p.display_name == "China"

    def test_immutable(self):
        p = Partner(156, "CN", "CHN", "China")
        with pytest.raises(FrozenInstanceError):
            p.country_code = 100  # type: ignore[misc]

    def test_partner_not_equal_to_country_with_same_fields(self):
        # Per dataclass equality, distinct types are never equal even
        # if their field values match. This is by design — Partner
        # and Country carry different semantic meaning.
        p = Partner(699, "IN", "IND", "India")
        c = Country(699, "IN", "IND", "India")
        assert p != c

    def test_partner_shares_validation_with_country(self):
        # Same validation rules apply.
        with pytest.raises(ValueError, match="iso_alpha2"):
            Partner(
                country_code=156,
                iso_alpha2="china",
                iso_alpha3="CHN",
                display_name="China",
            )

    def test_to_dict(self):
        p = Partner(156, "CN", "CHN", "China")
        d = p.to_dict()
        assert d["country_code"] == 156
        assert d["display_name"] == "China"

    def test_equality(self):
        a = Partner(156, "CN", "CHN", "China")
        b = Partner(156, "CN", "CHN", "China")
        assert a == b


# ---------------------------------------------------------------------------
# HSCode
# ---------------------------------------------------------------------------


class TestHSCode:
    @pytest.mark.parametrize(
        "code", ["01", "0101", "010110", "TOTAL"]
    )
    def test_valid_codes(self, code: str):
        h = HSCode(
            commodity_code=code,
            classification_code="HS",
            edition="2022",
        )
        assert h.commodity_code == code

    @pytest.mark.parametrize(
        "code",
        ["1", "012", "01012", "0101100", "ABC", "01AB", "total"],
    )
    def test_invalid_codes_rejected(self, code: str):
        with pytest.raises(ValueError):
            HSCode(
                commodity_code=code,
                classification_code="HS",
                edition="2022",
            )

    def test_non_hs_classification_rejected(self):
        with pytest.raises(ValueError, match="HS"):
            HSCode(
                commodity_code="0101",
                classification_code="SITC",
                edition="Rev.4",
            )

    def test_empty_commodity_code_rejected(self):
        with pytest.raises(ValueError, match="commodity_code"):
            HSCode(
                commodity_code="",
                classification_code="HS",
                edition="2022",
            )

    def test_empty_edition_rejected(self):
        with pytest.raises(ValueError, match="edition"):
            HSCode(
                commodity_code="0101",
                classification_code="HS",
                edition="",
            )

    def test_display_name_optional(self):
        h = HSCode(
            commodity_code="0101",
            classification_code="HS",
            edition="2022",
        )
        assert h.display_name is None

    def test_display_name_when_provided(self):
        h = HSCode(
            commodity_code="0101",
            classification_code="HS",
            edition="2022",
            display_name="Live horses",
        )
        assert h.display_name == "Live horses"

    def test_empty_display_name_rejected(self):
        with pytest.raises(ValueError, match="display_name"):
            HSCode(
                commodity_code="0101",
                classification_code="HS",
                edition="2022",
                display_name="  ",
            )

    def test_immutable(self):
        h = HSCode("0101", "HS", "2022")
        with pytest.raises(FrozenInstanceError):
            h.commodity_code = "9999"  # type: ignore[misc]

    def test_equality(self):
        a = HSCode("0101", "HS", "2022", "Live horses")
        b = HSCode("0101", "HS", "2022", "Live horses")
        c = HSCode("0101", "HS", "2017", "Live horses")
        assert a == b
        assert a != c

    def test_to_dict(self):
        h = HSCode("0101", "HS", "2022", "Live horses")
        d = h.to_dict()
        assert d == {
            "commodity_code": "0101",
            "classification_code": "HS",
            "edition": "2022",
            "display_name": "Live horses",
        }

    def test_pickle_roundtrip(self):
        h = HSCode("0101", "HS", "2022")
        restored = pickle.loads(pickle.dumps(h))
        assert restored == h


# ---------------------------------------------------------------------------
# TradeFlow
# ---------------------------------------------------------------------------


class TestTradeFlow:
    @pytest.mark.parametrize(
        "code,name",
        [("M", "Import"), ("X", "Export"), ("RX", "Re-export"), ("RM", "Re-import")],
    )
    def test_valid_flow_codes(self, code: str, name: str):
        f = TradeFlow(flow_code=code, display_name=name)
        assert f.flow_code == code
        assert f.display_name == name

    @pytest.mark.parametrize("code", ["", "m", "X1", "IMPORT", "EXP", "XX"])
    def test_invalid_flow_codes_rejected(self, code: str):
        with pytest.raises(ValueError, match="flow_code"):
            TradeFlow(flow_code=code, display_name="Anything")

    def test_empty_display_name_rejected(self):
        with pytest.raises(ValueError, match="display_name"):
            TradeFlow(flow_code="M", display_name="   ")

    def test_immutable(self):
        f = TradeFlow(flow_code="M", display_name="Import")
        with pytest.raises(FrozenInstanceError):
            f.flow_code = "X"  # type: ignore[misc]

    def test_equality(self):
        assert TradeFlow("M", "Import") == TradeFlow("M", "Import")
        assert TradeFlow("M", "Import") != TradeFlow("X", "Export")

    def test_to_dict(self):
        f = TradeFlow("M", "Import")
        assert f.to_dict() == {"flow_code": "M", "display_name": "Import"}


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


class TestClassification:
    @pytest.mark.parametrize(
        "code,name",
        [
            ("HS", "Harmonized System"),
            ("SITC", "Standard International Trade Classification"),
            ("BEC", "Broad Economic Categories"),
            ("EBOPS", "Extended Balance of Payments Services"),
        ],
    )
    def test_valid_codes(self, code: str, name: str):
        c = Classification(classification_code=code, display_name=name)
        assert c.classification_code == code

    @pytest.mark.parametrize("code", ["", "hs", "XYZ", "FOO"])
    def test_invalid_codes_rejected(self, code: str):
        with pytest.raises(ValueError, match="classification_code"):
            Classification(classification_code=code, display_name="Anything")

    def test_empty_display_name_rejected(self):
        with pytest.raises(ValueError, match="display_name"):
            Classification(classification_code="HS", display_name="   ")

    def test_immutable(self):
        c = Classification("HS", "Harmonized System")
        with pytest.raises(FrozenInstanceError):
            c.classification_code = "SITC"  # type: ignore[misc]

    def test_equality(self):
        assert Classification("HS", "HS") == Classification("HS", "HS")
        assert Classification("HS", "HS") != Classification("SITC", "SITC")

    def test_to_dict(self):
        c = Classification("HS", "Harmonized System")
        assert c.to_dict() == {
            "classification_code": "HS",
            "display_name": "Harmonized System",
        }


# ---------------------------------------------------------------------------
# Frequency
# ---------------------------------------------------------------------------


class TestFrequency:
    @pytest.mark.parametrize(
        "code,name",
        [("A", "Annual"), ("M", "Monthly")],
    )
    def test_valid_codes(self, code: str, name: str):
        f = Frequency(frequency_code=code, display_name=name)
        assert f.frequency_code == code

    @pytest.mark.parametrize("code", ["", "a", "Q", "W", "D", "Y"])
    def test_invalid_codes_rejected(self, code: str):
        with pytest.raises(ValueError, match="frequency_code"):
            Frequency(frequency_code=code, display_name="Anything")

    def test_empty_display_name_rejected(self):
        with pytest.raises(ValueError, match="display_name"):
            Frequency(frequency_code="A", display_name="")

    def test_immutable(self):
        f = Frequency("A", "Annual")
        with pytest.raises(FrozenInstanceError):
            f.frequency_code = "M"  # type: ignore[misc]

    def test_equality(self):
        assert Frequency("A", "Annual") == Frequency("A", "Annual")
        assert Frequency("A", "Annual") != Frequency("M", "Monthly")

    def test_to_dict(self):
        f = Frequency("A", "Annual")
        assert f.to_dict() == {"frequency_code": "A", "display_name": "Annual"}


# ---------------------------------------------------------------------------
# TransportMode
# ---------------------------------------------------------------------------


class TestTransportMode:
    def test_zero_total(self):
        m = TransportMode(mot_code=0, display_name="TOTAL")
        assert m.mot_code == 0
        assert m.display_name == "TOTAL"

    @pytest.mark.parametrize("code", [1, 2, 3, 10, 100])
    def test_valid_codes(self, code: int):
        m = TransportMode(mot_code=code, display_name="Mode")
        assert m.mot_code == code

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            TransportMode(mot_code=-1, display_name="Mode")

    def test_non_int_rejected(self):
        with pytest.raises(TypeError, match="int"):
            TransportMode(mot_code="1", display_name="Mode")  # type: ignore[arg-type]

    def test_bool_rejected(self):
        # bool is technically int but semantically wrong here.
        with pytest.raises(TypeError, match="int"):
            TransportMode(mot_code=True, display_name="Mode")  # type: ignore[arg-type]

    def test_empty_display_name_rejected(self):
        with pytest.raises(ValueError, match="display_name"):
            TransportMode(mot_code=0, display_name="   ")

    def test_immutable(self):
        m = TransportMode(mot_code=0, display_name="TOTAL")
        with pytest.raises(FrozenInstanceError):
            m.mot_code = 1  # type: ignore[misc]

    def test_equality(self):
        assert TransportMode(0, "TOTAL") == TransportMode(0, "TOTAL")
        assert TransportMode(0, "TOTAL") != TransportMode(1, "Sea")

    def test_to_dict(self):
        m = TransportMode(mot_code=0, display_name="TOTAL")
        assert m.to_dict() == {"mot_code": 0, "display_name": "TOTAL"}


# ---------------------------------------------------------------------------
# Base model
# ---------------------------------------------------------------------------


class TestBaseModel:
    def test_all_models_inherit_basemodel(self):
        for cls in (
            Country,
            Partner,
            HSCode,
            TradeFlow,
            Classification,
            Frequency,
            TransportMode,
        ):
            assert issubclass(cls, BaseModel)

    def test_base_model_is_subclass_base(self):
        # BaseModel is a plain base class (no abstract methods).
        # Subclasses inherit `to_dict()` and the canonical repr.
        assert isinstance(Country(699, "IN", "IND", "India"), BaseModel)
        assert isinstance(HSCode("0101", "HS", "2022"), BaseModel)

    def test_to_dict_returns_plain_dict(self):
        c = Country(699, "IN", "IND", "India")
        d = c.to_dict()
        assert isinstance(d, dict)
        assert all(isinstance(k, str) for k in d.keys())

    def test_repr_is_informative(self):
        c = Country(699, "IN", "IND", "India")
        s = repr(c)
        assert "Country" in s
        assert "699" in s
        assert "India" in s