```
Document ID
037

Title
Release Freeze — v1.0.1 TestPyPI Validation

Version
1.0.1

Status
LIVE

Created
2026-06-30T20:24:55+05:30

Last Updated
2026-06-30T20:24:55+05:30

Author
Codex (acting on behalf of Horizon-Labs)

Project
UN Comtrade Python SDK

Dependencies
014_PACKAGING_SPECIFICATION.md,
028_SEMANTIC_VERSION_AUDIT.md,
031_PRODUCTION_READINESS.md,
032_v1_RELEASE_NOTES.md,
docs/CHANGELOG.md

Supersedes
None
```

# Release Freeze — v1.0.1 for TestPyPI Validation

This document freezes the SDK at a single, auditable commit so the
release pipeline can be validated against TestPyPI without surprises
creeping in mid-stream. The freeze is internal — no GitHub Release,
no PyPI tag is created by this document.

## 1. Frozen State

| Field | Value |
|---|---|
| SDK version | `1.0.1` |
| Source of truth | `un_comtrade.__version__` + `pyproject.toml [project].version` |
| Git commit (freeze SHA) | `1e1dbe89e12a8f64c6c9c6dc8251b13c9ddb6ba4` |
| Branch | `main` |
| Working tree at freeze | tracked files: clean · untracked files: pre-existing (see §7) |
| Freeze applied | `docs/037_RELEASE_FREEZE.md` is the freeze record |
| Repository | `Horizon-Labs-Building-AI-Systems/un-comtrade-sdk` |

The freeze SHA is the head of `main` at the time this document was
authored. Every release-ready artifact (wheel, sdist, documentation
site, CLI executable) MUST rebuild bit-identically from this commit.

## 2. Release Readiness Checklist

| # | Gate | Status | Evidence |
|---|---|---|---|
| 1 | `un_comtrade.__version__ == "1.0.1"` | PASS | `un_comtrade/__version__.py` L30 |
| 2 | `pyproject.toml [project].version == "1.0.1"` | PASS | `pyproject.toml` L7 |
| 3 | `un_comtrade/__init__.py` re-exports `ComtradeClient`, `__version__` | PASS | `un_comtrade/__init__.py` L18-21 |
| 4 | Wheel builds | PASS | `python -m build` → `un_comtrade_sdk-1.0.1-py3-none-any.whl` |
| 5 | sdist builds | PASS | `python -m build` → `un_comtrade_sdk-1.0.1.tar.gz` |
| 6 | Wheel contains `__init__.py` for every subpackage | PASS | CI-FIX-003 commit `d79463e` |
| 7 | Wheel contains `__version__.py` | PASS | CI-FIX-003 commit `d79463e` |
| 8 | `twine check` PASS on wheel + sdist | PASS | `returncode: 0` |
| 9 | CLI entry-point registered | PASS | `[console_scripts] un-comtrade = un_comtrade.cli.main:main` |
| 10 | Documentation site builds (`mkdocs build --strict`) | PASS | "Documentation built in 8.08 seconds" |
| 11 | Cookbook section present | PASS | `website/docs/cookbook/{analytics,cli,end_to_end,index,metadata,storage,trade}.md` |
| 12 | API reference present | PASS | `website/docs/api/{analytics,cli,client,etl,exceptions,index,metadata,models,storage,trade}.md` |
| 13 | README present | PASS | `README.md`, 2598 bytes, badges resolve to `main` workflows |
| 14 | LICENSE present | PASS | `LICENSE`, 1083 bytes, MIT |
| 15 | CHANGELOG references v1.0.1 | PASS | `docs/CHANGELOG.md`, CHG-0080 + CHG-0081 entries |
| 16 | Release notes present | PASS | `docs/032_v1_RELEASE_NOTES.md`, 12,462 bytes |
| 17 | Repository URLs declared | PASS | `pyproject.toml [project.urls]` (Homepage, Documentation, Repository, Issues, Changelog, Release_Notes) |
| 18 | `scripts/build_docs.py` is executable | PASS | CI-FIX-003 commit `d79463e` set mode `100755` |
| 19 | Working tree clean at freeze SHA | PASS | `git status --short` returns only pre-existing untracked files (§7) |
| 20 | All five GitHub Actions workflows green at freeze SHA | PASS | See §3 |

## 3. CI Snapshot at Freeze SHA

Last workflow runs against commit `1e1dbe89e12a8f64c6c9c6dc8251b13c9ddb6ba4`:

| Workflow | Status | Trigger | Notes |
|---|---|---|---|
| CI (placeholder `echo`) | PASS | `push` to `main` | Mechanical check, always green |
| Quality / ruff 3.11 / 3.12 / 3.13 | PASS | `push` to `main` | EXE001 closed by CI-FIX-003 |
| Quality / mypy 3.11 / 3.12 / 3.13 | PASS | `push` to `main` | "Success: no issues found in 185 source files" |
| Quality / pytest 3.11 / 3.12 / 3.13 | PASS | `push` to `main` | After CI-FIX-004 (`test_windows_default`) + CI-FIX-005 (2 JSONWriter tests) |
| Documentation / mkdocs build 3.11 / 3.12 / 3.13 | PASS | `push` to `main` | All three Python versions |
| Package / build 3.11 / 3.12 / 3.13 | PASS | `push` to `main` | Wheels produced |
| Package / install 3.11 / 3.12 / 3.13 | PASS | `push` to `main` | wheel contains `__version__.py` since CI-FIX-003 |
| Security / pip-audit 3.11 / 3.12 / 3.13 | PASS | `push` to `main` | No known vulns |
| Security / TruffleHog | PASS | `push` to `main` | After CI-SEC-001 + CI-SEC-002 (gitleaks → trufflehog, automatic commit detection, single `--fail`) |
| Release | NOT TRIGGERED | tag `v*.*.*` | No tag was created for `1.0.1` |

## 4. Allowed Post-Freeze Changes

Post-freeze commits on `main` are restricted to:

1. **Release blockers.** Anything that prevents `pip install un-comtrade-sdk==1.0.1`
   from succeeding on TestPyPI (broken `METADATA`, malformed `RECORD`,
   `twine check` failure on the produced artifact).
2. **Packaging issues.** `pyproject.toml` corrections to classifiers,
   `requires-python`, `license` SPDX expression, build-backend
   declaration. No new transitive dependencies.
3. **Metadata corrections only.** Author name, project URL list,
   long description / `README.md` badge links. No rewritten prose
   for the SDK API.
4. **TestPyPI validation fixes.** Trivial fixes strictly to make a
   TestPyPI "publish" succeed (for example: a `twine` upload flag,
   a URL in the project's `[project.urls]` section, a misspelled
   classifier string). These fixes MUST land before the publish
   `git tag v1.0.1`.

## 5. Prohibited Changes

Until the freeze is lifted, the following are **not** permitted on
`main`:

1. New SDK features.
2. Public-API changes (additions, removals, signature changes,
   semantic-version-impacting edits to `un_comtrade/`).
3. CLI changes (new subcommands, changed flags, removed flags).
4. Documentation expansion (`docs/*.md`, `website/docs/**`) other
   than the metadata corrections listed in §4.
5. Cookbook / recipe additions
   (`website/docs/cookbook/`, `recipes/`).
6. Architectural changes (storage backend shape, query-engine
   rewrite, public re-export graph).
7. Dependency upgrades unless the upgrade is itself a release
   blocker. Transitive bumps ride a separate version.

## 6. Rollback Strategy

If a post-freeze commit breaks the release:

1. **Identify the bad commit.** `git log --oneline 1e1dbe8..HEAD`
   lists every commit since the freeze SHA.
2. **Revert.** `git revert <bad-sha> --no-edit` produces a single
   commit that undoes the offending change. The freeze SHA
   `1e1dbe89e12a8f64c6c9c6dc8251b13c9ddb6ba4` is the immutable
   baseline.
3. **Re-verify.** `python -m pytest`, `python -m build`,
   `python -m twine check dist/*`, `mkdocs build --strict`,
   `git push` and re-watch GitHub Actions.
4. **Re-tag (later).** The tag `v1.0.1` is created only after the
   pipeline is green end-to-end against TestPyPI. Until then, no
   tag, no GitHub Release, no PyPI publish.
5. **Lift the freeze.** Only after a tagged and validated
   `v1.0.1` exists on PyPI does this document move to status
   `SUPERSEDED` and the freeze is over.

## 7. Working-Tree Disclosure

At the time this freeze was authored, the following paths were
**untracked** in the working tree. They pre-date the freeze, are
not part of the 1.0.1 deliverable, and are out of scope for this
release. They are recorded here for transparency.

```
?? _tmp_log.py
?? comtrade/__init__.py
?? comtrade/__main__.py
?? recipes/_TEMPLATE.py
?? tools/_f002_scan.py
?? tools/_mem_probe.py
?? tools/_tab.py
?? website/.mkdocs-serve.log
```

Notes:

- `comtrade/` is the legacy standalone client, explicitly excluded
  from the SDK build via `[tool.setuptools.packages.find]` in
  `pyproject.toml` and from the mypy type-gate. It is not in the
  wheel, not in the sdist, and not in the documentation site.
- `recipes/_TEMPLATE.py` and `tools/_*.py` are template / one-off
  helper scripts, not part of the SDK import surface.
- `website/.mkdocs-serve.log` is a transient `mkdocs serve` log
  written into the working tree.
- `_tmp_log.py` is a transient debugging artifact.

None of these paths is referenced by `un_comtrade`, the CLI entry
point, the documentation configuration, or the packaging config.
The wheel and sdist built from the freeze SHA do not change
content if these files exist, are deleted, or are renamed.

## 8. What Happens Next

1. **TestPyPI validation.** Build from `1e1dbe8`, upload via
   `twine upload --repository testpypi dist/*`, install in a
   clean venv with `pip install -i https://test.pypi.org/simple/
   un-comtrade-sdk==1.0.1`, smoke-test the CLI, run the test
   suite against the TestPyPI install.
2. **Tag.** `git tag -a v1.0.1 -m "<message>"` only after the
   TestPyPI install is verified.
3. **Publish to PyPI.** `twine upload dist/*`.
4. **GitHub Release.** `gh release create v1.0.1` with
   `032_v1_RELEASE_NOTES.md` as the body.

## 9. Provenance

This document was authored as part of release engineering for
v1.0.1. The fixes that landed immediately before the freeze:

| Commit | Title | Effect on release readiness |
|---|---|---|
| `f1b866a` | CI-FIX-001 docs.yml / package.yml / requirements-docs.txt | Workflow YAML validity |
| `d79463e` | CI-FIX-003 restore tracked package modules | Wheel imports resolve on a clean runner |
| `8b87a52` | CI-FIX-004 host-deterministic cache directory | Cross-platform config tests pass |
| `5d18e32` | CI-FIX-005 platform-deterministic JSONWriter tests | Two tests no longer rely on filesystem ordering |
| `026a6ef` | CI-SEC-001 Gitleaks → TruffleHog | Security gate no longer requires `GITLEAKS_LICENSE` |
| `03d86ad` | CI-SEC-002 automatic commit detection for TruffleHog | Push-to-default-branch no longer collapses BASE/HEAD |
| `1e1dbe8` | CI-SEC-002 follow-up: drop duplicate `--fail` | TruffleHog CLI no longer rejects `flag 'fail' cannot be repeated` |

End of freeze record.
