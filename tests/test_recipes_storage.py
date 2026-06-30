"""Regression tests for the storage recipes (CB-005).

The recipes live under ``recipes/storage/``. Each
recipe exposes one or more ``*_demo(...)``
functions that take either a pre-built
``TradeResponse`` (for the export recipes) or a
``CanonicalDataset`` path / client (for the
reload + analytics-on-stored recipes). The
regression tests inject synthetic records and
assert on the round-trip (write → read →
assert).

The test layout mirrors the previous batches:

- one class per recipe (TestRecipe01..06)
- synthetic raw upstream records parsed by
  ``TradeParser`` to populate ``TradeResponse``
- ``tmp_path`` for storage destinations
- ``ComtradeClient(configuration=...)`` for the
  analytics-on-stored recipe (which needs a
  client for ``client.analytics``)
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from un_comtrade.config import Configuration
from un_comtrade import ComtradeClient
from un_comtrade.parser import TradeParser
from un_comtrade.storage._base import StorageError, StorageRegistry
from un_comtrade.transform import CanonicalDataset


# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
RECIPES_DIR = ROOT / "recipes" / "storage"


def _load_recipe(name: str):
    spec = importlib.util.spec_from_file_location(
        f"recipe_storage_{name}", RECIPES_DIR / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


R01 = _load_recipe("01_etl_pipeline")
R02 = _load_recipe("02_export_csv")
R03 = _load_recipe("03_export_parquet")
R04 = _load_recipe("04_export_duckdb")
R05 = _load_recipe("05_reload_storage")
R06 = _load_recipe("06_analytics_on_stored")


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _baseline_raw(**overrides: Any) -> dict:
    """Build a raw upstream record satisfying the parser's required set.

    Mirrors the helper in ``tests/test_recipes_analytics.py``.
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


def _build_dataset(records: list[dict], *, name: str = "test") -> CanonicalDataset:
    """Parse raw upstream records into TradeRecords and wrap."""
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


def _build_trade_response(records: list[dict]) -> Any:
    """Build a synthetic ``TradeResponse`` from raw upstream dicts."""
    from un_comtrade.models import TradeResponse
    dataset = _build_dataset(records, name="test")
    return TradeResponse(
        elapsed_seconds=0.01,
        count=len(dataset.records),
        records=list(dataset.records),
        error="",
        upstream_url="(mock)",
        request=None,
        skipped=dataset.skipped,
    )


# ---------------------------------------------------------------------------
# Recipe 01 — etl_pipeline (smoke only)
# ---------------------------------------------------------------------------


class TestRecipe01EtlPipeline:
    """The 01 recipe drives a live client; we only assert the
    public surface (signature + return shape) here.
    """

    def test_demo_signature(self):
        import inspect
        sig = inspect.signature(R01.etl_pipeline_demo)
        params = list(sig.parameters.keys())
        assert params == [
            "client", "reporter_code", "period",
            "flow", "output_path",
        ]
        # All except client are keyword-only.
        assert all(
            sig.parameters[p].kind
            == inspect.Parameter.KEYWORD_ONLY
            for p in params[1:]
        )

    def test_result_dataclass_is_frozen(self):
        from dataclasses import FrozenInstanceError
        result = R01.EtlPipelineResult(
            status="SUCCESS",
            source_count=10,
            skipped=0,
            duplicates_removed=0,
            output_path="/tmp/x.parquet",
            output_row_count=10,
            stage_durations={"extract": 0.01, "transform": 0.02},
        )
        assert result.status == "SUCCESS"
        with pytest.raises(FrozenInstanceError):
            result.status = "FAILED"  # type: ignore[misc]

    def test_helpers_exposed(self):
        # The recipe should expose its stage classes so callers
        # can compose their own pipelines.
        assert hasattr(R01, "_ExtractFromTrade")
        assert hasattr(R01, "_TransformToDataset")
        assert hasattr(R01, "_LoadToParquet")


# ---------------------------------------------------------------------------
# Recipe 02 — export_csv
# ---------------------------------------------------------------------------


class TestRecipe02ExportCsv:
    def test_demo_writes_csv_with_one_row_per_record(self, tmp_path):
        raw = [
            _baseline_raw(
                reporterCode=699, partnerCode=156,
                flowCode="X", primaryValue=1_000.0,
            ),
            _baseline_raw(
                reporterCode=699, partnerCode=840,
                flowCode="X", primaryValue=2_000.0,
            ),
            _baseline_raw(
                reporterCode=699, partnerCode=76,
                flowCode="X", primaryValue=3_000.0,
            ),
        ]
        response = _build_trade_response(raw)
        out_dir = tmp_path / "exports"
        result = R02.export_csv_demo(response, out_dir)

        assert result.row_count == 3
        assert result.bytes_written > 0
        # The writer places the file under ``out_dir`` named
        # after the dataset, so the dir must contain a .csv file.
        csv_files = list(out_dir.rglob("*.csv"))
        assert csv_files, "expected a CSV file to be written"
        contents = csv_files[0].read_text(encoding="utf-8")
        assert "trade_value_primary_value" in contents.splitlines()[0]
        # Header + 3 data rows.
        assert len(contents.splitlines()) == 4

    def test_demo_with_empty_response_writes_header_only(self, tmp_path):
        # Empty dataset still produces a header-only CSV
        # file (so the read path can detect the schema).
        # The byte count > 0 reflects the header row.
        response = _build_trade_response([])
        out_dir = tmp_path / "empty"
        result = R02.export_csv_demo(response, out_dir)
        assert result.row_count == 0
        # Header line + no data rows.
        csv_files = list(out_dir.rglob("*.csv"))
        assert csv_files
        assert len(csv_files[0].read_text().splitlines()) == 1


# ---------------------------------------------------------------------------
# Recipe 03 — export_parquet
# ---------------------------------------------------------------------------


class TestRecipe03ExportParquet:
    def test_demo_writes_one_partition_per_default_key(self, tmp_path):
        # Two distinct partners → no dedup → 2 records,
        # single partition (same reporter+year+freq).
        raw = [
            _baseline_raw(
                reporterCode=699, partnerCode=156,
                flowCode="X", primaryValue=1_000.0,
            ),
            _baseline_raw(
                reporterCode=699, partnerCode=840,
                flowCode="X", primaryValue=2_000.0,
            ),
        ]
        response = _build_trade_response(raw)
        out = tmp_path / "parquet"
        result = R03.export_parquet_demo(
            response, out, compression="snappy"
        )
        assert result.row_count == 2
        assert result.partition_count == 1
        assert result.codec == "snappy"
        assert result.bytes_written > 0
        assert any(out.rglob("*.parquet"))

    def test_demo_honours_compression_argument(self, tmp_path):
        raw = [
            _baseline_raw(partnerCode=156, primaryValue=1.0),
        ]
        response = _build_trade_response(raw)
        out = tmp_path / "parquet_gzip"
        result = R03.export_parquet_demo(
            response, out, compression="gzip"
        )
        assert result.codec == "gzip"
        assert result.partition_count == 1


# ---------------------------------------------------------------------------
# Recipe 04 — export_duckdb
# ---------------------------------------------------------------------------


class TestRecipe04ExportDuckdb:
    def test_demo_writes_db_and_query_returns_rows(self, tmp_path):
        raw = [
            _baseline_raw(
                reporterCode=699, partnerCode=156,
                flowCode="X", primaryValue=1_000.0,
            ),
            _baseline_raw(
                reporterCode=699, partnerCode=840,
                flowCode="X", primaryValue=2_000.0,
            ),
        ]
        response = _build_trade_response(raw)
        db = tmp_path / "exports.duckdb"
        result = R04.export_duckdb_demo(response, db, mode="replace")
        assert result.row_count == 2
        assert result.db_path == str(db)
        assert result.table_name == "trade_records"
        assert result.mode == "replace"
        assert result.bytes_written > 0

        # Round-trip: query the persisted DB.
        rows = R04.query_demo(
            str(db),
            "SELECT count(*) FROM trade_records",
        )
        assert rows == [(2,)]

    def test_demo_append_mode_keeps_existing_rows(self, tmp_path):
        raw1 = [
            _baseline_raw(
                reporterCode=699, partnerCode=156,
                flowCode="X", primaryValue=1.0,
            )
        ]
        raw2 = [
            _baseline_raw(
                reporterCode=699, partnerCode=156,
                flowCode="X", primaryValue=2.0,
            )
        ]
        db = tmp_path / "exports.duckdb"
        R04.export_duckdb_demo(
            _build_trade_response(raw1), db, mode="replace"
        )
        result = R04.export_duckdb_demo(
            _build_trade_response(raw2), db, mode="append"
        )
        assert result.row_count == 1
        assert result.mode == "append"
        rows = R04.query_demo(
            str(db), "SELECT count(*) FROM trade_records"
        )
        # replace: 1 row, append: +1 row.
        assert rows == [(2,)]


# ---------------------------------------------------------------------------
# Recipe 05 — reload_storage
# ---------------------------------------------------------------------------


class TestRecipe05ReloadStorage:
    def test_reload_demo_round_trip_csv(self, tmp_path):
        # 1. Write with recipe 02.
        raw = [
            _baseline_raw(
                reporterCode=699, partnerCode=156,
                flowCode="X", primaryValue=1.0,
            ),
            _baseline_raw(
                reporterCode=699, partnerCode=840,
                flowCode="X", primaryValue=2.0,
            ),
        ]
        response = _build_trade_response(raw)
        csv_dir = tmp_path / "csv_dataset"
        R02.export_csv_demo(response, csv_dir)

        # 2. Reload via recipe 05 — pass the directory
        # (the writer wrote the sidecar there).
        result = R05.reload_demo(csv_dir)
        assert result.path == str(csv_dir)
        assert result.backend == "csv"
        assert result.row_count == 2
        assert result.built is False

    def test_reload_demo_round_trip_parquet(self, tmp_path):
        raw = [
            _baseline_raw(
                reporterCode=699, partnerCode=156,
                flowCode="X", primaryValue=1.0,
            )
        ]
        response = _build_trade_response(raw)
        parquet_dir = tmp_path / "parquet_dataset"
        R03.export_parquet_demo(response, parquet_dir)
        # Recipe 05 resolves the parquet dir and dispatches
        # directly to the parquet backend, bypassing the
        # SDK's first-level suffix detection.
        result = R05.reload_demo(parquet_dir)
        assert result.backend == "parquet"
        assert result.row_count == 1
        assert result.built is False

    def test_reload_demo_round_trip_duckdb(self, tmp_path):
        raw = [
            _baseline_raw(
                reporterCode=699, partnerCode=156,
                flowCode="X", primaryValue=1.0,
            ),
            _baseline_raw(
                reporterCode=699, partnerCode=76,
                flowCode="X", primaryValue=2.0,
            ),
        ]
        response = _build_trade_response(raw)
        db = tmp_path / "exports.duckdb"
        R04.export_duckdb_demo(response, db, mode="replace")
        result = R05.reload_demo(db)
        assert result.backend == "duckdb"
        assert result.row_count == 2
        assert result.built is False

    def test_reload_demo_raises_storage_error_on_missing_path(self, tmp_path):
        # ``StorageRegistry.open`` raises ``StorageError``
        # before any API call when the path is missing.
        missing = tmp_path / "missing.duckdb"
        with pytest.raises(StorageError) as excinfo:
            R05.reload_demo(missing)
        assert "does not exist" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Recipe 06 — analytics_on_stored
# ---------------------------------------------------------------------------


class TestRecipe06AnalyticsOnStored:
    def test_demo_reloads_and_runs_analytics(self, tmp_path):
        raw = [
            _baseline_raw(
                reporterCode=699, partnerCode=156,
                flowCode="X", primaryValue=1_000.0,
            ),
            _baseline_raw(
                reporterCode=699, partnerCode=840,
                flowCode="X", primaryValue=2_000.0,
            ),
            _baseline_raw(
                reporterCode=699, partnerCode=156,
                flowCode="M", primaryValue=500.0,
            ),
            _baseline_raw(
                reporterCode=699, partnerCode=840,
                flowCode="M", primaryValue=700.0,
            ),
        ]
        response = _build_trade_response(raw)
        db = tmp_path / "exports.duckdb"
        R04.export_duckdb_demo(response, db, mode="replace")

        client = ComtradeClient(
            configuration=Configuration(api_key="test")
        )
        result = R06.analytics_on_stored_demo(
            db, client=client, reporter_code=699, top_n=5
        )
        assert result.row_count == 4
        assert result.built is False
        assert result.summary is not None
        assert result.summary.reporter_code == 699
        assert result.summary.total_exports == Decimal("3000.00")
        assert result.summary.total_imports == Decimal("1200.00")
        assert result.summary.trade_balance == Decimal("1800.00")
        # Top partners by total trade (exports + imports).
        assert len(result.top_partners) > 0
        partner_codes = {row.partner_code for row in result.top_partners}
        assert partner_codes <= {156, 840}

    def test_format_summary_handles_none(self):
        lines = R06._format_summary(None)
        assert lines == ["  (no summary — reporter has no records)"]

    def test_format_partners_handles_empty(self):
        lines = R06._format_partners(())
        assert lines == ["  (no partner rankings)"]

    def test_writer_for_path_picks_correct_backend(self, tmp_path):
        from un_comtrade.storage.file import CSVWriter
        from un_comtrade.storage.parquet import ParquetWriter
        from un_comtrade.storage.duckdb import DuckDBWriter
        assert isinstance(
            R06._writer_for_path(tmp_path / "x.csv"), CSVWriter
        )
        assert isinstance(
            R06._writer_for_path(tmp_path / "x.parquet"), ParquetWriter
        )
        assert isinstance(
            R06._writer_for_path(tmp_path / "x.duckdb"), DuckDBWriter
        )

    def test_writer_for_path_raises_on_unknown(self, tmp_path):
        # StorageError already imported above.
        with pytest.raises(StorageError):
            R06._writer_for_path(tmp_path / "x.txt")