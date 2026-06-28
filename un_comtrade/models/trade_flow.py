"""TradeFlow metadata model (E05).

A `TradeFlow` represents the direction of a trade.
Per `006_DATA_MODEL.md` §3.5 the documented flow codes
are:

- `M`  — Import
- `X`  — Export
- `RX` — Re-export
- `RM` — Re-import
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ._base import BaseModel


#: Documented flow codes from the data-model spec.
_VALID_FLOW_CODES: Final[frozenset[str]] = frozenset({"M", "X", "RX", "RM"})


@dataclass(frozen=True)
class TradeFlow(BaseModel):
    """E05 TradeFlow — direction of a trade.

    Primary key: `flow_code` (string).
    Validation per `006_DATA_MODEL.md` §3.5.
    """

    flow_code: str
    display_name: str

    def __post_init__(self) -> None:
        if not isinstance(self.flow_code, str):
            raise TypeError(
                f"flow_code must be a str; got {type(self.flow_code).__name__}"
            )
        if self.flow_code not in _VALID_FLOW_CODES:
            raise ValueError(
                f"flow_code must be one of {sorted(_VALID_FLOW_CODES)}; "
                f"got {self.flow_code!r}"
            )
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            raise ValueError("display_name must be a non-empty string")


__all__ = ["TradeFlow"]