"""Tests for the C-003 trade CLI commands.

The trade commands call into the public
``un_comtrade.trade.TradeService``. We mock the
service so no live HTTP is exercised. Tests verify:

- Each ``trade <sub>`` invocation calls the
  corresponding public method on
  ``client.trade``.
- The CLI passes ONLY public method parameters
  (no URL assembly, no transport construction).
- Required options (``--reporter``, ``--year``)
  are enforced.
- Optional options (``--partner``,
  ``--classification``, ``--frequency``, etc.)
  flow through to the SDK.
- ``--progress`` writes to stderr (not stdout),
  and is silent when stderr is not a TTY.
- ``TradeResponse`` is serialised via the
  public ``to_dict()`` method.
- Exit codes are mapped correctly.
- The CLI consumes only public SDK APIs.
- ``URL never built inside CLI`` is enforced by a
  static check.
"""

from __future__ import annotations

import io
import json
import re
from pathlib import Path
from unittest import mock

import pytest

from un_comtrade.cli import (
    EXIT_GENERIC_ERROR,
    EXIT_OK,
    main,
)
from un_comtrade.cli.commands.trade import TradeCommand
from un_comtrade.models.response import TradeResponse


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _fake_response(count: int = 3) -> TradeResponse:
    """Build a ``TradeResponse`` whose ``to_dict``
    returns a small, stable dict.
    """
    return TradeResponse(
        elapsed_seconds=0.42,
        count=count,
        records=[],
        error="",
        upstream_url="https://example.invalid/get/X/A/HS",
        request={"reporterCode": 699, "period": "2022"},
        skipped=0,
    )


@pytest.fixture
def patched_client():
    """Patch ``ComtradeClient`` so the trade
    service methods return canned responses.
    """
    fake_trade = mock.MagicMock()
    response = _fake_response()
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
    ) as m:
        yield m, fake_client, fake_trade


# ---------------------------------------------------------------------------
# Registration / parser shape
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_trade_command_is_registered(self):
        from un_comtrade.cli.commands import get_command
        cmd = get_command("trade")
        assert isinstance(cmd, TradeCommand)

    def test_root_help_lists_trade(self):
        from un_comtrade.cli import build_parser
        parser = build_parser()
        for action in parser._actions:
            choices = getattr(action, "choices", None)
            if isinstance(choices, dict) and "trade" in choices:
                break
        else:
            pytest.fail("trade subparser not registered")

    def test_trade_help_lists_six_subs(self, capsys):
        main(["trade", "--help"])
        out = capsys.readouterr().out
        for sub in (
            "exports",
            "imports",
            "world",
            "bilateral",
            "balance",
            "tariffline",
        ):
            assert sub in out


# ---------------------------------------------------------------------------
# Required-argument enforcement
# ---------------------------------------------------------------------------


class TestRequiredArguments:
    def test_missing_reporter_errors(self):
        code = main(["trade", "exports", "--year", "2022"])
        assert code == 2  # argparse EXIT_USER_ERROR

    def test_missing_year_errors(self):
        code = main(["trade", "exports", "--reporter", "699"])
        assert code == 2  # argparse EXIT_USER_ERROR

    def test_reporter_must_be_integer(self):
        code = main(
            [
                "trade",
                "exports",
                "--reporter",
                "abc",
                "--year",
                "2022",
            ]
        )
        assert code == 2


# ---------------------------------------------------------------------------
# Each subcommand invokes the right SDK method
# ---------------------------------------------------------------------------


class TestExports:
    def test_invokes_get_exports(self, patched_client, capsys):
        _, _, fake_trade = patched_client
        code = main(
            [
                "trade",
                "exports",
                "--reporter",
                "699",
                "--year",
                "2022",
            ]
        )
        assert code == EXIT_OK
        fake_trade.get_exports.assert_called_once_with(
            699, "2022",
        )
        out = capsys.readouterr().out
        loaded = json.loads(out)
        assert loaded["count"] == 3


class TestImports:
    def test_invokes_get_imports(self, patched_client, capsys):
        _, _, fake_trade = patched_client
        code = main(
            [
                "trade",
                "imports",
                "--reporter",
                "699",
                "--year",
                "2022",
            ]
        )
        assert code == EXIT_OK
        fake_trade.get_imports.assert_called_once_with(
            699, "2022",
        )


class TestWorld:
    def test_invokes_get_world_trade(self, patched_client, capsys):
        _, _, fake_trade = patched_client
        code = main(
            [
                "trade",
                "world",
                "--reporter",
                "699",
                "--year",
                "2022",
            ]
        )
        assert code == EXIT_OK
        # ``get_world_trade(reporter_code, flow_code, period, ...)``
        # takes flow_code as a positional. The CLI defaults it to
        # ``"X"`` (exports) when the user did not supply --flow.
        fake_trade.get_world_trade.assert_called_once_with(
            699, "X", "2022",
        )

    def test_world_ignores_partner(self, patched_client):
        """``world`` does not accept ``--partner``;
        the CLI must NOT pass it through.
        """
        _, _, fake_trade = patched_client
        code = main(
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
        assert code == EXIT_OK
        kwargs = fake_trade.get_world_trade.call_args.kwargs
        # ``partner_code`` MUST NOT be in the call.
        assert "partner_code" not in kwargs


class TestBilateral:
    def test_invokes_get_bilateral(self, patched_client, capsys):
        _, _, fake_trade = patched_client
        code = main(
            [
                "trade",
                "bilateral",
                "--reporter",
                "699",
                "--partner",
                "840",
                "--year",
                "2022",
                "--flow",
                "X",
            ]
        )
        assert code == EXIT_OK
        fake_trade.get_bilateral.assert_called_once_with(
            699, "X", "2022", partner_code=840,
        )

    def test_bilateral_defaults_flow_to_X(self, patched_client):
        _, _, fake_trade = patched_client
        main(
            [
                "trade",
                "bilateral",
                "--reporter",
                "699",
                "--partner",
                "840",
                "--year",
                "2022",
            ]
        )
        fake_trade.get_bilateral.assert_called_once_with(
            699, "X", "2022", partner_code=840,
        )


class TestBalance:
    def test_invokes_get_trade_balance(self, patched_client, capsys):
        _, _, fake_trade = patched_client
        code = main(
            [
                "trade",
                "balance",
                "--reporter",
                "699",
                "--year",
                "2022",
            ]
        )
        assert code == EXIT_OK
        fake_trade.get_trade_balance.assert_called_once_with(
            699, "2022",
        )


class TestTariffline:
    def test_invokes_get_tariffline(self, patched_client, capsys):
        _, _, fake_trade = patched_client
        code = main(
            [
                "trade",
                "tariffline",
                "--reporter",
                "699",
                "--year",
                "2022",
                "--flow",
                "M",
            ]
        )
        assert code == EXIT_OK
        fake_trade.get_tariffline.assert_called_once_with(
            699, "M", "2022",
        )


# ---------------------------------------------------------------------------
# Optional kwargs flow-through
# ---------------------------------------------------------------------------


class TestOptionalKwargs:
    def test_classification_kwarg(self, patched_client):
        _, _, fake_trade = patched_client
        main(
            [
                "trade",
                "exports",
                "--reporter",
                "699",
                "--year",
                "2022",
                "--classification",
                "HS",
            ]
        )
        kwargs = fake_trade.get_exports.call_args.kwargs
        assert kwargs.get("classification") == "HS"

    def test_commodity_kwarg(self, patched_client):
        _, _, fake_trade = patched_client
        main(
            [
                "trade",
                "exports",
                "--reporter",
                "699",
                "--year",
                "2022",
                "--commodity",
                "270900",
            ]
        )
        kwargs = fake_trade.get_exports.call_args.kwargs
        assert kwargs.get("commodity_code") == "270900"

    def test_max_records_kwarg(self, patched_client):
        _, _, fake_trade = patched_client
        main(
            [
                "trade",
                "exports",
                "--reporter",
                "699",
                "--year",
                "2022",
                "--max-records",
                "500",
            ]
        )
        kwargs = fake_trade.get_exports.call_args.kwargs
        assert kwargs.get("max_records") == 500

    def test_breakdown_mode_kwarg(self, patched_client):
        _, _, fake_trade = patched_client
        main(
            [
                "trade",
                "exports",
                "--reporter",
                "699",
                "--year",
                "2022",
                "--breakdown-mode",
                "plus",
            ]
        )
        kwargs = fake_trade.get_exports.call_args.kwargs
        assert kwargs.get("breakdown_mode") == "plus"


# ---------------------------------------------------------------------------
# --progress flag
# ---------------------------------------------------------------------------


class TestProgressFlag:
    def test_progress_default_is_silent(self, patched_client, capsys):
        main(
            [
                "trade",
                "exports",
                "--reporter",
                "699",
                "--year",
                "2022",
            ]
        )
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_progress_writes_to_stderr(self, patched_client, capsys):
        main(
            [
                "trade",
                "exports",
                "--reporter",
                "699",
                "--year",
                "2022",
                "--progress",
            ]
        )
        captured = capsys.readouterr()
        # Stderr contains the progress line.
        assert "trade/exports" in captured.err
        assert "done" in captured.err
        # Stdout is the data stream, untouched.
        loaded = json.loads(captured.out)
        assert loaded["count"] == 3


# ---------------------------------------------------------------------------
# --output-format and --output
# ---------------------------------------------------------------------------


class TestOutputHandling:
    def test_default_format_is_json(self, patched_client, capsys):
        main(
            [
                "trade",
                "exports",
                "--reporter",
                "699",
                "--year",
                "2022",
            ]
        )
        loaded = json.loads(capsys.readouterr().out)
        assert loaded["count"] == 3

    def test_table_format(self, patched_client, capsys):
        main(
            [
                "trade",
                "exports",
                "--reporter",
                "699",
                "--year",
                "2022",
                "--output-format",
                "table",
            ]
        )
        out = capsys.readouterr().out
        assert "count" in out
        assert "---" in out

    def test_csv_format(self, patched_client, capsys):
        main(
            [
                "trade",
                "exports",
                "--reporter",
                "699",
                "--year",
                "2022",
                "--output-format",
                "csv",
            ]
        )
        out = capsys.readouterr().out
        # TradeResponse.to_dict() is a flat dict
        # so the CSV has one row.
        import csv as _csv
        import io as _io
        rows = list(_csv.reader(_io.StringIO(out)))
        assert len(rows) >= 2

    def test_output_to_file(self, patched_client, tmp_path):
        target = tmp_path / "exports.json"
        code = main(
            [
                "trade",
                "exports",
                "--reporter",
                "699",
                "--year",
                "2022",
                "--output",
                str(target),
            ]
        )
        assert code == EXIT_OK
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded["count"] == 3


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------


class TestErrorMapping:
    def test_unknown_subsubcommand_errors(self):
        code = main(
            [
                "trade",
                "not-a-real-sub",
                "--reporter",
                "699",
                "--year",
                "2022",
            ]
        )
        assert code == 2  # argparse EXIT_USER_ERROR

    def test_sdk_error_returns_generic_error(self):
        from un_comtrade.exceptions import ComtradeError
        fake_trade = mock.MagicMock()
        fake_trade.get_exports.side_effect = ComtradeError("boom")
        fake_client = mock.MagicMock()
        fake_client.trade = fake_trade
        with mock.patch(
            "un_comtrade.cli.commands.trade.ComtradeClient",
            return_value=fake_client,
        ):
            code = main(
                [
                    "trade",
                    "exports",
                    "--reporter",
                    "699",
                    "--year",
                    "2022",
                ]
            )
        assert code == EXIT_GENERIC_ERROR

    def test_validation_error_returns_user_error(self):
        from un_comtrade.exceptions import ValidationError
        fake_trade = mock.MagicMock()
        fake_trade.get_exports.side_effect = ValidationError(
            "bad reporter code"
        )
        fake_client = mock.MagicMock()
        fake_client.trade = fake_trade
        with mock.patch(
            "un_comtrade.cli.commands.trade.ComtradeClient",
            return_value=fake_client,
        ):
            code = main(
                [
                    "trade",
                    "exports",
                    "--reporter",
                    "699",
                    "--year",
                    "2022",
                ]
            )
        # ValidationError → CLIError → EXIT_USER_ERROR (2)
        assert code == 2


# ---------------------------------------------------------------------------
# URL-not-built-inside-CLI guard (C-003 requirement)
# ---------------------------------------------------------------------------


class TestURLNotBuiltInsideCLI:
    """C-003 mandates: 'URL never built inside
    CLI'. The CLI must delegate URL construction
    to the SDK. We enforce this with a static
    check on the trade command source.
    """

    URL_RE = re.compile(
        r"(https?://|/data/v1/|/files/v1/|/tools/v1/|"
        r"/get/|/getTariffline/|/preview/)",
        re.IGNORECASE,
    )

    def test_no_endpoint_url_in_trade_source(self):
        """No endpoint URL substrings may appear in
        ``commands/trade.py``. The CLI is
        forbidden from assembling upstream URLs.
        """
        path = Path("un_comtrade/cli/commands/trade.py")
        source = path.read_text(encoding="utf-8")
        # Strip comments and docstrings before
        # scanning.
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
        # The cleaned source MUST NOT contain any
        # URL pattern.
        match = self.URL_RE.search(cleaned)
        assert not match, (
            f"trade.py references an upstream URL "
            f"pattern {match.group()!r}; the CLI "
            f"must delegate URL assembly to the SDK"
        )

    def test_no_url_construction_in_trade_helpers(self):
        """Same check for the helper modules used
        by trade.py.
        """
        for path in (
            "un_comtrade/cli/commands/trade.py",
            "un_comtrade/cli/utils/progress.py",
        ):
            text = Path(path).read_text(encoding="utf-8")
            assert not self.URL_RE.search(text), (
                f"{path} contains an upstream URL pattern"
            )


# ---------------------------------------------------------------------------
# Public-SDK-only constraint
# ---------------------------------------------------------------------------


class TestTradeCommandPublicSDKOnly:
    PRIVATE_RE = re.compile(r"^un_comtrade(_|\.)_")

    def test_no_private_module_imports(self):
        import ast
        path = Path("un_comtrade/cli/commands/trade.py")
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
            f"trade.py imports private SDK modules: "
            f"{violations}"
        )

    def test_only_public_trade_methods_used(self):
        """Every ``method_name=`` value in the
        ``_SPECS`` list must be a public method on
        ``TradeService``.
        """
        from un_comtrade.trade import TradeService
        import ast
        path = Path("un_comtrade/cli/commands/trade.py")
        source = path.read_text(encoding="utf-8")
        public = {
            name
            for name in dir(TradeService)
            if not name.startswith("_")
        }
        for line in source.splitlines():
            if "method_name=" in line:
                rhs = line.split("method_name=", 1)[1]
                rhs = rhs.split(",", 1)[0].strip().strip('"').strip("'")
                assert rhs in public, (
                    f"trade.py references unknown "
                    f"TradeService method {rhs!r}"
                )


# ---------------------------------------------------------------------------
# Configuration injection
# ---------------------------------------------------------------------------


class TestConfigurationInjection:
    def test_cli_uses_public_configuration(self, monkeypatch):
        """The trade command constructs the
        client with a real public
        ``Configuration``.
        """
        monkeypatch.delenv("UN_COMTRADE_KEY", raising=False)
        seen_config = []

        class _SpyClient:
            def __init__(self, configuration=None, **_kw):
                seen_config.append(configuration)

            @property
            def trade(self):
                t = mock.MagicMock()
                t.get_exports.return_value = _fake_response()
                return t

            def close(self):
                pass

        with mock.patch(
            "un_comtrade.cli.commands.trade.ComtradeClient",
            _SpyClient,
        ):
            code = main(
                [
                    "trade",
                    "exports",
                    "--reporter",
                    "699",
                    "--year",
                    "2022",
                ]
            )
        assert code == EXIT_OK
        from un_comtrade.config import Configuration
        assert isinstance(seen_config[0], Configuration)


# ---------------------------------------------------------------------------
# to_dict is the public serialisation boundary
# ---------------------------------------------------------------------------


class TestPublicSerialisationBoundary:
    def test_response_serialised_via_to_dict(self, patched_client):
        """The CLI MUST use the public
        ``TradeResponse.to_dict()`` method to
        serialise the response. We verify by
        monkey-patching ``to_dict`` to raise; the
        exception must propagate out of the CLI
        (proving to_dict was invoked).
        """
        original = TradeResponse.to_dict

        def _explode(self):
            raise RuntimeError("to_dict was called")

        try:
            TradeResponse.to_dict = _explode
            with pytest.raises(RuntimeError, match="to_dict was called"):
                main(
                    [
                        "trade",
                        "exports",
                        "--reporter",
                        "699",
                        "--year",
                        "2022",
                    ]
                )
        finally:
            TradeResponse.to_dict = original

    def test_response_to_dict_result_is_json_serialisable(
        self, patched_client, capsys
    ):
        """The default output format is JSON. The
        CLI's serialisation pipeline must produce
        valid JSON from the public ``to_dict()``
        output.
        """
        main(
            [
                "trade",
                "exports",
                "--reporter",
                "699",
                "--year",
                "2022",
            ]
        )
        loaded = json.loads(capsys.readouterr().out)
        # TradeResponse.to_dict() exposes these
        # canonical keys.
        assert "count" in loaded
        assert "records" in loaded
        assert "upstream_url" in loaded
        assert "request" in loaded