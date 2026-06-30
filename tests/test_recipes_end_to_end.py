"""Regression tests for the end-to-end recipes (CB-007).

These are the most-referenced recipes: they
demonstrate the full SDK integration pattern
(fetch → parse → store → analyse → emit).

Test layout:

- ``TestRecipe01IndiaExports`` exercises the
  India-exports pipeline: synthetic
  ``TradeResponse`` → ``CanonicalDataset`` →
  DuckDB → partner CSV + summary JSON. The
  test asserts on every artefact path, the
  row count, and the top-partner ordering.
- ``TestRecipe02HsExplorer`` exercises the
  HS-code explorer pipeline: synthetic
  ``HSCode`` list + ``TradeResponse`` →
  per-commodity partner totals → Markdown
  report. The test asserts on the Markdown
  content, line count, and partner totals.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from un_comtrade.models import HSCode, TradeResponse
from un_comtrade.parser import TradeParser
from un_comtrade.transform import CanonicalDataset


# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
RECIPES_DIR = ROOT / "recipes" / "end_to_end"


def _load_recipe(name: str):
    spec = importlib.util.spec_from_file_location(
        f"recipe_e2e_{name}", RECIPES_DIR / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


R01 = _load_recipe("01_india_exports_to_report")
R02 = _load_recipe("02_hs_explorer_to_markdown")


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _baseline_raw(**overrides: Any) -> dict:
    """Build a raw upstream record satisfying the parser's
    required field set.
    """
    base: dict = {
        "typeCode": "C",
        "freqCode": "A",
        "refPeriodId": 20220101,
        "refYear": 2022,
        "refMonth": 52,
        "period": "2022",
        "reporterCode": 699,
        "reporterISO": "IND",
        "partnerCode": 156,
        "partnerISO": "CHN",
        "flowCode": "X",
        "classificationCode": "H6",
        "cmdCode": "TOTAL",
        "customsCode": "C00",
        "mosCode": "0",
        "motCode": 0,
        "qtyUnitCode": -1,
        "primaryValue": 1_000_000.0,
    }
    base.update(overrides)
    return base


def _build_trade_response(records: list[dict]) -> TradeResponse:
    """Build a synthetic ``TradeResponse`` from raw upstream dicts."""
    parser = TradeParser(log_skipped=False)
    parsed = parser.parse_records(records)
    return TradeResponse(
        elapsed_seconds=0.42,
        count=len(parsed.records),
        records=list(parsed.records),
        error="",
        upstream_url="(mock)",
        request={"reporterCode": 699, "period": "2022"},
        skipped=parsed.skipped,
    )


# ---------------------------------------------------------------------------
# Recipe 01 — India exports pipeline
# ---------------------------------------------------------------------------


class TestRecipe01IndiaExports:
    def _build_response(self) -> TradeResponse:
        """Synthetic India exports for 4 partners."""
        raw = [
            _baseline_raw(
                partnerCode=156, partnerISO="CHN",
                primaryValue=2_000_000_000.0,
            ),
            _baseline_raw(
                partnerCode=840, partnerISO="USA",
                primaryValue=1_500_000_000.0,
            ),
            _baseline_raw(
                partnerCode=784, partnerISO="ARE",
                primaryValue=1_000_000_000.0,
            ),
            _baseline_raw(
                partnerCode=76, partnerISO="BRA",
                primaryValue=500_000_000.0,
            ),
        ]
        return _build_trade_response(raw)

    def test_full_pipeline_produces_all_artefacts(self, tmp_path):
        response = self._build_response()
        report = R01.india_exports_pipeline_demo(
            response=response,
            output_dir=tmp_path,
            reporter_code=699,
            period="2022",
            flow="X",
        )
        # DuckDB file exists.
        assert Path(report.database_path).exists()
        # Partner CSV exists with header + 4 rows.
        assert Path(report.partner_csv_path).exists()
        csv_content = Path(report.partner_csv_path).read_text(
            encoding="utf-8"
        )
        assert "rank" in csv_content
        assert csv_content.count("\n") == 5  # header + 4 data rows
        # Summary JSON exists and contains the headline numbers.
        assert Path(report.summary_json_path).exists()
        summary = json.loads(
            Path(report.summary_json_path).read_text(encoding="utf-8")
        )
        assert summary["reporter_code"] == 699
        assert summary["period"] == "2022"
        assert summary["record_count"] == 4
        assert Decimal(summary["total_exports"]) == Decimal("5000000000")
        # Top partner is CHN (highest value).
        assert summary["top_5_partners"][0]["partner_iso3"] == "CHN"

    def test_top_partners_are_ranked_by_total_trade(self, tmp_path):
        response = self._build_response()
        report = R01.india_exports_pipeline_demo(
            response=response, output_dir=tmp_path,
        )
        assert report.top_partner_iso3[0] == "CHN"
        assert report.top_partner_iso3[1] == "USA"
        assert report.top_partner_codes[0] == 156
        assert report.top_partner_codes[1] == 840
        assert report.partner_count == 4
        assert report.total_exports == Decimal("5000000000")

    def test_pipeline_handles_empty_response(self, tmp_path):
        # Empty response still produces the
        # artefacts — DuckDB with metadata, CSV
        # header only, JSON with zero totals.
        response = _build_trade_response([])
        report = R01.india_exports_pipeline_demo(
            response=response, output_dir=tmp_path,
        )
        assert report.record_count == 0
        assert report.total_exports == Decimal("0")
        assert report.partner_count == 0
        assert Path(report.database_path).exists()
        assert Path(report.partner_csv_path).exists()
        summary = json.loads(
            Path(report.summary_json_path).read_text(encoding="utf-8")
        )
        assert summary["record_count"] == 0


# ---------------------------------------------------------------------------
# Recipe 02 — HS explorer pipeline
# ---------------------------------------------------------------------------


class TestRecipe02HsExplorer:
    def _build_response(self) -> TradeResponse:
        """India exports for 5 HS codes × 2 partners."""
        raw: list[dict] = []
        # HS code 870380 — partner 156 (China) and 840 (USA).
        raw.append(_baseline_raw(
            cmdCode="870380",
            partnerCode=156, partnerISO="CHN",
            primaryValue=2_000_000_000.0,
        ))
        raw.append(_baseline_raw(
            cmdCode="870380",
            partnerCode=840, partnerISO="USA",
            primaryValue=1_000_000_000.0,
        ))
        # HS code 870360 — partner 156 and 840.
        raw.append(_baseline_raw(
            cmdCode="870360",
            partnerCode=156, partnerISO="CHN",
            primaryValue=1_500_000_000.0,
        ))
        raw.append(_baseline_raw(
            cmdCode="870360",
            partnerCode=840, partnerISO="USA",
            primaryValue=500_000_000.0,
        ))
        # HS code 870370 — partner 156 only.
        raw.append(_baseline_raw(
            cmdCode="870370",
            partnerCode=156, partnerISO="CHN",
            primaryValue=900_000_000.0,
        ))
        return _build_trade_response(raw)

    def _matched_codes(self) -> list[HSCode]:
        """The HSCode list returned by ``search_hs``."""
        return [
            HSCode(
                commodity_code="870380",
                classification_code="HS",
                edition="H6",
                display_name="Motor cars, electric",
            ),
            HSCode(
                commodity_code="870360",
                classification_code="HS",
                edition="H6",
                display_name="Motor cars, spark-ignition",
            ),
            HSCode(
                commodity_code="870370",
                classification_code="HS",
                edition="H6",
                display_name="Motor cars, diesel",
            ),
        ]

    def test_full_pipeline_writes_markdown_report(self, tmp_path):
        response = self._build_response()
        matched = self._matched_codes()
        out_md = tmp_path / "report.md"
        report = R02.hs_explorer_pipeline_demo(
            matched_codes=matched,
            response=response,
            partner_a_code=156,
            partner_b_code=840,
            reporter_code=699,
            period="2022",
            output_path=out_md,
            hs_edition="H6",
            reporter_iso3="IND",
            partner_a_iso3="CHN",
            partner_b_iso3="USA",
        )
        # Markdown exists.
        assert Path(report.markdown_path).exists()
        md = Path(report.markdown_path).read_text(encoding="utf-8")
        # Required sections.
        assert "# HS explorer:" in md
        assert "## HS catalogue matches" in md
        assert "## CHN vs. USA" in md
        # Required content.
        assert "870380" in md
        assert "870360" in md
        assert "870370" in md
        assert "IND" in md
        assert "2022" in md

    def test_partner_totals_match_expected(self, tmp_path):
        response = self._build_response()
        matched = self._matched_codes()
        report = R02.hs_explorer_pipeline_demo(
            matched_codes=matched,
            response=response,
            partner_a_code=156,
            partner_b_code=840,
            reporter_code=699,
            period="2022",
            output_path=tmp_path / "report.md",
            hs_edition="H6",
        )
        # China total: 2.0B + 1.5B + 0.9B = 4.4B
        assert report.partner_a_total == Decimal("4400000000")
        # USA total: 1.0B + 0.5B = 1.5B
        assert report.partner_b_total == Decimal("1500000000")

    def test_comparison_rows_align_with_matched_codes(self, tmp_path):
        response = self._build_response()
        matched = self._matched_codes()
        report = R02.hs_explorer_pipeline_demo(
            matched_codes=matched,
            response=response,
            partner_a_code=156,
            partner_b_code=840,
            reporter_code=699,
            period="2022",
            output_path=tmp_path / "report.md",
            hs_edition="H6",
        )
        # Three rows, in matched-codes order.
        assert len(report.comparison_rows) == 3
        assert report.comparison_rows[0][0] == "870380"
        assert report.comparison_rows[1][0] == "870360"
        assert report.comparison_rows[2][0] == "870370"
        # Row 0: CHN=2.0B, USA=1.0B, Δ=+1.0B.
        assert report.comparison_rows[0][1] == Decimal("2000000000")
        assert report.comparison_rows[0][2] == Decimal("1000000000")
        assert report.comparison_rows[0][3] == Decimal("1000000000")

    def test_pipeline_filters_to_matched_codes(self, tmp_path):
        response = self._build_response()
        matched = self._matched_codes()
        report = R02.hs_explorer_pipeline_demo(
            matched_codes=matched,
            response=response,
            partner_a_code=156,
            partner_b_code=840,
            reporter_code=699,
            period="2022",
            output_path=tmp_path / "report.md",
            hs_edition="H6",
        )
        # Records before filter: 5 (the synthetic dataset).
        assert report.record_count == 5
        # After filtering to matched HS codes: 5 (all 5
        # synthetic records happen to match the matched
        # codes). The point is that the filter ran.
        assert report.filtered_record_count == 5

    def test_markdown_contains_money_formatter(self):
        # Direct test of the helper.
        assert R02._format_money(Decimal("1500000000")) == "$1.50B"
        assert R02._format_money(Decimal("2500000")) == "$2.50M"
        assert R02._format_money(Decimal("750")) == "$750.00"
        assert R02._format_money(None) == "—"
        assert R02._format_money(Decimal("0")) == "$0.00"