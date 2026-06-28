"""TransportMode metadata model (E06).

A `TransportMode` represents the mode of transport used
when goods cross the border. Per `006_DATA_MODEL.md`
§3.6 the code `0` represents the TOTAL aggregate.
"""

from __future__ import annotations

from dataclasses import dataclass

from ._base import BaseModel


@dataclass(frozen=True)
class TransportMode(BaseModel):
    """E06 TransportMode — mode of transport.

    Primary key: `mot_code` (integer; `0` represents the
    TOTAL aggregate). Validation per `006_DATA_MODEL.md`
    §3.6.
    """

    mot_code: int
    display_name: str

    def __post_init__(self) -> None:
        # Reject bool (a subclass of int) to keep the type
        # contract clean.
        if isinstance(self.mot_code, bool) or not isinstance(self.mot_code, int):
            raise TypeError(
                f"mot_code must be an int; got {type(self.mot_code).__name__}"
            )
        if self.mot_code < 0:
            raise ValueError(
                f"mot_code must be a non-negative integer; got {self.mot_code}"
            )
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            raise ValueError("display_name must be a non-empty string")


__all__ = ["TransportMode"]