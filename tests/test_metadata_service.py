"""Unit tests for the MetadataService skeleton (P1-012).

The service is a skeleton in this task scope: it
declares the 18 method signatures from the SDK spec
(M01-M18) and raises `NotImplementedError` when called.
No API requests, no parsing, no persistence.

Coverage:

- Service instantiates with a transport.
- Service holds the transport dependency.
- All 18 interface methods exist with the documented
  signatures.
- All 18 methods raise `NotImplementedError`.
- `ComtradeClient` owns the service via `client.metadata`.
- The service is constructed lazily on first access.
- Caller-supplied services are honoured (no override).
- Default base path is the documented UN Comtrade path.
- Module exports `MetadataService`.
"""

from __future__ import annotations

import inspect
from typing import Callable

import httpx
import pytest

from un_comtrade.client import ComtradeClient
from un_comtrade.config import Configuration
from un_comtrade.metadata import (
    DEFAULT_REFERENCE_BASE_PATH,
    MetadataService,
)
from un_comtrade.models import (
    Classification,
    Country,
    Frequency,
    HSCode,
    Partner,
    TradeFlow,
    TransportMode,
)
from un_comtrade.transport import HttpTransport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_transport() -> HttpTransport:
    """Build a mock-backed HttpTransport for skeleton wiring tests."""
    return HttpTransport(
        base_url="https://example.org",
        user_agent="ua/1.0",
        client=httpx.Client(transport=httpx.MockTransport(lambda r: r)),
    )


# ---------------------------------------------------------------------------
# Service instantiation
# ---------------------------------------------------------------------------


class TestServiceInstantiation:
    def test_instantiates_with_transport(self):
        t = _build_transport()
        service = MetadataService(t)
        assert service.transport is t
        t.close()

    def test_default_base_path(self):
        t = _build_transport()
        service = MetadataService(t)
        assert service.base_path == DEFAULT_REFERENCE_BASE_PATH
        assert service.base_path == "/files/v1/app/reference"
        t.close()

    def test_custom_base_path(self):
        t = _build_transport()
        service = MetadataService(t, base_path="/custom/path")
        assert service.base_path == "/custom/path"
        t.close()

    def test_cache_property_none_when_unset(self):
        t = _build_transport()
        service = MetadataService(t)
        assert service.cache is None
        t.close()


# ---------------------------------------------------------------------------
# Interface methods exist (M01-M18)
# ---------------------------------------------------------------------------


class TestInterfaceMethodsExist:
    """Every method from the SDK spec (M01-M18) is declared."""

    @pytest.mark.parametrize(
        "name",
        [
            "get_countries",
            "get_country",
            "get_partners",
            "get_partner",
            "get_classifications",
            "get_classification",
            "get_classification_editions",
            "get_hs_codes",
            "get_hs_code",
            "search_hs",
            "get_trade_flows",
            "get_transport_modes",
            "get_customs_procedures",
            "get_quantity_units",
            "get_modes_of_supply",
            "get_frequencies",
            "get_data_items",
            "get_metadata",
        ],
    )
    def test_method_exists(self, name: str):
        t = _build_transport()
        service = MetadataService(t)
        assert hasattr(service, name)
        assert callable(getattr(service, name))
        t.close()

    @pytest.mark.parametrize(
        "name",
        [
            "get_countries",
            "get_partners",
            "get_classifications",
            "get_trade_flows",
            "get_transport_modes",
            "get_customs_procedures",
            "get_quantity_units",
            "get_modes_of_supply",
            "get_frequencies",
            "get_data_items",
        ],
    )
    def test_zero_arg_list_methods(self, name: str):
        """Zero-argument list-returning methods take no required args
        in the skeleton (callers pass filters later, when
        implementation lands).
        """
        t = _build_transport()
        service = MetadataService(t)
        method = getattr(service, name)
        sig = inspect.signature(method)
        required = [
            p.name
            for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty
            and p.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
        assert required == [], (
            f"{name} should take no required args in the skeleton; "
            f"got {required}"
        )
        t.close()

    @pytest.mark.parametrize(
        "name,expected_required",
        [
            ("get_country", ["country_code"]),
            ("get_partner", ["country_code"]),
            ("get_classification", ["classification_code"]),
            ("get_classification_editions", ["classification_code"]),
            ("get_hs_codes", ["edition"]),
            ("get_hs_code", ["commodity_code", "edition"]),
            ("search_hs", ["query", "edition"]),
            ("get_metadata", ["table_name"]),
        ],
    )
    def test_methods_with_required_args(
        self, name: str, expected_required: list[str]
    ):
        """Methods that take a key parameter declare that key in
        the documented position. The skeleton keeps the
        documented signatures verbatim so callers can begin
        integrating today.
        """
        t = _build_transport()
        service = MetadataService(t)
        sig = inspect.signature(service.get_country)  # any same-shape
        method = getattr(service, name)
        method_sig = inspect.signature(method)
        params = list(method_sig.parameters.keys())
        assert params == expected_required, (
            f"{name} signature mismatch: expected {expected_required}, "
            f"got {params}"
        )
        t.close()


# ---------------------------------------------------------------------------
# Interface methods raise NotImplementedError
# ---------------------------------------------------------------------------


class TestInterfaceMethodsRaise:
    """Methods whose canonical model / parser isn't yet
    implemented raise `NotImplementedError`. The remaining
    M01-M18 methods are implemented in P2-001 and exercised
    in `tests/test_catalogue_fetchers.py`.
    """

    @pytest.mark.parametrize(
        "name,args",
        [
            ("get_customs_procedures", ()),
            ("get_modes_of_supply", ()),
        ],
    )
    def test_method_raises_not_implemented(
        self, name: str, args: tuple[object, ...]
    ):
        t = _build_transport()
        service = MetadataService(t)
        try:
            with pytest.raises(NotImplementedError):
                getattr(service, name)(*args)
        finally:
            t.close()


# ---------------------------------------------------------------------------
# ComtradeClient owns MetadataService
# ---------------------------------------------------------------------------


class TestClientOwnership:
    def test_client_owns_metadata_service(self):
        client = ComtradeClient(
            Configuration(base_url="https://example.org", user_agent="ua/1.0")
        )
        try:
            assert isinstance(client.metadata, MetadataService)
        finally:
            client.close()

    def test_metadata_constructed_lazily(self):
        client = ComtradeClient(
            Configuration(base_url="https://example.org", user_agent="ua/1.0")
        )
        try:
            # No MetadataService exists yet.
            assert client._metadata_service is None
            # Access creates it.
            _ = client.metadata
            assert client._metadata_service is not None
        finally:
            client.close()

    def test_metadata_reused_on_second_access(self):
        client = ComtradeClient(
            Configuration(base_url="https://example.org", user_agent="ua/1.0")
        )
        try:
            first = client.metadata
            second = client.metadata
            assert first is second
        finally:
            client.close()

    def test_metadata_uses_clients_transport(self):
        client = ComtradeClient(
            Configuration(base_url="https://example.org", user_agent="ua/1.0")
        )
        try:
            assert client.metadata.transport is client.transport
        finally:
            client.close()

    def test_caller_supplied_metadata_service_used(self):
        custom = MetadataService(_build_transport())
        try:
            client = ComtradeClient(
                Configuration(
                    base_url="https://example.org", user_agent="ua/1.0"
                ),
                metadata_service=custom,
            )
            try:
                assert client.metadata is custom
            finally:
                client.close()
        finally:
            custom.transport.close()

    def test_metadata_raises_not_implemented_for_unsupported(self):
        # `get_customs_procedures` and `get_modes_of_supply`
        # are the two methods whose canonical model isn't
        # implemented yet. The rest of the M01-M18 surface
        # is exercised in `tests/test_catalogue_fetchers.py`.
        client = ComtradeClient(
            Configuration(base_url="https://example.org", user_agent="ua/1.0")
        )
        try:
            with pytest.raises(NotImplementedError):
                client.metadata.get_customs_procedures()
            with pytest.raises(NotImplementedError):
                client.metadata.get_modes_of_supply()
        finally:
            client.close()


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------


class TestModuleExports:
    def test_metadata_service_exported(self):
        from un_comtrade import metadata as md_mod

        assert hasattr(md_mod, "MetadataService")
        assert md_mod.MetadataService is MetadataService

    def test_default_base_path_constant(self):
        from un_comtrade import metadata as md_mod

        assert "DEFAULT_REFERENCE_BASE_PATH" in md_mod.__all__
        assert md_mod.DEFAULT_REFERENCE_BASE_PATH == "/files/v1/app/reference"


# ---------------------------------------------------------------------------
# Service does not perform I/O at construction
# ---------------------------------------------------------------------------


class TestServiceDoesNoIO:
    def test_construction_does_not_invoke_handler(self):
        # If the service performed I/O at construction, the handler
        # would have been called by now. With an empty response queue
        # this would raise. The fact that construction completes
        # cleanly proves no I/O is performed.
        called = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            called["n"] += 1
            return httpx.Response(
                status_code=200,
                content=b"{}",
                request=request,
            )

        t = HttpTransport(
            base_url="https://example.org",
            user_agent="ua/1.0",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        try:
            MetadataService(t)
            assert called["n"] == 0
        finally:
            t.close()

    def test_no_io_when_client_constructed(self):
        # The client also must not issue requests just by being
        # instantiated (per spec §2.2). Constructing a client does
        # not touch the metadata service either.
        called = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            called["n"] += 1
            return httpx.Response(
                status_code=200,
                content=b"{}",
                request=request,
            )

        client = ComtradeClient(
            Configuration(base_url="https://example.org", user_agent="ua/1.0"),
            transport=HttpTransport(
                base_url="https://example.org",
                user_agent="ua/1.0",
                client=httpx.Client(transport=httpx.MockTransport(handler)),
            ),
        )
        try:
            assert called["n"] == 0
        finally:
            client.close()