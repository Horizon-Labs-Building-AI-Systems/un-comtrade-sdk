"""Unit tests for the L4 TradeParser (`un_comtrade.parser.TradeParser`).

Per the P2-006 task scope, the parser converts raw
upstream JSON records (camelCase dicts) into canonical
`TradeRecord` instances, validates them, and deduplicates
by the composite primary key.

Coverage:

- Single-record parsing (`parse_record`)
- List parsing + deduplication (`parse_records`)
- Field-level helpers (string / int / bool / Decimal
  coercion)
- Validation: missing required fields, bad types,
  non-finite floats, malformed booleans
- Decimal precision preservation
- Provenance capture (extra upstream fields preserved
  on `TradeRecord.provenance`)
- `TRADE_RECORD_KEY_FIELDS` composite key tuple
- `log_skipped` constructor option (silent vs logged)
- Roundtrip through pickle
"""

from __future__ import annotations

import dataclasses
import pickle
from decimal import Decimal

import pytest

from un_comtrade.models import (
    Commodity,
    Quantity,
    Reporter,
    TradePartner,
    TradeRecord,
    TradeResponse,
    TradeValue,
    RecordTradeFlow,
)
from un_comtrade.parser import (
    ParseResult,
    TRADE_RECORD_KEY_FIELDS,
    TradeParser,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _baseline_record(**overrides) -> dict:
    """Build a baseline raw upstream record (camelCase).

    Tests override individual fields to exercise the
    parser's coercion and validation paths.
    """
    raw = {
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
        "fobvalue": 452684213646.747,
        "primaryValue": 452684213646.747,
        "legacyEstimationFlag": 0,
        "isReported": False,
        "isAggregate": True,
    }
    raw.update(overrides)
    return raw


@pytest.fixture
def parser() -> TradeParser:
    return TradeParser(log_skipped=False)


@pytest.fixture
def verbose_parser() -> TradeParser:
    return TradeParser(log_skipped=True)


# ---------------------------------------------------------------------------
# Single-record parsing
# ---------------------------------------------------------------------------


class TestParseRecord:
    def test_returns_trade_record(self, parser):
        record = parser.parse_record(_baseline_record())
        assert isinstance(record, TradeRecord)

    def test_minimal_record(self, parser):
        record = parser.parse_record(_baseline_record())
        assert record.reporter.reporter_code == 699
        assert record.partner.partner_code == 0
        assert record.flow.flow_code == "X"
        assert record.commodity.commodity_code == "TOTAL"
        assert record.period == "2022"
        assert record.ref_year == 2022
        assert record.ref_month == 52

    def test_trade_value_decimal(self, parser):
        record = parser.parse_record(_baseline_record())
        # Per ADR-0027: Decimal preserves precision.
        assert record.trade_value.primary_value == Decimal(
            "452684213646.747"
        )
        assert isinstance(record.trade_value.primary_value, Decimal)
        assert record.trade_value.fob_value == Decimal("452684213646.747")
        assert record.trade_value.cif_value is None

    def test_decimal_precision_preserved(self, parser):
        # 0.1 + 0.2 in float would round; Decimal preserves.
        raw = _baseline_record(
            primaryValue="0.30000000000000004",
            fobvalue="0.30000000000000004",
        )
        record = parser.parse_record(raw)
        assert record.trade_value.primary_value == Decimal(
            "0.30000000000000004"
        )

    def test_partner2_default_none(self, parser):
        # All-zero partner2 sentinel collapses to None.
        record = parser.parse_record(_baseline_record())
        assert record.partner2 is None

    def test_partner2_set_when_present(self, parser):
        raw = _baseline_record(
            partner2Code=842, partner2ISO="USA", partner2Desc="USA"
        )
        record = parser.parse_record(raw)
        assert record.partner2 is not None
        assert record.partner2.partner_code == 842
        assert record.partner2.iso3 == "USA"
        assert record.partner2.name == "USA"

    def test_world_partner_sentinel(self, parser):
        record = parser.parse_record(_baseline_record(partnerCode=0))
        assert record.partner.is_world is True

    def test_specific_partner(self, parser):
        record = parser.parse_record(
            _baseline_record(
                partnerCode=842, partnerISO="USA", partnerDesc="USA"
            )
        )
        assert record.partner.is_world is False
        assert record.partner.name == "USA"

    def test_classification_edition(self, parser):
        # edition is derived from classificationCode for HS records.
        record = parser.parse_record(_baseline_record(classificationCode="H4"))
        assert record.classification_code == "H4"
        assert record.edition == "H4"

    def test_provenance_captures_extra_fields(self, parser):
        raw = _baseline_record(
            aggrLevel=0,
            isLeaf=False,
            extraField="hello",
            extraNumeric=42,
        )
        record = parser.parse_record(raw)
        # aggrLevel and isLeaf are KNOWN (filtered out).
        # extraField and extraNumeric are preserved.
        assert "extraField" in record.provenance
        assert record.provenance["extraField"] == "hello"
        assert record.provenance["extraNumeric"] == 42
        assert "aggrLevel" not in record.provenance

    def test_pickle_roundtrip(self, parser):
        record = parser.parse_record(_baseline_record())
        restored = pickle.loads(pickle.dumps(record))
        assert restored == record

    def test_immutable(self, parser):
        record = parser.parse_record(_baseline_record())
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.ref_year = 2023  # type: ignore[misc]


# ---------------------------------------------------------------------------
# List parsing + deduplication
# ---------------------------------------------------------------------------


class TestParseRecords:
    def test_empty_list(self, parser):
        result = parser.parse_records([])
        assert isinstance(result, ParseResult)
        assert result.records == []
        assert result.skipped == 0

    def test_single_record(self, parser):
        result = parser.parse_records([_baseline_record()])
        assert len(result.records) == 1
        assert result.skipped == 0

    def test_multiple_distinct_records(self, parser):
        # Two records with different partner codes (distinct
        # composite keys) — both should survive dedup.
        result = parser.parse_records(
            [
                _baseline_record(partnerCode=0, partnerISO="W00", partnerDesc="World"),
                _baseline_record(
                    partnerCode=842,
                    partnerISO="USA",
                    partnerDesc="USA",
                ),
            ]
        )
        assert len(result.records) == 2
        assert result.skipped == 0

    def test_duplicate_composite_key_first_wins(self, parser):
        # Two records with identical composite keys → first wins.
        # Second is recorded as a skip.
        result = parser.parse_records(
            [
                _baseline_record(primaryValue=100.0),
                _baseline_record(primaryValue=200.0),
            ]
        )
        assert len(result.records) == 1
        assert result.skipped == 1
        # First-wins: value is 100, not 200.
        assert result.records[0].trade_value.primary_value == Decimal("100")

    def test_composite_key_uniqueness(self, parser):
        # Three records sharing the same composite key → first wins,
        # two skipped.
        result = parser.parse_records(
            [
                _baseline_record(primaryValue=100.0),
                _baseline_record(primaryValue=200.0),
                _baseline_record(primaryValue=300.0),
            ]
        )
        assert len(result.records) == 1
        assert result.skipped == 2

    def test_distinct_keys_only_one(self, parser):
        # Records that differ in only one key field are distinct.
        result = parser.parse_records(
            [
                _baseline_record(period="2022"),
                _baseline_record(period="2023"),
            ]
        )
        assert len(result.records) == 2
        assert result.skipped == 0

    def test_skip_invalid_records(self, parser):
        # One valid record + one missing primaryValue + one bad
        # flowCode. Both invalids are skipped.
        valid = _baseline_record()
        missing_primary = _baseline_record(primaryValue=None)
        bad_flow = _baseline_record(flowCode="ZZ")
        result = parser.parse_records([valid, missing_primary, bad_flow])
        assert len(result.records) == 1
        assert result.skipped == 2

    def test_skip_non_mapping(self, parser):
        result = parser.parse_records(
            [_baseline_record(), "not a mapping", 42]
        )
        assert len(result.records) == 1
        assert result.skipped == 2

    def test_log_skipped_silent(self, parser):
        # Parser built with log_skipped=False — no exception,
        # no log; just the skipped count.
        result = parser.parse_records([_baseline_record(primaryValue=None)])
        assert result.skipped == 1
        assert result.records == []

    def test_log_skipped_verbose(self, verbose_parser, caplog):
        import logging

        caplog.set_level(logging.WARNING, logger="un_comtrade.metadata")
        result = verbose_parser.parse_records(
            [_baseline_record(primaryValue=None)]
        )
        assert result.skipped == 1
        # WARNING log emitted.
        assert any(
            "skipped trade record" in record.message
            for record in caplog.records
        )


# ---------------------------------------------------------------------------
# Composite key constant
# ---------------------------------------------------------------------------


class TestCompositeKey:
    def test_trade_record_key_fields(self):
        assert TRADE_RECORD_KEY_FIELDS == (
            "reporter_code",
            "partner_code",
            "period",
            "flow_code",
            "commodity_code",
            "classification_code",
            "edition",
            "customs_code",
            "mot_code",
            "partner2_code",
        )


# ---------------------------------------------------------------------------
# Field-level helpers
# ---------------------------------------------------------------------------


class TestFieldHelpers:
    def test_coerce_str_required_missing(self, parser):
        with pytest.raises(ValueError, match="missing"):
            parser._coerce_str({}, "typeCode")

    def test_coerce_str_required_null(self, parser):
        with pytest.raises(ValueError, match="missing"):
            parser._coerce_str({"typeCode": None}, "typeCode")

    def test_coerce_str_required_empty(self, parser):
        # Empty string is treated as missing (raises
        # ValueError with the "missing required field" message).
        with pytest.raises(ValueError, match="missing"):
            parser._coerce_str({"typeCode": ""}, "typeCode")

    def test_coerce_str_coerces_int(self, parser):
        # Upstream may send int codes as strings (or vice versa).
        assert parser._coerce_str({"x": 699}, "x") == "699"

    def test_optional_str_missing(self, parser):
        assert parser._optional_str({}, "x") is None

    def test_optional_str_empty(self, parser):
        assert parser._optional_str({"x": ""}, "x") is None

    def test_optional_str_present(self, parser):
        assert parser._optional_str({"x": "hello"}, "x") == "hello"

    def test_coerce_int_missing_default(self, parser):
        assert parser._coerce_int({}, "x", default=0) == 0

    def test_coerce_int_missing_no_default(self, parser):
        with pytest.raises(ValueError, match="missing"):
            parser._coerce_int({}, "x")

    def test_coerce_int_int(self, parser):
        assert parser._coerce_int({"x": 42}, "x") == 42

    def test_coerce_int_float(self, parser):
        assert parser._coerce_int({"x": 42.0}, "x") == 42

    def test_coerce_int_string(self, parser):
        assert parser._coerce_int({"x": "42"}, "x") == 42

    def test_coerce_int_bool_rejected(self, parser):
        with pytest.raises(TypeError, match="bool"):
            parser._coerce_int({"x": True}, "x")

    def test_coerce_int_nan_rejected(self, parser):
        with pytest.raises(ValueError, match="non-finite"):
            parser._coerce_int({"x": float("nan")}, "x")

    def test_optional_int_missing(self, parser):
        assert parser._optional_int({}, "x") is None

    def test_optional_int_present(self, parser):
        assert parser._optional_int({"x": 42}, "x") == 42

    def test_coerce_decimal_required_missing(self, parser):
        with pytest.raises(ValueError, match="missing"):
            parser._coerce_decimal({}, "primaryValue")

    def test_coerce_decimal_from_float(self, parser):
        # Decimal(str(value)) preserves precision.
        assert parser._coerce_decimal(
            {"x": 452684213646.747}, "x"
        ) == Decimal("452684213646.747")

    def test_coerce_decimal_from_string(self, parser):
        assert parser._coerce_decimal(
            {"x": "452684213646.747"}, "x"
        ) == Decimal("452684213646.747")

    def test_coerce_decimal_already_decimal(self, parser):
        d = Decimal("452684213646.747")
        assert parser._coerce_decimal({"x": d}, "x") == d

    def test_optional_decimal_null(self, parser):
        assert parser._optional_decimal({"x": None}, "x") is None

    def test_optional_decimal_present(self, parser):
        assert parser._optional_decimal(
            {"x": 452684213646.747}, "x"
        ) == Decimal("452684213646.747")

    def test_optional_bool_true(self, parser):
        assert parser._optional_bool({"x": True}, "x") is True

    def test_optional_bool_false(self, parser):
        assert parser._optional_bool({"x": False}, "x") is False

    def test_optional_bool_string_true(self, parser):
        assert parser._optional_bool({"x": "true"}, "x") is True

    def test_optional_bool_string_false(self, parser):
        assert parser._optional_bool({"x": "false"}, "x") is False

    def test_optional_bool_string_capitalized(self, parser):
        assert parser._optional_bool({"x": "True"}, "x") is True
        assert parser._optional_bool({"x": "False"}, "x") is False

    def test_optional_bool_missing(self, parser):
        assert parser._optional_bool({}, "x") is None

    def test_optional_bool_null(self, parser):
        assert parser._optional_bool({"x": None}, "x") is None

    def test_optional_bool_invalid_type(self, parser):
        with pytest.raises(TypeError, match="bool"):
            parser._optional_bool({"x": 42}, "x")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_missing_required_field_skips_record(self, parser):
        # primaryValue is required for TradeValue.
        bad = _baseline_record(primaryValue=None)
        result = parser.parse_records([bad])
        assert result.records == []
        assert result.skipped == 1

    def test_missing_period_skips_record(self, parser):
        bad = _baseline_record(period=None)
        result = parser.parse_records([bad])
        assert result.records == []
        assert result.skipped == 1

    def test_invalid_flow_code_skips_record(self, parser):
        bad = _baseline_record(flowCode="ZZ")
        result = parser.parse_records([bad])
        assert result.records == []
        assert result.skipped == 1

    def test_invalid_ref_year_skips_record(self, parser):
        # ref_year must be in 1900..2100.
        bad = _baseline_record(refYear=1800)
        result = parser.parse_records([bad])
        assert result.records == []
        assert result.skipped == 1

    def test_invalid_ref_month_skips_record(self, parser):
        bad = _baseline_record(refMonth=13)
        result = parser.parse_records([bad])
        assert result.records == []
        assert result.skipped == 1

    def test_invalid_period_format_skips_record(self, parser):
        bad = _baseline_record(period="2022-01")
        result = parser.parse_records([bad])
        assert result.records == []
        assert result.skipped == 1

    def test_invalid_hs_code_skips_record(self, parser):
        bad = _baseline_record(cmdCode="ABC")
        result = parser.parse_records([bad])
        assert result.records == []
        assert result.skipped == 1

    def test_negative_primary_value_skips_record(self, parser):
        bad = _baseline_record(primaryValue=-100.0)
        result = parser.parse_records([bad])
        assert result.records == []
        assert result.skipped == 1

    def test_partial_batch_skips_some(self, parser):
        valid = _baseline_record()
        bad1 = _baseline_record(primaryValue=None)
        bad2 = _baseline_record(refMonth=0)
        result = parser.parse_records([valid, bad1, bad2])
        assert len(result.records) == 1
        assert result.skipped == 2


# ---------------------------------------------------------------------------
# ParseResult + canonical surface
# ---------------------------------------------------------------------------


class TestParseResult:
    def test_records_field_is_list(self, parser):
        result = parser.parse_records([_baseline_record()])
        assert isinstance(result.records, list)
        assert all(isinstance(r, TradeRecord) for r in result.records)

    def test_skipped_count_is_int(self, parser):
        result = parser.parse_records([_baseline_record()])
        assert isinstance(result.skipped, int)
        assert result.skipped >= 0


# ---------------------------------------------------------------------------
# TradeResponse integration with parser-produced records
# ---------------------------------------------------------------------------


class TestTradeResponseIntegration:
    def test_trade_response_with_parsed_records(self, parser):
        records = parser.parse_records([_baseline_record()]).records
        response = TradeResponse(
            elapsed_seconds=0.27,
            count=1,
            records=records,
            error="",
            upstream_url="https://example/",
        )
        assert len(response.records) == 1
        assert isinstance(response.records[0], TradeRecord)
        assert response.records[0].reporter.reporter_code == 699

    def test_trade_response_skipped_field(self, parser):
        records = parser.parse_records(
            [_baseline_record(), _baseline_record(primaryValue=None)]
        )
        response = TradeResponse(
            elapsed_seconds=0.27,
            count=1,
            records=records.records,
            error="",
            upstream_url="https://example/",
            skipped=records.skipped,
        )
        assert response.skipped == 1
        assert len(response.records) == 1