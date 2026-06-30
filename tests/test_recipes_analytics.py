"""Regression tests for the analytics recipes (CB-004).

The recipes live under ``recipes/analytics/``. Each
recipe is a thin wrapper around the SDK's
analytics layer; the recipes take a pre-built
``CanonicalDataset`` in their ``*_demo()`` function
and the regression tests inject a synthetic
dataset. The recipes' ``main()`` fetches the data
via the trade service and builds the dataset.

The tests are structured as one class per recipe:

- ``TestRecipe01CountryBalance``
- ``TestRecipe02TopCommodities``
- ``TestRecipe03PartnerAnalysis``
- ``TestRecipe04CountryComparison``
- ``TestRecipe05TrendAnalysis``

Each test:

- Builds a synthetic ``CanonicalDataset`` from
  raw upstream records (parsed via ``TradeParser``).
- Calls the recipe's ``*_demo(dataset, ...)``
  function directly.
- Asserts on the returned dataclass — never on
  stdout. The recipes return stable, frozen
  dataclasses that decouple the public recipe
  surface from the analytics layer's internal
  types.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from un_comtrade.parser import TradeParser
from un_comtrade.transform import CanonicalDataset


# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
RECIPES_DIR = ROOT / "recipes" / "analytics"


def _load_recipe(name: str):
    spec = importlib.util.spec_from_file_location(
        f"recipe_{name}", RECIPES_DIR / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


R01 = _load_recipe("country_balance")
R02 = _load_recipe("top_commodities")
R03 = _load_recipe("partner_analysis")
R04 = _load_recipe("country_comparison")
R05 = _load_recipe("trend_analysis")


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _baseline_raw(**overrides: Any) -> dict:
    """Build a raw upstream record satisfying the parser's
    full required-field set.

    The parser drops records missing any of:
    typeCode, freqCode, classificationCode, refYear,
    refMonth, period, reporterCode, partnerCode,
    flowCode, cmdCode, customsCode, mosCode, motCode,
    qtyUnitCode, primaryValue. Tests fill the
    minimum required fields plus the dimension
    fields they care about via ``overrides``.
    """
    base: dict = {
        "typeCode": "C",
        "freqCode": "A",
        "refPeriodId": 20220101,
        "refYear": 2022,
        "refMonth": 52,  # annual sentinel
        "period": "2022",
        "reporterCode": 699,
        "reporterISO": "IND",
        "partnerCode": 0,
        "partnerISO": "W00",
        "flowCode": "X",
        "classificationCode": "H6",
        "cmdCode": "TOTAL",
        "customsCode": "C00",
        "mosCode": "0",
        "motCode": 0,
        "qtyUnitCode": -1,
        "primaryValue": 0.0,
    }
    base.update(overrides)
    return base


def _build_dataset(records: list[dict], *, name: str = "test") -> CanonicalDataset:
    """Parse raw records into TradeRecords and wrap in a dataset."""
    parser = TradeParser(log_skipped=False)
    result = parser.parse_records(records)
    return CanonicalDataset(
        name=name,
        records=result.records,
        parser_name="TradeParser",
        skipped=result.skipped,
        source_count=len(records),
        extracted_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Recipe 01 — country_balance
# ---------------------------------------------------------------------------


class TestRecipe01CountryBalance:
    def test_demo_computes_export_import_and_balance(self):
        raw = [
            _baseline_raw(
                reporterCode=699, partnerCode=0, period="2022",
                flowCode="X", primaryValue=500_000.0,
            ),
            _baseline_raw(
                reporterCode=699, partnerCode=156, period="2022",
                flowCode="X", primaryValue=300_000.0,
            ),
            _baseline_raw(
                reporterCode=699, partnerCode=0, period="2022",
                flowCode="M", primaryValue=400_000.0,
            ),
            _baseline_raw(
                reporterCode=699, partnerCode=156, period="2022",
                flowCode="M", primaryValue=200_000.0,
            ),
        ]
        dataset = _build_dataset(raw)
        result = R01.country_balance_demo(dataset, reporter_code=699)
        assert result is not None
        assert result.reporter_code == 699
        assert result.total_exports == Decimal("800000.00")
        assert result.total_imports == Decimal("600000.00")
        # balance = 800_000 - 600_000 = 200_000
        assert result.trade_balance == Decimal("200000.00")
        assert result.record_count == 4

    def test_demo_returns_none_when_no_records(self):
        raw = [
            # Records for a different reporter so the
            # balance query for 699 returns nothing.
            _baseline_raw(
                reporterCode=156, partnerCode=0, period="2022",
                flowCode="X", primaryValue=100.0,
            )
        ]
        dataset = _build_dataset(raw)
        result = R01.country_balance_demo(dataset, reporter_code=699)
        assert result is None

    def test_render_includes_all_headline_numbers(self, capsys):
        raw = [
            _baseline_raw(
                reporterCode=699, flowCode="X", primaryValue=100.0,
            ),
            _baseline_raw(
                reporterCode=699, flowCode="M", primaryValue=50.0,
            ),
        ]
        dataset = _build_dataset(raw)
        result = R01.country_balance_demo(dataset, reporter_code=699)
        assert result is not None
        print(R01.render(result))
        out = capsys.readouterr().out
        assert "exports" in out
        assert "imports" in out
        assert "balance" in out
        assert "records" in out


# ---------------------------------------------------------------------------
# Recipe 02 — top_commodities
# ---------------------------------------------------------------------------


class TestRecipe02TopCommodities:
    def test_demo_returns_top_commodities_ranked(self):
        # India exports 2022: 5 chapters with varying values.
        # 27 (mineral fuels) is the largest.
        raw = [
            _baseline_raw(
                reporterCode=699, cmdCode="27", primaryValue=10_000.0,
            ),
            _baseline_raw(
                reporterCode=699, cmdCode="85", primaryValue=8_000.0,
            ),
            _baseline_raw(
                reporterCode=699, cmdCode="71", primaryValue=6_000.0,
            ),
            _baseline_raw(
                reporterCode=699, cmdCode="84", primaryValue=4_000.0,
            ),
            _baseline_raw(
                reporterCode=699, cmdCode="87", primaryValue=2_000.0,
            ),
            # A 6-digit code: must be EXCLUDED when
            # hs_level=2 (the parser's exact-digit check
            # requires 0101 to be treated as a 4-digit,
            # not a 2-digit prefix).
            _baseline_raw(
                reporterCode=699, cmdCode="0101", primaryValue=99_999.0,
            ),
        ]
        dataset = _build_dataset(raw)
        result = R02.top_commodities_demo(
            dataset, reporter_code=699, flow="X", hs_level=2, limit=5
        )
        assert result.flow == "X"
        assert result.hs_level == 2
        # The 6-digit code is excluded by hs_level=2.
        # The top 5 by export value are 27, 85, 71, 84, 87.
        assert len(result.rows) == 5
        assert result.rows[0].commodity_code == "27"
        assert result.rows[0].rank == 1
        assert result.rows[0].export_value == Decimal("10000.00")
        # Subsequent rows are descending.
        for i in range(len(result.rows) - 1):
            assert (
                result.rows[i].export_value
                >= result.rows[i + 1].export_value
            )

    def test_rejects_invalid_flow(self):
        raw = [_baseline_raw(reporterCode=699, primaryValue=10.0)]
        dataset = _build_dataset(raw)
        with pytest.raises(ValueError, match="flow must be one of"):
            R02.top_commodities_demo(
                dataset, reporter_code=699, flow="ZZ", hs_level=2
            )

    def test_rejects_invalid_hs_level(self):
        raw = [_baseline_raw(reporterCode=699, primaryValue=10.0)]
        dataset = _build_dataset(raw)
        with pytest.raises(ValueError, match="hs_level must be one of"):
            R02.top_commodities_demo(
                dataset, reporter_code=699, flow="X", hs_level=3
            )


# ---------------------------------------------------------------------------
# Recipe 03 — partner_analysis
# ---------------------------------------------------------------------------


class TestRecipe03PartnerAnalysis:
    def test_demo_returns_top_partners_ranked(self):
        raw = [
            _baseline_raw(
                reporterCode=699, partnerCode=0,
                partnerISO="W00", flowCode="X", primaryValue=10_000.0,
            ),
            _baseline_raw(
                reporterCode=699, partnerCode=156,
                partnerISO="CHN", flowCode="X", primaryValue=5_000.0,
            ),
            _baseline_raw(
                reporterCode=699, partnerCode=643,
                partnerISO="RUS", flowCode="X", primaryValue=3_000.0,
            ),
        ]
        dataset = _build_dataset(raw)
        result = R03.partner_analysis_demo(
            dataset,
            reporter_code=699,
            flow="X",
            top_n=3,
            focus_partner=None,
        )
        assert len(result.top_partners) == 3
        assert result.top_partners[0].partner_code == 0
        assert result.top_partners[0].total_exports == Decimal("10000.00")
        # No focus partner → no growth summary.
        assert result.growth is None

    def test_demo_with_focus_partner_returns_growth(self):
        # Two years of data for partner 156.
        raw = [
            _baseline_raw(
                reporterCode=699, partnerCode=156, partnerISO="CHN",
                refYear=2018, period="2018",
                refPeriodId=20180101,
                flowCode="X", primaryValue=1_000.0,
            ),
            _baseline_raw(
                reporterCode=699, partnerCode=156, partnerISO="CHN",
                refYear=2022, period="2022",
                refPeriodId=20220101,
                flowCode="X", primaryValue=1_500.0,
            ),
        ]
        dataset = _build_dataset(raw)
        result = R03.partner_analysis_demo(
            dataset,
            reporter_code=699,
            flow="X",
            top_n=5,
            focus_partner=156,
        )
        assert result.growth is not None
        assert result.growth.reporter_code == 699
        assert result.growth.partner_code == 156
        # Two years → one growth row (the first has no
        # prior). Sorted by year, 2018 first.
        assert [p.year for p in result.growth.points] == [2018, 2022]
        # CAGR over 4 years from 1_000 to 1_500 ≈ 10.67%.
        assert result.growth.cagr is not None
        assert float(result.growth.cagr) == pytest.approx(0.1067, rel=0.01)

    def test_rejects_invalid_flow(self):
        raw = [_baseline_raw(reporterCode=699, primaryValue=10.0)]
        dataset = _build_dataset(raw)
        with pytest.raises(ValueError, match="flow must be one of"):
            R03.partner_analysis_demo(
                dataset, reporter_code=699, flow="ZZ", top_n=5
            )


# ---------------------------------------------------------------------------
# Recipe 04 — country_comparison
# ---------------------------------------------------------------------------


class TestRecipe04CountryComparison:
    def test_demo_returns_side_by_side_comparison(self):
        # India and China exports, two HS chapters.
        raw = [
            # India — chapter 27 dominant.
            _baseline_raw(
                reporterCode=699, partnerCode=0, cmdCode="27",
                flowCode="X", primaryValue=1_000.0,
            ),
            _baseline_raw(
                reporterCode=699, partnerCode=0, cmdCode="85",
                flowCode="X", primaryValue=500.0,
            ),
            # China — chapter 85 dominant.
            _baseline_raw(
                reporterCode=156, reporterISO="CHN", partnerCode=0,
                cmdCode="27", flowCode="X", primaryValue=200.0,
            ),
            _baseline_raw(
                reporterCode=156, reporterISO="CHN", partnerCode=0,
                cmdCode="85", flowCode="X", primaryValue=2_000.0,
            ),
        ]
        dataset = _build_dataset(raw)
        result = R04.country_comparison_demo(
            dataset,
            reporter_a=699,
            reporter_b=156,
            period="2022",
            flow="X",
            breakdown_by="commodity",
            limit=10,
        )
        assert result.reporter_codes == (699, 156)
        assert result.breakdown_by == "commodity"
        # Two chapters.
        assert len(result.rows) == 2
        # Chapter 27: A=1000, B=200, delta=-800, pct=-80%.
        row_27 = next(r for r in result.rows if r.dimension_key == "27")
        assert row_27.values[0] == Decimal("1000")
        assert row_27.values[1] == Decimal("200")
        assert row_27.deltas[1] == Decimal("-800")
        assert row_27.pct_changes[1] == Decimal("-80.0")
        # Chapter 85: A=500, B=2000, delta=+1500, pct=+300%.
        row_85 = next(r for r in result.rows if r.dimension_key == "85")
        assert row_85.pct_changes[1] == Decimal("300.0")
        # Aggregate totals: A=1500, B=2200, delta=+700.
        assert result.summary.total_values[0] == Decimal("1500")
        assert result.summary.total_values[1] == Decimal("2200")

    def test_rejects_invalid_flow(self):
        raw = [_baseline_raw(reporterCode=699, primaryValue=10.0)]
        dataset = _build_dataset(raw)
        with pytest.raises(ValueError, match="flow must be one of"):
            R04.country_comparison_demo(
                dataset,
                reporter_a=699, reporter_b=156, period="2022",
                flow="ZZ", breakdown_by="commodity",
            )

    def test_rejects_invalid_breakdown(self):
        raw = [_baseline_raw(reporterCode=699, primaryValue=10.0)]
        dataset = _build_dataset(raw)
        with pytest.raises(
            ValueError, match="breakdown_by must be one of"
        ):
            R04.country_comparison_demo(
                dataset,
                reporter_a=699, reporter_b=156, period="2022",
                flow="X", breakdown_by="year",
            )


# ---------------------------------------------------------------------------
# Recipe 05 — trend_analysis
# ---------------------------------------------------------------------------


class TestRecipe05TrendAnalysis:
    def test_demo_returns_annual_trend_with_growth_and_cagr(self):
        # India exports: 3 years of monotonically rising data.
        raw = [
            _baseline_raw(
                reporterCode=699, partnerCode=0, refYear=2020,
                period="2020", refPeriodId=20200101,
                flowCode="X", primaryValue=1_000.0,
            ),
            _baseline_raw(
                reporterCode=699, partnerCode=0, refYear=2021,
                period="2021", refPeriodId=20210101,
                flowCode="X", primaryValue=1_100.0,
            ),
            _baseline_raw(
                reporterCode=699, partnerCode=0, refYear=2022,
                period="2022", refPeriodId=20220101,
                flowCode="X", primaryValue=1_210.0,
            ),
        ]
        dataset = _build_dataset(raw)
        result = R05.trend_analysis_demo(
            dataset, reporter_code=699, flow="X"
        )
        assert result.flow == "X"
        assert result.years == (2020, 2021, 2022)
        # First row: growth is None (no prior).
        assert result.rows[0].growth is None
        # Second row: (1100-1000)/1000 = 0.1
        assert result.rows[1].growth == Decimal("0.1")
        # Third row: (1210-1100)/1100 = 0.1
        assert result.rows[2].growth == Decimal("0.1")
        # CAGR over 2 years from 1000 to 1210:
        # (1210/1000)^(1/2) - 1 ≈ 0.1
        assert result.cagr is not None
        assert float(result.cagr) == pytest.approx(0.1, rel=0.01)

    def test_demo_returns_empty_when_no_records(self):
        # Records for a different reporter.
        raw = [
            _baseline_raw(
                reporterCode=156, refYear=2022, period="2022",
                refPeriodId=20220101, primaryValue=10.0,
            )
        ]
        dataset = _build_dataset(raw)
        result = R05.trend_analysis_demo(
            dataset, reporter_code=699, flow="X"
        )
        assert result.rows == ()
        assert result.cagr is None
        assert result.years == ()

    def test_rejects_invalid_flow(self):
        raw = [_baseline_raw(reporterCode=699, primaryValue=10.0)]
        dataset = _build_dataset(raw)
        with pytest.raises(ValueError, match="flow must be one of"):
            R05.trend_analysis_demo(
                dataset, reporter_code=699, flow="ZZ"
            )
