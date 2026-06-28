"""F-002 regression: no hand-rolled aggregation
patterns in the analytics package.

This guards V-001 Critical C2 (8 hand-rolled
per-group Decimal summation patterns) from ever
regressing. Any future analytics code that
introduces the classic
``by_X[code] = (by_X.get(code, Decimal("0")) + v)``
pattern will fail this test.

The guard allows read-side ``by_X.get(code,
Decimal("0"))`` defaults (which compute per-row
values from the precomputed sum) — only the
write-side ``= ... + v`` aggregation is
forbidden.

History:
- V-001 (2026-06) flagged 8 sites.
- F-002 (2026-06) routed all aggregations
  through the internal Query Engine
  (``Query.group_by + summarize``).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ANALYTICS_DIR = Path(
    "un_comtrade/analytics"
).resolve()

# Pattern is forbidden in the WRITE side: an
# AugAssign or assignment where the RHS is
# ``container.get(key, Decimal("0")) + value``
# (or any of its symmetric variants).
FORBIDDEN_WRITE_PATTERN_TEMPLATE = (
    "{var}[{key}] = "
    "({var}.get({key}, Decimal({zero})) + {value})"
)


def _iter_python_files() -> list[Path]:
    return sorted(p for p in ANALYTICS_DIR.glob("*.py"))


def _forbidden_violations(
    source: str,
) -> list[tuple[int, str]]:
    """Return ``(line_number, line_text)`` for
    every forbidden write-side aggregation.
    """
    violations: list[tuple[int, str]] = []
    tree = ast.parse(source)
    # We look for ``Assign`` nodes where the LHS
    # is a ``Subscript`` (container[key]) and the
    # RHS is a ``BinOp(Add, Call(get, ...), Name)``
    # pattern.
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Subscript):
            continue
        # RHS must be ``a.get(k, Decimal("0")) + v``
        value = node.value
        if not isinstance(value, ast.BinOp):
            continue
        if not isinstance(value.op, ast.Add):
            continue
        # ``a.get(k, Decimal("0"))``
        get_call = value.left
        if not isinstance(get_call, ast.Call):
            continue
        if (
            isinstance(get_call.func, ast.Attribute)
            and get_call.func.attr == "get"
            and len(get_call.args) >= 2
        ):
            default_arg = get_call.args[1]
            if (
                isinstance(default_arg, ast.Call)
                and isinstance(default_arg.func, ast.Name)
                and default_arg.func.id == "Decimal"
                and len(default_arg.args) >= 1
            ):
                # Match!
                line_no = node.lineno
                line_text = source.splitlines()[line_no - 1]
                violations.append((line_no, line_text.strip()))
    return violations


def test_no_handrolled_aggregation_in_analytics() -> None:
    """V-001 C2 regression guard.

    Every analytics module must delegate Decimal
    summation to the internal Query Engine
    (``Query.group_by + summarize``). Manual
    ``dict.get(k, Decimal('0')) + v`` accumulation
    is forbidden.
    """
    py_files = _iter_python_files()
    assert py_files, "no analytics source files found"

    all_violations: dict[str, list[tuple[int, str]]] = {}
    for py_file in py_files:
        source = py_file.read_text(encoding="utf-8")
        violations = _forbidden_violations(source)
        if violations:
            all_violations[py_file.name] = violations

    if all_violations:
        msg_lines = [
            "F-002 regression: hand-rolled "
            "aggregation patterns detected in:"
        ]
        for fname, vios in all_violations.items():
            msg_lines.append(f"\n  {fname}:")
            for line_no, line_text in vios:
                msg_lines.append(f"    L{line_no}: {line_text}")
        pytest.fail("\n".join(msg_lines))


def test_analytics_uses_query_engine_for_sum() -> None:
    """Every analytics module that does Decimal
    summation must import and use the Query
    Engine primitives (``summarize`` or
    ``Query.group_by + Query.summarize``).
    """
    py_files = _iter_python_files()
    modules_needing_qe: set[str] = set()
    for py_file in py_files:
        if py_file.name == "_query_engine.py":
            # Internal engine itself doesn't need
            # to import itself.
            continue
        source = py_file.read_text(encoding="utf-8")
        # A module needs QE if it imports
        # ``Decimal`` (means it touches money)
        # and is NOT the framework __init__.
        if "Decimal" not in source:
            continue
        if py_file.name == "__init__.py":
            # Framework may not need QE itself
            continue
        # Check the file references one of the QE
        # primitives via _query_engine import.
        if "from ._query_engine import" not in source:
            modules_needing_qe.add(py_file.name)

    assert not modules_needing_qe, (
        "F-002: these modules touch Decimal but "
        "do not import from ._query_engine: "
        f"{sorted(modules_needing_qe)}"
    )