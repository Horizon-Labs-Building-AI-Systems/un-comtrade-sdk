"""Frequency metadata model (E09).

A `Frequency` represents the time granularity of a query
or a record. Per `006_DATA_MODEL.md` §3.9 the documented
frequency codes are:

- `A` — Annual
- `M` — Monthly
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ._base import BaseModel


#: Documented frequency codes from the data-model spec.
_VALID_FREQUENCY_CODES: Final[frozenset[str]] = frozenset({"A", "M"})


@dataclass(frozen=True)
class Frequency(BaseModel):
    """E09 Frequency — time granularity of a query or record.

    Primary key: `frequency_code` (string).
    Validation per `006_DATA_MODEL.md` §3.9.
    """

    frequency_code: str
    display_name: str

    def __post_init__(self) -> None:
        if not isinstance(self.frequency_code, str):
            raise TypeError(
                f"frequency_code must be a str; got "
                f"{type(self.frequency_code).__name__}"
            )
        if self.frequency_code not in _VALID_FREQUENCY_CODES:
            raise ValueError(
                f"frequency_code must be one of {sorted(_VALID_FREQUENCY_CODES)}; "
                f"got {self.frequency_code!r}"
            )
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            raise ValueError("display_name must be a non-empty string")


__all__ = ["Frequency"]