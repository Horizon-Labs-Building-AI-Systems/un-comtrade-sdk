"""Unit tests for `un_comtrade.exceptions`.

Per ADR-0030, the exception hierarchy is part of the SDK's public
API and requires unit tests. The tests verify:
- the 13-class hierarchy declared in ADR-0012,
- `ComtradeError` is the root of every other exception,
- exception chaining is preserved (`__cause__`),
- exceptions stringify cleanly via `str()`,
- subclass relationships match the documented inheritance chain.
"""

from __future__ import annotations

import pytest

from un_comtrade.exceptions import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    ComtradeError,
    ConfigurationError,
    NetworkError,
    RateLimitError,
    RetryError,
    SerializationError,
    ServerError,
    TimeoutError,
    UnknownError,
    ValidationError,
)


# ---------------------------------------------------------------------------
# Hierarchy
# ---------------------------------------------------------------------------


class TestHierarchy:
    def test_comtrade_error_is_root_of_all(self):
        for cls in (
            ConfigurationError,
            AuthenticationError,
            AuthorizationError,
            ValidationError,
            NetworkError,
            TimeoutError,
            RetryError,
            RateLimitError,
            SerializationError,
            APIError,
            ServerError,
            UnknownError,
        ):
            assert issubclass(cls, ComtradeError), (
                f"{cls.__name__} does not inherit from ComtradeError"
            )

    def test_thirteen_exception_classes_exist(self):
        # Per ADR-0012 there are exactly 13 exception types in the SDK.
        # Filter to classes defined in this module (excludes stdlib
        # `Exception` and `BaseException` which are also visible).
        from un_comtrade import exceptions
        sdk_types = [
            v for v in vars(exceptions).values()
            if isinstance(v, type)
            and issubclass(v, BaseException)
            and v.__module__ == "un_comtrade.exceptions"
        ]
        assert len(sdk_types) == 13

    def test_authorization_inherits_from_authentication(self):
        assert issubclass(AuthorizationError, AuthenticationError)

    def test_timeout_retry_rate_limit_inherit_from_network(self):
        for cls in (TimeoutError, RetryError, RateLimitError):
            assert issubclass(cls, NetworkError)

    def test_server_inherits_from_api(self):
        assert issubclass(ServerError, APIError)

    def test_configuration_error_is_value_error(self):
        # Configuration errors are ValueError-compatible for ergonomics.
        assert issubclass(ConfigurationError, ValueError)

    def test_validation_error_is_value_error(self):
        assert issubclass(ValidationError, ValueError)

    def test_comtrade_error_is_exception(self):
        assert issubclass(ComtradeError, Exception)


# ---------------------------------------------------------------------------
# Construction and stringification
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_message_only(self):
        e = ComtradeError("something broke")
        assert str(e) == "something broke"

    def test_message_with_cause(self):
        cause = ValueError("root cause")
        e = ComtradeError("wrapper").__init__  # type: ignore[attr-defined]
        e = ComtradeError("wrapper")
        e.__cause__ = cause
        assert e.__cause__ is cause
        # `raise X from Y` semantics: __cause__ is set automatically
        try:
            try:
                raise ValueError("inner")
            except ValueError as inner:
                raise ComtradeError("outer") from inner
        except ComtradeError as outer:
            assert outer.__cause__ is not None
            assert isinstance(outer.__cause__, ValueError)
            assert str(outer.__cause__) == "inner"

    def test_api_error_carries_status_code(self):
        e = APIError("bad request", status_code=400, response_body="<html>")
        assert e.status_code == 400
        assert e.response_body == "<html>"
        assert str(e) == "bad request"

    def test_api_error_status_optional(self):
        e = APIError("oops")
        assert e.status_code is None
        assert e.response_body is None

    def test_server_error_inherits_api_error_attributes(self):
        e = ServerError("upstream 500", status_code=500)
        assert e.status_code == 500
        assert isinstance(e, APIError)
        assert isinstance(e, ComtradeError)

    def test_authorization_error_inherits_authentication(self):
        e = AuthorizationError("401 unauthorized")
        assert isinstance(e, AuthenticationError)
        assert isinstance(e, ComtradeError)
        assert str(e) == "401 unauthorized"


# ---------------------------------------------------------------------------
# Catching
# ---------------------------------------------------------------------------


class TestCatching:
    def test_catch_comtrade_error_catches_everything(self):
        for cls in (
            ConfigurationError,
            AuthenticationError,
            AuthorizationError,
            ValidationError,
            NetworkError,
            TimeoutError,
            RetryError,
            RateLimitError,
            SerializationError,
            APIError,
            ServerError,
            UnknownError,
        ):
            try:
                raise cls("boom")
            except ComtradeError as caught:
                assert caught.__class__ is cls
            else:
                pytest.fail(f"{cls.__name__} not caught by ComtradeError")

    def test_catch_network_catches_subclasses(self):
        for cls in (TimeoutError, RetryError, RateLimitError):
            try:
                raise cls("net boom")
            except NetworkError as caught:
                assert caught.__class__ is cls
            else:
                pytest.fail(f"{cls.__name__} not caught by NetworkError")

    def test_catch_api_error_catches_server_error(self):
        try:
            raise ServerError("server boom", status_code=500)
        except APIError as caught:
            assert caught.__class__ is ServerError
        else:
            pytest.fail("ServerError not caught by APIError")

    def test_catch_authentication_catches_authorization(self):
        try:
            raise AuthorizationError("auth boom")
        except AuthenticationError as caught:
            assert caught.__class__ is AuthorizationError
        else:
            pytest.fail("AuthorizationError not caught by AuthenticationError")


# ---------------------------------------------------------------------------
# Exception chaining
# ---------------------------------------------------------------------------


class TestChaining:
    def test_raise_from_preserves_cause(self):
        try:
            try:
                raise ValueError("original")
            except ValueError as original:
                raise NetworkError("wrapped") from original
        except NetworkError as caught:
            assert caught.__cause__ is not None
            assert isinstance(caught.__cause__, ValueError)

    def test_raise_from_none_sets_cause_to_none(self):
        try:
            raise NetworkError("standalone")
        except NetworkError as caught:
            assert caught.__cause__ is None

    def test_implicit_chaining_uses_context_not_cause(self):
        # Per Python semantics, a bare `raise X` inside an `except` block
        # sets `__context__` (not `__cause__`). `__cause__` is only set
        # by the explicit `raise X from Y` form.
        try:
            try:
                raise KeyError("k")
            except KeyError:
                raise ComtradeError("wrapped implicit")
        except ComtradeError as caught:
            assert caught.__cause__ is None
            assert caught.__context__ is not None
            assert isinstance(caught.__context__, KeyError)


# ---------------------------------------------------------------------------
# Compatibility with config.ConfigurationError
# ---------------------------------------------------------------------------


class TestConfigCompatibility:
    """The ConfigurationError defined in exceptions.py is the same class
    the config module uses."""

    def test_config_uses_exceptions_module(self):
        from un_comtrade.config import ConfigurationError as ConfigCE
        assert ConfigCE is ConfigurationError

    def test_config_validation_raises_exceptions_module_class(self):
        from un_comtrade.config import Configuration
        try:
            Configuration(max_retries=-1)
        except ConfigurationError as e:
            assert type(e) is ConfigurationError
            assert isinstance(e, ComtradeError)
            assert isinstance(e, ValueError)
        else:
            pytest.fail("Configuration(max_retries=-1) did not raise")


# ---------------------------------------------------------------------------
# Str / repr sanity
# ---------------------------------------------------------------------------


class TestStrRepr:
    @pytest.mark.parametrize("cls,args", [
        (ComtradeError, ("msg",)),
        (ConfigurationError, ("bad config",)),
        (AuthenticationError, ("no key",)),
        (AuthorizationError, ("denied",)),
        (ValidationError, ("bad param",)),
        (NetworkError, ("conn refused",)),
        (TimeoutError, ("timed out",)),
        (RetryError, ("retries exhausted",)),
        (RateLimitError, ("429",)),
        (SerializationError, ("invalid json",)),
        (APIError, ("400",)),
        (ServerError, ("500",)),
        (UnknownError, ("weird",)),
    ])
    def test_str_returns_message(self, cls, args):
        e = cls(*args)
        assert str(e) == args[0]
        assert isinstance(e, ComtradeError)


# ---------------------------------------------------------------------------
# Count check (frozen invariant)
# ---------------------------------------------------------------------------


def test_thirteen_subclasses_only():
    """Exactly 12 subclasses + 1 base = 13 total exception classes."""
    import un_comtrade.exceptions as exc_module

    exception_types = [
        v for v in vars(exc_module).values()
        if isinstance(v, type) and issubclass(v, BaseException)
    ]
    # Filter to those defined in this module specifically.
    sdk_exceptions = [
        v for v in exception_types
        if v.__module__ == "un_comtrade.exceptions"
    ]
    # ComtradeError + 12 subclasses = 13
    assert len(sdk_exceptions) == 13, (
        f"Expected 13 exception classes, got {len(sdk_exceptions)}: "
        f"{[c.__name__ for c in sdk_exceptions]}"
    )