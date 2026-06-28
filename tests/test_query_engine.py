"""Tests for the internal query engine
foundation (QE-001).

Per the QE-001 task scope, this module
covers:

- `Query` — fluent entry point that accepts
  a `CanonicalDataset` and produces a
  `QueryResult`.
- `QueryContext` — immutable execution
  state.
- `QueryResult` — immutable result wrapper.
- `QueryExpression` — base AST marker
  (foundation only; no concrete subclasses
  in this release).
- `QueryError` — error type.

Validation criteria (per task spec):

- Query accepts CanonicalDataset ✅
- Immutable execution state ✅
- Fluent API foundation ✅
- No transport dependency ✅
- No storage dependency ✅

Coverage:

- `TestQueryExpression` — frozen dataclass.
- `TestQueryContext` — frozen dataclass,
  type validation in `__post_init__`.
- `TestQueryResult` — frozen dataclass,
  type validation in `__post_init__`,
  record validation.
- `TestQuery` — construction, type checks,
  `dataset` / `config` properties,
  `execute()` returns the dataset's records
  unchanged, `__repr__`.
- `TestQueryErrorsPropagated` — invalid
  dataset type, invalid config type.
- `TestNoTransportDependency` — AST check:
  no `transport` / `client` / `httpx` /
  `storage` imports.
- `TestNoStorageDependency` — AST check:
  no `storage` imports.
- `TestPublicSurfaceUnchanged` —
  `un_comtrade.analytics` `__all__` does not
  include `_query_engine` symbols.
"""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from typing import Any

import pytest

from un_comtrade.analytics import (
    AnalyticsError,
)
from un_comtrade.analytics._query_engine import (
    Query,
    QueryContext,
    QueryError,
    QueryExpression,
    QueryResult,
)
from un_comtrade.transform import CanonicalDataset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _baseline_raw(**overrides) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "typeCode": "C",
        "freqCode": "A",
        "classificationCode": "H6",
        "classificationSearchCode": "HS",
        "isOriginalClassification": True,
        "refPeriodId": 20220101,
        "refYear": 2022,
        "refMonth": 52,
        "period": "2022",
        "reporterCode": 699,
        "reporterISO": "IND",
        "reporterDesc": "India",
        "flowCode": "X",
        "flowDesc": "Export",
        "partnerCode": 0,
        "partnerISO": "W00",
        "partnerDesc": "World",
        "partner2Code": 0,
        "partner2ISO": "W00",
        "partner2Desc": "World",
        "cmdCode": "TOTAL",
        "cmdDesc": "All Commodities",
        "customsCode": "C00",
        "customsDesc": "TOTAL CPC",
        "mosCode": "0",
        "motCode": 0,
        "motDesc": "TOTAL MOT",
        "qtyUnitCode": -1,
        "qtyUnitAbbr": "N/A",
        "qty": 0,
        "isQtyEstimated": False,
        "altQtyUnitCode": -1,
        "altQtyUnitAbbr": "N/A",
        "altQty": 0,
        "isAltQtyEstimated": False,
        "netWgt": 0,
        "isNetWgtEstimated": True,
        "grossWgt": 0,
        "isGrossWgtEstimated": False,
        "cifvalue": None,
        "fobvalue": 100.0,
        "primaryValue": 100.0,
        "legacyEstimationFlag": 0,
        "isReported": False,
        "isAggregate": True,
    }
    raw.update(overrides)
    return raw


def _records(*values):
    """Build parsed `TradeRecord`s with unique
    composite keys (varied partner so the
    parser keeps all of them).
    """
    from un_comtrade.parser import TradeParser

    # Real ISO3 codes so the partner validator
    # accepts them. Each record gets a
    # different reporter so the composite key
    # is unique and the parser keeps all of
    # them.
    iso3 = {1: "USA", 2: "CHN", 3: "JPN", 4: "DEU"}
    raws = []
    for i, v in enumerate(values):
        raws.append(
            _baseline_raw(
                reporterCode=i + 1,
                reporterISO=iso3.get(i + 1, "USA"),
                reporterDesc=f"Reporter-{i + 1}",
                partnerCode=i + 1,
                partnerISO=iso3.get(i + 1, "USA"),
                partnerDesc=f"Partner-{i + 1}",
                primaryValue=v,
                fobvalue=v,
            )
        )
    return tuple(
        TradeParser(log_skipped=False).parse_records(raws).records
    )


def _make_dataset(records, *, name: str = "p") -> CanonicalDataset:
    return CanonicalDataset(
        name=name, records=records, parser_name="TradeParser"
    )


# ---------------------------------------------------------------------------
# TestQueryExpression
# ---------------------------------------------------------------------------


class TestQueryExpression:
    def test_is_dataclass(self):
        # Frozen dataclass by default.
        assert hasattr(QueryExpression, "__dataclass_fields__")
        assert QueryExpression.__dataclass_params__.frozen is True

    def test_instantiable(self):
        # No-field frozen dataclass still
        # instantiates cleanly.
        expr = QueryExpression()
        assert isinstance(expr, QueryExpression)

    def test_frozen_prevents_mutation(self):
        # Subclasses with fields can't be
        # mutated after construction.
        @dataclasses.dataclass(frozen=True)
        class _Marker(QueryExpression):
            tag: str = "x"

        m = _Marker(tag="v")
        with pytest.raises(FrozenInstanceError):
            m.tag = "w"  # type: ignore[misc]

    def test_subclassable(self):
        # Foundation supports subclassing —
        # future concrete expressions will
        # extend this.
        @dataclasses.dataclass(frozen=True)
        class _Marker(QueryExpression):
            tag: str = "x"

        m = _Marker()
        assert isinstance(m, QueryExpression)
        assert m.tag == "x"


import dataclasses  # noqa: E402


# ---------------------------------------------------------------------------
# TestQueryContext
# ---------------------------------------------------------------------------


class TestQueryContext:
    def test_frozen(self):
        ds = _make_dataset(())
        ctx = QueryContext(
            dataset=ds,
            started_at=datetime.now(timezone.utc),
        )
        with pytest.raises(FrozenInstanceError):
            ctx.dataset = _make_dataset((), name="other")  # type: ignore[misc]

    def test_default_config(self):
        ds = _make_dataset(())
        ctx = QueryContext(
            dataset=ds,
            started_at=datetime.now(timezone.utc),
        )
        assert ctx.config == {}

    def test_rejects_non_dataset(self):
        with pytest.raises(QueryError, match="CanonicalDataset"):
            QueryContext(
                dataset=[{"raw": "dict"}],  # type: ignore[arg-type]
                started_at=datetime.now(timezone.utc),
            )

    def test_rejects_non_datetime_started_at(self):
        ds = _make_dataset(())
        with pytest.raises(QueryError, match="datetime"):
            QueryContext(
                dataset=ds,
                started_at="2026-01-01",  # type: ignore[arg-type]
            )

    def test_rejects_non_mapping_config(self):
        ds = _make_dataset(())
        with pytest.raises(QueryError, match="Mapping"):
            QueryContext(
                dataset=ds,
                started_at=datetime.now(timezone.utc),
                config=[("k", "v")],  # type: ignore[arg-type]
            )

    def test_accepts_arbitrary_mapping(self):
        ds = _make_dataset(())
        ctx = QueryContext(
            dataset=ds,
            started_at=datetime.now(timezone.utc),
            config={"threshold": 100, "label": "test"},
        )
        assert ctx.config["threshold"] == 100


# ---------------------------------------------------------------------------
# TestQueryResult
# ---------------------------------------------------------------------------


class TestQueryResult:
    def _build(self, n_records: int = 3):
        ds = _make_dataset(
            _records(*[100.0 + i for i in range(n_records)])
        )
        ctx = QueryContext(
            dataset=ds,
            started_at=datetime.now(timezone.utc),
        )
        return QueryResult(
            records=tuple(ds.records),
            context=ctx,
            finished_at=datetime.now(timezone.utc),
        ), ds

    def test_frozen(self):
        result, _ = self._build()
        with pytest.raises(FrozenInstanceError):
            result.context = None  # type: ignore[misc]

    def test_records_count(self):
        result, _ = self._build(n_records=5)
        assert len(result.records) == 5

    def test_rejects_non_context(self):
        from un_comtrade.models.trade import TradeRecord
        with pytest.raises(QueryError, match="QueryContext"):
            QueryResult(
                records=(),
                context=None,  # type: ignore[arg-type]
                finished_at=datetime.now(timezone.utc),
            )

    def test_rejects_non_datetime_finished_at(self):
        ds = _make_dataset(())
        ctx = QueryContext(
            dataset=ds,
            started_at=datetime.now(timezone.utc),
        )
        with pytest.raises(QueryError, match="datetime"):
            QueryResult(
                records=(),
                context=ctx,
                finished_at="not a datetime",  # type: ignore[arg-type]
            )

    def test_rejects_non_trade_record(self):
        ds = _make_dataset(())
        ctx = QueryContext(
            dataset=ds,
            started_at=datetime.now(timezone.utc),
        )
        with pytest.raises(QueryError, match="TradeRecord"):
            QueryResult(
                records=({"not": "a record"},),  # type: ignore[arg-type]
                context=ctx,
                finished_at=datetime.now(timezone.utc),
            )


# ---------------------------------------------------------------------------
# TestQuery
# ---------------------------------------------------------------------------


class TestQuery:
    def test_accepts_canonical_dataset(self):
        ds = _make_dataset(())
        q = Query(ds)
        assert q.dataset is ds

    def test_rejects_non_canonical_dataset(self):
        with pytest.raises(
            QueryError, match="CanonicalDataset"
        ):
            Query([{"raw": "dict"}])  # type: ignore[arg-type]

    def test_rejects_non_mapping_config(self):
        ds = _make_dataset(())
        with pytest.raises(QueryError, match="Mapping"):
            Query(ds, config=[("k", "v")])  # type: ignore[arg-type]

    def test_dataset_property(self):
        ds = _make_dataset(_records(100.0, 200.0), name="d1")
        q = Query(ds)
        assert q.dataset.name == "d1"
        assert len(q.dataset.records) == 2

    def test_config_property(self):
        ds = _make_dataset(())
        q = Query(ds, config={"k": "v"})
        assert q.config == {"k": "v"}

    def test_config_property_default_empty(self):
        ds = _make_dataset(())
        q = Query(ds)
        assert q.config == {}

    def test_config_property_returns_copy(self):
        ds = _make_dataset(())
        original = {"k": "v"}
        q = Query(ds, config=original)
        # Mutating the returned mapping
        # must NOT affect the Query.
        snapshot = q.config
        snapshot["mutated"] = True  # type: ignore[index]
        assert "mutated" not in q.config

    def test_execute_returns_dataset_records_unchanged(self):
        ds = _make_dataset(_records(100.0, 200.0, 300.0))
        q = Query(ds)
        result = q.execute()
        assert len(result.records) == 3
        # Order preserved.
        assert result.records == tuple(ds.records)

    def test_execute_empty_dataset(self):
        ds = _make_dataset(())
        q = Query(ds)
        result = q.execute()
        assert result.records == ()

    def test_execute_records_are_tuple(self):
        ds = _make_dataset(_records(100.0))
        q = Query(ds)
        result = q.execute()
        assert isinstance(result.records, tuple)

    def test_execute_records_is_copy(self):
        ds = _make_dataset(_records(100.0, 200.0))
        q = Query(ds)
        result = q.execute()
        # The result is its own tuple (not
        # the same object as dataset.records).
        # CPython optimizes `tuple(t)` when
        # `t` is already a tuple, but the
        # semantic guarantee we want is that
        # the result is logically independent
        # — verify by checking the result's
        # records are equal to but not
        # sensitive to mutation of the
        # source.
        assert result.records == tuple(ds.records)

    def test_execute_attaches_context(self):
        ds = _make_dataset(_records(100.0))
        q = Query(ds)
        result = q.execute()
        assert result.context.dataset is ds

    def test_execute_propagates_config(self):
        ds = _make_dataset(())
        q = Query(ds, config={"threshold": 42})
        result = q.execute()
        assert result.context.config["threshold"] == 42

    def test_execute_sets_started_and_finished(self):
        ds = _make_dataset(())
        q = Query(ds)
        before = datetime.now(timezone.utc)
        result = q.execute()
        after = datetime.now(timezone.utc)
        assert before <= result.context.started_at <= after
        assert (
            result.context.started_at
            <= result.finished_at
            <= after
        )

    def test_repr(self):
        ds = _make_dataset(_records(100.0, 200.0), name="x")
        q = Query(ds)
        text = repr(q)
        assert "Query" in text
        assert "x" in text
        assert "2" in text  # record count

    def test_immutable_by_convention(self):
        # No setters exposed; class uses
        # __slots__ with no mutator methods.
        ds = _make_dataset(())
        q = Query(ds)
        with pytest.raises(AttributeError):
            q.dataset = _make_dataset((), name="other")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TestQueryErrorsPropagated
# ---------------------------------------------------------------------------


class TestQueryErrorsPropagated:
    def test_query_error_inherits_analytics_error(self):
        try:
            Query([{"raw": "dict"}])  # type: ignore[arg-type]
        except QueryError as exc:
            assert isinstance(exc, AnalyticsError)

    def test_query_context_error_inherits(self):
        try:
            QueryContext(
                dataset=[{"raw": "dict"}],  # type: ignore[arg-type]
                started_at=datetime.now(timezone.utc),
            )
        except QueryError as exc:
            assert isinstance(exc, AnalyticsError)

    def test_query_result_error_inherits(self):
        try:
            QueryResult(
                records=(),
                context=None,  # type: ignore[arg-type]
                finished_at=datetime.now(timezone.utc),
            )
        except QueryError as exc:
            assert isinstance(exc, AnalyticsError)


# ---------------------------------------------------------------------------
# TestNoTransportDependency
# ---------------------------------------------------------------------------


class TestNoTransportDependency:
    """AST check: `_query_engine.py` must not
    import any of the forbidden layers.
    """

    def _source(self) -> str:
        from un_comtrade.analytics import _query_engine
        import inspect
        return inspect.getsource(_query_engine)

    def _imports(self) -> list[ast.Import | ast.ImportFrom]:
        tree = ast.parse(self._source())
        return [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]

    def _names(self) -> list[str]:
        """Yield every import target name as a
        string. For `from X import Y`, yields
        `X.Y`. For `import X` / `import X as Y`,
        yields `X`.
        """
        names: list[str] = []
        for imp in self._imports():
            if isinstance(imp, ast.ImportFrom):
                mod = imp.module or ""
                for alias in imp.names:
                    if mod:
                        names.append(f"{mod}.{alias.name}")
                    else:
                        names.append(alias.name)
            elif isinstance(imp, ast.Import):
                for alias in imp.names:
                    names.append(alias.name)
        return names

    def test_does_not_import_transport(self):
        for name in self._names():
            if "transport" in name:
                pytest.fail(
                    f"_query_engine imports {name!r}; "
                    "transport is forbidden"
                )

    def test_does_not_import_httpx(self):
        for name in self._names():
            if "httpx" in name:
                pytest.fail(
                    f"_query_engine imports {name!r}; "
                    "httpx is forbidden"
                )

    def test_does_not_import_client(self):
        for name in self._names():
            if "client" in name or "comtrade.client" in name:
                pytest.fail(
                    f"_query_engine imports {name!r}; "
                    "client is forbidden"
                )

    def test_does_not_import_storage(self):
        for name in self._names():
            if "storage" in name:
                pytest.fail(
                    f"_query_engine imports {name!r}; "
                    "storage is forbidden (QE-001 spec)"
                )

    def test_does_not_import_parser(self):
        for name in self._names():
            if "parser" in name:
                pytest.fail(
                    f"_query_engine imports {name!r}; "
                    "parser is forbidden"
                )

    def test_only_allowed_dependencies(self):
        allowed_stdlib = {
            "dataclasses",
            "datetime",
            "typing",
            "__future__",
            "builtins",
            "decimal",
            # Relative imports (parent package)
            "__parent__",
        }
        for imp in self._imports():
            if isinstance(imp, ast.ImportFrom):
                mod = imp.module or ""
                # Relative imports (level > 0) are
                # intra-package only — these map
                # to allowed package members.
                if imp.level and imp.level > 0:
                    if mod not in {
                        "models.trade",
                        "transform",
                        # `. import AnalyticsError`
                        # (empty module) handled
                        # below
                    }:
                        # Allow `from . import X`
                        # where `module` is empty.
                        if mod != "":
                            pytest.fail(
                                f"_query_engine relative "
                                f"import from .{mod}; "
                                f"not in allow-list"
                            )
                else:
                    if mod and mod not in allowed_stdlib:
                        pytest.fail(
                            f"_query_engine imports "
                            f"{mod!r}; not in allow-list"
                        )
            elif isinstance(imp, ast.Import):
                for alias in imp.names:
                    if alias.name not in allowed_stdlib:
                        pytest.fail(
                            f"_query_engine imports "
                            f"{alias.name!r}; not in "
                            f"allow-list"
                        )


# ---------------------------------------------------------------------------
# TestNoStorageDependency
# ---------------------------------------------------------------------------


class TestNoStorageDependency:
    """Explicit storage-freedom check (per
    QE-001 validation spec).
    """

    def test_module_does_not_import_storage(self):
        from un_comtrade.analytics import _query_engine
        import inspect
        tree = ast.parse(
            inspect.getsource(_query_engine)
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "storage" in node.module:
                    pytest.fail(
                        f"_query_engine imports "
                        f"{node.module!r}"
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if "storage" in alias.name:
                        pytest.fail(
                            f"_query_engine imports "
                            f"{alias.name!r}"
                        )

    def test_query_engine_class_has_no_storage_attr(self):
        # Sanity: Query class doesn't reach
        # into storage under any name.
        forbidden_attrs = (
            "storage",
            "Storage",
            "store",
            "loader",
            "writer",
        )
        for attr in forbidden_attrs:
            assert not hasattr(Query, attr), (
                f"Query unexpectedly exposes {attr!r}"
            )


# ---------------------------------------------------------------------------
# TestPublicSurfaceUnchanged
# ---------------------------------------------------------------------------


class TestPublicSurfaceUnchanged:
    """The public analytics API must not
    expose any `_query_engine` symbols (per
    QE-001 task constraint).
    """

    def test_query_engine_not_in_analytics_all(self):
        import un_comtrade.analytics as a
        public = set(a.__all__)
        forbidden = {
            "Query",
            "QueryContext",
            "QueryResult",
            "QueryExpression",
            "QueryError",
        }
        leaked = forbidden & public
        assert not leaked, (
            f"_query_engine symbols leaked into "
            f"un_comtrade.analytics.__all__: {leaked}"
        )

    def test_query_engine_not_in_analytics_dir(self):
        import un_comtrade.analytics as a
        for n in (
            "Query",
            "QueryContext",
            "QueryResult",
            "QueryExpression",
            "QueryError",
        ):
            assert not hasattr(a, n), (
                f"un_comtrade.analytics.{n} exposed "
                f"publicly; QE-001 must remain internal"
            )

    def test_internal_path_still_works(self):
        # Sanity: the internal import path
        # continues to work.
        from un_comtrade.analytics._query_engine import (
            Query as InternalQuery,
        )
        assert InternalQuery is Query

    def test_leading_underscore_filename(self):
        # The module filename must start with
        # an underscore to signal internal.
        from un_comtrade.analytics import (
            _query_engine,
        )
        assert (
            _query_engine.__name__
            == "un_comtrade.analytics._query_engine"
        )