"""Analytics engine foundation (P6-001).

This module defines the **analytics framework** — a
collection of composable abstractions that operate
**exclusively on `CanonicalDataset`**.

It is intentionally **decoupled from the transport
layer** (`un_comtrade.transport`, `un_comtrade.client`)
and from the parser. Callers feed it a parsed
`CanonicalDataset` (typically produced by the ETL
pipeline + persisted via the Storage layer) and
receive a structured `AnalysisResult`. The engine
does NOT make HTTP calls, does NOT parse raw
upstream payloads, and does NOT depend on
`httpx`.

The framework provides three core abstractions:

- **`Filter`** — selects a subset of records from a
  `CanonicalDataset` according to a predicate.
  Filters are **composable** via `&`, `|`, `~`
  (boolean algebra on the predicate).
- **`Metric`** — computes a single numeric value
  from a `CanonicalDataset` (e.g. `count`,
  `sum_primary_value`, `avg_primary_value`,
  `distinct_reporters`).
- **`Aggregation`** — partitions records by one
  or more fields and computes a `Metric` per
  group.

These are orchestrated by `AnalyticsEngine`, which
threads state through `AnalysisContext` and
returns a frozen `AnalysisResult`.

Per ADR-0027 (`Decimal` preservation), monetary
metrics return `Decimal` (not `float`) so exact
precision is preserved end-to-end.

Per ADR-0013 / ADR-0030, every dataclass in this
module is `frozen=True`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import (
    Any,
    Callable,
    Iterable,
    Mapping,
    Sequence,
)

from ..exceptions import ComtradeError
from ..models.trade import TradeRecord
from ..transform import CanonicalDataset

__all__ = [
    # Exceptions
    "AnalyticsError",
    "MetricError",
    "FilterError",
    "AggregationError",
    # Abstractions
    "Filter",
    "Metric",
    "Aggregation",
    "AggregationRow",
    # Context + result
    "AnalysisContext",
    "AnalysisResult",
    # Engine
    "AnalyticsEngine",
]


# Country-level concrete analytics (P6-002).
# Submodule imports are placed at the BOTTOM of
# this file (after all the core classes are
# defined) to avoid a circular-import problem.
# The country.py / partner.py modules reference
# `AnalyticsError` and `AnalyticsEngine` at
# class-definition time, so the parent's
# `class AnalyticsError` and the
# `class AnalyticsEngine` definitions must run
# BEFORE these submodule imports.


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class AnalyticsError(ComtradeError):
    """Base error for the analytics layer.

    Inherits from `ComtradeError` so callers can
    catch the SDK-wide base class.
    """


class MetricError(AnalyticsError):
    """Raised when a `Metric` cannot compute its value
    (e.g. dataset is empty when the metric requires
    at least one record, or the target field is
    missing)."""


class FilterError(AnalyticsError):
    """Raised when a `Filter` is constructed with
    invalid arguments."""


class AggregationError(AnalyticsError):
    """Raised when an `Aggregation` cannot be applied
    (e.g. an unknown `group_by` field)."""


# ---------------------------------------------------------------------------
# Numeric value type for metrics
# ---------------------------------------------------------------------------


#: Union of numeric types returned by `Metric.compute`.
#: Monetary metrics return `Decimal` (per ADR-0027);
#: count metrics return `int`.
NumericValue = Decimal | int | float


def _coerce_numeric(value: Any) -> NumericValue:
    """Coerce an arbitrary value to a canonical
    numeric type (`Decimal` for non-integer floats,
    `int` for integer-shaped values)."""
    if isinstance(value, bool):
        # bool is a subclass of int — treat as int.
        return int(value)
    if isinstance(value, (Decimal, int)):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    if value is None:
        raise MetricError("Metric returned None")
    try:
        return Decimal(str(value))
    except Exception as exc:  # pragma: no cover
        raise MetricError(
            f"Cannot coerce metric value {value!r} to "
            f"a numeric type: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------


#: Predicate signature for a `Filter`.
FilterPredicate = Callable[[TradeRecord], bool]


@dataclass(frozen=True)
class Filter:
    """Composable record predicate.

    A `Filter` selects a subset of records from a
    `CanonicalDataset` according to its `predicate`.
    Filters are **composable** via the boolean
    operators:

    - `f1 & f2` — conjunction (both must match).
    - `f1 | f2` — disjunction (either must match).
    - `~f` — negation.

    The composition preserves `name` and
    `description` for introspection.

    Pre-built filters are exposed as class-method
    constructors (e.g. `Filter.reporter(699)`,
    `Filter.flow_export()`).
    """

    name: str
    description: str
    predicate: FilterPredicate

    # ----- Boolean composition --------------------------------------

    def __and__(self, other: "Filter") -> "Filter":
        if not isinstance(other, Filter):
            return NotImplemented
        return Filter(
            name=f"({self.name}) AND ({other.name})",
            description=(
                f"{self.description}; "
                f"AND {other.description}"
            ),
            predicate=lambda r: self.predicate(r) and other.predicate(r),
        )

    def __or__(self, other: "Filter") -> "Filter":
        if not isinstance(other, Filter):
            return NotImplemented
        return Filter(
            name=f"({self.name}) OR ({other.name})",
            description=(
                f"{self.description}; "
                f"OR {other.description}"
            ),
            predicate=lambda r: self.predicate(r) or other.predicate(r),
        )

    def __invert__(self) -> "Filter":
        return Filter(
            name=f"NOT ({self.name})",
            description=f"NOT ({self.description})",
            predicate=lambda r: not self.predicate(r),
        )

    # ----- Application ----------------------------------------------

    def apply(
        self, dataset: CanonicalDataset
    ) -> CanonicalDataset:
        """Return a new `CanonicalDataset` containing
        only the records matching this filter.

        The original dataset is NOT mutated. The
        returned dataset inherits `name`,
        `schema_version`, `parser_name`,
        `extracted_at`, `skipped` (carried over),
        `duplicates_removed` (carried over),
        `source_count` (set to the new record
        count), and `metadata` (shallow-copied).
        """
        if not isinstance(dataset, CanonicalDataset):
            raise AnalyticsError(
                f"Filter.apply source must be a CanonicalDataset; "
                f"got {type(dataset).__name__}"
            )
        matched = tuple(r for r in dataset.records if self.predicate(r))
        return CanonicalDataset(
            name=dataset.name,
            records=matched,
            schema_version=dataset.schema_version,
            extracted_at=dataset.extracted_at,
            parser_name=dataset.parser_name,
            skipped=dataset.skipped,
            duplicates_removed=dataset.duplicates_removed,
            source_count=len(matched),
            metadata=dict(dataset.metadata),
        )

    # ----- Pre-built constructors ----------------------------------

    @classmethod
    def reporter(cls, reporter_code: int) -> "Filter":
        """Match records whose reporter code equals
        `reporter_code`."""
        return cls(
            name=f"reporter={reporter_code}",
            description=f"Reporter code equals {reporter_code}",
            predicate=lambda r: r.reporter.reporter_code == reporter_code,
        )

    @classmethod
    def partner(cls, partner_code: int) -> "Filter":
        """Match records whose partner code equals
        `partner_code`."""
        return cls(
            name=f"partner={partner_code}",
            description=f"Partner code equals {partner_code}",
            predicate=lambda r: r.partner.partner_code == partner_code,
        )

    @classmethod
    def flow(cls, flow_code: str) -> "Filter":
        """Match records whose flow code equals
        `flow_code` (`"X"` for export, `"M"` for
        import, etc.)."""
        return cls(
            name=f"flow={flow_code}",
            description=f"Flow code equals {flow_code!r}",
            predicate=lambda r: r.flow.flow_code == flow_code,
        )

    @classmethod
    def flow_export(cls) -> "Filter":
        """Match records with `flow_code == "X"`
        (exports)."""
        return cls.flow("X")

    @classmethod
    def flow_import(cls) -> "Filter":
        """Match records with `flow_code == "M"`
        (imports)."""
        return cls.flow("M")

    @classmethod
    def year(cls, year: int) -> "Filter":
        """Match records with `ref_year == year`."""
        return cls(
            name=f"year={year}",
            description=f"Reference year equals {year}",
            predicate=lambda r: r.ref_year == year,
        )

    @classmethod
    def year_in(cls, *years: int) -> "Filter":
        """Match records whose `ref_year` is in the
        given set of years."""
        year_set = frozenset(years)
        return cls(
            name=f"year IN {{{', '.join(str(y) for y in sorted(year_set))}}}",
            description=(
                f"Reference year is one of "
                f"{sorted(year_set)}"
            ),
            predicate=lambda r: r.ref_year in year_set,
        )

    @classmethod
    def period(cls, period: str) -> "Filter":
        """Match records with `period == period`."""
        return cls(
            name=f"period={period}",
            description=f"Period equals {period!r}",
            predicate=lambda r: r.period == period,
        )

    @classmethod
    def commodity(cls, commodity_code: str) -> "Filter":
        """Match records whose commodity code equals
        `commodity_code`."""
        return cls(
            name=f"commodity={commodity_code}",
            description=(
                f"Commodity code equals {commodity_code!r}"
            ),
            predicate=lambda r: r.commodity.commodity_code == commodity_code,
        )

    @classmethod
    def classification(cls, classification_code: str) -> "Filter":
        """Match records whose classification code
        equals `classification_code`."""
        return cls(
            name=f"classification={classification_code}",
            description=(
                f"Classification code equals "
                f"{classification_code!r}"
            ),
            predicate=(
                lambda r: r.classification_code == classification_code
            ),
        )

    # ----- Custom ---------------------------------------------------

    @classmethod
    def custom(
        cls,
        *,
        name: str,
        description: str = "",
        predicate: FilterPredicate,
    ) -> "Filter":
        """Build a custom `Filter` from an arbitrary
        predicate."""
        if not callable(predicate):
            raise FilterError("predicate must be callable")
        return cls(
            name=name, description=description or name, predicate=predicate
        )

    def __repr__(self) -> str:
        return f"Filter({self.name!r})"


# ---------------------------------------------------------------------------
# Metric
# ---------------------------------------------------------------------------


#: Function signature for a `Metric.compute`.
MetricFunction = Callable[[CanonicalDataset], NumericValue]


@dataclass(frozen=True)
class Metric:
    """A named numeric computation over a
    `CanonicalDataset`.

    A `Metric` is a pure function from
    `CanonicalDataset` to a single numeric value
    (`Decimal` for monetary metrics, `int` for
    counts).

    Pre-built metrics are exposed as class-method
    constructors. Custom metrics can be built via
    `Metric.custom(...)` or by composing existing
    metrics via arithmetic operators:

    ```python
    avg = Metric.sum_primary_value / Metric.count
    ```
    """

    name: str
    description: str
    compute: MetricFunction
    unit: str | None = None

    # ----- Composition ----------------------------------------------

    def __add__(self, other: "Metric") -> "Metric":
        return _compose(self, other, "+")

    def __sub__(self, other: "Metric") -> "Metric":
        return _compose(self, other, "-")

    def __mul__(self, other: "Metric") -> "Metric":
        return _compose(self, other, "*")

    def __truediv__(self, other: "Metric") -> "Metric":
        return _compose(self, other, "/")

    # ----- Pre-built constructors -----------------------------------

    @classmethod
    def count(cls) -> "Metric":
        """Number of records in the dataset."""
        return cls(
            name="count",
            description="Number of records",
            compute=lambda ds: len(ds.records),
            unit="records",
        )

    @classmethod
    def sum_primary_value(cls) -> "Metric":
        """Sum of `trade_value.primary_value` across
        all records. Returns `Decimal` (per
        ADR-0027)."""
        def _compute(ds: CanonicalDataset) -> Decimal:
            total = Decimal("0")
            for r in ds.records:
                v = r.trade_value.primary_value
                if v is None:
                    continue
                total += v
            return total
        return cls(
            name="sum_primary_value",
            description=(
                "Sum of trade_value.primary_value (USD)"
            ),
            compute=_compute,
            unit="USD",
        )

    @classmethod
    def sum_fob_value(cls) -> "Metric":
        """Sum of `trade_value.fob_value`."""
        def _compute(ds: CanonicalDataset) -> Decimal:
            total = Decimal("0")
            for r in ds.records:
                v = r.trade_value.fob_value
                if v is None:
                    continue
                total += v
            return total
        return cls(
            name="sum_fob_value",
            description="Sum of trade_value.fob_value (USD)",
            compute=_compute,
            unit="USD",
        )

    @classmethod
    def sum_cif_value(cls) -> "Metric":
        """Sum of `trade_value.cif_value`."""
        def _compute(ds: CanonicalDataset) -> Decimal:
            total = Decimal("0")
            for r in ds.records:
                v = r.trade_value.cif_value
                if v is None:
                    continue
                total += v
            return total
        return cls(
            name="sum_cif_value",
            description="Sum of trade_value.cif_value (USD)",
            compute=_compute,
            unit="USD",
        )

    @classmethod
    def sum_quantity(cls) -> "Metric":
        """Sum of `quantity.qty` across all records."""
        def _compute(ds: CanonicalDataset) -> Decimal:
            total = Decimal("0")
            for r in ds.records:
                v = r.quantity.qty
                if v is None:
                    continue
                total += v
            return total
        return cls(
            name="sum_quantity",
            description="Sum of quantity.qty",
            compute=_compute,
        )

    @classmethod
    def avg_primary_value(cls) -> "Metric":
        """Mean of `trade_value.primary_value` across
        all records. Returns `Decimal`."""
        def _compute(ds: CanonicalDataset) -> Decimal:
            values = [
                r.trade_value.primary_value
                for r in ds.records
                if r.trade_value.primary_value is not None
            ]
            if not values:
                raise MetricError(
                    "Cannot compute avg_primary_value on "
                    "an empty (or all-null) dataset"
                )
            total = sum(values, start=Decimal("0"))
            return total / Decimal(len(values))
        return cls(
            name="avg_primary_value",
            description=(
                "Mean of trade_value.primary_value (USD)"
            ),
            compute=_compute,
            unit="USD",
        )

    @classmethod
    def distinct_reporters(cls) -> "Metric":
        """Number of distinct reporter codes."""
        def _compute(ds: CanonicalDataset) -> int:
            return len({
                r.reporter.reporter_code for r in ds.records
            })
        return cls(
            name="distinct_reporters",
            description="Count of distinct reporter codes",
            compute=_compute,
            unit="reporters",
        )

    @classmethod
    def distinct_partners(cls) -> "Metric":
        """Number of distinct partner codes."""
        def _compute(ds: CanonicalDataset) -> int:
            return len({
                r.partner.partner_code for r in ds.records
            })
        return cls(
            name="distinct_partners",
            description="Count of distinct partner codes",
            compute=_compute,
            unit="partners",
        )

    @classmethod
    def distinct_commodities(cls) -> "Metric":
        """Number of distinct commodity codes."""
        def _compute(ds: CanonicalDataset) -> int:
            return len({
                r.commodity.commodity_code for r in ds.records
            })
        return cls(
            name="distinct_commodities",
            description="Count of distinct commodity codes",
            compute=_compute,
            unit="commodities",
        )

    @classmethod
    def min_year(cls) -> "Metric":
        """Minimum `ref_year` across all records."""
        def _compute(ds: CanonicalDataset) -> int:
            if not ds.records:
                raise MetricError(
                    "Cannot compute min_year on empty dataset"
                )
            return min(r.ref_year for r in ds.records)
        return cls(
            name="min_year",
            description="Minimum reference year",
            compute=_compute,
        )

    @classmethod
    def max_year(cls) -> "Metric":
        """Maximum `ref_year` across all records."""
        def _compute(ds: CanonicalDataset) -> int:
            if not ds.records:
                raise MetricError(
                    "Cannot compute max_year on empty dataset"
                )
            return max(r.ref_year for r in ds.records)
        return cls(
            name="max_year",
            description="Maximum reference year",
            compute=_compute,
        )

    @classmethod
    def custom(
        cls,
        *,
        name: str,
        description: str = "",
        compute: MetricFunction,
        unit: str | None = None,
    ) -> "Metric":
        """Build a custom `Metric` from an arbitrary
        function."""
        if not callable(compute):
            raise MetricError("compute must be callable")
        return cls(
            name=name,
            description=description or name,
            compute=compute,
            unit=unit,
        )

    def __repr__(self) -> str:
        return f"Metric({self.name!r})"


def _compose(left: Metric, right: Metric, op: str) -> Metric:
    """Compose two metrics via a binary operator."""
    op_symbol = {
        "+": "+",
        "-": "-",
        "*": "×",
        "/": "÷",
    }[op]
    name = f"({left.name} {op_symbol} {right.name})"
    description = (
        f"{left.description} {op_symbol} {right.description}"
    )

    def _compute(ds: CanonicalDataset) -> NumericValue:
        l = left.compute(ds)
        r = right.compute(ds)
        if op == "+":
            return _coerce_numeric(l) + _coerce_numeric(r)
        if op == "-":
            return _coerce_numeric(l) - _coerce_numeric(r)
        if op == "*":
            return _coerce_numeric(l) * _coerce_numeric(r)
        if op == "/":
            r_num = _coerce_numeric(r)
            if r_num == 0:
                raise MetricError(
                    f"Division by zero in {name}: "
                    f"{right.name!r} returned 0"
                )
            return _coerce_numeric(l) / r_num
        raise MetricError(f"Unknown operator: {op!r}")

    return Metric(name=name, description=description, compute=_compute)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


#: Supported group-by field extractors. Maps the
#: short name to a function that pulls the value
#: from a `TradeRecord`.
_GROUP_BY_EXTRACTORS: Mapping[str, Callable[[TradeRecord], Any]] = {
    "reporter_code": lambda r: r.reporter.reporter_code,
    "reporter_iso3": lambda r: r.reporter.iso3,
    "partner_code": lambda r: r.partner.partner_code,
    "partner_iso3": lambda r: r.partner.iso3,
    "flow_code": lambda r: r.flow.flow_code,
    "commodity_code": lambda r: r.commodity.commodity_code,
    "classification_code": lambda r: r.classification_code,
    "ref_year": lambda r: r.ref_year,
    "period": lambda r: r.period,
    "frequency_code": lambda r: r.frequency_code,
    "type_code": lambda r: r.type_code,
    "mot_code": lambda r: r.mot_code,
    "customs_code": lambda r: r.customs_code,
    "edition": lambda r: r.edition,
}


@dataclass(frozen=True)
class AggregationRow:
    """One row of an aggregation result.

    `group_values` is a tuple with one entry per
    group-by field (in the order the fields were
    declared on the parent `Aggregation`). The
    `metric_name` / `metric_value` pair describe
    the metric that was computed for this group.
    """

    group_values: tuple[Any, ...]
    group_labels: tuple[str, ...]
    metric_name: str
    metric_value: NumericValue
    record_count: int


@dataclass(frozen=True)
class Aggregation:
    """Group records by one or more fields, then
    compute a `Metric` per group.

    `group_by` is a tuple of field names drawn from
    `Aggregation.SUPPORTED_FIELDS`. The metric is
    applied to each non-empty group independently.
    """

    name: str
    group_by: tuple[str, ...]
    metric: Metric

    # The set of recognised group-by field names.
    SUPPORTED_FIELDS: tuple[str, ...] = tuple(
        _GROUP_BY_EXTRACTORS.keys()
    )

    def __post_init__(self) -> None:
        unknown = [
            f for f in self.group_by
            if f not in _GROUP_BY_EXTRACTORS
        ]
        if unknown:
            raise AggregationError(
                f"Unknown group_by field(s): {unknown!r}. "
                f"Supported fields: "
                f"{list(self.SUPPORTED_FIELDS)}"
            )
        if not isinstance(self.metric, Metric):
            raise AggregationError(
                f"metric must be a Metric; got "
                f"{type(self.metric).__name__}"
            )

    def apply(
        self, dataset: CanonicalDataset
    ) -> tuple[AggregationRow, ...]:
        """Apply the aggregation to a
        `CanonicalDataset`.

        Returns a tuple of `AggregationRow`s in
        first-seen order of the group keys. Records
        that share all `group_by` field values
        land in the same group.
        """
        if not isinstance(dataset, CanonicalDataset):
            raise AnalyticsError(
                f"Aggregation.apply source must be a "
                f"CanonicalDataset; got "
                f"{type(dataset).__name__}"
            )
        groups: dict[tuple, list[TradeRecord]] = {}
        for record in dataset.records:
            key = tuple(
                _GROUP_BY_EXTRACTORS[field](record)
                for field in self.group_by
            )
            groups.setdefault(key, []).append(record)
        # Compute the metric per group.
        rows: list[AggregationRow] = []
        for key, group_records in groups.items():
            group_dataset = CanonicalDataset(
                name=dataset.name,
                records=tuple(group_records),
                schema_version=dataset.schema_version,
                extracted_at=dataset.extracted_at,
                parser_name=dataset.parser_name,
                skipped=0,
                duplicates_removed=0,
                source_count=len(group_records),
                metadata=dict(dataset.metadata),
            )
            value = self.metric.compute(group_dataset)
            rows.append(
                AggregationRow(
                    group_values=key,
                    group_labels=self.group_by,
                    metric_name=self.metric.name,
                    metric_value=value,
                    record_count=len(group_records),
                )
            )
        return tuple(rows)

    def __repr__(self) -> str:
        fields_str = ", ".join(self.group_by)
        return (
            f"Aggregation({self.name!r}, "
            f"group_by=({fields_str}), "
            f"metric={self.metric.name!r})"
        )


# ---------------------------------------------------------------------------
# AnalysisContext
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AnalysisContext:
    """Shared execution context threaded through
    `AnalyticsEngine.run`.

    Captures warnings, errors, timing, and the
    configuration passed to the engine. Mirrors the
    shape of `PipelineContext` (from
    `un_comtrade.etl`) but is independent — the
    analytics layer is decoupled from the ETL
    layer's runtime.
    """

    analysis_name: str
    config: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    started_at: datetime | None = None
    finished_at: datetime | None = None
    metric_durations: Mapping[str, float] = field(default_factory=dict)
    aggregation_durations: Mapping[str, float] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        if self.started_at is None or self.finished_at is None:
            return 0.0
        return (
            self.finished_at - self.started_at
        ).total_seconds()


# ---------------------------------------------------------------------------
# AnalysisResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AnalysisResult:
    """Frozen output of `AnalyticsEngine.run`.

    Captures:

    - `metric_values` — a mapping from metric name
      to the computed value (per the metric list
      passed to the engine).
    - `aggregation_results` — a mapping from
      aggregation name to a tuple of
      `AggregationRow`s.
    - `record_count` — the number of records in
      the input dataset.
    - `filtered_count` — the number of records that
      survived the filter chain.
    - `context` — the `AnalysisContext` used for
      this run.
    - `duration_seconds` — wall-clock duration.
    """

    analysis_name: str
    metric_values: Mapping[str, NumericValue]
    aggregation_results: Mapping[str, tuple[AggregationRow, ...]]
    record_count: int
    filtered_count: int
    context: AnalysisContext
    duration_seconds: float

    @property
    def warnings(self) -> tuple[str, ...]:
        return self.context.warnings

    @property
    def errors(self) -> tuple[str, ...]:
        return self.context.errors

    def get_metric(self, name: str) -> NumericValue:
        """Return the value of a previously-computed
        metric by name, or raise `AnalyticsError` if
        no such metric exists."""
        if name not in self.metric_values:
            raise AnalyticsError(
                f"No metric named {name!r}; "
                f"available: {list(self.metric_values.keys())}"
            )
        return self.metric_values[name]

    def get_aggregation(
        self, name: str
    ) -> tuple[AggregationRow, ...]:
        """Return the rows of a previously-computed
        aggregation by name, or raise `AnalyticsError`
        if no such aggregation exists."""
        if name not in self.aggregation_results:
            raise AnalyticsError(
                f"No aggregation named {name!r}; "
                f"available: "
                f"{list(self.aggregation_results.keys())}"
            )
        return self.aggregation_results[name]


# ---------------------------------------------------------------------------
# AnalyticsEngine
# ---------------------------------------------------------------------------


class AnalyticsEngine:
    """High-level orchestrator for the analytics layer.

    A single `AnalyticsEngine` instance holds:

    - A **filter chain** — filters are applied in
      order; the resulting dataset is what each
      metric and aggregation sees.
    - A list of **metrics** — each is computed once
      on the filtered dataset.
    - A list of **aggregations** — each is computed
      once on the filtered dataset.

    Construction is purely declarative; no work
    happens until `run(dataset)` is called.

    Usage::

        engine = (
            AnalyticsEngine(name="india_2022_summary")
            .add_filter(Filter.reporter(699))
            .add_filter(Filter.year(2022))
            .add_metric(Metric.count())
            .add_metric(Metric.sum_primary_value())
            .add_aggregation(
                Aggregation(
                    name="by_partner",
                    group_by=("partner_code",),
                    metric=Metric.sum_primary_value(),
                )
            )
        )
        result = engine.run(dataset)
    """

    def __init__(
        self,
        *,
        name: str,
        config: Mapping[str, Any] | None = None,
    ) -> None:
        if not name:
            raise AnalyticsError("AnalyticsEngine.name must be non-empty")
        self._name = name
        self._config: dict[str, Any] = dict(config or {})
        self._filters: list[Filter] = []
        self._metrics: list[Metric] = []
        self._aggregations: list[Aggregation] = []

    # ----- Builder methods ------------------------------------------

    def add_filter(self, filter_: Filter) -> "AnalyticsEngine":
        """Append a `Filter` to the engine's filter
        chain. Returns `self` for chaining."""
        if not isinstance(filter_, Filter):
            raise AnalyticsError(
                f"add_filter expects a Filter; got "
                f"{type(filter_).__name__}"
            )
        self._filters.append(filter_)
        return self

    def add_metric(self, metric: Metric) -> "AnalyticsEngine":
        """Append a `Metric` to be computed against
        the filtered dataset. Returns `self` for
        chaining."""
        if not isinstance(metric, Metric):
            raise AnalyticsError(
                f"add_metric expects a Metric; got "
                f"{type(metric).__name__}"
            )
        self._metrics.append(metric)
        return self

    def add_aggregation(
        self, aggregation: Aggregation
    ) -> "AnalyticsEngine":
        """Append an `Aggregation` to be computed
        against the filtered dataset. Returns `self`
        for chaining."""
        if not isinstance(aggregation, Aggregation):
            raise AnalyticsError(
                f"add_aggregation expects an Aggregation; "
                f"got {type(aggregation).__name__}"
            )
        self._aggregations.append(aggregation)
        return self

    # ----- Read-only properties -------------------------------------

    @property
    def name(self) -> str:
        return self._name

    @property
    def config(self) -> Mapping[str, Any]:
        return dict(self._config)

    @property
    def filters(self) -> tuple[Filter, ...]:
        return tuple(self._filters)

    @property
    def metrics(self) -> tuple[Metric, ...]:
        return tuple(self._metrics)

    @property
    def aggregations(self) -> tuple[Aggregation, ...]:
        return tuple(self._aggregations)

    # ----- Execution -------------------------------------------------

    def run(self, dataset: CanonicalDataset) -> AnalysisResult:
        """Apply the filter chain, compute metrics,
        and run aggregations.

        Returns a frozen `AnalysisResult`. Raises
        `AnalyticsError` if `dataset` is not a
        `CanonicalDataset`. Metric / aggregation
        failures are surfaced as warnings on the
        result's context (rather than re-raised) so
        that one broken metric doesn't abort the
        whole analysis.
        """
        if not isinstance(dataset, CanonicalDataset):
            raise AnalyticsError(
                f"AnalyticsEngine.run source must be a "
                f"CanonicalDataset; got "
                f"{type(dataset).__name__}"
            )

        started = datetime.now(timezone.utc)
        start_perf = time.monotonic()
        warnings: list[str] = []
        errors: list[str] = []
        metric_durations: dict[str, float] = {}
        aggregation_durations: dict[str, float] = {}

        # Apply filter chain.
        current = dataset
        for f in self._filters:
            current = f.apply(current)

        # Compute metrics.
        metric_values: dict[str, NumericValue] = {}
        for m in self._metrics:
            t0 = time.monotonic()
            try:
                metric_values[m.name] = m.compute(current)
            except MetricError as exc:
                warnings.append(
                    f"metric {m.name!r} failed: {exc}"
                )
            except Exception as exc:  # pragma: no cover
                warnings.append(
                    f"metric {m.name!r} raised {type(exc).__name__}: "
                    f"{exc}"
                )
            finally:
                metric_durations[m.name] = time.monotonic() - t0

        # Run aggregations.
        aggregation_results: dict[
            str, tuple[AggregationRow, ...]
        ] = {}
        for a in self._aggregations:
            t0 = time.monotonic()
            try:
                aggregation_results[a.name] = a.apply(current)
            except AggregationError as exc:
                errors.append(
                    f"aggregation {a.name!r} failed: {exc}"
                )
            except Exception as exc:  # pragma: no cover
                errors.append(
                    f"aggregation {a.name!r} raised "
                    f"{type(exc).__name__}: {exc}"
                )
            finally:
                aggregation_durations[a.name] = time.monotonic() - t0

        finished = datetime.now(timezone.utc)
        duration = time.monotonic() - start_perf

        context = AnalysisContext(
            analysis_name=self._name,
            config=dict(self._config),
            warnings=tuple(warnings),
            errors=tuple(errors),
            started_at=started,
            finished_at=finished,
            metric_durations=dict(metric_durations),
            aggregation_durations=dict(aggregation_durations),
        )

        return AnalysisResult(
            analysis_name=self._name,
            metric_values=dict(metric_values),
            aggregation_results=dict(aggregation_results),
            record_count=len(dataset.records),
            filtered_count=len(current.records),
            context=context,
            duration_seconds=duration,
        )

    # ----- Repr -----------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"AnalyticsEngine(name={self._name!r}, "
            f"filters={len(self._filters)}, "
            f"metrics={len(self._metrics)}, "
            f"aggregations={len(self._aggregations)})"
        )


# ---------------------------------------------------------------------------
# Submodule imports — placed at the BOTTOM so the
# core classes above are fully bound before the
# submodules load.
# ---------------------------------------------------------------------------


# Country-level concrete analytics (P6-002).
from .country import (  # noqa: E402
    CountryAnalyticsError,
    CountryRankingRow,
    CountrySummary,
    CountryTrend,
    CountryTrendPoint,
    country_ranking,
    country_summary,
    country_trend,
    total_exports,
    total_imports,
)

# Partner-level concrete analytics (P6-003).
from .partner import (  # noqa: E402
    BilateralSummary,
    PartnerAnalyticsError,
    PartnerBalanceRow,
    PartnerGrowth,
    PartnerGrowthPoint,
    PartnerRankingRow,
    bilateral_summary,
    partner_balance,
    partner_growth,
    top_partners,
)

# Commodity-level concrete analytics (P6-004).
from .commodity import (  # noqa: E402
    CommodityAnalyticsError,
    CommodityRankingRow,
    CommodityTrendPoint,
    HSCodeRankingRow,
    SECTORS,
    SectorSummaryRow,
    commodity_ranking,
    commodity_trend,
    sector_for_chapter,
    sector_summaries,
    top_hs_codes,
)

# Time-series concrete analytics (P6-005).
from .timeseries import (  # noqa: E402
    GrowthRatePoint,
    TimeSeriesAnalyticsError,
    TrendPoint,
    annual_trend,
    cagr,
    growth_rates,
    monthly_trend,
    rolling_average,
)

# Trade-balance concrete analytics (P6-006).
from .balance import (  # noqa: E402
    BalanceAnalyticsError,
    BalanceSummary,
    CommodityBalanceRow,
    CountryBalanceRow,
    PartnerBalanceRow,
    commodity_balance,
    country_balance,
    global_balance,
    partner_trade_balance,
)

# Comparative concrete analytics (P6-007).
from .compare import (  # noqa: E402
    CommodityComparison,
    ComparisonRow,
    ComparisonSummary,
    ComparativeAnalyticsError,
    CountryComparison,
    PartnerComparison,
    YearComparison,
    commodity_vs_commodity,
    country_vs_country,
    partner_vs_partner,
    year_vs_year,
)