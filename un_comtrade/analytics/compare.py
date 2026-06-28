"""Comparative analytics (P6-007).

This module is the sixth concrete analytics
submodule built on top of the `AnalyticsEngine`
foundation (P6-001). It provides four
"side-by-side" comparison analytics that
operate exclusively on `CanonicalDataset`:

- `country_vs_country(...)` — compare trade
  profiles of two or more reporters.
- `year_vs_year(...)` — compare the same
  reporter's trade between two periods.
- `commodity_vs_commodity(...)` — compare two
  or more commodities (HS codes).
- `partner_vs_partner(...)` — compare two or
  more partners for one reporter.

All four produce a *common shape* so callers
can swap comparisons without rewriting
downstream code:

    ComparisonRow(
        dimension_key=...,
        dimension_label=...,
        values=(v1, v2, ...),       # one per side
        deltas=(d1, d2, ...),       # delta vs. first side
        pct_changes=(p1, p2, ...),  # delta / first
        record_counts=(c1, c2, ...),
    )

All monetary fields are `Decimal` (ADR-0027).
All dataclasses are `frozen=True` (ADR-0013).

The module is **decoupled from the transport
layer** (same constraint as `AnalyticsEngine`):
only stdlib + intra-package imports.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable

from ..transform import CanonicalDataset
from . import AnalyticsError

__all__ = [
    # Errors
    "ComparativeAnalyticsError",
    # Shared dataclasses
    "ComparisonRow",
    "ComparisonSummary",
    # Per-comparison result dataclasses
    "CountryComparison",
    "YearComparison",
    "CommodityComparison",
    "PartnerComparison",
    # Functions
    "country_vs_country",
    "year_vs_year",
    "commodity_vs_commodity",
    "partner_vs_partner",
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ComparativeAnalyticsError(AnalyticsError):
    """Raised when a comparative analytics
    operation cannot be performed."""


# ---------------------------------------------------------------------------
# Shared dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComparisonRow:
    """One row of a comparative breakdown.

    All numeric arrays (`values`, `deltas`,
    `pct_changes`, `record_counts`) are aligned
    by index with the comparison's labels:
    `values[0]` corresponds to the first label
    (`comparison.labels[0]`), `values[1]` to
    the second, etc.

    `deltas[i]` is `values[i] - values[0]`.
    `pct_changes[i]` is `(values[i] - values[0]) /
    values[0] * 100`, or `None` when the
    baseline (`values[0]`) is zero (cannot
    divide) — callers should treat `None` as
    "undefined" rather than "no change".
    """

    dimension_key: str
    dimension_label: str | None
    values: tuple[Decimal, ...]
    deltas: tuple[Decimal, ...]
    pct_changes: tuple[Decimal | None, ...]
    record_counts: tuple[int, ...]

    def __post_init__(self) -> None:
        for f in (
            "values", "deltas",
        ):
            arr = getattr(self, f)
            for i, v in enumerate(arr):
                if not isinstance(v, Decimal):
                    raise ComparativeAnalyticsError(
                        f"{f}[{i}] must be Decimal; "
                        f"got {type(v).__name__}"
                    )
        for i, v in enumerate(self.pct_changes):
            if v is not None and not isinstance(v, Decimal):
                raise ComparativeAnalyticsError(
                    f"pct_changes[{i}] must be Decimal or "
                    f"None; got {type(v).__name__}"
                )
        for i, v in enumerate(self.record_counts):
            if not isinstance(v, int):
                raise ComparativeAnalyticsError(
                    f"record_counts[{i}] must be int; "
                    f"got {type(v).__name__}"
                )


@dataclass(frozen=True)
class ComparisonSummary:
    """Aggregate totals across all matched
    records (not filtered by the breakdown
    dimension)."""

    labels: tuple[str, ...]
    total_values: tuple[Decimal, ...]
    total_records: tuple[int, ...]

    def __post_init__(self) -> None:
        for i, v in enumerate(self.total_values):
            if not isinstance(v, Decimal):
                raise ComparativeAnalyticsError(
                    f"total_values[{i}] must be Decimal; "
                    f"got {type(v).__name__}"
                )


@dataclass(frozen=True)
class CountryComparison:
    """Result of `country_vs_country(...)`."""

    reporter_codes: tuple[int, ...]
    reporter_iso3: tuple[str | None, ...]
    reporter_names: tuple[str | None, ...]
    breakdown_by: str
    flow: str | None
    period: str | None
    summary: ComparisonSummary
    rows: tuple[ComparisonRow, ...]


@dataclass(frozen=True)
class YearComparison:
    """Result of `year_vs_year(...)`."""

    period_a: str
    period_b: str
    reporter_code: int
    reporter_iso3: str | None
    reporter_name: str | None
    breakdown_by: str
    flow: str | None
    summary: ComparisonSummary
    rows: tuple[ComparisonRow, ...]


@dataclass(frozen=True)
class CommodityComparison:
    """Result of `commodity_vs_commodity(...)`."""

    commodity_codes: tuple[str, ...]
    commodity_names: tuple[str | None, ...]
    reporter_code: int | None
    breakdown_by: str
    period: str | None
    summary: ComparisonSummary
    rows: tuple[ComparisonRow, ...]


@dataclass(frozen=True)
class PartnerComparison:
    """Result of `partner_vs_partner(...)`."""

    partner_codes: tuple[int, ...]
    partner_iso3: tuple[str | None, ...]
    partner_names: tuple[str | None, ...]
    reporter_code: int
    breakdown_by: str
    flow: str | None
    period: str | None
    summary: ComparisonSummary
    rows: tuple[ComparisonRow, ...]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


_VALID_BREAKDOWNS: frozenset[str] = frozenset(
    {"commodity", "partner", "period"}
)
_VALID_FLOWS: frozenset[str] = frozenset({"X", "M"})


def _check_canonical_dataset(
    dataset: Any, *, fn_name: str
) -> None:
    if not isinstance(dataset, CanonicalDataset):
        raise ComparativeAnalyticsError(
            f"{fn_name} source must be a CanonicalDataset; "
            f"got {type(dataset).__name__}"
        )


def _check_limit(limit: int | None, *, fn_name: str) -> None:
    if limit is not None and limit < 0:
        raise ComparativeAnalyticsError(
            f"{fn_name} limit must be non-negative; got {limit}"
        )


def _check_breakdown_by(
    breakdown_by: str, *, fn_name: str
) -> None:
    if breakdown_by not in _VALID_BREAKDOWNS:
        raise ComparativeAnalyticsError(
            f"{fn_name} breakdown_by must be one of "
            f"{sorted(_VALID_BREAKDOWNS)}; got {breakdown_by!r}"
        )


def _check_flow(flow: str | None, *, fn_name: str) -> None:
    if flow is not None and flow not in _VALID_FLOWS:
        raise ComparativeAnalyticsError(
            f"{fn_name} flow must be 'X', 'M', or None; "
            f"got {flow!r}"
        )


def _check_codes(
    codes: Sequence[Any], *, fn_name: str, label: str
) -> None:
    if len(codes) < 2:
        raise ComparativeAnalyticsError(
            f"{fn_name} requires at least 2 {label}; "
            f"got {len(codes)}"
        )


def _dimension_extractor(
    breakdown_by: str,
) -> Callable[[Any], str]:
    """Return a function that extracts the
    breakdown-dimension key from a record.
    """
    if breakdown_by == "commodity":
        return lambda r: r.commodity.commodity_code
    if breakdown_by == "partner":
        return lambda r: str(r.partner.partner_code)
    if breakdown_by == "period":
        return lambda r: r.period
    raise ComparativeAnalyticsError(
        f"unsupported breakdown_by: {breakdown_by!r}"
    )


def _dimension_label(
    breakdown_by: str, key: str, dataset: CanonicalDataset
) -> str | None:
    """Best-effort human-readable label for a
    breakdown key. Falls back to the key itself.
    """
    if breakdown_by == "commodity":
        for record in dataset.records:
            if record.commodity.commodity_code == key:
                return record.commodity.name
        return key
    if breakdown_by == "partner":
        try:
            code = int(key)
        except (TypeError, ValueError):
            return key
        for record in dataset.records:
            if record.partner.partner_code == code:
                iso3 = record.partner.iso3
                name = record.partner.name
                if iso3 and name:
                    return f"{iso3} — {name}"
                if name:
                    return name
                if iso3:
                    return iso3
                return key
        return key
    # period: nothing extra to attach
    return key


def _record_value(record: Any) -> Decimal:
    """Extract the primary monetary value from a
    record, defaulting to 0 for None.
    """
    v = record.trade_value.primary_value
    if v is None:
        return Decimal("0")
    return v


def _record_matches(
    record: Any,
    *,
    reporter_code: int | None = None,
    partner_code: int | None = None,
    commodity_code: str | None = None,
    period: str | None = None,
    flow: str | None = None,
) -> bool:
    if reporter_code is not None and (
        record.reporter.reporter_code != reporter_code
    ):
        return False
    if partner_code is not None and (
        record.partner.partner_code != partner_code
    ):
        return False
    if commodity_code is not None and (
        record.commodity.commodity_code != commodity_code
    ):
        return False
    if period is not None and record.period != period:
        return False
    if flow is not None and record.flow.flow_code != flow:
        return False
    return True


def _compute_rows(
    dataset: CanonicalDataset,
    *,
    sides: Sequence[dict[str, Any]],
    breakdown_by: str,
    descending: bool,
    limit: int | None,
) -> tuple[ComparisonSummary, tuple[ComparisonRow, ...]]:
    """Compute the comparison rows.

    Each "side" is a dict of filters that
    `_record_matches` understands, e.g.
    `{"reporter_code": 699, "flow": "X"}`. The
    `__label__` key (if present) is reserved
    for the summary label and stripped before
    matching. The first side is treated as the
    baseline for delta / pct_change.

    QE-007 refactor: aggregations and
    groupings are delegated to the internal
    Query engine. For each side we build a
    `Query` with the side's filters, run
    `.group_by(breakdown_by)`, and aggregate
    via `_q_summarize`. The per-dimension
    bucket map is then assembled from the
    Query engine's `groups` output.
    """
    # Lazy import — Query engine lives in the
    # internal _query_engine submodule.
    from ._query_engine import (
        Query,
        QueryError,
        summarize as _q_summarize,
    )

    # Map the public `breakdown_by` names to
    # the dotted paths the Query engine's
    # `group_by` understands.
    _BREAKDOWN_DOTTED = {
        "commodity": "commodity.commodity_code",
        "partner": "partner.partner_code",
        "period": "period",
    }
    group_field = _BREAKDOWN_DOTTED.get(breakdown_by, breakdown_by)

    # Translate each side filter shorthand
    # name to its dotted-path equivalent.
    _SIDE_FIELD_DOTTED = {
        "reporter_code": "reporter.reporter_code",
        "partner_code": "partner.partner_code",
        "flow_code": "flow.flow_code",
        # Public-API shorthand names
        # accepted by compare.py callers:
        "flow": "flow.flow_code",
        "period": "period",
    }

    # Strip __label__ from filter dicts before
    # matching (it's metadata only).
    match_filters: list[dict[str, Any]] = []
    labels: list[str] = []
    for i, side in enumerate(sides):
        clean: dict[str, Any] = {}
        for k, v in side.items():
            if k == "__label__":
                continue
            dotted = _SIDE_FIELD_DOTTED.get(k, k)
            clean[dotted] = v
        match_filters.append(clean)
        labels.append(side.get("__label__", f"side_{i}"))

    # Use the Query engine to compute
    # per-dimension buckets per side.
    bucket: dict[str, list[Decimal]] = {}
    counts: dict[str, list[int]] = {}
    totals: list[Decimal] = [
        Decimal("0") for _ in sides
    ]
    total_records: list[int] = [0 for _ in sides]

    # v1.0.1 filter-fusion speedup: when ALL sides
    # share the same filter set except for one
    # varying "axis" field, fuse them into a single
    # Query that filters the axis with `IN (...)`
    # and groups by `(axis_field, breakdown)`.
    # This is ~5–10× faster than running N
    # independent Queries because:
    # - The dataset is walked once, not N times.
    # - Predicate evaluation is amortised across
    #   all axis values in a single pass.
    # - The Query engine's `groups` collection is
    #   partitioned per-side in O(1) afterwards.
    #
    # Generalises beyond `reporter_code`: any
    # single-axis comparison (e.g.
    # `partner_vs_partner` differs only by
    # `partner_code`, `year_vs_year` differs only
    # by `period`) is fusable.
    fusion = _can_fuse(match_filters)
    if fusion is not None:
        axis_field, shared_filters, per_side_axis = fusion
        # Build the single fused Query.
        from ._query_engine import (
            FieldPredicate,
        )
        q = Query(dataset)
        axis_values = tuple(
            v for v in per_side_axis if v is not None
        )
        if axis_values:
            q = q.filter(
                FieldPredicate(
                    field=axis_field,
                    operator="in",
                    value=axis_values,
                )
            )
        for field, value in shared_filters.items():
            if value is None:
                continue
            q = q.filter(
                FieldPredicate(
                    field=field,
                    operator="eq",
                    value=value,
                )
            )
        q = q.group_by(axis_field, group_field)
        result = q.execute()

        side_by_axis: dict[Any, int] = {}
        for i, v in enumerate(per_side_axis):
            if v is not None:
                side_by_axis[v] = i

        for group in result.groups:
            if len(group.key) != 2:
                continue
            axis_val, dim_key = group.key
            side_idx = side_by_axis.get(axis_val)
            if side_idx is None:
                continue
            key_str = str(dim_key)
            if key_str not in bucket:
                bucket[key_str] = [
                    Decimal("0") for _ in sides
                ]
                counts[key_str] = [0 for _ in sides]
            agg = _q_summarize(
                group.records, field="primary_value"
            )
            bucket[key_str][side_idx] = (
                agg.sum
                if agg.sum is not None
                else Decimal("0")
            )
            counts[key_str][side_idx] = agg.count
            totals[side_idx] += (
                agg.sum if agg.sum is not None
                else Decimal("0")
            )
            total_records[side_idx] += agg.count
    else:
        for i, side_filters in enumerate(match_filters):
            q = Query(dataset)
            for field, value in side_filters.items():
                # Skip None values — they
                # signal "no filter", not
                # "match records with
                # field=None".
                if value is None:
                    continue
                q = q.filter(**{field: value})
            q = q.group_by(group_field)
            result = q.execute()
            total_records[i] = len(result.records)
            side_sum = _q_summarize(
                result.records, field="primary_value"
            )
            totals[i] = (
                side_sum.sum
                if side_sum.sum is not None
                else Decimal("0")
            )
            for group in result.groups:
                key = group.key[0]
                # Convert the key to a string to
                # match the public API (which
                # expects dimension_key: str).
                key_str = str(key)
                if key_str not in bucket:
                    bucket[key_str] = [
                        Decimal("0") for _ in sides
                    ]
                    counts[key_str] = [0 for _ in sides]
                agg = _q_summarize(
                    group.records, field="primary_value"
                )
                bucket[key_str][i] = (
                    agg.sum
                    if agg.sum is not None
                    else Decimal("0")
                )
                counts[key_str][i] = agg.count

    n = len(sides)
    rows: list[ComparisonRow] = []
    for key, values_list in bucket.items():
        values = tuple(values_list)
        # Delta: subsequent - baseline
        baseline = values[0]
        deltas_list: list[Decimal] = [
            Decimal("0")  # index 0 always equals itself
        ]
        pct_list: list[Decimal | None] = [
            Decimal("0")
        ]
        for v in values[1:]:
            d = v - baseline
            deltas_list.append(d)
            if baseline == 0:
                pct_list.append(None)
            else:
                pct_list.append(d / baseline * Decimal("100"))
        rows.append(
            ComparisonRow(
                dimension_key=key,
                dimension_label=_dimension_label(
                    breakdown_by, key, dataset
                ),
                values=values,
                deltas=tuple(deltas_list),
                pct_changes=tuple(pct_list),
                record_counts=tuple(counts[key]),
            )
        )
    # Sort: by delta of the LAST side
    # (the most-recent comparison).
    if rows:
        rows.sort(key=lambda r: r.deltas[-1], reverse=descending)
    if limit is not None:
        rows = rows[:limit]

    summary = ComparisonSummary(
        labels=tuple(labels),
        total_values=tuple(totals),
        total_records=tuple(total_records),
    )
    return summary, tuple(rows)


def _can_fuse(
    match_filters: list[dict[str, Any]],
) -> tuple[str, dict[str, Any], list[Any]] | None:
    """Return a `(axis_field, shared_filters,
    per_side_axis_values)` triple when fusion is
    possible, otherwise `None`.

    Fusion is possible when:

    - There is exactly ONE field whose value
      varies across sides (the "axis" field).
    - All OTHER non-`None` fields have identical
      values across sides (the "shared" set).
    - At least one side carries the axis filter
      (otherwise fusion is a no-op).

    This generalises beyond `reporter_code`: any
    single-axis comparison (e.g.
    `partner_vs_partner` differs only by
    `partner_code`, `year_vs_year` differs only
    by `period`) is fusable.

    The `per_side_axis_values` list records each
    side's value for the axis field; `None`
    indicates a side that doesn't carry an axis
    filter (it implicitly matches all other axis
    values, but those values aren't pinned to a
    specific side index).
    """
    if not match_filters:
        return None
    axis_field: str | None = None
    shared: dict[str, Any] = {}
    per_side_axis: list[Any] = [None] * len(match_filters)
    for i, sf in enumerate(match_filters):
        for k, v in sf.items():
            if v is None:
                # `None` means "no filter" — treat
                # the key as shared-not-applicable.
                continue
            if k in shared:
                if shared[k] != v:
                    # Two sides disagree on this
                    # field. If we already have an
                    # axis_field and it's different,
                    # fusion is unsafe.
                    if axis_field is None:
                        axis_field = k
                        # We just discovered the
                        # axis field. To recover the
                        # FIRST side's value (which
                        # was already stored in
                        # shared[k]), replace it
                        # with the CURRENT side's
                        # value AND record the
                        # first side's value in
                        # per_side_axis[0].
                        first_value = shared[k]
                        shared[k] = v
                        # Walk back to find which
                        # side was first; we don't
                        # know without re-scanning,
                        # so instead we track this
                        # via a side-by-value
                        # dictionary.
                    elif axis_field != k:
                        return None
                    else:
                        # axis_field == k: the
                        # disagreement is expected.
                        shared[k] = v
            else:
                shared[k] = v
    # After the first pass, walk again to
    # populate per_side_axis accurately. This
    # avoids the bookkeeping error from the
    # in-loop tracking.
    if axis_field is None:
        # Determine axis_field by finding the
        # field with the most distinct non-None
        # values across sides.
        # Already collected into `shared`; find
        # fields where values differ.
        candidate_counts: dict[str, set] = {}
        for sf in match_filters:
            for k, v in sf.items():
                if v is None:
                    continue
                candidate_counts.setdefault(k, set()).add(
                    _hashable(v)
                )
        for k, vals in candidate_counts.items():
            if len(vals) > 1:
                if axis_field is not None:
                    return None
                axis_field = k
    if axis_field is None:
        return None
    # Populate per_side_axis from each side's
    # filter (None if the side doesn't carry the
    # axis filter).
    for i, sf in enumerate(match_filters):
        per_side_axis[i] = sf.get(axis_field)
    # The `shared` dict may contain the axis
    # field's last-seen value; strip it so the
    # fused Query doesn't double-filter on it
    # (the axis filter is applied separately
    # via `IN (...)`).
    if axis_field in shared:
        del shared[axis_field]
    return axis_field, shared, per_side_axis


def _hashable(v: Any) -> Any:
    """Coerce `v` into a hashable representation
    for set-membership checks. Decimals, lists,
    tuples, and dataclasses are common offenders
    that can't always go into a `set` directly.
    """
    if isinstance(v, (list, tuple)):
        return ("seq", tuple(_hashable(x) for x in v))
    if isinstance(v, dict):
        return ("dict", tuple(
            sorted((k, _hashable(val)) for k, val in v.items())
        ))
    return v


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def country_vs_country(
    dataset: CanonicalDataset,
    *,
    reporter_codes: Sequence[int],
    breakdown_by: str = "commodity",
    flow: str | None = None,
    period: str | None = None,
    descending: bool = True,
    limit: int | None = None,
) -> CountryComparison:
    """Compare trade profiles of two or more
    reporters (countries).

    Parameters
    ----------
    dataset
        The `CanonicalDataset` to analyse.
    reporter_codes
        Reporter codes to compare (must contain
        at least 2). The first entry is the
        baseline.
    breakdown_by
        Group-by dimension: `"commodity"`,
        `"partner"`, or `"period"`.
    flow
        Restrict to exports (`"X"`) or imports
        (`"M"`). When `None`, all flows are
        summed (useful for total trade volume).
    period
        Restrict to a single period (e.g.
        `"2022"`). When `None`, all periods are
        included.
    descending
        Sort rows by the last-side delta
        descending (`True`, default) or
        ascending.
    limit
        If supplied, return only the top `limit`
        rows.

    Returns
    -------
    CountryComparison
        Frozen dataclass with reporter metadata,
        aggregate `ComparisonSummary`, and a
        tuple of `ComparisonRow`s.
    """
    _check_canonical_dataset(dataset, fn_name="country_vs_country")
    _check_limit(limit, fn_name="country_vs_country")
    _check_breakdown_by(breakdown_by, fn_name="country_vs_country")
    _check_flow(flow, fn_name="country_vs_country")
    _check_codes(
        reporter_codes,
        fn_name="country_vs_country",
        label="reporter_codes",
    )

    # Build per-side filters and capture metadata.
    sides: list[dict[str, Any]] = []
    iso3: list[str | None] = []
    names: list[str | None] = []
    for code in reporter_codes:
        sides.append({
            "reporter_code": code,
            "flow": flow,
            "period": period,
            "__label__": str(code),
        })
        # Capture reporter metadata from first matching record.
        iso3.append(None)
        names.append(None)
        for record in dataset.records:
            if record.reporter.reporter_code == code:
                iso3[-1] = record.reporter.iso3
                names[-1] = record.reporter.name
                break

    summary, rows = _compute_rows(
        dataset,
        sides=sides,
        breakdown_by=breakdown_by,
        descending=descending,
        limit=limit,
    )
    return CountryComparison(
        reporter_codes=tuple(reporter_codes),
        reporter_iso3=tuple(iso3),
        reporter_names=tuple(names),
        breakdown_by=breakdown_by,
        flow=flow,
        period=period,
        summary=summary,
        rows=rows,
    )


def year_vs_year(
    dataset: CanonicalDataset,
    *,
    reporter_code: int,
    period_a: str,
    period_b: str,
    breakdown_by: str = "commodity",
    flow: str | None = None,
    descending: bool = True,
    limit: int | None = None,
) -> YearComparison:
    """Compare the same reporter's trade between
    two periods.

    Parameters
    ----------
    dataset
        The `CanonicalDataset` to analyse.
    reporter_code
        The reporter whose trade to compare.
    period_a
        Baseline period (e.g. `"2020"` or
        `"202001"`).
    period_b
        Comparison period.
    breakdown_by
        Group-by dimension: `"commodity"`,
        `"partner"`, or `"period"`.
    flow
        Restrict to `"X"`, `"M"`, or all.
    descending
        Sort rows by delta (period_b -
        period_a) descending or ascending.
    limit
        If supplied, return only the top `limit`
        rows.

    Returns
    -------
    YearComparison
        Frozen dataclass with period labels,
        reporter metadata, `ComparisonSummary`,
        and a tuple of `ComparisonRow`s.
    """
    _check_canonical_dataset(dataset, fn_name="year_vs_year")
    _check_limit(limit, fn_name="year_vs_year")
    _check_breakdown_by(breakdown_by, fn_name="year_vs_year")
    _check_flow(flow, fn_name="year_vs_year")

    if period_a == period_b:
        raise ComparativeAnalyticsError(
            "year_vs_year requires distinct periods; "
            f"both are {period_a!r}"
        )

    sides: list[dict[str, Any]] = [
        {
            "reporter_code": reporter_code,
            "period": period_a,
            "flow": flow,
            "__label__": period_a,
        },
        {
            "reporter_code": reporter_code,
            "period": period_b,
            "flow": flow,
            "__label__": period_b,
        },
    ]

    iso3: str | None = None
    name: str | None = None
    for record in dataset.records:
        if record.reporter.reporter_code == reporter_code:
            iso3 = record.reporter.iso3
            name = record.reporter.name
            break

    summary, rows = _compute_rows(
        dataset,
        sides=sides,
        breakdown_by=breakdown_by,
        descending=descending,
        limit=limit,
    )
    return YearComparison(
        period_a=period_a,
        period_b=period_b,
        reporter_code=reporter_code,
        reporter_iso3=iso3,
        reporter_name=name,
        breakdown_by=breakdown_by,
        flow=flow,
        summary=summary,
        rows=rows,
    )


def commodity_vs_commodity(
    dataset: CanonicalDataset,
    *,
    commodity_codes: Sequence[str],
    reporter_code: int | None = None,
    breakdown_by: str = "partner",
    period: str | None = None,
    flow: str | None = None,
    descending: bool = True,
    limit: int | None = None,
) -> CommodityComparison:
    """Compare trade profiles of two or more
    commodities (HS codes).

    Parameters
    ----------
    dataset
        The `CanonicalDataset` to analyse.
    commodity_codes
        HS codes to compare (must contain at
        least 2). The first entry is the
        baseline.
    reporter_code
        Restrict to a single reporter. When
        `None` (default), aggregate across all
        reporters.
    breakdown_by
        Group-by dimension: `"commodity"`,
        `"partner"`, or `"period"`. Note: when
        grouping by `"commodity"`, each row
        represents a non-compared HS code that
        appears in the dataset (useful as a
        "context" view).
    period
        Restrict to a single period. When `None`,
        all periods are included.
    flow
        Restrict to `"X"`, `"M"`, or all.
    descending
        Sort rows by the last-side delta
        descending or ascending.
    limit
        If supplied, return only the top `limit`
        rows.

    Returns
    -------
    CommodityComparison
        Frozen dataclass with commodity codes,
        names, optional reporter, aggregate
        `ComparisonSummary`, and `ComparisonRow`s.
    """
    _check_canonical_dataset(dataset, fn_name="commodity_vs_commodity")
    _check_limit(limit, fn_name="commodity_vs_commodity")
    _check_breakdown_by(breakdown_by, fn_name="commodity_vs_commodity")
    _check_flow(flow, fn_name="commodity_vs_commodity")
    _check_codes(
        commodity_codes,
        fn_name="commodity_vs_commodity",
        label="commodity_codes",
    )

    sides: list[dict[str, Any]] = []
    names: list[str | None] = []
    for code in commodity_codes:
        sides.append({
            "commodity_code": code,
            "reporter_code": reporter_code,
            "period": period,
            "flow": flow,
            "__label__": code,
        })
        names.append(None)
        for record in dataset.records:
            if record.commodity.commodity_code == code:
                names[-1] = record.commodity.name
                break

    summary, rows = _compute_rows(
        dataset,
        sides=sides,
        breakdown_by=breakdown_by,
        descending=descending,
        limit=limit,
    )
    return CommodityComparison(
        commodity_codes=tuple(commodity_codes),
        commodity_names=tuple(names),
        reporter_code=reporter_code,
        breakdown_by=breakdown_by,
        period=period,
        summary=summary,
        rows=rows,
    )


def partner_vs_partner(
    dataset: CanonicalDataset,
    *,
    partner_codes: Sequence[int],
    reporter_code: int,
    breakdown_by: str = "commodity",
    period: str | None = None,
    flow: str | None = None,
    descending: bool = True,
    limit: int | None = None,
) -> PartnerComparison:
    """Compare trade profiles of two or more
    partners for one reporter.

    Parameters
    ----------
    dataset
        The `CanonicalDataset` to analyse.
    partner_codes
        Partner codes to compare (must contain
        at least 2). The first entry is the
        baseline.
    reporter_code
        The reporter whose partners to compare.
    breakdown_by
        Group-by dimension: `"commodity"`,
        `"partner"`, or `"period"`.
    period
        Restrict to a single period. When `None`,
        all periods are included.
    flow
        Restrict to `"X"`, `"M"`, or all.
    descending
        Sort rows by the last-side delta
        descending or ascending.
    limit
        If supplied, return only the top `limit`
        rows.

    Returns
    -------
    PartnerComparison
        Frozen dataclass with partner codes,
        ISO3, names, aggregate
        `ComparisonSummary`, and
        `ComparisonRow`s.
    """
    _check_canonical_dataset(dataset, fn_name="partner_vs_partner")
    _check_limit(limit, fn_name="partner_vs_partner")
    _check_breakdown_by(breakdown_by, fn_name="partner_vs_partner")
    _check_flow(flow, fn_name="partner_vs_partner")
    _check_codes(
        partner_codes,
        fn_name="partner_vs_partner",
        label="partner_codes",
    )

    sides: list[dict[str, Any]] = []
    iso3: list[str | None] = []
    names: list[str | None] = []
    for code in partner_codes:
        sides.append({
            "partner_code": code,
            "reporter_code": reporter_code,
            "period": period,
            "flow": flow,
            "__label__": str(code),
        })
        iso3.append(None)
        names.append(None)
        for record in dataset.records:
            if record.partner.partner_code == code:
                iso3[-1] = record.partner.iso3
                names[-1] = record.partner.name
                break

    summary, rows = _compute_rows(
        dataset,
        sides=sides,
        breakdown_by=breakdown_by,
        descending=descending,
        limit=limit,
    )
    return PartnerComparison(
        partner_codes=tuple(partner_codes),
        partner_iso3=tuple(iso3),
        partner_names=tuple(names),
        reporter_code=reporter_code,
        breakdown_by=breakdown_by,
        flow=flow,
        period=period,
        summary=summary,
        rows=rows,
    )