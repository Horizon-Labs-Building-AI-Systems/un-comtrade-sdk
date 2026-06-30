"""Output formatting for the CLI.

The CLI supports five output formats declared
in :data:`un_comtrade.cli.utils.OUTPUT_FORMATS`:

- ``"json"``     — stable JSON output.
- ``"table"``    — aligned text table.
- ``"csv"``      — RFC 4180 CSV.
- ``"markdown"`` — GitHub-Flavored-Markdown table.
- ``"text"``     — line-oriented plain text.

Each formatter implements the
:class:`OutputFormatter` protocol.

The five formatters live in:

- :mod:`un_comtrade.cli.formatting.json`
- :mod:`un_comtrade.cli.formatting.table`
- :mod:`un_comtrade.cli.formatting.csv`
- :mod:`un_comtrade.cli.formatting.markdown`
- :mod:`un_comtrade.cli.formatting.text`

The private module :mod:`_records` provides
shared row-dict normalisation helpers used by
all five.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable

from un_comtrade.cli.utils import OUTPUT_FORMATS
from un_comtrade.cli.formatting.csv import CsvFormatter
from un_comtrade.cli.formatting.json import JsonFormatter
from un_comtrade.cli.formatting.markdown import MarkdownFormatter
from un_comtrade.cli.formatting.table import TableFormatter
from un_comtrade.cli.formatting.text import TextFormatter


@runtime_checkable
class OutputFormatter(Protocol):
    """Protocol every output formatter must
    implement.

    A formatter takes a Python value (typically a
    dict, list of dicts, or a dataclass) and
    returns a string ready to be written to
    stdout.
    """

    name: str

    def render(self, value: Any) -> str: ...


#: Internal registry: format name → formatter
#: class.
_FORMATTERS: Mapping[str, type[OutputFormatter]] = {
    "json": JsonFormatter,
    "table": TableFormatter,
    "csv": CsvFormatter,
    "markdown": MarkdownFormatter,
    "text": TextFormatter,
}


def get_formatter(name: str) -> OutputFormatter:
    """Return the formatter registered under
    ``name``. Raises :class:`KeyError` on unknown
    names; :func:`un_comtrade.cli.main.main`
    translates this into ``EXIT_USER_ERROR``.
    """
    if name not in OUTPUT_FORMATS:
        raise KeyError(name)
    cls = _FORMATTERS[name]
    return cls()


__all__ = [
    "CsvFormatter",
    "JsonFormatter",
    "MarkdownFormatter",
    "OutputFormatter",
    "TableFormatter",
    "TextFormatter",
    "get_formatter",
]