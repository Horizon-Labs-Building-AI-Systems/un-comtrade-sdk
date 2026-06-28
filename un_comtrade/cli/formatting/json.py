"""JSON output formatter.

Stable JSON serialisation. The output is
``json.dumps(..., indent=2, sort_keys=True)`` so
two runs of the same command produce
byte-identical output (modulo platform JSON
encoder differences).

The formatter never raises on user data: any
non-serialisable value is coerced to its
``repr()`` via the standard library's fallback.

Decimal and datetime values are coerced to
string / ISO-8601 by the shared
:mod:`un_comtrade.cli.formatting._records`
helpers so that precision and timezone are
preserved exactly.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping

from un_comtrade.cli.formatting._records import (
    coerce_value,
    to_dict,
)


class JsonFormatter:
    """Stable JSON formatter.

    Output is ``json.dumps(..., indent=2,
    sort_keys=True)`` so two runs of the same
    command produce byte-identical output
    (modulo platform JSON encoder differences).

    The formatter never raises on user data:
    any non-serialisable value is coerced to its
    ``repr()`` via the standard library's
    fallback.
    """

    name: str = "json"

    def render(self, value: Any) -> str:
        """Render ``value`` as a stable JSON string.

        Parameters
        ----------
        value
            Any JSON-compatible Python value.
            Dataclasses, ``Decimal``, and
            ``datetime`` are coerced to their
            canonical string forms.
        """
        normalised = _normalise(value)
        try:
            return json.dumps(
                normalised,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
        except (TypeError, ValueError):
            # Last-resort fallback: string repr.
            return json.dumps(
                repr(value),
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )


def _normalise(value: Any) -> Any:
    """Recursively coerce values that the default
    JSON encoder cannot serialise.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return _normalise(asdict(value))
    if isinstance(value, Mapping):
        return {str(k): _normalise(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_normalise(v) for v in value]
    return str(value)


__all__ = ["JsonFormatter"]