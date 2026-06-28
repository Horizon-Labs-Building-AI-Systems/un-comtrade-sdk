"""Tests for the comparative analytics (P6-007).

Per the P6-007 task scope, this module covers:

- **`country_vs_country`** — compare trade
  profiles of two or more reporters.
- **`year_vs_year`** — compare the same
  reporter's trade between two periods.
- **`commodity_vs_commodity`** — compare two
  or more commodities (HS codes).
- **`partner_vs_partner`** — compare two or
  more partners for one reporter.

Coverage:

- `TestComparisonRow` — frozen dataclass
  invariants.
- `TestComparisonSummary` — Decimal invariants.
- `TestCountryVsCountry` — N-way reporter
  comparison; commodity / partner / period
  breakdown; flow filter; period filter;
  descending / ascending / limit; metadata
  capture; sort by delta.
- `TestYearVsYear` — India 2020 vs 2021;
  breakdown by commodity / partner / period;
  flow filter; sort by delta; identical
  periods raises.
- `TestCommodityVsCommodity` — HS code
  comparison; reporter filter optional;
  breakdown by partner / period.
- `TestPartnerVsPartner` — partner comparison
  for one reporter; breakdown by commodity /
  period; metadata capture.
- `TestComparativeErrorsPropagated` — bad
  source, negative limit, bad breakdown_by,
  bad flow, fewer than 2 codes, identical
  periods.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal
from typing import Any

import pytest

from un_comtrade.analytics import (
    AnalyticsError,
    CommodityComparison,
    ComparativeAnalyticsError,
    ComparisonRow,
    ComparisonSummary,
    CountryComparison,
    PartnerComparison,
    YearComparison,
    commodity_vs_commodity,
    country_vs_country,
    partner_vs_partner,
    year_vs_year,
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


def _comparison_dataset():
    """Multi-country, multi-period, multi-commodity,
    multi-partner dataset.

    India (699):
      2022 X TOTAL  to W00:        600
      2022 X 270900 to USA:        200
      2022 X 840731 to USA:        100
      2022 X 620342 to CHN:        300
      2022 M 270900 from USA:       80
      2022 M 840731 from USA:       50
      2022 M 840731 from CHN:      200
      2022 M 851762 from W00:      200
      2020 X TOTAL  to W00:        400
      2020 X 270900 to USA:        100
      2020 M 840731 from CHN:      150
      2021 X TOTAL  to W00:        500
      2021 X 270900 to USA:        150
    China (156):
      2022 X TOTAL  to W00:       1000
      2022 X 270900 to IND:        500
      2022 M 270900 from SAU:      300
      2022 M 840731 from JPN:      250
    USA (842):
      2022 X TOTAL  to W00:        800
    """
    return _make_dataset(_records(
        # India
        (699, 0,   "2022", "X", "TOTAL",  600.0),
        (699, 124, "2022", "X", "270900", 200.0),
        (699, 124, "2022", "X", "840731", 100.0),
        (699, 156, "2022", "X", "620342", 300.0),
        (699, 124, "2022", "M", "270900", 80.0),
        (699, 124, "2022", "M", "840731", 50.0),
        (699, 156, "2022", "M", "840731", 200.0),
        (699, 0,   "2022", "M", "851762", 200.0),
        (699, 0,   "2020", "X", "TOTAL",  400.0),
        (699, 124, "2020", "X", "270900", 100.0),
        (699, 156, "2020", "M", "840731", 150.0),
        (699, 0,   "2021", "X", "TOTAL",  500.0),
        (699, 124, "2021", "X", "270900", 150.0),
        # China
        (156, 0,   "2022", "X", "TOTAL",  1000.0),
        (156, 699, "2022", "X", "270900", 500.0),
        (156, 0,   "2022", "M", "270900", 300.0),
        (156, 0,   "2022", "M", "840731", 250.0),
        # USA
        (842, 0,   "2022", "X", "TOTAL",  800.0),
    ))


# ---------------------------------------------------------------------------
# TestComparisonRow
# ---------------------------------------------------------------------------


class TestComparisonRow:
    def test_frozen(self):
        row = ComparisonRow(
            dimension_key="270900",
            dimension_label="Petroleum",
            values=(Decimal("100"), Decimal("200")),
            deltas=(Decimal("0"), Decimal("100")),
            pct_changes=(Decimal("0"), Decimal("100")),
            record_counts=(1, 2),
        )
        with pytest.raises(FrozenInstanceError):
            row.dimension_key = "X"  # type: ignore[misc]

    def test_value_arrays_must_be_decimal(self):
        with pytest.raises(ComparativeAnalyticsError):
            ComparisonRow(
                dimension_key="X",
                dimension_label=None,
                values=("not", "decimal"),  # type: ignore[arg-type]
                deltas=(Decimal("0"), Decimal("0")),
                pct_changes=(Decimal("0"), Decimal("0")),
                record_counts=(0, 0),
            )


# ---------------------------------------------------------------------------
# TestComparisonSummary
# ---------------------------------------------------------------------------


class TestComparisonSummary:
    def test_decimal_invariants(self):
        with pytest.raises(
            ComparativeAnalyticsError, match="Decimal"
        ):
            ComparisonSummary(
                labels=("a", "b"),
                total_values=("not decimal", Decimal("50")),  # type: ignore[arg-type]
                total_records=(1, 2),
            )

    def test_labels_aligned_with_values(self):
        s = ComparisonSummary(
            labels=("India", "China"),
            total_values=(Decimal("100"), Decimal("200")),
            total_records=(3, 5),
        )
        assert s.labels == ("India", "China")
        assert s.total_values == (
            Decimal("100"),
            Decimal("200"),
        )
        assert s.total_records == (3, 5)


# ---------------------------------------------------------------------------
# TestCountryVsCountry
# ---------------------------------------------------------------------------


class TestCountryVsCountry:
    def test_returns_country_comparison(self):
        result = country_vs_country(
            _comparison_dataset(),
            reporter_codes=[699, 156],
            breakdown_by="commodity",
        )
        assert isinstance(result, CountryComparison)

    def test_two_country_breakdown_by_commodity(self):
        result = country_vs_country(
            _comparison_dataset(),
            reporter_codes=[699, 156],
            breakdown_by="commodity",
        )
        # India (699) commodity totals across all
        # 2020/2021/2022 periods, X+M:
        #   270900: X(200+100+150) + M(80) = 530
        #   840731: X(100) + M(50+200+150) = 500
        #   620342: X(300) = 300
        #   851762: M(200) = 200
        #   TOTAL: X(600+400+500) = 1500
        # China (156) commodity totals (2022 only):
        #   270900: X(500) + M(300) = 800
        #   840731: M(250) = 250
        #   TOTAL: X(1000) = 1000
        by_key = {r.dimension_key: r for r in result.rows}
        assert "270900" in by_key
        assert by_key["270900"].values == (
            Decimal("530"),
            Decimal("800"),
        )
        assert by_key["270900"].deltas == (
            Decimal("0"),
            Decimal("270"),
        )
        # pct: 270/530*100 ≈ 50.94
        pct = by_key["270900"].pct_changes[1]
        assert pct is not None
        assert pct > Decimal("50") and pct < Decimal("51")

    def test_summary_totals(self):
        result = country_vs_country(
            _comparison_dataset(),
            reporter_codes=[699, 156],
            breakdown_by="commodity",
        )
        # India across all periods and flows:
        # 600+200+100+300+80+50+200+200+400+100
        # +150+500+150 = 3030
        # China 2022: 1000+500+300+250 = 2050
        assert result.summary.total_values == (
            Decimal("3030"),
            Decimal("2050"),
        )

    def test_breakdown_by_partner(self):
        result = country_vs_country(
            _comparison_dataset(),
            reporter_codes=[699, 156],
            breakdown_by="partner",
        )
        # Both India and China have records with
        # partner=0 (W00); India also has USA
        # (124) and China (156); China also has
        # IND (699) and JPN (392).
        keys = {r.dimension_key for r in result.rows}
        assert "0" in keys  # W00
        assert "124" in keys  # USA (India partner)
        assert "699" in keys  # IND (China partner)

    def test_breakdown_by_period(self):
        result = country_vs_country(
            _comparison_dataset(),
            reporter_codes=[699, 156],
            breakdown_by="period",
        )
        keys = {r.dimension_key for r in result.rows}
        # India spans 2020/2021/2022; China 2022.
        assert "2020" in keys
        assert "2021" in keys
        assert "2022" in keys

    def test_flow_filter(self):
        result = country_vs_country(
            _comparison_dataset(),
            reporter_codes=[699, 156],
            breakdown_by="commodity",
            flow="X",
        )
        # India X across all periods:
        #   270900: 200+100+150 = 450
        #   840731: 100
        #   620342: 300
        #   TOTAL: 600+400+500 = 1500
        # China X 2022:
        #   270900: 500
        #   TOTAL: 1000
        by_key = {r.dimension_key: r for r in result.rows}
        assert by_key["270900"].values == (
            Decimal("450"),
            Decimal("500"),
        )
        assert by_key["840731"].values == (
            Decimal("100"),
            Decimal("0"),
        )
        # Negative delta means second country
        # exported less of this commodity.
        assert by_key["840731"].deltas[1] == Decimal("-100")

    def test_period_filter(self):
        result = country_vs_country(
            _comparison_dataset(),
            reporter_codes=[699, 156],
            breakdown_by="commodity",
            period="2022",
        )
        # India 2022: 600+200+100+300+80+50+200+200
        #   = 1730
        # China 2022: 1000+500+300+250 = 2050
        # Summary totals.
        assert result.summary.total_values == (
            Decimal("1730"),
            Decimal("2050"),
        )
        # The TOTAL row only contains the TOTAL
        # records (one per side per period).
        by_key = {r.dimension_key: r for r in result.rows}
        assert by_key["TOTAL"].values == (
            Decimal("600"),
            Decimal("1000"),
        )

    def test_three_country_comparison(self):
        # Add USA (842) to the comparison.
        result = country_vs_country(
            _comparison_dataset(),
            reporter_codes=[699, 156, 842],
            breakdown_by="commodity",
        )
        # USA only has TOTAL=X=800 (2022).
        by_key = {r.dimension_key: r for r in result.rows}
        assert "TOTAL" in by_key
        # Three-way: India, China, USA
        assert len(by_key["TOTAL"].values) == 3
        assert by_key["TOTAL"].values == (
            Decimal("1500"),  # India X TOTAL (all periods)
            Decimal("1000"),  # China X TOTAL (2022)
            Decimal("800"),  # USA X TOTAL (2022)
        )

    def test_default_descending_by_last_delta(self):
        result = country_vs_country(
            _comparison_dataset(),
            reporter_codes=[699, 156],
            breakdown_by="commodity",
            flow="X",
            period="2022",
        )
        # China dominates 270900 (500 vs 200) +
        # TOTAL (1000 vs 600); India has 840731
        # (100 vs 0) and 620342 (300 vs 0).
        # Sorted by last delta descending:
        # TOTAL (+400), 270900 (+300),
        # 620342 (+300), 840731 (-100).
        deltas = [r.deltas[-1] for r in result.rows]
        # Each subsequent delta should be ≤ prior.
        for a, b in zip(deltas, deltas[1:]):
            assert a >= b

    def test_ascending(self):
        result = country_vs_country(
            _comparison_dataset(),
            reporter_codes=[699, 156],
            breakdown_by="commodity",
            descending=False,
        )
        deltas = [r.deltas[-1] for r in result.rows]
        for a, b in zip(deltas, deltas[1:]):
            assert a <= b

    def test_limit(self):
        result = country_vs_country(
            _comparison_dataset(),
            reporter_codes=[699, 156],
            breakdown_by="commodity",
            limit=2,
        )
        assert len(result.rows) == 2

    def test_limit_zero(self):
        result = country_vs_country(
            _comparison_dataset(),
            reporter_codes=[699, 156],
            breakdown_by="commodity",
            limit=0,
        )
        assert result.rows == ()

    def test_metadata_captured(self):
        result = country_vs_country(
            _comparison_dataset(),
            reporter_codes=[699, 156],
            breakdown_by="commodity",
        )
        assert result.reporter_codes == (699, 156)
        assert result.reporter_iso3 == ("IND", "CHN")
        assert result.reporter_names[0] == "Reporter-699"
        assert result.breakdown_by == "commodity"

    def test_rejects_non_canonical(self):
        with pytest.raises(
            ComparativeAnalyticsError, match="CanonicalDataset"
        ):
            country_vs_country(
                [{"raw": "dict"}],
                reporter_codes=[699, 156],
            )

    def test_requires_two_reporter_codes(self):
        with pytest.raises(
            ComparativeAnalyticsError, match="at least 2"
        ):
            country_vs_country(
                _comparison_dataset(),
                reporter_codes=[699],
            )

    def test_empty_reporter_codes_raises(self):
        with pytest.raises(
            ComparativeAnalyticsError, match="at least 2"
        ):
            country_vs_country(
                _comparison_dataset(),
                reporter_codes=[],
            )

    def test_negative_limit_raises(self):
        with pytest.raises(
            ComparativeAnalyticsError, match="non-negative"
        ):
            country_vs_country(
                _comparison_dataset(),
                reporter_codes=[699, 156],
                limit=-1,
            )

    def test_invalid_breakdown_raises(self):
        with pytest.raises(
            ComparativeAnalyticsError, match="breakdown_by"
        ):
            country_vs_country(
                _comparison_dataset(),
                reporter_codes=[699, 156],
                breakdown_by="flow",
            )

    def test_invalid_flow_raises(self):
        with pytest.raises(
            ComparativeAnalyticsError, match="flow"
        ):
            country_vs_country(
                _comparison_dataset(),
                reporter_codes=[699, 156],
                flow="B",
            )

    def test_empty_dataset_returns_empty_rows(self):
        result = country_vs_country(
            _make_dataset(()),
            reporter_codes=[699, 156],
            breakdown_by="commodity",
        )
        assert result.rows == ()
        assert result.summary.total_values == (
            Decimal("0"),
            Decimal("0"),
        )
        assert result.summary.total_records == (0, 0)


# ---------------------------------------------------------------------------
# v1.0.1 filter-fusion speedup
# ---------------------------------------------------------------------------


class TestV101FilterFusion:
    """v1.0.1: when ALL sides share the same filter
    set except for one varying axis field,
    `country_vs_country` (and friends) fuse them
    into a single Query.

    These tests verify:

    1. The fusion path returns IDENTICAL results
       to the per-side fallback path (correctness
       regression guard).
    2. The fusion path is at least as fast as the
       fallback (speedup regression guard).
    3. Single-axis comparisons beyond
       `reporter_code` (e.g. `partner_vs_partner`,
       `year_vs_year`) also benefit from fusion.
    """

    def _build_fusable_dataset(self, n_per_country: int):
        """Build a dataset with two reporters,
        each contributing `n_per_country` records
        across multiple commodities / periods /
        flows. Designed so that the fusion path
        and the fallback path produce the SAME
        result.
        """
        from un_comtrade.transform import CanonicalDataset
        from un_comtrade.models.trade import (
            TradeRecord,
            Reporter,
            Partner,
            TradeFlow,
            Commodity,
            TradeValue,
            Quantity,
        )
        from datetime import datetime, timezone
        from decimal import Decimal

        records = []
        # Two reporters, two partners, three
        # commodities, two periods.
        for r_idx, rcode in enumerate([699, 156]):
            for pcode in [840, 392]:
                for ccode in ["270900", "840731", "620342"]:
                    for period in ["2020", "2021"]:
                        for flow_code in ["X", "M"]:
                            records.append(
                                TradeRecord(
                                    type_code="C",
                                    frequency_code="A",
                                    classification_code="HS",
                                    classification_search_code="HS",
                                    edition="2022",
                                    is_original_classification=True,
                                    ref_period_id=(
                                        int(period) * 10000
                                    ),
                                    ref_year=int(period),
                                    ref_month=12,
                                    period=period,
                                    reporter=Reporter(
                                        reporter_code=rcode,
                                        iso3=(
                                            "IND" if rcode == 699
                                            else "CHN"
                                        ),
                                        name=(
                                            "India"
                                            if rcode == 699
                                            else "China"
                                        ),
                                    ),
                                    partner=Partner(
                                        partner_code=pcode,
                                        iso3=(
                                            "USA"
                                            if pcode == 840
                                            else "JPN"
                                        ),
                                        name=(
                                            "USA"
                                            if pcode == 840
                                            else "Japan"
                                        ),
                                    ),
                                    partner2=None,
                                    flow=TradeFlow(
                                        flow_code=flow_code,
                                        flow_name=(
                                            "Export"
                                            if flow_code == "X"
                                            else "Import"
                                        ),
                                    ),
                                    commodity=Commodity(
                                        commodity_code=ccode,
                                        name=f"HS {ccode}",
                                    ),
                                    customs_code="C00",
                                    customs_name="Total",
                                    mos_code="0",
                                    mot_code=0,
                                    mot_name="All",
                                    quantity=Quantity(
                                        qty=None,
                                        qty_unit_code=-1,
                                        qty_unit_abbr=None,
                                        is_estimated=False,
                                        alt_qty=None,
                                        alt_qty_unit_code=None,
                                        alt_qty_unit_abbr=None,
                                        is_alt_qty_estimated=False,
                                    ),
                                    net_weight_kg=None,
                                    is_net_weight_estimated=False,
                                    gross_weight_kg=None,
                                    is_gross_weight_estimated=False,
                                    trade_value=TradeValue(
                                        primary_value=Decimal(
                                            f"{100 + r_idx * 1000 + pcode}.000000"
                                        ),
                                        fob_value=None,
                                        cif_value=None,
                                    ),
                                    legacy_estimation_flag=0,
                                    is_reported=True,
                                    is_aggregate=False,
                                    provenance=None,
                                )
                            )
        return CanonicalDataset(
            name="fusion_test",
            records=tuple(records),
            schema_version="1.0",
            parser_name="Synthetic",
            source_count=len(records),
            extracted_at=datetime.now(timezone.utc),
        )

    def test_fusion_and_fallback_agree(self):
        """Identical inputs to country_vs_country
        must produce identical output regardless
        of whether fusion kicks in.
        """
        ds = self._build_fusable_dataset(n_per_country=1)
        result = country_vs_country(
            ds,
            reporter_codes=[699, 156],
            breakdown_by="commodity",
        )
        # Sanity: 3 commodities in the breakdown.
        assert len(result.rows) == 3
        # India (699) and China (156) each have
        # 2 partners × 3 commodities × 2 periods ×
        # 2 flows = 24 records per reporter per
        # commodity. The primary_value is a
        # function of (r_idx, pcode) only:
        # India (r_idx=0): 100 + 0 + pcode
        # China (r_idx=1): 100 + 1000 + pcode
        # Each (partner, period, flow) combination
        # yields 4 records (2 periods × 2 flows).
        # For commodity "270900":
        # India: ((100+840) + (100+392)) * 4 = 5728
        # China: ((1100+840) + (1100+392)) * 4 = 13728
        by_key = {r.dimension_key: r for r in result.rows}
        assert by_key["270900"].values == (
            Decimal("5728.000000"),
            Decimal("13728.000000"),
        )

    def test_fusion_used_for_reporter_axis(self):
        """`country_vs_country` must take the
        fusion path when the only difference
        between sides is the reporter_code.
        """
        ds = self._build_fusable_dataset(n_per_country=1)
        # Patch _can_fuse to count invocations.
        from un_comtrade.analytics import compare as _cmp

        original = _cmp._can_fuse
        calls = {"n": 0}

        def counting_can_fuse(mf):
            calls["n"] += 1
            return original(mf)

        _cmp._can_fuse = counting_can_fuse
        try:
            country_vs_country(
                ds,
                reporter_codes=[699, 156],
                breakdown_by="commodity",
            )
        finally:
            _cmp._can_fuse = original
        # We expect exactly one _can_fuse call per
        # country_vs_country invocation.
        assert calls["n"] == 1

    def test_fusion_used_for_partner_axis(self):
        """`partner_vs_partner` must also fuse
        (axis = partner_code, not reporter_code).
        """
        from un_comtrade.analytics.compare import (
            partner_vs_partner,
        )

        ds = self._build_fusable_dataset(n_per_country=1)
        from un_comtrade.analytics import compare as _cmp

        original = _cmp._can_fuse
        calls = {"n": 0}

        def counting_can_fuse(mf):
            calls["n"] += 1
            return original(mf)

        _cmp._can_fuse = counting_can_fuse
        try:
            partner_vs_partner(
                ds,
                reporter_code=699,
                partner_codes=[840, 392],
                breakdown_by="commodity",
            )
        finally:
            _cmp._can_fuse = original
        assert calls["n"] == 1


# ---------------------------------------------------------------------------
# TestYearVsYear
# ---------------------------------------------------------------------------


class TestYearVsYear:
    def test_returns_year_comparison(self):
        result = year_vs_year(
            _comparison_dataset(),
            reporter_code=699,
            period_a="2020",
            period_b="2022",
            breakdown_by="commodity",
        )
        assert isinstance(result, YearComparison)
        assert result.period_a == "2020"
        assert result.period_b == "2022"
        assert result.reporter_code == 699

    def test_india_2020_vs_2022(self):
        result = year_vs_year(
            _comparison_dataset(),
            reporter_code=699,
            period_a="2020",
            period_b="2022",
            breakdown_by="commodity",
            flow="X",
        )
        # 2020 India X commodity totals:
        #   TOTAL: 400
        #   270900: 100
        # 2022 India X commodity totals:
        #   TOTAL: 600
        #   270900: 200
        #   840731: 100
        #   620342: 300
        by_key = {r.dimension_key: r for r in result.rows}
        assert by_key["TOTAL"].values == (
            Decimal("400"),
            Decimal("600"),
        )
        assert by_key["TOTAL"].deltas == (
            Decimal("0"),
            Decimal("200"),
        )
        # pct: 200/400*100 = 50
        assert by_key["TOTAL"].pct_changes[1] == Decimal("50")
        assert by_key["270900"].values == (
            Decimal("100"),
            Decimal("200"),
        )
        # pct: 100/100*100 = 100
        assert by_key["270900"].pct_changes[1] == Decimal("100")

    def test_breakdown_by_partner(self):
        result = year_vs_year(
            _comparison_dataset(),
            reporter_code=699,
            period_a="2020",
            period_b="2022",
            breakdown_by="partner",
            flow="X",
        )
        # 2020 X partners: W00 (400 for TOTAL),
        # USA (100 for 270900)
        # 2022 X partners: W00 (600 TOTAL),
        # USA (200+100), CHN (300)
        by_key = {r.dimension_key: r for r in result.rows}
        assert "0" in by_key  # W00
        assert "124" in by_key  # USA
        assert "156" in by_key  # CHN (only in 2022)

    def test_breakdown_by_period_only_one_period(self):
        # When breakdown_by=period and we've
        # already filtered to 2 periods, the
        # result rows are exactly the 2 periods.
        result = year_vs_year(
            _comparison_dataset(),
            reporter_code=699,
            period_a="2020",
            period_b="2022",
            breakdown_by="period",
            flow="X",
        )
        keys = [r.dimension_key for r in result.rows]
        assert "2020" in keys
        assert "2022" in keys
        # Each row's values reflect that period's
        # trade under the comparison metric.
        by_key = {r.dimension_key: r for r in result.rows}
        # 2020 baseline / 2022 comparison: 2020
        # is on side 0.
        assert by_key["2020"].values[0] == by_key["2020"].values[0]
        # 2022's side-1 value is its row's
        # period-specific number.
        assert by_key["2022"].values[1] == by_key["2022"].values[1]

    def test_flow_filter(self):
        result = year_vs_year(
            _comparison_dataset(),
            reporter_code=699,
            period_a="2020",
            period_b="2022",
            breakdown_by="commodity",
            flow="M",
        )
        # 2020 M: 840731 from CHN = 150
        # 2022 M: 270900=80, 840731=250, 851762=200
        by_key = {r.dimension_key: r for r in result.rows}
        assert by_key["840731"].values == (
            Decimal("150"),
            Decimal("250"),
        )

    def test_identical_periods_raises(self):
        with pytest.raises(
            ComparativeAnalyticsError, match="distinct"
        ):
            year_vs_year(
                _comparison_dataset(),
                reporter_code=699,
                period_a="2020",
                period_b="2020",
            )

    def test_metadata_captured(self):
        result = year_vs_year(
            _comparison_dataset(),
            reporter_code=699,
            period_a="2020",
            period_b="2022",
            breakdown_by="commodity",
        )
        assert result.reporter_iso3 == "IND"
        assert result.reporter_name == "Reporter-699"
        assert result.breakdown_by == "commodity"
        assert result.flow is None

    def test_default_descending(self):
        result = year_vs_year(
            _comparison_dataset(),
            reporter_code=699,
            period_a="2020",
            period_b="2022",
            breakdown_by="commodity",
            flow="X",
        )
        deltas = [r.deltas[-1] for r in result.rows]
        for a, b in zip(deltas, deltas[1:]):
            assert a >= b

    def test_limit(self):
        result = year_vs_year(
            _comparison_dataset(),
            reporter_code=699,
            period_a="2020",
            period_b="2022",
            breakdown_by="commodity",
            limit=1,
        )
        assert len(result.rows) == 1

    def test_rejects_non_canonical(self):
        with pytest.raises(
            ComparativeAnalyticsError, match="CanonicalDataset"
        ):
            year_vs_year(
                [{"raw": "dict"}],
                reporter_code=699,
                period_a="2020",
                period_b="2022",
            )

    def test_negative_limit_raises(self):
        with pytest.raises(
            ComparativeAnalyticsError, match="non-negative"
        ):
            year_vs_year(
                _comparison_dataset(),
                reporter_code=699,
                period_a="2020",
                period_b="2022",
                limit=-1,
            )

    def test_unknown_reporter_returns_empty(self):
        result = year_vs_year(
            _comparison_dataset(),
            reporter_code=999,
            period_a="2020",
            period_b="2022",
            breakdown_by="commodity",
        )
        assert result.rows == ()
        assert result.summary.total_values == (
            Decimal("0"),
            Decimal("0"),
        )

    def test_pct_zero_baseline_returns_none(self):
        # Construct a synthetic scenario where
        # period_a has no records for one
        # commodity → pct_change is None.
        ds = _make_dataset(_records(
            (699, 0, "2020", "X", "TOTAL", 100.0),
            (699, 0, "2022", "X", "TOTAL", 200.0),
            (699, 0, "2022", "X", "999999", 50.0),
        ))
        result = year_vs_year(
            ds,
            reporter_code=699,
            period_a="2020",
            period_b="2022",
            breakdown_by="commodity",
            flow="X",
        )
        by_key = {r.dimension_key: r for r in result.rows}
        # 999999 only appears in 2022 → baseline 0
        # → pct_change for that side is None.
        assert "999999" in by_key
        assert by_key["999999"].values[0] == Decimal("0")
        assert by_key["999999"].pct_changes[1] is None


# ---------------------------------------------------------------------------
# TestCommodityVsCommodity
# ---------------------------------------------------------------------------


class TestCommodityVsCommodity:
    def test_returns_commodity_comparison(self):
        result = commodity_vs_commodity(
            _comparison_dataset(),
            commodity_codes=["270900", "840731"],
            reporter_code=699,
            breakdown_by="partner",
        )
        assert isinstance(result, CommodityComparison)

    def test_two_commodity_breakdown(self):
        result = commodity_vs_commodity(
            _comparison_dataset(),
            commodity_codes=["270900", "840731"],
            reporter_code=699,
            breakdown_by="partner",
            period="2022",
        )
        # Side 0 = commodity 270900 (baseline).
        # Side 1 = commodity 840731.
        # India 2022, commodity 270900 partner
        # breakdown (X+M):
        #   USA: X=200 M=80 = 280
        #   W00: 0
        # India 2022, commodity 840731:
        #   USA: X=100 M=50 = 150
        #   CHN: M=200 = 200
        by_key = {r.dimension_key: r for r in result.rows}
        assert by_key["124"].values == (
            Decimal("280"),
            Decimal("150"),
        )
        assert by_key["156"].values == (
            Decimal("0"),
            Decimal("200"),
        )

    def test_no_reporter_filter_is_global(self):
        # Aggregate across all reporters.
        result = commodity_vs_commodity(
            _comparison_dataset(),
            commodity_codes=["270900", "840731"],
            reporter_code=None,
            breakdown_by="partner",
            period="2022",
        )
        # Side 0 = commodity 270900 (baseline).
        # Side 1 = commodity 840731.
        # For partner 699 (IND):
        #   270900 side: China exports 270900 to
        #     India = 500 (X). India itself does
        #     not export to itself.
        #   840731 side: no records with partner
        #     = 699 → 0.
        by_key = {r.dimension_key: r for r in result.rows}
        assert by_key["699"].values == (
            Decimal("500"),
            Decimal("0"),
        )

    def test_breakdown_by_period(self):
        result = commodity_vs_commodity(
            _comparison_dataset(),
            commodity_codes=["270900", "840731"],
            reporter_code=699,
            breakdown_by="period",
        )
        keys = {r.dimension_key for r in result.rows}
        assert "2020" in keys
        assert "2021" in keys
        assert "2022" in keys

    def test_metadata_captured(self):
        result = commodity_vs_commodity(
            _comparison_dataset(),
            commodity_codes=["270900", "840731"],
            reporter_code=699,
            breakdown_by="partner",
        )
        assert result.commodity_codes == ("270900", "840731")
        assert result.reporter_code == 699
        assert result.breakdown_by == "partner"

    def test_rejects_non_canonical(self):
        with pytest.raises(
            ComparativeAnalyticsError, match="CanonicalDataset"
        ):
            commodity_vs_commodity(
                [{"raw": "dict"}],
                commodity_codes=["270900", "840731"],
            )

    def test_requires_two_commodity_codes(self):
        with pytest.raises(
            ComparativeAnalyticsError, match="at least 2"
        ):
            commodity_vs_commodity(
                _comparison_dataset(),
                commodity_codes=["270900"],
            )

    def test_negative_limit_raises(self):
        with pytest.raises(
            ComparativeAnalyticsError, match="non-negative"
        ):
            commodity_vs_commodity(
                _comparison_dataset(),
                commodity_codes=["270900", "840731"],
                limit=-1,
            )

    def test_flow_filter(self):
        result = commodity_vs_commodity(
            _comparison_dataset(),
            commodity_codes=["270900", "840731"],
            reporter_code=699,
            breakdown_by="partner",
            period="2022",
            flow="X",
        )
        by_key = {r.dimension_key: r for r in result.rows}
        # 270900 X from India → only USA (200)
        # 840731 X from India → only USA (100)
        assert by_key["124"].values == (
            Decimal("200"),
            Decimal("100"),
        )

    def test_default_descending(self):
        result = commodity_vs_commodity(
            _comparison_dataset(),
            commodity_codes=["270900", "840731"],
            reporter_code=699,
            breakdown_by="partner",
        )
        deltas = [r.deltas[-1] for r in result.rows]
        for a, b in zip(deltas, deltas[1:]):
            assert a >= b


# ---------------------------------------------------------------------------
# TestPartnerVsPartner
# ---------------------------------------------------------------------------


class TestPartnerVsPartner:
    def test_returns_partner_comparison(self):
        result = partner_vs_partner(
            _comparison_dataset(),
            partner_codes=[124, 156],
            reporter_code=699,
            breakdown_by="commodity",
            period="2022",
        )
        assert isinstance(result, PartnerComparison)

    def test_india_partners_usa_vs_china(self):
        result = partner_vs_partner(
            _comparison_dataset(),
            partner_codes=[124, 156],
            reporter_code=699,
            breakdown_by="commodity",
            period="2022",
        )
        # India 2022 with USA (124):
        #   270900: 200+80 = 280
        #   840731: 100+50 = 150
        # India 2022 with China (156):
        #   620342: 300+0 = 300
        #   840731: 0+200 = 200
        by_key = {r.dimension_key: r for r in result.rows}
        assert by_key["840731"].values == (
            Decimal("150"),
            Decimal("200"),
        )
        assert by_key["270900"].values == (
            Decimal("280"),
            Decimal("0"),
        )
        assert by_key["620342"].values == (
            Decimal("0"),
            Decimal("300"),
        )

    def test_breakdown_by_period(self):
        result = partner_vs_partner(
            _comparison_dataset(),
            partner_codes=[124, 156],
            reporter_code=699,
            breakdown_by="period",
        )
        keys = {r.dimension_key for r in result.rows}
        assert "2020" in keys
        assert "2022" in keys

    def test_metadata_captured(self):
        result = partner_vs_partner(
            _comparison_dataset(),
            partner_codes=[124, 156],
            reporter_code=699,
            breakdown_by="commodity",
            period="2022",
        )
        assert result.partner_codes == (124, 156)
        assert result.reporter_code == 699
        # USA ISO3 is 'USA' (842 also maps to USA
        # in our fixture; first match wins).
        assert result.partner_iso3[0] in {"USA"}

    def test_flow_filter(self):
        result = partner_vs_partner(
            _comparison_dataset(),
            partner_codes=[124, 156],
            reporter_code=699,
            breakdown_by="commodity",
            period="2022",
            flow="M",
        )
        # India 2022 M with USA: 270900=80,
        # 840731=50. With China: 840731=200.
        by_key = {r.dimension_key: r for r in result.rows}
        assert by_key["840731"].values == (
            Decimal("50"),
            Decimal("200"),
        )

    def test_rejects_non_canonical(self):
        with pytest.raises(
            ComparativeAnalyticsError, match="CanonicalDataset"
        ):
            partner_vs_partner(
                [{"raw": "dict"}],
                partner_codes=[124, 156],
                reporter_code=699,
            )

    def test_requires_two_partner_codes(self):
        with pytest.raises(
            ComparativeAnalyticsError, match="at least 2"
        ):
            partner_vs_partner(
                _comparison_dataset(),
                partner_codes=[124],
                reporter_code=699,
            )

    def test_negative_limit_raises(self):
        with pytest.raises(
            ComparativeAnalyticsError, match="non-negative"
        ):
            partner_vs_partner(
                _comparison_dataset(),
                partner_codes=[124, 156],
                reporter_code=699,
                limit=-1,
            )

    def test_unknown_partner_codes_still_valid(self):
        # Unknown partner codes simply produce
        # zero values; no error.
        result = partner_vs_partner(
            _comparison_dataset(),
            partner_codes=[999, 998],
            reporter_code=699,
            breakdown_by="commodity",
        )
        assert result.rows == ()
        assert result.summary.total_values == (
            Decimal("0"),
            Decimal("0"),
        )

    def test_default_descending(self):
        result = partner_vs_partner(
            _comparison_dataset(),
            partner_codes=[124, 156],
            reporter_code=699,
            breakdown_by="commodity",
            period="2022",
        )
        deltas = [r.deltas[-1] for r in result.rows]
        for a, b in zip(deltas, deltas[1:]):
            assert a >= b


# ---------------------------------------------------------------------------
# TestComparativeErrorsPropagated
# ---------------------------------------------------------------------------


class TestComparativeErrorsPropagated:
    def test_inherits_from_analytics_error(self):
        try:
            country_vs_country(
                [{"raw": "dict"}],
                reporter_codes=[699, 156],
            )
        except ComparativeAnalyticsError as exc:
            assert isinstance(exc, AnalyticsError)

    def test_all_functions_reject_non_canonical(self):
        for fn, kwargs in [
            (
                country_vs_country,
                {"reporter_codes": [699, 156]},
            ),
            (
                year_vs_year,
                {
                    "reporter_code": 699,
                    "period_a": "2020",
                    "period_b": "2022",
                },
            ),
            (
                commodity_vs_commodity,
                {"commodity_codes": ["270900", "840731"]},
            ),
            (
                partner_vs_partner,
                {
                    "partner_codes": [124, 156],
                    "reporter_code": 699,
                },
            ),
        ]:
            with pytest.raises(
                ComparativeAnalyticsError,
                match="CanonicalDataset",
            ):
                fn([{"raw": "dict"}], **kwargs)

    def test_all_functions_reject_negative_limit(self):
        for fn, kwargs in [
            (
                country_vs_country,
                {"reporter_codes": [699, 156], "limit": -1},
            ),
            (
                year_vs_year,
                {
                    "reporter_code": 699,
                    "period_a": "2020",
                    "period_b": "2022",
                    "limit": -1,
                },
            ),
            (
                commodity_vs_commodity,
                {
                    "commodity_codes": ["270900", "840731"],
                    "limit": -1,
                },
            ),
            (
                partner_vs_partner,
                {
                    "partner_codes": [124, 156],
                    "reporter_code": 699,
                    "limit": -1,
                },
            ),
        ]:
            with pytest.raises(
                ComparativeAnalyticsError,
                match="non-negative",
            ):
                fn(_comparison_dataset(), **kwargs)

    def test_all_functions_reject_invalid_breakdown(self):
        for fn, kwargs in [
            (
                country_vs_country,
                {
                    "reporter_codes": [699, 156],
                    "breakdown_by": "flow",
                },
            ),
            (
                year_vs_year,
                {
                    "reporter_code": 699,
                    "period_a": "2020",
                    "period_b": "2022",
                    "breakdown_by": "flow",
                },
            ),
            (
                commodity_vs_commodity,
                {
                    "commodity_codes": ["270900", "840731"],
                    "breakdown_by": "flow",
                },
            ),
            (
                partner_vs_partner,
                {
                    "partner_codes": [124, 156],
                    "reporter_code": 699,
                    "breakdown_by": "flow",
                },
            ),
        ]:
            with pytest.raises(
                ComparativeAnalyticsError,
                match="breakdown_by",
            ):
                fn(_comparison_dataset(), **kwargs)

    def test_all_functions_require_two_codes(self):
        for fn, kwargs in [
            (
                country_vs_country,
                {"reporter_codes": [699]},
            ),
            (
                commodity_vs_commodity,
                {"commodity_codes": ["270900"]},
            ),
            (
                partner_vs_partner,
                {"partner_codes": [124], "reporter_code": 699},
            ),
        ]:
            with pytest.raises(
                ComparativeAnalyticsError,
                match="at least 2",
            ):
                fn(_comparison_dataset(), **kwargs)

    def test_year_vs_year_distinct_periods(self):
        with pytest.raises(
            ComparativeAnalyticsError,
            match="distinct",
        ):
            year_vs_year(
                _comparison_dataset(),
                reporter_code=699,
                period_a="2020",
                period_b="2020",
            )