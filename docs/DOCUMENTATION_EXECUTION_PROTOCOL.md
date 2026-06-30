```
Document ID
035

Title
Documentation Execution Protocol

Version
1.0.0

Status
LIVE

Created
2026-06-30T00:55:00Z

Last Updated
2026-06-30T00:55:00Z

Author
Mavis (D9-000)

Project
UN Comtrade Python SDK

Dependencies
docs/034_COOKBOOK_REVIEW.md
recipes/README.md
docs/007_SDK_SPECIFICATION.md
docs/032_v1_RELEASE_NOTES.md

Supersedes
None
```

---

# Documentation Execution Protocol (D9-000)

## 0. Purpose

This document is the **authoritative instruction manual** for every
subsequent documentation task in Phase 9 (Documentation Website) and
beyond. It defines:

- The documentation philosophy.
- The supported audiences and their entry points.
- The architecture, navigation, and URL conventions.
- The page standards and cross-link rules.
- The example, API reference, cookbook integration, versioning, search,
  verification, and quality-gate policies.
- The official Phase 9 execution order (D9-001..D9-018).

No website implementation, MkDocs installation, Markdown migration, or
configuration file SHALL be produced until the corresponding tasks
in §14 read this document and produce work that conforms to it.

Every future documentation task SHALL read this document before
implementation. The task is incomplete if any clause below is violated.

---

# 1. Documentation Principles

The documentation system is governed by the following principles.
A page, recipe reference, or API entry that violates any of these
SHALL be rejected at review.

## 1.1 User-first

Documentation is written for the reader, not for the author or the
SDK maintainer. Every page answers a specific question a user would
ask. A page that exists only to mirror internal engineering artefacts
SHALL be removed.

## 1.2 Public SDK only

Documentation SHALL describe the **frozen public SDK** (the symbols
exported via `un_comtrade/__init__.py`'s `__all__`, the public
submodules listed in `tests/test_recipes_verification.py`'s
`PUBLIC_TOP_LEVEL_MODULES` allowlist, and the documented surface in
`docs/007_SDK_SPECIFICATION.md` §3.4). Documentation SHALL NOT
describe internal modules — `un_comtrade._foo`, `un_comtrade.storage._base`,
`un_comtrade.analytics._query_engine`, or any underscore-prefixed
symbol. A recipe that documents an internal path is a documentation
bug, not a recipe enhancement.

## 1.3 Cookbook is the executable source of examples

The Cookbook (`recipes/`) is the **authoritative source of runnable
examples**. Documentation pages SHALL reference recipes rather than
duplicating code. When a guide page needs a code example, it SHALL
embed a minimal snippet that demonstrates the API call and link to
the relevant recipe for the full executable form.

## 1.4 API reference is generated

The API reference SHALL be generated from the SDK's docstrings via
mkdocstrings (or equivalent). No manually-edited API pages are
permitted; manual edits SHALL be rejected at review. Generation SHALL
be wired into the documentation build so a docstring edit
automatically flows to the published API reference.

## 1.5 Examples compile and execute

Every code example on every documentation page SHALL be:

- Syntactically valid Python that parses without errors.
- Importable against the public SDK (no private imports).
- Executable against mocks for offline CI verification.

The documentation build pipeline SHALL run a linter that catches
broken examples; the example SHALL be considered broken if it cannot
be parsed.

## 1.6 Cross-references are bidirectional

Every documentation page that references an API symbol, a recipe,
or another page SHALL be referenced back from the target wherever
the target exposes a "See also" section. The build pipeline SHALL
warn on asymmetric references and fail the build on broken ones.

## 1.7 Stability over novelty

Documentation reflects the **frozen** public API. A documentation
update that anticipates an unreleased API change SHALL be deferred
to the release that introduces the change. The docs version SHALL
match the SDK version it describes (§10).

---

# 2. Audience Definition

The documentation system supports six audiences. Each audience has
a defined goal, an entry page, and an expected knowledge baseline.

## 2.1 First-time users

- **Goal**: install the SDK and run a hello-world query against
  the UN Comtrade API.
- **Entry page**: `getting-started/index.md` (the landing page).
- **Expected knowledge**: basic Python (interpreter installed,
  pip understood). No prior knowledge of the SDK, the UN
  Comtrade API, or trade data formats.

## 2.2 Python developers

- **Goal**: integrate the SDK into a script or application; use
  the SDK programmatically to fetch, parse, and analyse trade
  data.
- **Entry page**: `guides/python/index.md` (the "Python SDK" guide).
- **Expected knowledge**: idiomatic Python (typing, dataclasses,
  context managers). Comfortable with `pip install`, virtualenvs,
  and reading API documentation.

## 2.3 CLI users

- **Goal**: drive the SDK from a terminal or shell script; chain
  commands; pipe output to other Unix tools.
- **Entry page**: `guides/cli/index.md` (the "Command-line" guide).
- **Expected knowledge**: comfortable on a POSIX or PowerShell
  shell. Familiar with environment variables. No Python required.

## 2.4 Data analysts

- **Goal**: explore UN Comtrade trade data interactively;
  compute country summaries, partner rankings, and HS-code
  breakdowns; export results to CSV, Parquet, DuckDB, or
  Markdown.
- **Entry page**: `guides/analysts/index.md` (the "Data Analysis
  with the SDK" guide).
- **Expected knowledge**: pandas, Jupyter notebooks, SQL
  basics, Parquet/DuckDB concepts. Familiar with trade-data
  vocabulary (reporter, partner, HS code).

## 2.5 Contributors

- **Goal**: extend the SDK; add a new analytics function, a new
  storage backend, or a new CLI command; submit a pull request.
- **Entry page**: `architecture/contributing.md` (the
  "Contributing" page under Architecture).
- **Expected knowledge**: the SDK's public surface
  (`docs/007_SDK_SPECIFICATION.md`), the testing standard
  (`docs/013_TESTING_STANDARD.md`), and the cookbook verification
  suite (`tests/test_recipes_verification.py`).

## 2.6 Maintainers

- **Goal**: cut a release; sync the documentation version with the
  SDK version; deprecate pages; write migration guides.
- **Entry page**: `release-notes/index.md` (release notes index).
- **Expected knowledge**: the full engineering specification
  set (`docs/`), the cookbook review gate
  (`docs/034_COOKBOOK_REVIEW.md`), and the semantic-versioning
  policy (`docs/028_SEMANTIC_VERSION_AUDIT.md`).

---

# 3. Documentation Architecture

The documentation hierarchy is **fixed** at seven top-level
sections. The site SHALL NOT introduce new top-level sections
without updating this protocol first.

## 3.1 Top-level sections

| Section        | Path                  | Audience emphasis              | Purpose                                                                 |
| -------------- | --------------------- | ------------------------------ | ----------------------------------------------------------------------- |
| Home           | `index.md`            | All                            | Landing page; quick links to Getting Started, Cookbook, API reference. |
| Getting Started| `getting-started/`    | First-time users, CLI users    | Install, configure, run a first query.                                   |
| Guides         | `guides/`             | All (Python, CLI, analysts)    | Task-oriented walkthroughs; per-service guides.                          |
| Cookbook       | `cookbook/`           | All                            | Index of cookbook recipes grouped by category.                          |
| API            | `api/`                | Python developers              | Generated reference for every public symbol.                            |
| Architecture   | `architecture/`       | Contributors, maintainers      | SDK design; testing standard; release process.                           |
| Release Notes  | `release-notes/`      | Maintainers, returning users   | Versioned changelog; migration guides for breaking changes.            |

## 3.2 Maximum navigation depth

The navigation tree SHALL NOT exceed **three (3) levels** below
the home page. That is:

- L0: home (`/`)
- L1: top-level section (`/getting-started/`)
- L2: section page (`/getting-started/installation/`)
- L3: leaf page (`/getting-started/installation/windows.md`)

L4 or deeper pages are rejected at review. The hierarchy's job
is to be **shallow**; if a topic needs L4, it is a sign the topic
should be split across L3 pages or moved to a sub-section at L2.

## 3.3 URL conventions

URL paths SHALL follow these conventions:

- All lowercase.
- Words separated by single hyphens (`-`); never underscores.
- No trailing slash.
- No file extensions in the URL (the MkDocs build produces
  `.html`; navigation references the slug, not the filename).
- Short, descriptive, stable. A URL SHALL NOT change once
  published unless the page's identity changes (a deprecated
  page SHALL redirect, not 404).
- Plurals for collection pages (`/guides/python/`); singulars
  for individual pages (`/cookbook/recipe-031/`).

## 3.4 Folder conventions

Folders under `website/docs/` mirror the URL hierarchy. The
folder structure is fixed at the layout in §4. New folders at L1
require a protocol amendment.

---

# 4. Website Structure

The website lives under `website/`. It is **separate from the
engineering specifications** under `docs/`. The two SHALL NOT be
merged: engineering specs are normative; website pages are
user-facing.

## 4.1 Directory layout

```
website/
    mkdocs.yml                 # build config (created in D9-002)
    docs/
        index.md               # landing page (Home, L0)
        getting_started/       # L1
            index.md
            installation.md
            quick_start.md
            authentication.md
        guides/                # L1
            index.md
            python/
                index.md
                metadata.md
                trade.md
                analytics.md
                etl.md
                storage.md
            cli/
                index.md
                metadata.md
                trade.md
                analytics.md
                storage.md
                etl.md
            analysts/
                index.md
                exploration.md
                reporting.md
        cookbook/              # L1
            index.md
            metadata.md
            trade.md
            analytics.md
            storage.md
            cli.md
            end_to_end.md
        api/                    # L1 (generated)
            index.md
            client.md
            metadata.md
            trade.md
            analytics.md
            etl.md
            storage.md
            cli.md
            models.md
            exceptions.md
        architecture/           # L1
            index.md
            sdk_overview.md
            contributing.md
            cookbook.md
            testing.md
        release_notes/          # L1
            index.md
            v1.md
            migration.md
        assets/
            images/
            stylesheets/
            javascripts/
    overrides/
        main.html
```

## 4.2 Engineering specs remain in `docs/`

The pre-existing `docs/` directory contains the engineering
specifications (specs 000..033, the cookbook review, the
implementation logs). It SHALL NOT be merged with `website/docs/`.
The engineering specs are referenced from the website via
**explicit cross-links**, not by content duplication.

## 4.3 Cookbook remains in `recipes/`

The cookbook (`recipes/`) is the executable source of examples. The
website's `cookbook/` directory is a **browsable index** that links
to each recipe file in `recipes/`. A recipe's content is **not
duplicated** on the website; the website links to the file and
renders its frontmatter (title, difficulty, runtime, API key flag)
as a card.

---

# 5. Navigation Rules

## 5.1 Sidebar policy

- The MkDocs sidebar SHALL render the **full** documentation tree
  (all L1 sections visible at all times).
- The current page's section is **expanded**; other sections are
  **collapsed by default** but their section index is always visible.
- The sidebar order is fixed at the order in §4.1 (Home, Getting
  Started, Guides, Cookbook, API, Architecture, Release Notes).
  Re-ordering requires a protocol amendment.

## 5.2 Breadcrumbs

Every page SHALL display a breadcrumb trail of the form
`Home > Section > Sub-section > Page`. The breadcrumb is generated
by MkDocs from the navigation tree; no manual breadcrumbs.

## 5.3 Previous / next links

MkDocs generates **previous** and **next** links from the
navigation tree. The order within each section is determined by
the order of pages in `mkdocs.yml`'s `nav:` block. A task that adds
a new page SHALL set its position explicitly; "appended to the end"
is rejected at review unless the page is the last in its section.

## 5.4 Cross-link strategy

- **API references** use MkDocs' autolink extension
  (`<https://docs.uncomtrade.org/un_comtrade.ComtradeClient>`)
  for symbol references.
- **Recipe references** use a relative path
  (`../../recipes/storage/02_export_csv.py`) so the link survives
  site moves.
- **Engineering spec references** use an absolute URL
  (`/docs/012_STORAGE_SPECIFICATION.md`) — the engineering docs are
  served from a separate path.
- **Internal section references** use the MkDocs
  `[link text](../section/page.md)` syntax.

The build pipeline SHALL run a link checker on every build;
broken links fail the build.

## 5.5 Orphan-page policy

A page is **orphaned** when it cannot be reached from the home
page via the navigation tree. The build pipeline SHALL detect
orphans and fail the build. A page is exempt from orphan detection
only when:

- It is a **redirect source** (a deprecated page that points to
  the replacement).
- It is in the `assets/` directory (a non-page artefact).
- It is an explicit **archive** page listed under
  `release-notes/archive/` with the `orphan: true` flag in its
  frontmatter.

---

# 6. Page Standards

Every documentation page (under `website/docs/`) SHALL define
the following frontmatter and content sections. The build pipeline
SHALL fail on pages that omit required sections.

## 6.1 Frontmatter

```yaml
---
title: <Page title — verb form, e.g. "Install the SDK">
description: <One-sentence summary, ≤160 chars>
audience: <first-time | python | cli | analyst | contributor | maintainer>
prerequisites:
  - <URL or page slug>
related_recipes:
  - <RECIPE-NNN>
related_api:
  - <symbol>
related_guides:
  - <URL or page slug>
---
```

Required keys: `title`, `description`, `audience`. The other keys
are required when the page has applicable references; a page
without any related recipe/API/guide still requires the section
with an empty list.

## 6.2 Content sections

Pages SHALL be organised under the following H2 sections, in this
order:

1. **Purpose** — what this page covers and who it's for.
2. **Prerequisites** — what the reader must know or have
   installed before following the page.
3. **Walkthrough** — the body of the page (steps, examples,
   explanations). May be multiple H3 sub-sections.
4. **Examples** — code snippets. Each snippet SHALL be a
   fenced block with a `python` language tag and a comment
   showing the expected output (where deterministic).
5. **Related Recipes** — list of recipe IDs with one-line
   descriptions, linking to the recipe file in `recipes/`.
6. **Related API** — list of public SDK symbols the page
   uses, linking to the generated API reference.
7. **Related Guides** — list of related guide pages.
8. **Next steps** — one-paragraph signpost to the next page
   in the natural reading order.

The build pipeline SHALL verify each page contains all eight H2
sections (or have an explicit `skips: [...]` list in frontmatter
for pages where a section does not apply).

## 6.3 Heading depth

Pages SHALL use H2 (`##`) for top-level sections and H3 (`###`)
for sub-sections. H1 is reserved for the page title (the `title:`
frontmatter field). H4 and deeper are discouraged; a page that
needs H4 should be split.

## 6.4 Code examples

Code blocks SHALL be fenced with the language tag (`python`,
`bash`, `yaml`, `json`). The build pipeline SHALL run `python -m
py_compile` on every fenced Python block in offline mode (the
example SHALL parse). Where the example is too long for the page
context, the page SHALL embed the first 5–15 lines and link to
the cookbook recipe for the full executable form.

---

# 7. Example Policy

Code examples on documentation pages SHALL conform to the
following rules. Examples that violate any rule are rejected at
review.

## 7.1 Public SDK only

Examples SHALL import only public SDK symbols. A page that
documents a private symbol (`un_comtrade._foo`,
`un_comtrade.storage._base`) is a documentation bug and SHALL be
removed or rewritten.

## 7.2 Examples SHALL execute

Examples SHALL be syntactically valid Python and SHALL import
without errors against the documented public SDK. The build
pipeline runs a syntax check on every Python block; a parse error
fails the build.

Examples that perform I/O (network calls, file writes) SHALL
include a "mock mode" variant for offline CI verification, or
SHALL be clearly marked as requiring a configured API key.

## 7.3 Examples SHALL reference Cookbook

When a guide page needs more than a one-call code snippet, the
example SHALL link to the relevant recipe file in `recipes/`.
The Cookbook is the **executable source**; the page is the
**conceptual narrative**. A page that duplicates a recipe's full
code is a maintenance liability and SHALL be rewritten to link
instead.

## 7.4 Examples SHALL NOT import internal modules

The example's import lines SHALL pass the
`TestRecipeImports.test_recipe_does_not_import_underscore_module`
check (see `tests/test_recipes_verification.py`). An example that
imports a private module fails the documentation build.

## 7.5 Examples SHALL handle errors

Examples that perform network calls SHALL wrap them in the
documented error-handling pattern:

```python
from un_comtrade import ComtradeClient
from un_comtrade.exceptions import ComtradeError

try:
    with ComtradeClient() as client:
        result = client.trade.get_exports(reporter_code=699, period="2022")
except ComtradeError as exc:
    print(f"un-comtrade error: {exc}")
```

A code snippet that performs network I/O without a `try/except`
SHALL be flagged at review and SHAL not ship.

---

# 8. API Reference Policy

## 8.1 Generated from docstrings

The API reference SHALL be generated via mkdocstrings
(or equivalent: pdoc, sphinx-autodoc). No manually-edited API
pages are permitted. The generation pipeline is wired into the
MkDocs build so a docstring edit propagates to the published
reference automatically.

## 8.2 No manual duplication

An API page SHALL NOT contain content that duplicates the
docstring. The page renders the docstring verbatim (with the
chosen theme's formatting); adding prose around the rendered
docstring is permitted only as a **conceptual overview** above
the auto-generated block.

## 8.3 Public SDK only

The API reference SHALL render only public symbols. Underscore-
prefixed symbols and the contents of private modules SHALL be
excluded from the build via the generation tool's `members:`
configuration.

## 8.4 Version synchronization

The API reference version SHALL match the SDK version it
describes. The build pipeline SHALL verify the
`un_comtrade.__version__` value against the MkDocs `site_url`
configuration and the release-notes page. A mismatch fails the
build.

---

# 9. Cookbook Integration Policy

## 9.1 Recipes are authoritative

The Cookbook (`recipes/`) is the **executable source of examples**.
Each recipe's frontmatter is the contract; the recipe body is
the implementation; the per-recipe test (`tests/test_recipes_*.py`)
is the runtime verification. The website does NOT replace any of
these.

## 9.2 Documentation links to recipes

Documentation pages SHALL reference recipes by recipe_id
(`RECIPE-NNN`) and link to the recipe file under
`../../recipes/<category>/<file>.py`. The link is a relative
path so the website remains portable.

The website's `cookbook/` section is a **browsable index** with
one entry per recipe, organised by category. Each entry card
displays the recipe's:

- Title (from `title:` frontmatter)
- Difficulty (from `difficulty:`)
- Estimated runtime (from `estimated_runtime:`)
- API-key flag (from `requires_api_key:`)
- One-line description (first paragraph of the docstring)
- A link to the recipe file and to the per-recipe test file

## 9.3 Recipes are not copied into documentation

A documentation page SHALL NOT contain the full body of a recipe.
The page links to the recipe and embeds a brief excerpt (≤15 lines)
that demonstrates the API call in the page's narrative context.

## 9.4 Cookbook version

The Cookbook version SHALL match the SDK version. A cookbook
recipe that targets a future SDK feature SHALL be marked
`PROPOSED` in the per-category README and excluded from the
published website until the SDK ships that feature.

---

# 10. Versioning Policy

## 10.1 Documentation version

The documentation site is versioned alongside the SDK. The
version string matches the SDK's `__version__` value (per the
semantic-versioning policy in `docs/028_SEMANTIC_VERSION_AUDIT.md`).

## 10.2 SDK version synchronization

The build pipeline SHALL verify that:

- The documentation version matches
  `un_comtrade.__version__`.
- The release-notes index has an entry for the current version.
- The migration guide references any breaking changes since
  the previous version.

A mismatch fails the build.

## 10.3 Release notes

A release-notes entry SHALL be published for every SDK release.
Each entry includes:

- Version number and release date.
- **Added** — new features (with cookbook recipe IDs).
- **Changed** — modifications to existing features.
- **Deprecated** — features marked for removal.
- **Removed** — features removed in this release.
- **Fixed** — bug fixes (linked to GitHub issues where available).
- **Security** — security fixes (CVE references where applicable).

The release-notes page SHALL be linked from the home page's
"What's new" callout.

## 10.4 Deprecated pages

A page is **deprecated** when its target audience or its
underlying API feature is deprecated. A deprecated page SHALL:

- Display a banner at the top: "Deprecated since v1.X. See the
  replacement page here: [link]."
- Set `deprecated: true` in frontmatter.
- Continue to render in the navigation (with a struck-through
  sidebar entry) for **two minor releases** before being
  redirected.

## 10.5 Migration guides

A breaking change SHALL ship with a **migration guide** under
`release-notes/migration.md`. The guide covers:

- What changed (a one-paragraph summary).
- Who is affected (the audience + the cookbook recipe IDs).
- How to migrate (concrete before/after code snippets).
- A timeline (when the deprecation was announced, when the
  removal will ship).

---

# 11. Search Policy

## 11.1 Searchable content

The MkDocs search index includes:

- All page titles (`title:` frontmatter).
- All page descriptions (`description:` frontmatter).
- All H2 and H3 headings on every page.
- All code-block captions and "Examples" section content.
- All recipe titles and recipe_id values.
- All API symbol names.

## 11.2 Excluded content

The search index excludes:

- Engineering specs under `docs/` (not part of the website).
- Generated API pages (rendered separately; their content is
  mirrored in the symbol index).
- Pages with `search-exclude: true` in frontmatter (e.g.,
  internal planning pages).
- The `assets/` directory (images, stylesheets).

## 11.3 Tags

Pages SHALL set tags in frontmatter where applicable:

```yaml
tags:
  - getting-started
  - install
  - python
```

Tags are surfaced in the page footer and feed into the search
filter UI.

## 11.4 Indexing rules

- The search index is rebuilt on every `mkdocs build`.
- The index is stored under `website/site/search/` (generated)
  and is served as a static JSON file.
- The build pipeline SHALL verify the index contains at least
  one entry per public page; a missing entry fails the build.

---

# 12. Verification Policy

Every documentation build SHALL verify the following. A failure
on any item blocks the publication of the build artefact.

## 12.1 Builds successfully

The `mkdocs build --strict` command SHALL exit 0. The `--strict`
flag turns warnings (broken links, missing pages, etc.) into
errors.

## 12.2 Zero broken links

The link checker (mkdocs-build's built-in link checker or
`lychee`) SHALL find zero broken internal links and zero broken
external links (modulo a documented allowlist of external URLs
that are known to be flaky but content-critical).

## 12.3 Zero orphan pages

Every page SHALL be reachable from the home page via the
navigation tree (§5.5).

## 12.4 Zero duplicate navigation

A page SHALL appear at exactly one path in the navigation tree.
A page listed in two sections is rejected at review.

## 12.5 API pages generated

The `api/` directory SHALL contain one entry per public SDK
module. The build pipeline SHALL verify the entry count matches
the public module count (per `PUBLIC_TOP_LEVEL_MODULES`).

## 12.6 Cookbook links valid

Every recipe referenced from a documentation page SHALL exist in
`recipes/`. The link checker SHALL verify each recipe reference
points to a real file with a parseable `recipe_id:` frontmatter
field.

## 12.7 Search index builds

The MkDocs search plugin SHALL build without errors and SHALL
emit a non-empty `search_index.json` file.

## 12.8 Examples compile

Every fenced Python block on every documentation page SHALL parse
without errors. The build pipeline extracts the blocks, writes
them to a temporary file, and runs `python -m py_compile`.

---

# 13. Documentation Quality Gates

Before any documentation task (D9-NNN) is declared complete, the
following items SHALL be verified. The task is incomplete if
any item is missing.

| # | Item                                                                                  | Verification                                       |
| - | ------------------------------------------------------------------------------------- | -------------------------------------------------- |
| 1 | Navigation updated (new pages added to `mkdocs.yml`'s `nav:` block)                  | `mkdocs build --strict` succeeds                   |
| 2 | Search index updated (no stale entries; new pages indexed)                            | `mkdocs build` succeeds; `search_index.json` non-empty |
| 3 | Links verified (zero broken internal/external links)                                 | link checker output is empty                       |
| 4 | Examples compile (every fenced Python block parses)                                   | `py_compile` succeeds on the extracted blocks      |
| 5 | Examples execute (offline-mode examples run without errors)                          | `pytest tests/test_documentation_examples.py` passes|
| 6 | Public API only (no `_foo` imports in any example)                                   | CB-008 verification layer (no false positives)     |
| 7 | Page added to navigation (visible in sidebar)                                        | manual review of `mkdocs.yml`                      |
| 8 | Cross-links created (related_recipes, related_api, related_guides)                   | page passes the frontmatter lint                   |
| 9 | Page standards (§6) met (title, description, audience, prerequisites, etc.)          | `mkdocs build --strict` succeeds                   |
|10 | Section depth ≤ L3                                                                    | `mkdocs build --strict` succeeds                   |
|11 | Release-notes updated (if SDK version bumped)                                        | manual review                                      |
|12 | Version synchronized (`un_comtrade.__version__` matches site version)                 | `mkdocs build --strict` succeeds                   |

---

# 14. Phase 9 Roadmap

Phase 9 (Documentation Website) is delivered under the `D9-NNN`
task family. Each task reads this protocol before implementation
and conforms to every clause. The official execution order is:

```
D9-001 Documentation Architecture
        ↓
D9-002 MkDocs Foundation
        ↓
D9-003 Landing
        ↓
D9-004 Installation
        ↓
D9-005 Quick Start
        ↓
D9-006 Authentication
        ↓
D9-007 Metadata
        ↓
D9-008 Trade
        ↓
D9-009 Analytics
        ↓
D9-010 ETL
        ↓
D9-011 Storage
        ↓
D9-012 CLI
        ↓
D9-013 Cookbook
        ↓
D9-014 API Reference
        ↓
D9-015 Architecture
        ↓
D9-016 Search
        ↓
D9-017 Verification
        ↓
D9-018 Documentation Review
```

A task may only begin when its predecessor is **complete and
STABLE**. Skipping a task (e.g., starting D9-008 before D9-007 is
done) requires a protocol amendment.

---

# Quality Gates

Before this protocol is itself declared complete and the first
implementation task (D9-001) is unblocked, the following items
SHALL be verified:

| # | Gate                                                                            | Status |
| - | ------------------------------------------------------------------------------- | ------ |
| 1 | Website directory is separated from engineering specs (`website/` vs `docs/`)| ✅     |
| 2 | Navigation hierarchy is deterministic (7 fixed L1 sections; max depth L3)      | ✅     |
| 3 | Cookbook remains the authoritative source of runnable examples                  | ✅     |
| 4 | API reference policy mandates generation (no manual duplication)               | ✅     |
| 5 | No duplicated documentation strategy (Cookbook vs docs vs website all distinct) | ✅     |
| 6 | Public SDK is the only documented API (private symbols are excluded)            | ✅     |
| 7 | Phase 9 task ordering is correct (D9-001..D9-018, sequential dependencies)     | ✅     |

---

# Completion Requirements

The following items are the **return contract** of this task.

## Sections created

1. Documentation Principles (§1)
2. Audience Definition (§2)
3. Documentation Architecture (§3)
4. Website Structure (§4)
5. Navigation Rules (§5)
6. Page Standards (§6)
7. Example Policy (§7)
8. API Reference Policy (§8)
9. Cookbook Integration Policy (§9)
10. Versioning Policy (§10)
11. Search Policy (§11)
12. Verification Policy (§12)
13. Documentation Quality Gates (§13)
14. Phase 9 Roadmap (§14)

## Website structure

`website/` with `mkdocs.yml`, `docs/` mirroring the seven L1
sections (Home, Getting Started, Guides, Cookbook, API,
Architecture, Release Notes), `assets/`, and `overrides/`. The
engineering specs in `docs/` remain separate.

## Navigation strategy

Sidebar renders the full tree (collapsed by default); breadcrumb
trail on every page; previous/next links from the `nav:` block
order; autolinks for API symbols; relative paths for recipes;
absolute URLs for engineering specs; orphan detection fails the
build.

## Documentation principles

User-first; public SDK only; cookbook is the executable source;
API reference is generated; examples compile and execute;
cross-references are bidirectional; stability over novelty.

## Verification strategy

`mkdocs build --strict`; link checker; orphan detection;
duplicate-navigation check; API-page count check; recipe-link
validity; search-index build; example `py_compile`; offline-mode
example execution via the CB-008 verification layer.

## Recommended first implementation task

**D9-001 — Documentation Architecture.** This task instantiates
the `website/` skeleton, defines the `mkdocs.yml` configuration,
pins the navigation tree to the seven L1 sections, sets up the
theme (e.g., Material for MkDocs), wires the search plugin, and
produces a greenfield build with a single home-page entry. D9-001
SHALL NOT introduce any L2 pages; it sets up the container.
D9-002 (MkDocs Foundation) follows with the link checker, the
orphan detector, and the example-compile hook; D9-003 onwards
populate the content.

---

# Sign-off

This protocol is **LIVE** as of 2026-06-30T00:55:00Z. Every
subsequent documentation task SHALL read this document before
implementation. A documentation task that violates any clause
above is rejected at review.

**Authored by**: Mavis (D9-000).
**Supersedes**: None.
**Next document**: D9-001 — Documentation Architecture.