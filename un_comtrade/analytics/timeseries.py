"""Time-series analytics (P6-005).

This module is the fourth concrete analytics
submodule built on top of the `AnalyticsEngine`
foundation (P6-001). It provides five
time-series analytics that operate exclusively
on `CanonicalDataset`:

- `annual_trend(...)` — yearly time-series of
  `sum_primary_value()` (or any user-supplied
  metric) for a reporter / partner /
  commodity, with optional flow filter.
- `monthly_trend(...)` — same shape but
  bucketed per month (UN Comtrade periods
  `"202201"`..`"202212"` are parsed for
  `year + month`; pure-year periods like
  `"2022"` are excluded).
- `rolling_average(points, *, window=3)` —
  rolling mean over a window of `n` points
  applied to any time-series of `TrendPoint`s.
- `cagr(points, *, field="value")` —
  compound annual growth rate between the
  first and last point of a series.
- `growth_rates(points, *, field="value")` —
  per-point period-over-period growth rates
  (relative change).

All monetary fields are `Decimal` (ADR-0027).
All dataclasses are `frozen=True` (ADR-0013).

The module is **decoupled from the transport
layer** (same constraint as `AnalyticsEngine`):
only stdlib + intra-package imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import Any, Sequence

from ..transform import CanonicalDataset
from . import AnalyticsError, Filter, Metric
# QE-007 refactor: route filter / group
# operations through the internal Query
# engine rather than re-implementing.
from ._query_engine import (
    Query,
    sum as _q_sum,
    summarize as _q_summarize,
)

__all__ = [
    # Errors
    "TimeSeriesAnalyticsError",
    # Trend point
    "TrendPoint",
    # Annual / monthly trends
    "annual_trend",
    "monthly_trend",
    # Rolling average
    "rolling_average",
    # CAGR
    "cagr",
    # Growth rates
    "growth_rates",
    "GrowthRatePoint",
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class TimeSeriesAnalyticsError(AnalyticsError):
    """Raised when a time-series analytics
    operation cannot be performed."""


# ---------------------------------------------------------------------------
# TrendPoint
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrendPoint:
    """One point on a time-series trend.

    `year` is the calendar year. `period` is the
    canonical period string from the source
    record (`"2022"`, `"202201"`, etc.). `value`
    is the metric value at this point. For
    monthly trends `month` is set; for annual
    trends it's `None`.

    `record_count` is the number of source
    records that contributed to this point.
    """

    year: int
    period: str
    value: Decimal
    record_count: int
    month: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            raise TimeSeriesAnalyticsError(
                f"value must be Decimal; got {type(self.value).__name__}"
            )
        if not isinstance(self.year, int):
            raise TimeSeriesAnalyticsError(
                f"year must be int; got {type(self.year).__name__}"
            )
        if self.month is not None and (
            not isinstance(self.month, int)
            or self.month < 1
            or self.month > 12
        ):
            raise TimeSeriesAnalyticsError(
                f"month must be int in 1..12 or None; got {self.month!r}"
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_canonical_dataset(
    dataset: Any, *, fn_name: str
) -> None:
    if not isinstance(dataset, CanonicalDataset):
        raise TimeSeriesAnalyticsError(
            f"{fn_name} source must be a CanonicalDataset; "
            f"got {type(dataset).__name__}"
        )


def _select_records(
    dataset: CanonicalDataset,
    *,
    reporter_code: int | None = None,
    partner_code: int | None = None,
    flow_code: str | None = None,
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
    if flow_code is not None:
        q = q.filter(flow_code=flow_code)
    if commodity_code is not None:
        q = q.filter(commodity_code=commodity_code)
    return q.execute().records


def _parse_period_year_month(period: str) -> tuple[int, int | None]:
    """Parse a UN Comtrade period string.

    Returns `(year, month)` where `month` is
    `None` for annual-only periods. Raises
    `TimeSeriesAnalyticsError` if the period
    string is malformed.
    """
    if not period:
        raise TimeSeriesAnalyticsError("Empty period string")
    digits = ""
    for ch in period:
        if ch.isdigit():
            digits += ch
        else:
            break
    if len(digits) < 4:
        raise TimeSeriesAnalyticsError(
            f"Period {period!r} has fewer than 4 digits"
        )
    try:
        year = int(digits[:4])
    except ValueError as exc:
        raise TimeSeriesAnalyticsError(
            f"Invalid year in period {period!r}: {exc}"
        ) from exc
    month: int | None = None
    if len(digits) >= 6:
        try:
            month = int(digits[4:6])
        except ValueError as exc:
            raise TimeSeriesAnalyticsError(
                f"Invalid month in period {period!r}: {exc}"
            ) from exc
        if month < 1 or month > 12:
            raise TimeSeriesAnalyticsError(
                f"Period {period!r} has out-of-range month {month}"
            )
    return year, month


def _bucket_records(
    records,
    *,
    granularity: str,
) -> dict[tuple, list]:
    """Group records by `(year, month_or_None)`
    according to the requested granularity."""
    buckets: dict[tuple, list] = {}
    for r in records:
        year, month = _parse_period_year_month(r.period)
        if granularity == "year":
            key = (year, None)
        elif granularity == "month":
            if month is None:
                # Annual-only records are skipped
                # for monthly trends.
                continue
            key = (year, month)
        else:
            raise TimeSeriesAnalyticsError(
                f"Unknown granularity {granularity!r}; "
                f"valid: 'year', 'month'"
            )
        buckets.setdefault(key, []).append(r)
    return buckets


def _metric_for_sum() -> Metric:
    """Return the default `sum_primary_value`
    metric, lazy-imported to avoid the
    parent-package circular-import."""
    from . import Metric
    return Metric.sum_primary_value()


def _coerce_metric(metric: Any) -> Metric:
    """Validate and coerce the metric argument."""
    if not isinstance(metric, Metric):
        raise TimeSeriesAnalyticsError(
            f"metric must be a Metric; got {type(metric).__name__}"
        )
    return metric


# ---------------------------------------------------------------------------
# Annual trend
# ---------------------------------------------------------------------------


def annual_trend(
    dataset: CanonicalDataset,
    *,
    reporter_code: int | None = None,
    flow: str | None = None,
    partner_code: int | None = None,
    commodity_code: str | None = None,
    metric: Metric | None = None,
) -> tuple[TrendPoint, ...]:
    """Build an annual time-series trend.

    Parameters
    ----------
    dataset
        The `CanonicalDataset` to analyse.
    reporter_code, partner_code, flow,
    commodity_code
        Optional filters (any combination).
    metric
        The `Metric` to compute per year.
        Defaults to `Metric.sum_primary_value()`
        (total trade value).

    Returns
    -------
    tuple[TrendPoint, ...]
        Sorted ascending by year. Empty when no
        records match.
    """
    _check_canonical_dataset(dataset, fn_name="annual_trend")
    m = _coerce_metric(metric) if metric is not None else _metric_for_sum()
    selected = _select_records(
        dataset,
        reporter_code=reporter_code,
        partner_code=partner_code,
        flow_code=flow,
        commodity_code=commodity_code,
    )
    if not selected:
        return ()
    buckets = _bucket_records(selected, granularity="year")
    points: list[TrendPoint] = []
    for (year, _month), group in buckets.items():
        group_dataset = CanonicalDataset(
            name=dataset.name,
            records=tuple(group),
            schema_version=dataset.schema_version,
            extracted_at=dataset.extracted_at,
            parser_name=dataset.parser_name,
            skipped=0,
            duplicates_removed=0,
            source_count=len(group),
            metadata=dict(dataset.metadata),
        )
        value = m.compute(group_dataset)
        points.append(
            TrendPoint(
                year=year,
                period=str(year),
                value=_to_decimal(value),
                record_count=len(group),
            )
        )
    points.sort(key=lambda p: p.year)
    return tuple(points)


# ---------------------------------------------------------------------------
# Monthly trend
# ---------------------------------------------------------------------------


def monthly_trend(
    dataset: CanonicalDataset,
    *,
    reporter_code: int | None = None,
    flow: str | None = None,
    partner_code: int | None = None,
    commodity_code: str | None = None,
    metric: Metric | None = None,
) -> tuple[TrendPoint, ...]:
    """Build a monthly time-series trend.

    Same shape as `annual_trend(...)` but
    bucketed per month. Records with annual-only
    period strings (e.g. `"2022"`) are excluded
    because they cannot be mapped to a specific
    month.
    """
    _check_canonical_dataset(dataset, fn_name="monthly_trend")
    m = _coerce_metric(metric) if metric is not None else _metric_for_sum()
    selected = _select_records(
        dataset,
        reporter_code=reporter_code,
        partner_code=partner_code,
        flow_code=flow,
        commodity_code=commodity_code,
    )
    if not selected:
        return ()
    buckets = _bucket_records(selected, granularity="month")
    points: list[TrendPoint] = []
    for (year, month), group in buckets.items():
        assert month is not None
        group_dataset = CanonicalDataset(
            name=dataset.name,
            records=tuple(group),
            schema_version=dataset.schema_version,
            extracted_at=dataset.extracted_at,
            parser_name=dataset.parser_name,
            skipped=0,
            duplicates_removed=0,
            source_count=len(group),
            metadata=dict(dataset.metadata),
        )
        value = m.compute(group_dataset)
        points.append(
            TrendPoint(
                year=year,
                period=f"{year}{month:02d}",
                value=_to_decimal(value),
                record_count=len(group),
                month=month,
            )
        )
    points.sort(key=lambda p: (p.year, p.month))
    return tuple(points)


def _to_decimal(value: Any) -> Decimal:
    """Coerce a metric return value to `Decimal`."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return Decimal(int(value))
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    raise TimeSeriesAnalyticsError(
        f"Cannot coerce metric value {value!r} to Decimal"
    )


# ---------------------------------------------------------------------------
# Rolling average
# ---------------------------------------------------------------------------


def rolling_average(
    points: Sequence[TrendPoint],
    *,
    window: int = 3,
    field: str = "value",
) -> tuple[TrendPoint, ...]:
    """Compute the rolling average of a time-
    series over a window.

    At each index `i`, the output point's
    `field` value is the mean of the input
    `field` values from `max(0, i - window + 1)`
    through `i` (inclusive — i.e., a
    trailing window). The first `window - 1`
    output points are based on a partial
    window (e.g. for `window=3`, index 0 uses
    just point 0, index 1 uses points 0–1, etc.).

    Parameters
    ----------
    points
        Input time-series. Should be sorted by
        `(year, period)`.
    window
        Number of consecutive points to average.
        Default `3`.
    field
        Name of the dataclass attribute to
        average. Default `"value"`.

    Returns
    -------
    tuple[TrendPoint, ...]
        Same length as the input. Each point's
        `field` is replaced with the rolling
        average; all other attributes are
        preserved from the input point.
    """
    if window < 1:
        raise TimeSeriesAnalyticsError(
            "window must be at least 1"
        )
    if not points:
        return ()
    if not all(isinstance(p, TrendPoint) for p in points):
        raise TimeSeriesAnalyticsError(
            "points must be a sequence of TrendPoint"
        )

    # Extract the field values, preserving the
    # original indices.
    raw_values: list[Decimal] = []
    for p in points:
        v = getattr(p, field)
        if not isinstance(v, (Decimal, int, float)):
            raise TimeSeriesAnalyticsError(
                f"point.{field} must be numeric; got {type(v).__name__}"
            )
        raw_values.append(_to_decimal(v))

    # Compute rolling mean.
    result: list[TrendPoint] = []
    for i, point in enumerate(points):
        lo = max(0, i - window + 1)
        window_values = raw_values[lo:i + 1]
        avg = sum(window_values, start=Decimal("0")) / Decimal(
            len(window_values)
        )
        result.append(replace(point, **{field: avg}))
    return tuple(result)


# ---------------------------------------------------------------------------
# CAGR
# ---------------------------------------------------------------------------


def cagr(
    points: Sequence[TrendPoint],
    *,
    field: str = "value",
    years: int | None = None,
) -> Decimal | None:
    """Compute the Compound Annual Growth Rate
    between the first and last point of a
    series.

    Parameters
    ----------
    points
        Input time-series (sorted ascending).
    field
        Dataclass attribute to use. Default
        `"value"`.
    years
        Override for the time span (in years).
        When `None`, derived from the
        `year` difference between the first
        and last points.

    Returns
    -------
    Decimal | None
        The CAGR as a fraction (e.g.
        `Decimal("0.5")` for 50 % annual growth).
        Returns `None` when the calculation is
        undefined (zero / negative first, no
        span, or fewer than 2 points).
    """
    if len(points) < 2:
        return None
    if not all(isinstance(p, TrendPoint) for p in points):
        raise TimeSeriesAnalyticsError(
            "points must be a sequence of TrendPoint"
        )

    first = _to_decimal(getattr(points[0], field))
    last = _to_decimal(getattr(points[-1], field))

    if years is None:
        years = points[-1].year - points[0].year
    if years <= 0:
        return None
    if first == 0:
        if last == 0:
            return Decimal("0")
        return None
    if first < 0:
        return None
    try:
        ratio = float(last) / float(first)
        if ratio <= 0:
            return None
        return Decimal(str(ratio ** (1.0 / years) - 1))
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


# ---------------------------------------------------------------------------
# Growth rates
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GrowthRatePoint:
    """Per-point growth rate observation.

    `growth` is `(current - previous) / previous`
    as a fraction. `previous` is `None` for the
    first point (no prior value to compare
    against).
    """

    year: int
    period: str
    value: Decimal
    previous: Decimal | None
    growth: Decimal | None
    record_count: int
    month: int | None = None

    def __post_init__(self) -> None:
        for f in ("value", "previous", "growth"):
            v = getattr(self, f)
            if v is not None and not isinstance(v, Decimal):
                raise TimeSeriesAnalyticsError(
                    f"{f} must be Decimal or None; got {type(v).__name__}"
                )


def growth_rates(
    points: Sequence[TrendPoint],
    *,
    field: str = "value",
) -> tuple[GrowthRatePoint, ...]:
    """Compute period-over-period growth rates.

    For each point `i ≥ 1`, the `growth` is
    `(value[i] - value[i-1]) / value[i-1]`.
    For `i = 0`, `growth` is `None` (no prior
    value).

    Parameters
    ----------
    points
        Input time-series (sorted ascending).
    field
        Dataclass attribute to compare. Default
        `"value"`.

    Returns
    -------
    tuple[GrowthRatePoint, ...]
        One row per input point. `previous`
        is `None` for the first row.
    """
    if not points:
        return ()
    if not all(isinstance(p, TrendPoint) for p in points):
        raise TimeSeriesAnalyticsError(
            "points must be a sequence of TrendPoint"
        )

    result: list[GrowthRatePoint] = []
    prev_value: Decimal | None = None
    for point in points:
        value = _to_decimal(getattr(point, field))
        if prev_value is None:
            result.append(
                GrowthRatePoint(
                    year=point.year,
                    period=point.period,
                    value=value,
                    previous=None,
                    growth=None,
                    record_count=point.record_count,
                    month=point.month,
                )
            )
        else:
            if prev_value == 0:
                growth: Decimal | None = None
            else:
                growth = (value - prev_value) / prev_value
            result.append(
                GrowthRatePoint(
                    year=point.year,
                    period=point.period,
                    value=value,
                    previous=prev_value,
                    growth=growth,
                    record_count=point.record_count,
                    month=point.month,
                )
            )
        prev_value = value
    return tuple(result)