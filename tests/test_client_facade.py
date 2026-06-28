"""FC-001 — ComtradeClient public facade regression tests.

The CLI Contract Verification (docs/033) established that the
`ComtradeClient` should expose five service attributes:

- ``client.metadata``  → `MetadataService`
- ``client.trade``     → `TradeService`
- ``client.analytics`` → `AnalyticsEngine`
- ``client.etl``       → `ETLFacade`
- ``client.storage``   → `StorageRegistry`

This module pins that contract.

What the tests verify
---------------------
1.  Every facade attribute exists on a fresh `ComtradeClient`.
2.  Every facade attribute returns an instance of the documented
    public type (no MagicMocks, no placeholders).
3.  Repeated access returns the **same** instance (per-client
    singleton — no duplicate services).
4.  The CLI's real production code path works against the real
    facade: `client.trade.get_exports(...)`, `client.etl.pipeline(...)`,
    and `client.storage.open(...)` all succeed end-to-end against
    an `httpx.MockTransport`-backed transport.
5.  The ``ComtradeClient(api_key="...")`` string shortcut still
    resolves.
6.  Each facade attribute is overridable via the constructor for
    advanced consumers.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

import un_comtrade
from un_comtrade import ComtradeClient
from un_comtrade.analytics import AnalyticsEngine
from un_comtrade.config import Configuration
from un_comtrade.etl import ETLFacade, ETLPipeline
from un_comtrade.metadata import MetadataService
from un_comtrade.storage._base import (
    StorageBackend,
    StorageRegistry,
)
from un_comtrade.trade import TradeService
from un_comtrade.transport import (
    HttpTransport,
    RetryPolicy,
    TimeoutConfig,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_transport() -> HttpTransport:
    """An ``HttpTransport`` whose ``send`` round-trips through an
    ``httpx.MockTransport`` so we never touch the network."""

    def handler(request: httpx.Request) -> httpx.Response:
        # Trade catalogue / metadata catalogue / etc. all share the
        # same minimal empty-list response shape.
        return httpx.Response(
            200,
            json={"data": [], "records": [], "count": 0, "elapsed": 0.1},
        )

    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    return HttpTransport(
        base_url="https://example.invalid",
        user_agent="fc-001-test",
        api_key="test-key",
        client=mock_client,
        retry=RetryPolicy(attempts=1, initial_delay=0.1),
        timeout=TimeoutConfig(default=5.0),
    )


@pytest.fixture
def client(mock_transport: HttpTransport) -> ComtradeClient:
    """A fresh `ComtradeClient` with the mock transport injected."""
    return ComtradeClient(transport=mock_transport)


# ---------------------------------------------------------------------------
# Existence + typing
# ---------------------------------------------------------------------------


class TestFacadeAttributesExist:
    """Every documented facade attribute exists and is reachable."""

    @pytest.mark.parametrize(
        "attr",
        ["metadata", "trade", "analytics", "etl", "storage"],
    )
    def test_attribute_exists(
        self, client: ComtradeClient, attr: str
    ) -> None:
        assert hasattr(client, attr), f"client.{attr} is missing"

    def test_metadata_is_metadata_service(
        self, client: ComtradeClient
    ) -> None:
        assert isinstance(client.metadata, MetadataService)

    def test_trade_is_trade_service(self, client: ComtradeClient) -> None:
        assert isinstance(client.trade, TradeService)

    def test_analytics_is_analytics_engine(
        self, client: ComtradeClient
    ) -> None:
        assert isinstance(client.analytics, AnalyticsEngine)

    def test_etl_is_etl_facade(self, client: ComtradeClient) -> None:
        assert isinstance(client.etl, ETLFacade)

    def test_storage_is_storage_registry(
        self, client: ComtradeClient
    ) -> None:
        assert isinstance(client.storage, StorageRegistry)


# ---------------------------------------------------------------------------
# Singleton semantics
# ---------------------------------------------------------------------------


class TestFacadeSingletons:
    """Each facade attribute is constructed lazily once per client.
    Repeated access returns the SAME instance — no duplicate services."""

    @pytest.mark.parametrize(
        "attr",
        ["metadata", "trade", "analytics", "etl", "storage"],
    )
    def test_repeated_access_returns_same_instance(
        self, client: ComtradeClient, attr: str
    ) -> None:
        first = getattr(client, attr)
        second = getattr(client, attr)
        assert first is second, (
            f"client.{attr} must be a per-client singleton"
        )


# ---------------------------------------------------------------------------
# Construction-side overrides
# ---------------------------------------------------------------------------


class TestFacadeOverrides:
    """Every facade attribute is overridable via the constructor for
    advanced consumers (e.g. test suites, custom registries)."""

    def test_metadata_service_override(self, mock_transport: HttpTransport) -> None:
        sentinel = MetadataService(mock_transport)
        c = ComtradeClient(transport=mock_transport, metadata_service=sentinel)
        assert c.metadata is sentinel

    def test_trade_service_override(self, mock_transport: HttpTransport) -> None:
        sentinel = TradeService(transport=mock_transport)
        c = ComtradeClient(transport=mock_transport, trade_service=sentinel)
        assert c.trade is sentinel

    def test_analytics_engine_override(
        self, mock_transport: HttpTransport
    ) -> None:
        sentinel = AnalyticsEngine(name="sentinel")
        c = ComtradeClient(transport=mock_transport, analytics_engine=sentinel)
        assert c.analytics is sentinel

    def test_etl_facade_override(self, mock_transport: HttpTransport) -> None:
        sentinel = ETLFacade(configuration={"log_level": "DEBUG"})
        c = ComtradeClient(transport=mock_transport, etl_facade=sentinel)
        assert c.etl is sentinel

    def test_storage_registry_override(
        self, mock_transport: HttpTransport
    ) -> None:
        sentinel = StorageRegistry()
        c = ComtradeClient(transport=mock_transport, storage_registry=sentinel)
        assert c.storage is sentinel


# ---------------------------------------------------------------------------
# End-to-end behaviour against the real facade
# ---------------------------------------------------------------------------


class TestFacadeEndToEnd:
    """The CLI's real production code path works against the real
    facade. These tests use ``httpx.MockTransport`` for the HTTP
    layer; everything else is the actual public SDK."""

    def test_trade_get_exports_runs_end_to_end(
        self, client: ComtradeClient
    ) -> None:
        response = client.trade.get_exports(699, "2022")
        assert response.count == 0
        # ``to_dict`` is the public serialisation boundary used by
        # the CLI's trade commands.
        d = response.to_dict()
        assert d["count"] == 0
        assert d["records"] == []

    def test_analytics_engine_inherits_client_name(
        self, client: ComtradeClient
    ) -> None:
        assert client.analytics.name == "comtrade"

    def test_etl_pipeline_builds_with_client_config(
        self, client: ComtradeClient
    ) -> None:
        pipeline = client.etl.pipeline("noop", ())
        assert isinstance(pipeline, ETLPipeline)
        assert pipeline.name == "noop"

    def test_storage_registry_supports_all_five_backends(
        self, client: ComtradeClient
    ) -> None:
        backends = {b.value for b in client.storage.supported_backends()}
        assert backends == {
            "local_files",
            "json",
            "csv",
            "parquet",
            "duckdb",
        }

    def test_storage_get_returns_engine_for_each_backend(
        self, client: ComtradeClient
    ) -> None:
        for backend in (
            StorageBackend.JSON,
            StorageBackend.CSV,
            StorageBackend.PARQUET,
            StorageBackend.DUCKDB,
        ):
            storage = client.storage.get(backend)
            assert storage is not None
            assert storage.backend is backend

    def test_storage_open_reads_csv_dataset(
        self, client: ComtradeClient, tmp_path: Any
    ) -> None:
        """``StorageRegistry.open`` is the public read path; it
        must dispatch by file extension and return a
        ``CanonicalDataset``."""
        # Build a directory layout (CSV + sidecar) that the
        # CLI's `load_dataset` already accepts.
        ds_dir = tmp_path / "tiny"
        ds_dir.mkdir()
        (ds_dir / "records.csv").write_text(
            "ref_period_id,reporter_code,partner_code,flow_code,"
            "commodity_code,primary_value\n"
            "2022,699,0,X,TOTAL,100\n",
            encoding="utf-8",
        )
        (ds_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "dataset_name": "tiny",
                    "schema_version": "1.0.0",
                    "record_count": 1,
                }
            ),
            encoding="utf-8",
        )
        dataset = client.storage.open(ds_dir)
        # Sanity: open() returned a CanonicalDataset (the exact
        # dataset_name comes from the writer's sidecar; here we
        # only verify the open() dispatch path works end-to-end).
        assert dataset is not None
        assert hasattr(dataset, "records")
        assert hasattr(dataset, "name")


# ---------------------------------------------------------------------------
# Construction ergonomics
# ---------------------------------------------------------------------------


class TestConstructionErgonomics:
    """``ComtradeClient(api_key="...")`` is the documented
    string-shortcut form."""

    def test_string_shortcut(
        self, mock_transport: HttpTransport
    ) -> None:
        c = ComtradeClient("test-key", transport=mock_transport)
        assert isinstance(c.config, Configuration)
        assert c.config.api_key == "test-key"

    def test_top_level_import(self) -> None:
        """``from un_comtrade import ComtradeClient`` works."""
        assert un_comtrade.ComtradeClient is ComtradeClient

    def test_legacy_import_path(self) -> None:
        """``from un_comtrade.client import ComtradeClient`` still
        works (backward-compatible)."""
        from un_comtrade.client import ComtradeClient as Legacy
        assert Legacy is ComtradeClient


# ---------------------------------------------------------------------------
# CLI without mocking missing attributes (the FC-001 validation gate)
# ---------------------------------------------------------------------------


class TestCLIRunsAgainstRealFacade:
    """The CLI's real production code path works against the real
    `ComtradeClient` — i.e. ``ComtradeClient()`` is injected into
    the CLI command module, no attribute patching required.

    These tests are the FC-001 acceptance criteria from the task
    brief: "CLI executes without mocking missing attributes."
    """

    def test_metadata_command_uses_real_client(
        self,
        mock_transport: HttpTransport,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # Inject the REAL ComtradeClient (with the real mock-backed
        # transport) into the metadata command module. No patching
        # of `client.metadata`.
        from un_comtrade.cli.commands import metadata as cli_meta
        from un_comtrade.cli.main import main as cli_entry

        real_client = ComtradeClient(transport=mock_transport)
        monkeypatch.setattr(
            cli_meta, "ComtradeClient", lambda *a, **kw: real_client
        )
        code = cli_entry(["metadata", "countries"])
        out = capsys.readouterr()
        assert code == 0, f"exit {code}\nstderr:\n{out.err}\nstdout:\n{out.out}"

    def test_trade_command_uses_real_client(
        self,
        mock_transport: HttpTransport,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from un_comtrade.cli.commands import trade as cli_trade
        from un_comtrade.cli.main import main as cli_entry

        real_client = ComtradeClient(transport=mock_transport)
        monkeypatch.setattr(
            cli_trade, "ComtradeClient", lambda *a, **kw: real_client
        )
        code = cli_entry(
            [
                "trade", "exports",
                "--reporter", "699",
                "--year", "2022",
                "--api-key", "test-key",
            ]
        )
        out = capsys.readouterr()
        assert code == 0, f"exit {code}\nstderr:\n{out.err}\nstdout:\n{out.out}"

    def test_no_private_module_imports_in_facade(
        self, client: ComtradeClient
    ) -> None:
        """A diagnostic check: the facade imports nothing from a
        private module. (Catches accidental regressions to the
        public-only discipline.)"""
        import ast
        import glob

        for path in glob.glob("un_comtrade/client.py"):
            tree = ast.parse(open(path, encoding="utf-8").read())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("un_comtrade._"):
                        raise AssertionError(
                            f"client.py imports private module {node.module!r}"
                        )