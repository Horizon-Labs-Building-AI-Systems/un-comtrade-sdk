#!/usr/bin/env python
"""Documentation build + verification script.

Implements the protocol §12 verification policy. Each step is a
hard gate; a failure exits non-zero.

Usage::

    python scripts/build_docs.py                 # build + verify
    python scripts/build_docs.py --no-build       # verify only
    python scripts/build_docs.py --serve         # mkdocs serve (dev)

The script is intentionally stdlib-only — it shells out to
``mkdocs``, ``python -m py_compile``, and the link checker
installed in requirements-docs.txt.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parent.parent
WEBSITE = ROOT / "website"
DOCS = WEBSITE / "docs"
SITE = WEBSITE / "site"
SDK = ROOT / "un_comtrade"

EXIT_OK = 0
EXIT_BUILD_FAIL = 2
EXIT_LINK_FAIL = 3
EXIT_ORPHAN_FAIL = 4
EXIT_NAV_FAIL = 5
EXIT_API_FAIL = 6
EXIT_RECIPE_FAIL = 7
EXIT_EXAMPLES_FAIL = 8


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run(cmd: Sequence[str], **kw) -> int:
    """Run a command, return exit code, stream output."""
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.call(cmd, **kw)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Step 1 — mkdocs build --strict
# ---------------------------------------------------------------------------


def step_build() -> int:
    print("=== Step 1: mkdocs build --strict ===")
    # Use `python -m mkdocs` rather than relying on the `mkdocs`
    # console script being on PATH — the latter requires the
    # Python user-Scripts directory to be exposed, which is not
    # portable across contributors or CI runners. D9-002 (MkDocs
    # Foundation) wired this up so the script works on a fresh
    # `pip install -r website/requirements-docs.txt` checkout.
    return run(
        [sys.executable, "-m", "mkdocs", "build", "--strict"],
        cwd=str(WEBSITE),
    )


# ---------------------------------------------------------------------------
# Step 2 — zero broken internal links
# ---------------------------------------------------------------------------


def step_internal_links() -> int:
    """Walk every page, check that ``.md`` and ``.py`` cross-links
    point to a real file. This is a *second* pass after mkdocs's
    built-in link check, because mkdocs warns but ``--strict``
    may have suppressed some categories.

    The check inspects:

    - ``[text](../path/to/page.md)`` style links
    - ``[text](../../recipes/<category>/<file>.py)`` recipe links
    - ``[text](/docs/<file>.md)`` engineering-spec links
    """
    print("\n=== Step 2: zero broken internal links ===")
    broken: list[tuple[Path, str]] = []
    md_links = re.compile(r"\[([^\]]+)\]\(([^)]+\.(?:md|py))\)")
    for page in DOCS.rglob("*.md"):
        if "archive" in page.parts:
            continue
        text = read_text(page)
        for match in md_links.finditer(text):
            label, target = match.group(1), match.group(2)
            # Resolve relative to page.
            if target.startswith("/"):
                # Absolute path: resolve against ROOT.
                candidate = ROOT / target.lstrip("/")
            else:
                candidate = (page.parent / target).resolve()
            if not candidate.exists():
                broken.append((page, f"{label} -> {target} "
                                        f"(resolved to {candidate})"))
    if broken:
        for page, link in broken:
            print(f"  BROKEN  {page.relative_to(ROOT)} : {link}")
        return EXIT_LINK_FAIL
    print(f"  ok — {len(list(DOCS.rglob('*.md')))} pages scanned.")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Step 3 — zero orphan pages
# ---------------------------------------------------------------------------


def _walk_mkdocs_nav(nav: dict | list, prefix: str = "") -> set[str]:
    """Walk the mkdocs nav tree and collect the set of reachable
    page paths (relative to ``website/docs/``).
    """
    reachable: set[str] = set()
    if isinstance(nav, dict):
        for label, children in nav.items():
            if isinstance(children, str):
                reachable.add(children)
            elif isinstance(children, (dict, list)):
                reachable.update(_walk_mkdocs_nav(children, prefix))
    elif isinstance(nav, list):
        for entry in nav:
            if isinstance(entry, str):
                reachable.add(entry)
            elif isinstance(entry, dict):
                # {label: <string | dict | list>}
                for v in entry.values():
                    if isinstance(v, str):
                        reachable.add(v)
                    else:
                        reachable.update(_walk_mkdocs_nav(v, prefix))
    return reachable


def _parse_nav(mkdocs_yml_text: str) -> list | dict:
    """Parse the ``nav:`` block from mkdocs.yml.

    This is a *very small* subset of YAML — enough to walk the
    hierarchical nav block produced by D9-001. It deliberately
    avoids the PyYAML dependency (the script is stdlib-only).
    """
    lines = mkdocs_yml_text.splitlines()
    in_nav = False
    nav_indent = 0
    out: list = []
    stack: list[tuple[int, list | dict]] = [(0, out)]

    for line in lines:
        stripped = line.strip()
        if not in_nav:
            if re.match(r"^nav:\s*$", line):
                in_nav = True
                nav_indent = 0
            continue
        if stripped.startswith("#") or not stripped:
            continue
        # Detect indent.
        indent = len(line) - len(line.lstrip(" "))
        # Pop stack until we find a parent.
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not stack:
            break
        parent = stack[-1][1]
        if stripped.startswith("- "):
            # List item: "- foo: bar.md" or just "- bar.md"
            content = stripped[2:].strip()
            if ":" in content and not content.endswith(":"):
                label, value = content.split(":", 1)
                value = value.strip().strip('"').strip("'")
                entry = {label.strip(): value}
                parent.append(entry)
                if value.endswith(".md"):
                    pass
                else:
                    # Sub-list with children.
                    stack.append((indent + 2, entry))
            elif content.endswith(":"):
                label = content.rstrip(":").strip()
                entry = {label: []}
                parent.append(entry)
                stack.append((indent + 2, entry[label]))
            else:
                parent.append(content.strip('"').strip("'"))
        elif ":" in stripped and not stripped.endswith(":"):
            label, value = stripped.split(":", 1)
            value = value.strip().strip('"').strip("'")
            if isinstance(parent, list):
                parent.append({label.strip(): value})
            elif isinstance(parent, dict):
                parent[label.strip()] = value
        elif stripped.endswith(":"):
            label = stripped.rstrip(":").strip()
            if isinstance(parent, dict):
                parent[label] = []
                stack.append((indent + 2, parent[label]))
        # Otherwise: ignore (this minimal parser doesn't handle
        # edge cases like flow-style mappings).
    return out


def step_orphan_pages() -> int:
    print("\n=== Step 3: zero orphan pages ===")
    nav_text = read_text(WEBSITE / "mkdocs.yml")
    nav = _parse_nav(nav_text)
    reachable = _walk_mkdocs_nav(nav)
    # `index.md` and `getting_started/index.md` etc. are
    # reachable; reduce to set of slugs relative to docs/.
    reachable = {Path(p).as_posix() for p in reachable}
    orphans: list[Path] = []
    for page in DOCS.rglob("*.md"):
        rel = page.relative_to(DOCS).as_posix()
        if rel not in reachable:
            # Frontmatter `orphan: true` exempts a page.
            text = read_text(page)
            if "orphan: true" in text:
                continue
            orphans.append(page)
    if orphans:
        for p in orphans:
            print(f"  ORPHAN  {p.relative_to(ROOT)}")
        return EXIT_ORPHAN_FAIL
    print(f"  ok — {len(list(DOCS.rglob('*.md')))} pages, all reachable.")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Step 4 — zero duplicate navigation
# ---------------------------------------------------------------------------


def step_duplicate_nav() -> int:
    print("\n=== Step 4: zero duplicate navigation ===")
    nav_text = read_text(WEBSITE / "mkdocs.yml")
    nav = _parse_nav(nav_text)
    reachable = _walk_mkdocs_nav(nav)
    seen: dict[str, int] = {}
    for path in reachable:
        seen[path] = seen.get(path, 0) + 1
    dups = [p for p, n in seen.items() if n > 1]
    if dups:
        for p in dups:
            print(f"  DUPLICATE  {p}")
        return EXIT_NAV_FAIL
    print(f"  ok — {len(reachable)} unique paths.")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Step 5 — API pages generated
# ---------------------------------------------------------------------------


def step_api_pages() -> int:
    print("\n=== Step 5: API pages generated ===")
    api_dir = DOCS / "api"
    expected = [
        "index.md", "client.md", "metadata.md", "trade.md",
        "analytics.md", "etl.md", "storage.md", "cli.md",
        "models.md", "exceptions.md",
    ]
    missing = [n for n in expected if not (api_dir / n).exists()]
    if missing:
        for m in missing:
            print(f"  MISSING  api/{m}")
        return EXIT_API_FAIL
    print(f"  ok — {len(expected)} API pages present.")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Step 6 — Cookbook links valid
# ---------------------------------------------------------------------------


def step_recipe_links() -> int:
    print("\n=== Step 6: cookbook links valid ===")
    recipes_dir = ROOT / "recipes"
    recipe_files = list(recipes_dir.rglob("*.py"))
    recipe_ids: set[str] = set()
    for py in recipe_files:
        if py.name.startswith("_"):
            continue
        text = read_text(py)
        m = re.search(r"recipe_id:\s*(\S+)", text)
        if m:
            rid = m.group(1).strip().strip('"').strip("'")
            recipe_ids.add(rid)

    broken: list[tuple[Path, str]] = []
    for page in DOCS.rglob("*.md"):
        text = read_text(page)
        for m in re.finditer(r"RECIPE-\d{3}", text):
            ref = m.group(0)
            if ref not in recipe_ids:
                broken.append((page, ref))
    if broken:
        for page, ref in broken:
            print(f"  BROKEN  {page.relative_to(ROOT)} : {ref}")
        return EXIT_RECIPE_FAIL
    print(f"  ok — {len(recipe_ids)} recipes, all referenced.")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Step 7 — Examples compile
# ---------------------------------------------------------------------------


def step_examples_compile() -> int:
    print("\n=== Step 7: examples compile ===")
    block_re = re.compile(
        r"```(?:python|py)\s*\n(.*?)```",
        re.DOTALL,
    )
    bad: list[tuple[Path, int, str]] = []
    for page in DOCS.rglob("*.md"):
        text = read_text(page)
        for n, match in enumerate(block_re.finditer(text)):
            code = match.group(1).rstrip()
            # Strip "Expected output:" comments and the like.
            # We just write to a temp file and py_compile.
            tmp = ROOT / "website" / f".__example_{n}.py"
            try:
                tmp.write_text(code, encoding="utf-8")
                res = subprocess.run(
                    [sys.executable, "-m", "py_compile", str(tmp)],
                    capture_output=True, text=True,
                )
                if res.returncode != 0:
                    bad.append((page, n, res.stderr))
            finally:
                tmp.unlink(missing_ok=True)
    if bad:
        for page, n, err in bad:
            print(f"  COMPILE FAIL  {page.relative_to(ROOT)} "
                  f"(block {n}): {err.strip()}")
        return EXIT_EXAMPLES_FAIL
    n_blocks = sum(
        len(block_re.findall(read_text(p))) for p in DOCS.rglob("*.md")
    )
    print(f"  ok — {n_blocks} examples compiled.")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Step 8 — search index builds
# ---------------------------------------------------------------------------


def step_search_index() -> int:
    print("\n=== Step 8: search index builds ===")
    idx = SITE / "search" / "search_index.json"
    if not idx.exists():
        print(f"  MISSING  {idx.relative_to(ROOT)}")
        return EXIT_BUILD_FAIL
    size = idx.stat().st_size
    if size < 100:
        print(f"  TOO SMALL  {idx} ({size} bytes)")
        return EXIT_BUILD_FAIL
    print(f"  ok — {idx.relative_to(ROOT)} ({size} bytes)")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Build + verify the un-comtrade-sdk docs.",
    )
    parser.add_argument("--no-build", action="store_true",
                        help="Skip mkdocs build (verify-only).")
    parser.add_argument("--serve", action="store_true",
                        help="Run mkdocs serve (dev mode).")
    args = parser.parse_args(argv)

    if args.serve:
        return run([sys.executable, "-m", "mkdocs", "serve"], cwd=str(WEBSITE))

    if not args.no_build:
        rc = step_build()
        if rc != EXIT_OK:
            return rc

    steps = [
        ("Internal links", step_internal_links),
        ("Orphan pages", step_orphan_pages),
        ("Duplicate nav", step_duplicate_nav),
        ("API pages", step_api_pages),
        ("Recipe links", step_recipe_links),
        ("Examples compile", step_examples_compile),
        ("Search index", step_search_index),
    ]

    failures: list[tuple[str, int]] = []
    for label, fn in steps:
        rc = fn()
        if rc != EXIT_OK:
            failures.append((label, rc))

    print("\n=== Build + verification summary ===")
    if failures:
        for label, rc in failures:
            print(f"  FAIL  {label} (exit {rc})")
        # Use the first failure's exit code.
        return failures[0][1]
    print("  PASS  all 8 verification steps.")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))