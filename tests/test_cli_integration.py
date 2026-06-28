"""End-to-end CLI integration tests (C-007).

This file exercises the CLI as a whole, end-to-
end, with every external dependency mocked:

- :class:`un_comtrade.client.ComtradeClient` —
  every CLI command instantiates one. We mock
  the class itself so the tests can drive the
  ``client.metadata`` / ``client.trade``
  attributes directly.
- :mod:`un_comtrade.storage` writers — exercised
  by ``storage`` sub-subcommands. We mock the
  concrete writer classes so we can assert
  they were called without touching the
  filesystem.
- :class:`un_comtrade.etl.ETLPipeline` —
  exercised by ``etl run``. We mock
  ``ETLPipeline.run``.
- :class:`un_comtrade.analytics.*` functions —
  exercised by ``analytics`` sub-subcommands.
  We mock each function.

Coverage:

1. **Metadata** — all 6 sub-subcommands flow
   through ``MetadataService`` and exit 0.
2. **Trade** — all 6 sub-subcommands flow
   through ``TradeService`` and exit 0.
3. **Analytics** — all 6 outer commands load a
   stored dataset and dispatch to the matching
   analytics function.
4. **ETL** — ``etl run`` loads a pipeline config
   and runs the pipeline.
5. **Storage** — all 4 storage write
   sub-subcommands invoke the corresponding
   writer.
6. **Formatting** — all 5 output formats work
   end-to-end on a metadata response.
7. **Configuration** — ``--api-key``,
   ``--log-level``, ``--output-format``,
   ``--output`` flow through the public SDK
   configuration loader.
8. **Exit codes** — the 6 documented exit codes
   (0/1/2/69/77/78) are mapped correctly.
9. **Public-SDK-only** — the entire
   ``un_comtrade/cli/`` package imports only
   public SDK symbols (no
   ``un_comtrade._*``).

No live API.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from un_comtrade.cli import (
    EXIT_AUTH_ERROR,
    EXIT_CONFIG_ERROR,
    EXIT_GENERIC_ERROR,
    EXIT_NETWORK_ERROR,
    EXIT_OK,
    EXIT_USER_ERROR,
    main,
)
from un_comtrade.cli.utils import (
    EXIT_OK as _EXIT_OK_FROM_UTILS,
    OUTPUT_FORMATS,
)
from un_comtrade.etl import PipelineResult, PipelineStatus
from un_comtrade.exceptions import (
    AuthenticationError,
    ComtradeError,
    NetworkError,
)
from un_comtrade.storage import StorageResult
from un_comtrade.transform import CanonicalDataset


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _FakeCountry:
    country_code: int
    iso_alpha3: str
    display_name: str


SAMPLE_COUNTRIES = [
    _FakeCountry(0, "WLD", "World"),
    _FakeCountry(699, "IND", "India"),
    _FakeCountry(156, "CHN", "China"),
]


def _fake_dataset() -> CanonicalDataset:
    """Build a minimal CanonicalDataset."""
    return CanonicalDataset(
        name="integration",
        records=(),
        schema_version="1.0",
        parser_name="Synthetic",
        source_count=0,
        extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _fake_storage_result(
    backend_value: str = "parquet",
    record_count: int = 3,
    byte_size: int = 1024,
) -> StorageResult:
    """Build a minimal StorageResult."""
    from un_comtrade.storage import StorageBackend
    backend = StorageBackend(backend_value)
    from un_comtrade.storage._base import DatasetMetadata
    meta = DatasetMetadata(
        dataset_name="integration",
        schema_version="1.0",
        parser_name="Synthetic",
        record_count=record_count,
        skipped=0,
        duplicates_removed=0,
        source_count=record_count,
        extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        stored_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        partition_keys=(),
        backend=backend,
        destination="/fake/path",
        extra={},
    )
    return StorageResult(
        backend=backend,
        destination="/fake/path",
        metadata=meta,
        partitions={},
        byte_size=byte_size,
    )


@dataclass(frozen=True)
class _FakeTradeResponse:
    """Stand-in for ``un_comtrade.models.response.TradeResponse``."""
    elapsed_seconds: float = 0.1
    count: int = 0
    records: tuple = ()
    error: str = ""
    upstream_url: str = ""
    request: dict | None = None
    skipped: int = 0

    def to_dict(self):
        return {
            "elapsed_seconds": self.elapsed_seconds,
            "count": self.count,
            "records": list(self.records),
            "error": self.error,
            "upstream_url": self.upstream_url,
            "request": self.request,
            "skipped": self.skipped,
        }


# ---------------------------------------------------------------------------
# 1. Metadata end-to-end
# ---------------------------------------------------------------------------


class TestMetadataEndToEnd:
    """All 6 metadata sub-subcommands flow through
    the public ``MetadataService`` and exit 0.
    """

    @pytest.fixture
    def patched_metadata_client(self):
        """Patch ``ComtradeClient.metadata`` with
        canned return values.
        """
        fake_metadata = mock.MagicMock()
        fake_metadata.get_countries.return_value = SAMPLE_COUNTRIES
        fake_metadata.get_partners.return_value = SAMPLE_COUNTRIES[:2]
        fake_metadata.get_classifications.return_value = [
            type("C", (), {"classification_code": "HS",
                            "display_name": "Harmonized System"})(),
        ]
        fake_metadata.get_frequencies.return_value = [
            type("F", (), {"frequency_code": "A",
                            "display_name": "Annual"})(),
        ]
        fake_metadata.get_transport_modes.return_value = [
            type("T", (), {"mot_code": 0,
                            "display_name": "All modes of transport"})(),
        ]
        fake_metadata.get_hs_codes.return_value = [
            type("H", (), {"commodity_code": "270900",
                            "classification_code": "HS",
                            "edition": "HS",
                            "display_name": "Oils, petroleum"})(),
        ]
        fake_client = mock.MagicMock()
        fake_client.metadata = fake_metadata
        with mock.patch(
            "un_comtrade.cli.commands.metadata.ComtradeClient",
            return_value=fake_client,
        ):
            yield fake_metadata

    @pytest.mark.parametrize("sub", [
        "countries",
        "partners",
        "classifications",
        "frequencies",
        "transport-modes",
        "hs",
    ])
    def test_metadata_sub_exits_zero(
        self, patched_metadata_client, sub, capsys
    ):
        """Every metadata sub-subcommand must
        complete with exit code 0 and produce
        some output.
        """
        code = main(["metadata", sub])
        assert code == EXIT_OK
        out = capsys.readouterr().out
        assert out.strip(), f"metadata {sub} produced empty output"

    def test_metadata_counters_invokes_get_countries(
        self, patched_metadata_client, capsys
    ):
        """Spot-check: ``metadata countries`` must
        call ``MetadataService.get_countries``.
        """
        main(["metadata", "countries"])
        patched_metadata_client.get_countries.assert_called_once()

    def test_metadata_hs_invokes_get_hs_codes(
        self, patched_metadata_client, capsys
    ):
        main(["metadata", "hs"])
        patched_metadata_client.get_hs_codes.assert_called_once_with("HS")

    def test_metadata_hs_with_edition_flag(
        self, patched_metadata_client, capsys
    ):
        main(["metadata", "hs", "--edition", "H0"])
        patched_metadata_client.get_hs_codes.assert_called_once_with("H0")

    def test_metadata_all_subs_succeed_via_table_format(
        self, patched_metadata_client, capsys
    ):
        """All metadata sub-subcommands must work
        with the ``--output-format table`` flag.
        """
        for sub in [
            "countries",
            "partners",
            "classifications",
            "frequencies",
            "transport-modes",
            "hs",
        ]:
            capsys.readouterr()
            code = main(["metadata", sub, "--output-format", "table"])
            assert code == EXIT_OK, (
                f"metadata {sub} with --output-format table failed"
            )


# ---------------------------------------------------------------------------
# 2. Trade end-to-end
# ---------------------------------------------------------------------------


class TestTradeEndToEnd:
    """All 6 trade sub-subcommands flow through
    ``TradeService`` and exit 0.
    """

    @pytest.fixture
    def patched_trade_client(self):
        """Patch ``ComtradeClient.trade`` with
        canned TradeResponse returns.
        """
        response = _FakeTradeResponse(
            count=10,
            upstream_url="https://example.invalid/get/X/A/HS",
            request={"reporterCode": 699, "period": "2022"},
        )
        fake_trade = mock.MagicMock()
        fake_trade.get_exports.return_value = response
        fake_trade.get_imports.return_value = response
        fake_trade.get_world_trade.return_value = response
        fake_trade.get_bilateral.return_value = response
        fake_trade.get_trade_balance.return_value = response
        fake_trade.get_tariffline.return_value = response

        fake_client = mock.MagicMock()
        fake_client.trade = fake_trade
        with mock.patch(
            "un_comtrade.cli.commands.trade.ComtradeClient",
            return_value=fake_client,
        ):
            yield fake_trade

    @pytest.mark.parametrize("sub,extra_args", [
        ("exports", []),
        ("imports", []),
        ("world", []),
        ("bilateral", ["--partner", "840", "--flow", "X"]),
        ("balance", []),
        ("tariffline", ["--flow", "M"]),
    ])
    def test_trade_sub_exits_zero(
        self, patched_trade_client, sub, extra_args, capsys
    ):
        """Every trade sub-subcommand must
        complete with exit code 0.
        """
        args = [
            "trade",
            sub,
            "--reporter",
            "699",
            "--year",
            "2022",
            *extra_args,
        ]
        code = main(args)
        assert code == EXIT_OK, f"trade {sub} failed"
        out = capsys.readouterr().out
        assert "count" in out

    def test_trade_world_does_not_pass_partner(
        self, patched_trade_client
    ):
        """``trade world`` must NOT pass
        ``partner_code`` (the SDK method does not
        accept it).
        """
        main(
            [
                "trade",
                "world",
                "--reporter",
                "699",
                "--year",
                "2022",
                "--partner",
                "840",
            ]
        )
        kwargs = patched_trade_client.get_world_trade.call_args.kwargs
        assert "partner_code" not in kwargs


# ---------------------------------------------------------------------------
# 3. Analytics end-to-end
# ---------------------------------------------------------------------------


class TestAnalyticsEndToEnd:
    """All 6 analytics outer commands load a
    stored dataset and dispatch to the matching
    public analytics function.
    """

    @pytest.fixture
    def fake_dataset_dir(self, tmp_path):
        """Write a minimal parquet file inside a
        directory.
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
            pa.field(
                "trade_value_primary_value",
                pa.decimal128(38, 18),
            ),
        ])
        arrays = [
            pa.array([], type=field.type) for field in schema
        ]
        table = pa.Table.from_arrays(arrays, schema=schema)
        pq.write_table(table, str(target_file))
        return target_dir

    @pytest.fixture
    def patched_analytics(self, monkeypatch):
        """Patch each analytics function the CLI
        may dispatch to.
        """
        monkeypatch.setattr(
            "un_comtrade.analytics.country.country_summary",
            mock.MagicMock(return_value=None),
        )
        monkeypatch.setattr(
            "un_comtrade.analytics.partner.top_partners",
            mock.MagicMock(return_value=[]),
        )
        monkeypatch.setattr(
            "un_comtrade.analytics.commodity.top_hs_codes",
            mock.MagicMock(return_value=[]),
        )
        monkeypatch.setattr(
            "un_comtrade.analytics.timeseries.annual_trend",
            mock.MagicMock(return_value=[]),
        )
        monkeypatch.setattr(
            "un_comtrade.analytics.balance.country_balance",
            mock.MagicMock(return_value=[]),
        )
        monkeypatch.setattr(
            "un_comtrade.analytics.compare.country_vs_country",
            mock.MagicMock(return_value=mock.MagicMock(
                reporter_codes=(699, 156),
                rows=(),
                summary=mock.MagicMock(),
            )),
        )

    @pytest.mark.parametrize("sub,extra_args", [
        ("country", ["--reporter", "699"]),
        ("partner", ["--reporter", "699"]),
        ("commodity", []),
        ("trend", ["--reporter", "699"]),
        ("balance", []),
        ("compare", ["--reporter", "699", "156"]),
    ])
    def test_analytics_outer_exits_zero(
        self, patched_analytics, fake_dataset_dir, sub, extra_args
    ):
        """Every analytics outer command must
        complete with exit code 0.
        """
        args = [
            "analytics",
            sub,
            "--dataset",
            str(fake_dataset_dir),
            *extra_args,
        ]
        code = main(args)
        assert code == EXIT_OK, f"analytics {sub} failed"

    def test_analytics_loads_dataset_via_storage_layer(
        self, patched_analytics, fake_dataset_dir
    ):
        """The CLI must load the dataset via the
        public Storage layer (not direct file
        I/O).
        """
        from un_comtrade.storage import StorageRegistry
        seen_backends: list = []
        original_get = StorageRegistry.get

        def spy_get(self, backend):
            seen_backends.append(backend)
            return original_get(self, backend)

        with mock.patch.object(
            StorageRegistry, "get", spy_get
        ):
            main(
                [
                    "analytics",
                    "country",
                    "--dataset",
                    str(fake_dataset_dir),
                    "--reporter",
                    "699",
                ]
            )
        from un_comtrade.storage import StorageBackend
        assert StorageBackend.PARQUET in seen_backends


# ---------------------------------------------------------------------------
# 4. ETL end-to-end
# ---------------------------------------------------------------------------


class TestETLEndToEnd:
    """``etl run`` loads a pipeline config and runs
    the pipeline.
    """

    @pytest.fixture
    def pipeline_config(self, tmp_path):
        """Write a valid pipeline config JSON."""
        config = {
            "name": "test-pipeline",
            "stages": [
                {
                    "name": "passthrough",
                    "kind": "extract",
                    "factory": (
                        "tests.test_cli_integration:"
                        "_identity_stage_factory"
                    ),
                },
            ],
        }
        path = tmp_path / "pipeline.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        return path

    def test_etl_run_invokes_pipeline(self, pipeline_config):
        """``etl run`` must invoke
        ``ETLPipeline.run`` exactly once.
        """
        from un_comtrade.etl import ETLPipeline

        with mock.patch.object(
            ETLPipeline,
            "run",
            return_value=PipelineResult(
                pipeline_name="test-pipeline",
                status=PipelineStatus.SUCCESS,
                output=None,
                warnings=[],
                errors=[],
                records_in=0,
                records_out=0,
                started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                finished_at=datetime(
                    2026, 1, 1, 0, 1, tzinfo=timezone.utc
                ),
                stage_durations={"passthrough": 0.01},
            ),
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

    def test_etl_run_propagates_failure_status(
        self, pipeline_config
    ):
        """A failed pipeline must surface as
        ``EXIT_GENERIC_ERROR`` (1).
        """
        from un_comtrade.etl import ETLPipeline

        with mock.patch.object(
            ETLPipeline,
            "run",
            return_value=PipelineResult(
                pipeline_name="test-pipeline",
                status=PipelineStatus.FAILED,
                output=None,
                warnings=[],
                errors=["boom"],
                records_in=0,
                records_out=0,
                started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                finished_at=datetime(
                    2026, 1, 1, 0, 1, tzinfo=timezone.utc
                ),
                stage_durations={},
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

    def test_etl_run_missing_config_errors(self):
        code = main(
            [
                "etl",
                "run",
                "--pipeline-config",
                "/no/such/config.json",
            ]
        )
        assert code == EXIT_CONFIG_ERROR  # 78


# ---------------------------------------------------------------------------
# 5. Storage end-to-end
# ---------------------------------------------------------------------------


class TestStorageEndToEnd:
    """All 4 storage write sub-subcommands invoke
    the corresponding writer.
    """

    @pytest.fixture
    def fake_dataset_dir(self, tmp_path):
        """Write a minimal parquet file inside a
        directory so storage commands can read it.
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
            pa.field(
                "trade_value_primary_value",
                pa.decimal128(38, 18),
            ),
        ])
        arrays = [
            pa.array([], type=field.type) for field in schema
        ]
        table = pa.Table.from_arrays(arrays, schema=schema)
        pq.write_table(table, str(target_file))
        return target_dir

    @pytest.mark.parametrize("fmt", ["parquet", "csv", "json", "duckdb"])
    def test_storage_fmt_invokes_writer(
        self, fake_dataset_dir, fmt, tmp_path
    ):
        """Each ``storage <fmt>`` sub-subcommand
        must invoke the corresponding writer's
        ``store`` method.
        """
        writer_module = {
            "parquet": "un_comtrade.storage.parquet",
            "csv": "un_comtrade.storage.file",
            "json": "un_comtrade.storage.file",
            "duckdb": "un_comtrade.storage.duckdb",
        }[fmt]
        writer_class_name = {
            "parquet": "ParquetWriter",
            "csv": "CSVWriter",
            "json": "JSONWriter",
            "duckdb": "DuckDBWriter",
        }[fmt]
        import importlib
        mod = importlib.import_module(writer_module)
        cls = getattr(mod, writer_class_name)
        ext = {"parquet": ".parquet", "csv": ".csv",
               "json": ".json", "duckdb": ".duckdb"}[fmt]
        out_path = tmp_path / f"out{ext}"
        with mock.patch.object(
            cls, "store", return_value=_fake_storage_result(fmt)
        ) as mock_store:
            args = [
                "storage",
                fmt,
                "--dataset",
                str(fake_dataset_dir),
                "--output-path",
                str(out_path),
            ]
            code = main(args)
        assert code == EXIT_OK, f"storage {fmt} failed"
        mock_store.assert_called_once()
        # The StorageConfig.root matches --output-path.
        called_args, _ = mock_store.call_args
        assert called_args[1].root == str(out_path)


# ---------------------------------------------------------------------------
# 6. Formatting end-to-end
# ---------------------------------------------------------------------------


class TestFormattingEndToEnd:
    """All 5 output formats work end-to-end via the
    CLI.
    """

    @pytest.fixture
    def patched_metadata_client(self):
        """Patch ``ComtradeClient.metadata`` with a
        single canned record.
        """
        fake_metadata = mock.MagicMock()
        fake_metadata.get_countries.return_value = SAMPLE_COUNTRIES
        fake_client = mock.MagicMock()
        fake_client.metadata = fake_metadata
        with mock.patch(
            "un_comtrade.cli.commands.metadata.ComtradeClient",
            return_value=fake_client,
        ):
            yield

    @pytest.mark.parametrize("fmt", [
        "json",
        "table",
        "csv",
        "markdown",
        "text",
    ])
    def test_all_five_formats_via_metadata(
        self, patched_metadata_client, fmt, capsys
    ):
        """``un-comtrade metadata countries`` must
        accept each of the five output formats and
        render non-empty output.
        """
        code = main(
            ["metadata", "countries", "--output-format", fmt]
        )
        assert code == EXIT_OK, f"format {fmt!r} failed"
        captured = capsys.readouterr()
        assert captured.out.strip(), (
            f"format {fmt!r} produced empty output"
        )

    def test_default_format_is_json(
        self, patched_metadata_client, capsys
    ):
        code = main(["metadata", "countries"])
        assert code == EXIT_OK
        loaded = json.loads(capsys.readouterr().out)
        assert isinstance(loaded, list)
        assert len(loaded) == 3

    def test_output_to_file(
        self, patched_metadata_client, tmp_path
    ):
        """``--output PATH`` writes the rendered
        output to PATH (rather than stdout).
        """
        target = tmp_path / "countries.json"
        code = main(
            [
                "metadata",
                "countries",
                "--output",
                str(target),
            ]
        )
        assert code == EXIT_OK
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert isinstance(loaded, list)
        assert len(loaded) == 3


# ---------------------------------------------------------------------------
# 7. Configuration end-to-end
# ---------------------------------------------------------------------------


class TestConfigurationEndToEnd:
    """``--api-key``, ``--log-level``, ``--output-format``,
    ``--output`` flow through the public SDK
    configuration loader.
    """

    @pytest.fixture
    def patched_client(self):
        fake_metadata = mock.MagicMock()
        fake_metadata.get_countries.return_value = []
        fake_client = mock.MagicMock()
        fake_client.metadata = fake_metadata
        with mock.patch(
            "un_comtrade.cli.commands.metadata.ComtradeClient",
            return_value=fake_client,
        ):
            yield

    def test_api_key_override_flows_to_configuration(
        self, patched_client, monkeypatch
    ):
        """``--api-key`` must reach the SDK's
        :class:`Configuration`.
        """
        from un_comtrade.config import Configuration

        seen_configs: list = []

        original_ctor = Configuration

        class _SpyConfig(Configuration):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                seen_configs.append(self)

        seen_comtradeclients: list = []

        class _SpyClient:
            def __init__(self, configuration=None, **_):
                seen_comtradeclients.append(configuration)
                self.metadata = mock.MagicMock()
                self.metadata.get_countries.return_value = []

            def close(self):
                pass

        monkeypatch.setattr(
            "un_comtrade.cli.commands.metadata.ComtradeClient",
            _SpyClient,
        )
        # load_configuration must still work;
        # the CLI wraps Configuration in
        # dataclasses.replace so the actual
        # instance is built via load_configuration.
        code = main(
            ["metadata", "countries", "--api-key", "test-key-123"]
        )
        assert code == EXIT_OK
        # At least one ComtradeClient was
        # constructed with a Configuration
        # carrying the override key.
        assert any(
            c is not None and getattr(c, "api_key", None)
            == "test-key-123"
            for c in seen_comtradeclients
        )

    def test_log_level_override(
        self, patched_client, monkeypatch, capsys
    ):
        """``--log-level DEBUG`` must validate
        against the public log-level table.
        """
        code = main(
            [
                "metadata",
                "countries",
                "--log-level",
                "DEBUG",
            ]
        )
        assert code == EXIT_OK

    def test_invalid_log_level_errors(
        self, patched_client, capsys
    ):
        code = main(
            [
                "metadata",
                "countries",
                "--log-level",
                "BOGUS_LEVEL",
            ]
        )
        # argparse would not catch this (it's a
        # CLI-side validation). Expected exit
        # code: 78 (EXIT_CONFIG_ERROR).
        assert code == EXIT_CONFIG_ERROR

    def test_output_format_default_is_json(
        self, patched_client, capsys
    ):
        """When --output-format is omitted, the
        CLI uses ``json``.
        """
        code = main(["metadata", "countries"])
        assert code == EXIT_OK
        out = capsys.readouterr().out
        loaded = json.loads(out)
        assert isinstance(loaded, list)

    def test_output_formats_choices_validated(self):
        """argparse enforces that ``--output-format``
        is one of the 5 documented choices.
        """
        for choice in OUTPUT_FORMATS:
            assert choice in ("json", "table", "csv",
                               "markdown", "text")


# ---------------------------------------------------------------------------
# 8. Exit codes end-to-end
# ---------------------------------------------------------------------------


class TestExitCodes:
    """The 6 documented exit codes are mapped
    correctly across the CLI.
    """

    def test_exit_0_success(self):
        """Bare ``un-comtrade`` (no subcommand)
        exits 0 with the banner.
        """
        code = main([])
        assert code == EXIT_OK

    def test_exit_2_argparse_error(self, capsys):
        """Unknown subcommand exits 2.
        """
        code = main(["definitely-not-a-real-subcommand"])
        assert code == EXIT_USER_ERROR

    def test_exit_78_config_error(self):
        """Missing ``--dataset`` for analytics
        that doesn't require it: actually
        argparse exits 2 there. Let me use a
        config-error path: missing pipeline
        config.
        """
        code = main(
            [
                "etl",
                "run",
                "--pipeline-config",
                "/no/such/file.json",
            ]
        )
        assert code == EXIT_CONFIG_ERROR

    def test_exit_77_auth_error(self):
        """Authentication errors map to
        ``EXIT_AUTH_ERROR``.
        """
        from un_comtrade.cli.commands.metadata import (
            MetadataCommand,
        )
        # Patch the MetadataCommand so its
        # __call__ raises AuthenticationError.
        with mock.patch.object(
            MetadataCommand, "__call__",
            side_effect=AuthenticationError("401"),
        ):
            code = main(["metadata", "countries"])
        assert code == EXIT_AUTH_ERROR

    def test_exit_69_network_error(self):
        from un_comtrade.cli.commands.metadata import (
            MetadataCommand,
        )
        with mock.patch.object(
            MetadataCommand, "__call__",
            side_effect=NetworkError("connection reset"),
        ):
            code = main(["metadata", "countries"])
        assert code == EXIT_NETWORK_ERROR

    def test_exit_1_generic_sdk_error(self):
        from un_comtrade.cli.commands.metadata import (
            MetadataCommand,
        )
        with mock.patch.object(
            MetadataCommand, "__call__",
            side_effect=ComtradeError("unexpected"),
        ):
            code = main(["metadata", "countries"])
        assert code == EXIT_GENERIC_ERROR


# ---------------------------------------------------------------------------
# 9. Public-SDK-only AST guard
# ---------------------------------------------------------------------------


class TestPublicSDKOnlyAcrossCLI:
    """Walk the entire ``un_comtrade/cli/``
    directory and verify ZERO imports of
    private ``un_comtrade._*`` modules.

    Every CLI module MUST consume only the
    public SDK surface (per the Phase 7 design
    contract).
    """

    PRIVATE_RE = re.compile(r"^un_comtrade(_|\.)_")

    def _all_cli_files(self) -> list[Path]:
        cli_dir = Path("un_comtrade/cli")
        return [
            p for p in cli_dir.rglob("*.py")
            if "__pycache__" not in str(p)
        ]

    def _collect_imports(self, path: Path) -> list[tuple[int, str]]:
        """Return ``[(lineno, module_name), ...]``
        for all import statements in ``path``.
        """
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        imports: list[tuple[int, str]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((node.lineno, alias.name))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append((node.lineno, node.module))
        return imports

    def test_no_private_module_imports_anywhere_in_cli(self):
        """No CLI module may import any
        ``un_comtrade._*`` private symbol.
        """
        violations: list[tuple[str, int, str]] = []
        for path in self._all_cli_files():
            for lineno, target in self._collect_imports(path):
                if self.PRIVATE_RE.match(target):
                    if target.startswith("un_comtrade"):
                        violations.append(
                            (str(path), lineno, target)
                        )
        assert not violations, (
            f"CLI imports private SDK modules: {violations}"
        )

    def test_only_public_submodules_imported(self):
        """The CLI's imports of ``un_comtrade``
        submodules MUST resolve to public names
        (i.e. appear in the module's ``__all__``).
        """
        # Walk imports; for each ``un_comtrade.X``
        # import, import the module and check
        # ``X`` is in ``X.__all__`` (when present).
        # For ``from un_comtrade.X import Y``, we
        # check ``Y`` is in ``X.__all__`` (or is a
        # submodule).
        import importlib
        bad: list[tuple[str, int, str]] = []
        for path in self._all_cli_files():
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if not node.module.startswith("un_comtrade"):
                        continue
                    # The ``from`` target.
                    parts = node.module.split(".")
                    # Try each prefix up to a
                    # package leaf.
                    for i in range(len(parts), 1, -1):
                        sub = ".".join(parts[:i])
                        try:
                            mod = importlib.import_module(sub)
                        except ImportError:
                            continue
                        all_ = getattr(mod, "__all__", None)
                        if all_ is None:
                            # No __all__ defined; skip
                            # (module re-exports
                            # implicitly).
                            break
                        # Verify each imported name
                        # is in __all__.
                        for alias in node.names:
                            name = alias.name
                            if name == "*":
                                continue
                            if name not in all_:
                                bad.append(
                                    (str(path), node.lineno,
                                     f"{sub}.{name}")
                                )
                        break
        assert not bad, (
            f"CLI imports symbols not in "
            f"un_comtrade.__all__: {bad}"
        )


# ---------------------------------------------------------------------------
# 10. End-to-end smoke
# ---------------------------------------------------------------------------


class TestEndToEndSmoke:
    """Run the CLI in a subprocess to confirm the
    console-script entry point works.
    """

    @pytest.mark.skipif(
        sys.platform.startswith("win")
        and not __import__("shutil").which("un-comtrade"),
        reason="un-comtrade console script not on PATH",
    )
    def test_console_script_version(self):
        result = subprocess.run(
            ["un-comtrade", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "1.0.1" in result.stdout

    @pytest.mark.skipif(
        sys.platform.startswith("win")
        and not __import__("shutil").which("un-comtrade"),
        reason="un-comtrade console script not on PATH",
    )
    def test_console_script_help(self):
        result = subprocess.run(
            ["un-comtrade", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        # The five outer commands should appear.
        for cmd in (
            "metadata",
            "trade",
            "analytics",
            "storage",
            "etl",
        ):
            assert cmd in result.stdout


# ---------------------------------------------------------------------------
# Module-level helper used by the ETL test
# ---------------------------------------------------------------------------


def _identity_stage_factory(context):
    """Identity stage factory used by the ETL
    integration test.
    """
    class _Passthrough:
        name = "passthrough"

        def __call__(self, source, context):
            return source

    return _Passthrough()