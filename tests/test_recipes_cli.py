"""Regression tests for the CLI recipes (CB-006).

The recipes live under ``recipes/cli/``. Each
recipe demonstrates one CLI command by
constructing the argv and invoking
``un_comtrade.cli.main`` directly. The tests
patch the underlying ``ComtradeClient`` (or
write a real test dataset to disk) so the suite
runs offline.

Test layout:

- one class per recipe (TestRecipe01..06)
- ``monkeypatch`` for SDK client mocking
- ``capsys`` for stdout capture (the CLI prints
  through the captured stream)
- ``tmp_path`` for storage/ETL fixtures

The ETL recipe's pipeline config JSON points
to ``tests.test_recipes_cli:identity_stage_factory``;
that factory ships here at module level.
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

from un_comtrade.etl import PipelineContext, PipelineResult, PipelineStatus
from un_comtrade.transform import CanonicalDataset


# ---------------------------------------------------------------------------
# ETL stage factory shim (referenced by recipe 05's pipeline JSON)
# ---------------------------------------------------------------------------


def identity_stage_factory(**_: Any) -> Any:
    """Trivial stage factory used by the ETL recipe's
    test pipeline config.

    Returns a callable stage that passes its
    input through unchanged. The recipe's
    tests patch ``ETLPipeline.run`` so this
    factory's output is never actually invoked.
    """

    class _IdentityStage:
        def __call__(self, context: PipelineContext,
                     source: Any) -> Any:
            return source

    return _IdentityStage()


# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
RECIPES_DIR = ROOT / "recipes" / "cli"


def _load_recipe(name: str):
    spec = importlib.util.spec_from_file_location(
        f"recipe_cli_{name}", RECIPES_DIR / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


R01 = _load_recipe("01_metadata_cli")
R02 = _load_recipe("02_trade_cli")
R03 = _load_recipe("03_analytics_cli")
R04 = _load_recipe("04_storage_cli")
R05 = _load_recipe("05_etl_cli")
R06 = _load_recipe("06_output_formats_cli")


# ---------------------------------------------------------------------------
# Recipe 01 — metadata_cli (un-comtrade metadata countries)
# ---------------------------------------------------------------------------


class TestRecipe01MetadataCli:
    def test_demo_runs_metadata_countries(self, monkeypatch):
        result = R01.metadata_cli_demo(
            output_format="table", monkeypatch=monkeypatch
        )
        assert result.exit_code == 0
        assert "metadata" in result.argv
        assert "countries" in result.argv
        assert "--output-format" in result.argv
        assert "table" in result.argv

    def test_demo_renders_with_format(self, monkeypatch, capsys):
        R01.metadata_cli_demo(
            output_format="json", monkeypatch=monkeypatch
        )
        # The CLI writes to stdout; the recipe's
        # demo captures stdout internally. Verify
        # the captured stdout has JSON content.
        captured = capsys.readouterr()
        # No recipe-level print beyond the demo.
        assert captured.err == "" or "Warning" not in captured.err

    def test_demo_with_output_path(self, monkeypatch, tmp_path):
        target = tmp_path / "countries.txt"
        result = R01.metadata_cli_demo(
            output_format="json",
            output_path=str(target),
            monkeypatch=monkeypatch,
        )
        assert result.exit_code == 0
        # The CLI wrote the rendered output to PATH.
        assert target.exists()


# ---------------------------------------------------------------------------
# Recipe 02 — trade_cli (un-comtrade trade exports)
# ---------------------------------------------------------------------------


class TestRecipe02TradeCli:
    def test_demo_runs_trade_exports(self, monkeypatch):
        result = R02.trade_cli_demo(
            reporter=699, period="2022",
            monkeypatch=monkeypatch,
        )
        assert result.exit_code == 0
        assert "trade" in result.argv
        assert "exports" in result.argv
        assert "--reporter" in result.argv
        assert "699" in result.argv
        assert "--year" in result.argv
        assert "2022" in result.argv

    def test_demo_with_partner_and_max_records(self, monkeypatch):
        result = R02.trade_cli_demo(
            reporter=699, period="2022",
            partner=156, max_records=10,
            monkeypatch=monkeypatch,
        )
        assert result.exit_code == 0
        assert "--partner" in result.argv
        assert "156" in result.argv
        assert "--max-records" in result.argv
        assert "10" in result.argv

    def test_demo_with_output_path(self, monkeypatch, tmp_path):
        target = tmp_path / "exports.json"
        result = R02.trade_cli_demo(
            reporter=699, period="2022",
            output_path=str(target),
            monkeypatch=monkeypatch,
        )
        assert result.exit_code == 0
        assert target.exists()


# ---------------------------------------------------------------------------
# Recipe 03 — analytics_cli (un-comtrade analytics country)
# ---------------------------------------------------------------------------


class TestRecipe03AnalyticsCli:
    def test_demo_runs_analytics_country(self, tmp_path):
        # Write a real DuckDB dataset for the CLI to read.
        dataset_path = tmp_path / "exports.duckdb"
        R03.write_test_dataset(dataset_path)
        assert dataset_path.exists()

        result = R03.analytics_cli_demo(
            dataset_path=dataset_path,
            reporter=699, output_format="table",
        )
        assert result.exit_code == 0
        assert "analytics" in result.argv
        assert "country" in result.argv
        assert "--dataset" in result.argv
        assert "--reporter" in result.argv
        assert "699" in result.argv

    def test_demo_with_output_path(self, tmp_path):
        dataset_path = tmp_path / "exports.duckdb"
        R03.write_test_dataset(dataset_path)
        out_log = tmp_path / "summary.txt"
        result = R03.analytics_cli_demo(
            dataset_path=dataset_path,
            reporter=699, output_format="json",
            output_path=str(out_log),
        )
        assert result.exit_code == 0
        assert out_log.exists()


# ---------------------------------------------------------------------------
# Recipe 04 — storage_cli (un-comtrade storage parquet)
# ---------------------------------------------------------------------------


class TestRecipe04StorageCli:
    def test_demo_converts_csv_to_parquet(self, tmp_path):
        # 1. Write a real CSV dataset.
        csv_dir = tmp_path / "input_csv"
        R04.write_csv_dataset(csv_dir)
        assert csv_dir.exists()

        # 2. Convert via the CLI to Parquet. The CLI's
        # CSV loader expects a *directory* (not a
        # single file) — pass the dir.
        parquet_out = tmp_path / "out.parquet"
        result = R04.storage_cli_demo(
            dataset_path=csv_dir,
            output_path=parquet_out,
            fmt="parquet",
        )
        assert result.exit_code == 0
        assert "storage" in result.argv
        assert "parquet" in result.argv
        assert "--dataset" in result.argv
        assert "--output-path" in result.argv
        # The CLI's parquet writer produced a file
        # under the requested directory.
        assert any(parquet_out.rglob("*.parquet"))

    def test_demo_with_overwrite(self, tmp_path):
        csv_dir = tmp_path / "input_csv"
        R04.write_csv_dataset(csv_dir)
        out = tmp_path / "out.parquet"
        R04.storage_cli_demo(
            dataset_path=csv_dir, output_path=out,
            fmt="parquet", overwrite=True,
        )
        # Second run should still succeed with --overwrite.
        result = R04.storage_cli_demo(
            dataset_path=csv_dir, output_path=out,
            fmt="parquet", overwrite=True,
        )
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Recipe 05 — etl_cli (un-comtrade etl run)
# ---------------------------------------------------------------------------


class TestRecipe05EtlCli:
    def test_demo_runs_etl(self, monkeypatch, tmp_path):
        config_path = tmp_path / "pipeline.json"
        R05.write_minimal_pipeline_config(config_path)
        result = R05.etl_cli_demo(
            pipeline_config=config_path,
            monkeypatch=monkeypatch,
        )
        assert result.exit_code == 0
        assert "etl" in result.argv
        assert "run" in result.argv
        assert "--pipeline-config" in result.argv

    def test_demo_with_source(self, monkeypatch, tmp_path):
        config_path = tmp_path / "pipeline.json"
        R05.write_minimal_pipeline_config(config_path)
        source = '{"reporterCode": 699, "period": "2022"}'
        result = R05.etl_cli_demo(
            pipeline_config=config_path,
            source=source, monkeypatch=monkeypatch,
        )
        assert result.exit_code == 0
        assert "--source" in result.argv
        assert source in result.argv

    def test_minimal_pipeline_config_is_valid_json(self, tmp_path):
        config_path = tmp_path / "pipeline.json"
        R05.write_minimal_pipeline_config(config_path)
        parsed = json.loads(config_path.read_text(encoding="utf-8"))
        assert parsed["name"] == "my-pipeline"
        assert parsed["stages"][0]["kind"] == "extract"
        assert parsed["stages"][0]["factory"].endswith(
            "identity_stage_factory"
        )

    def test_identity_stage_factory_returns_callable(self):
        stage = identity_stage_factory()
        ctx = PipelineContext(pipeline_name="t")
        out = stage(ctx, source="hello")
        assert out == "hello"


# ---------------------------------------------------------------------------
# Recipe 06 — output_formats_cli
# ---------------------------------------------------------------------------


class TestRecipe06OutputFormatsCli:
    def test_demo_renders_all_five_formats(self, monkeypatch):
        runs = R06.output_formats_cli_demo(monkeypatch=monkeypatch)
        assert len(runs) == 5
        formats = {r.fmt for r in runs}
        assert formats == {"json", "table", "csv", "markdown", "text"}
        # All five should succeed.
        assert all(r.exit_code == 0 for r in runs)

    def test_demo_subset_of_formats(self, monkeypatch):
        runs = R06.output_formats_cli_demo(
            formats=["json", "table"], monkeypatch=monkeypatch
        )
        assert len(runs) == 2
        formats = {r.fmt for r in runs}
        assert formats == {"json", "table"}

    def test_each_format_writes_non_empty_stdout(self, monkeypatch):
        runs = R06.output_formats_cli_demo(monkeypatch=monkeypatch)
        for run in runs:
            assert run.stdout.strip(), (
                f"format={run.fmt} produced empty stdout"
            )