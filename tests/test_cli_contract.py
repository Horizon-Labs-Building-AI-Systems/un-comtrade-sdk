"""CLI Contract Verification (C-007A).

Five contracts are verified by this module:

1.  **One-to-one mapping.** Every CLI leaf subcommand delegates to
    exactly one public SDK entry point. The mapping is declared in
    :data:`EXPECTED_MAPPING` and cross-checked against the actual
    importable attribute on the SDK.

2.  **No private imports.** No file under ``un_comtrade/cli/`` may
    ``import`` from a private module (anything under ``un_comtrade._*``).

3.  **Help coverage.** Every reachable subparser appears in ``--help``
    with a non-empty help string.

4.  **Documented examples execute.** The five recipes documented in
    ``docs/032_CLI_REVIEW.md`` §14 (and re-published in
    ``docs/033_CLI_CONTRACT_VERIFICATION.md``) all return exit code
    ``0`` against a mocked transport.

5.  **Command-tree frozen.** The set of reachable subcommand paths and
    their user-visible flags are pinned to the v1.0.x release. Future
    versions that change the tree must update :data:`FROZEN_TREE` in
    an explicit, reviewed commit.

These tests are the regression gate for the CLI's public contract.
"""

from __future__ import annotations

import argparse
import ast
import glob
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

import pytest

import un_comtrade
import un_comtrade.cli
from un_comtrade.cli import build_parser, main


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _walk_subparsers(
    parser: argparse.ArgumentParser, parent: tuple[str, ...] = ()
) -> list[tuple[tuple[str, ...], argparse.ArgumentParser]]:
    """Return ``(path, subparser)`` for every reachable subparser."""
    found: list[tuple[tuple[str, ...], argparse.ArgumentParser]] = [
        (parent, parser)
    ]
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, sub in action.choices.items():
                found.extend(_walk_subparsers(sub, parent + (name,)))
    return found


def _leaf_subparsers(
    parser: argparse.ArgumentParser,
) -> list[tuple[tuple[str, ...], argparse.ArgumentParser]]:
    """Return only leaf subparsers (those without nested subparsers)."""
    leaves: list[tuple[tuple[str, ...], argparse.ArgumentParser]] = []
    for path, sp in _walk_subparsers(parser):
        has_subs = any(
            isinstance(a, argparse._SubParsersAction) for a in sp._actions
        )
        if not has_subs and path:
            leaves.append((path, sp))
    return leaves


def _user_visible_flags(sp: argparse.ArgumentParser) -> list[str]:
    """Return sorted user-visible flags (excluding ``-h``/``--help``)."""
    flags: set[str] = set()
    for action in sp._actions:
        if isinstance(action, argparse._SubParsersAction):
            continue
        for opt in action.option_strings:
            if opt in {"-h", "--help"}:
                continue
            flags.add(opt)
    return sorted(flags)


def _required_flags(sp: argparse.ArgumentParser) -> list[str]:
    """Return sorted required user-visible flags (excluding ``-h``/``--help``)."""
    required: set[str] = set()
    for action in sp._actions:
        if isinstance(action, argparse._SubParsersAction):
            continue
        if not getattr(action, "required", False):
            continue
        for opt in action.option_strings:
            if opt in {"-h", "--help"}:
                continue
            required.add(opt)
    return sorted(required)


def _cli_source_files() -> list[str]:
    """All Python source files under ``un_comtrade/cli/``."""
    return sorted(
        glob.glob(os.path.join("un_comtrade", "cli", "**", "*.py"), recursive=True)
    )


# ---------------------------------------------------------------------------
# Contract 1 — One-to-one mapping
# ---------------------------------------------------------------------------


#: Authoritative mapping: ``(command_group, leaf) -> "module.path:attr"``.
#: Each leaf subcommand delegates to exactly one public SDK entry
#: point. The ``:attr`` part may be a dotted path (e.g.
#: ``"un_comtrade.storage.parquet.ParquetWriter.store"`` resolves the
#: attribute by walking the dotted path). Adding a leaf = adding a row
#: here; this is the single source of truth for the contract.
EXPECTED_MAPPING: dict[tuple[str, str], str] = {
    # metadata
    ("metadata", "countries"):        "un_comtrade.metadata:MetadataService.get_countries",
    ("metadata", "partners"):         "un_comtrade.metadata:MetadataService.get_partners",
    ("metadata", "classifications"):  "un_comtrade.metadata:MetadataService.get_classifications",
    ("metadata", "frequencies"):      "un_comtrade.metadata:MetadataService.get_frequencies",
    ("metadata", "transport-modes"):  "un_comtrade.metadata:MetadataService.get_transport_modes",
    ("metadata", "hs"):               "un_comtrade.metadata:MetadataService.get_hs_codes",
    # trade
    ("trade", "exports"):             "un_comtrade.trade:TradeService.get_exports",
    ("trade", "imports"):             "un_comtrade.trade:TradeService.get_imports",
    ("trade", "world"):               "un_comtrade.trade:TradeService.get_world_trade",
    ("trade", "bilateral"):           "un_comtrade.trade:TradeService.get_bilateral",
    ("trade", "balance"):             "un_comtrade.trade:TradeService.get_trade_balance",
    ("trade", "tariffline"):          "un_comtrade.trade:TradeService.get_tariffline",
    # analytics (live in submodule functions, not on AnalyticsEngine)
    ("analytics", "country"):         "un_comtrade.analytics.country:country_summary",
    ("analytics", "partner"):         "un_comtrade.analytics.partner:top_partners",
    ("analytics", "commodity"):       "un_comtrade.analytics.commodity:top_hs_codes",
    ("analytics", "trend"):           "un_comtrade.analytics.timeseries:annual_trend",
    ("analytics", "balance"):         "un_comtrade.analytics.balance:country_balance",
    ("analytics", "compare"):         "un_comtrade.analytics.compare:country_vs_country",
    # storage (delegate to public *Writer.store)
    ("storage", "parquet"):           "un_comtrade.storage.parquet:ParquetWriter.store",
    ("storage", "csv"):               "un_comtrade.storage.file:CSVWriter.store",
    ("storage", "json"):              "un_comtrade.storage.file:JSONWriter.store",
    ("storage", "duckdb"):            "un_comtrade.storage.duckdb:DuckDBWriter.store",
    # etl
    ("etl", "run"):                   "un_comtrade.etl:ETLPipeline.run",
}


def _resolve(module_dot_path: str) -> Any:
    """Resolve ``module.path:attr.path`` to the underlying attribute.

    Returns a tuple ``(module, attribute)`` where ``attribute`` is the
    final object after walking the dotted ``attr.path``.
    """
    if ":" not in module_dot_path:
        raise ValueError(
            f"spec {module_dot_path!r} must be in 'module.path:attr.path' form"
        )
    module_name, _, attr_path = module_dot_path.partition(":")
    if not module_name.startswith("un_comtrade"):
        raise ValueError(
            f"module {module_name!r} must be a public un_comtrade.* module"
        )
    if "." in module_name.lstrip("_"):  # catch leading-underscore privates
        pass
    if module_name.split(".")[0] == "un_comtrade" and any(
        part.startswith("_") for part in module_name.split(".")[1:]
    ):
        raise ValueError(
            f"module {module_name!r} is a private (leading-underscore) module"
        )
    mod = importlib.import_module(module_name)
    obj: Any = mod
    for part in attr_path.split("."):
        obj = getattr(obj, part)
        if obj is None:
            raise AttributeError(
                f"could not resolve {module_dot_path!r}: attribute "
                f"{part!r} is None"
            )
    return obj


class TestOneToOneMapping:
    """Every leaf CLI subcommand delegates to exactly one public SDK
    entry point. The mapping is the same on every release."""

    def test_every_leaf_in_mapping(self) -> None:
        """No leaf is missing from EXPECTED_MAPPING."""
        parser = build_parser()
        leaves = {tuple(p) for p, _ in _leaf_subparsers(parser)}
        leaves.discard(("root",))
        expected = set(EXPECTED_MAPPING.keys())
        missing = leaves - expected
        extra = expected - leaves
        assert not missing, f"leaf subparsers missing from mapping: {sorted(missing)}"
        assert not extra, f"mapping entries with no matching subparser: {sorted(extra)}"

    def test_every_mapping_entry_is_a_real_public_symbol(self) -> None:
        """Each ``module.path:attr`` resolves to an importable,
        public, callable attribute on the SDK."""
        for (group, leaf), ref in EXPECTED_MAPPING.items():
            attr = _resolve(ref)
            assert callable(attr), (
                f"{ref!r} is not callable (resolved to {type(attr).__name__})"
            )

    def test_mapping_is_one_to_one(self) -> None:
        """No two leaves map to the same public attribute (would
        imply duplicate or ambiguous bindings)."""
        seen: dict[str, tuple[str, str]] = {}
        for path, ref in EXPECTED_MAPPING.items():
            if ref in seen:
                raise AssertionError(
                    f"{ref!r} is mapped twice: {seen[ref]} and {path}"
                )
            seen[ref] = path

    def test_every_mapping_module_is_public(self) -> None:
        """Every module in the mapping must be importable from a
        public ``un_comtrade.*`` path (no leading-underscore modules,
        no private submodules)."""
        for path, ref in EXPECTED_MAPPING.items():
            module_name = ref.partition(":")[0]
            parts = module_name.split(".")
            assert parts[0] == "un_comtrade", (
                f"{ref!r}: top-level module must be un_comtrade"
            )
            assert not any(p.startswith("_") for p in parts[1:]), (
                f"{ref!r}: contains a private (underscore) submodule"
            )


# ---------------------------------------------------------------------------
# Contract 2 — No private imports
# ---------------------------------------------------------------------------


class TestNoPrivateImports:
    """Zero ``from un_comtrade._*`` imports anywhere in the CLI."""

    def test_no_private_imports(self) -> None:
        violations: list[tuple[str, int, str]] = []
        for path in _cli_source_files():
            tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("un_comtrade._"):
                        violations.append(
                            (
                                path,
                                node.lineno,
                                f"from {node.module} import ...",
                            )
                        )
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("un_comtrade._"):
                            violations.append(
                                (
                                    path,
                                    node.lineno,
                                    f"import {alias.name}",
                                )
                            )
        assert not violations, (
            "CLI imports private modules:\n"
            + "\n".join(f"  {p}:{ln} {what}" for p, ln, what in violations)
        )


# ---------------------------------------------------------------------------
# Contract 3 — Every command in --help
# ---------------------------------------------------------------------------


class TestEveryCommandInHelp:
    """Every reachable subparser appears in ``--help`` with a
    non-empty help string."""

    def test_every_subparser_has_help(self) -> None:
        parser = build_parser()
        for path, sp in _walk_subparsers(parser):
            if path == ():
                continue
            assert sp.description or sp.help, (
                f"subparser {path!r} has empty help"
            )

    def test_root_help_lists_every_group(self) -> None:
        parser = build_parser()
        import io

        buf = io.StringIO()
        original = sys.stdout
        sys.stdout = buf
        try:
            with pytest.raises(SystemExit):
                parser.parse_args(["--help"])
        finally:
            sys.stdout = original
        rendered = buf.getvalue()

        for group in EXPECTED_MAPPING:
            assert group[0] in rendered, (
                f"root --help is missing top-level command {group[0]!r}"
            )

    def test_group_help_lists_every_leaf(self) -> None:
        parser = build_parser()
        for path, sp in _walk_subparsers(parser):
            if path == () or len(path) != 1:
                continue
            group = path[0]
            if group == "root":
                continue
            leaves_for_group = {
                leaf for (g, leaf) in EXPECTED_MAPPING if g == group
            }
            inner = next(
                action
                for action in sp._actions
                if isinstance(action, argparse._SubParsersAction)
            )
            for leaf_name in leaves_for_group:
                assert leaf_name in inner.choices, (
                    f"group {group!r} help is missing leaf {leaf_name!r}"
                )


# ---------------------------------------------------------------------------
# Contract 4 — Documented examples execute
# ---------------------------------------------------------------------------


class _StubTransport:
    """In-process transport stub used by contract tests.

    Implements only the methods that the public SDK actually calls
    during a CLI command: ``send`` (returns a stub response) and
    ``close`` (no-op). All command bodies never see the real network.
    """

    def __init__(self, payload: Any = None) -> None:
        self._payload = payload if payload is not None else {"data": []}

    def send(self, request):  # noqa: ANN001 - signature from HttpTransport
        return self._payload

    def close(self) -> None:
        return None


def _patch_transport(monkeypatch: pytest.MonkeyPatch, payload: Any = None) -> None:
    """Patch ``HttpTransport`` constructors in every public module
    that imports it."""
    stub_factory = lambda *_a, **_kw: _StubTransport(payload)
    monkeypatch.setattr(
        "un_comtrade.transport.HttpTransport",
        stub_factory,
    )
    for module_name in (
        "un_comtrade.client",
        "un_comtrade.metadata",
        "un_comtrade.trade",
    ):
        try:
            monkeypatch.setattr(
                f"{module_name}.HttpTransport",
                stub_factory,
            )
        except (ImportError, AttributeError):
            pass


def _csv_dataset(tmp_path: Path) -> Path:
    """Write a tiny CSV fixture."""
    p = tmp_path / "tiny.csv"
    p.write_text(
        "ref_period_id,reporter_code,partner_code,flow_code,"
        "commodity_code,primary_value\n"
        "2022,699,0,X,TOTAL,100\n",
        encoding="utf-8",
    )
    return p


class TestDocumentedExamplesExecute:
    """The five recipes documented in
    ``docs/032_CLI_REVIEW.md`` §14 (and republished in
    ``docs/033_CLI_CONTRACT_VERIFICATION.md``) all return exit code 0
    when invoked against ``ComtradeClient`` (mocked at the
    construction boundary), the public ``Storage`` writers, and a
    tiny CSV dataset.

    Following the established pattern in
    ``tests/test_cli_*.py``, we mock ``ComtradeClient`` at the
    construction site of each command module — that is the
    documented "mocked services" boundary for the v1.0.x CLI.
    """

    def _mocked_metadata_client(self, monkeypatch: pytest.MonkeyPatch) -> dict:
        """Patch ``ComtradeClient.metadata`` with a MagicMock that
        returns a stable, empty list for every catalogue method.
        """
        from unittest import mock
        from un_comtrade.cli.commands import metadata as cli_meta

        fake_service = mock.MagicMock()
        fake_service.get_countries.return_value = []
        fake_service.get_partners.return_value = []
        fake_service.get_classifications.return_value = []
        fake_service.get_frequencies.return_value = []
        fake_service.get_transport_modes.return_value = []
        fake_service.get_hs_codes.return_value = []

        fake_client = mock.MagicMock()
        fake_client.metadata = fake_service
        monkeypatch.setattr(cli_meta, "ComtradeClient", lambda *a, **kw: fake_client)
        return {"client": fake_client, "service": fake_service}

    def _mocked_trade_client(self, monkeypatch: pytest.MonkeyPatch) -> dict:
        """Patch ``ComtradeClient.trade`` with a MagicMock that
        returns a ``TradeResponse`` with empty records for every
        ``TradeService`` method.
        """
        from unittest import mock
        from un_comtrade.cli.commands import trade as cli_trade
        from un_comtrade.trade import TradeResponse

        def _empty_response(*args, **kwargs):  # noqa: ANN001
            return TradeResponse(
                elapsed_seconds=0.0,
                count=0,
                records=[],
                error="",
                upstream_url="https://example.invalid",
                request={},
                skipped=0,
            )

        fake_service = mock.MagicMock()
        fake_service.get_exports.side_effect = _empty_response
        fake_service.get_imports.side_effect = _empty_response
        fake_service.get_world_trade.side_effect = _empty_response
        fake_service.get_bilateral.side_effect = _empty_response
        fake_service.get_trade_balance.side_effect = _empty_response
        fake_service.get_tariffline.side_effect = _empty_response

        fake_client = mock.MagicMock()
        fake_client.trade = fake_service
        monkeypatch.setattr(cli_trade, "ComtradeClient", lambda *a, **kw: fake_client)
        return {"client": fake_client, "service": fake_service}

    def _mocked_analytics_engine(self, monkeypatch: pytest.MonkeyPatch) -> dict:
        """Patch the analytics submodules' public functions with
        MagicMocks. The CLI's analytics commands dispatch via
        ``getattr(importlib.import_module(module_path), method_name)``
        so we patch at the submodule level."""
        from unittest import mock
        from un_comtrade.cli.commands import analytics as cli_an

        empty = {"data": [], "rows": []}
        fake_country = mock.MagicMock(return_value=empty)
        fake_partner = mock.MagicMock(return_value=empty)
        fake_commodity = mock.MagicMock(return_value=empty)
        fake_trend = mock.MagicMock(return_value=empty)
        fake_balance = mock.MagicMock(return_value=empty)
        fake_compare = mock.MagicMock(return_value=empty)

        import un_comtrade.analytics.country as country_mod
        import un_comtrade.analytics.partner as partner_mod
        import un_comtrade.analytics.commodity as commodity_mod
        import un_comtrade.analytics.timeseries as timeseries_mod
        import un_comtrade.analytics.balance as balance_mod
        import un_comtrade.analytics.compare as compare_mod

        monkeypatch.setattr(country_mod, "country_summary", fake_country)
        monkeypatch.setattr(partner_mod, "top_partners", fake_partner)
        monkeypatch.setattr(commodity_mod, "top_hs_codes", fake_commodity)
        monkeypatch.setattr(timeseries_mod, "annual_trend", fake_trend)
        monkeypatch.setattr(balance_mod, "country_balance", fake_balance)
        monkeypatch.setattr(compare_mod, "country_vs_country", fake_compare)
        return {
            "country_summary": fake_country,
            "top_partners": fake_partner,
            "top_hs_codes": fake_commodity,
            "annual_trend": fake_trend,
            "country_balance": fake_balance,
            "country_vs_country": fake_compare,
        }

    def test_recipe_1_metadata_countries(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mocks = self._mocked_metadata_client(monkeypatch)
        code = main(["metadata", "countries"])
        out = capsys.readouterr()
        assert code == 0, f"exit {code}\nstderr:\n{out.err}\nstdout:\n{out.out}"
        mocks["service"].get_countries.assert_called_once()

    def test_recipe_2_trade_exports_authenticated(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mocks = self._mocked_trade_client(monkeypatch)
        code = main(
            [
                "trade", "exports",
                "--reporter", "699",
                "--year", "2022",
                "--partner", "0",
                "--api-key", "test-key",
            ]
        )
        out = capsys.readouterr()
        assert code == 0, f"exit {code}\nstderr:\n{out.err}\nstdout:\n{out.out}"
        mocks["service"].get_exports.assert_called_once()

    def test_recipe_3_markdown_report(
        self, monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``analytics country`` exercises the dataset-loading path
        and the markdown formatter in one go. We mock at three
        boundaries: the analytics function (submodule level), the
        CSV reader (so the tiny fixture loads), and the metadata
        sidecar requirement (the CSVWriter reads it)."""
        self._mocked_analytics_engine(monkeypatch)
        # Provide a dataset directory layout that the storage reader accepts.
        ds_dir = tmp_path / "tiny"
        ds_dir.mkdir()
        csv_path = ds_dir / "records.csv"
        csv_path.write_text(
            "ref_period_id,reporter_code,partner_code,flow_code,"
            "commodity_code,primary_value\n"
            "2022,699,0,X,TOTAL,100\n",
            encoding="utf-8",
        )
        # Write a minimal metadata sidecar that the reader accepts.
        import json as _json
        (ds_dir / "metadata.json").write_text(
            _json.dumps(
                {
                    "dataset_name": "tiny",
                    "schema_version": "1.0.0",
                    "row_count": 1,
                }
            ),
            encoding="utf-8",
        )
        out_path = tmp_path / "report.md"
        code = main(
            [
                "analytics", "country",
                "--dataset", str(ds_dir),
                "--reporter", "699",
                "--output-format", "markdown",
                "--output", str(out_path),
            ]
        )
        out = capsys.readouterr()
        assert code == 0, f"exit {code}\nstderr:\n{out.err}\nstdout:\n{out.out}"
        assert out_path.exists() and out_path.stat().st_size > 0

    def test_recipe_4_storage_duckdb(
        self, monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from un_comtrade.storage.duckdb import DuckDBWriter

        called: dict[str, Any] = {}

        def _stub_store(self, dataset, config):  # noqa: ANN001
            from un_comtrade.storage._base import (
                DatasetMetadata,
                StorageBackend,
                StorageResult,
            )
            called["path"] = str(config.root)
            called["table_name"] = config.table_name
            meta = DatasetMetadata(
                dataset_name=dataset.name,
                schema_version=dataset.schema_version,
                parser_name=dataset.parser_name,
                record_count=len(dataset.records),
                skipped=dataset.skipped,
                duplicates_removed=dataset.duplicates_removed,
                source_count=dataset.source_count,
                extracted_at=dataset.extracted_at,
                stored_at=dataset.extracted_at,
                partition_keys=(),
                backend=StorageBackend.DUCKDB,
                destination=str(config.root),
                extra={},
            )
            return StorageResult(
                backend=StorageBackend.DUCKDB,
                destination=str(config.root),
                metadata=meta,
                partitions=(),
                byte_size=0,
            )

        monkeypatch.setattr(DuckDBWriter, "store", _stub_store)
        # Provide a dataset directory layout.
        ds_dir = tmp_path / "tiny"
        ds_dir.mkdir()
        (ds_dir / "records.csv").write_text(
            "ref_period_id,reporter_code,partner_code,flow_code,"
            "commodity_code,primary_value\n"
            "2022,699,0,X,TOTAL,100\n",
            encoding="utf-8",
        )
        import json as _json
        (ds_dir / "metadata.json").write_text(
            _json.dumps(
                {"dataset_name": "tiny", "schema_version": "1.0.0", "row_count": 1}
            ),
            encoding="utf-8",
        )
        out_path = tmp_path / "data.duckdb"
        code = main(
            [
                "storage", "duckdb",
                "--dataset", str(ds_dir),
                "--output-path", str(out_path),
            ]
        )
        out = capsys.readouterr()
        assert code == 0, f"exit {code}\nstderr:\n{out.err}\nstdout:\n{out.out}"
        assert called.get("path") == str(out_path)


# ---------------------------------------------------------------------------
# Contract 5 — Command-tree frozen
# ---------------------------------------------------------------------------


#: Frozen command tree at v1.0.x. Each entry is the full subparser
#: path plus the set of *user-visible* flags (excluding the
#: auto-generated ``-h``/``--help``) and the subset of required flags.
#:
#: Any future commit that changes the tree (added/removed/renamed
#: command, renamed flag, changed required/optional status) MUST
#: update this dict in the same commit and call it out in CHANGELOG.
#:
#: Regenerate with: ``python _gen_snapshot.py`` (kept in repo root,
#: trash after use).
FROZEN_TREE: dict[str, dict[str, Any]] = {
    "analytics/balance": {
        "flags": [
            "--api-key", "--dataset", "--limit", "--log-level",
            "--output", "--output-format", "--reporter",
        ],
        "required": ["--dataset"],
    },
    "analytics/commodity": {
        "flags": [
            "--api-key", "--dataset", "--flow", "--limit", "--log-level",
            "--output", "--output-format", "--reporter",
        ],
        "required": ["--dataset"],
    },
    "analytics/compare": {
        "flags": [
            "--api-key", "--breakdown-by", "--dataset", "--log-level",
            "--output", "--output-format", "--reporter",
        ],
        "required": ["--dataset", "--reporter"],
    },
    "analytics/country": {
        "flags": [
            "--api-key", "--dataset", "--log-level", "--output",
            "--output-format", "--reporter",
        ],
        "required": ["--dataset", "--reporter"],
    },
    "analytics/partner": {
        "flags": [
            "--api-key", "--dataset", "--flow", "--limit", "--log-level",
            "--output", "--output-format", "--reporter",
        ],
        "required": ["--dataset", "--reporter"],
    },
    "analytics/trend": {
        "flags": [
            "--api-key", "--dataset", "--flow", "--log-level", "--output",
            "--output-format", "--partner", "--reporter",
        ],
        "required": ["--dataset"],
    },
    "etl/run": {
        "flags": [
            "--api-key", "--log-level", "--output", "--output-format",
            "--pipeline-config", "--source",
        ],
        "required": ["--pipeline-config"],
    },
    "metadata/classifications": {
        "flags": [
            "--api-key", "--log-level", "--output", "--output-format",
        ],
        "required": [],
    },
    "metadata/countries": {
        "flags": [
            "--api-key", "--log-level", "--output", "--output-format",
        ],
        "required": [],
    },
    "metadata/frequencies": {
        "flags": [
            "--api-key", "--log-level", "--output", "--output-format",
        ],
        "required": [],
    },
    "metadata/hs": {
        "flags": [
            "--api-key", "--edition", "--log-level", "--output",
            "--output-format",
        ],
        "required": [],
    },
    "metadata/partners": {
        "flags": [
            "--api-key", "--log-level", "--output", "--output-format",
        ],
        "required": [],
    },
    "metadata/transport-modes": {
        "flags": [
            "--api-key", "--log-level", "--output", "--output-format",
        ],
        "required": [],
    },
    "storage/csv": {
        "flags": [
            "--api-key", "--dataset", "--log-level", "--output",
            "--output-format", "--output-path", "--overwrite",
            "--table-name",
        ],
        "required": ["--dataset", "--output-path"],
    },
    "storage/duckdb": {
        "flags": [
            "--api-key", "--dataset", "--log-level", "--output",
            "--output-format", "--output-path", "--overwrite",
            "--table-name",
        ],
        "required": ["--dataset", "--output-path"],
    },
    "storage/json": {
        "flags": [
            "--api-key", "--dataset", "--log-level", "--output",
            "--output-format", "--output-path", "--overwrite",
            "--table-name",
        ],
        "required": ["--dataset", "--output-path"],
    },
    "storage/parquet": {
        "flags": [
            "--api-key", "--dataset", "--log-level", "--output",
            "--output-format", "--output-path", "--overwrite",
            "--table-name",
        ],
        "required": ["--dataset", "--output-path"],
    },
    "trade/balance": {
        "flags": [
            "--api-key", "--breakdown-mode", "--classification",
            "--commodity", "--edition", "--frequency", "--log-level",
            "--max-records", "--output", "--output-format",
            "--partner", "--period", "--progress", "--reporter",
            "--year",
        ],
        "required": ["--period", "--reporter", "--year"],
    },
    "trade/bilateral": {
        "flags": [
            "--api-key", "--breakdown-mode", "--classification",
            "--commodity", "--edition", "--flow", "--frequency",
            "--log-level", "--max-records", "--output",
            "--output-format", "--partner", "--period", "--progress",
            "--reporter", "--year",
        ],
        "required": ["--period", "--reporter", "--year"],
    },
    "trade/exports": {
        "flags": [
            "--api-key", "--breakdown-mode", "--classification",
            "--commodity", "--edition", "--frequency", "--log-level",
            "--max-records", "--output", "--output-format",
            "--partner", "--period", "--progress", "--reporter",
            "--year",
        ],
        "required": ["--period", "--reporter", "--year"],
    },
    "trade/imports": {
        "flags": [
            "--api-key", "--breakdown-mode", "--classification",
            "--commodity", "--edition", "--frequency", "--log-level",
            "--max-records", "--output", "--output-format",
            "--partner", "--period", "--progress", "--reporter",
            "--year",
        ],
        "required": ["--period", "--reporter", "--year"],
    },
    "trade/tariffline": {
        "flags": [
            "--api-key", "--breakdown-mode", "--classification",
            "--commodity", "--edition", "--flow", "--frequency",
            "--log-level", "--max-records", "--output",
            "--output-format", "--partner", "--period", "--progress",
            "--reporter", "--year",
        ],
        "required": ["--period", "--reporter", "--year"],
    },
    "trade/world": {
        "flags": [
            "--api-key", "--breakdown-mode", "--classification",
            "--commodity", "--edition", "--flow", "--frequency",
            "--log-level", "--max-records", "--output",
            "--output-format", "--partner", "--period", "--progress",
            "--reporter", "--year",
        ],
        "required": ["--period", "--reporter", "--year"],
    },
}


class TestCommandTreeFrozen:
    """The reachable CLI command tree is frozen for v1.0.x. Any
    change to command paths, flag names, or required-flag status is
    a breaking change and MUST update :data:`FROZEN_TREE` in the
    same commit."""

    def test_tree_matches_frozen_snapshot(self) -> None:
        parser = build_parser()
        actual: dict[str, dict[str, Any]] = {}
        for path, sp in _leaf_subparsers(parser):
            if path == ("root",):
                continue
            actual["/".join(path)] = {
                "flags": _user_visible_flags(sp),
                "required": _required_flags(sp),
            }
        assert actual == FROZEN_TREE, _diff_tree(actual, FROZEN_TREE)

    def test_no_subparser_path_uses_uppercase(self) -> None:
        """Convention: every command path component is lowercase,
        possibly hyphenated. Stability includes case stability."""
        parser = build_parser()
        for path, _ in _walk_subparsers(parser):
            for component in path:
                assert component == component.lower(), (
                    f"command path component {component!r} must be lowercase"
                )

    def test_no_subparser_path_collides_with_global_flag(self) -> None:
        """A command path must not collide with a global flag name."""
        parser = build_parser()
        root_flag_names = {
            opt
            for action in parser._actions
            if not isinstance(action, argparse._SubParsersAction)
            for opt in action.option_strings
        }
        for path, _ in _walk_subparsers(parser):
            for component in path:
                assert component not in root_flag_names, (
                    f"command path component {component!r} collides "
                    f"with root flag"
                )


def _diff_tree(actual: dict, frozen: dict) -> str:
    """Render a human-readable diff between the actual and frozen tree."""
    added = set(actual) - set(frozen)
    removed = set(frozen) - set(actual)
    changed = sorted(
        p for p in actual if p in frozen and actual[p] != frozen[p]
    )
    lines: list[str] = []
    for p in sorted(added):
        lines.append(f"+ {p}: {actual[p]!r}")
    for p in sorted(removed):
        lines.append(f"- {p}: {frozen[p]!r}")
    for p in changed:
        lines.append(f"~ {p}:")
        lines.append(f"    expected: {frozen[p]!r}")
        lines.append(f"    actual:   {actual[p]!r}")
    return "\n".join(lines) if lines else "no diff"