"""Internal query engine foundation and
filtering engine (QE-001 + QE-002).

This module provides the foundational data
structures for an internal query engine that
operates on `CanonicalDataset`. It is **NOT**
part of the public SDK surface (the leading
underscore in the filename marks it as
internal) and is intended as the starting
point for a fluent query API.

Scope
-----

QE-001 added the foundational types
(`QueryExpression`, `QueryContext`,
`QueryResult`, `Query`). QE-002 extends
that foundation with a filtering engine
(`Predicate` and its concrete subclasses)
plus two fluent methods on `Query`:
`.filter(...)` and `.exclude(...)`. No
grouping, no aggregation, no aggregation-
level operations are introduced in QE-002.

Types in this module
--------------------

- **`QueryExpression`** — base AST marker
  class. Subclassed by `Predicate` for
  filter expressions.
- **`QueryContext`** — frozen execution
  state (dataset + start time + config).
- **`QueryResult`** — frozen result wrapper
  (records + groups + context + finish
  time).
- **`Group`** — frozen record grouping
  (key tuple + records tuple). Populated
  by `Query.group_by(...)` at execute
  time.
- **`AggregationResult`** — frozen
  dataclass holding all five aggregation
  values (sum, count, average, minimum,
  maximum) for one logical group of
  records. Returned by `summarize(...)`.
- **`sum`, `count`, `average`, `minimum`,
  `maximum`** — Decimal-safe aggregation
  functions. Each accepts an iterable of
  `TradeRecord`s plus a `field` argument
  (except `count`, which is optional)
  and returns the aggregated value or
  `None` for empty inputs.
- **`Predicate`** — base class for filter
  expressions. Implements `__call__`,
  `__and__`, `__or__`, `__invert__` for
  composition.
- **`FieldPredicate`** — atomic predicate
  that tests a record field against a value
  via a comparison operator (`eq`, `ne`,
  `lt`, `le`, `gt`, `ge`, `in`, `not_in`).
- **`AndPredicate`**, **`OrPredicate`**,
  **`NotPredicate`** — composition nodes
  (binary AND, binary OR, unary NOT).
- **`Query`** — fluent entry point with
  `.filter(...)`, `.exclude(...)`,
  `.group_by(...)`, and `.execute()`.
  Filtering is applied during `execute()`
  and produces a `QueryResult` whose
  `records` is the **filtered subset** of
  `context.dataset.records`. Grouping is
  applied after filtering and produces a
  `QueryResult` whose `groups` is a tuple
  of `Group`s sorted lexicographically by
  key for determinism.

Decoupling
----------

The module is **decoupled from the transport
layer** (same constraint as
`AnalyticsEngine`): only stdlib +
intra-package imports. It is also
**decoupled from the storage layer**:
takes `CanonicalDataset` directly; no
`un_comtrade.storage` imports.

Public SDK surface
------------------

This module is **internal**. It is not
re-exported from `un_comtrade.analytics`
`__init__.py`. The leading underscore in the
filename signals this. Internal callers
should import via the full path:

    from un_comtrade.analytics._query_engine import (
        Query, QueryContext, QueryResult,
        QueryExpression,
    )
"""

from __future__ import annotations

import builtins
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable, Mapping, Sequence

from ..models.trade import TradeRecord
from ..transform import CanonicalDataset
from . import AnalyticsError

__all__ = [
    "Query",
    "QueryContext",
    "QueryResult",
    "QueryExpression",
    "Predicate",
    "FieldPredicate",
    "AndPredicate",
    "OrPredicate",
    "NotPredicate",
    "Group",
    "AggregationResult",
    "AggregationError",
    "sum",
    "count",
    "average",
    "minimum",
    "maximum",
    "summarize",
    "QueryError",
    # Ordering and windowing (QE-005)
    "SortKey",
]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class QueryError(AnalyticsError):
    """Raised when a query cannot be constructed
    or executed.

    Inherits from `AnalyticsError` so callers
    that already catch `AnalyticsError` keep
    working.
    """


# ---------------------------------------------------------------------------
# QueryExpression (base AST marker)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QueryExpression:
    """Base AST marker for query expressions.

    Subclassed by `Predicate` for filter
    expressions. Future releases may add
    further subclasses (e.g. projection or
    aggregation expressions).

    The class is frozen so any subclass
    inherits immutability by default, matching
    the `AnalyticsEngine` convention
    (ADR-0013, ADR-0030).
    """


# ---------------------------------------------------------------------------
# Predicate (filter expressions)
# ---------------------------------------------------------------------------


# Operators supported by `FieldPredicate`.
_OPERATORS: frozenset[str] = frozenset({
    "eq", "ne", "lt", "le", "gt", "ge", "in", "not_in",
})

# Shorthand → dotted-path translation for
# common trade field names. Lets callers
# write `.filter(reporter_code=699)` instead
# of `.filter(FieldPredicate(field=
# "reporter.reporter_code", ...))`.
_FLAT_TO_DOTTED: dict[str, str] = {
    "reporter_code": "reporter.reporter_code",
    "reporter_iso3": "reporter.iso3",
    "reporter_name": "reporter.name",
    "partner_code": "partner.partner_code",
    "partner_iso3": "partner.iso3",
    "partner_name": "partner.name",
    "flow_code": "flow.flow_code",
    "flow_name": "flow.flow_name",
    "commodity_code": "commodity.commodity_code",
    "commodity_name": "commodity.name",
    "primary_value": "trade_value.primary_value",
    "fob_value": "trade_value.fob_value",
    "cif_value": "trade_value.cif_value",
}


def _resolve_path(path: str) -> str:
    """Translate a (possibly short-form) field
    name to its dotted path. Returns
    `path` unchanged if it is not a
    shorthand or already a dotted path.
    """
    if not path:
        return path
    if "." in path:
        return path
    return _FLAT_TO_DOTTED.get(path, path)


def _get_field(record: TradeRecord, path: str) -> Any:
    """Walk a dotted attribute path on a
    `TradeRecord`.

    Supports both flat field names (with
    shorthand translation) and explicit
    dotted paths. Raises `QueryError` on
    unknown attribute or empty path.

    Examples
    --------

    - `"period"` → `record.period`
    - `"ref_year"` → `record.ref_year`
    - `"reporter_code"` → shorthand →
      `record.reporter.reporter_code`
    - `"flow.flow_code"` →
      `record.flow.flow_code`
    - `"reporter.reporter_code"` →
      `record.reporter.reporter_code`
    - `"commodity.commodity_code"` →
      `record.commodity.commodity_code`
    """
    if not path:
        raise QueryError(
            "FieldPredicate.field must be a non-empty "
            "field name or dotted path"
        )
    resolved = _resolve_path(path)
    if "." not in resolved:
        # Direct attribute lookup.
        if not hasattr(record, resolved):
            raise QueryError(
                f"FieldPredicate.field {path!r} "
                f"(resolved to {resolved!r}) "
                f"references unknown attribute "
                f"{resolved!r}"
            )
        return getattr(record, resolved)
    obj: Any = record
    for part in resolved.split("."):
        if not hasattr(obj, part):
            raise QueryError(
                f"FieldPredicate.field {path!r} "
                f"references unknown attribute "
                f"{part!r}"
            )
        obj = getattr(obj, part)
    return obj


def _apply_operator(
    operator: str, actual: Any, expected: Any
) -> bool:
    """Dispatch a single comparison."""
    try:
        if operator == "eq":
            return actual == expected
        if operator == "ne":
            return actual != expected
        if operator == "lt":
            return actual < expected
        if operator == "le":
            return actual <= expected
        if operator == "gt":
            return actual > expected
        if operator == "ge":
            return actual >= expected
        if operator == "in":
            if not isinstance(expected, (Sequence, frozenset, set)):
                raise QueryError(
                    f"FieldPredicate operator 'in' "
                    f"requires a sequence / set "
                    f"value; got {type(expected).__name__}"
                )
            return actual in expected
        if operator == "not_in":
            if not isinstance(expected, (Sequence, frozenset, set)):
                raise QueryError(
                    f"FieldPredicate operator 'not_in' "
                    f"requires a sequence / set "
                    f"value; got {type(expected).__name__}"
                )
            return actual not in expected
    except TypeError as exc:
        # Comparisons on incompatible types
        # (e.g. Decimal vs str) raise
        # TypeError; treat as "no match" rather
        # than letting the error escape.
        return False
    raise QueryError(
        f"FieldPredicate: unknown operator {operator!r}"
    )


@dataclass(frozen=True)
class Predicate(QueryExpression):
    """Base class for filter predicates.

    A `Predicate` is a callable that, given a
    `TradeRecord`, returns `True` (keep) or
    `False` (drop). Subclasses:

    - **`FieldPredicate`** — atomic
      comparison.
    - **`AndPredicate`** — logical AND.
    - **`OrPredicate`** — logical OR.
    - **`NotPredicate`** — logical NOT.

    Composition operators:

    - `p & q`  →  `AndPredicate(p, q)`
    - `p | q`  →  `OrPredicate(p, q)`
    - `~p`     →  `NotPredicate(p)`
    """

    def __call__(self, record: TradeRecord) -> bool:  # noqa: D401
        """Return `True` if `record` matches."""
        raise NotImplementedError

    def __and__(
        self, other: "Predicate"
    ) -> "AndPredicate":
        return AndPredicate(self, other)

    def __or__(
        self, other: "Predicate"
    ) -> "OrPredicate":
        return OrPredicate(self, other)

    def __invert__(self) -> "NotPredicate":
        return NotPredicate(self)


@dataclass(frozen=True)
class FieldPredicate(Predicate):
    """Atomic predicate that tests a record
    field against a value via a comparison
    operator.

    Parameters
    ----------
    field
        Dotted attribute path on
        `TradeRecord`. Examples:
        `"reporter.reporter_code"`,
        `"flow.flow_code"`, `"period"`,
        `"commodity.commodity_code"`.
    operator
        Comparison operator: `"eq"`, `"ne"`,
        `"lt"`, `"le"`, `"gt"`, `"ge"`,
        `"in"`, `"not_in"`. The `in` and
        `not_in` operators require a sequence
        or set value.
    value
        The expected value to compare against.
    """

    field: str
    operator: str
    value: Any

    def __post_init__(self) -> None:
        if not isinstance(self.field, str) or not self.field:
            raise QueryError(
                "FieldPredicate.field must be a "
                "non-empty string"
            )
        if self.operator not in _OPERATORS:
            raise QueryError(
                f"FieldPredicate.operator must be one of "
                f"{sorted(_OPERATORS)}; got "
                f"{self.operator!r}"
            )

    def __call__(self, record: TradeRecord) -> bool:
        actual = _get_field(record, self.field)
        return _apply_operator(
            self.operator, actual, self.value
        )


@dataclass(frozen=True)
class AndPredicate(Predicate):
    """Logical AND of two predicates."""

    left: Predicate
    right: Predicate

    def __post_init__(self) -> None:
        if not isinstance(self.left, Predicate):
            raise QueryError(
                "AndPredicate.left must be a Predicate; "
                f"got {type(self.left).__name__}"
            )
        if not isinstance(self.right, Predicate):
            raise QueryError(
                "AndPredicate.right must be a Predicate; "
                f"got {type(self.right).__name__}"
            )

    def __call__(self, record: TradeRecord) -> bool:
        return self.left(record) and self.right(record)


@dataclass(frozen=True)
class OrPredicate(Predicate):
    """Logical OR of two predicates."""

    left: Predicate
    right: Predicate

    def __post_init__(self) -> None:
        if not isinstance(self.left, Predicate):
            raise QueryError(
                "OrPredicate.left must be a Predicate; "
                f"got {type(self.left).__name__}"
            )
        if not isinstance(self.right, Predicate):
            raise QueryError(
                "OrPredicate.right must be a Predicate; "
                f"got {type(self.right).__name__}"
            )

    def __call__(self, record: TradeRecord) -> bool:
        return self.left(record) or self.right(record)


@dataclass(frozen=True)
class NotPredicate(Predicate):
    """Logical NOT of a predicate."""

    operand: Predicate

    def __post_init__(self) -> None:
        if not isinstance(self.operand, Predicate):
            raise QueryError(
                "NotPredicate.operand must be a "
                "Predicate; got "
                f"{type(self.operand).__name__}"
            )

    def __call__(self, record: TradeRecord) -> bool:
        return not self.operand(record)


# ---------------------------------------------------------------------------
# QueryContext (immutable execution state)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QueryContext:
    """Immutable execution state for a query.

    Holds the dataset reference, the start
    timestamp, and any caller-supplied
    configuration. The dataclass is
    `frozen=True` (ADR-0013) — once created it
    cannot be mutated, which is required for
    the result to be reproducible from
    `(dataset, config)`.

    Parameters
    ----------
    dataset
        The `CanonicalDataset` the query runs
        against. Validated at construction time
        to fail fast on misuse.
    started_at
        Wall-clock timestamp at which the query
        began executing (UTC, tz-aware).
    config
        Optional caller-supplied configuration
        dict. Defaults to empty.
    """

    dataset: CanonicalDataset
    started_at: datetime
    config: Mapping[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not isinstance(self.dataset, CanonicalDataset):
            raise QueryError(
                "QueryContext.dataset must be a "
                "CanonicalDataset; got "
                f"{type(self.dataset).__name__}"
            )
        if not isinstance(self.started_at, datetime):
            raise QueryError(
                "QueryContext.started_at must be a "
                "datetime; got "
                f"{type(self.started_at).__name__}"
            )
        # Mapping is structurally fine; just
        # ensure we have a true mapping type
        # (not a bare dict subclass that lies
        # about being a Mapping).
        if not isinstance(self.config, Mapping):
            raise QueryError(
                "QueryContext.config must be a "
                "Mapping; got "
                f"{type(self.config).__name__}"
            )


# ---------------------------------------------------------------------------
# Group (record grouping)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Group:
    """One group of records sharing a common
    key.

    `key` is a tuple of values, one per
    grouping field. The tuple length equals
    `Query.group_by(...)`'s argument count.
    Single-column grouping produces
    single-element tuples; multi-column
    grouping produces tuples of the same
    length as the field count.

    `records` is the tuple of `TradeRecord`s
    that share this key. Order within the
    tuple matches the order in the source
    dataset (records are NOT re-sorted within
    a group).

    Groups are produced by
    `Query.group_by(...)` and stored in
    `QueryResult.groups` sorted
    lexicographically by `key` for
    determinism.

    Parameters
    ----------
    key
        Tuple of grouping-key values.
    records
        Tuple of `TradeRecord`s sharing this
        key.
    """

    key: tuple[Any, ...]
    records: tuple[TradeRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.key, tuple):
            raise QueryError(
                "Group.key must be a tuple; got "
                f"{type(self.key).__name__}"
            )
        if not isinstance(self.records, tuple):
            raise QueryError(
                "Group.records must be a tuple; got "
                f"{type(self.records).__name__}"
            )
        # Records must be TradeRecord.
        for i, r in enumerate(self.records):
            if not isinstance(r, TradeRecord):
                raise QueryError(
                    f"Group.records[{i}] must be a "
                    f"TradeRecord; got "
                    f"{type(r).__name__}"
                )


# ---------------------------------------------------------------------------
# SortKey (sort specification)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SortKey:
    """One component of a multi-key sort.

    `field` is a record field path
    (shorthand or dotted). `descending`
    controls whether the sort flips for
    this field. `SortKey`s are produced
    internally by `Query.sort(...)` and
    exposed via `Query.sort_keys` so
    callers can introspect the sort
    specification.

    Parameters
    ----------
    field
        Non-empty field path.
    descending
        When `True`, this field sorts
        descending; otherwise ascending.
    """

    field: str
    descending: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.field, str) or not self.field:
            raise QueryError(
                "SortKey.field must be a non-empty "
                "string"
            )


# ---------------------------------------------------------------------------
# QueryResult (immutable result wrapper)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QueryResult:
    """Immutable result of a `Query.execute()`
    call.

    Holds the filtered records, optionally
    the grouped view, plus the context that
    produced them and the finish timestamp.

    `records` is the filtered subset of
    `context.dataset.records` (or the full
    dataset if no filters were applied).

    `groups` is empty by default. When
    `Query.group_by(...)` is used, `groups`
    is populated with the records grouped
    by the requested fields, sorted
    lexicographically by key.

    Parameters
    ----------
    records
        Tuple of `TradeRecord`s produced by
        the query (filtered, not grouped).
    context
        The `QueryContext` that produced this
        result.
    finished_at
        Wall-clock timestamp at which the
        query finished executing (UTC,
        tz-aware).
    groups
        Tuple of `Group`s. Empty when no
        grouping was applied.
    """

    records: tuple[TradeRecord, ...]
    context: QueryContext
    finished_at: datetime
    groups: tuple[Group, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.context, QueryContext):
            raise QueryError(
                "QueryResult.context must be a "
                "QueryContext; got "
                f"{type(self.context).__name__}"
            )
        if not isinstance(self.finished_at, datetime):
            raise QueryError(
                "QueryResult.finished_at must be a "
                "datetime; got "
                f"{type(self.finished_at).__name__}"
            )
        if not isinstance(self.groups, tuple):
            raise QueryError(
                "QueryResult.groups must be a tuple; "
                f"got {type(self.groups).__name__}"
            )
        # Validate each record.
        for i, record in enumerate(self.records):
            if not isinstance(record, TradeRecord):
                raise QueryError(
                    f"QueryResult.records[{i}] must be "
                    f"a TradeRecord; got "
                    f"{type(record).__name__}"
                )
        # Validate each group.
        for i, group in enumerate(self.groups):
            if not isinstance(group, Group):
                raise QueryError(
                    f"QueryResult.groups[{i}] must be "
                    f"a Group; got "
                    f"{type(group).__name__}"
                )


# ---------------------------------------------------------------------------
# Query (fluent entry point — foundation + filter)
# ---------------------------------------------------------------------------


def _and_all(predicates: list[Predicate]) -> Predicate:
    """Combine a list of predicates with AND.

    Returns the single predicate when the
    list has length 1, otherwise builds a
    left-leaning chain of `AndPredicate`s.

    Raises `QueryError` if `predicates` is
    empty (caller should have guarded).

    Implemented as a manual fold rather than
    `functools.reduce` to keep the analytics
    package's stdlib dependency surface
    minimal — every stdlib import shows up in
    the `TestNoTransportDependency` AST test.
    """
    if not predicates:
        raise QueryError(
            "_and_all requires at least one predicate"
        )
    if len(predicates) == 1:
        return predicates[0]
    result = predicates[0]
    for p in predicates[1:]:
        result = AndPredicate(result, p)
    return result


class Query:
    """Fluent query builder.

    QE-002 added a filtering engine;
    QE-003 adds a grouping engine. Three
    fluent methods are now available:

    - **`.filter(predicate=None, **fields)`** —
      keep records that match the predicate.
      Either pass an explicit `Predicate` or
      keyword arguments that build
      `FieldPredicate`s implicitly (combined
      with AND).
    - **`.exclude(predicate=None, **fields)`** —
      drop records that match the predicate.
      Equivalent to `.filter(~predicate)`.
    - **`.group_by(*fields)`** — group the
      filtered records by one or more
      fields. Each field can be a shorthand
      (`"reporter_code"`) or an explicit
      dotted path (`"reporter.reporter_code"`).
      Multi-column grouping produces tuple
      keys whose length equals the field
      count.

    All fluent methods return a **new**
    `Query` instance — the receiver is never
    mutated (immutable by convention; uses
    `__slots__` with no setters).

    `execute()` runs all filters against the
    dataset's records, optionally groups
    the result, and returns a `QueryResult`
    whose `records` is the filtered subset
    and whose `groups` is the grouping view
    (empty when no grouping was applied).
    The dataset itself is never mutated.

    Future releases will layer additional
    operations on top: `.order_by(*fields)`,
    `.limit(n)`, `.aggregate(metric)`.

    Parameters
    ----------
    dataset
        The `CanonicalDataset` to query.
    config
        Optional caller-supplied configuration
        (becomes `QueryContext.config`).
    predicates
        Optional sequence of predicates
        applied at execute time (kept as a
        tuple for immutability). Empty by
        default.
    group_by_fields
        Optional sequence of field names
        applied at execute time (after
        filtering). Empty by default. Each
        field is a shorthand or dotted path
        walked via `_get_field`.
    """

    __slots__ = (
        "_dataset",
        "_config",
        "_predicates",
        "_group_by_fields",
        "_sort_keys",
        "_limit",
        "_offset",
        "_reverse",
    )

    def __init__(
        self,
        dataset: CanonicalDataset,
        *,
        config: Mapping[str, Any] | None = None,
        predicates: Sequence[Predicate] = (),
        group_by_fields: Sequence[str] = (),
        sort_keys: Sequence[SortKey] = (),
        limit: int | None = None,
        offset: int | None = None,
        reverse: bool = False,
    ) -> None:
        if not isinstance(dataset, CanonicalDataset):
            raise QueryError(
                "Query source must be a CanonicalDataset; "
                f"got {type(dataset).__name__}"
            )
        # Validate config type up front for
        # fail-fast behaviour, matching the
        # `QueryContext.__post_init__` check.
        if config is not None and not isinstance(
            config, Mapping
        ):
            raise QueryError(
                "Query config must be a Mapping or "
                "None; got "
                f"{type(config).__name__}"
            )
        # Validate predicates up front.
        normalised: list[Predicate] = []
        for i, p in enumerate(predicates):
            if not isinstance(p, Predicate):
                raise QueryError(
                    f"Query predicates[{i}] must be a "
                    f"Predicate; got {type(p).__name__}"
                )
            normalised.append(p)
        # Validate group-by fields up front.
        normalised_gb: list[str] = []
        for i, f in enumerate(group_by_fields):
            if not isinstance(f, str) or not f:
                raise QueryError(
                    f"Query group_by_fields[{i}] must be "
                    f"a non-empty string; got "
                    f"{type(f).__name__}"
                )
            normalised_gb.append(f)
        # Validate sort keys up front.
        normalised_sk: list[SortKey] = []
        for i, k in enumerate(sort_keys):
            if not isinstance(k, SortKey):
                raise QueryError(
                    f"Query sort_keys[{i}] must be a "
                    f"SortKey; got {type(k).__name__}"
                )
            normalised_sk.append(k)
        # Validate limit.
        if limit is not None and (
            not isinstance(limit, int) or limit < 0
        ):
            raise QueryError(
                f"Query limit must be a non-negative "
                f"int or None; got {limit!r}"
            )
        # Validate offset.
        if offset is not None and (
            not isinstance(offset, int) or offset < 0
        ):
            raise QueryError(
                f"Query offset must be a non-negative "
                f"int or None; got {offset!r}"
            )
        self._dataset = dataset
        # Copy to a regular dict to detach from
        # any caller-owned mutable mapping.
        self._config: dict[str, Any] = (
            dict(config) if config is not None else {}
        )
        self._predicates: tuple[Predicate, ...] = tuple(
            normalised
        )
        self._group_by_fields: tuple[str, ...] = tuple(
            normalised_gb
        )
        self._sort_keys: tuple[SortKey, ...] = tuple(
            normalised_sk
        )
        self._limit: int | None = limit
        self._offset: int | None = offset
        self._reverse: bool = bool(reverse)

    @property
    def dataset(self) -> CanonicalDataset:
        """Read-only access to the dataset."""
        return self._dataset

    @property
    def config(self) -> Mapping[str, Any]:
        """Read-only access to the configuration
        mapping (a copy is returned)."""
        return dict(self._config)

    @property
    def predicates(self) -> tuple[Predicate, ...]:
        """Read-only access to the predicate
        sequence (a copy is returned).
        """
        return tuple(self._predicates)

    @property
    def group_by_fields(self) -> tuple[str, ...]:
        """Read-only access to the grouping
        fields (a copy is returned).
        """
        return tuple(self._group_by_fields)

    @property
    def sort_keys(self) -> tuple[SortKey, ...]:
        """Read-only access to the sort keys
        (a copy is returned).
        """
        return tuple(self._sort_keys)

    @property
    def limit_value(self) -> int | None:
        """Read-only access to the limit.

        Named `limit_value` to avoid
        shadowing the `.limit(n)` fluent
        method (Python can't have a
        property and a method with the
        same name).
        """
        return self._limit

    @property
    def offset_value(self) -> int | None:
        """Read-only access to the offset.

        Named `offset_value` to avoid
        shadowing the `.offset(n)` fluent
        method.
        """
        return self._offset

    @property
    def reverse_value(self) -> bool:
        """Read-only access to the reverse flag.

        Named `reverse_value` to avoid
        shadowing the `.reverse()` fluent
        method.
        """
        return self._reverse

    # ------------------------------------------------------------------
    # Fluent filter / exclude
    # ------------------------------------------------------------------

    def filter(
        self,
        predicate: Predicate | None = None,
        /,
        **fields: Any,
    ) -> "Query":
        """Add a filter predicate.

        Two call styles:

        1. `q.filter(my_predicate)` — pass an
           explicit `Predicate`. The receiver
           returns a new `Query` with the
           predicate appended.
        2. `q.filter(reporter_code=699,
           flow_code="X")` — pass keyword
           arguments. Each kwarg becomes a
           `FieldPredicate(field=k,
           operator="eq", value=v)`, combined
           with AND. Equivalent to
           `q.filter(FieldPredicate(... ) &
           FieldPredicate(...))`.

        Cannot mix styles: passing both a
        positional predicate and kwargs
        raises `QueryError`.

        Filters compose: a record is kept iff
        it matches **every** predicate added
        across `.filter()` calls (logical
        AND at the Query level).
        """
        if predicate is not None and fields:
            raise QueryError(
                "filter() takes either a positional "
                "predicate or keyword arguments, "
                "not both"
            )
        if predicate is None and not fields:
            raise QueryError(
                "filter() requires a positional "
                "predicate or at least one keyword "
                "argument"
            )
        if predicate is None:
            # Build predicates from kwargs.
            built: list[Predicate] = []
            for k, v in fields.items():
                built.append(
                    FieldPredicate(
                        field=k, operator="eq", value=v
                    )
                )
            predicate = _and_all(built)
        new_predicates = self._predicates + (predicate,)
        return Query(
            self._dataset,
            config=self._config,
            predicates=new_predicates,
            group_by_fields=self._group_by_fields,
            sort_keys=self._sort_keys,
            limit=self._limit,
            offset=self._offset,
            reverse=self._reverse,
        )

    def exclude(
        self,
        predicate: Predicate | None = None,
        /,
        **fields: Any,
    ) -> "Query":
        """Add an inverted filter (exclusion).

        Semantically equivalent to
        `.filter(~predicate)`. A record is
        kept iff it does NOT match the
        predicate.

        Same call styles as `.filter()`.
        """
        if predicate is None and not fields:
            raise QueryError(
                "exclude() requires a positional "
                "predicate or at least one keyword "
                "argument"
            )
        if predicate is None:
            built: list[Predicate] = []
            for k, v in fields.items():
                built.append(
                    FieldPredicate(
                        field=k, operator="eq", value=v
                    )
                )
            predicate = _and_all(built)
        return self.filter(~predicate)

    # ------------------------------------------------------------------
    # Fluent grouping
    # ------------------------------------------------------------------

    def group_by(self, *fields: str) -> "Query":
        """Group filtered records by one or more
        fields.

        Each `field` is a shorthand
        (`"reporter_code"`,
        `"partner_code"`, `"flow_code"`,
        `"commodity_code"`) or an explicit
        dotted path (`"reporter.reporter_code"`,
        `"flow.flow_code"`, etc.) — resolved via
        the same `_get_field` helper that
        `FieldPredicate` uses.

        Multiple fields produce tuple keys
        whose length equals the field count.
        Single-field grouping produces
        single-element tuple keys.

        Calling `.group_by()` with no
        arguments is allowed but produces no
        grouping (equivalent to no
        `.group_by()` call at all). With one
        or more arguments, the resulting
        `QueryResult.groups` is a tuple of
        `Group`s sorted lexicographically by
        `key` for deterministic output.

        Like `.filter()` and `.exclude()`,
        `.group_by()` returns a NEW `Query`
        — the receiver is never mutated.
        """
        normalised: list[str] = []
        for i, f in enumerate(fields):
            if not isinstance(f, str) or not f:
                raise QueryError(
                    f"group_by() argument {i} must be "
                    f"a non-empty string; got "
                    f"{type(f).__name__}"
                )
            normalised.append(f)
        return Query(
            self._dataset,
            config=self._config,
            predicates=self._predicates,
            group_by_fields=tuple(normalised),
            sort_keys=self._sort_keys,
            limit=self._limit,
            offset=self._offset,
            reverse=self._reverse,
        )

    # ------------------------------------------------------------------
    # Fluent ordering and windowing (QE-005)
    # ------------------------------------------------------------------

    def sort(
        self,
        *fields: str,
        descending: bool = False,
    ) -> "Query":
        """Sort filtered records by one or more
        fields (stable sort).

        Each `field` is a shorthand
        (`"primary_value"`,
        `"reporter_code"`, `"period"`, etc.)
        or an explicit dotted path
        (`"trade_value.primary_value"`). The
        sort is **stable**: equal keys
        preserve source order.

        `descending=True` flips the order
        across all fields. Per-field
        direction is not supported in this
        release; future releases may add it.

        Multiple fields produce a
        left-leaning multi-key sort (the
        first field is the primary key, the
        second is the tie-breaker, and so
        on).

        Like `.filter()` and `.group_by()`,
        `.sort()` returns a NEW `Query` —
        the receiver is never mutated.
        """
        if not fields:
            raise QueryError(
                "sort() requires at least one field"
            )
        new_keys: list[SortKey] = []
        for f in fields:
            if not isinstance(f, str) or not f:
                raise QueryError(
                    "sort() field must be a non-empty "
                    "string; got "
                    f"{type(f).__name__}"
                )
            new_keys.append(
                SortKey(field=f, descending=descending)
            )
        return Query(
            self._dataset,
            config=self._config,
            predicates=self._predicates,
            group_by_fields=self._group_by_fields,
            sort_keys=tuple(new_keys),
            limit=self._limit,
            offset=self._offset,
            reverse=self._reverse,
        )

    def limit(self, n: int) -> "Query":
        """Keep only the first `n` records
        (post-sort, post-offset).

        `limit(0)` returns no records.
        `limit(None)` clears the limit.

        Like the other fluent methods,
        `.limit()` returns a NEW `Query`.
        """
        if n is None:
            new_limit: int | None = None
        elif not isinstance(n, int) or n < 0:
            raise QueryError(
                f"limit() requires a non-negative int "
                f"or None; got {n!r}"
            )
        else:
            new_limit = n
        return Query(
            self._dataset,
            config=self._config,
            predicates=self._predicates,
            group_by_fields=self._group_by_fields,
            sort_keys=self._sort_keys,
            limit=new_limit,
            offset=self._offset,
            reverse=self._reverse,
        )

    def offset(self, n: int) -> "Query":
        """Skip the first `n` records
        (post-sort, pre-limit).

        `offset(0)` is a no-op. `offset(None)`
        clears the offset.

        Like the other fluent methods,
        `.offset()` returns a NEW `Query`.
        """
        if n is None:
            new_offset: int | None = None
        elif not isinstance(n, int) or n < 0:
            raise QueryError(
                f"offset() requires a non-negative int "
                f"or None; got {n!r}"
            )
        else:
            new_offset = n
        return Query(
            self._dataset,
            config=self._config,
            predicates=self._predicates,
            group_by_fields=self._group_by_fields,
            sort_keys=self._sort_keys,
            limit=self._limit,
            offset=new_offset,
            reverse=self._reverse,
        )

    def reverse(self) -> "Query":
        """Flip the order of the filtered
        records.

        Applied AFTER sort (so
        `sort("period").reverse()` produces
        reverse-chronological order) and
        BEFORE limit/offset.

        Like the other fluent methods,
        `.reverse()` returns a NEW `Query`.
        """
        return Query(
            self._dataset,
            config=self._config,
            predicates=self._predicates,
            group_by_fields=self._group_by_fields,
            sort_keys=self._sort_keys,
            limit=self._limit,
            offset=self._offset,
            reverse=True,
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self) -> QueryResult:
        """Execute the query and return a result.

        Applies every registered predicate to
        the dataset's records (logical AND at
        the Query level — a record must match
        ALL predicates to be kept). Then
        applies sort, reverse, offset, and
        limit in that order. Finally, if
        grouping was requested via
        `.group_by(...)`, the filtered records
        are partitioned into a tuple of
        `Group`s, sorted lexicographically by
        key for deterministic output.

        The dataset itself is never mutated.
        """
        started_at = datetime.now(timezone.utc)
        context = QueryContext(
            dataset=self._dataset,
            started_at=started_at,
            config=self._config,
        )
        # Apply predicates. A record is kept
        # iff it matches every predicate.
        predicates = self._predicates
        if predicates:
            records = tuple(
                r for r in self._dataset.records
                if all(p(r) for p in predicates)
            )
        else:
            records = tuple(self._dataset.records)
        # Apply sort (stable).
        if self._sort_keys:
            records = _sort_records(
                records, self._sort_keys
            )
        # Apply reverse.
        if self._reverse:
            records = tuple(reversed(records))
        # Apply offset.
        if self._offset:
            records = records[self._offset:]
        # Apply limit.
        if self._limit is not None:
            records = records[: self._limit]
        # Group if requested. Groups are
        # sorted lexicographically by key
        # for deterministic output.
        groups: tuple[Group, ...] = ()
        if self._group_by_fields:
            groups = _group_records(
                records, self._group_by_fields
            )
        finished_at = datetime.now(timezone.utc)
        return QueryResult(
            records=records,
            context=context,
            finished_at=finished_at,
            groups=groups,
        )

    def __repr__(self) -> str:
        return (
            f"Query(dataset={self._dataset.name!r}, "
            f"records={len(self._dataset.records)}, "
            f"predicates={len(self._predicates)}, "
            f"group_by={len(self._group_by_fields)}, "
            f"sort={len(self._sort_keys)}, "
            f"limit={self._limit}, "
            f"offset={self._offset}, "
            f"reverse={self._reverse})"
        )


def _sort_records(
    records: tuple[TradeRecord, ...],
    keys: tuple[SortKey, ...],
) -> tuple[TradeRecord, ...]:
    """Sort records by one or more `SortKey`s.

    The sort is **stable** (Python's
    `sorted()` guarantees this). Per-key
    `descending` flag is honoured by
    reversing the key order for descending
    fields: descending fields are sorted
    first in REVERSE order so the final
    multi-key sort is correct.

    Implementation note: Python's
    `sorted(reverse=True)` reverses ALL
    keys, which doesn't match SQL-style
    per-key ASC/DESC. The classic
    work-around is to sort multiple times
    in reverse priority order, leveraging
    sort stability. We sort descending
    fields first (in reverse priority),
    then ascending fields last — the final
    order is correct because stable sorts
    preserve prior ordering for equal
    keys.
    """
    if not keys:
        return records
    # Validate keys at execution time too
    # (defence in depth — keys are already
    # validated at construction).
    for k in keys:
        if not isinstance(k, SortKey):
            raise QueryError(
                "sort key must be a SortKey; got "
                f"{type(k).__name__}"
            )

    # Split into ascending and descending.
    ascending = [
        k.field for k in keys if not k.descending
    ]
    descending = [
        k.field for k in keys if k.descending
    ]
    # Sort by descending fields first
    # (rightmost has highest priority for
    # tie-breaking). Each step uses stable
    # sort.
    result = records
    for field in reversed(descending):
        result = tuple(sorted(
            result,
            key=lambda r, f=field: _get_field(r, f),
            reverse=True,
        ))
    for field in reversed(ascending):
        result = tuple(sorted(
            result,
            key=lambda r, f=field: _get_field(r, f),
        ))
    return result


def _group_records(
    records: tuple[TradeRecord, ...],
    fields: tuple[str, ...],
) -> tuple[Group, ...]:
    """Group records by one or more fields.

    The grouping key is the tuple of
    field values extracted via `_get_field`
    (which resolves shorthand to dotted
    paths). The result is a tuple of
    `Group`s sorted lexicographically by
    key for determinism.

    A `dict` is used internally as an
    insertion-ordered map (Python 3.7+
    guarantee) so the per-group record
    order matches source order. The final
    sort, however, makes the GROUP order
    deterministic rather than the
    WITHIN-GROUP order.
    """
    if not fields:
        return ()
    buckets: dict[tuple[Any, ...], list[TradeRecord]] = {}
    for record in records:
        key_parts = tuple(
            _get_field(record, f) for f in fields
        )
        if key_parts not in buckets:
            buckets[key_parts] = []
        buckets[key_parts].append(record)
    # Sort groups lexicographically by key.
    sorted_keys = sorted(buckets.keys())
    return tuple(
        Group(key=k, records=tuple(buckets[k]))
        for k in sorted_keys
    )


# ---------------------------------------------------------------------------
# Aggregation engine (QE-004)
# ---------------------------------------------------------------------------


class AggregationError(AnalyticsError):
    """Raised when an aggregation cannot be
    performed.

    Inherits from `AnalyticsError` so callers
    that already catch `AnalyticsError` keep
    working. Subclasses `QueryError` semantically
    (this is the query engine's aggregation
    layer), but is exported separately to keep
    the import surface clean.
    """


@dataclass(frozen=True)
class AggregationResult:
    """Aggregated values for one group of
    records.

    All five values are computed in a single
    pass over the records by `summarize(...)`.
    When the input is empty, `count` is `0`
    and the four `Decimal`-valued fields are
    `None`. When the input contains only
    `None` values for `field`, `count` is
    `0` and the four `Decimal`-valued fields
    are `None` (no values to aggregate).

    Parameters
    ----------
    count
        Number of records contributing to
        this aggregation (always a `int`).
    sum
        Sum of `field` values, or `None` if
        no values contributed.
    average
        Mean of `field` values (Decimal
        division, no float conversion), or
        `None` if no values contributed.
    minimum
        Smallest `field` value, or `None`
        if no values contributed.
    maximum
        Largest `field` value, or `None` if
        no values contributed.
    """

    count: int
    sum: Decimal | None
    average: Decimal | None
    minimum: Decimal | None
    maximum: Decimal | None

    def __post_init__(self) -> None:
        if not isinstance(self.count, int):
            raise AggregationError(
                "AggregationResult.count must be int; "
                f"got {type(self.count).__name__}"
            )
        for f in ("sum", "average", "minimum", "maximum"):
            v = getattr(self, f)
            if v is not None and not isinstance(v, Decimal):
                raise AggregationError(
                    f"AggregationResult.{f} must be "
                    f"Decimal or None; got "
                    f"{type(v).__name__}"
                )


# ---------------------------------------------------------------------------
# Aggregation helpers (internal)
# ---------------------------------------------------------------------------


def _values_for_field(
    records: "Iterable[TradeRecord]",
    field: str,
) -> list[Decimal]:
    """Extract non-None Decimal values for a
    given field across the records.

    Walks the field path (shorthand or
    dotted) and returns a list of `Decimal`
    values, skipping records where the
    field value is `None`. Raises
    `AggregationError` on an unknown field
    (translates `QueryError` from
    `_get_field`) or a non-Decimal,
    non-None value (which would indicate a
    parser bug — every monetary field on
    `TradeRecord` is supposed to be
    `Decimal | None`).
    """
    out: list[Decimal] = []
    for record in records:
        try:
            v = _get_field(record, field)
        except QueryError as exc:
            raise AggregationError(
                f"aggregation field {field!r}: {exc}"
            ) from exc
        if v is None:
            continue
        if not isinstance(v, Decimal):
            raise AggregationError(
                f"aggregation field {field!r} must "
                f"yield Decimal or None; got "
                f"{type(v).__name__}"
            )
        out.append(v)
    return out


# ---------------------------------------------------------------------------
# Aggregation functions (public)
# ---------------------------------------------------------------------------


def sum(
    records: "Iterable[TradeRecord]",
    *,
    field: str,
) -> Decimal | None:
    """Sum a Decimal-valued field across
    records.

    Parameters
    ----------
    records
        Iterable of `TradeRecord`s. May be a
        `tuple[TradeRecord, ...]` (typical
        `Group.records`) or any other
        iterable.
    field
        Field path (shorthand or dotted)
        whose values will be summed.

    Returns
    -------
    Decimal | None
        The exact-Decimal sum, or `None` if
        no records contributed a value
        (empty input or all `None` values).

    Notes
    -----
    Sums use `Decimal("0")` initialization
    and `+=` accumulation — never
    `float()`. The result preserves full
    precision per ADR-0027.
    """
    total = Decimal("0")
    found = False
    for v in _values_for_field(records, field):
        total += v
        found = True
    return total if found else None


def count(
    records: "Iterable[TradeRecord]",
    *,
    field: str | None = None,
) -> int:
    """Count records (or non-None field values).

    Parameters
    ----------
    records
        Iterable of `TradeRecord`s.
    field
        When `None` (default), counts records.
        When supplied, counts records whose
        `field` value is not `None`.

    Returns
    -------
    int
        Always a non-negative integer.

    Notes
    -----
    This is intentionally not Decimal-typed —
    counts are whole numbers.
    """
    if field is None:
        # Use the built-in `sum` (not our
        # aggregation `sum`).
        return builtins.sum(1 for _ in records)
    n = 0
    for record in records:
        try:
            v = _get_field(record, field)
        except QueryError as exc:
            raise AggregationError(
                f"count() field {field!r}: {exc}"
            ) from exc
        if v is not None:
            n += 1
    return n


def average(
    records: "Iterable[TradeRecord]",
    *,
    field: str,
) -> Decimal | None:
    """Average a Decimal-valued field across
    records.

    Parameters
    ----------
    records
        Iterable of `TradeRecord`s.
    field
        Field path (shorthand or dotted).

    Returns
    -------
    Decimal | None
        The Decimal mean, or `None` if no
        records contributed a value.

    Notes
    -----
    Division uses `Decimal` arithmetic
    (preserves full precision per
    ADR-0027). For inputs with N records
    and total `T`, the result is exactly
    `T / N`.
    """
    values = _values_for_field(records, field)
    if not values:
        return None
    total = Decimal("0")
    for v in values:
        total += v
    return total / Decimal(len(values))


def minimum(
    records: "Iterable[TradeRecord]",
    *,
    field: str,
) -> Decimal | None:
    """Smallest Decimal value of a field across
    records.

    Parameters
    ----------
    records
        Iterable of `TradeRecord`s.
    field
        Field path (shorthand or dotted).

    Returns
    -------
    Decimal | None
        The minimum value, or `None` if no
        records contributed a value.
    """
    values = _values_for_field(records, field)
    if not values:
        return None
    return min(values)


def maximum(
    records: "Iterable[TradeRecord]",
    *,
    field: str,
) -> Decimal | None:
    """Largest Decimal value of a field across
    records.

    Parameters
    ----------
    records
        Iterable of `TradeRecord`s.
    field
        Field path (shorthand or dotted).

    Returns
    -------
    Decimal | None
        The maximum value, or `None` if no
        records contributed a value.
    """
    values = _values_for_field(records, field)
    if not values:
        return None
    return max(values)


def summarize(
    records: "Iterable[TradeRecord]",
    *,
    field: str,
) -> AggregationResult:
    """Compute all five aggregations in a single
    pass over the records.

    Equivalent to calling `sum`, `count`,
    `average`, `minimum`, `maximum` separately
    but more efficient (one walk through the
    records rather than five).

    Parameters
    ----------
    records
        Iterable of `TradeRecord`s.
    field
        Field path (shorthand or dotted).

    Returns
    -------
    AggregationResult
        Frozen dataclass with `count`, `sum`,
        `average`, `minimum`, `maximum`.
    """
    # Materialize once so we don't iterate
    # multiple times.
    values = _values_for_field(records, field)
    n = len(values)
    if n == 0:
        return AggregationResult(
            count=0,
            sum=None,
            average=None,
            minimum=None,
            maximum=None,
        )
    total = Decimal("0")
    mn = values[0]
    mx = values[0]
    for v in values:
        total += v
        if v < mn:
            mn = v
        if v > mx:
            mx = v
    return AggregationResult(
        count=n,
        sum=total,
        average=total / Decimal(n),
        minimum=mn,
        maximum=mx,
    )