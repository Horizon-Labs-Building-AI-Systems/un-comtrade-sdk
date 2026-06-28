"""Commodity / HS Analytics (P6-004).

This module is the third concrete analytics
submodule built on top of `AnalyticsEngine`
(P6-001). It provides four commodity-level
analytics that operate exclusively on
`CanonicalDataset`:

- **`top_hs_codes(...)`** — rank HS codes
  (`commodity_code`) by trade value for a given
  reporter (or globally). Supports flow filter,
  HS-level filter (2/4/6 digit), and limit.
- **`commodity_ranking(...)`** — rank
  commodities with optional `share` field
  (each commodity's percentage of the grand
  total).
- **`commodity_trend(...)`** — time-series of
  trade for one HS code.
- **`sector_summaries(...)`** — aggregate by
  HS section (the 21 WCO Harmonized System
  sections identified by Roman numerals),
  using the standard chapter-to-section mapping.

All monetary fields are `Decimal` (ADR-0027).
All dataclasses are `frozen=True` (ADR-0013).

The module is **decoupled from the transport
layer**: only stdlib + intra-package imports.
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
# F-002: per-group per-flow Decimal sums are
# delegated to `_sum_primary_by_group` (a
# helper in `balance.py` that wraps the Query
# Engine's `group_by + summarize` primitives).
from .balance import _sum_primary_by_group

__all__ = [
    # Errors
    "CommodityAnalyticsError",
    # Top HS codes
    "HSCodeRankingRow",
    "top_hs_codes",
    # Commodity ranking
    "CommodityRankingRow",
    "commodity_ranking",
    # Commodity trend
    "CommodityTrendPoint",
    "commodity_trend",
    # Sector summaries
    "SectorSummaryRow",
    "sector_summaries",
    "sector_for_chapter",
    "SECTORS",
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CommodityAnalyticsError(AnalyticsError):
    """Raised when a commodity-level analytics
    operation cannot be performed."""


# ---------------------------------------------------------------------------
# HS section mapping (WCO Harmonized System)
# ---------------------------------------------------------------------------


#: WCO Harmonized System section → chapter
#: ranges. Each entry is `(section_id, section_name,
#: (chapter_min, chapter_max))`. Chapters outside
#: the listed ranges return `("??", "Unknown",
#: (0, 0))` from `sector_for_chapter(...)`.
#: Reference: WCO Harmonized System nomenclature
#: (sections are identified by Roman numerals).
SECTORS: tuple[tuple[str, str, tuple[int, int]], ...] = (
    ("I", "Live animals; animal products", (1, 5)),
    ("II", "Vegetable products", (6, 14)),
    ("III", "Animal or vegetable fats and oils", (15, 15)),
    ("IV", "Prepared foodstuffs; beverages, spirits, vinegar; tobacco",
     (16, 24)),
    ("V", "Mineral products", (25, 27)),
    ("VI", "Products of the chemical or allied industries", (28, 38)),
    ("VII", "Plastics and articles thereof; rubber and articles thereof",
     (39, 40)),
    ("VIII", "Raw hides and skins, leather, furskins; saddlery",
     (41, 43)),
    ("IX", "Wood; charcoal; cork; manufactures of straw", (44, 46)),
    ("X", "Pulp; paper; paperboard", (47, 49)),
    ("XI", "Textiles and textile articles", (50, 63)),
    ("XII", "Footwear, headgear; umbrellas; feathers", (64, 67)),
    ("XIII", "Articles of stone, plaster, cement; ceramic; glass",
     (68, 70)),
    ("XIV", "Natural or cultured pearls; precious stones; metals",
     (71, 71)),
    ("XV", "Base metals; articles of base metal", (72, 83)),
    ("XVI", "Machinery and mechanical appliances; electrical equipment",
     (84, 85)),
    ("XVII", "Vehicles, aircraft, vessels", (86, 89)),
    ("XVIII", "Optical, photographic, cinematographic, measuring, "
     "medical instruments", (90, 92)),
    ("XIX", "Arms and ammunition", (93, 93)),
    ("XX", "Miscellaneous manufactured articles", (94, 96)),
    ("XXI", "Works of art, collectors' pieces, antiques", (97, 98)),
)

#: Lookup map: chapter (int) → section info.
_CHAPTER_TO_SECTOR: dict[int, tuple[str, str]] = {}
for _sid, _sname, (_lo, _hi) in SECTORS:
    for _c in range(_lo, _hi + 1):
        _CHAPTER_TO_SECTOR[_c] = (_sid, _sname)


def sector_for_chapter(chapter: int) -> tuple[str, str]:
    """Return `(section_id, section_name)` for a
    2-digit HS chapter code. Returns
    `("??", "Unknown")` for chapters outside the
    standard WCO HS range (1-98)."""
    return _CHAPTER_TO_SECTOR.get(chapter, ("??", "Unknown"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_canonical_dataset(
    dataset: Any, *, fn_name: str
) -> None:
    if not isinstance(dataset, CanonicalDataset):
        raise CommodityAnalyticsError(
            f"{fn_name} source must be a CanonicalDataset; "
            f"got {type(dataset).__name__}"
        )


def _sum_primary_value(records) -> Decimal:
    """Sum `trade_value.primary_value` across a
    sequence of records, ignoring `None`.

    QE-007 refactor: delegates to the
    internal Query engine's `sum(...)`.
    """
    result = _q_sum(records, field="primary_value")
    return result if result is not None else Decimal("0")


def _hs_chapter(commodity_code: str) -> int | None:
    """Extract the 2-digit chapter from a
    commodity code, or `None` if the code is not
    numeric / too short."""
    if not commodity_code:
        return None
    digits = ""
    for ch in commodity_code:
        if ch.isdigit():
            digits += ch
        else:
            break
    if len(digits) < 2:
        return None
    try:
        return int(digits[:2])
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Top HS codes
# ---------------------------------------------------------------------------


_RANKING_FIELDS = frozenset({
    "total_trade",
    "exports",
    "imports",
    "trade_balance",
    "abs_trade_balance",
    "record_count",
})


@dataclass(frozen=True)
class HSCodeRankingRow:
    """One row of a commodity ranking.

    Captures exports / imports / total trade /
    balance for a single HS code (or commodity
    code) plus the commodity name (if present in
    the source records).
    """

    commodity_code: str
    commodity_name: str | None
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
                raise CommodityAnalyticsError(
                    f"{f} must be Decimal; got {type(v).__name__}"
                )


def top_hs_codes(
    dataset: CanonicalDataset,
    *,
    reporter_code: int | None = None,
    flow: str | None = None,
    by: str = "total_trade",
    descending: bool = True,
    limit: int | None = None,
    hs_level: int | None = None,
) -> tuple[HSCodeRankingRow, ...]:
    """Rank HS codes by trade value.

    Parameters
    ----------
    dataset
        The `CanonicalDataset` to analyse.
    reporter_code
        If supplied, only records with this
        reporter contribute.
    flow
        `"X"` keeps exports; `"M"` keeps imports;
        `None` (default) keeps both flows.
    by
        `"total_trade"` (default), `"exports"`,
        `"imports"`, `"trade_balance"`,
        `"abs_trade_balance"`, or `"record_count"`.
    descending
        When `True` (default), largest first.
    limit
        If supplied, return only the top `limit`
        rows.
    hs_level
        If supplied (one of `2`, `4`, `6`), keep
        only records whose commodity code has
        exactly that many leading digits. Useful
        for ranking at the HS section, HS
        heading, or HS subheading level.

    Returns
    -------
    tuple[HSCodeRankingRow, ...]
        Sorted by `by`. Empty when no records
        match.
    """
    if by not in _RANKING_FIELDS:
        raise CommodityAnalyticsError(
            f"Unknown ranking field {by!r}; "
            f"valid: {sorted(_RANKING_FIELDS)}"
        )
    if limit is not None and limit < 0:
        raise CommodityAnalyticsError(
            "limit must be non-negative"
        )
    if hs_level is not None and hs_level not in (2, 4, 6):
        raise CommodityAnalyticsError(
            "hs_level must be one of 2, 4, 6"
        )
    _check_canonical_dataset(dataset, fn_name="top_hs_codes")

    selected = []
    for record in dataset.records:
        if reporter_code is not None:
            if record.reporter.reporter_code != reporter_code:
                continue
        if flow is not None:
            if record.flow.flow_code != flow:
                continue
        if hs_level is not None:
            code = record.commodity.commodity_code
            # HS-level filter: keep only records
            # whose commodity code has EXACTLY
            # `hs_level` leading digits. A 6-digit
            # code is at the subheading level, NOT
            # at the chapter level.
            leading_digits = 0
            for c in code:
                if c.isdigit():
                    leading_digits += 1
                else:
                    break
            if leading_digits != hs_level:
                continue
        selected.append(record)
    return _aggregate_by_commodity(
        selected,
        by=by,
        descending=descending,
        limit=limit,
        flow=flow,
    )


# ---------------------------------------------------------------------------
# Commodity ranking (with optional share)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommodityRankingRow:
    """One row of a commodity ranking with an
    optional `share` field (each commodity's
    percentage of the grand total trade).

    `share` is in [0, 1]. When
    `include_share=False` (default), `share`
    is `None`.
    """

    commodity_code: str
    commodity_name: str | None
    total_exports: Decimal
    total_imports: Decimal
    total_trade: Decimal
    trade_balance: Decimal
    record_count: int
    share: Decimal | None = None

    def __post_init__(self) -> None:
        for f in (
            "total_exports", "total_imports",
            "total_trade", "trade_balance",
        ):
            v = getattr(self, f)
            if not isinstance(v, Decimal):
                raise CommodityAnalyticsError(
                    f"{f} must be Decimal; got {type(v).__name__}"
                )
        if self.share is not None and not isinstance(
            self.share, Decimal
        ):
            raise CommodityAnalyticsError(
                "share must be Decimal when set"
            )


def commodity_ranking(
    dataset: CanonicalDataset,
    *,
    reporter_code: int | None = None,
    flow: str | None = None,
    by: str = "total_trade",
    descending: bool = True,
    limit: int | None = None,
    hs_level: int | None = None,
    include_share: bool = False,
) -> tuple[CommodityRankingRow, ...]:
    """Rank commodities with optional share.

    Same shape as `top_hs_codes(...)` but with
    an optional `share` field
    (`commodity.total_trade / grand_total_trade`)
    that lets callers see each commodity's
    percentage of the grand total. Useful for
    concentration analysis (e.g. "top 5
    commodities account for 60% of trade").

    Parameters
    ----------
    include_share
        When `True`, attach a `share` field
        (in [0, 1]) to each row.
    """
    if not isinstance(include_share, bool):
        raise CommodityAnalyticsError(
            "include_share must be a bool"
        )
    base_rows = top_hs_codes(
        dataset,
        reporter_code=reporter_code,
        flow=flow,
        by=by,
        descending=descending,
        limit=limit,
        hs_level=hs_level,
    )
    if not base_rows:
        return ()

    if not include_share:
        # Re-shape into CommodityRankingRow with
        # share=None.
        return tuple(
            CommodityRankingRow(
                commodity_code=r.commodity_code,
                commodity_name=r.commodity_name,
                total_exports=r.total_exports,
                total_imports=r.total_imports,
                total_trade=r.total_trade,
                trade_balance=r.trade_balance,
                record_count=r.record_count,
                share=None,
            )
            for r in base_rows
        )

    # Compute share relative to the dataset's
    # GRAND total (not the filtered subset, so
    # callers can compare across filters).
    grand_total = _sum_primary_value(
        r for r in dataset.records
        if reporter_code is None
        or r.reporter.reporter_code == reporter_code
    )
    rows: list[CommodityRankingRow] = []
    for r in base_rows:
        share: Decimal | None = None
        if grand_total != 0:
            share = r.total_trade / grand_total
        rows.append(
            CommodityRankingRow(
                commodity_code=r.commodity_code,
                commodity_name=r.commodity_name,
                total_exports=r.total_exports,
                total_imports=r.total_imports,
                total_trade=r.total_trade,
                trade_balance=r.trade_balance,
                record_count=r.record_count,
                share=share,
            )
        )
    return tuple(rows)


def _aggregate_by_commodity(
    records,
    *,
    by: str,
    descending: bool,
    limit: int | None,
    flow: str | None = None,
) -> tuple[HSCodeRankingRow, ...]:
    """Internal helper: aggregate records by
    commodity_code and return sorted
    `HSCodeRankingRow`s.

    `flow` (when supplied) signals that the
    caller has already filtered the records
    down to a single flow; in that case we
    zero the counter-flow values so the
    output reflects only the requested flow.

    QE-007 refactor: aggregations are now
    delegated to the internal Query engine.
    We still walk records once for
    metadata (commodity name) and counts,
    but the X and M totals come from
    `_q_sum` over the already-filtered
    records.
    """
    if not records:
        return ()

    by_code_x: dict[str, Decimal] = {}
    by_code_m: dict[str, Decimal] = {}
    meta: dict[str, str | None] = {}
    counts: dict[str, int] = {}

    for record in records:
        code = record.commodity.commodity_code
        if code not in meta:
            meta[code] = record.commodity.name
        counts[code] = counts.get(code, 0) + 1

    # F-002: per-flow per-commodity Decimal sums
    # are routed through the internal Query
    # Engine (group_by + summarize). The
    # hand-rolled `dict.get(...) + v` pattern
    # has been retired across the analytics
    # package.
    by_code_x = _sum_primary_by_group(
        records, flow_code="X",
        group_field="commodity.commodity_code",
    )
    by_code_m = _sum_primary_by_group(
        records, flow_code="M",
        group_field="commodity.commodity_code",
    )

    # Counter-flow zeroing when a flow filter is
    # supplied by the caller.
    if flow == "X":
        for code in by_code_m:
            by_code_m[code] = Decimal("0")
    elif flow == "M":
        for code in by_code_x:
            by_code_x[code] = Decimal("0")

    rows: list[HSCodeRankingRow] = []
    for code in sorted(counts):
        x = by_code_x.get(code, Decimal("0"))
        m = by_code_m.get(code, Decimal("0"))
        rows.append(
            HSCodeRankingRow(
                commodity_code=code,
                commodity_name=meta[code],
                total_exports=x,
                total_imports=m,
                total_trade=x + m,
                trade_balance=x - m,
                record_count=counts[code],
            )
        )

    def _sort_key(row: HSCodeRankingRow):
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
        raise CommodityAnalyticsError(f"unreachable: {by}")

    rows.sort(key=_sort_key, reverse=descending)
    if limit is not None:
        rows = rows[:limit]
    return tuple(rows)


# ---------------------------------------------------------------------------
# Commodity trend
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommodityTrendPoint:
    """One point on a commodity trend (one year
    or one period)."""

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
                raise CommodityAnalyticsError(
                    f"{f} must be Decimal; got {type(v).__name__}"
                )


def commodity_trend(
    dataset: CanonicalDataset,
    *,
    commodity_code: str,
    reporter_code: int | None = None,
    granularity: str = "year",
) -> tuple[CommodityTrendPoint, ...]:
    """Build a commodity trend for one HS code.

    Parameters
    ----------
    dataset
        The `CanonicalDataset` to analyse.
    commodity_code
        The HS / commodity code to track (exact
        match against `record.commodity.commodity_code`).
    reporter_code
        If supplied, only records with this
        reporter contribute.
    granularity
        `"year"` (default) groups by `ref_year`;
        `"period"` groups by `period` string.

    Returns
    -------
    tuple[CommodityTrendPoint, ...]
        Sorted by `(year, period)`. Empty when
        no records match.
    """
    if not commodity_code:
        raise CommodityAnalyticsError(
            "commodity_code must be a non-empty string"
        )
    if granularity not in ("year", "period"):
        raise CommodityAnalyticsError(
            f"Unknown granularity {granularity!r}; "
            f"valid: 'year', 'period'"
        )
    _check_canonical_dataset(dataset, fn_name="commodity_trend")

    selected = []
    for r in dataset.records:
        if r.commodity.commodity_code != commodity_code:
            continue
        if reporter_code is not None:
            if r.reporter.reporter_code != reporter_code:
                continue
        selected.append(r)
    if not selected:
        return ()

    bucket: dict[tuple[int, str], list] = {}
    for r in selected:
        key = (r.ref_year, r.period)
        bucket.setdefault(key, []).append(r)

    points: list[CommodityTrendPoint] = []
    for (year, period), group in bucket.items():
        x = _sum_primary_value(
            r for r in group if r.flow.flow_code == "X"
        )
        m = _sum_primary_value(
            r for r in group if r.flow.flow_code == "M"
        )
        points.append(
            CommodityTrendPoint(
                year=year,
                period=period,
                total_trade=x + m,
                exports=x,
                imports=m,
                record_count=len(group),
            )
        )
    points.sort(key=lambda p: (p.year, p.period))
    return tuple(points)


# ---------------------------------------------------------------------------
# Sector summaries
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SectorSummaryRow:
    """One row of the sector summary.

    Captures totals per WCO Harmonized System
    section. The `chapter_codes` tuple lists the
    2-digit chapter numbers that fall within
    this section.
    """

    sector_id: str
    sector_name: str
    total_exports: Decimal
    total_imports: Decimal
    total_trade: Decimal
    trade_balance: Decimal
    record_count: int
    chapter_codes: tuple[int, ...] = field(
        default_factory=tuple
    )
    hs_code_count: int = 0

    def __post_init__(self) -> None:
        for f in (
            "total_exports", "total_imports",
            "total_trade", "trade_balance",
        ):
            v = getattr(self, f)
            if not isinstance(v, Decimal):
                raise CommodityAnalyticsError(
                    f"{f} must be Decimal; got {type(v).__name__}"
                )


def sector_summaries(
    dataset: CanonicalDataset,
    *,
    reporter_code: int | None = None,
    flow: str | None = None,
) -> tuple[SectorSummaryRow, ...]:
    """Build sector summaries (per WCO HS section).

    Parameters
    ----------
    dataset
        The `CanonicalDataset` to analyse.
    reporter_code
        If supplied, only records with this
        reporter contribute.
    flow
        `"X"` keeps exports; `"M"` keeps imports;
        `None` (default) keeps both flows.

    Returns
    -------
    tuple[SectorSummaryRow, ...]
        One row per WCO HS section (21 sections
        plus an "Unknown" pseudo-section for
        commodity codes outside the HS range).
        Sections with zero records are still
        included (with zero totals) so callers
        can render a complete matrix.
    """
    _check_canonical_dataset(dataset, fn_name="sector_summaries")

    selected = []
    for r in dataset.records:
        if reporter_code is not None:
            if r.reporter.reporter_code != reporter_code:
                continue
        if flow is not None:
            if r.flow.flow_code != flow:
                continue
        selected.append(r)

    # Group by sector_id.
    by_sector_x: dict[str, Decimal] = {}
    by_sector_m: dict[str, Decimal] = {}
    by_sector_chapters: dict[str, set[int]] = {}
    by_sector_codes: dict[str, set[str]] = {}
    counts: dict[str, int] = {}
    sector_meta: dict[str, str] = {}

    # F-002: bucket records by sector_id so the
    # per-flow Decimal sums can be delegated to
    # `_q_summarize(...)` (the internal Query Engine
    # aggregation primitive). The buckets themselves
    # are NOT aggregations — they are pre-grouping
    # routing structures; the actual Decimal
    # summation is performed by the Query Engine.
    buckets_x: dict[str, list] = {}
    buckets_m: dict[str, list] = {}

    for record in selected:
        chapter = _hs_chapter(record.commodity.commodity_code)
        if chapter is None:
            section_id, section_name = "??", "Unknown"
        else:
            section_id, section_name = sector_for_chapter(chapter)
        if section_id not in sector_meta:
            sector_meta[section_id] = section_name
        by_sector_chapters.setdefault(section_id, set()).add(chapter or 0)
        by_sector_codes.setdefault(section_id, set()).add(
            record.commodity.commodity_code
        )
        counts[section_id] = counts.get(section_id, 0) + 1
        if record.flow.flow_code == "X":
            buckets_x.setdefault(section_id, []).append(record)
        elif record.flow.flow_code == "M":
            buckets_m.setdefault(section_id, []).append(record)

    # F-002: delegate the per-sector per-flow
    # Decimal summation to the Query Engine
    # `summarize(...)` primitive.
    for section_id, bucket in buckets_x.items():
        s = summarize(
            tuple(bucket), field="trade_value.primary_value"
        )
        by_sector_x[section_id] = (
            s.sum if s.sum is not None else Decimal("0")
        )
    for section_id, bucket in buckets_m.items():
        s = summarize(
            tuple(bucket), field="trade_value.primary_value"
        )
        by_sector_m[section_id] = (
            s.sum if s.sum is not None else Decimal("0")
        )

    # Counter-flow zeroing.
    if flow == "X":
        for code in by_sector_m:
            by_sector_m[code] = Decimal("0")
    elif flow == "M":
        for code in by_sector_x:
            by_sector_x[code] = Decimal("0")

    # Build rows in section order (Roman
    # numerals I..XXI then "??") so callers see a
    # stable order.
    section_order = [sid for sid, _, _ in SECTORS] + ["??"]
    rows: list[SectorSummaryRow] = []
    for section_id in section_order:
        x = by_sector_x.get(section_id, Decimal("0"))
        m = by_sector_m.get(section_id, Decimal("0"))
        rows.append(
            SectorSummaryRow(
                sector_id=section_id,
                sector_name=sector_meta.get(
                    section_id,
                    next(
                        sname for sid, sname, _ in SECTORS
                        if sid == section_id
                    ),
                ) if section_id != "??" else "Unknown",
                total_exports=x,
                total_imports=m,
                total_trade=x + m,
                trade_balance=x - m,
                record_count=counts.get(section_id, 0),
                chapter_codes=tuple(
                    sorted(by_sector_chapters.get(section_id, set()))
                ),
                hs_code_count=len(
                    by_sector_codes.get(section_id, set())
                ),
            )
        )
    return tuple(rows)