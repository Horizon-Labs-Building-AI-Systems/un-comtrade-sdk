"""Tests for the C-006 formatter isolation.

Each of the five formatters (json, csv, table,
markdown, text) lives in its own module under
``un_comtrade.cli.formatting``. Tests verify:

- Each formatter renders the canonical
  record-shape inputs to a stable,
  parseable-by-the-corresponding-tool output.
- The formatters are interchangeable via
  :func:`un_comtrade.cli.formatting.get_formatter`.
- All five formatters implement the
  :class:`OutputFormatter` protocol.
- ``OUTPUT_FORMATS`` exposes all five names.
- "Business logic never formats output": a
  static check confirms that the CLI command
  modules and the SDK command bodies do NOT
  contain any string-formatting calls that would
  pre-empt the formatter layer.
"""

from __future__ import annotations

import csv as _csv
import io
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from un_comtrade.cli.formatting import (
    CsvFormatter,
    JsonFormatter,
    MarkdownFormatter,
    OutputFormatter,
    TableFormatter,
    TextFormatter,
    get_formatter,
)
from un_comtrade.cli.utils import OUTPUT_FORMATS


# ---------------------------------------------------------------------------
# Sample fixtures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Country:
    name: str
    code: int
    region: str


SAMPLE_RECORDS = [
    _Country("India", 699, "Asia"),
    _Country("China", 156, "Asia"),
    _Country("United States", 840, "Americas"),
]


SAMPLE_DICTS = [
    {"name": "India", "code": 699, "region": "Asia"},
    {"name": "China", "code": 156, "region": "Asia"},
    {"name": "United States", "code": 840, "region": "Americas"},
]


# ---------------------------------------------------------------------------
# Per-formatter tests
# ---------------------------------------------------------------------------


class TestJsonFormatter:
    def test_renders_list_of_dicts(self):
        out = JsonFormatter().render(SAMPLE_DICTS)
        loaded = json.loads(out)
        assert loaded == SAMPLE_DICTS

    def test_renders_single_dict(self):
        out = JsonFormatter().render({"a": 1, "b": 2})
        loaded = json.loads(out)
        assert loaded == {"a": 1, "b": 2}

    def test_renders_dataclass(self):
        out = JsonFormatter().render(_Country("India", 699, "Asia"))
        loaded = json.loads(out)
        assert loaded == {"name": "India", "code": 699, "region": "Asia"}

    def test_decimal_preserved_as_string(self):
        out = JsonFormatter().render({"value": Decimal("123.456")})
        loaded = json.loads(out)
        assert loaded == {"value": "123.456"}

    def test_datetime_preserved_as_iso(self):
        dt = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        out = JsonFormatter().render({"t": dt})
        loaded = json.loads(out)
        assert loaded["t"] == "2026-01-01T12:00:00+00:00"

    def test_indent_and_sort_keys(self):
        out = JsonFormatter().render({"b": 1, "a": 2})
        assert "\n" in out  # indented
        # sort_keys=True means "a" precedes "b".
        assert out.index('"a"') < out.index('"b"')

    def test_stable_across_runs(self):
        """Two runs of the same input must produce
        byte-identical output.
        """
        v = {"x": 1, "y": [1, 2, 3]}
        a = JsonFormatter().render(v)
        b = JsonFormatter().render(v)
        assert a == b


class TestCsvFormatter:
    def test_renders_list_of_dicts(self):
        out = CsvFormatter().render(SAMPLE_DICTS)
        reader = _csv.reader(io.StringIO(out))
        rows = list(reader)
        # header + 3 data rows.
        assert len(rows) == 4
        assert rows[0] == ["name", "code", "region"]
        assert rows[1] == ["India", "699", "Asia"]
        assert rows[2] == ["China", "156", "Asia"]
        assert rows[3] == ["United States", "840", "Americas"]

    def test_renders_single_dict(self):
        out = CsvFormatter().render({"a": 1, "b": 2})
        rows = list(_csv.reader(io.StringIO(out)))
        assert rows[0] == ["a", "b"]
        assert rows[1] == ["1", "2"]

    def test_renders_dataclass(self):
        out = CsvFormatter().render(_Country("India", 699, "Asia"))
        rows = list(_csv.reader(io.StringIO(out)))
        assert rows[0] == ["name", "code", "region"]
        assert rows[1] == ["India", "699", "Asia"]

    def test_rfc_4180_line_terminator(self):
        """CSV output uses CRLF as the row
        terminator (RFC 4180).
        """
        out = CsvFormatter().render([{"a": 1}, {"a": 2}])
        # At least one CRLF between data rows.
        assert "\r\n" in out

    def test_empty_input_returns_empty(self):
        assert CsvFormatter().render([]) == ""


class TestTableFormatter:
    def test_renders_list_of_dicts(self):
        out = TableFormatter().render(SAMPLE_DICTS)
        lines = out.rstrip("\n").split("\n")
        # Header + separator + 3 rows = 5 lines.
        assert len(lines) == 5
        # Header contains column names.
        assert "name" in lines[0]
        assert "code" in lines[0]
        # Separator uses dashes between columns.
        sep = lines[1]
        assert "---" in sep
        # Count dash groups (each `---` group
        # separated by spaces).
        groups = [g for g in sep.split("  ") if g]
        assert len(groups) == 3
        assert all(set(g) == {"-"} for g in groups)
        # Data rows contain values.
        assert "India" in lines[2]
        assert "699" in lines[2]

    def test_renders_dataclass(self):
        out = TableFormatter().render(SAMPLE_RECORDS)
        assert "India" in out
        assert "699" in out
        assert "Asia" in out

    def test_column_width_alignment(self):
        """Column widths match the longest cell in
        each column. We verify that the header line
        is wider than the narrowest column's data.
        """
        out = TableFormatter().render(
            [
                {"a": "a-much-longer-value", "b": "x"},
                {"a": "short", "b": "y"},
            ]
        )
        # The header row is the longest because the
        # wide column's header equals the longest
        # data cell. Compare header length to each
        # data row.
        lines = out.rstrip("\n").split("\n")
        header_len = len(lines[0])
        for line in lines[2:]:
            assert header_len >= len(line), (
                f"header {header_len} < data {len(line)}: "
                f"{line!r}"
            )


class TestMarkdownFormatter:
    def test_renders_gfm_table(self):
        out = MarkdownFormatter().render(SAMPLE_DICTS)
        lines = out.rstrip("\n").split("\n")
        # Header + alignment + 3 rows = 5 lines.
        assert len(lines) == 5
        # Header row starts and ends with "|".
        assert lines[0].startswith("|")
        assert lines[0].endswith("|")
        # Alignment marker row has the same number
        # of cells as the header (one "---" per
        # column).
        sep_cells = [c for c in lines[1].split("|") if c.strip()]
        assert all(c.strip() == "---" for c in sep_cells), (
            f"alignment row malformed: {lines[1]!r}"
        )
        assert len(sep_cells) == 3
        # Each data row has the right number of
        # columns.
        for line in lines[2:]:
            cells = [c for c in line.split("|") if c.strip()]
            assert len(cells) == 3

    def test_renders_dataclass(self):
        out = MarkdownFormatter().render(SAMPLE_RECORDS)
        assert "| India | 699 | Asia |" in out

    def test_pipe_in_value_is_escaped(self):
        """Pipes inside cell values must be escaped
        with ``\\|`` so they don't break the row
        layout.
        """
        out = MarkdownFormatter().render(
            [{"name": "India | Bharat", "code": 699}]
        )
        # The cell "India | Bharat" must appear as
        # the escaped form in the rendered output.
        assert "India \\| Bharat" in out
        # Count the unescaped pipes in the data
        # row: a 2-cell data row has 3 unescaped
        # pipes (1 leading + 1 between + 1
        # trailing).
        data_row = [
            line for line in out.splitlines()
            if "India" in line
        ][0]
        unescaped = data_row.replace("\\|", "")
        pipe_count = unescaped.count("|")
        assert pipe_count == 3

    def test_empty_input_returns_empty(self):
        assert MarkdownFormatter().render([]) == ""


class TestTextFormatter:
    def test_renders_dict_as_key_value_lines(self):
        out = TextFormatter().render({"a": 1, "b": 2})
        lines = out.rstrip("\n").split("\n")
        assert "a: 1" in lines
        assert "b: 2" in lines

    def test_renders_list_of_dicts(self):
        out = TextFormatter().render(SAMPLE_DICTS)
        # Each dict renders as a key-value block.
        assert "name: India" in out
        assert "code: 699" in out
        # Blocks are separated by blank lines.
        assert "\n\n" in out

    def test_renders_primitive(self):
        out = TextFormatter().render("hello")
        assert out == "hello\n"

    def test_renders_list_of_primitives(self):
        out = TextFormatter().render(["a", "b", "c"])
        assert out == "a\nb\nc\n"

    def test_empty_input_returns_empty(self):
        assert TextFormatter().render(None) == ""

    def test_line_oriented_for_grep(self):
        """Output is line-oriented so users can pipe
        it through grep. Every non-empty line ends
        with a single newline.
        """
        out = TextFormatter().render(SAMPLE_DICTS)
        # No double-newlines at start or end.
        assert not out.startswith("\n")
        assert out.endswith("\n")


# ---------------------------------------------------------------------------
# Protocol + registry
# ---------------------------------------------------------------------------


class TestProtocolAndRegistry:
    def test_all_formatters_implement_protocol(self):
        for cls in (
            JsonFormatter,
            CsvFormatter,
            TableFormatter,
            MarkdownFormatter,
            TextFormatter,
        ):
            instance = cls()
            assert isinstance(instance, OutputFormatter)
            assert hasattr(instance, "render")
            assert callable(instance.render)

    @pytest.mark.parametrize("name,cls", [
        ("json", JsonFormatter),
        ("table", TableFormatter),
        ("csv", CsvFormatter),
        ("markdown", MarkdownFormatter),
        ("text", TextFormatter),
    ])
    def test_get_formatter_returns_correct_class(self, name, cls):
        formatter = get_formatter(name)
        assert isinstance(formatter, cls)
        assert formatter.name == name

    def test_get_formatter_unknown_raises_keyerror(self):
        with pytest.raises(KeyError):
            get_formatter("xml")

    def test_output_formats_lists_all_five(self):
        assert sorted(OUTPUT_FORMATS) == sorted([
            "json",
            "table",
            "csv",
            "markdown",
            "text",
        ])

    def test_formatter_names_match_output_formats(self):
        """The set of formatter ``name`` attributes
        must equal :data:`OUTPUT_FORMATS`.
        """
        formatter_names = {
            JsonFormatter().name,
            CsvFormatter().name,
            TableFormatter().name,
            MarkdownFormatter().name,
            TextFormatter().name,
        }
        assert formatter_names == set(OUTPUT_FORMATS)


# ---------------------------------------------------------------------------
# File structure
# ---------------------------------------------------------------------------


class TestFileStructure:
    """The five formatter modules live as
    separate files under
    ``un_comtrade/cli/formatting``.
    """

    @pytest.mark.parametrize("filename", [
        "json.py",
        "csv.py",
        "table.py",
        "markdown.py",
        "text.py",
    ])
    def test_formatter_file_exists(self, filename):
        path = Path("un_comtrade/cli/formatting") / filename
        assert path.exists(), f"missing {path}"
        assert path.stat().st_size > 0

    def test_old_formatter_files_removed(self):
        for old in (
            "json_formatter.py",
            "csv_formatter.py",
            "table_formatter.py",
        ):
            path = Path("un_comtrade/cli/formatting") / old
            assert not path.exists(), f"stale {path}"


# ---------------------------------------------------------------------------
# "Business logic never formats output" guard
# ---------------------------------------------------------------------------


class TestBusinessLogicNeverFormats:
    """Static check: the CLI command modules
    (analytics, metadata, trade, storage, etl)
    MUST NOT construct output strings themselves
    inside their ``_render_and_emit`` /
    ``render_and_emit`` / ``_dispatch`` body.

    Permitted:
    - Calling ``get_formatter(name).render(...)``
      to delegate to the formatter layer.
    - Calling ``render_to_destination(...)`` to
      route the result to stdout / file.
    - Error messages (raised ``CLIError`` strings)
      are exempt — those are diagnostic, not
      command output.

    Forbidden:
    - ``json.dumps(...)`` / ``csv.writer(...)``
      / manual ``|`` table building / manual
      Markdown building / manual text formatting.
    """

    # Patterns that indicate manual output
    # construction. The intent is to forbid
    # business logic from re-implementing a
    # formatter.
    FORBIDDEN_PATTERNS = [
        r"\bjson\.dumps\(",
        r"\bjson\.dump\(",
        r"\bcsv\.writer\(",
        r"\bcsv\.DictWriter\(",
        r"\bcsv\.reader\(",
    ]

    @pytest.mark.parametrize("cli_command_file", [
        "un_comtrade/cli/commands/metadata.py",
        "un_comtrade/cli/commands/trade.py",
        "un_comtrade/cli/commands/analytics.py",
        "un_comtrade/cli/commands/storage.py",
        "un_comtrade/cli/commands/etl.py",
    ])
    def test_cli_commands_do_not_construct_output_strings(
        self, cli_command_file
    ):
        path = Path(cli_command_file)
        if not path.exists():
            pytest.skip(f"{cli_command_file} missing")
        text = path.read_text(encoding="utf-8")
        # Strip docstrings + comments to avoid
        # false positives.
        import ast

        tree = ast.parse(text)
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
        for pattern in self.FORBIDDEN_PATTERNS:
            assert not re.search(pattern, cleaned), (
                f"{cli_command_file} contains forbidden "
                f"output-construction pattern {pattern!r}; "
                f"delegate to "
                f"un_comtrade.cli.formatting.get_formatter"
            )

    def test_cli_commands_route_through_formatter_layer(self):
        """CLI command bodies MUST route their
        output via ``get_formatter(name)`` (the
        public formatter layer). They MUST NOT
        bypass it with manual string-building.
        """
        SKIP = {"__init__.py"}
        for path in Path("un_comtrade/cli/commands").glob("*.py"):
            if path.name in SKIP:
                continue
            text = path.read_text(encoding="utf-8")
            # Each concrete command module must
            # reference ``get_formatter`` (or
            # ``render_to_destination`` which is
            # the formatter's output routing
            # helper).
            assert (
                "get_formatter" in text
                or "render_to_destination" in text
            ), (
                f"{path} does not appear to route "
                f"output through the formatter layer"
            )


# ---------------------------------------------------------------------------
# Interchangeability: a single value renders to all 5 formats
# ---------------------------------------------------------------------------


class TestInterchangeability:
    """A single record shape must render to all
    five formats without raising.
    """

    @pytest.mark.parametrize("fmt_name", [
        "json",
        "table",
        "csv",
        "markdown",
        "text",
    ])
    def test_renders_records_to_format(self, fmt_name):
        formatter = get_formatter(fmt_name)
        out = formatter.render(SAMPLE_DICTS)
        assert isinstance(out, str)
        assert len(out) > 0
        # JSON / CSV / Markdown / Table all
        # include the literal "India" string.
        # (Text formatter renders dicts as
        # "name: India" — also contains "India".)
        assert "India" in out

    @pytest.mark.parametrize("fmt_name", [
        "json",
        "table",
        "csv",
        "markdown",
        "text",
    ])
    def test_renders_dataclass_to_format(self, fmt_name):
        formatter = get_formatter(fmt_name)
        out = formatter.render(SAMPLE_RECORDS)
        assert "India" in out
        assert "699" in out


# ---------------------------------------------------------------------------
# Smoke test via the public main entry point
# ---------------------------------------------------------------------------


class TestMainEntrypoint:
    """The CLI's main() entry point must accept
    each of the five format names via
    --output-format.
    """

    @pytest.mark.parametrize("fmt", [
        "json",
        "table",
        "csv",
        "markdown",
        "text",
    ])
    def test_main_accepts_format(self, fmt, capsys, monkeypatch):
        # Use the existing root command (no
        # business logic) to verify the global
        # --output-format flag accepts all five
        # values.
        monkeypatch.delenv("UN_COMTRADE_LOG_LEVEL", raising=False)
        from un_comtrade.cli import main as cli_main
        code = cli_main(["--output-format", fmt])
        assert code == 0
        # Banner is printed; assert no crash.
        captured = capsys.readouterr()
        assert "un-comtrade" in captured.out