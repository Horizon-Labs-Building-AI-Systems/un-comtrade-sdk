"""Metadata models for the UN Comtrade Python SDK.

This package provides frozen, validated dataclasses for
the canonical metadata entities described in
`006_DATA_MODEL.md`:

- `Country` / `Partner` (E01)
- `Classification` (E02)
- `HSCode` (E04, HS-specialized commodity code)
- `TradeFlow` (E05)
- `TransportMode` (E06)
- `Frequency` (E09)

And the canonical trade-record models from §3.12
(P2-003):

- `Reporter` (record-embedded)
- `Partner` (record-embedded; aliased to `TradePartner`
  at the package level to avoid clashing with the
  catalog `Partner`)
- `Commodity` (record-embedded)
- `TradeFlow` (record-embedded; aliased to
  `RecordTradeFlow` at the package level)
- `TradeValue`
- `Quantity`
- `TradeRecord`

Per the task scope (P1-011 + P2-003) this module
contains **models only**: no transport, no metadata
download, no API integration. Validation is enforced
in `__post_init__` per ADR-0013 and the documented
rules in the data-model specification.
"""

from __future__ import annotations

from .country import Country, Partner
from .classification import Classification
from .data_item import DataItem
from .frequency import Frequency
from .hs_code import HSCode
from .quantity_unit import QuantityUnit
from .reference_entry import ReferenceEntry
from .response import TradeResponse
from .trade import (
    Commodity,
    Partner as TradePartner,
    Quantity,
    Reporter,
    TradeFlow as RecordTradeFlow,
    TradeRecord,
    TradeValue,
)
from .trade_flow import TradeFlow
from .transport_mode import TransportMode


__all__ = [
    "Classification",
    "Commodity",
    "Country",
    "DataItem",
    "Frequency",
    "HSCode",
    "Partner",
    "Quantity",
    "QuantityUnit",
    "RecordTradeFlow",
    "ReferenceEntry",
    "Reporter",
    "TradeFlow",
    "TradePartner",
    "TradeRecord",
    "TradeResponse",
    "TradeValue",
    "TransportMode",
]