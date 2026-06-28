"""Plain-text formatter.

Renders records as a stable, human-readable
plain-text representation. Useful when JSON is
too noisy and tables are too structured:

- dicts render as ``"key: value"`` per line.
- lists of dicts render as consecutive dict
  blocks separated by blank lines.
- lists of primitives render as one item per
  line.
- primitives are returned via ``str(...)``.

The output is intended for human consumption in
a terminal; ``un-comtrade analytics ... | grep
^name`` workflows remain easy because the
output is line-oriented.
"""

from __future__ import annotations

from typing import Any, Mapping

from un_comtrade.cli.formatting._records import (
    coerce_value,
    to_dict,
)


class TextFormatter:
    """Plain-text formatter.

    Output is line-oriented so the user can pipe
    it through ``grep``, ``awk``, etc.
    """

    name: str = "text"

    def render(self, value: Any) -> str:
        """Render ``value`` as plain text.
        """
        if value is None:
            return ""
        if isinstance(value, Mapping):
            return self._render_mapping(value) + "\n"
        if isinstance(value, (list, tuple, set, frozenset)):
            return self._render_sequence(list(value)) + "\n"
        # Primitives (str / int / float / bool).
        return f"{coerce_value(value)}\n"

    @staticmethod
    def _render_mapping(d: Mapping) -> str:
        """Render a mapping as ``key: value`` per
        line.
        """
        lines = []
        for k, v in d.items():
            lines.append(f"{k}: {_render_value(v)}")
        return "\n".join(lines)

    def _render_sequence(self, items: list[Any]) -> str:
        """Render a list. If every item is a
        mapping, render each as its own dict
        block separated by blank lines.
        """
        if not items:
            return ""
        if all(isinstance(x, Mapping) for x in items):
            blocks = [
                self._render_mapping(x) for x in items
            ]
            return "\n\n".join(blocks)
        return "\n".join(_render_value(x) for x in items)


def _render_value(value: Any) -> str:
    """Format a single value for the plain-text
    formatter.
    """
    if value is None:
        return ""
    coerced = coerce_value(value)
    if isinstance(coerced, Mapping):
        # Avoid flattening nested mappings into
        # huge single lines; render the inner
        # mapping as ``key: value`` per line.
        return "\n    " + "\n    ".join(
            f"{k}: {coerce_value(v)}" for k, v in coerced.items()
        )
    return str(coerced)


__all__ = ["TextFormatter"]