# `.github/` — GitHub-side Configuration

This directory holds the GitHub-side configuration for the
`un-comtrade-sdk` repository. The contents are owned by Phase 10
(CI/CD) and are governed by `docs/037_CI_BASELINE_AUDIT.md` and
the Phase 10 execution protocol.

## Layout

```
.github/
├── README.md           # this file
└── workflows/          # GitHub Actions workflow definitions
    ├── ci.yml          # Continuous Integration pipeline
    ├── quality.yml     # Lint, typing, unit tests, cookbook verification
    ├── docs.yml        # MkDocs build, link checker, search index
    ├── package.yml     # sdist / wheel build, install, import, CLI smoke
    ├── release.yml     # TestPyPI → PyPI publication + GitHub Release
    └── security.yml    # Dependency audit, secret scan, license check
```

## Workflow responsibilities

| Workflow     | Owner Task  | Purpose (planned)                                            |
| ------------ | ----------- | ------------------------------------------------------------ |
| `ci.yml`     | CI-003..004 | Aggregator / status check across the full CI matrix.         |
| `quality.yml`| CI-003      | Ruff, MyPy, PyTest, CLI tests, cookbook verification.        |
| `docs.yml`   | CI-006      | `mkdocs build --strict`, internal-link check, search index.  |
| `package.yml`| CI-005      | Build sdist + wheel, install, import, smoke the CLI.         |
| `release.yml`| CI-007      | Tag-driven publish to TestPyPI then PyPI; cut GitHub Release. |
| `security.yml`| CI-008     | Weekly dependency audit, secret scan, license whitelist.     |

## Triggers

The current skeletons declare the following triggers (these are
placeholders and SHALL be tightened by their owning tasks):

- `ci.yml`, `quality.yml`, `docs.yml` — `push` to `main`,
  `pull_request` to `main`, `workflow_dispatch`.
- `package.yml` — same as above plus `push` on `v*.*.*` tags.
- `release.yml` — `push` on `v*.*.*` tags, `release: published`,
  `workflow_dispatch`.
- `security.yml` — same as `ci.yml` plus a weekly `schedule` cron.

## Permissions

Every workflow declares the **minimum** permissions required for
its placeholder body — currently `contents: read`. Owning tasks
SHALL request the **least privilege** they need via `permissions:`
at the workflow or job level and SHALL NOT inherit the repo-wide
`GITHUB_TOKEN` default.

## Concurrency

- `ci.yml`, `quality.yml`, `docs.yml`, `security.yml` set
  `cancel-in-progress: true` so a new push supersedes an in-flight
  run on the same ref.
- `package.yml`, `release.yml` set `cancel-in-progress: false`
  because package builds and releases are sensitive and MUST NOT
  be aborted mid-flight.

## Status

CI-001 — **GitHub Actions Skeleton** — landed. Six placeholder
workflows are present and YAML-valid; they contain a single
echo-only `placeholder` job each. Real steps (checkouts, Python
setup, ruff/mypy/pytest invocations, mkdocs builds, twine
uploads) ship in CI-002 .. CI-008.

See `docs/037_CI_BASELINE_AUDIT.md` for the baseline that drove
this skeleton.