"""Canonical trade-record models.

Per `006_DATA_MODEL.md` §3.12 and §4.12, a single trade
observation (E12 `TradeRecord`) carries ~30 fields across
identifiers, period, subjects (reporter / partner /
commodity / flow), procedural metadata, monetary values,
quantities, weights, and estimation flags.

The models in this module are the **record-embedded**
variants that live inside a `TradeRecord`. They are
distinct from the catalog entities in `country.py`
(metadata `Country` / `Partner` with full ISO codes,
effective dates, etc.) and `trade_flow.py` (metadata
`TradeFlow`). The record-embedded variants have a
smaller shape because they only carry the codes and
display names actually present in a trade record.

Design notes (per task scope P2-003 — models only,
no parsing, no downloading):

- Every model is a `@dataclass(frozen=True)` subclass
  of `BaseModel` (ADR-0030).
- Monetary and quantity values use `Decimal` for
  exact arithmetic (ADR-0027 / PCR Q52).
- Validation is enforced in `__post_init__` per the
  documented rules in `006_DATA_MODEL.md` §4.12.
- Sentinel values are preserved: `partner_code=0`,
  `partner_iso3="W00"`, `partner_name="World"` for the
  World aggregate (Q13).
- `null` upstream fields map to `None` on the SDK
  model (PCR Q54).
- `to_dict()` produces a plain dict; `Decimal` values
  survive as `Decimal` instances. Callers that need
  JSON must encode via their preferred strategy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Final

from ._base import BaseModel


# ---------------------------------------------------------------------------
# Constants (record-embedded)
# ---------------------------------------------------------------------------


#: Documented flow codes (mirrors `models/trade_flow.py`).
_VALID_FLOW_CODES: Final[frozenset[str]] = frozenset({"M", "X", "RX", "RM"})

#: Documented type codes (commodities / services).
_VALID_TYPE_CODES: Final[frozenset[str]] = frozenset({"C", "S"})

#: Documented frequency codes.
_VALID_FREQUENCY_CODES: Final[frozenset[str]] = frozenset({"A", "M"})

#: HS commodity code pattern: 2, 4, 6, 8, or 10 digits.
#: 2/4/6 are the standard HS levels (chapter / heading /
#: subheading). 8/10 are the line-level extensions
#: returned by the upstream tariffline endpoint
#: (`/data/v1/getTariffline/...` per
#: `005_API_ENDPOINT_CATALOG.md` §F1). The HS
#: classification only defines 6-digit codes; longer
#: codes are national tariff-line extensions built on
#: top of the HS subheading.
_HS_CODE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^\d{2}$|^\d{4}$|^\d{6}$|^\d{8}$|^\d{10}$"
)

#: Wildcard that selects every commodity.
_TOTAL_COMMODITY: Final[str] = "TOTAL"

#: Period token pattern: YYYY or YYYYMM.
_PERIOD_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\d{4}(\d{2})?$")

#: ref_month accepts 1..12 (monthly) or 52 (annual sentinel).
_VALID_REF_MONTHS: Final[frozenset[int]] = frozenset({52, *range(1, 13)})

#: Sentinel partner_code for the World aggregate.
_WORLD_PARTNER_CODE: Final[int] = 0

#: Sentinel ISO code for the World aggregate.
_WORLD_ISO3: Final[str] = "W00"

#: Sentinel display name for the World aggregate.
_WORLD_NAME: Final[str] = "World"

#: Acceptable ref_year range (1900..2100).
_MIN_REF_YEAR: Final[int] = 1900
_MAX_REF_YEAR: Final[int] = 2100


# ---------------------------------------------------------------------------
# Shared validation helpers
# ---------------------------------------------------------------------------


def _require_non_negative_int(
    value: int,
    *,
    field: str,
    allow_zero: bool = True,
) -> None:
    """Validate that `value` is a non-negative int (and not a bool)."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(
            f"{field} must be an int; got {type(value).__name__}"
        )
    if value < 0 or (not allow_zero and value == 0):
        raise ValueError(
            f"{field} must be a positive int; got {value}"
        )


def _require_non_negative_decimal(
    value: Any,
    *,
    field: str,
) -> None:
    """Validate that `value` is a Decimal and ≥ 0."""
    if value is None:
        return
    if not isinstance(value, Decimal):
        raise TypeError(
            f"{field} must be a Decimal; got {type(value).__name__}"
        )
    if value.is_nan():
        raise ValueError(f"{field} must not be NaN")
    if value.is_signed() and value != 0:
        raise ValueError(f"{field} must be non-negative; got {value}")


def _require_optional_str(
    value: Any,
    *,
    field: str,
    allow_empty: bool = False,
) -> None:
    """Validate that `value` is a non-empty str (or None)."""
    if value is None:
        return
    if not isinstance(value, str):
        raise TypeError(
            f"{field} must be a str; got {type(value).__name__}"
        )
    if not allow_empty and not value.strip():
        raise ValueError(f"{field}, if provided, must be non-empty")


def _require_iso3_or_world(
    value: Any,
    *,
    field: str,
) -> None:
    """Validate that `value` is None, "W00" (World sentinel),
    or a 3-letter uppercase ISO 3166-1 alpha-3 code.
    """
    if value is None:
        return
    if not isinstance(value, str):
        raise TypeError(
            f"{field} must be a str; got {type(value).__name__}"
        )
    if value == _WORLD_ISO3:
        return
    if not re.fullmatch(r"^[A-Z]{3}$", value):
        raise ValueError(
            f"{field} must be a 3-letter uppercase ISO 3166-1 code "
            f"or {repr(_WORLD_ISO3)} for World; got {value!r}"
        )


# ---------------------------------------------------------------------------
# Record-embedded dimension models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Reporter(BaseModel):
    """Reporter as it appears on a trade record.

    Smaller than the catalog `Country` model: only the
    code, ISO alpha-3 code (if provided), and display
    name. No effective dates, no entry metadata.

    `reporter_code` is the upstream's `reporterCode`
    integer (e.g. `699` for India).
    """

    reporter_code: int
    iso3: str | None
    name: str | None

    def __post_init__(self) -> None:
        _require_non_negative_int(
            self.reporter_code, field="reporter_code"
        )
        _require_iso3_or_world(self.iso3, field="iso3")
        _require_optional_str(self.name, field="name")


@dataclass(frozen=True)
class Partner(BaseModel):
    """Partner as it appears on a trade record.

    `partner_code=0` with `iso3="W00"` and `name="World"`
    is the documented sentinel for the World aggregate
    (PCR Q13, `006_DATA_MODEL.md` §4.12). The model
    accepts any non-negative int but does NOT enforce
    that the World sentinel is paired with the matching
    iso3/name — that is the upstream's responsibility.
    """

    partner_code: int
    iso3: str | None
    name: str | None

    def __post_init__(self) -> None:
        _require_non_negative_int(
            self.partner_code, field="partner_code"
        )
        _require_iso3_or_world(self.iso3, field="iso3")
        _require_optional_str(self.name, field="name")

    @property
    def is_world(self) -> bool:
        """Return True if this partner is the World sentinel."""
        return self.partner_code == _WORLD_PARTNER_CODE


@dataclass(frozen=True)
class Commodity(BaseModel):
    """Commodity as it appears on a trade record.

    `commodity_code` is the HS code (2/4/6 digits) or a
    tariffline extension (8/10 digits), or `"TOTAL"`
    (the wildcard that selects every commodity). The
    display name is optional because the upstream
    returns `null` when `includeDesc=false`.
    """

    commodity_code: str
    name: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.commodity_code, str):
            raise TypeError(
                f"commodity_code must be a str; got "
                f"{type(self.commodity_code).__name__}"
            )
        if not self.commodity_code.strip():
            raise ValueError("commodity_code must be non-empty")
        if (
            self.commodity_code != _TOTAL_COMMODITY
            and not _HS_CODE_PATTERN.fullmatch(self.commodity_code)
        ):
            raise ValueError(
                f"commodity_code must be {repr(_TOTAL_COMMODITY)} "
                f"or 2/4/6/8/10 digits; got {self.commodity_code!r}"
            )
        _require_optional_str(self.name, field="name")


@dataclass(frozen=True)
class TradeFlow(BaseModel):
    """Trade flow as it appears on a trade record.

    Distinct from the catalog `TradeFlow` model in
    `models/trade_flow.py`: the record-embedded variant
    carries only the code and display name, no taxonomy
    metadata.

    `flow_code` must be one of `M` / `X` / `RX` / `RM`.
    """

    flow_code: str
    flow_name: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.flow_code, str):
            raise TypeError(
                f"flow_code must be a str; got "
                f"{type(self.flow_code).__name__}"
            )
        if self.flow_code not in _VALID_FLOW_CODES:
            raise ValueError(
                f"flow_code must be one of "
                f"{sorted(_VALID_FLOW_CODES)}; got {self.flow_code!r}"
            )
        _require_optional_str(self.flow_name, field="flow_name")


# ---------------------------------------------------------------------------
# Value-bearing sub-models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TradeValue(BaseModel):
    """Monetary value triplet for a trade record.

    All values are USD (per `006_DATA_MODEL.md` §4.12)
    and use `Decimal` for exact arithmetic. The
    upstream may return `null` for `cif_value` and
    `fob_value` (when not applicable to the flow
    direction); `primary_value` is required.

    Per `006_DATA_MODEL.md` §3.12, all values SHALL be
    non-negative when present.
    """

    primary_value: Decimal
    fob_value: Decimal | None
    cif_value: Decimal | None

    def __post_init__(self) -> None:
        if not isinstance(self.primary_value, Decimal):
            raise TypeError(
                f"primary_value must be a Decimal; got "
                f"{type(self.primary_value).__name__}"
            )
        if self.primary_value.is_nan():
            raise ValueError("primary_value must not be NaN")
        if self.primary_value.is_signed() and self.primary_value != 0:
            raise ValueError(
                f"primary_value must be non-negative; got "
                f"{self.primary_value}"
            )
        _require_non_negative_decimal(
            self.fob_value, field="fob_value"
        )
        _require_non_negative_decimal(
            self.cif_value, field="cif_value"
        )


@dataclass(frozen=True)
class Quantity(BaseModel):
    """Quantity section of a trade record.

    Carries the primary quantity, the alternate quantity
    (when reported by the upstream), and their unit codes
    / abbreviations. All numeric values are `Decimal`.
    The unit code `-1` is the documented "no unit"
    sentinel and is accepted as-is (PCR Q28).

    Estimation flags default to `False` because the
    upstream omits the field when the value is exact.
    """

    qty: Decimal | None
    qty_unit_code: int
    qty_unit_abbr: str | None
    is_estimated: bool
    alt_qty: Decimal | None
    alt_qty_unit_code: int | None
    alt_qty_unit_abbr: str | None
    is_alt_qty_estimated: bool

    def __post_init__(self) -> None:
        if isinstance(self.qty_unit_code, bool) or not isinstance(
            self.qty_unit_code, int
        ):
            raise TypeError(
                f"qty_unit_code must be an int; got "
                f"{type(self.qty_unit_code).__name__}"
            )
        _require_non_negative_decimal(self.qty, field="qty")
        _require_optional_str(self.qty_unit_abbr, field="qty_unit_abbr")
        if not isinstance(self.is_estimated, bool):
            raise TypeError(
                f"is_estimated must be a bool; got "
                f"{type(self.is_estimated).__name__}"
            )
        _require_non_negative_decimal(self.alt_qty, field="alt_qty")
        if self.alt_qty_unit_code is not None:
            if isinstance(
                self.alt_qty_unit_code, bool
            ) or not isinstance(self.alt_qty_unit_code, int):
                raise TypeError(
                    f"alt_qty_unit_code must be an int; got "
                    f"{type(self.alt_qty_unit_code).__name__}"
                )
        _require_optional_str(
            self.alt_qty_unit_abbr, field="alt_qty_unit_abbr"
        )
        if not isinstance(self.is_alt_qty_estimated, bool):
            raise TypeError(
                f"is_alt_qty_estimated must be a bool; got "
                f"{type(self.is_alt_qty_estimated).__name__}"
            )


# ---------------------------------------------------------------------------
# TradeRecord
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TradeRecord(BaseModel):
    """E12 TradeRecord — a single trade observation.

    Composes the record-embedded dimension models
    (Reporter / Partner / Commodity / TradeFlow) and the
    value-bearing sub-models (TradeValue / Quantity) with
    the upstream's metadata fields. Frozen and validated.

    Validation rules enforced (per `006_DATA_MODEL.md` §4.12):

    - `type_code` ∈ `{"C", "S"}`.
    - `frequency_code` ∈ `{"A", "M"}`.
    - `ref_year` in 1900..2100.
    - `ref_month` in {1..12, 52} (52 = annual).
    - `period` matches `YYYY` or `YYYYMM`.
    - `classification_code`, `edition`, `period`,
      `customs_code`, `mos_code` are non-empty strings.
    - `mot_code` is a non-negative int.
    - `legacy_estimation_flag` is a non-negative int.
    - `net_weight_kg`, `gross_weight_kg` are non-negative
      Decimals (or None).
    """

    # Identifier / metadata
    type_code: str
    frequency_code: str
    classification_code: str
    classification_search_code: str | None
    edition: str
    is_original_classification: bool | None
    # Period
    ref_period_id: int | None
    ref_year: int
    ref_month: int
    period: str
    # Subjects (composed)
    reporter: Reporter
    partner: Partner
    partner2: Partner | None
    flow: TradeFlow
    commodity: Commodity
    # Procedural
    customs_code: str
    customs_name: str | None
    mos_code: str
    mot_code: int
    mot_name: str | None
    # Values / quantities
    quantity: Quantity
    net_weight_kg: Decimal | None
    is_net_weight_estimated: bool
    gross_weight_kg: Decimal | None
    is_gross_weight_estimated: bool
    trade_value: TradeValue
    # Flags
    legacy_estimation_flag: int
    is_reported: bool
    is_aggregate: bool
    # Provenance (derived / upstream metadata; opaque)
    provenance: dict[str, Any] | None

    def __post_init__(self) -> None:
        # type_code
        if not isinstance(self.type_code, str):
            raise TypeError(
                f"type_code must be a str; got "
                f"{type(self.type_code).__name__}"
            )
        if self.type_code not in _VALID_TYPE_CODES:
            raise ValueError(
                f"type_code must be one of "
                f"{sorted(_VALID_TYPE_CODES)}; got {self.type_code!r}"
            )
        # frequency_code
        if not isinstance(self.frequency_code, str):
            raise TypeError(
                f"frequency_code must be a str; got "
                f"{type(self.frequency_code).__name__}"
            )
        if self.frequency_code not in _VALID_FREQUENCY_CODES:
            raise ValueError(
                f"frequency_code must be one of "
                f"{sorted(_VALID_FREQUENCY_CODES)}; got "
                f"{self.frequency_code!r}"
            )
        # classification_code
        _require_optional_str(
            self.classification_code,
            field="classification_code",
            allow_empty=False,
        )
        if not self.classification_code or not isinstance(
            self.classification_code, str
        ):
            raise ValueError("classification_code must be non-empty")
        _require_optional_str(
            self.classification_search_code,
            field="classification_search_code",
        )
        _require_optional_str(self.edition, field="edition")
        if self.is_original_classification is not None and not isinstance(
            self.is_original_classification, bool
        ):
            raise TypeError(
                f"is_original_classification must be a bool or None; got "
                f"{type(self.is_original_classification).__name__}"
            )
        # ref_period_id
        if self.ref_period_id is not None:
            if isinstance(self.ref_period_id, bool) or not isinstance(
                self.ref_period_id, int
            ):
                raise TypeError(
                    f"ref_period_id must be an int or None; got "
                    f"{type(self.ref_period_id).__name__}"
                )
            if self.ref_period_id < 0:
                raise ValueError(
                    f"ref_period_id must be non-negative; got "
                    f"{self.ref_period_id}"
                )
        # ref_year
        if isinstance(self.ref_year, bool) or not isinstance(
            self.ref_year, int
        ):
            raise TypeError(
                f"ref_year must be an int; got "
                f"{type(self.ref_year).__name__}"
            )
        if not _MIN_REF_YEAR <= self.ref_year <= _MAX_REF_YEAR:
            raise ValueError(
                f"ref_year must be in "
                f"{_MIN_REF_YEAR}..{_MAX_REF_YEAR}; got {self.ref_year}"
            )
        # ref_month
        if isinstance(self.ref_month, bool) or not isinstance(
            self.ref_month, int
        ):
            raise TypeError(
                f"ref_month must be an int; got "
                f"{type(self.ref_month).__name__}"
            )
        if self.ref_month not in _VALID_REF_MONTHS:
            raise ValueError(
                f"ref_month must be 1..12 or 52 (annual sentinel); "
                f"got {self.ref_month}"
            )
        # period
        if not isinstance(self.period, str):
            raise TypeError(
                f"period must be a str; got "
                f"{type(self.period).__name__}"
            )
        if not _PERIOD_PATTERN.fullmatch(self.period):
            raise ValueError(
                f"period must match YYYY or YYYYMM; got {self.period!r}"
            )
        # customs / mot / mos
        _require_optional_str(
            self.customs_code, field="customs_code", allow_empty=False
        )
        _require_optional_str(self.customs_name, field="customs_name")
        _require_optional_str(
            self.mos_code, field="mos_code", allow_empty=False
        )
        _require_non_negative_int(self.mot_code, field="mot_code")
        _require_optional_str(self.mot_name, field="mot_name")
        # weights
        _require_non_negative_decimal(
            self.net_weight_kg, field="net_weight_kg"
        )
        if not isinstance(self.is_net_weight_estimated, bool):
            raise TypeError(
                f"is_net_weight_estimated must be a bool; got "
                f"{type(self.is_net_weight_estimated).__name__}"
            )
        _require_non_negative_decimal(
            self.gross_weight_kg, field="gross_weight_kg"
        )
        if not isinstance(self.is_gross_weight_estimated, bool):
            raise TypeError(
                f"is_gross_weight_estimated must be a bool; got "
                f"{type(self.is_gross_weight_estimated).__name__}"
            )
        # legacy_estimation_flag
        if isinstance(
            self.legacy_estimation_flag, bool
        ) or not isinstance(self.legacy_estimation_flag, int):
            raise TypeError(
                f"legacy_estimation_flag must be an int; got "
                f"{type(self.legacy_estimation_flag).__name__}"
            )
        if self.legacy_estimation_flag < 0:
            raise ValueError(
                f"legacy_estimation_flag must be non-negative; got "
                f"{self.legacy_estimation_flag}"
            )
        # is_reported / is_aggregate
        if not isinstance(self.is_reported, bool):
            raise TypeError(
                f"is_reported must be a bool; got "
                f"{type(self.is_reported).__name__}"
            )
        if not isinstance(self.is_aggregate, bool):
            raise TypeError(
                f"is_aggregate must be a bool; got "
                f"{type(self.is_aggregate).__name__}"
            )
        # provenance
        if self.provenance is not None and not isinstance(
            self.provenance, dict
        ):
            raise TypeError(
                f"provenance must be a dict or None; got "
                f"{type(self.provenance).__name__}"
            )


__all__ = [
    "Commodity",
    "Partner",
    "Quantity",
    "Reporter",
    "TradeFlow",
    "TradeRecord",
    "TradeValue",
]