"""CSV output formatter.

RFC 4180-compliant CSV. The output uses CRLF
line terminators (per RFC 4180) and the stdlib
:mod:`csv` module's minimal quoting.

Column ordering is taken from the dataclass
declaration when the rows are homogeneous
dataclasses; otherwise the union of keys
across rows in insertion order.

This file is named ``csv.py`` (not ``csv.py``
within a different name) because Python's
absolute import machinery correctly resolves
``import csv`` to the stdlib (the file's own
``__name__`` is ``un_comtrade.cli.formatting.csv``,
not ``csv``).
"""

from __future__ import annotations

import csv
import io
from typing import Any

from un_comtrade.cli.formatting._records import (
    collect_field_names,
    coerce_value,
    field_names_from_dataclass,
    to_dict,
)


class CsvFormatter:
    """RFC 4180 CSV formatter.

    Output is suitable for ``csv.reader`` /
    ``pandas.read_csv`` consumption. For
    machine-readable structured output, use
    :class:`JsonFormatter`.
    """

    name: str = "csv"

    def render(self, value: Any) -> str:
        """Render ``value`` as a CSV string.

        ``value`` may be:

        - a list of dicts / dataclasses
          (preferred — one row each);
        - a single dict / dataclass (single row);
        - a primitive (single cell, no header).
        """
        rows = self._coerce(value)
        if not rows:
            return ""

        column_names = self._column_names(rows)

        buf = io.StringIO(newline="")
        writer = csv.writer(
            buf,
            dialect="excel",  # RFC 4180 defaults
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writerow(column_names)
        for row in rows:
            writer.writerow(
                [_format_cell(row.get(col)) for col in column_names]
            )
        # csv.writer uses \r\n by default with
        # the excel dialect; preserve that.
        return buf.getvalue()

    @staticmethod
    def _column_names(rows: list[dict[str, Any]]) -> list[str]:
        sample = rows[0]
        names = field_names_from_dataclass(sample)
        if names is not None and all(
            set(r.keys()) == set(names) for r in rows
        ):
            return names
        return collect_field_names(rows)

    @staticmethod
    def _coerce(value: Any) -> list[dict[str, Any]]:
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            return [
                _to_row_dict(item)
                for item in value
                if item is not None
            ]
        return [_to_row_dict(value)]


def _to_row_dict(record: Any) -> dict[str, Any]:
    raw = to_dict(record)
    return {k: coerce_value(v) for k, v in raw.items()}


def _format_cell(value: Any) -> Any:
    """Format a single CSV cell. Numeric values are
    preserved as-is so downstream consumers get
    ints / floats; strings are passed through;
    ``None`` becomes an empty string. ``Decimal``
    is preserved as its string form (per
    :func:`un_comtrade.cli.formatting._records.coerce_value`).
    """
    if value is None:
        return ""
    return coerce_value(value)


__all__ = ["CsvFormatter"]