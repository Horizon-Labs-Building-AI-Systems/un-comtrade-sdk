"""GitHub-Flavored-Markdown table formatter.

Renders a list of records as a GFM-compatible
table::

    | name  | code |
    | ----- | ---- |
    | India | 699  |
    | China | 156  |

The first row is the header (``column_names``);
the second is the alignment marker row
(``---``); every subsequent row is one record's
values.

GFM tables do not support nested pipes; pipes
inside cell values are escaped with ``\\|``.

This is the natural format for posting analytics
results to GitHub issues / READMEs / Slack.
"""

from __future__ import annotations

from typing import Any

from un_comtrade.cli.formatting._records import (
    collect_field_names,
    coerce_value,
    field_names_from_dataclass,
    to_dict,
)


class MarkdownFormatter:
    """GitHub-Flavored-Markdown table formatter.

    Output is suitable for direct inclusion in
    Markdown documents (``README.md``, GitHub
    issues, etc.).
    """

    name: str = "markdown"

    def render(self, value: Any) -> str:
        """Render ``value`` as a Markdown table.

        ``value`` may be:

        - a list of dicts / dataclasses
          (preferred — one row each);
        - a single dict / dataclass (single row);
        - a primitive (single cell, no header).
        """
        rows = self._coerce(value)
        if not rows:
            return ""
        sample = rows[0]
        column_names = field_names_from_dataclass(sample)
        if column_names is None:
            column_names = list(rows[0].keys())
        if any(set(r.keys()) != set(column_names) for r in rows[1:]):
            column_names = collect_field_names(rows)

        # Header row.
        header_cells = [str(col) for col in column_names]
        # Alignment marker row.
        marker_cells = ["---"] * len(column_names)

        out_lines = [
            self._row(header_cells),
            self._row(marker_cells),
        ]
        for row in rows:
            cells = [
                self._cell(row.get(col)) for col in column_names
            ]
            out_lines.append(self._row(cells))
        return "\n".join(out_lines) + "\n"

    @staticmethod
    def _row(cells: list[str]) -> str:
        """Render a Markdown table row.

        Pipes inside cell values are escaped so
        they don't break the row layout.
        """
        escaped = [c.replace("|", "\\|") for c in cells]
        return "| " + " | ".join(escaped) + " |"

    @staticmethod
    def _cell(value: Any) -> str:
        if value is None:
            return ""
        return str(coerce_value(value)).replace("\n", " ")

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


__all__ = ["MarkdownFormatter"]