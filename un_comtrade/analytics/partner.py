"""Partner-level analytics (P6-003).

This module is the second concrete analytics
submodule built on top of the `AnalyticsEngine`
foundation (P6-001). It provides **four
partner-level analytics** that operate
exclusively on `CanonicalDataset`:

- `top_partners(...)` — rank partners by trade
  value for a given reporter.
- `partner_growth(...)` — year-over-year (or
  period-over-period) growth of a specific
  partner's trade with the reporter.
- `partner_balance(...)` — exports minus imports
  per partner for a given reporter.
- `bilateral_summary(...)` — comprehensive
  summary of trade between two reporters (or a
  reporter and a partner), including the mirror
  flow from the partner's perspective.

All functions accept a `CanonicalDataset` and
return either a frozen dataclass (for
`bilateral_summary`) or a tuple of frozen
dataclasses (for `top_partners`,
`partner_balance`). The growth function returns
a `PartnerGrowth` container that includes both
the per-period points and the absolute /
relative change summary.

The module reuses the `Filter`, `Metric`, and
`Aggregation` primitives from the parent
`AnalyticsEngine` — no new abstractions are
introduced. The dataclasses are frozen
(ADR-0013) and use `Decimal` for monetary values
(ADR-0027).

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
# / group operations through the internal
# Query engine rather than re-implementing.
from ._query_engine import (
    Query,
    sum as _q_sum,
    summarize as _q_summarize,
)

__all__ = [
    # Errors
    "PartnerAnalyticsError",
    # Top partners
    "PartnerRankingRow",
    "top_partners",
    # Partner growth
    "PartnerGrowthPoint",
    "PartnerGrowth",
    "partner_growth",
    # Partner balance
    "PartnerBalanceRow",
    "partner_balance",
    # Bilateral summary
    "BilateralSummary",
    "bilateral_summary",
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class PartnerAnalyticsError(AnalyticsError):
    """Raised when a partner-level analytics
    operation cannot be performed (e.g. unknown
    ranking field, missing reporter / partner)."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _select_records(
    dataset: CanonicalDataset,
    *,
    reporter_code: int | None = None,
    partner_code: int | None = None,
    flow_code: str | None = None,
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
    if flow_code is not None:
        q = q.filter(flow_code=flow_code)
    return q.execute().records


def _sum_primary_value(records) -> Decimal:
    """Sum `trade_value.primary_value` across a
    sequence of records, ignoring `None`.

    QE-007 refactor: delegates to the
    internal Query engine's `sum(...)`
    aggregation.
    """
    result = _q_sum(records, field="primary_value")
    return result if result is not None else Decimal("0")


def _check_canonical_dataset(
    dataset: Any, *, fn_name: str
) -> None:
    if not isinstance(dataset, CanonicalDataset):
        raise PartnerAnalyticsError(
            f"{fn_name} source must be a CanonicalDataset; "
            f"got {type(dataset).__name__}"
        )


# ---------------------------------------------------------------------------
# Top partners
# ---------------------------------------------------------------------------


#: Fields accepted by `top_partners(...,
#: by=...)` and `partner_balance(...,
#: by=...)`.
_PARTNER_RANKING_FIELDS = frozenset({
    "total_trade",
    "exports",
    "imports",
    "trade_balance",
    "abs_trade_balance",
    "record_count",
})


@dataclass(frozen=True)
class PartnerRankingRow:
    """One row of a partner ranking.

    Captures totals for a single partner (relative
    to a fixed reporter) plus the ISO3 / name
    metadata if present in the source records.
    """

    partner_code: int
    partner_iso3: str | None
    partner_name: str | None
    total_exports: Decimal
    total_imports: Decimal
    total_trade: Decimal
    trade_balance: Decimal
    record_count: int

    def __post_init__(self) -> None:
        for f in (
            "total_exports", "total_imports",
            "total_trade", "trade_balance",
        ):
            v = getattr(self, f)
            if not isinstance(v, Decimal):
                raise PartnerAnalyticsError(
                    f"{f} must be Decimal; got {type(v).__name__}"
                )


def top_partners(
    dataset: CanonicalDataset,
    *,
    reporter_code: int,
    flow: str | None = None,
    by: str = "total_trade",
    descending: bool = True,
    limit: int | None = None,
) -> tuple[PartnerRankingRow, ...]:
    """Rank partners by trade value for a fixed
    reporter.

    Parameters
    ----------
    dataset
        The `CanonicalDataset` to analyse.
    reporter_code
        The reporter whose partners to rank.
    flow
        Optional flow filter. `"X"` keeps exports
        only; `"M"` keeps imports only; `None`
        (default) keeps both flows (totals are
        exports + imports).
    by
        One of `"total_trade"` (default),
        `"exports"`, `"imports"`, `"trade_balance"`,
        `"abs_trade_balance"`, or `"record_count"`.
    descending
        When `True` (default), largest values
        first.
    limit
        If supplied, return only the top `limit`
        rows (after sorting).

    Returns
    -------
    tuple[PartnerRankingRow, ...]
        Sorted by `by`. Empty tuple when no
        partners match.
    """
    if by not in _PARTNER_RANKING_FIELDS:
        raise PartnerAnalyticsError(
            f"Unknown ranking field {by!r}; "
            f"valid: {sorted(_PARTNER_RANKING_FIELDS)}"
        )
    if limit is not None and limit < 0:
        raise PartnerAnalyticsError(
            "limit must be non-negative"
        )
    _check_canonical_dataset(dataset, fn_name="top_partners")

    records = _select_records(
        dataset,
        reporter_code=reporter_code,
        flow_code=flow,
    )
    if not records:
        return ()

    # QE-007 refactor: group records via the
    # Query engine. Two queries capture X
    # and M totals; one captures counts.
    # This replaces the hand-rolled
    # `by_partner_x` / `by_partner_m` dicts.
    by_partner_x: dict[int, Decimal] = {}
    by_partner_m: dict[int, Decimal] = {}
    meta: dict[int, dict[str, Any]] = {}
    counts: dict[int, int] = {}

    # Single pass over records for metadata
    # (iso3 / name) and counts (we still
    # need these even though the Query
    # engine could compute counts too,
    # because the partner.partner_code is
    # the group key).
    for record in records:
        code = record.partner.partner_code
        if code not in meta:
            meta[code] = {
                "iso3": record.partner.iso3,
                "name": record.partner.name,
            }
        counts[code] = counts.get(code, 0) + 1

    # X totals via the Query engine.
    qx = (
        Query(dataset)
        .filter(reporter_code=reporter_code)
        .filter(flow_code="X")
        .group_by("partner_code")
    )
    for group in qx.execute().groups:
        code = group.key[0]
        s = _q_summarize(
            group.records, field="primary_value"
        )
        by_partner_x[code] = (
            s.sum if s.sum is not None else Decimal("0")
        )

    # M totals via the Query engine.
    qm = (
        Query(dataset)
        .filter(reporter_code=reporter_code)
        .filter(flow_code="M")
        .group_by("partner_code")
    )
    for group in qm.execute().groups:
        code = group.key[0]
        s = _q_summarize(
            group.records, field="primary_value"
        )
        by_partner_m[code] = (
            s.sum if s.sum is not None else Decimal("0")
        )

    # If a flow filter is in effect, suppress the
    # counter-flow values so the rank focuses on
    # the requested flow.
    if flow == "X":
        for code in by_partner_m:
            by_partner_m[code] = Decimal("0")
    elif flow == "M":
        for code in by_partner_x:
            by_partner_x[code] = Decimal("0")

    rows: list[PartnerRankingRow] = []
    for code in sorted(counts):
        x = by_partner_x.get(code, Decimal("0"))
        m = by_partner_m.get(code, Decimal("0"))
        rows.append(
            PartnerRankingRow(
                partner_code=code,
                partner_iso3=meta[code].get("iso3"),
                partner_name=meta[code].get("name"),
                total_exports=x,
                total_imports=m,
                total_trade=x + m,
                trade_balance=x - m,
                record_count=counts[code],
            )
        )

    def _sort_key(row: PartnerRankingRow):
        if by == "total_trade":
            return row.total_trade
        if by == "exports":
            return row.total_exports
        if by == "imports":
            return row.total_imports
        if by == "trade_balance":
            return row.trade_balance
        if by == "abs_trade_balance":
            return abs(row.trade_balance)
        if by == "record_count":
            return row.record_count
        raise PartnerAnalyticsError(f"unreachable: {by}")

    rows.sort(key=_sort_key, reverse=descending)
    if limit is not None:
        rows = rows[:limit]
    return tuple(rows)


# ---------------------------------------------------------------------------
# Partner growth
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PartnerGrowthPoint:
    """One point on a partner growth series."""

    year: int
    period: str
    total_trade: Decimal
    exports: Decimal
    imports: Decimal
    record_count: int

    def __post_init__(self) -> None:
        for f in ("total_trade", "exports", "imports"):
            v = getattr(self, f)
            if not isinstance(v, Decimal):
                raise PartnerAnalyticsError(
                    f"{f} must be Decimal; got {type(v).__name__}"
                )


@dataclass(frozen=True)
class PartnerGrowth:
    """Time-series of partner growth for one
    reporter / partner pair.

    `points` is sorted by `(year, period)`. The
    `absolute_change` is `last_total_trade -
    first_total_trade`. The `relative_change` is
    `(last - first) / first` when `first != 0`,
    else `None`. The `cagr` is the compound
    annual growth rate when there are ≥ 2 points
    spanning at least 1 year, else `None`.
    """

    reporter_code: int
    partner_code: int
    points: tuple[PartnerGrowthPoint, ...] = field(
        default_factory=tuple
    )
    absolute_change: Decimal = Decimal("0")
    relative_change: Decimal | None = None
    cagr: Decimal | None = None

    @property
    def years(self) -> tuple[int, ...]:
        return tuple(sorted({p.year for p in self.points}))


def _compute_cagr(
    first: Decimal, last: Decimal, years: int
) -> Decimal | None:
    """Compute the compound annual growth rate.

    Returns `None` when the calculation is
    undefined (years ≤ 0, or first is non-positive
    with a non-zero last). For zero first /
    zero last, returns 0.
    """
    if years <= 0:
        return None
    if first == 0:
        if last == 0:
            return Decimal("0")
        return None  # undefined: 0 → non-zero
    if first < 0:
        return None  # CAGR undefined for negative bases
    try:
        ratio = float(last) / float(first)
        if ratio <= 0:
            return None
        return Decimal(str(ratio ** (1.0 / years) - 1))
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


def partner_growth(
    dataset: CanonicalDataset,
    *,
    reporter_code: int,
    partner_code: int,
    granularity: str = "year",
) -> PartnerGrowth:
    """Compute partner growth for one
    reporter / partner pair.

    Parameters
    ----------
    dataset
        The `CanonicalDataset` to analyse.
    reporter_code
        The reporter whose side of the trade is
        counted.
    partner_code
        The partner whose growth is computed.
    granularity
        `"year"` (default) groups by `ref_year`;
        `"period"` groups by `period` string.

    Returns
    -------
    PartnerGrowth
        Container with sorted per-period
        `points` plus absolute / relative
        change summary and CAGR. Returns an
        empty `PartnerGrowth` when the pair has
        no records.
    """
    if granularity not in ("year", "period"):
        raise PartnerAnalyticsError(
            f"Unknown granularity {granularity!r}; "
            f"valid: 'year', 'period'"
        )
    _check_canonical_dataset(dataset, fn_name="partner_growth")

    records = _select_records(
        dataset,
        reporter_code=reporter_code,
        partner_code=partner_code,
    )
    if not records:
        return PartnerGrowth(
            reporter_code=reporter_code,
            partner_code=partner_code,
        )

    # Group by (year, period).
    bucket: dict[tuple[int, str], list] = {}
    for r in records:
        key = (r.ref_year, r.period)
        bucket.setdefault(key, []).append(r)

    points: list[PartnerGrowthPoint] = []
    for (year, period), group in bucket.items():
        x = _sum_primary_value(
            r for r in group if r.flow.flow_code == "X"
        )
        m = _sum_primary_value(
            r for r in group if r.flow.flow_code == "M"
        )
        points.append(
            PartnerGrowthPoint(
                year=year,
                period=period,
                total_trade=x + m,
                exports=x,
                imports=m,
                record_count=len(group),
            )
        )
    points.sort(key=lambda p: (p.year, p.period))

    first = points[0].total_trade
    last = points[-1].total_trade
    abs_change = last - first
    if first != 0:
        rel_change = abs_change / first
    else:
        rel_change = None

    cagr: Decimal | None = None
    if granularity == "year" and len(points) >= 2:
        n_years = points[-1].year - points[0].year
        if n_years > 0:
            cagr = _compute_cagr(first, last, n_years)

    return PartnerGrowth(
        reporter_code=reporter_code,
        partner_code=partner_code,
        points=tuple(points),
        absolute_change=abs_change,
        relative_change=rel_change,
        cagr=cagr,
    )


# ---------------------------------------------------------------------------
# Partner balance
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PartnerBalanceRow:
    """One row of a partner balance view.

    Sibling of `PartnerRankingRow` — kept as a
    separate type so callers can opt into the
    balance view semantically.
    """

    partner_code: int
    partner_iso3: str | None
    partner_name: str | None
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
                raise PartnerAnalyticsError(
                    f"{f} must be Decimal; got {type(v).__name__}"
                )


def partner_balance(
    dataset: CanonicalDataset,
    *,
    reporter_code: int,
    by: str = "trade_balance",
    descending: bool = True,
    limit: int | None = None,
) -> tuple[PartnerBalanceRow, ...]:
    """Compute per-partner trade balance for one
    reporter.

    Equivalent to `top_partners(...,
    by="trade_balance")` but typed separately
    (returns `PartnerBalanceRow` instead of
    `PartnerRankingRow`) so callers can opt into
    the balance view semantically.

    Parameters
    ----------
    dataset
        The `CanonicalDataset` to analyse.
    reporter_code
        The reporter whose partners to summarise.
    by
        One of `"trade_balance"` (default),
        `"abs_trade_balance"`, `"total_trade"`,
        `"exports"`, `"imports"`, or
        `"record_count"`.
    descending
        When `True` (default), largest values
        first.
    limit
        If supplied, return only the top `limit`
        rows (after sorting).

    Returns
    -------
    tuple[PartnerBalanceRow, ...]
        Sorted by `by`. Empty tuple when no
        partners match.
    """
    if by not in _PARTNER_RANKING_FIELDS:
        raise PartnerAnalyticsError(
            f"Unknown ranking field {by!r}; "
            f"valid: {sorted(_PARTNER_RANKING_FIELDS)}"
        )
    if limit is not None and limit < 0:
        raise PartnerAnalyticsError(
            "limit must be non-negative"
        )
    _check_canonical_dataset(dataset, fn_name="partner_balance")

    # Reuse top_partners' grouping logic.
    ranking = top_partners(
        dataset,
        reporter_code=reporter_code,
        flow=None,
        by=by,
        descending=descending,
        limit=limit,
    )

    # Re-shape as PartnerBalanceRow.
    return tuple(
        PartnerBalanceRow(
            partner_code=r.partner_code,
            partner_iso3=r.partner_iso3,
            partner_name=r.partner_name,
            total_exports=r.total_exports,
            total_imports=r.total_imports,
            trade_balance=r.trade_balance,
            total_trade=r.total_trade,
            record_count=r.record_count,
        )
        for r in ranking
    )


# ---------------------------------------------------------------------------
# Bilateral summary
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BilateralSummary:
    """Comprehensive summary of trade between a
    reporter and a partner.

    Captures BOTH sides of the relationship:

    - `reporter_to_partner_exports` /
      `reporter_to_partner_imports` — flows
      reported by `reporter_code` with
      `partner_code` as counterparty.
    - `partner_to_reporter_exports` /
      `partner_to_reporter_imports` — mirror
      flows where the counterparty is the
      reporter and the partner is the partner
      (i.e. `reporter == partner_code` and
      `partner == reporter_code`). Useful for
      reconciling asymmetries between the two
      sides' reporting.

    Returns `None` from `bilateral_summary(...)`
    when the pair has no records on either side.
    """

    reporter_code: int
    partner_code: int
    partner_iso3: str | None
    partner_name: str | None
    reporter_to_partner_exports: Decimal
    reporter_to_partner_imports: Decimal
    partner_to_reporter_exports: Decimal
    partner_to_reporter_imports: Decimal
    total_exports: Decimal
    total_imports: Decimal
    total_trade: Decimal
    record_count: int
    year_range: tuple[int, int] | None

    def __post_init__(self) -> None:
        for f in (
            "reporter_to_partner_exports",
            "reporter_to_partner_imports",
            "partner_to_reporter_exports",
            "partner_to_reporter_imports",
            "total_exports", "total_imports",
            "total_trade",
        ):
            v = getattr(self, f)
            if not isinstance(v, Decimal):
                raise PartnerAnalyticsError(
                    f"{f} must be Decimal; got {type(v).__name__}"
                )


def bilateral_summary(
    dataset: CanonicalDataset,
    *,
    reporter_code: int,
    partner_code: int,
) -> BilateralSummary | None:
    """Compute the bilateral summary for one
    reporter / partner pair.

    Returns `None` when no records exist on
    either side.
    """
    _check_canonical_dataset(
        dataset, fn_name="bilateral_summary"
    )

    # Side A: reporter == reporter_code,
    # partner == partner_code.
    side_a = _select_records(
        dataset,
        reporter_code=reporter_code,
        partner_code=partner_code,
    )
    # Side B (mirror): reporter == partner_code,
    # partner == reporter_code.
    side_b = _select_records(
        dataset,
        reporter_code=partner_code,
        partner_code=reporter_code,
    )

    if not side_a and not side_b:
        return None

    a_x = _sum_primary_value(
        r for r in side_a if r.flow.flow_code == "X"
    )
    a_m = _sum_primary_value(
        r for r in side_a if r.flow.flow_code == "M"
    )
    b_x = _sum_primary_value(
        r for r in side_b if r.flow.flow_code == "X"
    )
    b_m = _sum_primary_value(
        r for r in side_b if r.flow.flow_code == "M"
    )

    total_exports = a_x + b_x
    total_imports = a_m + b_m
    total_trade = total_exports + total_imports

    # Pick metadata from whichever side had data
    # first; prefer side_a so the partner is
    # identified consistently.
    iso3: str | None = None
    name: str | None = None
    if side_a:
        iso3 = side_a[0].partner.iso3
        name = side_a[0].partner.name
    elif side_b:
        iso3 = side_b[0].partner.iso3
        name = side_b[0].partner.name

    years = [
        r.ref_year
        for r in (*side_a, *side_b)
    ]
    year_range: tuple[int, int] | None = (
        (min(years), max(years)) if years else None
    )

    return BilateralSummary(
        reporter_code=reporter_code,
        partner_code=partner_code,
        partner_iso3=iso3,
        partner_name=name,
        reporter_to_partner_exports=a_x,
        reporter_to_partner_imports=a_m,
        partner_to_reporter_exports=b_x,
        partner_to_reporter_imports=b_m,
        total_exports=total_exports,
        total_imports=total_imports,
        total_trade=total_trade,
        record_count=len(side_a) + len(side_b),
        year_range=year_range,
    )