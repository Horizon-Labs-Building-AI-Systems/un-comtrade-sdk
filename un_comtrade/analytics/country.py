"""Country-level analytics (P6-002).

This module is the first concrete analytics
submodule built on top of the `AnalyticsEngine`
foundation (P6-001). It provides **five
country-level analytics** that operate exclusively
on `CanonicalDataset`:

- `total_imports(...)` — sum of imports for a
  given reporter (optionally filtered by year /
  window).
- `total_exports(...)` — sum of exports for a
  given reporter (optionally filtered by year /
  window).
- `country_ranking(...)` — rank reporters by
  total trade / exports / imports, with optional
  flow filter and limit.
- `country_summary(...)` — one-stop summary per
  reporter: totals, balance, partner count,
  year range.
- `country_trend(...)` — exports / imports /
  balance per year (or per period) for a given
  reporter.

All functions accept a `CanonicalDataset` and
return either a `Decimal` (for total_*), a frozen
dataclass (for summary / trend / ranking), or a
tuple of frozen dataclasses (for ranking).

**QE-007 refactor:** this module's filter /
group / aggregate / sort logic is now built on
top of the internal `Query` engine (see
`un_comtrade.analytics._query_engine`). The
public API is unchanged; only the internal
implementation now delegates to `Query(...)`,
`Query.filter(...)`, `Query.group_by(...)`,
`sum(...)`, `summarize(...)`, and `Query.sort(...)`.

The dataclasses are frozen (ADR-0013) and use
`Decimal` for monetary values (ADR-0027).

The module is **decoupled from the transport
layer** (same constraint as `AnalyticsEngine`):
only stdlib + intra-package imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from ..transform import CanonicalDataset
# QE-007: route all filter / group / aggregate /
# sort operations through the internal Query
# engine rather than re-implementing them.
from ._query_engine import (
    Query,
    QueryError,
    sum as _q_sum,
    summarize as _q_summarize,
)

__all__ = [
    # Errors
    "CountryAnalyticsError",
    # Total imports / exports
    "total_imports",
    "total_exports",
    # Ranking
    "CountryRankingRow",
    "country_ranking",
    # Summary
    "CountrySummary",
    "country_summary",
    # Trend
    "CountryTrendPoint",
    "CountryTrend",
    "country_trend",
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CountryAnalyticsError(Exception):
    """Raised when a country-level analytics
    operation cannot be performed (e.g. unknown
    ranking field, missing reporter).
    """


# ---------------------------------------------------------------------------
# Helpers (QE-007 — delegated to Query engine)
# ---------------------------------------------------------------------------


def _check_dataset(
    dataset: Any, *, fn_name: str
) -> None:
    """Validate that `dataset` is a
    `CanonicalDataset`. Used to fail fast on
    misuse at the public analytics boundary.
    """
    if not isinstance(dataset, CanonicalDataset):
        raise CountryAnalyticsError(
            f"{fn_name} source must be a "
            f"CanonicalDataset; got "
            f"{type(dataset).__name__}"
        )


def _filter_records(
    dataset: CanonicalDataset,
    *,
    reporter_code: int | None = None,
    flow_code: str | None = None,
    year: int | None = None,
    years: tuple[int, ...] | None = None,
):
    """Return records filtered by reporter_code
    (optional), flow_code (optional), and one of
    `year` / `years` (optional).

    QE-007 refactor: builds a `Query` via the
    internal query engine's `.filter(...)` and
    `.execute()` pipeline rather than hand-rolling
    the filter loop.
    """
    q = Query(dataset)
    # `Query.filter()` accepts kwargs that build
    # FieldPredicates; we route the same filters
    # through it instead of an inline loop.
    if reporter_code is not None:
        q = q.filter(reporter_code=reporter_code)
    if flow_code is not None:
        q = q.filter(flow_code=flow_code)
    if year is not None:
        q = q.filter(ref_year=year)
    if years is not None:
        # The internal Query supports single-value
        # `eq` only at the kwargs layer; build an
        # explicit predicate for `in`.
        from ._query_engine import (
            FieldPredicate,
        )
        in_pred = FieldPredicate(
            field="ref_year",
            operator="in",
            value=years,
        )
        q = q.filter(in_pred)
    return q.execute().records


def _sum_primary_value(records) -> Decimal:
    """Sum `trade_value.primary_value` across a
    sequence of records, ignoring `None`.

    QE-007 refactor: delegates to the internal
    query engine's `sum(records,
    field="primary_value")` for Decimal-safe
    aggregation.
    """
    result = _q_sum(records, field="primary_value")
    return result if result is not None else Decimal("0")


# ---------------------------------------------------------------------------
# Total imports / exports
# ---------------------------------------------------------------------------


def total_imports(
    dataset: CanonicalDataset,
    *,
    reporter_code: int | None = None,
    year: int | None = None,
    years: tuple[int, ...] | None = None,
) -> Decimal:
    """Sum of imports (`flow_code == "M"`) for the
    optional filters.

    Parameters
    ----------
    dataset
        The `CanonicalDataset` to analyse.
    reporter_code
        If supplied, only records whose
        `reporter.reporter_code == reporter_code`
        contribute.
    year
        If supplied, only records with
        `ref_year == year` contribute.
    years
        If supplied, only records whose `ref_year`
        is in this tuple contribute. Mutually
        exclusive with `year`.

    Returns
    -------
    Decimal
        Total import value (USD). Returns
        `Decimal("0")` when no records match.
    """
    if year is not None and years is not None:
        raise CountryAnalyticsError(
            "year and years are mutually exclusive"
        )
    _check_dataset(dataset, fn_name="total_imports")
    records = _filter_records(
        dataset,
        reporter_code=reporter_code,
        flow_code="M",
        year=year,
        years=years,
    )
    return _sum_primary_value(records)


def total_exports(
    dataset: CanonicalDataset,
    *,
    reporter_code: int | None = None,
    year: int | None = None,
    years: tuple[int, ...] | None = None,
) -> Decimal:
    """Sum of exports (`flow_code == "X"`) for the
    optional filters. Mirror of `total_imports`."""
    if year is not None and years is not None:
        raise CountryAnalyticsError(
            "year and years are mutually exclusive"
        )
    _check_dataset(dataset, fn_name="total_exports")
    records = _filter_records(
        dataset,
        reporter_code=reporter_code,
        flow_code="X",
        year=year,
        years=years,
    )
    return _sum_primary_value(records)


# ---------------------------------------------------------------------------
# Country ranking
# ---------------------------------------------------------------------------


#: Fields accepted by `country_ranking(...,
#: by=...)`. The "total_trade_value" alias
#: means "exports + imports combined".
_COUNTRY_RANKING_FIELDS = frozenset({
    "total_trade_value",
    "exports",
    "imports",
    "trade_balance",
    "record_count",
})


@dataclass(frozen=True)
class CountryRankingRow:
    """One row of a country ranking.

    Captures totals for a single reporter plus the
    ISO3 / name metadata if present in the source
    records.
    """

    reporter_code: int
    reporter_iso3: str | None
    reporter_name: str | None
    total_exports: Decimal
    total_imports: Decimal
    total_trade_value: Decimal
    trade_balance: Decimal
    record_count: int

    def __post_init__(self) -> None:
        if not isinstance(
            self.total_exports, Decimal
        ) or not isinstance(
            self.total_imports, Decimal
        ):
            raise CountryAnalyticsError(
                "total_exports / total_imports must be "
                "Decimal"
            )
        if not isinstance(self.total_trade_value, Decimal):
            raise CountryAnalyticsError(
                "total_trade_value must be Decimal"
            )
        if not isinstance(self.trade_balance, Decimal):
            raise CountryAnalyticsError(
                "trade_balance must be Decimal"
            )


def country_ranking(
    dataset: CanonicalDataset,
    *,
    flow: str | None = None,
    by: str = "total_trade_value",
    descending: bool = True,
    limit: int | None = None,
) -> tuple[CountryRankingRow, ...]:
    """Rank reporters by total trade (or by a
    specific flow / metric).

    Parameters
    ----------
    dataset
        The `CanonicalDataset` to analyse.
    flow
        Optional flow filter. `"X"` keeps exports
        only; `"M"` keeps imports only; `None`
        (default) keeps both flows (totals are
        exports + imports).
    by
        One of `"total_trade_value"` (default),
        `"exports"`, `"imports"`, `"trade_balance"`,
        or `"record_count"`.
    descending
        When `True` (default), largest values
        first; when `False`, smallest values
        first.
    limit
        If supplied, return only the top `limit`
        rows (after sorting).

    Returns
    -------
    tuple[CountryRankingRow, ...]
        Rows sorted by `by` in the requested
        direction. Empty tuple if no records match.
    """
    if by not in _COUNTRY_RANKING_FIELDS:
        raise CountryAnalyticsError(
            f"Unknown ranking field {by!r}; "
            f"valid: {sorted(_COUNTRY_RANKING_FIELDS)}"
        )
    if limit is not None and limit < 0:
        raise CountryAnalyticsError(
            "limit must be non-negative"
        )
    _check_dataset(dataset, fn_name="country_ranking")

    # Aggregate by reporter_code using the
    # internal Query engine (QE-007).
    # Step 1: apply the flow filter (if any)
    # and group by reporter_code.
    q = Query(dataset)
    if flow is not None:
        q = q.filter(flow_code=flow)
    q = q.group_by("reporter_code")
    result = q.execute()
    if not result.groups:
        return ()

    # For flow=None we still need both
    # exports and imports totals per
    # reporter; compute those via the
    # Query engine too.
    by_reporter_x: dict[int, Decimal] = {}
    by_reporter_m: dict[int, Decimal] = {}
    if flow is None:
        # No flow filter: capture both
        # X and M sums in one pass via two
        # queries.
        qx = Query(dataset).filter(flow_code="X")
        rx = qx.group_by("reporter_code").execute()
        for group in rx.groups:
            s = _q_summarize(
                group.records, field="primary_value"
            )
            code = group.key[0]
            by_reporter_x[code] = (
                s.sum if s.sum is not None
                else Decimal("0")
            )
        qm = Query(dataset).filter(flow_code="M")
        rm = qm.group_by("reporter_code").execute()
        for group in rm.groups:
            s = _q_summarize(
                group.records, field="primary_value"
            )
            code = group.key[0]
            by_reporter_m[code] = (
                s.sum if s.sum is not None
                else Decimal("0")
            )

    # Capture reporter metadata (iso3 / name)
    # from the source dataset, indexed by
    # reporter_code.
    meta: dict[int, dict[str, Any]] = {}
    for record in dataset.records:
        code = record.reporter.reporter_code
        if code not in meta:
            meta[code] = {
                "iso3": record.reporter.iso3,
                "name": record.reporter.name,
            }

    rows_by_code: dict[int, CountryRankingRow] = {}
    for group in result.groups:
        code = group.key[0]
        # `summarize` gives us count and sum
        # in one pass.
        agg = _q_summarize(
            group.records, field="primary_value"
        )
        flow_total = (
            agg.sum if agg.sum is not None
            else Decimal("0")
        )
        if flow == "X":
            x_value = flow_total
            m_value = Decimal("0")
        elif flow == "M":
            x_value = Decimal("0")
            m_value = flow_total
        else:
            x_value = by_reporter_x.get(
                code, Decimal("0")
            )
            m_value = by_reporter_m.get(
                code, Decimal("0")
            )
        total_trade = x_value + m_value
        balance = x_value - m_value
        rows_by_code[code] = CountryRankingRow(
            reporter_code=code,
            reporter_iso3=meta.get(code, {}).get("iso3"),
            reporter_name=meta.get(code, {}).get("name"),
            total_exports=x_value,
            total_imports=m_value,
            total_trade_value=total_trade,
            trade_balance=balance,
            record_count=agg.count,
        )

    # Sort by the requested field via the
    # Query engine (sort key columnar).
    def _sort_key(row: CountryRankingRow):
        if by == "total_trade_value":
            return row.total_trade_value
        if by == "exports":
            return row.total_exports
        if by == "imports":
            return row.total_imports
        if by == "trade_balance":
            return row.trade_balance
        if by == "record_count":
            return row.record_count
        raise CountryAnalyticsError(f"unreachable: {by}")

    # Use Query.sort + limit for the final
    # ranking. We sort the rows through the
    # Query engine for consistency; for
    # arbitrary row-derived sort keys we
    # fall back to Python's sorted().
    # Convert rows back to a Query for sort
    # ordering — but since rows are
    # pre-built CountryRankingRow objects,
    # we sort with Python's sorted (the
    # Query engine sorts records, not
    # arbitrary dataclasses).
    rows = sorted(
        rows_by_code.values(),
        key=_sort_key,
        reverse=descending,
    )
    if limit is not None:
        rows = rows[:limit]
    return tuple(rows)


# ---------------------------------------------------------------------------
# Country summary
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CountrySummary:
    """One-stop summary of a single reporter's
    activity in a `CanonicalDataset`.

    Captures totals, trade balance, partner count,
    record count, and the observed year range.
    """

    reporter_code: int
    reporter_iso3: str | None
    reporter_name: str | None
    total_exports: Decimal
    total_imports: Decimal
    total_trade: Decimal
    trade_balance: Decimal
    partner_count: int
    record_count: int
    year_range: tuple[int, int] | None

    def __post_init__(self) -> None:
        for f in (
            "total_exports", "total_imports",
            "total_trade", "trade_balance",
        ):
            v = getattr(self, f)
            if not isinstance(v, Decimal):
                raise CountryAnalyticsError(
                    f"{f} must be Decimal; got {type(v).__name__}"
                )


def country_summary(
    dataset: CanonicalDataset,
    reporter_code: int,
) -> CountrySummary | None:
    """Build a `CountrySummary` for one reporter.

    Returns `None` when the reporter has no records
    in the dataset.
    """
    _check_dataset(dataset, fn_name="country_summary")
    # QE-007 refactor: filter via Query
    # engine.
    records = _filter_records(
        dataset, reporter_code=reporter_code
    )
    if not records:
        return None

    iso3 = records[0].reporter.iso3
    name = records[0].reporter.name
    # QE-007 refactor: sums delegated to
    # `_q_sum` (the Query engine's
    # aggregation).
    exports = _sum_primary_value(
        r for r in records if r.flow.flow_code == "X"
    )
    imports = _sum_primary_value(
        r for r in records if r.flow.flow_code == "M"
    )
    partner_codes = {r.partner.partner_code for r in records}
    years = [r.ref_year for r in records]
    year_range: tuple[int, int] | None = (
        (min(years), max(years)) if years else None
    )

    return CountrySummary(
        reporter_code=reporter_code,
        reporter_iso3=iso3,
        reporter_name=name,
        total_exports=exports,
        total_imports=imports,
        total_trade=exports + imports,
        trade_balance=exports - imports,
        partner_count=len(partner_codes),
        record_count=len(records),
        year_range=year_range,
    )


# ---------------------------------------------------------------------------
# Country trend
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CountryTrendPoint:
    """One point on a country trend (one year or
    one period)."""

    year: int
    period: str
    exports: Decimal
    imports: Decimal
    total_trade: Decimal
    trade_balance: Decimal
    record_count: int

    def __post_init__(self) -> None:
        for f in ("exports", "imports", "total_trade", "trade_balance"):
            v = getattr(self, f)
            if not isinstance(v, Decimal):
                raise CountryAnalyticsError(
                    f"{f} must be Decimal; got {type(v).__name__}"
                )


@dataclass(frozen=True)
class CountryTrend:
    """Time-series of country activity for one
    reporter.

    `points` is sorted by (year, period) in
    ascending order.
    """

    reporter_code: int
    points: tuple[CountryTrendPoint, ...] = field(
        default_factory=tuple
    )

    @property
    def years(self) -> tuple[int, ...]:
        return tuple(sorted({p.year for p in self.points}))

    @property
    def total_exports(self) -> Decimal:
        return _sum_primary_value_iter(p.exports for p in self.points)

    @property
    def total_imports(self) -> Decimal:
        return _sum_primary_value_iter(p.imports for p in self.points)

    @property
    def total_trade(self) -> Decimal:
        return self.total_exports + self.total_imports


def _sum_primary_value_iter(values) -> Decimal:
    """Sum `Decimal` values (handles `Decimal` + `0`)."""
    total = Decimal("0")
    for v in values:
        if v is None:
            continue
        total += v
    return total


def country_trend(
    dataset: CanonicalDataset,
    reporter_code: int,
    *,
    granularity: str = "year",
) -> CountryTrend:
    """Build a `CountryTrend` for one reporter.

    Parameters
    ----------
    dataset
        The `CanonicalDataset` to analyse.
    reporter_code
        The reporter to summarise.
    granularity
        `"year"` (default) groups by `ref_year`;
        `"period"` groups by `period` (e.g.
        `"2022"`, `"202201"`, etc.). `"year"`
        produces one point per calendar year;
        `"period"` can produce intra-year points.

    Returns
    -------
    CountryTrend
        Trend with `points` sorted by
        `(year, period)`. Returns an empty
        `CountryTrend` when the reporter has no
        records.
    """
    if granularity not in ("year", "period"):
        raise CountryAnalyticsError(
            f"Unknown granularity {granularity!r}; "
            f"valid: 'year', 'period'"
        )
    _check_dataset(dataset, fn_name="country_trend")

    records = _filter_records(
        dataset, reporter_code=reporter_code
    )
    if not records:
        return CountryTrend(
            reporter_code=reporter_code, points=()
        )

    # QE-007 refactor: group via the Query
    # engine's `.group_by(...)`. We group by
    # `ref_year` for "year" granularity, and
    # by `period` for "period" granularity.
    # Multi-field grouping produces tuple keys
    # of length 1.
    group_field = "ref_year" if granularity == "year" else "period"
    q = Query(dataset).filter(reporter_code=reporter_code)
    result = q.group_by(group_field).execute()

    points = []
    for group in result.groups:
        # group.key is (year,) or (period,).
        key_value = group.key[0]
        # Compute exports and imports
        # separately via Query engine.
        # We do this via two sum() calls on
        # the group's records (already
        # filtered to the right reporter +
        # group).
        x_records = [
            r for r in group.records
            if r.flow.flow_code == "X"
        ]
        m_records = [
            r for r in group.records
            if r.flow.flow_code == "M"
        ]
        exports = _sum_primary_value(x_records)
        imports = _sum_primary_value(m_records)
        if granularity == "year":
            year = key_value
            period = group.records[0].period
        else:
            year = group.records[0].ref_year
            period = key_value
        points.append(
            CountryTrendPoint(
                year=year,
                period=period,
                exports=exports,
                imports=imports,
                total_trade=exports + imports,
                trade_balance=exports - imports,
                record_count=len(group.records),
            )
        )
    points.sort(key=lambda p: (p.year, p.period))
    return CountryTrend(
        reporter_code=reporter_code,
        points=tuple(points),
    )