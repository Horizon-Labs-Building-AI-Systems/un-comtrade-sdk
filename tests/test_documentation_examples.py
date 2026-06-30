"""Documentation example verification (D9-017).

This test enforces protocol §6 (page standards) and §12.8 (example
compilation) on every documentation page. It is the runtime
companion to ``scripts/build_docs.py`` Step 7 (which only does
``py_compile``).

Specifically this test checks:

1. Every page has the required frontmatter keys (title, description,
   audience per §6.1).
2. Every page has the required H2 sections (Purpose, Prerequisites,
   Walkthrough, Examples, Related Recipes, Related API, Related
   Guides, Next steps per §6.2) OR an explicit ``skips:`` list.
3. Every Python code block parses without errors (per §12.8).
4. Every Python code block imports only public SDK symbols (per
   §1.2 and §7.4).
5. Every ``RECIPE-NNN`` reference matches a real recipe (per §12.6).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "website" / "docs"
RECIPES = ROOT / "recipes"

# Section names from protocol §6.2.
REQUIRED_H2 = [
    "Purpose",
    "Prerequisites",
    "Walkthrough",
    "Examples",
    "Related Recipes",
    "Related API",
    "Related Guides",
    "Next steps",
]

# Frontmatter keys from protocol §6.1 (required at minimum).
REQUIRED_FRONT = ["title", "description", "audience"]

# Audiences from protocol §2.
VALID_AUDIENCES = {
    "first-time", "python", "cli", "analyst",
    "contributor", "maintainer", "all",
}


def _pages() -> list[Path]:
    return [p for p in DOCS.rglob("*.md") if "archive" not in p.parts]


@pytest.fixture(scope="module")
def all_pages() -> list[Path]:
    return _pages()


# ---------------------------------------------------------------------------
# §6.1 — Frontmatter
# ---------------------------------------------------------------------------


def test_frontmatter_present(all_pages):
    """Every page declares the required frontmatter keys."""
    for page in all_pages:
        text = page.read_text(encoding="utf-8")
        assert text.startswith("---\n"), (
            f"{page.relative_to(ROOT)}: missing YAML frontmatter"
        )
        # Find closing ---.
        m = re.search(r"^---\s*$", text[4:], re.MULTILINE)
        assert m, f"{page.relative_to(ROOT)}: unterminated frontmatter"
        front = text[4 : 4 + m.start()]
        for key in REQUIRED_FRONT:
            assert f"{key}:" in front, (
                f"{page.relative_to(ROOT)}: missing frontmatter key {key!r}"
            )


def test_audience_is_valid(all_pages):
    """The audience field uses one of the seven §2 values."""
    for page in all_pages:
        text = page.read_text(encoding="utf-8")
        m = re.search(r"^audience:\s*(\S+)", text, re.MULTILINE)
        if m:
            audience = m.group(1)
            assert audience in VALID_AUDIENCES, (
                f"{page.relative_to(ROOT)}: invalid audience {audience!r} "
                f"(must be one of {sorted(VALID_AUDIENCES)})"
            )


# ---------------------------------------------------------------------------
# §6.2 — Required sections
# ---------------------------------------------------------------------------


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter, body) from a Markdown file."""
    if not text.startswith("---\n"):
        return "", text
    m = re.search(r"^---\s*$", text[4:], re.MULTILINE)
    if not m:
        return "", text
    return text[4 : 4 + m.start()], text[4 + m.end() :]


def test_required_sections_present(all_pages):
    """Every page has the 8 required H2 sections OR an explicit skips list."""
    for page in all_pages:
        text = page.read_text(encoding="utf-8")
        front, body = _split_frontmatter(text)
        # Find explicit skips list.
        if "skips:" in front:
            continue
        h2s = set(re.findall(r"^##\s+(.+?)\s*$", body, re.MULTILINE))
        missing = [s for s in REQUIRED_H2 if s not in h2s]
        assert not missing, (
            f"{page.relative_to(ROOT)}: missing required H2 sections "
            f"{missing}"
        )


# ---------------------------------------------------------------------------
# §12.8 — Examples compile
# ---------------------------------------------------------------------------


PY_BLOCK = re.compile(r"```(?:python|py)\s*\n(.*?)```", re.DOTALL)


def test_python_blocks_parse(all_pages):
    """Every fenced Python block parses without errors (per §12.8)."""
    for page in all_pages:
        text = page.read_text(encoding="utf-8")
        for n, match in enumerate(PY_BLOCK.finditer(text)):
            code = match.group(1).rstrip()
            tmp = ROOT / f".__doc_test_{page.stem}_{n}.py"
            try:
                tmp.write_text(code, encoding="utf-8")
                res = subprocess.run(
                    [sys.executable, "-m", "py_compile", str(tmp)],
                    capture_output=True, text=True,
                )
                assert res.returncode == 0, (
                    f"{page.relative_to(ROOT)} (block {n}): "
                    f"{res.stderr.strip()}"
                )
            finally:
                tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# §1.2 / §7.4 — Public SDK only
# ---------------------------------------------------------------------------


PRIVATE_IMPORT = re.compile(r"^\s*from\s+un_comtrade\._\w+\s+import", re.MULTILINE)


def test_no_private_imports(all_pages):
    """No Python block imports an internal (underscore-prefixed) module."""
    for page in all_pages:
        text = page.read_text(encoding="utf-8")
        for n, match in enumerate(PY_BLOCK.finditer(text)):
            code = match.group(1)
            m = PRIVATE_IMPORT.search(code)
            assert not m, (
                f"{page.relative_to(ROOT)} (block {n}): "
                f"private import detected: {m.group(0).strip()}"
            )


# ---------------------------------------------------------------------------
# §12.6 — Cookbook links valid
# ---------------------------------------------------------------------------


def test_recipe_references_exist(all_pages):
    """Every RECIPE-NNN reference points to a real recipe."""
    recipe_ids: set[str] = set()
    for py in RECIPES.rglob("*.py"):
        if py.name.startswith("_"):
            continue
        text = py.read_text(encoding="utf-8")
        m = re.search(r"recipe_id:\s*(\S+)", text)
        if m:
            recipe_ids.add(m.group(1).strip().strip('"').strip("'"))

    for page in all_pages:
        text = page.read_text(encoding="utf-8")
        for m in re.finditer(r"RECIPE-\d{3}", text):
            rid = m.group(0)
            assert rid in recipe_ids, (
                f"{page.relative_to(ROOT)}: references unknown recipe {rid}"
            )


# ---------------------------------------------------------------------------
# Sanity
# ---------------------------------------------------------------------------


def test_pages_collected():
    """Sanity check — there should be at least 30 documentation pages."""
    pages = _pages()
    assert len(pages) >= 30, f"expected ≥30 pages, got {len(pages)}"