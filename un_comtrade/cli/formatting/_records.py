"""Record-row normalisation helpers.

The formatters in this package accept arbitrary
Python values (dicts, dataclasses, lists). The
shared helpers here coerce them into the
canonical row-dict form expected by the
table / CSV formatters and the JSON
serialisation path.

The helpers are PRIVATE — `un_comtrade.cli`
consumers should not import them directly. Use
:class:`OutputFormatter` instead.
"""

from __future__ import annotations

from dataclasses import asdict, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, Mapping


_PRIMITIVE_TYPES = (str, int, float, bool, type(None))


def is_primitive(value: Any) -> bool:
    """``True`` when ``value`` is JSON-serialisable
    without further coercion.
    """
    return isinstance(value, _PRIMITIVE_TYPES)


def coerce_value(value: Any) -> Any:
    """Coerce a single value into a JSON-friendly
    form. Decimals become strings (precision-
    preserving); datetimes become ISO-8601
    strings; ``None`` passes through; everything
    else is left alone (the JSON encoder will
    fall back to ``repr``).
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    return value


def to_dict(record: Any) -> dict[str, Any]:
    """Convert a record (dataclass, dict, or
    namespace) into a flat ``dict``.

    - ``dataclass`` → :func:`asdict` (recursive).
    - ``Mapping`` → ``dict(mapping)``.
    - Anything else → ``vars(record)`` if it has a
      ``__dict__``, else ``{"value": str(record)}``.
    """
    if record is None:
        return {}
    if is_dataclass(record) and not isinstance(record, type):
        return asdict(record)
    if isinstance(record, Mapping):
        return {str(k): v for k, v in record.items()}
    if hasattr(record, "__dict__"):
        return {
            k: v for k, v in vars(record).items()
            if not k.startswith("_")
        }
    return {"value": str(record)}


def to_rows(records: Iterable[Any]) -> list[dict[str, Any]]:
    """Normalise a list of records into a list of
    row-dicts. Each row is passed through
    :func:`to_dict` and :func:`coerce_value`.
    """
    return [to_row(r) for r in records]


def to_row(record: Any) -> dict[str, Any]:
    """Single-record variant of :func:`to_rows`.
    """
    raw = to_dict(record)
    return {k: coerce_value(v) for k, v in raw.items()}


def collect_field_names(rows: list[dict[str, Any]]) -> list[str]:
    """Return the union of keys across ``rows`` in
    stable insertion order.

    For dataclass-based records every row
    typically has the same keys; for heterogeneous
    inputs (e.g. dicts from upstream) this gathers
    the union.
    """
    seen: set[str] = set()
    ordered: list[str] = []
    for row in rows:
        for k in row.keys():
            if k not in seen:
                seen.add(k)
                ordered.append(k)
    return ordered


def field_names_from_dataclass(
    sample: Any,
) -> list[str] | None:
    """When all rows are dataclasses of the same
    class, prefer the dataclass's declared field
    order over dict-iteration order. Returns
    ``None`` if ``sample`` is not a dataclass.
    """
    if is_dataclass(sample) and not isinstance(sample, type):
        return [f.name for f in fields(sample)]
    return None


__all__ = [
    "collect_field_names",
    "coerce_value",
    "field_names_from_dataclass",
    "is_primitive",
    "to_dict",
    "to_row",
    "to_rows",
]