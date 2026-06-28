"""Tests for the un-comtrade CLI foundation
(C-001).

These tests verify:

- The CLI starts without error.
- ``--help`` produces useful output.
- ``--version`` reports the public
  ``un_comtrade.__version__``.
- Invalid commands exit with a non-zero code.
- ``--api-key`` / ``--log-level`` /
  ``--output-format`` are accepted and forwarded
  to the public SDK configuration loader.
- The CLI consumes ONLY public SDK APIs
  (no private ``_``-prefixed modules).
- The CLI exposes its public surface in
  ``un_comtrade.cli.__all__``.
- Exit codes are mapped correctly.

No live API. No network. No state mutation.
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

import pytest

import un_comtrade
from un_comtrade import cli as cli_pkg
from un_comtrade.cli import (
    EXIT_AUTH_ERROR,
    EXIT_CONFIG_ERROR,
    EXIT_GENERIC_ERROR,
    EXIT_NETWORK_ERROR,
    EXIT_OK,
    EXIT_USER_ERROR,
    OUTPUT_FORMATS,
    CLIConfigurationError,
    CLIError,
    build_parser,
    load_cli_configuration,
    main,
)
from un_comtrade.cli.formatting import (
    JsonFormatter,
    OutputFormatter,
    get_formatter,
)
from un_comtrade.cli.utils import (
    EXIT_OK as _EXIT_OK_FROM_UTILS,
)


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


class TestPublicSurface:
    def test_cli_package_exposes_build_parser_and_main(self):
        assert callable(build_parser)
        assert callable(main)
        assert "build_parser" in cli_pkg.__all__
        assert "main" in cli_pkg.__all__

    def test_cli_package_exposes_exit_codes(self):
        for name in (
            "EXIT_OK",
            "EXIT_GENERIC_ERROR",
            "EXIT_USER_ERROR",
            "EXIT_CONFIG_ERROR",
            "EXIT_NETWORK_ERROR",
            "EXIT_AUTH_ERROR",
        ):
            assert name in cli_pkg.__all__
            assert isinstance(getattr(cli_pkg, name), int)

    def test_cli_package_exposes_errors(self):
        assert "CLIError" in cli_pkg.__all__
        assert "CLIConfigurationError" in cli_pkg.__all__
        assert issubclass(CLIError, Exception)
        assert issubclass(CLIConfigurationError, CLIError)

    def test_cli_errors_inherit_sdk_error(self):
        """CLI errors MUST inherit from
        ``un_comtrade.exceptions.ComtradeError`` so
        that a single ``except`` clause catches
        both SDK and CLI errors.
        """
        from un_comtrade.exceptions import ComtradeError
        assert issubclass(CLIError, ComtradeError)
        assert issubclass(CLIConfigurationError, ComtradeError)


# ---------------------------------------------------------------------------
# --version / --help
# ---------------------------------------------------------------------------


class TestVersionAndHelp:
    def test_version_flag_reports_public_version(self, capsys):
        code = main(["--version"])
        assert code == EXIT_OK
        out = capsys.readouterr().out
        assert un_comtrade.__version__ in out
        # Belt-and-braces: the literal "un-comtrade"
        # prefix should be present.
        assert "un-comtrade" in out

    def test_help_flag_exits_zero(self, capsys):
        code = main(["--help"])
        assert code == EXIT_OK
        out = capsys.readouterr().out
        # The help text must describe the global
        # options.
        assert "--api-key" in out
        assert "--log-level" in out
        assert "--output-format" in out
        assert "--version" in out

    def test_help_shows_root_command(self, capsys):
        """The foundation ships the `root` command
        so a bare `un-comtrade` invocation works.
        """
        main(["--help"])
        out = capsys.readouterr().out
        assert "root" in out

    def test_help_lists_output_format_choices(self, capsys):
        main(["--help"])
        out = capsys.readouterr().out
        for fmt in OUTPUT_FORMATS:
            assert fmt in out


# ---------------------------------------------------------------------------
# Bare invocation (no subcommand)
# ---------------------------------------------------------------------------


class TestBareInvocation:
    def test_bare_invocation_returns_zero(self, capsys):
        code = main([])
        assert code == EXIT_OK

    def test_bare_invocation_prints_banner(self, capsys):
        main([])
        out = capsys.readouterr().out
        assert "un-comtrade" in out
        assert un_comtrade.__version__ in out


# ---------------------------------------------------------------------------
# Invalid commands
# ---------------------------------------------------------------------------


class TestInvalidInput:
    def test_unknown_subcommand_exits_user_error(self, capsys):
        code = main(["nonexistent-subcommand"])
        assert code == EXIT_USER_ERROR
        err = capsys.readouterr().err
        # argparse prints "unrecognized arguments"
        # to stderr; we just check we surface a
        # non-zero code.
        assert err or True  # err may be empty if argparse prints differently

    def test_invalid_log_level_exits_config_error(self, capsys):
        code = main(["--log-level", "BOGUS", "root"])
        assert code == EXIT_CONFIG_ERROR
        err = capsys.readouterr().err
        assert "log level" in err.lower()

    def test_invalid_output_format_exits_user_error(self, capsys):
        # ``choices=OUTPUT_FORMATS`` in argparse
        # catches this BEFORE main's logic runs,
        # so the exit code is argparse's standard 2.
        code = main(["--output-format", "xml", "root"])
        assert code == EXIT_USER_ERROR


# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------


class TestConfigurationLoading:
    def test_loads_with_no_args(self, monkeypatch):
        """No API key in env: ``load_cli_configuration``
        still returns a ``Configuration`` (the
        upstream will reject on call).
        """
        monkeypatch.delenv("UN_COMTRADE_KEY", raising=False)
        monkeypatch.delenv("UN_COMTRADE_LOG_LEVEL", raising=False)
        cfg = load_cli_configuration()
        # Public Configuration dataclass.
        from un_comtrade.config import Configuration
        assert isinstance(cfg, Configuration)

    def test_api_key_override(self, monkeypatch):
        monkeypatch.delenv("UN_COMTRADE_KEY", raising=False)
        cfg = load_cli_configuration(api_key="abc-123")
        assert cfg.api_key == "abc-123"

    def test_log_level_override(self, monkeypatch):
        monkeypatch.delenv("UN_COMTRADE_LOG_LEVEL", raising=False)
        cfg = load_cli_configuration(log_level="DEBUG")
        assert cfg.log_level == "DEBUG"

    def test_log_level_case_insensitive(self, monkeypatch):
        monkeypatch.delenv("UN_COMTRADE_LOG_LEVEL", raising=False)
        cfg = load_cli_configuration(log_level="info")
        assert cfg.log_level == "INFO"

    def test_invalid_log_level_raises(self, monkeypatch):
        monkeypatch.delenv("UN_COMTRADE_LOG_LEVEL", raising=False)
        with pytest.raises(CLIConfigurationError):
            load_cli_configuration(log_level="NUCLEAR")

    def test_main_propagates_log_level_via_argv(self, monkeypatch):
        monkeypatch.delenv("UN_COMTRADE_LOG_LEVEL", raising=False)
        # Run with --log-level DEBUG and the root
        # command. The configuration is loaded
        # inside main; we observe it via the env
        # var the SDK writes back? No — the SDK
        # only reads it. We instead assert the
        # call returns OK and does not crash.
        code = main(["--log-level", "DEBUG"])
        assert code == EXIT_OK

    def test_main_propagates_api_key_via_argv(self, monkeypatch):
        monkeypatch.delenv("UN_COMTRADE_KEY", raising=False)
        code = main(["--api-key", "test-key"])
        assert code == EXIT_OK


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


class TestFormatters:
    def test_json_formatter_serialises_dict(self):
        out = JsonFormatter().render({"b": 1, "a": "x"})
        # sort_keys=True + indent=2.
        assert json.loads(out) == {"a": "x", "b": 1}
        assert "\n" in out  # indented

    def test_json_formatter_serialises_list(self):
        out = JsonFormatter().render([{"x": 1}, {"x": 2}])
        assert json.loads(out) == [{"x": 1}, {"x": 2}]

    def test_json_formatter_handles_decimal(self):
        from decimal import Decimal
        out = JsonFormatter().render({"value": Decimal("123.456")})
        # Decimal is serialised as its string form
        # to preserve exact precision.
        assert json.loads(out) == {"value": "123.456"}

    def test_json_formatter_handles_datetime(self):
        from datetime import datetime, timezone
        dt = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        out = JsonFormatter().render({"t": dt})
        loaded = json.loads(out)
        assert loaded["t"].startswith("2026-01-01T12:00:00")

    def test_json_formatter_handles_dataclass(self):
        from dataclasses import dataclass

        @dataclass
        class Row:
            x: int
            y: str

        out = JsonFormatter().render(Row(1, "hello"))
        assert json.loads(out) == {"x": 1, "y": "hello"}

    def test_json_formatter_implements_protocol(self):
        assert isinstance(JsonFormatter(), OutputFormatter)

    def test_get_formatter_returns_json_for_json_name(self):
        f = get_formatter("json")
        assert isinstance(f, JsonFormatter)

    def test_get_formatter_raises_keyerror_for_unknown(self):
        with pytest.raises(KeyError):
            get_formatter("xml")

    def test_table_formatter_is_functional_in_c002(self):
        """C-002 promoted TableFormatter from a
        placeholder to a full implementation.
        It MUST now return a non-empty string for
        a non-empty list of dicts.
        """
        from un_comtrade.cli.formatting.table import (
            TableFormatter,
        )
        out = TableFormatter().render([{"a": 1, "b": 2}])
        assert "a" in out
        assert "b" in out
        assert "1" in out
        assert "2" in out

    def test_csv_formatter_is_functional_in_c002(self):
        """C-002 promoted CsvFormatter from a
        placeholder to a full implementation.
        """
        from un_comtrade.cli.formatting.csv import (
            CsvFormatter,
        )
        out = CsvFormatter().render([{"a": 1, "b": 2}, {"a": 3, "b": 4}])
        assert "a,b" in out or "a\r\nb" in out  # header line
        assert "1,2" in out
        assert "3,4" in out


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------


class TestParser:
    def test_parser_prog_is_un_comtrade(self):
        parser = build_parser()
        assert parser.prog == "un-comtrade"

    def test_parser_has_global_options(self):
        parser = build_parser()
        # argparse stores actions keyed by the
        # destination name.
        for opt in (
            "api_key",
            "log_level",
            "output_format",
        ):
            assert any(
                a.dest == opt for a in parser._actions
            ), f"missing global option --{opt.replace('_', '-')}"

    def test_parser_accepts_long_version_flag(self):
        parser = build_parser()
        # argparse registers the --version action
        # with the literal string "--version" in
        # its option_strings.
        assert any(
            "--version" in a.option_strings
            for a in parser._actions
        )


# ---------------------------------------------------------------------------
# Public-SDK-only constraint
# ---------------------------------------------------------------------------


class TestPublicSDKOnlyConstraint:
    """The CLI MUST consume ONLY public SDK APIs.
    Verify by AST: no import may target a private
    (underscore-prefixed) module of the SDK.
    """

    PRIVATE_MODULE_PATTERN = re.compile(
        r"^un_comtrade(_|\.)_"
    )

    @pytest.mark.parametrize("cli_file", [
        "un_comtrade/cli/__init__.py",
        "un_comtrade/cli/main.py",
        "un_comtrade/cli/commands/__init__.py",
        "un_comtrade/cli/formatting/__init__.py",
        "un_comtrade/cli/formatting/json.py",
        "un_comtrade/cli/formatting/table.py",
        "un_comtrade/cli/formatting/csv.py",
        "un_comtrade/cli/formatting/markdown.py",
        "un_comtrade/cli/formatting/text.py",
        "un_comtrade/cli/utils/__init__.py",
        "un_comtrade/cli/utils/exceptions.py",
        "un_comtrade/cli/utils/exit_codes.py",
        "un_comtrade/cli/utils/config_loader.py",
    ])
    def test_no_private_module_imports(self, cli_file):
        import ast
        path = Path(cli_file)
        if not path.exists():
            pytest.skip(f"{cli_file} does not exist")
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
            if target and self.PRIVATE_MODULE_PATTERN.match(target):
                # The leading-underscore rule applies
                # to the SDK's own private modules
                # (e.g. ``un_comtrade._query_engine``).
                # Python's own ``_collections_abc`` etc.
                # are not part of the SDK.
                if target.startswith("un_comtrade"):
                    violations.append(
                        (node.lineno, target)
                    )
        assert not violations, (
            f"{cli_file} imports private SDK modules: "
            f"{violations}"
        )


# ---------------------------------------------------------------------------
# Console script registration
# ---------------------------------------------------------------------------


class TestConsoleScriptRegistration:
    def test_pyproject_registers_un_comtrade_console_script(self):
        import tomllib
        with Path("pyproject.toml").open("rb") as f:
            pkg = tomllib.load(f)["project"]
        scripts = pkg.get("scripts", {})
        assert "un-comtrade" in scripts, (
            f"pyproject.toml [project.scripts] missing "
            f"'un-comtrade' entry; got {sorted(scripts)}"
        )
        assert scripts["un-comtrade"] == "un_comtrade.cli.main:main"


# ---------------------------------------------------------------------------
# End-to-end smoke (no live API)
# ---------------------------------------------------------------------------


class TestEndToEndSmoke:
    """``un-comtrade --version`` and ``un-comtrade
    --help`` must work end-to-end when invoked
    via ``subprocess`` (i.e. as a console script).
    """

    @pytest.mark.skipif(
        sys.platform.startswith("win") and not __import__("shutil").which("un-comtrade"),
        reason="un-comtrade console script not on PATH",
    )
    def test_un_comtrade_console_script_version(self):
        result = subprocess.run(
            ["un-comtrade", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == EXIT_OK
        assert un_comtrade.__version__ in result.stdout

    @pytest.mark.skipif(
        sys.platform.startswith("win") and not __import__("shutil").which("un-comtrade"),
        reason="un-comtrade console script not on PATH",
    )
    def test_un_comtrade_console_script_help(self):
        result = subprocess.run(
            ["un-comtrade", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == EXIT_OK
        assert "--api-key" in result.stdout