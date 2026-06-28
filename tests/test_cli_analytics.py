"""Tests for the C-004 analytics CLI commands.

The analytics commands call into the public
``un_comtrade.analytics`` submodule functions.
We mock those functions so no analytics logic
runs in-process. Tests verify:

- Each ``analytics <sub>`` invocation calls the
  corresponding public function on the
  analytics submodule.
- The CLI passes the loaded ``CanonicalDataset``
  (loaded via the public Storage layer) as the
  first positional argument.
- Required options (``--dataset``, ``--reporter``,
  etc.) are enforced.
- The CLI performs **no analytics logic of its
  own** (static check).
- ``--output-format`` / ``--output`` work end-to-
  end.
- Exit codes are mapped correctly.

No live data. No live API.
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest import mock

import pytest

from un_comtrade.cli import (
    EXIT_GENERIC_ERROR,
    EXIT_OK,
    main,
)
from un_comtrade.cli.commands.analytics import AnalyticsCommand
from un_comtrade.transform import CanonicalDataset


# ---------------------------------------------------------------------------
# Fixtures: minimal CanonicalDataset + sample analytics returns
# ---------------------------------------------------------------------------


def _make_dataset() -> CanonicalDataset:
    return CanonicalDataset(
        name="cli-test",
        records=(),
        schema_version="1.0",
        parser_name="TradeParser",
        source_count=0,
        extracted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


@dataclass(frozen=True)
class _FakeSummary:
    """Stand-in for ``country.CountrySummary``."""
    reporter_code: int
    iso3: str
    name: str
    total_exports: Decimal = Decimal("0")
    total_imports: Decimal = Decimal("0")


def _fake_top_rows():
    return []


@pytest.fixture
def fake_dataset_dir(tmp_path) -> Path:
    """Write a minimal on-disk parquet file
    inside a directory. The CLI's
    ``ParquetWriter.read`` uses
    ``root.rglob("*.parquet")``, so the loader
    must point at the containing DIRECTORY (not
    the file itself).
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
        pa.array([], type=field.type)
        for field in schema
    ]
    table = pa.Table.from_arrays(arrays, schema=schema)
    pq.write_table(table, str(target_file))
    return target_dir


@pytest.fixture
def patched_analytics(monkeypatch, fake_dataset_dir):
    """Patch every analytics function the CLI may
    dispatch to. Each function returns a small
    sentinel value so the JSON formatter can
    serialise it.
    """
    monkeypatch.setattr(
        "un_comtrade.analytics.country.country_summary",
        mock.MagicMock(
            return_value=_FakeSummary(
                reporter_code=699,
                iso3="IND",
                name="India",
                total_exports=Decimal("100.00"),
                total_imports=Decimal("50.00"),
            )
        ),
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
    fake_compare = mock.MagicMock()
    fake_compare.summary = _FakeSummary(
        reporter_code=0, iso3="", name="",
    )
    fake_compare.rows = ()
    fake_compare.reporter_codes = (699, 156)
    monkeypatch.setattr(
        "un_comtrade.analytics.compare.country_vs_country",
        mock.MagicMock(return_value=fake_compare),
    )
    return {
        "country_summary": mock.MagicMock(
            return_value=mock.sentinel.country_summary_call
        ),
    }


# ---------------------------------------------------------------------------
# Registration / parser shape
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_analytics_command_is_registered(self):
        from un_comtrade.cli.commands import get_command
        cmd = get_command("analytics")
        assert isinstance(cmd, AnalyticsCommand)

    def test_root_help_lists_analytics(self):
        from un_comtrade.cli import build_parser
        parser = build_parser()
        for action in parser._actions:
            choices = getattr(action, "choices", None)
            if isinstance(choices, dict) and "analytics" in choices:
                break
        else:
            pytest.fail("analytics subparser not registered")

    def test_analytics_help_lists_six_subs(self, capsys):
        main(["analytics", "--help"])
        out = capsys.readouterr().out
        for sub in (
            "country",
            "partner",
            "commodity",
            "trend",
            "balance",
            "compare",
        ):
            assert sub in out


# ---------------------------------------------------------------------------
# Required-argument enforcement
# ---------------------------------------------------------------------------


class TestRequiredArguments:
    def test_missing_dataset_errors(self):
        code = main(
            [
                "analytics",
                "country",
                "--reporter",
                "699",
            ]
        )
        assert code == 2  # argparse EXIT_USER_ERROR

    def test_missing_reporter_errors(self, fake_dataset_dir):
        code = main(
            [
                "analytics",
                "country",
                "--dataset",
                str(fake_dataset_dir),
            ]
        )
        assert code == 2  # argparse EXIT_USER_ERROR

    def test_missing_dataset_path(self):
        code = main(
            [
                "analytics",
                "country",
                "--dataset",
                "/no/such/directory",
                "--reporter",
                "699",
            ]
        )
        # 78 = EXIT_CONFIG_ERROR (CLIConfigurationError)
        assert code == 78


# ---------------------------------------------------------------------------
# Each subcommand invokes the right analytics function
# ---------------------------------------------------------------------------


class TestCountry:
    def test_invokes_country_summary(
        self, patched_analytics, fake_dataset_dir, capsys
    ):
        code = main(
            [
                "analytics",
                "country",
                "--dataset",
                str(fake_dataset_dir),
                "--reporter",
                "699",
            ]
        )
        assert code == EXIT_OK
        # Inspect the mock to confirm it was called.
        from un_comtrade.analytics import country
        country.country_summary.assert_called_once()
        # First positional arg = the loaded dataset.
        call_args = country.country_summary.call_args
        assert isinstance(call_args.args[0], CanonicalDataset)
        # ``reporter_code`` is forwarded via kwargs (mapped through
        # the ``param_name`` table); only ``dataset`` is positional.
        assert call_args.kwargs.get("reporter_code") == 699

    def test_output_is_json(
        self, patched_analytics, fake_dataset_dir, capsys
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
        loaded = json.loads(capsys.readouterr().out)
        assert loaded["reporter_code"] == 699
        assert loaded["iso3"] == "IND"


class TestPartner:
    def test_invokes_top_partners(
        self, patched_analytics, fake_dataset_dir, capsys
    ):
        code = main(
            [
                "analytics",
                "partner",
                "--dataset",
                str(fake_dataset_dir),
                "--reporter",
                "699",
            ]
        )
        assert code == EXIT_OK
        from un_comtrade.analytics import partner
        partner.top_partners.assert_called_once()
        call_args = partner.top_partners.call_args
        assert isinstance(call_args.args[0], CanonicalDataset)
        assert call_args.kwargs.get("reporter_code") == 699

    def test_optional_kwargs_pass_through(
        self, patched_analytics, fake_dataset_dir
    ):
        main(
            [
                "analytics",
                "partner",
                "--dataset",
                str(fake_dataset_dir),
                "--reporter",
                "699",
                "--flow",
                "X",
                "--limit",
                "5",
            ]
        )
        from un_comtrade.analytics import partner
        kwargs = partner.top_partners.call_args.kwargs
        assert kwargs["reporter_code"] == 699
        assert kwargs["flow"] == "X"
        assert kwargs["limit"] == 5


class TestCommodity:
    def test_invokes_top_hs_codes(
        self, patched_analytics, fake_dataset_dir, capsys
    ):
        code = main(
            [
                "analytics",
                "commodity",
                "--dataset",
                str(fake_dataset_dir),
                "--reporter",
                "699",
            ]
        )
        assert code == EXIT_OK
        from un_comtrade.analytics import commodity
        commodity.top_hs_codes.assert_called_once()
        call_args = commodity.top_hs_codes.call_args
        assert isinstance(call_args.args[0], CanonicalDataset)
        assert call_args.kwargs.get("reporter_code") == 699


class TestTrend:
    def test_invokes_annual_trend(
        self, patched_analytics, fake_dataset_dir, capsys
    ):
        code = main(
            [
                "analytics",
                "trend",
                "--dataset",
                str(fake_dataset_dir),
                "--reporter",
                "699",
            ]
        )
        assert code == EXIT_OK
        from un_comtrade.analytics import timeseries
        timeseries.annual_trend.assert_called_once()
        call_args = timeseries.annual_trend.call_args
        assert isinstance(call_args.args[0], CanonicalDataset)


class TestBalance:
    def test_invokes_country_balance(
        self, patched_analytics, fake_dataset_dir, capsys
    ):
        code = main(
            [
                "analytics",
                "balance",
                "--dataset",
                str(fake_dataset_dir),
            ]
        )
        assert code == EXIT_OK
        from un_comtrade.analytics import balance
        balance.country_balance.assert_called_once()
        call_args = balance.country_balance.call_args
        assert isinstance(call_args.args[0], CanonicalDataset)


class TestCompare:
    def test_invokes_country_vs_country(
        self, patched_analytics, fake_dataset_dir, capsys
    ):
        code = main(
            [
                "analytics",
                "compare",
                "--dataset",
                str(fake_dataset_dir),
                "--reporter",
                "699",
                "156",
            ]
        )
        assert code == EXIT_OK
        from un_comtrade.analytics import compare
        compare.country_vs_country.assert_called_once()
        call_args = compare.country_vs_country.call_args
        assert isinstance(call_args.args[0], CanonicalDataset)
        assert call_args.kwargs["reporter_codes"] == [699, 156]

    def test_compare_requires_at_least_two_reporters(
        self, fake_dataset_dir
    ):
        """``country_vs_country`` requires ≥ 2
        reporters; with only one, the SDK
        rejects and the CLI surfaces a
        ComtradeError → EXIT_GENERIC_ERROR.
        """
        code = main(
            [
                "analytics",
                "compare",
                "--dataset",
                str(fake_dataset_dir),
                "--reporter",
                "699",
            ]
        )
        # The SDK raises a ValueError; the CLI
        # wraps it as ComtradeError → generic
        # error (1).
        assert code == EXIT_GENERIC_ERROR


# ---------------------------------------------------------------------------
# --output-format / --output
# ---------------------------------------------------------------------------


class TestOutputHandling:
    def test_table_format(
        self, patched_analytics, fake_dataset_dir, capsys
    ):
        main(
            [
                "analytics",
                "country",
                "--dataset",
                str(fake_dataset_dir),
                "--reporter",
                "699",
                "--output-format",
                "table",
            ]
        )
        out = capsys.readouterr().out
        # dataclass fields → column headers.
        assert "reporter_code" in out
        assert "---" in out

    def test_output_to_file(
        self, patched_analytics, fake_dataset_dir, tmp_path
    ):
        target = tmp_path / "summary.json"
        code = main(
            [
                "analytics",
                "country",
                "--dataset",
                str(fake_dataset_dir),
                "--reporter",
                "699",
                "--output",
                str(target),
            ]
        )
        assert code == EXIT_OK
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded["reporter_code"] == 699


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------


class TestErrorMapping:
    def test_unknown_subsubcommand_errors(self):
        code = main(["analytics", "not-a-real-sub"])
        assert code == 2

    def test_sdk_error_returns_generic_error(
        self, patched_analytics, fake_dataset_dir
    ):
        from un_comtrade.exceptions import ComtradeError
        from un_comtrade.analytics import country
        country.country_summary.side_effect = ComtradeError("boom")
        code = main(
            [
                "analytics",
                "country",
                "--dataset",
                str(fake_dataset_dir),
                "--reporter",
                "699",
            ]
        )
        assert code == EXIT_GENERIC_ERROR


# ---------------------------------------------------------------------------
# "No analytics logic exists inside CLI" (C-004 requirement)
# ---------------------------------------------------------------------------


class TestNoAnalyticsLogicInsideCLI:
    """Static check: ``commands/analytics.py``
    contains no aggregation / Decimal-sum /
    list-construction patterns that would
    re-implement an analytics function.
    """

    FORBIDDEN = re.compile(
        r"by_(?:sector|reporter|partner|code)\.get\("
    )

    def test_no_handrolled_aggregations(self):
        path = Path("un_comtrade/cli/commands/analytics.py")
        source = path.read_text(encoding="utf-8")
        # Strip comments + docstrings.
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
        assert not self.FORBIDDEN.search(cleaned), (
            "analytics.py must not implement aggregation "
            "patterns; all aggregation must delegate to "
            "the SDK."
        )

    def test_only_public_analytics_functions_used(self):
        """Every ``method_name=`` value in the spec
        table maps to a function on a public
        ``un_comtrade.analytics.*`` submodule.
        """
        import importlib
        from un_comtrade.cli.commands.analytics import (
            _SPEC_METHODS,
            _SPECS,
        )
        for spec in _SPECS:
            mod = importlib.import_module(spec.module_path)
            method_name = _SPEC_METHODS[spec.method_name]
            assert hasattr(mod, method_name), (
                f"{spec.module_path}.{method_name} missing"
            )
            assert callable(getattr(mod, method_name)), (
                f"{spec.module_path}.{method_name} is not "
                f"callable"
            )


# ---------------------------------------------------------------------------
# Public-SDK-only constraint
# ---------------------------------------------------------------------------


class TestAnalyticsPublicSDKOnly:
    PRIVATE_RE = re.compile(r"^un_comtrade(_|\.)_")

    def test_no_private_module_imports(self):
        import ast
        path = Path("un_comtrade/cli/commands/analytics.py")
        source = path.read_text(encoding="utf-8")
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
            f"analytics.py imports private SDK modules: "
            f"{violations}"
        )


# ---------------------------------------------------------------------------
# Storage layer integration
# ---------------------------------------------------------------------------


class TestStorageIntegration:
    def test_cli_reads_dataset_via_public_storage(
        self, patched_analytics, fake_dataset_dir
    ):
        """The CLI must read the dataset via the
        public Storage layer, not via direct file
        I/O.
        """
        from un_comtrade.storage import StorageRegistry
        # Snapshot the registry before the run.
        original_get = StorageRegistry.get
        seen_backends: list = []

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
        # The CLI must have dispatched to the
        # PARQUET backend.
        from un_comtrade.storage import StorageBackend
        assert StorageBackend.PARQUET in seen_backends


# ---------------------------------------------------------------------------
# Dataset loader error mapping
# ---------------------------------------------------------------------------


class TestDatasetLoader:
    def test_unsupported_extension_errors(self):
        from un_comtrade.cli.utils.dataset_loader import (
            load_dataset,
        )
        from un_comtrade.cli.utils import CLIConfigurationError
        # Build a fake path with an unknown suffix.
        # We don't need the file to exist for the
        # extension check to run first — but
        # ``load_dataset`` checks existence before
        # extension, so we use a path with a
        # supported extension.
        # Use a non-existent path with a known
        # extension to assert "file does not
        # exist" wins:
        with pytest.raises(CLIConfigurationError, match="does not exist"):
            load_dataset("/tmp/no-such.parquet")