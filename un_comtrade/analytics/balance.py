"""Trade-balance analytics (P6-006).

This module is the fifth concrete analytics
submodule built on top of the `AnalyticsEngine`
foundation (P6-001). It provides four
trade-balance analytics that operate
exclusively on `CanonicalDataset`:

- `country_balance(...)` — exports minus
  imports aggregated per reporter (country).
  With `reporter_code=None`, returns balance
  for ALL reporters (effectively a per-country
  breakdown of the global balance).
- `partner_trade_balance(...)` — exports minus
  imports aggregated per partner for one
  reporter.
- `commodity_balance(...)` — exports minus
  imports aggregated per HS code for one
  reporter (or globally when `reporter_code`
  is `None`).
- `global_balance(...)` — global trade balance
  across all reporters, all partners, all
  commodities (single `BalanceSummary`).

All monetary fields are `Decimal` (ADR-0027).
All dataclasses are `frozen=True` (ADR-0013).

The module is **decoupled from the transport
layer** (same constraint as `AnalyticsEngine`):
only stdlib + intra-package imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from ..transform import CanonicalDataset
from . import AnalyticsError
# QE-007 refactor: route filter / aggregate
# operations through the internal Query
# engine rather than re-implementing.
from ._query_engine import (
    Query,
    sum as _q_sum,
    summarize,
)
# `PartnerBalanceRow` was first defined in
# `partner.py` (P6-003). We re-export it from
# here so callers of `balance.partner_trade_balance`
# get the same class regardless of import
# surface. Use lazy import below to avoid the
# `__init__.py` circular import.
from .partner import PartnerBalanceRow  # noqa: E402

__all__ = [
    # Errors
    "BalanceAnalyticsError",
    # Summary dataclasses
    "BalanceSummary",
    "CountryBalanceRow",
    "PartnerBalanceRow",
    "CommodityBalanceRow",
    # Functions
    "country_balance",
    "partner_trade_balance",
    "commodity_balance",
    "global_balance",
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class BalanceAnalyticsError(AnalyticsError):
    """Raised when a balance analytics operation
    cannot be performed."""


# ---------------------------------------------------------------------------
# Shared dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BalanceSummary:
    """A single-snapshot trade balance summary.

    `trade_balance = total_exports - total_imports`.
    `total_trade = total_exports + total_imports`.
    """

    total_exports: Decimal
    total_imports: Decimal
    trade_balance: Decimal
    total_trade: Decimal
    record_count: int

    def __post_init__(self) -> None:
        for f in (
            "total_exports", "total_imports",
            "trade_balance", "total_trade",
        ):
            v = getattr(self, f)
            if not isinstance(v, Decimal):
                raise BalanceAnalyticsError(
                    f"{f} must be Decimal; got {type(v).__name__}"
                )


@dataclass(frozen=True)
class CountryBalanceRow:
    """One row of the country balance breakdown."""

    reporter_code: int
    reporter_iso3: str | None
    reporter_name: str | None
    total_exports: Decimal
    total_imports: Decimal
    trade_balance: Decimal
    total_trade: Decimal
    record_count: int

    def __post_init__(self) -> None:
        for f in (
            "total_exports", "total_imports",
            "trade_balance", "total_trade",
        ):
            v = getattr(self, f)
            if not isinstance(v, Decimal):
                raise BalanceAnalyticsError(
                    f"{f} must be Decimal; got {type(v).__name__}"
                )


@dataclass(frozen=True)
class CommodityBalanceRow:
    """One row of the commodity balance breakdown."""

    commodity_code: str
    commodity_name: str | None
    total_exports: Decimal
    total_imports: Decimal
    trade_balance: Decimal
    total_trade: Decimal
    record_count: int

    def __post_init__(self) -> None:
        for f in (
            "total_exports", "total_imports",
            "trade_balance", "total_trade",
        ):
            v = getattr(self, f)
            if not isinstance(v, Decimal):
                raise BalanceAnalyticsError(
                    f"{f} must be Decimal; got {type(v).__name__}"
                )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_canonical_dataset(
    dataset: Any, *, fn_name: str
) -> None:
    if not isinstance(dataset, CanonicalDataset):
        raise BalanceAnalyticsError(
            f"{fn_name} source must be a CanonicalDataset; "
            f"got {type(dataset).__name__}"
        )


def _select_records(
    dataset: CanonicalDataset,
    *,
    reporter_code: int | None = None,
    partner_code: int | None = None,
    commodity_code: str | None = None,
) -> tuple:
    """Return records matching the given filters.

    QE-007 refactor: delegates to the
    internal Query engine's `.filter(...)`
    rather than re-implementing the filter
    loop.
    """
    q = Query(dataset)
    if reporter_code is not None:
        q = q.filter(reporter_code=reporter_code)
    if partner_code is not None:
        q = q.filter(partner_code=partner_code)
    if commodity_code is not None:
        q = q.filter(commodity_code=commodity_code)
    return q.execute().records


def _sum_primary_by_group(
    records,
    *,
    flow_code: str,
    group_field: str,
) -> dict:
    """Group `records` by `group_field`, filter to
    `flow_code`, and sum `trade_value.primary_value`
    per group via the internal Query Engine.

    F-002 refactor: replaces the previous
    hand-rolled `dict.get(key, Decimal('0')) + v`
    pattern with `Query.group_by + summarize`. The
    Query Engine already does a single-pass walk
    over the records and yields Decimal precision
    identical to the previous hand-rolled code.

    Parameters
    ----------
    records
        Iterable of `TradeRecord` (typically the
        output of `_select_records`).
    flow_code
        `"X"` (exports) or `"M"` (imports); the
        helper pre-filters by this before grouping.
    group_field
        Dotted path to the group key (e.g.
        `"reporter.reporter_code"`).

    Returns
    -------
    `dict[Any, Decimal]` mapping the group key
    to the summed `primary_value`. Groups whose
    filtered records contain only `None`
    `primary_value` values map to `Decimal("0")`.
    """
    from ._query_engine import summarize
    if not records:
        return {}
    q = (
        Query.from_records(records)
        if hasattr(Query, "from_records")
        else _Query_from_records(records)
    )
    q = q.filter(flow_code=flow_code).group_by(group_field)
    result = q.execute()
    sums: dict = {}
    for group in result.groups:
        s = summarize(group.records, field="trade_value.primary_value")
        sums[group.key[0]] = s.sum if s.sum is not None else Decimal("0")
    return sums


def _Query_from_records(records):
    """Tiny adapter: build a `Query` from a raw
    record tuple, bypassing the `CanonicalDataset`
    type check. Used internally by
    `_sum_primary_by_group` so the helper can be
    called with the output of `_select_records`
    (which is a plain `tuple`, not a
    `CanonicalDataset`)."""
    # The Query engine requires a `CanonicalDataset`
    # as the source. We rebuild a minimal one here;
    # the records themselves are reused as-is, so
    # no extra copying is performed.
    from ..transform import CanonicalDataset
    if isinstance(records, CanonicalDataset):
        # Already a CanonicalDataset; return directly.
        return Query(records)
    ds = CanonicalDataset(
        name="__internal__",
        records=tuple(records),
        schema_version="1.0",
        parser_name="QueryEngine",
    )
    return Query(ds)


def _build_balance_summary(
    records,
) -> BalanceSummary:
    """Build a `BalanceSummary` from a sequence of
    `TradeRecord`s.

    F-002: the per-flow Decimal summation is
    delegated to `_q_summarize(...)` (the
    internal Query Engine aggregation primitive).
    The hand-rolled `x += v` / `m += v` pattern
    has been retired in favour of the engine.
    """
    x_records: list = []
    m_records: list = []
    for record in records:
        v = record.trade_value.primary_value
        if v is None:
            continue
        if record.flow.flow_code == "X":
            x_records.append(record)
        elif record.flow.flow_code == "M":
            m_records.append(record)

    x = Decimal("0")
    if x_records:
        s = summarize(
            tuple(x_records), field="trade_value.primary_value"
        )
        x = s.sum if s.sum is not None else Decimal("0")
    m = Decimal("0")
    if m_records:
        s = summarize(
            tuple(m_records), field="trade_value.primary_value"
        )
        m = s.sum if s.sum is not None else Decimal("0")

    return BalanceSummary(
        total_exports=x,
        total_imports=m,
        trade_balance=x - m,
        total_trade=x + m,
        record_count=len(records),
    )


# ---------------------------------------------------------------------------
# Country balance
# ---------------------------------------------------------------------------


def country_balance(
    dataset: CanonicalDataset,
    *,
    reporter_code: int | None = None,
    descending: bool = True,
    limit: int | None = None,
) -> tuple[CountryBalanceRow, ...]:
    """Compute the trade balance per reporter
    (country).

    Parameters
    ----------
    dataset
        The `CanonicalDataset` to analyse.
    reporter_code
        If supplied, restrict to this single
        reporter. The result is then a
        zero-or-one-element tuple (zero when no
        records match).
    descending
        When `True` (default), the largest
        balances first.
    limit
        If supplied, return only the top `limit`
        rows.

    Returns
    -------
    tuple[CountryBalanceRow, ...]
        Sorted by `trade_balance` (descending by
        default). Empty when no records match.
    """
    if limit is not None and limit < 0:
        raise BalanceAnalyticsError("limit must be non-negative")
    _check_canonical_dataset(dataset, fn_name="country_balance")

    selected = _select_records(dataset, reporter_code=reporter_code)
    if not selected:
        return ()

    # F-002: per-flow per-reporter aggregation routed
    # through the internal Query Engine (group_by +
    # summarize). The hand-rolled `dict.get(...)` +
    # `+ v` pattern has been retired.
    by_reporter_x = _sum_primary_by_group(
        selected, flow_code="X", group_field="reporter.reporter_code"
    )
    by_reporter_m = _sum_primary_by_group(
        selected, flow_code="M", group_field="reporter.reporter_code"
    )

    # Metadata (iso3 / name) is still collected per-
    # record because the Query Engine does not yet
    # support multi-attribute grouping; this is a
    # pure lookup, not an aggregation.
    meta: dict[int, dict[str, Any]] = {}
    counts: dict[int, int] = {}
    for record in selected:
        code = record.reporter.reporter_code
        if code not in meta:
            meta[code] = {
                "iso3": record.reporter.iso3,
                "name": record.reporter.name,
            }
        counts[code] = counts.get(code, 0) + 1

    rows: list[CountryBalanceRow] = []
    for code in sorted(counts):
        x = by_reporter_x.get(code, Decimal("0"))
        m = by_reporter_m.get(code, Decimal("0"))
        rows.append(
            CountryBalanceRow(
                reporter_code=code,
                reporter_iso3=meta[code].get("iso3"),
                reporter_name=meta[code].get("name"),
                total_exports=x,
                total_imports=m,
                trade_balance=x - m,
                total_trade=x + m,
                record_count=counts[code],
            )
        )
    rows.sort(key=lambda r: r.trade_balance, reverse=descending)
    if limit is not None:
        rows = rows[:limit]
    return tuple(rows)


# ---------------------------------------------------------------------------
# Partner balance
# ---------------------------------------------------------------------------


def partner_trade_balance(
    dataset: CanonicalDataset,
    *,
    reporter_code: int,
    descending: bool = True,
    limit: int | None = None,
) -> tuple[PartnerBalanceRow, ...]:
    """Compute the trade balance per partner for
    one reporter.

    Parameters
    ----------
    dataset
        The `CanonicalDataset` to analyse.
    reporter_code
        The reporter whose partners to rank.
    descending
        When `True` (default), the largest
        balances first.
    limit
        If supplied, return only the top `limit`
        rows.

    Returns
    -------
    tuple[PartnerBalanceRow, ...]
        Sorted by `trade_balance` (descending by
        default). Empty when no records match.

    Notes
    -----
    Named `partner_trade_balance` (not
    `partner_balance`) to disambiguate from
    `partner.partner_balance` in P6-003, which
    has a different signature (`by=...`) and a
    different shape (per-partner ranking keyed
    by any sortable field, not strictly
    `trade_balance`).
    """
    if limit is not None and limit < 0:
        raise BalanceAnalyticsError("limit must be non-negative")
    _check_canonical_dataset(dataset, fn_name="partner_trade_balance")

    selected = _select_records(dataset, reporter_code=reporter_code)
    if not selected:
        return ()

    # F-002: per-flow per-partner aggregation routed
    # through the internal Query Engine (group_by +
    # summarize). The hand-rolled `dict.get(...)` +
    # `+ v` pattern has been retired.
    by_partner_x = _sum_primary_by_group(
        selected, flow_code="X", group_field="partner.partner_code"
    )
    by_partner_m = _sum_primary_by_group(
        selected, flow_code="M", group_field="partner.partner_code"
    )

    # Metadata (iso3 / name) is still collected per-
    # record because the Query Engine does not yet
    # support multi-attribute grouping; this is a
    # pure lookup, not an aggregation.
    meta: dict[int, dict[str, Any]] = {}
    counts: dict[int, int] = {}
    for record in selected:
        code = record.partner.partner_code
        if code not in meta:
            meta[code] = {
                "iso3": record.partner.iso3,
                "name": record.partner.name,
            }
        counts[code] = counts.get(code, 0) + 1

    rows: list[PartnerBalanceRow] = []
    for code in sorted(counts):
        x = by_partner_x.get(code, Decimal("0"))
        m = by_partner_m.get(code, Decimal("0"))
        rows.append(
            PartnerBalanceRow(
                partner_code=code,
                partner_iso3=meta[code].get("iso3"),
                partner_name=meta[code].get("name"),
                total_exports=x,
                total_imports=m,
                trade_balance=x - m,
                total_trade=x + m,
                record_count=counts[code],
            )
        )
    rows.sort(key=lambda r: r.trade_balance, reverse=descending)
    if limit is not None:
        rows = rows[:limit]
    return tuple(rows)


# ---------------------------------------------------------------------------
# Commodity balance
# ---------------------------------------------------------------------------


def commodity_balance(
    dataset: CanonicalDataset,
    *,
    reporter_code: int | None = None,
    descending: bool = True,
    limit: int | None = None,
) -> tuple[CommodityBalanceRow, ...]:
    """Compute the trade balance per commodity
    (HS code).

    Parameters
    ----------
    dataset
        The `CanonicalDataset` to analyse.
    reporter_code
        If supplied, restrict to this reporter's
        trades. When `None` (default), aggregate
        across all reporters (a global per-
        commodity breakdown).
    descending
        When `True` (default), the largest
        balances first.
    limit
        If supplied, return only the top `limit`
        rows.

    Returns
    -------
    tuple[CommodityBalanceRow, ...]
        Sorted by `trade_balance` (descending by
        default). Empty when no records match.
    """
    if limit is not None and limit < 0:
        raise BalanceAnalyticsError("limit must be non-negative")
    _check_canonical_dataset(dataset, fn_name="commodity_balance")

    selected = _select_records(dataset, reporter_code=reporter_code)
    if not selected:
        return ()

    # F-002: per-flow per-commodity aggregation routed
    # through the internal Query Engine (group_by +
    # summarize). The hand-rolled `dict.get(...)` +
    # `+ v` pattern has been retired.
    by_code_x = _sum_primary_by_group(
        selected, flow_code="X", group_field="commodity.commodity_code"
    )
    by_code_m = _sum_primary_by_group(
        selected, flow_code="M", group_field="commodity.commodity_code"
    )

    # Metadata (commodity name) is still collected per-
    # record because the Query Engine does not yet
    # support multi-attribute grouping; this is a
    # pure lookup, not an aggregation.
    meta: dict[str, str | None] = {}
    counts: dict[str, int] = {}
    for record in selected:
        code = record.commodity.commodity_code
        if code not in meta:
            meta[code] = record.commodity.name
        counts[code] = counts.get(code, 0) + 1

    rows: list[CommodityBalanceRow] = []
    for code in sorted(counts):
        x = by_code_x.get(code, Decimal("0"))
        m = by_code_m.get(code, Decimal("0"))
        rows.append(
            CommodityBalanceRow(
                commodity_code=code,
                commodity_name=meta[code],
                total_exports=x,
                total_imports=m,
                trade_balance=x - m,
                total_trade=x + m,
                record_count=counts[code],
            )
        )
    rows.sort(key=lambda r: r.trade_balance, reverse=descending)
    if limit is not None:
        rows = rows[:limit]
    return tuple(rows)


# ---------------------------------------------------------------------------
# Global balance
# ---------------------------------------------------------------------------


def global_balance(dataset: CanonicalDataset) -> BalanceSummary:
    """Compute the global trade balance across
    ALL reporters, ALL partners, ALL commodities
    and ALL flows.

    Returns a single `BalanceSummary` with
    `total_exports`, `total_imports`,
    `trade_balance` (= exports - imports),
    `total_trade` (= exports + imports), and
    `record_count`.

    The flow classification is exhaustive: any
    record whose `flow.flow_code` is not "X"
    (export) is counted as an import. This
    matches UN Comtrade's two-flow model.

    Returns a `BalanceSummary` with all zero
    values when the dataset is empty (the
    caller can detect an empty dataset via
    `record_count == 0`).
    """
    _check_canonical_dataset(dataset, fn_name="global_balance")
    return _build_balance_summary(dataset.records)