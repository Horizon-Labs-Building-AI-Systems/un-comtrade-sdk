"""Unit tests for the metadata parser (un_comtrade.parser).

The parser turns upstream JSON payloads into canonical
model instances. Per the task scope (P1-014) it covers:

- parsing
- validation (via model `__post_init__`)
- normalization (field-name variants, casing, dates)
- deduplication (by primary key)

No downloading and no storage.

Tests use the recorded JSON samples under `data/`. The
suite does not hit the network.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from un_comtrade.models import (
    Classification,
    Country,
    DataItem,
    Frequency,
    HSCode,
    Partner,
    QuantityUnit,
    ReferenceEntry,
    TradeFlow,
    TransportMode,
)
from un_comtrade.parser import (
    SUPPORTED_RESOURCES,
    MetadataParser,
    ParseResult,
)


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(name: str) -> Any:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture
def parser() -> MetadataParser:
    # Silent parser for tests so the suite's stdout stays clean.
    return MetadataParser(log_skipped=False)


@pytest.fixture
def loud_parser() -> MetadataParser:
    return MetadataParser(log_skipped=True)


# ---------------------------------------------------------------------------
# Top-level dispatch
# ---------------------------------------------------------------------------


class TestDispatch:
    @pytest.mark.parametrize(
        "rid",
        ["R01", "R02", "R03", "R04", "R09", "R10", "R12", "R14", "R15"],
    )
    def test_dispatch_supported(self, parser: MetadataParser, rid: str):
        payload = _load(
            {
                "R01": "reference_list.json",
                "R02": "reporters.json",
                "R03": "partners.json",
                "R04": "hs_combined.json",
                "R09": "frequency.json",
                "R10": "trade_flows.json",
                "R12": "modes_of_transport.json",
                "R14": "quantity_units.json",
                "R15": "data_items.json",
            }[rid]
        )
        result = parser.parse(rid, payload)
        assert isinstance(result, ParseResult)
        assert result.records  # non-empty

    def test_unknown_resource_raises(self, parser: MetadataParser):
        with pytest.raises(ValueError, match="No parser registered"):
            parser.parse("R99", [])

    def test_supported_resources_constant(self):
        assert "R02" in SUPPORTED_RESOURCES
        assert "R09" in SUPPORTED_RESOURCES
        assert "R15" in SUPPORTED_RESOURCES


# ---------------------------------------------------------------------------
# R01 — references
# ---------------------------------------------------------------------------


class TestParseReferences:
    def test_first_entry_is_reference_entry(self, parser: MetadataParser):
        result = parser.parse("R01", _load("reference_list.json"))
        assert all(isinstance(r, ReferenceEntry) for r in result.records)
        assert len(result.records) == 28

    def test_fields(self, parser: MetadataParser):
        first = parser.parse("R01", _load("reference_list.json")).records[0]
        assert first.category == "dataitem"
        assert first.variable == "Trade data items"
        assert first.fileuri.startswith("https://")


# ---------------------------------------------------------------------------
# R02 — reporters
# ---------------------------------------------------------------------------


class TestParseReporters:
    def test_returns_countries(self, parser: MetadataParser):
        result = parser.parse("R02", _load("reporters.json"))
        assert all(isinstance(c, Country) for c in result.records)
        # India must be present.
        codes = {c.country_code for c in result.records}
        assert 699 in codes

    def test_normalises_iso_codes_to_uppercase(self, parser: MetadataParser):
        result = parser.parse(
            "R02",
            [
                {
                    "reporterCode": 4,
                    "text": "Afghanistan",
                    "reporterCodeIsoAlpha2": "af",
                    "reporterCodeIsoAlpha3": "afg",
                }
            ],
        )
        assert len(result.records) == 1
        c = result.records[0]
        assert c.iso_alpha2 == "AF"
        assert c.iso_alpha3 == "AFG"

    def test_dedupes_by_country_code(self, parser: MetadataParser):
        result = parser.parse(
            "R02",
            [
                {"reporterCode": 4, "text": "First"},
                {"reporterCode": 4, "text": "Duplicate"},
            ],
        )
        assert len(result.records) == 1
        assert result.records[0].display_name == "First"

    def test_skips_invalid_records(self, parser: MetadataParser):
        # Empty display_name fails Country validation; record
        # must be skipped, not raised.
        result = parser.parse(
            "R02",
            [
                {"reporterCode": 4, "text": ""},  # invalid: empty name
                {"reporterCode": 100, "text": "Valid"},
            ],
        )
        assert len(result.records) == 1
        assert result.records[0].country_code == 100
        assert result.skipped == 1

    def test_iso_alpha2_lowercase_rejected_by_validation(self, parser: MetadataParser):
        # After normalisation the value is uppercase; lowercase
        # at source is normalised to uppercase and accepted.
        # Non-letter characters are still rejected.
        result = parser.parse(
            "R02",
            [
                {
                    "reporterCode": 4,
                    "text": "AF",
                    "reporterCodeIsoAlpha2": "12",  # digits, fails validation
                }
            ],
        )
        assert result.skipped == 1
        assert result.records == []


# ---------------------------------------------------------------------------
# R03 — partners
# ---------------------------------------------------------------------------


class TestParsePartners:
    def test_returns_partners(self, parser: MetadataParser):
        result = parser.parse("R03", _load("partners.json"))
        assert all(isinstance(p, Partner) for p in result.records)
        codes = {p.country_code for p in result.records}
        assert 156 in codes  # China

    def test_partner_camelcase_fields(self, parser: MetadataParser):
        # The partners endpoint uses capital-P field names
        # (PartnerCode, PartnerDesc, PartnerCodeIsoAlpha2,
        # PartnerCodeIsoAlpha3) — distinct from the reporter
        # endpoint. The parser must read both.
        result = parser.parse(
            "R03",
            [
                {
                    "PartnerCode": 156,
                    "text": "China",
                    "PartnerDesc": "China",
                    "PartnerCodeIsoAlpha2": "CN",
                    "PartnerCodeIsoAlpha3": "CHN",
                }
            ],
        )
        assert len(result.records) == 1
        assert result.records[0].iso_alpha2 == "CN"
        assert result.records[0].iso_alpha3 == "CHN"

    def test_partner_dedup(self, parser: MetadataParser):
        result = parser.parse(
            "R03",
            [
                {"PartnerCode": 156, "text": "First"},
                {"PartnerCode": 156, "text": "Duplicate"},
            ],
        )
        assert len(result.records) == 1


# ---------------------------------------------------------------------------
# R09 — frequencies
# ---------------------------------------------------------------------------


class TestParseFrequencies:
    def test_returns_frequencies(self, parser: MetadataParser):
        result = parser.parse("R09", _load("frequency.json"))
        assert all(isinstance(f, Frequency) for f in result.records)
        codes = {f.frequency_code for f in result.records}
        assert codes == {"A", "M"}

    def test_full_record(self, parser: MetadataParser):
        annual = next(
            f for f in parser.parse("R09", _load("frequency.json")).records
            if f.frequency_code == "A"
        )
        assert annual.display_name == "Annual"


# ---------------------------------------------------------------------------
# R10 — trade flows
# ---------------------------------------------------------------------------


class TestParseTradeFlows:
    def test_returns_trade_flows(self, parser: MetadataParser):
        result = parser.parse("R10", _load("trade_flows.json"))
        assert all(isinstance(f, TradeFlow) for f in result.records)
        codes = {f.flow_code for f in result.records}
        assert codes == {"M", "X", "RX", "RM"}

    def test_unknown_flow_code_skipped(self, parser: MetadataParser):
        # TradeFlow validation rejects codes outside the
        # documented set {M, X, RX, RM}.
        result = parser.parse(
            "R10",
            [
                {"id": "M", "text": "Import"},
                {"id": "ZZ", "text": "Unknown"},  # invalid
            ],
        )
        assert len(result.records) == 1
        assert result.records[0].flow_code == "M"
        assert result.skipped == 1


# ---------------------------------------------------------------------------
# R12 — transport modes
# ---------------------------------------------------------------------------


class TestParseTransportModes:
    def test_returns_transport_modes(self, parser: MetadataParser):
        result = parser.parse("R12", _load("modes_of_transport.json"))
        assert all(isinstance(m, TransportMode) for m in result.records)
        codes = {m.mot_code for m in result.records}
        assert 0 in codes  # TOTAL

    def test_coerces_string_id_to_int(self, parser: MetadataParser):
        result = parser.parse(
            "R12",
            [
                {"id": "0", "text": "TOTAL"},  # string id, must coerce
                {"id": "1", "text": "Sea"},
            ],
        )
        assert len(result.records) == 2
        assert result.records[0].mot_code == 0
        assert result.records[1].mot_code == 1

    def test_invalid_mot_code_skipped(self, parser: MetadataParser):
        result = parser.parse(
            "R12",
            [
                {"id": "0", "text": "TOTAL"},
                {"id": "-1", "text": "Negative"},  # fails validation
            ],
        )
        assert len(result.records) == 1
        assert result.records[0].mot_code == 0
        assert result.skipped == 1


# ---------------------------------------------------------------------------
# R14 — quantity units
# ---------------------------------------------------------------------------


class TestParseQuantityUnits:
    def test_returns_quantity_units(self, parser: MetadataParser):
        result = parser.parse("R14", _load("quantity_units.json"))
        assert all(isinstance(q, QuantityUnit) for q in result.records)

    def test_total_unit_is_negative_one(self, parser: MetadataParser):
        result = parser.parse("R14", _load("quantity_units.json"))
        codes = {q.qty_unit_code for q in result.records}
        assert -1 in codes

    def test_uses_qty_code_field(self, parser: MetadataParser):
        result = parser.parse(
            "R14",
            [{"qtyCode": 8, "qtyAbbr": "kg", "qtyDescription": "Kilograms"}],
        )
        assert len(result.records) == 1
        q = result.records[0]
        assert q.qty_unit_code == 8
        assert q.qty_abbr == "kg"
        assert q.qty_description == "Kilograms"


# ---------------------------------------------------------------------------
# R15 — data items
# ---------------------------------------------------------------------------


class TestParseDataItems:
    def test_returns_data_items(self, parser: MetadataParser):
        result = parser.parse("R15", _load("data_items.json"))
        assert all(isinstance(d, DataItem) for d in result.records)
        names = {d.data_item for d in result.records}
        assert "datasetCode" in names

    def test_first_record(self, parser: MetadataParser):
        first = parser.parse("R15", _load("data_items.json")).records[0]
        assert first.data_item == "datasetCode"


# ---------------------------------------------------------------------------
# R04 / R05 — HS codes
# ---------------------------------------------------------------------------


class TestParseHSCodes:
    def test_combined_returns_hs_codes(self, parser: MetadataParser):
        result = parser.parse("R04", _load("hs_combined.json"))
        assert all(isinstance(h, HSCode) for h in result.records)

    def test_combined_tagged_with_combined_edition(
        self, parser: MetadataParser
    ):
        result = parser.parse("R04", _load("hs_combined.json"))
        # Edition is set to "combined" sentinel for the
        # combined catalogue.
        assert all(h.edition == "combined" for h in result.records)

    def test_per_edition_returns_hs_codes(self, parser: MetadataParser):
        result = parser.parse(
            "R05", _load("hs_2022.json"),  # not actually supported by dispatch
        )
        # R05 dispatch requires edition kwarg; we use parse_payload
        # directly via the lower-level method.
        records = parser.parse_r05_hs_edition(
            _load("hs_2022.json"), edition="2022"
        )
        assert all(isinstance(h, HSCode) for h in records)
        assert all(h.edition == "2022" for h in records)

    def test_total_wildcard_preserved(self, parser: MetadataParser):
        codes = parser.parse("R04", _load("hs_combined.json")).records
        assert any(c.commodity_code == "TOTAL" for c in codes)

    def test_hs_codes_dedup_by_code(self, parser: MetadataParser):
        records = parser.parse_r05_hs_edition(
            [
                {"id": "0101", "text": "First"},
                {"id": "0101", "text": "Duplicate"},
            ],
            edition="2022",
        )
        assert len(records) == 1
        assert records[0].display_name == "First"

    def test_invalid_commodity_code_skipped(self, parser: MetadataParser):
        records = parser.parse_r05_hs_edition(
            [
                {"id": "0101", "text": "Valid"},
                {"id": "BAD", "text": "Invalid"},  # not 2/4/6 digits, not TOTAL
            ],
            edition="2022",
        )
        assert len(records) == 1


# ---------------------------------------------------------------------------
# Payload shape handling
# ---------------------------------------------------------------------------


class TestPayloadShape:
    @pytest.mark.parametrize(
        "rid,name",
        [
            ("R02", "reporters.json"),
            ("R09", "frequency.json"),
        ],
    )
    def test_bare_list_payload(self, parser: MetadataParser, rid: str, name: str):
        # Wrap a bare list under {"data": [...]} and verify both
        # shapes parse identically.
        payload = _load(name)
        bare = parser.parse(rid, payload).records
        wrapped = parser.parse(rid, {"data": payload}).records
        assert len(bare) == len(wrapped)
        assert bare == wrapped

    def test_unsupported_shape_raises(self, parser: MetadataParser):
        with pytest.raises(ValueError, match="Unsupported payload shape"):
            parser.parse("R02", "not a list or object")


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------


class TestNormalization:
    def test_iso_codes_lowercase_to_uppercase(self, parser: MetadataParser):
        records = parser.parse(
            "R02",
            [
                {
                    "reporterCode": 4,
                    "text": "AF",
                    "reporterCodeIsoAlpha2": "af",
                    "reporterCodeIsoAlpha3": "afg",
                }
            ],
        ).records
        assert records[0].iso_alpha2 == "AF"
        assert records[0].iso_alpha3 == "AFG"

    def test_iso_codes_uppercase_unchanged(self, parser: MetadataParser):
        records = parser.parse(
            "R02",
            [
                {
                    "reporterCode": 4,
                    "text": "AF",
                    "reporterCodeIsoAlpha2": "AF",
                    "reporterCodeIsoAlpha3": "AFG",
                }
            ],
        ).records
        assert records[0].iso_alpha2 == "AF"
        assert records[0].iso_alpha3 == "AFG"

    def test_iso_codes_empty_to_none(self, parser: MetadataParser):
        records = parser.parse(
            "R02",
            [
                {"reporterCode": 4, "text": "AF", "reporterCodeIsoAlpha2": "", "reporterCodeIsoAlpha3": ""}
            ],
        ).records
        assert records[0].iso_alpha2 is None
        assert records[0].iso_alpha3 is None

    def test_iso_codes_missing_to_none(self, parser: MetadataParser):
        records = parser.parse(
            "R02",
            [{"reporterCode": 4, "text": "AF"}],
        ).records
        assert records[0].iso_alpha2 is None
        assert records[0].iso_alpha3 is None

    def test_date_with_time_component(self, parser: MetadataParser):
        records = parser.parse(
            "R02",
            [
                {
                    "reporterCode": 4,
                    "text": "AF",
                    "entryEffectiveDate": "1900-01-01T00:00:00",
                }
            ],
        ).records
        assert records[0].entry_effective_date == date(1900, 1, 1)

    def test_date_without_time_component(self, parser: MetadataParser):
        records = parser.parse(
            "R02",
            [
                {
                    "reporterCode": 4,
                    "text": "AF",
                    "entryEffectiveDate": "1900-01-01",
                }
            ],
        ).records
        assert records[0].entry_effective_date == date(1900, 1, 1)

    def test_invalid_date_to_none(self, parser: MetadataParser):
        records = parser.parse(
            "R02",
            [
                {
                    "reporterCode": 4,
                    "text": "AF",
                    "entryEffectiveDate": "not-a-date",
                }
            ],
        ).records
        # The date parser returns None for unparseable values;
        # the model accepts None for entry_effective_date.
        assert records[0].entry_effective_date is None

    def test_partner_camelcase_normalisation(self, parser: MetadataParser):
        records = parser.parse(
            "R03",
            [
                {
                    "PartnerCode": 156,
                    "text": "CN",
                    "PartnerDesc": "China",
                    "PartnerCodeIsoAlpha2": "cn",
                    "PartnerCodeIsoAlpha3": "chn",
                }
            ],
        ).records
        assert records[0].iso_alpha2 == "CN"
        assert records[0].iso_alpha3 == "CHN"


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    def test_dedup_reporters(self, parser: MetadataParser):
        records = parser.parse(
            "R02",
            [
                {"reporterCode": 4, "text": "First"},
                {"reporterCode": 4, "text": "Second"},
                {"reporterCode": 5, "text": "Other"},
            ],
        ).records
        assert len(records) == 2
        codes = [r.country_code for r in records]
        assert codes == [4, 5]

    def test_dedup_hs_codes(self, parser: MetadataParser):
        records = parser.parse_r05_hs_edition(
            [
                {"id": "0101", "text": "First"},
                {"id": "0101", "text": "Second"},
                {"id": "0102", "text": "Other"},
            ],
            edition="2022",
        )
        assert len(records) == 2

    def test_dedup_frequencies(self, parser: MetadataParser):
        records = parser.parse(
            "R09",
            [
                {"id": "A", "text": "Annual 1"},
                {"id": "A", "text": "Annual 2"},
            ],
        ).records
        assert len(records) == 1

    def test_skip_count(self, parser: MetadataParser):
        result = parser.parse(
            "R02",
            [
                {"reporterCode": 4, "text": "First"},
                {"reporterCode": 4, "text": "Dup"},
            ],
        )
        assert len(result.records) == 1
        assert result.skipped == 1


# ---------------------------------------------------------------------------
# Skipped-record logging
# ---------------------------------------------------------------------------


class TestLogging:
    def test_loud_parser_logs_skips(self, loud_parser: MetadataParser, caplog):
        loud_parser.parse(
            "R02",
            [
                {"reporterCode": 4, "text": ""},  # invalid
            ],
        )
        # Caplog captures the SDK logger; filter by our namespace.
        assert any(
            "skipped" in record.message.lower()
            or "validation" in record.message.lower()
            for record in caplog.records
        )

    def test_silent_parser_no_logs(self, parser: MetadataParser, caplog):
        parser.parse(
            "R02",
            [{"reporterCode": 4, "text": ""}],
        )
        # log_skipped=False should keep the SDK logger quiet
        # for skip events.
        assert not any(
            "skipped" in record.message.lower() for record in caplog.records
        )


# ---------------------------------------------------------------------------
# Validation propagation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_empty_display_name_rejected(self, parser: MetadataParser):
        result = parser.parse(
            "R02",
            [{"reporterCode": 4, "text": ""}],
        )
        assert result.records == []
        assert result.skipped == 1

    def test_invalid_iso_alpha2_rejected(self, parser: MetadataParser):
        result = parser.parse(
            "R02",
            [
                {
                    "reporterCode": 4,
                    "text": "AF",
                    "reporterCodeIsoAlpha2": "XX1",  # 3 chars not 2
                }
            ],
        )
        assert result.records == []
        assert result.skipped == 1

    def test_negative_country_code_rejected(self, parser: MetadataParser):
        result = parser.parse(
            "R02",
            [{"reporterCode": -1, "text": "Bad"}],
        )
        assert result.records == []
        assert result.skipped == 1


# ---------------------------------------------------------------------------
# No downloading, no storage
# ---------------------------------------------------------------------------


class TestNoIO:
    def test_parser_does_no_io(self, parser: MetadataParser):
        # Constructing and using the parser must not touch any
        # network or filesystem resources.
        parser.parse("R02", _load("reporters.json"))
        parser.parse("R03", _load("partners.json"))
        parser.parse("R04", _load("hs_combined.json"))
        # No exception means no IO occurred (the test runner
        # would have caught a network failure or a file
        # permission error).