"""Country and Partner metadata models.

Per the data-model specification (E01), `Country` is the
canonical entity for any political entity that appears as
a reporter or a partner in a trade record. `Partner` is a
distinct subtype that represents the same shape but is
used specifically in the partner role of a trade record.
The data is identical; the role is recorded on the
trade record, not on the entity itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Final

from ._base import BaseModel


_ISO_ALPHA2: Final[re.Pattern[str]] = re.compile(r"^[A-Z]{2}$")
_ISO_ALPHA3: Final[re.Pattern[str]] = re.compile(r"^[A-Z]{3}$")


def _validate_country_fields(
    country_code: int,
    iso_alpha2: str | None,
    iso_alpha3: str | None,
    display_name: str,
    entry_effective_date: date | None,
    entry_expired_date: date | None,
) -> None:
    """Shared validation for Country and Partner."""
    if not isinstance(country_code, int) or isinstance(country_code, bool):
        raise TypeError(
            f"country_code must be an int; got {type(country_code).__name__}"
        )
    if country_code < 0:
        raise ValueError(
            f"country_code must be a non-negative integer; got {country_code}"
        )
    if iso_alpha2 is not None and not _ISO_ALPHA2.match(iso_alpha2):
        raise ValueError(
            f"iso_alpha2 must be a 2-letter uppercase ISO 3166-1 code; "
            f"got {iso_alpha2!r}"
        )
    if iso_alpha3 is not None and not _ISO_ALPHA3.match(iso_alpha3):
        raise ValueError(
            f"iso_alpha3 must be a 3-letter uppercase ISO 3166-1 code; "
            f"got {iso_alpha3!r}"
        )
    if not isinstance(display_name, str) or not display_name.strip():
        raise ValueError("display_name must be a non-empty string")
    if entry_effective_date is not None and entry_expired_date is not None:
        if entry_expired_date <= entry_effective_date:
            raise ValueError(
                f"entry_expired_date ({entry_expired_date}) must be later "
                f"than entry_effective_date ({entry_effective_date})"
            )


@dataclass(frozen=True)
class Country(BaseModel):
    """E01 Country — political entity.

    Primary key: `country_code` (non-negative integer).
    Validation per `006_DATA_MODEL.md` §3.1.
    """

    country_code: int
    iso_alpha2: str | None
    iso_alpha3: str | None
    display_name: str
    entry_effective_date: date | None = None
    entry_expired_date: date | None = None

    def __post_init__(self) -> None:
        _validate_country_fields(
            self.country_code,
            self.iso_alpha2,
            self.iso_alpha3,
            self.display_name,
            self.entry_effective_date,
            self.entry_expired_date,
        )


@dataclass(frozen=True)
class Partner(BaseModel):
    """E01 Country in the partner role.

    Distinct type from `Country` so dataclass equality
    treats them separately — `Country(699, ...) !=
    Partner(699, ...)`. Shape and validation are
    identical.
    """

    country_code: int
    iso_alpha2: str | None
    iso_alpha3: str | None
    display_name: str
    entry_effective_date: date | None = None
    entry_expired_date: date | None = None

    def __post_init__(self) -> None:
        _validate_country_fields(
            self.country_code,
            self.iso_alpha2,
            self.iso_alpha3,
            self.display_name,
            self.entry_effective_date,
            self.entry_expired_date,
        )


__all__ = ["Country", "Partner"]