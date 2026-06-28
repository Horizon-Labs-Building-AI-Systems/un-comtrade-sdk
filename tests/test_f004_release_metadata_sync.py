"""F-004 regression: package metadata is
synchronised across the canonical sources.

The `un-comtrade-sdk` package declares its
version in two places:

1. ``pyproject.toml`` ``[project] version = ...``
2. ``un_comtrade/__version__.py`` ``__version__``

These two MUST agree. If they drift, downstream
tools that read from `importlib.metadata.version()`
get a different answer than
`un_comtrade.__version__`, which breaks release
artifacts, build reproducibility, and runtime
diagnostics.

This guard verifies the version is consistent
across:

- The on-disk `pyproject.toml` parsed via
  `tomllib`.
- The runtime `un_comtrade.__version__`.
- The package metadata exposed via
  `importlib.metadata.version()` (when the
  package is import-installed).

It also asserts:

- The version string parses as a PEP 440
  `release` segment (`N.N.N`).
- Required classifiers are present.
- Required `[project.urls]` keys are present.
- Optional-dependency groups are declared.

History:

- F-004 (2026-06-29) introduced the regression
  guard after v1.0.1. Any future drift between
  `pyproject.toml` and `__version__.py` will
  fail this test.
"""

from __future__ import annotations

import importlib
import re
import sys
import tomllib
from pathlib import Path

import pytest

PYPROJECT_PATH = Path(
    "pyproject.toml"
).resolve()

VERSION_MODULE = "un_comtrade.__version__"
PACKAGE_NAME = "un-comtrade-sdk"


def _load_pyproject() -> dict:
    with PYPROJECT_PATH.open("rb") as f:
        return tomllib.load(f)


def _load_version_module() -> str:
    return importlib.import_module(VERSION_MODULE).__version__


# ---------------------------------------------------------------------------
# Version identity
# ---------------------------------------------------------------------------


def test_pyproject_version_is_pep440() -> None:
    pkg = _load_pyproject()["project"]
    version = pkg["version"]
    # PEP 440 release segment: N(.N)*
    pattern = re.compile(r"^\d+(\.\d+){0,3}$")
    assert pattern.match(version), (
        f"pyproject.toml version {version!r} is not "
        f"a PEP 440 release segment"
    )


def test_version_module_is_pep440() -> None:
    version = _load_version_module()
    pattern = re.compile(r"^\d+(\.\d+){0,3}$")
    assert pattern.match(version), (
        f"un_comtrade.__version__ {version!r} is "
        f"not a PEP 440 release segment"
    )


def test_pyproject_and_version_module_match() -> None:
    pkg = _load_pyproject()["project"]
    pyproject_version = pkg["version"]
    module_version = _load_version_module()
    assert pyproject_version == module_version, (
        f"VERSION MISMATCH: pyproject.toml says "
        f"{pyproject_version!r}, "
        f"un_comtrade.__version__ says "
        f"{module_version!r}. F-004 requires "
        f"both to agree."
    )


def test_importlib_metadata_agrees() -> None:
    """When the package is import-installed (the
    normal pip-install path),
    `importlib.metadata.version()` MUST return the
    same version as `un_comtrade.__version__`.
    """
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _v

    try:
        installed = _v(PACKAGE_NAME)
    except PackageNotFoundError:
        pytest.skip(
            f"Package {PACKAGE_NAME!r} not "
            f"import-installed; skipping "
            f"importlib.metadata check"
        )
    assert installed == _load_version_module(), (
        f"VERSION MISMATCH: importlib.metadata "
        f"reports {installed!r}, "
        f"un_comtrade.__version__ reports "
        f"{_load_version_module()!r}"
    )


def test_un_comtrade_dunder_version_exposed() -> None:
    """The runtime package re-exports
    `__version__` at the top level.
    """
    pkg = importlib.import_module("un_comtrade")
    assert hasattr(pkg, "__version__"), (
        "un_comtrade.__version__ must be exposed "
        "for `python -c \"import un_comtrade; "
        "print(un_comtrade.__version__)\"`"
    )
    assert pkg.__version__ == _load_version_module()


# ---------------------------------------------------------------------------
# Required classifiers
# ---------------------------------------------------------------------------


_REQUIRED_CLASSIFIERS = {
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Typing :: Typed",
}


def test_required_classifiers_present() -> None:
    pkg = _load_pyproject()["project"]
    classifiers = set(pkg["classifiers"])
    missing = _REQUIRED_CLASSIFIERS - classifiers
    assert not missing, (
        f"pyproject.toml is missing required "
        f"classifiers: {sorted(missing)}"
    )


def test_classifiers_no_alpha_beta_for_stable() -> None:
    """v1.0.1 is a stable release. PyPI classifiers
    MUST NOT advertise `Alpha` or `Beta` status
    alongside `Production/Stable`.
    """
    pkg = _load_pyproject()["project"]
    classifiers = list(pkg["classifiers"])
    bad_prefixes = ("Development Status :: 2 -",)
    # Note: 3 - Alpha is forbidden when 5 -
    # Production/Stable is present.
    for c in classifiers:
        if c.startswith("Development Status :: 3 -"):
            pytest.fail(
                f"v1.0.1 cannot advertise Alpha "
                f"status: {c!r}. F-004 forbids "
                f"co-existence with "
                f"'Production/Stable'."
            )
        if c.startswith("Development Status :: 4 -"):
            pytest.fail(
                f"v1.0.1 cannot advertise Beta "
                f"status: {c!r}."
            )


# ---------------------------------------------------------------------------
# Project URLs
# ---------------------------------------------------------------------------


_REQUIRED_URLS = {"Homepage", "Documentation", "Repository", "Issues"}


def test_required_project_urls_present() -> None:
    pkg = _load_pyproject()["project"]
    urls = set(pkg.get("urls", {}).keys())
    missing = _REQUIRED_URLS - urls
    assert not missing, (
        f"pyproject.toml [project.urls] is "
        f"missing required keys: {sorted(missing)}"
    )


# ---------------------------------------------------------------------------
# Optional dependencies
# ---------------------------------------------------------------------------


_REQUIRED_OPTIONAL_GROUPS = {"parquet", "duckdb", "dev"}


def test_optional_dependencies_declared() -> None:
    pkg = _load_pyproject()["project"]
    opt = pkg.get("optional-dependencies", {})
    missing = _REQUIRED_OPTIONAL_GROUPS - set(opt.keys())
    assert not missing, (
        f"pyproject.toml "
        f"[project.optional-dependencies] is "
        f"missing groups: {sorted(missing)}"
    )


def test_parquet_optional_depends_on_pyarrow() -> None:
    """The parquet group MUST declare pyarrow
    (or the SDK should not claim parquet
    support).
    """
    pkg = _load_pyproject()["project"]
    parquet = pkg["optional-dependencies"]["parquet"]
    assert any(
        "pyarrow" in dep for dep in parquet
    ), "parquet optional-dependency must include pyarrow"


def test_duckdb_optional_depends_on_duckdb() -> None:
    """The duckdb group MUST declare duckdb."""
    pkg = _load_pyproject()["project"]
    duckdb = pkg["optional-dependencies"]["duckdb"]
    assert any(
        "duckdb" in dep for dep in duckdb
    ), "duckdb optional-dependency must include duckdb"


# ---------------------------------------------------------------------------
# Python compatibility
# ---------------------------------------------------------------------------


def test_requires_python_at_least_3_11() -> None:
    pkg = _load_pyproject()["project"]
    rp = pkg["requires-python"]
    # Parse the floor; e.g. ">=3.11" → (3, 11).
    m = re.match(r">=(\d+)\.(\d+)", rp)
    assert m, (
        f"requires-python {rp!r} does not start "
        f"with '>='. ADR-0017 mandates 3.11+."
    )
    major, minor = int(m.group(1)), int(m.group(2))
    assert (major, minor) >= (3, 11), (
        f"ADR-0017 requires Python >= 3.11; "
        f"pyproject.toml says {rp!r}"
    )


# ---------------------------------------------------------------------------
# No accidental version duplication in the source
# ---------------------------------------------------------------------------


def test_no_stray_version_assignment_outside_canonical() -> None:
    """The only places allowed to declare the
    package version string are:

    1. ``pyproject.toml`` ``[project] version``
    2. ``un_comtrade/__version__.py`` ``__version__``

    The legacy ``comtrade/__init__.py`` package
    is a separate, undelivered reference client
    and may keep its own independent version
    (NOT in the wheel). All other
    ``version = "..."`` assignments in the SDK
    source are forbidden.
    """
    forbidden_paths = []
    allow = {
        PYPROJECT_PATH.resolve(),
        Path("un_comtrade/__version__.py").resolve(),
    }
    for src_path in Path("un_comtrade").rglob("*.py"):
        if src_path.resolve() in allow:
            continue
        text = src_path.read_text(encoding="utf-8")
        if re.search(
            r'^__version__\s*=\s*[\"\']\d', text, re.M
        ):
            forbidden_paths.append(src_path)
        elif re.search(
            r'^version\s*=\s*[\"\']\d', text, re.M
        ):
            forbidden_paths.append(src_path)
    assert not forbidden_paths, (
        f"Forbidden version declarations in "
        f"un_comtrade/ source: "
        f"{[str(p) for p in forbidden_paths]}"
    )