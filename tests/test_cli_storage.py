"""Tests for the C-005 storage + etl CLI commands.

The storage commands call into the public
``un_comtrade.storage`` writers. The etl command
calls into the public
``un_comtrade.etl.ETLPipeline``. Both are
mocked so no live storage or pipeline work
runs in-process.

Tests verify:

- Each ``storage <fmt>`` subcommand invokes the
  corresponding public writer's ``store``
  method.
- Each ``storage <fmt>`` subcommand passes a
  valid ``StorageConfig`` rooted at the
  ``--output-path``.
- The CLI performs orchestration only (static
  check: no row-by-row processing, no manual
  file I/O, no DuckDB / parquet-specific
  knowledge).
- ``etl run`` builds a public ``ETLPipeline``
  from a JSON config and calls ``run``.
- Stage factories are imported by dotted path;
  the CLI never hard-codes a stage.
- Exit codes are mapped correctly.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from un_comtrade.cli import (
    EXIT_GENERIC_ERROR,
    EXIT_OK,
    main,
)
from un_comtrade.cli.commands.etl import ETLCommand
from un_comtrade.cli.commands.storage import StorageCommand
from un_comtrade.etl import (
    ETLPipeline,
    PipelineResult,
    PipelineStatus,
    StageKind,
)
from un_comtrade.storage import StorageBackend, StorageResult
from un_comtrade.transform import CanonicalDataset


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_dataset_dir(tmp_path) -> Path:
    """Write a minimal on-disk parquet file
    inside a directory.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    target_dir = tmp_path / "fixture"
    target_dir.mkdir()
    target_file = target_dir / "data.parquet"
    schema = pa.schema([
        pa.field("ref_period_id", pa.int64()),
        pa.field("reporter_code", pa.int32()),
        pa.field("partner_code", pa.int32()),
        pa.field("flow_code", pa.string()),
        pa.field("commodity_code", pa.string()),
        pa.field("trade_value_primary_value", pa.decimal128(38, 18)),
    ])
    arrays = [
        pa.array([], type=field.type) for field in schema
    ]
    table = pa.Table.from_arrays(arrays, schema=schema)
    pq.write_table(table, str(target_file))
    return target_dir


def _fake_result() -> StorageResult:
    return StorageResult(
        backend=StorageBackend.PARQUET,
        destination="/fake/path",
        byte_size=1024,
        partitions={},
        metadata=__import__(
            "un_comtrade.storage._base", fromlist=["DatasetMetadata"]
        ).DatasetMetadata(
            dataset_name="cli-test",
            schema_version="1.0",
            parser_name="Synthetic",
            record_count=3,
            skipped=0,
            duplicates_removed=0,
            source_count=3,
            extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            stored_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            partition_keys=(),
            backend=StorageBackend.PARQUET,
            destination="/fake/path",
            extra={},
        ),
    )


# ---------------------------------------------------------------------------
# Registration / parser shape
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_storage_command_registered(self):
        from un_comtrade.cli.commands import get_command
        assert isinstance(get_command("storage"), StorageCommand)

    def test_etl_command_registered(self):
        from un_comtrade.cli.commands import get_command
        assert isinstance(get_command("etl"), ETLCommand)

    def test_storage_help_lists_four_subs(self, capsys):
        main(["storage", "--help"])
        out = capsys.readouterr().out
        for sub in ("parquet", "csv", "json", "duckdb"):
            assert sub in out

    def test_etl_help_lists_run(self, capsys):
        main(["etl", "--help"])
        out = capsys.readouterr().out
        assert "run" in out


# ---------------------------------------------------------------------------
# Storage command — each subcommand
# ---------------------------------------------------------------------------


class TestStorageParquet:
    def test_invokes_parquet_writer_store(
        self, monkeypatch, fake_dataset_dir, tmp_path, capsys
    ):
        from un_comtrade.storage.parquet import ParquetWriter
        output_path = tmp_path / "out.parquet"
        # Mock the writer class so we don't
        # depend on the broken ParquetWriter.store
        # behaviour in this environment.
        with mock.patch.object(
            ParquetWriter, "store", return_value=_fake_result()
        ) as mock_store:
            code = main(
                [
                    "storage",
                    "parquet",
                    "--dataset",
                    str(fake_dataset_dir),
                    "--output-path",
                    str(output_path),
                ]
            )
        assert code == EXIT_OK
        mock_store.assert_called_once()
        # First arg: dataset, second: StorageConfig
        args, _kwargs = mock_store.call_args
        assert isinstance(args[0], CanonicalDataset)
        assert args[1].root == str(output_path)


class TestStorageCSV:
    def test_invokes_csv_writer_store(
        self, monkeypatch, fake_dataset_dir, tmp_path, capsys
    ):
        from un_comtrade.storage.file import CSVWriter
        with mock.patch.object(
            CSVWriter, "store", return_value=_fake_result()
        ) as mock_store:
            code = main(
                [
                    "storage",
                    "csv",
                    "--dataset",
                    str(fake_dataset_dir),
                    "--output-path",
                    str(tmp_path / "out.csv"),
                ]
            )
        assert code == EXIT_OK
        mock_store.assert_called_once()


class TestStorageJSON:
    def test_invokes_json_writer_store(
        self, monkeypatch, fake_dataset_dir, tmp_path, capsys
    ):
        from un_comtrade.storage.file import JSONWriter
        with mock.patch.object(
            JSONWriter, "store", return_value=_fake_result()
        ) as mock_store:
            code = main(
                [
                    "storage",
                    "json",
                    "--dataset",
                    str(fake_dataset_dir),
                    "--output-path",
                    str(tmp_path / "out.json"),
                ]
            )
        assert code == EXIT_OK
        mock_store.assert_called_once()


class TestStorageDuckDB:
    def test_invokes_duckdb_writer_store(
        self, monkeypatch, fake_dataset_dir, tmp_path, capsys
    ):
        from un_comtrade.storage.duckdb import DuckDBWriter
        with mock.patch.object(
            DuckDBWriter, "store", return_value=_fake_result()
        ) as mock_store:
            code = main(
                [
                    "storage",
                    "duckdb",
                    "--dataset",
                    str(fake_dataset_dir),
                    "--output-path",
                    str(tmp_path / "out.duckdb"),
                    "--table-name",
                    "trade",
                ]
            )
        assert code == EXIT_OK
        mock_store.assert_called_once()
        args, _ = mock_store.call_args
        assert args[1].table_name == "trade"


# ---------------------------------------------------------------------------
# Storage orchestration
# ---------------------------------------------------------------------------


class TestStorageOrchestration:
    def test_overwrite_flag_propagates(
        self, monkeypatch, fake_dataset_dir, tmp_path
    ):
        from un_comtrade.storage.parquet import ParquetWriter
        with mock.patch.object(
            ParquetWriter, "store", return_value=_fake_result()
        ) as mock_store:
            main(
                [
                    "storage",
                    "parquet",
                    "--dataset",
                    str(fake_dataset_dir),
                    "--output-path",
                    str(tmp_path / "x.parquet"),
                    "--overwrite",
                ]
            )
        args, _ = mock_store.call_args
        assert args[1].overwrite is True

    def test_missing_output_path_errors(self, fake_dataset_dir):
        code = main(
            [
                "storage",
                "parquet",
                "--dataset",
                str(fake_dataset_dir),
            ]
        )
        assert code == 2  # argparse EXIT_USER_ERROR

    def test_unknown_subsubcommand_errors(self):
        code = main(["storage", "not-a-real-fmt"])
        assert code == 2


# ---------------------------------------------------------------------------
# etl run
# ---------------------------------------------------------------------------


class TestETLRun:
    @pytest.fixture
    def pipeline_config(self, tmp_path) -> Path:
        """Write a valid pipeline config JSON."""
        # We use a real importable factory for the
        # tests: an identity factory shipped in the
        # test module itself.
        config = {
            "name": "test-pipeline",
            "stages": [
                {
                    "name": "passthrough",
                    "kind": "extract",
                    "factory": (
                        "tests.test_cli_storage:"
                        "_identity_stage_factory"
                    ),
                },
            ],
        }
        path = tmp_path / "pipeline.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        return path

    def test_invokes_etlpipeline_run(
        self, pipeline_config, monkeypatch, capsys
    ):
        # ETLPipeline is built fresh per run, so we
        # patch its run method instead.
        with mock.patch.object(
            ETLPipeline, "run",
            return_value=_fake_pipeline_result(),
        ) as mock_run:
            code = main(
                [
                    "etl",
                    "run",
                    "--pipeline-config",
                    str(pipeline_config),
                ]
            )
        assert code == EXIT_OK
        mock_run.assert_called_once()

    def test_missing_pipeline_config_errors(self):
        code = main(
            [
                "etl",
                "run",
                "--pipeline-config",
                "/no/such/config.json",
            ]
        )
        # CLIConfigurationError → EXIT_CONFIG_ERROR (78)
        assert code == 78

    def test_invalid_json_errors(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{ not json", encoding="utf-8")
        code = main(
            [
                "etl",
                "run",
                "--pipeline-config",
                str(bad),
            ]
        )
        assert code == 78

    def test_pipeline_failure_returns_generic_error(
        self, pipeline_config, monkeypatch, capsys
    ):
        with mock.patch.object(
            ETLPipeline,
            "run",
            return_value=_fake_pipeline_result(
                status=PipelineStatus.FAILED,
                errors=["boom"],
            ),
        ):
            code = main(
                [
                    "etl",
                    "run",
                    "--pipeline-config",
                    str(pipeline_config),
                ]
            )
        assert code == EXIT_GENERIC_ERROR

    def test_unknown_etl_subsubcommand_errors(self):
        code = main(["etl", "not-a-real-sub"])
        assert code == 2


# ---------------------------------------------------------------------------
# "CLI performs orchestration only" guard
# ---------------------------------------------------------------------------


class TestOrchestrationOnly:
    """Static checks confirming the CLI does NOT
    implement storage or ETL logic — it only
    delegates to the public SDK.
    """

    FORBIDDEN_KEYWORDS = re.compile(
        # Operations that imply storage
        # implementation (NOT class names):
        # - pyarrow type constructors
        # - duckdb.connect / duckdb.execute
        # - .to_pylist / .to_parquet / .write_parquet
        # - low-level open() with binary modes
        # - direct file writes via Path.write_text
        r"(?:"
        r"pyarrow\.(?:Table|Array|Schema|field|array|record_batch)"
        r"|duckdb\.(?:connect|execute|sql)"
        r"|\.to_pylist\(|\.to_parquet\(|\.write_parquet\("
        r"|open\([^)]*['\"](?:wb|w|rb|a|ab)\b"
        r"|Path\([^)]*\)\.write_text|Path\([^)]*\)\.write_bytes"
        r")",
        re.IGNORECASE,
    )

    def test_storage_command_has_no_storage_implementation(self):
        path = Path("un_comtrade/cli/commands/storage.py")
        source = path.read_text(encoding="utf-8")
        # Strip docstrings.
        import ast
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(
                node,
                (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                 ast.ClassDef),
            ):
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    node.body.pop(0)
                    if not node.body:
                        node.body.append(ast.Pass())
        cleaned = ast.unparse(tree)
        match = self.FORBIDDEN_KEYWORDS.search(cleaned)
        assert not match, (
            f"storage.py contains forbidden keyword "
            f"{match.group()!r}; the CLI must not "
            f"implement storage"
        )

    def test_etl_command_has_no_pipeline_implementation(self):
        path = Path("un_comtrade/cli/commands/etl.py")
        source = path.read_text(encoding="utf-8")
        import ast
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(
                node,
                (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                 ast.ClassDef),
            ):
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    node.body.pop(0)
                    if not node.body:
                        node.body.append(ast.Pass())
        cleaned = ast.unparse(tree)
        match = self.FORBIDDEN_KEYWORDS.search(cleaned)
        assert not match, (
            f"etl.py contains forbidden keyword "
            f"{match.group()!r}; the CLI must not "
            f"implement pipeline logic"
        )


# ---------------------------------------------------------------------------
# Public-SDK-only constraint
# ---------------------------------------------------------------------------


class TestStorageETLPublicSDKOnly:
    PRIVATE_RE = re.compile(r"^un_comtrade(_|\.)_")

    @pytest.mark.parametrize("path", [
        "un_comtrade/cli/commands/storage.py",
        "un_comtrade/cli/commands/etl.py",
    ])
    def test_no_private_imports(self, path):
        import ast
        source = Path(path).read_text(encoding="utf-8")
        tree = ast.parse(source)
        violations = []
        for node in ast.walk(tree):
            target = None
            if isinstance(node, ast.Import):
                target = node.names[0].name
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    target = node.module
            if target and self.PRIVATE_RE.match(target):
                if target.startswith("un_comtrade"):
                    violations.append((node.lineno, target))
        assert not violations, (
            f"{path} imports private SDK modules: "
            f"{violations}"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_pipeline_result(
    *,
    status: PipelineStatus = PipelineStatus.SUCCESS,
    errors: list[str] | None = None,
) -> PipelineResult:
    """Build a minimal ``PipelineResult``."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return PipelineResult(
        pipeline_name="test-pipeline",
        status=status,
        output=None,
        warnings=[],
        errors=errors or [],
        records_in=0,
        records_out=0,
        started_at=now,
        finished_at=now,
        stage_durations={"passthrough": 0.01},
    )


# Module-level helper used by ``TestETLRun``.
# Defined here so the ``factory`` dotted path in
# the test config can import it.
def _identity_stage_factory(context):
    """A minimal stage factory: returns a stage
    that passes its input through unchanged.
    """
    class _Passthrough:
        name = "passthrough"

        def __call__(self, source, context):
            context.records_in = (
                context.records_in or len(source) if source else 0
            )
            context.records_out = context.records_in
            return source

    return _Passthrough()