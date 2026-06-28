"""Quantity unit metadata model (E08).

A `QuantityUnit` represents a unit of measurement used
for quantities in trade records. Per
`006_DATA_MODEL.md` §3.8 the documented values include
`-1` (not applicable / total) and `8` (kilograms).
"""

from __future__ import annotations

from dataclasses import dataclass

from ._base import BaseModel


@dataclass(frozen=True)
class QuantityUnit(BaseModel):
    """E08 QuantityUnit — unit of measurement for quantities.

    Primary key: `qty_unit_code` (integer; `-1` represents
    the TOTAL / not-applicable aggregate). Validation per
    `006_DATA_MODEL.md` §3.8.
    """

    qty_unit_code: int
    qty_abbr: str
    qty_description: str

    def __post_init__(self) -> None:
        if isinstance(self.qty_unit_code, bool) or not isinstance(
            self.qty_unit_code, int
        ):
            raise TypeError(
                f"qty_unit_code must be an int; got {type(self.qty_unit_code).__name__}"
            )
        if not isinstance(self.qty_abbr, str) or not self.qty_abbr.strip():
            raise ValueError("qty_abbr must be a non-empty string")
        if not isinstance(self.qty_description, str) or not self.qty_description.strip():
            raise ValueError("qty_description must be a non-empty string")


__all__ = ["QuantityUnit"]