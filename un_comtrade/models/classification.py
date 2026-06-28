"""Classification metadata model (E02).

A `Classification` represents a product classification
system (HS, SITC, BEC, EBOPS). The classification has
one or more editions (E03) and is referenced by every
trade record (E12-E17).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ._base import BaseModel


#: Documented classification codes from the upstream
#: reference catalogue. Per `006_DATA_MODEL.md` §3.2,
#: the codes are short strings from the catalogue.
_VALID_CLASSIFICATIONS: Final[frozenset[str]] = frozenset(
    {"HS", "SITC", "BEC", "EBOPS"}
)


@dataclass(frozen=True)
class Classification(BaseModel):
    """E02 Classification — product classification system.

    Primary key: `classification_code` (string).
    Validation per `006_DATA_MODEL.md` §3.2.
    """

    classification_code: str
    display_name: str

    def __post_init__(self) -> None:
        if not isinstance(self.classification_code, str):
            raise TypeError(
                f"classification_code must be a str; got "
                f"{type(self.classification_code).__name__}"
            )
        if not self.classification_code.strip():
            raise ValueError("classification_code must be a non-empty string")
        if self.classification_code not in _VALID_CLASSIFICATIONS:
            raise ValueError(
                f"classification_code must be one of "
                f"{sorted(_VALID_CLASSIFICATIONS)}; got "
                f"{self.classification_code!r}"
            )
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            raise ValueError("display_name must be a non-empty string")


__all__ = ["Classification"]