"""Tests for the C-002 metadata CLI commands.

The metadata commands call into the public
``un_comtrade.metadata.MetadataService``. We mock
the service so no live HTTP is exercised. The
tests verify:

- Each ``metadata <sub>`` invocation calls the
  corresponding public method on
  ``client.metadata``.
- The records returned are rendered with the
  chosen formatter (json / table / csv).
- ``--output PATH`` writes the rendered output to
  the file.
- Exit codes are mapped correctly (success =
  EXIT_OK, SDK errors = EXIT_GENERIC_ERROR).
- The CLI consumes only public SDK APIs.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from unittest import mock

import pytest

from un_comtrade.cli import (
    EXIT_GENERIC_ERROR,
    EXIT_OK,
    main,
)
from un_comtrade.cli.commands.metadata import (
    MetadataCommand,
)
from un_comtrade.models.classification import Classification
from un_comtrade.models.country import Country
from un_comtrade.models.frequency import Frequency
from un_comtrade.models.hs_code import HSCode
from un_comtrade.models.transport_mode import TransportMode


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _country(code: int, iso3: str, name: str) -> Country:
    return Country(
        country_code=code,
        iso_alpha2=iso3[:2],
        iso_alpha3=iso3,
        display_name=name,
        entry_effective_date=None,
        entry_expired_date=None,
    )


def _classification(code: str, name: str) -> Classification:
    return Classification(
        classification_code=code,
        display_name=name,
    )


def _frequency(code: str, name: str) -> Frequency:
    return Frequency(
        frequency_code=code,
        display_name=name,
    )


def _transport_mode(code: int, name: str) -> TransportMode:
    return TransportMode(
        mot_code=code,
        display_name=name,
    )


def _hs_code(commodity_code: str, edition: str, name: str) -> HSCode:
    return HSCode(
        commodity_code=commodity_code,
        classification_code="HS",
        edition=edition,
        display_name=name,
    )


SAMPLE_COUNTRIES = [
    _country(0, "WLD", "World"),
    _country(699, "IND", "India"),
    _country(156, "CHN", "China"),
]
SAMPLE_PARTNERS = [
    _country(0, "WLD", "World"),
    _country(840, "USA", "United States"),
]
SAMPLE_CLASSIFICATIONS = [
    _classification("HS", "Harmonized System"),
    _classification("SITC", "Standard International Trade Classification"),
]
SAMPLE_FREQUENCIES = [
    _frequency("A", "Annual"),
    _frequency("M", "Monthly"),
]
SAMPLE_TRANSPORT_MODES = [
    _transport_mode(0, "All modes of transport"),
    _transport_mode(1, "Maritime"),
]
SAMPLE_HS_CODES = [
    _hs_code("0101", "HS", "Live horses"),
    _hs_code("0102", "HS", "Live bovine animals"),
]


@pytest.fixture
def patched_client():
    """Patch ``ComtradeClient`` so the metadata
    service methods return canned lists.

    Returns the patched client so tests can
    introspect call args.
    """
    fake_metadata = mock.MagicMock()
    fake_metadata.get_countries.return_value = SAMPLE_COUNTRIES
    fake_metadata.get_partners.return_value = SAMPLE_PARTNERS
    fake_metadata.get_classifications.return_value = (
        SAMPLE_CLASSIFICATIONS
    )
    fake_metadata.get_frequencies.return_value = SAMPLE_FREQUENCIES
    fake_metadata.get_transport_modes.return_value = (
        SAMPLE_TRANSPORT_MODES
    )
    fake_metadata.get_hs_codes.return_value = SAMPLE_HS_CODES

    fake_client = mock.MagicMock()
    fake_client.metadata = fake_metadata

    with mock.patch(
        "un_comtrade.cli.commands.metadata.ComtradeClient",
        return_value=fake_client,
    ) as m:
        yield m, fake_client, fake_metadata


# ---------------------------------------------------------------------------
# Registration / parser shape
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_metadata_command_is_registered(self):
        from un_comtrade.cli.commands import get_command
        cmd = get_command("metadata")
        assert isinstance(cmd, MetadataCommand)

    def test_parser_has_metadata_subparser(self):
        from un_comtrade.cli import build_parser
        parser = build_parser()
        # Walk sub-action choices to find metadata.
        for action in parser._actions:
            choices = getattr(action, "choices", None)
            if isinstance(choices, dict) and "metadata" in choices:
                metadata_action = choices["metadata"]
                break
        else:
            pytest.fail("metadata subparser not registered")

    def test_metadata_help_lists_six_subs(self, capsys):
        main(["metadata", "--help"])
        out = capsys.readouterr().out
        for sub in (
            "countries",
            "partners",
            "hs",
            "classifications",
            "frequencies",
            "transport-modes",
        ):
            assert sub in out


# ---------------------------------------------------------------------------
# Each subcommand invokes the right SDK method
# ---------------------------------------------------------------------------


class TestCountries:
    def test_invokes_get_countries(self, patched_client, capsys):
        _, _, fake_metadata = patched_client
        code = main(["metadata", "countries"])
        assert code == EXIT_OK
        fake_metadata.get_countries.assert_called_once()
        out = capsys.readouterr().out
        assert "India" in out
        assert "World" in out


class TestPartners:
    def test_invokes_get_partners(self, patched_client, capsys):
        _, _, fake_metadata = patched_client
        code = main(["metadata", "partners"])
        assert code == EXIT_OK
        fake_metadata.get_partners.assert_called_once()
        out = capsys.readouterr().out
        assert "United States" in out


class TestClassifications:
    def test_invokes_get_classifications(self, patched_client, capsys):
        _, _, fake_metadata = patched_client
        code = main(["metadata", "classifications"])
        assert code == EXIT_OK
        fake_metadata.get_classifications.assert_called_once()
        out = capsys.readouterr().out
        assert "Harmonized System" in out


class TestFrequencies:
    def test_invokes_get_frequencies(self, patched_client, capsys):
        _, _, fake_metadata = patched_client
        code = main(["metadata", "frequencies"])
        assert code == EXIT_OK
        fake_metadata.get_frequencies.assert_called_once()
        out = capsys.readouterr().out
        assert "Annual" in out


class TestTransportModes:
    def test_invokes_get_transport_modes(self, patched_client, capsys):
        _, _, fake_metadata = patched_client
        code = main(["metadata", "transport-modes"])
        assert code == EXIT_OK
        fake_metadata.get_transport_modes.assert_called_once()
        out = capsys.readouterr().out
        assert "Maritime" in out


class TestHS:
    def test_invokes_get_hs_codes_with_default(self, patched_client, capsys):
        _, _, fake_metadata = patched_client
        code = main(["metadata", "hs"])
        assert code == EXIT_OK
        fake_metadata.get_hs_codes.assert_called_once_with("HS")
        out = capsys.readouterr().out
        assert "Live horses" in out

    def test_invokes_get_hs_codes_with_edition_flag(
        self, patched_client, capsys
    ):
        _, _, fake_metadata = patched_client
        code = main(["metadata", "hs", "--edition", "H0"])
        assert code == EXIT_OK
        fake_metadata.get_hs_codes.assert_called_once_with("H0")


# ---------------------------------------------------------------------------
# --output-format
# ---------------------------------------------------------------------------


class TestOutputFormat:
    def test_default_format_is_json(self, patched_client, capsys):
        main(["metadata", "countries"])
        out = capsys.readouterr().out
        # JSON output is valid JSON, contains the
        # record data.
        loaded = json.loads(out)
        assert isinstance(loaded, list)
        assert len(loaded) == 3

    def test_table_format(self, patched_client, capsys):
        main(["metadata", "countries", "--output-format", "table"])
        out = capsys.readouterr().out
        # Table layout has column headers + dashes
        # separator.
        assert "iso_alpha3" in out or "country_code" in out
        assert "---" in out

    def test_csv_format(self, patched_client, capsys):
        main(["metadata", "countries", "--output-format", "csv"])
        out = capsys.readouterr().out
        reader = csv.reader(io.StringIO(out))
        rows = list(reader)
        # Header + 3 records.
        assert len(rows) >= 4
        # First record row should be parseable as
        # a list of strings.
        assert all(isinstance(c, str) for c in rows[0])


# ---------------------------------------------------------------------------
# --output file
# ---------------------------------------------------------------------------


class TestOutputFile:
    def test_output_to_file(self, patched_client, tmp_path):
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
        text = target.read_text(encoding="utf-8")
        loaded = json.loads(text)
        assert len(loaded) == 3

    def test_output_to_file_with_table_format(
        self, patched_client, tmp_path
    ):
        target = tmp_path / "countries.txt"
        code = main(
            [
                "metadata",
                "countries",
                "--output-format",
                "table",
                "--output",
                str(target),
            ]
        )
        assert code == EXIT_OK
        text = target.read_text(encoding="utf-8")
        assert "iso_alpha3" in text or "country_code" in text

    def test_output_to_invalid_path_returns_config_error(
        self, patched_client, tmp_path
    ):
        # A directory that doesn't exist triggers
        # an OSError on open().
        bogus = tmp_path / "no-such-dir" / "x.json"
        code = main(
            [
                "metadata",
                "countries",
                "--output",
                str(bogus),
            ]
        )
        assert code == 78  # EXIT_CONFIG_ERROR


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------


class TestErrorMapping:
    def test_unknown_metadata_subsubcommand_errors(self, capsys):
        code = main(["metadata", "definitely-not-a-real-sub"])
        assert code == 2  # argparse EXIT_USER_ERROR

    def test_sdk_error_returns_generic_error(self):
        from un_comtrade.exceptions import ComtradeError
        fake_metadata = mock.MagicMock()
        fake_metadata.get_countries.side_effect = ComtradeError(
            "boom"
        )
        fake_client = mock.MagicMock()
        fake_client.metadata = fake_metadata
        with mock.patch(
            "un_comtrade.cli.commands.metadata.ComtradeClient",
            return_value=fake_client,
        ):
            code = main(["metadata", "countries"])
        # ComtradeError falls through to the catch-all
        # → EXIT_GENERIC_ERROR.
        assert code == EXIT_GENERIC_ERROR


# ---------------------------------------------------------------------------
# Public-SDK-only constraint (extended)
# ---------------------------------------------------------------------------


class TestMetadataCommandPublicSDKOnly:
    """The metadata command module MUST NOT import
    any private (``_``-prefixed) SDK modules.
    """

    PRIVATE_RE = __import__("re").compile(
        r"^un_comtrade(_|\.)_"
    )

    def test_no_private_imports(self):
        import ast
        path = Path("un_comtrade/cli/commands/metadata.py")
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
            f"metadata.py imports private SDK modules: "
            f"{violations}"
        )

    def test_only_public_metadata_methods_used(self):
        """The command module references only public
        methods on ``MetadataService`` (no leading
        underscore).
        """
        import ast
        path = Path("un_comtrade/cli/commands/metadata.py")
        source = path.read_text(encoding="utf-8")
        # Static check: every ``method_name=`` value
        # in the spec list must NOT start with an
        # underscore.
        for line in source.splitlines():
            if "method_name=" in line:
                # crude but adequate: extract the
                # right-hand-side of method_name="..."
                rhs = line.split("method_name=", 1)[1]
                rhs = rhs.split(",", 1)[0].strip().strip('"').strip("'")
                assert not rhs.startswith("_"), (
                    f"private method referenced in "
                    f"metadata.py: {rhs!r}"
                )


# ---------------------------------------------------------------------------
# End-to-end with Configuration injection
# ---------------------------------------------------------------------------


class TestConfigurationInjection:
    def test_cli_loads_public_configuration(self, monkeypatch):
        """The CLI must call ``load_configuration``
        from the public SDK surface — not reach
        into private internals.
        """
        monkeypatch.delenv("UN_COMTRADE_KEY", raising=False)
        # We assert by intercepting at the
        # boundary: the metadata command constructs
        # ``ComtradeClient(configuration=cfg)``; if
        # ``cfg`` is a real ``Configuration`` we
        # know the public path was used.
        seen_config = []

        class _SpyClient:
            def __init__(self, configuration=None, **_kw):
                seen_config.append(configuration)

            @property
            def metadata(self):
                m = mock.MagicMock()
                m.get_countries.return_value = []
                return m

            def close(self):
                pass

        with mock.patch(
            "un_comtrade.cli.commands.metadata.ComtradeClient",
            _SpyClient,
        ):
            code = main(["metadata", "countries"])
        assert code == EXIT_OK
        assert seen_config, "ComtradeClient was not called"
        from un_comtrade.config import Configuration
        assert isinstance(seen_config[0], Configuration)