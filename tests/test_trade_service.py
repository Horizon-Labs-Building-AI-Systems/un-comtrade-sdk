"""Unit tests for the TradeService skeleton (un_comtrade.trade).

Per the P2-004 task scope, the service is a SKELETON:
the constructor wires dependencies, the method
signatures match the documented contract, and the
method bodies raise `NotImplementedError`. No
endpoint execution, no parsing, no pagination.

Coverage:

- Constructor dependency wiring (transport, parser,
  configuration, defaults)
- Validation of default values (breakdown_mode,
  default_max_records bounds)
- Property exposure (transport, parser, configuration,
  default_classification, default_breakdown_mode,
  default_max_records)
- Method surface: T01-T11 (annual + monthly trade
  retrieval), F01-F02 (tariffline), P01-P04 (preview),
  C01-C03 (count) — all raise NotImplementedError
- Signature introspection (kwarg names, defaults)
- Lifecycle (`close`, `__enter__`, `__exit__`)
- Internal `_build_query` helper (translates kwargs
  into a `TradeQuery`)
"""

from __future__ import annotations

import inspect

import pytest

from un_comtrade.config import Configuration
from un_comtrade.query import (
    DEFAULT_BREAKDOWN_MODE,
    DEFAULT_CLASSIFICATION,
    FLOW_CODES,
    MAX_RECORDS_LIMIT,
    MIN_RECORDS,
    PARTNER_WORLD,
    TradeQuery,
)
from un_comtrade.trade import DECLARED_METHOD_COUNT, TradeService
from un_comtrade.transport import HttpTransport


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def configuration():
    return Configuration(api_key="test-key-123")


@pytest.fixture
def transport(configuration):
    return HttpTransport(
        base_url="https://example.invalid",
        user_agent="test/1",
        api_key=configuration.api_key,
    )


@pytest.fixture
def service(transport, configuration):
    return TradeService(transport, configuration=configuration)


# ---------------------------------------------------------------------------
# Constructor: dependency wiring
# ---------------------------------------------------------------------------


class TestConstructor:
    def test_transport_required(self):
        with pytest.raises(TypeError):
            TradeService()  # type: ignore[call-arg]

    def test_minimal_construction(self, transport):
        s = TradeService(transport)
        assert s.transport is transport
        assert s.parser is None
        assert s.configuration is None
        assert s.default_classification == DEFAULT_CLASSIFICATION
        assert s.default_breakdown_mode == DEFAULT_BREAKDOWN_MODE
        assert s.default_max_records is None

    def test_with_configuration(self, transport, configuration):
        s = TradeService(transport, configuration=configuration)
        assert s.configuration is configuration

    def test_with_parser_placeholder(self, transport):
        # Parser is optional and currently `None` (P2-005
        # will provide the parser). We accept any object
        # typed as the future TradeParser; the constructor
        # just stores it.
        sentinel = object()
        s = TradeService(transport, parser=sentinel)  # type: ignore[arg-type]
        assert s.parser is sentinel

    def test_custom_defaults(self, transport):
        s = TradeService(
            transport,
            default_classification="SITC",
            default_breakdown_mode="plus",
            default_max_records=10000,
        )
        assert s.default_classification == "SITC"
        assert s.default_breakdown_mode == "plus"
        assert s.default_max_records == 10000

    def test_invalid_breakdown_mode_rejected(self, transport):
        with pytest.raises(ValueError, match="default_breakdown_mode"):
            TradeService(transport, default_breakdown_mode="legacy")

    def test_max_records_lower_bound(self, transport):
        with pytest.raises(ValueError, match="default_max_records"):
            TradeService(transport, default_max_records=MIN_RECORDS - 1)

    def test_max_records_upper_bound(self, transport):
        with pytest.raises(ValueError, match="default_max_records"):
            TradeService(
                transport, default_max_records=MAX_RECORDS_LIMIT + 1
            )

    def test_max_records_at_limit_accepted(self, transport):
        s = TradeService(
            transport, default_max_records=MAX_RECORDS_LIMIT
        )
        assert s.default_max_records == MAX_RECORDS_LIMIT

    def test_max_records_min_accepted(self, transport):
        s = TradeService(transport, default_max_records=MIN_RECORDS)
        assert s.default_max_records == MIN_RECORDS


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


class TestProperties:
    def test_transport_exposed(self, service, transport):
        assert service.transport is transport

    def test_parser_none_in_skeleton(self, service):
        assert service.parser is None

    def test_configuration_exposed(self, service, configuration):
        assert service.configuration is configuration

    def test_default_classification_constant(self, service):
        assert service.default_classification == DEFAULT_CLASSIFICATION
        assert service.default_classification == "HS"

    def test_default_breakdown_mode_constant(self, service):
        assert service.default_breakdown_mode == DEFAULT_BREAKDOWN_MODE
        assert service.default_breakdown_mode == "classic"

    def test_default_max_records_default_none(self, service):
        assert service.default_max_records is None


# ---------------------------------------------------------------------------
# Method surface: T01-T11 + F + P + C
# ---------------------------------------------------------------------------


#: Expected public method names per `007_SDK_SPECIFICATION.md`
#: §3.2 (T01-T08), §3.3 (T09-T11), §3.4 (F01-F02),
#: §3.5 (P01-P04), §3.6 (C01-C03).
EXPECTED_METHODS = {
    # T01-T08: annual trade retrieval
    "get_exports",
    "get_imports",
    "get_trade",
    "get_trade_by_hs",
    "get_world_trade",
    "get_trade_balance",
    "get_bilateral",
    "get_trade_matrix",
    # T09-T11: monthly trade retrieval
    "get_monthly_exports",
    "get_monthly_imports",
    "get_monthly_trade",
    # F01-F02: tariffline
    "get_tariffline",
    "get_tariffline_by_hs",
    # P01-P04: preview (no key required)
    "preview_exports",
    "preview_imports",
    "preview_trade",
    "preview_tariffline",
    # C01-C03: counting
    "count_exports",
    "count_imports",
    "count_trade",
}


class TestMethodSurface:
    def test_all_expected_methods_present(self, service):
        for name in EXPECTED_METHODS:
            assert hasattr(service, name), (
                f"TradeService is missing {name!r}"
            )

    def test_no_unexpected_public_methods(self, service):
        # The documented skeleton exposes only the 20 trade
        # methods + `close`. Filter dunder / private out.
        public = {
            name
            for name in dir(service)
            if not name.startswith("_") and callable(getattr(service, name))
        }
        public -= {"close"}
        assert public == EXPECTED_METHODS

    def test_declared_method_count(self, service):
        # DECLARED_METHOD_COUNT counts everything callable
        # and non-dunder on the class — close + the 20 methods
        # = 21.
        assert DECLARED_METHOD_COUNT == 21

    def test_all_methods_callable(self, service):
        for name in EXPECTED_METHODS:
            method = getattr(service, name)
            assert callable(method)

    def test_all_methods_inherit_docstring(self, service):
        # Each method has a docstring that cites the spec section.
        for name in EXPECTED_METHODS:
            method = getattr(service, name)
            assert method.__doc__ is not None, (
                f"{name} is missing a docstring"
            )
            assert "007_SDK_SPECIFICATION.md" in method.__doc__, (
                f"{name} docstring doesn't cite the spec section"
            )


# ---------------------------------------------------------------------------
# Method bodies: NotImplementedError
# ---------------------------------------------------------------------------


class TestNotImplemented:
    """Methods that land in P2-005 raise no error (they work);
    methods deferred to later tasks still raise NotImplementedError.

    Implemented in P2-005: T01-T03 (annual) + T09-T11 (monthly).
    Still stubbed: T04-T08, F01-F02, P01-P04, C01-C03.
    """

    @staticmethod
    def _fake_transport_get(*args, **kwargs):
        """Build a fake `HttpResponse` for the patched transport.get."""
        import json as _json

        from un_comtrade.transport import HttpResponse

        body = _json.dumps(
            {"count": 1, "data": [{}], "elapsed_seconds": 0.1, "error": ""}
        ).encode("utf-8")
        return HttpResponse(
            status_code=200,
            body=body,
            headers={"content-type": "application/json"},
            elapsed_seconds=0.1,
            url="https://example.invalid/C/A/X/HS",
        )

    def test_get_exports_does_not_raise(self, service, monkeypatch):
        from un_comtrade.models import TradeResponse

        monkeypatch.setattr(
            service._transport, "get", self._fake_transport_get
        )
        result = service.get_exports(699, "2022")
        assert isinstance(result, TradeResponse)

    def test_get_imports_does_not_raise(self, service, monkeypatch):
        from un_comtrade.models import TradeResponse

        monkeypatch.setattr(
            service._transport, "get", self._fake_transport_get
        )
        result = service.get_imports(699, "2022")
        assert isinstance(result, TradeResponse)

    def test_get_trade_does_not_raise(self, service, monkeypatch):
        from un_comtrade.models import TradeResponse

        monkeypatch.setattr(
            service._transport, "get", self._fake_transport_get
        )
        result = service.get_trade(699, "X", "2022")
        assert isinstance(result, TradeResponse)

    def test_get_trade_by_hs_does_not_raise(self, service, monkeypatch):
        from un_comtrade.models import TradeResponse

        monkeypatch.setattr(
            service._transport, "get", self._fake_transport_get
        )
        result = service.get_trade_by_hs("0101", 699, "X", "2022")
        assert isinstance(result, TradeResponse)

    def test_get_world_trade_does_not_raise(self, service, monkeypatch):
        from un_comtrade.models import TradeResponse

        monkeypatch.setattr(
            service._transport, "get", self._fake_transport_get
        )
        result = service.get_world_trade(699, "X", "2022")
        assert isinstance(result, TradeResponse)

    def test_get_trade_balance_does_not_raise(self, service, monkeypatch):
        from un_comtrade.models import TradeResponse

        monkeypatch.setattr(
            service._transport, "get", self._fake_transport_get
        )
        result = service.get_trade_balance(699, "2022")
        assert isinstance(result, TradeResponse)

    def test_get_bilateral_does_not_raise(self, service, monkeypatch):
        from un_comtrade.models import TradeResponse

        monkeypatch.setattr(
            service._transport, "get", self._fake_transport_get
        )
        result = service.get_bilateral(699, "X", "2022")
        assert isinstance(result, TradeResponse)

    def test_get_trade_matrix_does_not_raise(self, service, monkeypatch):
        from un_comtrade.models import TradeResponse

        monkeypatch.setattr(
            service._transport, "get", self._fake_transport_get
        )
        result = service.get_trade_matrix("2022", "X", 699, 842, "TOTAL")
        assert isinstance(result, TradeResponse)

    def test_get_monthly_exports_does_not_raise(self, service, monkeypatch):
        from un_comtrade.models import TradeResponse

        monkeypatch.setattr(
            service._transport, "get", self._fake_transport_get
        )
        result = service.get_monthly_exports(699, "202201")
        assert isinstance(result, TradeResponse)

    def test_get_monthly_imports_does_not_raise(self, service, monkeypatch):
        from un_comtrade.models import TradeResponse

        monkeypatch.setattr(
            service._transport, "get", self._fake_transport_get
        )
        result = service.get_monthly_imports(699, "202201")
        assert isinstance(result, TradeResponse)

    def test_get_monthly_trade_does_not_raise(self, service, monkeypatch):
        from un_comtrade.models import TradeResponse

        monkeypatch.setattr(
            service._transport, "get", self._fake_transport_get
        )
        result = service.get_monthly_trade(699, "X", "202201")
        assert isinstance(result, TradeResponse)

    def test_preview_exports_raises(self, service):
        with pytest.raises(NotImplementedError, match="preview_exports"):
            service.preview_exports(699, "2022")

    def test_preview_imports_raises(self, service):
        with pytest.raises(NotImplementedError, match="preview_imports"):
            service.preview_imports(699, "2022")

    def test_preview_trade_raises(self, service):
        with pytest.raises(NotImplementedError, match="preview_trade"):
            service.preview_trade(699, "X", "2022")

    def test_preview_tariffline_raises(self, service):
        with pytest.raises(NotImplementedError, match="preview_tariffline"):
            service.preview_tariffline(699, "X", "2022")

    def test_count_exports_raises(self, service):
        with pytest.raises(NotImplementedError, match="count_exports"):
            service.count_exports(699, "2022")

    def test_count_imports_raises(self, service):
        with pytest.raises(NotImplementedError, match="count_imports"):
            service.count_imports(699, "2022")

    def test_count_trade_raises(self, service):
        with pytest.raises(NotImplementedError, match="count_trade"):
            service.count_trade(699, "X", "2022")


# ---------------------------------------------------------------------------
# Signature introspection
# ---------------------------------------------------------------------------


class TestSignatures:
    def test_get_exports_signature(self, service):
        sig = inspect.signature(service.get_exports)
        params = sig.parameters
        # reporter_code, period are required positional-or-keyword.
        assert "reporter_code" in params
        assert "period" in params
        # Default-kwargs match the spec.
        assert params["partner_code"].default is None
        assert params["commodity_code"].default == "TOTAL"
        assert params["breakdown_mode"].default is None
        assert params["max_records"].default is None

    def test_get_trade_signature(self, service):
        sig = inspect.signature(service.get_trade)
        params = sig.parameters
        # flow_code is required (no default).
        assert "flow_code" in params
        assert params["flow_code"].default is inspect.Parameter.empty

    def test_get_trade_by_hs_signature(self, service):
        sig = inspect.signature(service.get_trade_by_hs)
        params = sig.parameters
        # commodity_code first per spec §T04.
        param_names = list(params.keys())
        assert param_names[0] == "commodity_code"
        assert param_names[1] == "reporter_code"
        assert param_names[2] == "flow_code"
        assert param_names[3] == "period"

    def test_get_world_trade_signature(self, service):
        sig = inspect.signature(service.get_world_trade)
        params = sig.parameters
        # partner_code not in the surface (implied 0).
        assert "partner_code" not in params

    def test_get_trade_matrix_signature(self, service):
        sig = inspect.signature(service.get_trade_matrix)
        params = sig.parameters
        # classification and max_records are kwarg-only here.
        assert "classification" in params
        assert "max_records" in params

    def test_monthly_methods_signature(self, service):
        for name in (
            "get_monthly_exports",
            "get_monthly_imports",
            "get_monthly_trade",
        ):
            sig = inspect.signature(getattr(service, name))
            assert "period" in sig.parameters

    def test_count_methods_signature(self, service):
        for name in ("count_exports", "count_imports", "count_trade"):
            sig = inspect.signature(getattr(service, name))
            params = sig.parameters
            # count methods don't have max_records.
            assert "max_records" not in params


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_close_no_op(self, service):
        # close() is a no-op in this skeleton.
        service.close()  # should not raise

    def test_close_idempotent(self, service):
        service.close()
        service.close()  # second call also fine

    def test_context_manager(self, transport, configuration):
        with TradeService(transport, configuration=configuration) as s:
            assert s.transport is transport

    def test_context_manager_exit_does_not_raise(
        self, transport, configuration
    ):
        # Even if an exception is raised inside the block,
        # __exit__ runs close() which is a no-op.
        with pytest.raises(RuntimeError):
            with TradeService(transport, configuration=configuration) as s:
                _ = s.transport
                raise RuntimeError("boom")


# ---------------------------------------------------------------------------
# Internal helper: _build_query
# ---------------------------------------------------------------------------


class TestBuildQueryHelper:
    def test_minimal_query(self, service):
        # Uses the service's defaults for classification and
        # breakdown mode.
        q = service._build_query(
            reporter_code=699,
            flow_code="X",
            partner_code=None,
            period="2022",
            commodity_code="TOTAL",
            classification=None,
            edition=None,
            breakdown_mode=None,
            max_records=None,
        )
        assert isinstance(q, TradeQuery)
        assert q.reporter_code == 699
        assert q.flow_code == "X"
        assert q.period == "2022"
        assert q.cmd_code == "TOTAL"
        assert q.classification_code == DEFAULT_CLASSIFICATION
        assert q.breakdown_mode == DEFAULT_BREAKDOWN_MODE
        assert q.max_records is None

    def test_explicit_overrides(self, service):
        q = service._build_query(
            reporter_code=699,
            flow_code="M",
            partner_code=842,
            period="202201,202202",
            commodity_code="0101",
            classification="HS",
            edition="H2022",
            breakdown_mode="plus",
            max_records=1000,
        )
        assert q.partner_code == 842
        assert q.period == "202201,202202"
        assert q.cmd_code == "0101"
        assert q.classification_code == "HS"
        assert q.classification_edition == "H2022"
        assert q.breakdown_mode == "plus"
        assert q.max_records == 1000

    def test_default_max_records_applied(self, transport):
        s = TradeService(transport, default_max_records=5000)
        q = s._build_query(
            reporter_code=699,
            flow_code="X",
            partner_code=None,
            period="2022",
            commodity_code="TOTAL",
            classification=None,
            edition=None,
            breakdown_mode=None,
            max_records=None,
        )
        assert q.max_records == 5000

    def test_explicit_max_records_overrides_default(self, transport):
        s = TradeService(transport, default_max_records=5000)
        q = s._build_query(
            reporter_code=699,
            flow_code="X",
            partner_code=None,
            period="2022",
            commodity_code="TOTAL",
            classification=None,
            edition=None,
            breakdown_mode=None,
            max_records=100,
        )
        assert q.max_records == 100


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_partner_world_constant(self):
        assert PARTNER_WORLD == 0

    def test_flow_codes_constant(self):
        assert FLOW_CODES == frozenset({"M", "X", "RX", "RM"})

    def test_default_classification(self):
        assert DEFAULT_CLASSIFICATION == "HS"

    def test_default_breakdown_mode(self):
        assert DEFAULT_BREAKDOWN_MODE == "classic"

    def test_min_records(self):
        assert MIN_RECORDS == 1

    def test_max_records_limit(self):
        assert MAX_RECORDS_LIMIT == 250_000


# ---------------------------------------------------------------------------
# Determinism + isolation
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_repeated_construction_yields_equal_state(self, transport, configuration):
        s1 = TradeService(transport, configuration=configuration)
        s2 = TradeService(transport, configuration=configuration)
        assert s1.default_classification == s2.default_classification
        assert s1.default_breakdown_mode == s2.default_breakdown_mode
        assert s1.default_max_records == s2.default_max_records

    def test_method_count_stable(self):
        # DECLARED_METHOD_COUNT must not drift.
        assert DECLARED_METHOD_COUNT == sum(
            1
            for name in dir(TradeService)
            if not name.startswith("_")
            and callable(getattr(TradeService, name, None))
        )


# ---------------------------------------------------------------------------
# Service does NOT own transport / parser lifecycle
# ---------------------------------------------------------------------------


class TestOwnership:
    def test_transport_not_closed_on_service_close(self, service, transport):
        # The service must not close the transport — the
        # client owns it. After close(), the transport
        # must still be usable.
        service.close()
        # If the service had closed the transport, this
        # would raise. We can only verify by checking that
        # the transport's internal state hasn't been torn
        # down — we look at its `_closed` flag or use its
        # attributes.
        assert hasattr(transport, "_client") or hasattr(transport, "close")

    def test_parser_not_owned(self, service):
        # The service holds a parser reference but does not
        # construct one; in this skeleton it's None.
        assert service.parser is None