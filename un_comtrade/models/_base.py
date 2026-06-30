"""Base class for immutable metadata models.

All metadata models are `@dataclass(frozen=True)` and
inherit from `BaseModel`. The base class exposes
`to_dict()` for serialization and provides a stable
foundation for future shared behaviour (e.g. JSON
encoding of `datetime.date` fields).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any


class BaseModel:
    """Immutable metadata model base class.

    Subclasses are frozen dataclasses. `to_dict()` returns
    a plain `dict` representation derived from
    `dataclasses.asdict`. Date fields appear as
    `datetime.date` objects; consumers that need a JSON
    representation must encode them with their preferred
    strategy (e.g. `date.isoformat()`).
    """

    def to_dict(self) -> dict[str, Any]:
        """Return a dict representation of this model."""
        return asdict(self)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        fields = ", ".join(
            f"{name}={getattr(self, name)!r}"
            for name in self.__dataclass_fields__  # type: ignore[attr-defined]
        )
        return f"{type(self).__name__}({fields})"


__all__ = ["BaseModel"]