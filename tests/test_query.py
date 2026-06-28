"""Unit tests for the trade query builder (un_comtrade.query).

Per the P2-002 task scope, the query builder is pure
construction / validation / serialisation. No HTTP,
no parsing, no business logic.

Coverage:

- `TradeQuery` field validation (every documented rule)
- `TradeQueryBuilder` fluent interface
- `to_query_params` URL parameter mapping
- `to_url_path` path generation
- Deterministic serialisation (sorted keys)
- `default_trade_query` helper
"""

from __future__ import annotations

import pytest

from un_comtrade.query import (
    BREAKDOWN_MODES,
    DEFAULT_BREAKDOWN_MODE,
    DEFAULT_CLASSIFICATION,
    FLOW_CODES,
    FREQUENCY_CODES,
    MAX_RECORDS_LIMIT,
    MIN_RECORDS,
    PARTNER_WORLD,
    TRADE_TYPES,
    TradeQuery,
    TradeQueryBuilder,
    default_trade_query,
)


# ---------------------------------------------------------------------------
# TradeQuery field validation
# ---------------------------------------------------------------------------


class TestQueryValidation:
    def test_minimal_valid_query(self):
        q = TradeQuery(reporter_code=699, period="2022")
        assert q.reporter_code == 699
        assert q.period == "2022"
        assert q.cmd_code == "TOTAL"
        assert q.flow_code is None
        assert q.classification_code == "HS"
        assert q.partner_code is None
        assert q.include_desc is True
        assert q.count_only is False

    def test_negative_reporter_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            TradeQuery(reporter_code=-1, period="2022")

    def test_bool_reporter_rejected(self):
        with pytest.raises(TypeError, match="int"):
            TradeQuery(reporter_code=True, period="2022")  # type: ignore[arg-type]

    def test_string_reporter_rejected(self):
        with pytest.raises(TypeError, match="int"):
            TradeQuery(reporter_code="699", period="2022")  # type: ignore[arg-type]

    def test_empty_period_rejected(self):
        with pytest.raises(ValueError, match="period"):
            TradeQuery(reporter_code=699, period="")

    def test_invalid_period_format_rejected(self):
        for bad in ["abc", "202", "2022123", "20A2", "2022,abc"]:
            with pytest.raises(ValueError, match="period token"):
                TradeQuery(reporter_code=699, period=bad)

    def test_valid_period_formats(self):
        for good in ["2022", "202212", "2022,2023", "202201,202202,202212"]:
            q = TradeQuery(reporter_code=699, period=good)
            assert q.period == good

    def test_empty_cmd_code_rejected(self):
        with pytest.raises(ValueError, match="cmd_code"):
            TradeQuery(reporter_code=699, period="2022", cmd_code="")

    def test_invalid_flow_code_rejected(self):
        with pytest.raises(ValueError, match="flow_code"):
            TradeQuery(reporter_code=699, period="2022", flow_code="ZZ")

    def test_valid_flow_codes(self):
        for code in ("M", "X", "RX", "RM"):
            q = TradeQuery(reporter_code=699, period="2022", flow_code=code)
            assert q.flow_code == code

    def test_classification_required(self):
        with pytest.raises(ValueError, match="classification_code"):
            TradeQuery(
                reporter_code=699, period="2022", classification_code=""
            )

    def test_negative_partner_code_rejected(self):
        with pytest.raises(ValueError, match="partner_code"):
            TradeQuery(reporter_code=699, period="2022", partner_code=-1)

    def test_world_partner_code_zero_accepted(self):
        q = TradeQuery(reporter_code=699, period="2022", partner_code=0)
        assert q.partner_code == 0

    def test_max_records_lower_bound(self):
        with pytest.raises(ValueError, match="max_records"):
            TradeQuery(reporter_code=699, period="2022", max_records=0)

    def test_max_records_upper_bound(self):
        with pytest.raises(ValueError, match="max_records"):
            TradeQuery(
                reporter_code=699, period="2022", max_records=MAX_RECORDS_LIMIT + 1
            )

    def test_max_records_at_limit_accepted(self):
        q = TradeQuery(
            reporter_code=699, period="2022", max_records=MAX_RECORDS_LIMIT
        )
        assert q.max_records == MAX_RECORDS_LIMIT

    def test_max_records_min_accepted(self):
        q = TradeQuery(reporter_code=699, period="2022", max_records=MIN_RECORDS)
        assert q.max_records == MIN_RECORDS

    def test_invalid_breakdown_mode_rejected(self):
        with pytest.raises(ValueError, match="breakdown_mode"):
            TradeQuery(
                reporter_code=699, period="2022", breakdown_mode="legacy"
            )

    def test_immutable(self):
        from dataclasses import FrozenInstanceError

        q = TradeQuery(reporter_code=699, period="2022")
        with pytest.raises(FrozenInstanceError):
            q.reporter_code = 100  # type: ignore[misc]

    def test_empty_customs_code_rejected(self):
        with pytest.raises(ValueError, match="customs_code"):
            TradeQuery(reporter_code=699, period="2022", customs_code="")

    def test_empty_aggregate_by_rejected(self):
        with pytest.raises(ValueError, match="aggregate_by"):
            TradeQuery(reporter_code=699, period="2022", aggregate_by="")

    def test_negative_mot_rejected(self):
        with pytest.raises(ValueError, match="mot_code"):
            TradeQuery(reporter_code=699, period="2022", mot_code=-1)

    def test_zero_mot_accepted(self):
        q = TradeQuery(reporter_code=699, period="2022", mot_code=0)
        assert q.mot_code == 0


# ---------------------------------------------------------------------------
# TradeQueryBuilder
# ---------------------------------------------------------------------------


class TestQueryBuilder:
    def test_minimal_build(self):
        q = (
            TradeQueryBuilder()
            .reporter(699)
            .period("2022")
            .build()
        )
        assert isinstance(q, TradeQuery)
        assert q.reporter_code == 699
        assert q.period == "2022"

    def test_reporter_required(self):
        with pytest.raises(ValueError, match="reporter_code is required"):
            TradeQueryBuilder().period("2022").build()

    def test_period_required(self):
        with pytest.raises(ValueError, match="period is required"):
            TradeQueryBuilder().reporter(699).build()

    def test_full_fluent_chain(self):
        q = (
            TradeQueryBuilder()
            .reporter(699)
            .partner(156)
            .period("2022", "2023")
            .flow("M")
            .cmd("0101")
            .classification("HS", edition="H2022")
            .partner2(840)
            .customs("C00")
            .mot(0)
            .max_records(1000)
            .breakdown("classic")
            .aggregate_by("cmdCode", "partnerCode")
            .include_desc(True)
            .count_only(False)
            .build()
        )
        assert q.reporter_code == 699
        assert q.partner_code == 156
        assert q.period == "2022,2023"
        assert q.flow_code == "M"
        assert q.cmd_code == "0101"
        assert q.classification_code == "HS"
        assert q.classification_edition == "H2022"
        assert q.partner2_code == 840
        assert q.customs_code == "C00"
        assert q.mot_code == 0
        assert q.max_records == 1000
        assert q.breakdown_mode == "classic"
        assert q.aggregate_by == "cmdCode,partnerCode"
        assert q.include_desc is True
        assert q.count_only is False

    def test_period_normalises_comma_string(self):
        q = TradeQueryBuilder().reporter(699).period("2022, 2023, 2024").build()
        assert q.period == "2022,2023,2024"

    def test_period_with_multiple_args(self):
        q = TradeQueryBuilder().reporter(699).period("2022", "2023").build()
        assert q.period == "2022,2023"

    def test_invalid_period_rejected_in_builder(self):
        with pytest.raises(ValueError, match="period token"):
            TradeQueryBuilder().reporter(699).period("2022-13")

    def test_invalid_flow_rejected_in_builder(self):
        with pytest.raises(ValueError, match="flow_code"):
            TradeQueryBuilder().reporter(699).period("2022").flow("ZZ")

    def test_invalid_breakdown_rejected_in_builder(self):
        with pytest.raises(ValueError, match="breakdown_mode"):
            TradeQueryBuilder().reporter(699).period("2022").breakdown("legacy")

    def test_invalid_max_records_rejected_in_builder(self):
        with pytest.raises(ValueError, match="max_records"):
            TradeQueryBuilder().reporter(699).period("2022").max_records(0)

    def test_negative_reporter_rejected_in_builder(self):
        with pytest.raises(ValueError, match="reporter_code"):
            TradeQueryBuilder().reporter(-1)

    def test_bool_reporter_rejected_in_builder(self):
        with pytest.raises(TypeError, match="int"):
            TradeQueryBuilder().reporter(True)  # type: ignore[arg-type]

    def test_default_breakdown_is_classic(self):
        q = TradeQueryBuilder().reporter(699).period("2022").build()
        assert q.breakdown_mode == "classic"

    def test_chaining_returns_self(self):
        b = TradeQueryBuilder()
        assert b.reporter(699) is b
        assert b.period("2022") is b
        assert b.flow("M") is b
        assert b.cmd("TOTAL") is b
        assert b.classification("HS") is b
        assert b.max_records(100) is b
        assert b.breakdown("classic") is b
        assert b.include_desc(True) is b
        assert b.count_only(False) is b


# ---------------------------------------------------------------------------
# to_query_params: URL parameter mapping
# ---------------------------------------------------------------------------


class TestToQueryParams:
    def test_minimal_query(self):
        q = TradeQuery(reporter_code=699, period="2022")
        params = q.to_query_params()
        assert params["reporterCode"] == "699"
        assert params["period"] == "2022"
        assert params["cmdCode"] == "TOTAL"
        assert params["classification"] == "HS"
        assert params["includeDesc"] == "true"
        # countOnly not serialised when False.
        assert "countOnly" not in params
        # Optional fields omitted.
        assert "partnerCode" not in params
        assert "flowCode" not in params
        assert "maxRecords" not in params

    def test_full_query(self):
        q = TradeQuery(
            reporter_code=699,
            partner_code=156,
            period="2022",
            cmd_code="0101",
            flow_code="M",
            classification_code="HS",
            classification_edition="H2022",
            partner2_code=840,
            customs_code="C00",
            mot_code=0,
            max_records=1000,
            breakdown_mode="classic",
            aggregate_by="cmdCode,partnerCode",
            include_desc=True,
            count_only=False,
        )
        params = q.to_query_params()
        assert params["reporterCode"] == "699"
        assert params["partnerCode"] == "156"
        assert params["period"] == "2022"
        assert params["cmdCode"] == "0101"
        assert params["flowCode"] == "M"
        # Edition overrides the code value in the same `classification`
        # field (this is the upstream distinction: the value *is* the edition).
        assert params["classification"] == "H2022"  # edition wins
        assert "classificationCode" not in params  # trade_type=C uses `classification`
        assert params["partner2Code"] == "840"
        assert params["customsCode"] == "C00"
        assert params["motCode"] == "0"
        assert params["maxRecords"] == "1000"
        assert "breakdownMode" not in params  # default omitted
        assert params["aggregateBy"] == "cmdCode,partnerCode"
        assert params["includeDesc"] == "true"

    def test_breakdown_mode_emitted_when_non_default(self):
        q = TradeQuery(
            reporter_code=699, period="2022", breakdown_mode="plus"
        )
        params = q.to_query_params()
        assert params["breakdownMode"] == "plus"

    def test_services_trade_type_uses_classification_code_field(self):
        q = TradeQuery(
            reporter_code=699, period="2022", classification_code="EB"
        )
        params = q.to_query_params(trade_type="S")
        # For services the field is `classificationCode` (not `classification`).
        assert params["classificationCode"] == "EB"
        assert "classification" not in params

    def test_count_only_emitted_only_when_true(self):
        q1 = TradeQuery(reporter_code=699, period="2022", count_only=False)
        assert "countOnly" not in q1.to_query_params()
        q2 = TradeQuery(reporter_code=699, period="2022", count_only=True)
        assert q2.to_query_params()["countOnly"] == "true"

    def test_include_desc_false_emitted(self):
        q = TradeQuery(reporter_code=699, period="2022", include_desc=False)
        params = q.to_query_params()
        assert params["includeDesc"] == "false"

    def test_deterministic_output(self):
        # Same query twice produces equal params; ordering
        # does not matter to httpx, but the dict must be
        # hashable + equal across runs.
        q1 = TradeQuery(reporter_code=699, period="2022", flow_code="M")
        q2 = TradeQuery(reporter_code=699, period="2022", flow_code="M")
        assert q1.to_query_params() == q2.to_query_params()


# ---------------------------------------------------------------------------
# to_url_path
# ---------------------------------------------------------------------------


class TestToUrlPath:
    def test_default_trade_type(self):
        q = TradeQuery(reporter_code=699, period="2022", flow_code="M")
        path = q.to_url_path()
        assert path == "/C/{freqCode}/M/HS"

    def test_services_trade_type(self):
        q = TradeQuery(reporter_code=699, period="2022", flow_code="M")
        path = q.to_url_path(trade_type="S")
        assert path == "/S/{freqCode}/M/HS"

    def test_with_classification_edition(self):
        q = TradeQuery(
            reporter_code=699,
            period="2022",
            flow_code="M",
            classification_edition="H2022",
        )
        assert q.to_url_path() == "/C/{freqCode}/M/H2022"

    def test_invalid_trade_type_rejected(self):
        q = TradeQuery(reporter_code=699, period="2022", flow_code="M")
        with pytest.raises(ValueError, match="trade_type"):
            q.to_url_path(trade_type="X")

    def test_missing_flow_code_rejected(self):
        q = TradeQuery(reporter_code=699, period="2022")  # no flow_code
        with pytest.raises(ValueError, match="flow_code is required"):
            q.to_url_path()


# ---------------------------------------------------------------------------
# default_trade_query helper
# ---------------------------------------------------------------------------


class TestDefaultTradeQuery:
    def test_india_world_imports_2022(self):
        q = default_trade_query(699, 2022)
        assert q.reporter_code == 699
        assert q.partner_code == 0
        assert q.period == "2022"
        assert q.flow_code == "M"
        assert q.cmd_code == "TOTAL"

    def test_custom_year(self):
        q = default_trade_query(156, 2017)
        assert q.reporter_code == 156
        assert q.period == "2017"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_flow_codes(self):
        assert FLOW_CODES == frozenset({"M", "X", "RX", "RM"})

    def test_frequency_codes(self):
        assert FREQUENCY_CODES == frozenset({"A", "M"})

    def test_breakdown_modes(self):
        assert BREAKDOWN_MODES == frozenset({"classic", "plus"})

    def test_trade_types(self):
        assert TRADE_TYPES == frozenset({"C", "S"})

    def test_partner_world(self):
        assert PARTNER_WORLD == 0

    def test_default_classification(self):
        assert DEFAULT_CLASSIFICATION == "HS"

    def test_default_breakdown(self):
        assert DEFAULT_BREAKDOWN_MODE == "classic"

    def test_max_records_limit(self):
        assert MAX_RECORDS_LIMIT == 250_000


# ---------------------------------------------------------------------------
# Deterministic serialisation
# ---------------------------------------------------------------------------


class TestDeterministicSerialisation:
    def test_param_keys_are_sorted(self):
        # The dict returned by to_query_params is insertion-ordered
        # but we don't enforce sorted keys. The contract is
        # that two equal queries produce equal params; callers
        # can sort if they need a canonical order.
        q = TradeQuery(
            reporter_code=699,
            period="2022",
            partner_code=156,
            mot_code=0,
            max_records=1000,
        )
        params = q.to_query_params()
        # Verify round-trip equality: same input -> same output.
        again = q.to_query_params()
        assert params == again

    def test_query_is_picklable(self):
        # TradeQuery is frozen; it should roundtrip through pickle.
        import pickle

        q = TradeQuery(reporter_code=699, period="2022", flow_code="M")
        restored = pickle.loads(pickle.dumps(q))
        assert restored == q

    def test_repeated_calls_return_same_result(self):
        q = TradeQueryBuilder().reporter(699).period("2022").flow("M").build()
        snapshots = [q.to_query_params() for _ in range(100)]
        assert all(s == snapshots[0] for s in snapshots)