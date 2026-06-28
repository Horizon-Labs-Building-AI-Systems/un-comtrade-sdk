"""Canonical response models.

Per `006_DATA_MODEL.md` §3.22 and §4.22, an
`E22 Response` is the canonical envelope returned by
every successful SDK call. It wraps the records (as
canonical `TradeRecord` instances), the elapsed time,
the count, and the error message.

This module holds the response model only; the
transport-layer envelope validation and the
upstream-record-to-`TradeRecord` conversion live in
`un_comtrade.trade` and `un_comtrade.parser`
respectively.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ._base import BaseModel


if TYPE_CHECKING:
    from .trade import TradeRecord


__all__ = ["TradeResponse"]


@dataclass(frozen=True)
class TradeResponse(BaseModel):
    """E22 Response — canonical success envelope.

    Wraps the upstream's documented response shape:

    - `elapsed_seconds` — non-negative number.
    - `count` — non-negative integer; per the data
      model contract this SHALL equal the number of
      records upstream reported (`len(records)`).
    - `records` — list of canonical `TradeRecord`
      instances. Empty list when no records match.
      Distinct from the upstream's `data` field; the
      canonical name is `records` per PCR §10
      ("canonical renames `data` to `records`").
    - `error` — non-empty string on failure, empty
      string on success.
    - `upstream_url` — the URL the request was sent
      to; useful for diagnostics and for consumers
      that want to replay the call.
    - `request` — opaque request metadata (E21
      payload) when the caller supplied one.
    - `skipped` — number of records the parser dropped
      (validation failures or duplicates). Defaults
      to `0` when no parser ran.
    """

    elapsed_seconds: float
    count: int
    records: list["TradeRecord"] = field(default_factory=list)
    error: str = ""
    upstream_url: str = ""
    request: dict[str, Any] | None = None
    skipped: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.elapsed_seconds, bool) or not isinstance(
            self.elapsed_seconds, (int, float)
        ):
            raise TypeError(
                f"elapsed_seconds must be a number; got "
                f"{type(self.elapsed_seconds).__name__}"
            )
        if self.elapsed_seconds < 0:
            raise ValueError(
                f"elapsed_seconds must be non-negative; got "
                f"{self.elapsed_seconds}"
            )
        if isinstance(self.count, bool) or not isinstance(self.count, int):
            raise TypeError(
                f"count must be an int; got {type(self.count).__name__}"
            )
        if self.count < 0:
            raise ValueError(
                f"count must be non-negative; got {self.count}"
            )
        if not isinstance(self.records, list):
            raise TypeError(
                f"records must be a list; got "
                f"{type(self.records).__name__}"
            )
        if not isinstance(self.error, str):
            raise TypeError(
                f"error must be a str; got {type(self.error).__name__}"
            )
        if not isinstance(self.upstream_url, str):
            raise TypeError(
                f"upstream_url must be a str; got "
                f"{type(self.upstream_url).__name__}"
            )
        if self.request is not None and not isinstance(self.request, dict):
            raise TypeError(
                f"request must be a dict or None; got "
                f"{type(self.request).__name__}"
            )
        if isinstance(self.skipped, bool) or not isinstance(
            self.skipped, int
        ):
            raise TypeError(
                f"skipped must be an int; got {type(self.skipped).__name__}"
            )
        if self.skipped < 0:
            raise ValueError(
                f"skipped must be non-negative; got {self.skipped}"
            )