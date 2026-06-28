"""F-003 regression: logging DEFAULT_LOG_LEVEL
collision has been resolved.

V-001 / S-002 / 031_PRODUCTION_READINESS all
flagged the namespace collision between
``un_comtrade.logging.DEFAULT_LOG_LEVEL`` (an
``int`` = 30) and ``un_comtrade.config.DEFAULT_LOG_LEVEL``
(a ``str`` = ``"WARNING"``).

The v1.0.0 / v1.0.1 release applied R1: rename
the logging-side name to ``LOGGING_DEFAULT_LEVEL``.
A deprecated alias briefly bridged the
transition but F-003 removes it entirely.

This guard fails if:
1. ``un_comtrade.logging`` re-exports
   ``DEFAULT_LOG_LEVEL`` (the old name).
2. ``un_comtrade.logging`` has any module-level
   assignment to ``DEFAULT_LOG_LEVEL`` (would
   silently shadow the canonical config-side
   string).
3. The new ``LOGGING_DEFAULT_LEVEL`` constant is
   missing or has the wrong value.
4. Internal callers (e.g. ``un_comtrade.client``)
   still reference the old logging-side name.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

LOGGING_PY = Path(
    "un_comtrade/logging.py"
).resolve()

OLD_NAME = "DEFAULT_LOG_LEVEL"
NEW_NAME = "LOGGING_DEFAULT_LEVEL"


def _read_logging_source() -> str:
    return LOGGING_PY.read_text(encoding="utf-8")


def test_logging_module_does_not_export_old_name() -> None:
    """`DEFAULT_LOG_LEVEL` must not appear in
    `un_comtrade.logging.__all__`.
    """
    mod = importlib.import_module("un_comtrade.logging")
    assert OLD_NAME not in mod.__all__, (
        f"F-003 regression: {OLD_NAME!r} re-exported "
        f"from un_comtrade.logging.__all__"
    )


def test_logging_module_has_no_assignment_to_old_name() -> None:
    """No top-level assignment to
    `DEFAULT_LOG_LEVEL` may exist in
    `un_comtrade.logging`. The old value (an int)
    must not silently shadow the config-side
    string.
    """
    import ast

    tree = ast.parse(_read_logging_source())
    for node in tree.body:
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign) and node.target:
            targets = [node.target]
        elif isinstance(node, ast.AugAssign):
            targets = [node.target]
        for tgt in targets:
            if isinstance(tgt, ast.Name) and tgt.id == OLD_NAME:
                pytest.fail(
                    f"F-003 regression: top-level "
                    f"assignment to {OLD_NAME!r} "
                    f"remains in un_comtrade/logging.py "
                    f"at line {node.lineno}"
                )


def test_logging_module_exposes_new_constant() -> None:
    """The new canonical name must exist with the
    correct value (WARNING = 30).
    """
    import logging as _stdlib_logging

    mod = importlib.import_module("un_comtrade.logging")
    assert hasattr(mod, NEW_NAME), (
        f"F-003 regression: {NEW_NAME!r} missing "
        f"from un_comtrade.logging"
    )
    assert getattr(mod, NEW_NAME) == _stdlib_logging.WARNING


def test_logging_module_old_name_is_not_attribute() -> None:
    """Even after deleting the alias,
    `hasattr(logging, 'DEFAULT_LOG_LEVEL')` must
    return False (no accidental resurrection).
    """
    mod = importlib.import_module("un_comtrade.logging")
    assert not hasattr(mod, OLD_NAME), (
        f"F-003 regression: un_comtrade.logging "
        f"still exposes {OLD_NAME!r} as an attribute"
    )


def test_config_module_keeps_canonical_string_constant() -> None:
    """The config-side `DEFAULT_LOG_LEVEL` is the
    canonical name (str = "WARNING") and must NOT
    be touched by F-003.
    """
    mod = importlib.import_module("un_comtrade.config")
    assert hasattr(mod, OLD_NAME), (
        "F-003 must NOT touch un_comtrade.config — "
        "the canonical string constant is expected "
        "to remain at this name"
    )
    assert getattr(mod, OLD_NAME) == "WARNING"


def test_client_module_uses_new_name() -> None:
    """`un_comtrade.client` must import the new
    logging-side name. Direct access to the old
    name in `un_comtrade.client` is forbidden.
    """
    client_src = Path(
        "un_comtrade/client.py"
    ).read_text(encoding="utf-8")
    # Strip the docstring / comment references:
    # only enforce that no `DEFAULT_LOG_LEVEL` is
    # used as an identifier.
    import ast

    tree = ast.parse(client_src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == OLD_NAME:
            # The name being imported from .logging
            # is forbidden; a reference to
            # .config.DEFAULT_LOG_LEVEL is fine.
            pytest.fail(
                f"F-003 regression: "
                f"un_comtrade/client.py still "
                f"references {OLD_NAME!r} "
                f"(line {node.lineno}). Use "
                f"{NEW_NAME!r} from .logging, or "
                f"the canonical config-side name."
            )


def test_internal_callers_use_new_constant() -> None:
    """`LOGGING_DEFAULT_LEVEL` must be the value
    referenced wherever the SDK falls back to a
    default log level. `un_comtrade.client` is the
    one internal caller; verify the value flows
    end-to-end.
    """
    import logging as _stdlib_logging

    from un_comtrade.logging import LOGGING_DEFAULT_LEVEL
    from un_comtrade.config import (
        DEFAULT_LOG_LEVEL as CONFIG_DEFAULT_LOG_LEVEL,
    )

    # They MUST differ in both name and type —
    # that's the whole point of F-003.
    assert isinstance(
        LOGGING_DEFAULT_LEVEL, int
    ), f"{NEW_NAME!r} must be an int"
    assert isinstance(
        CONFIG_DEFAULT_LOG_LEVEL, str
    ), "config DEFAULT_LOG_LEVEL must remain a str"
    assert LOGGING_DEFAULT_LEVEL != CONFIG_DEFAULT_LOG_LEVEL
    assert LOGGING_DEFAULT_LEVEL == _stdlib_logging.WARNING
    assert CONFIG_DEFAULT_LOG_LEVEL == "WARNING"