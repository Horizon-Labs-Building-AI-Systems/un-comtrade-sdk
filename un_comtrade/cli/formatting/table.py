"""Aligned text table formatter.

Plain-text column-per-field layout with
auto-computed column widths from the maximum
string-width across all cells (header + rows).
Numeric and boolean values are stringified via
``str``; ``None`` becomes an empty cell.

Records may be dicts, dataclasses, or
``Mapping``-like. The :mod:`_records` helpers
coerce them to row-dicts.
"""

from __future__ import annotations

from typing import Any

from un_comtrade.cli.formatting._records import (
    collect_field_names,
    coerce_value,
    field_names_from_dataclass,
    to_dict,
)


class TableFormatter:
    """Plain-text tabular formatter.

    Output is suitable for human consumption in
    a terminal. For machine-readable output, use
    :class:`JsonFormatter` or :class:`CsvFormatter`.
    """

    name: str = "table"

    def render(self, value: Any) -> str:
        """Render ``value`` as a text table.

        ``value`` may be:

        - a list of dicts / dataclasses
          (preferred — one row each);
        - a single dict / dataclass (single row);
        - a primitive (string repr in a single
          cell).
        """
        rows = self._coerce(value)
        if not rows:
            return ""
        # Pick the column ordering. Prefer the
        # dataclass-declared field order when the
        # rows are homogeneous dataclasses.
        sample = rows[0]
        column_names = field_names_from_dataclass(sample)
        if column_names is None:
            column_names = list(rows[0].keys())
        # Union of keys across rows for
        # heterogeneous inputs.
        if any(set(r.keys()) != set(column_names) for r in rows[1:]):
            column_names = collect_field_names(rows)

        # Stringify every cell.
        stringified: list[list[str]] = []
        for row in rows:
            stringified.append(
                [self._cell(row.get(col)) for col in column_names]
            )
        header = [str(col) for col in column_names]

        # Compute column widths (max of header /
        # row).
        widths = [
            max(
                len(header[i]),
                *(len(r[i]) for r in stringified),
            )
            for i in range(len(column_names))
        ]

        def _line(cells: list[str]) -> str:
            return "  ".join(
                cell.ljust(widths[i]) for i, cell in enumerate(cells)
            )

        # Compose: header + separator + rows.
        sep = "  ".join("-" * w for w in widths)
        out_lines = [_line(header), sep]
        out_lines.extend(_line(r) for r in stringified)
        return "\n".join(out_lines) + "\n"

    @staticmethod
    def _coerce(value: Any) -> list[dict[str, Any]]:
        """Coerce ``value`` to a list of row-dicts.
        """
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            return [
                _to_row_dict(item)
                for item in value
                if item is not None
            ]
        # Single record: wrap in a list.
        return [_to_row_dict(value)]

    @staticmethod
    def _cell(value: Any) -> str:
        if value is None:
            return ""
        return str(coerce_value(value))


def _to_row_dict(record: Any) -> dict[str, Any]:
    """Coerce a single record (dict, dataclass,
    namespace) to a flat row-dict.
    """
    raw = to_dict(record)
    return {k: coerce_value(v) for k, v in raw.items()}


__all__ = ["TableFormatter"]