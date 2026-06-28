"""HS Code metadata model (E04 specialized to HS).

A `HSCode` represents a product code in the Harmonized
System (HS) classification. Per `006_DATA_MODEL.md` §3.4,
HS commodity codes are 2, 4, or 6 digits long, or the
wildcard `TOTAL` (which selects every commodity).

Per the P3-006 task scope, the model also accepts the
deeper line-level codes (8 or 10 digits) that the
upstream tariffline endpoint returns
(`/data/v1/getTariffline/...` per
`005_API_ENDPOINT_CATALOG.md` §F1). The HS
classification only defines 6-digit codes; longer
codes are national tariff-line extensions built on
top of the HS subheading.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from ._base import BaseModel


#: HS commodity code pattern: 2, 4, 6, 8, or 10 digits.
#: 2/4/6 are the standard HS levels; 8/10 are the
#: tariffline (line-level) extensions returned by the
#: upstream tariffline endpoint.
_HS_CODE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^\d{2}$|^\d{4}$|^\d{6}$|^\d{8}$|^\d{10}$"
)
#: Wildcard that selects every commodity in HS.
_TOTAL: Final[str] = "TOTAL"


@dataclass(frozen=True)
class HSCode(BaseModel):
    """E04 CommodityCode specialized to the HS classification.

    Primary key (composite): `(commodity_code,
    classification_code, edition)`. Validation per
    `006_DATA_MODEL.md` §3.4.

    The model is specialized to HS in this task scope;
    future editions of the model MAY generalize to
    other classifications (SITC, BEC, EBOPS).
    """

    commodity_code: str
    classification_code: str
    edition: str
    display_name: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.commodity_code, str):
            raise TypeError(
                f"commodity_code must be a str; got "
                f"{type(self.commodity_code).__name__}"
            )
        if not self.commodity_code.strip():
            raise ValueError("commodity_code must be a non-empty string")
        if (
            self.commodity_code != _TOTAL
            and not _HS_CODE_PATTERN.fullmatch(self.commodity_code)
        ):
            raise ValueError(
                f"HS commodity_code must be {repr(_TOTAL)} or "
                f"2/4/6/8/10 digits; got {self.commodity_code!r}"
            )
        if self.classification_code != "HS":
            raise ValueError(
                f"HSCode is specialized to HS; "
                f"got classification_code={self.classification_code!r}"
            )
        if not isinstance(self.edition, str) or not self.edition.strip():
            raise ValueError("edition must be a non-empty string")
        if self.display_name is not None and (
            not isinstance(self.display_name, str) or not self.display_name.strip()
        ):
            raise ValueError("display_name, if provided, must be a non-empty string")


__all__ = ["HSCode"]