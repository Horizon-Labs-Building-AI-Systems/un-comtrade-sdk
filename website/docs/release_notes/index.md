---
title: Release Notes
description: Versioned changelog for the un-comtrade-sdk; per-version Added / Changed / Deprecated / Removed / Fixed / Security sections.
audience: maintainer
prerequisites: []
skips:
  - Prerequisites
  - Walkthrough
  - Examples
related_recipes: []
related_api: []
related_guides:
  - release_notes/v1/
  - release_notes/migration/
---

# Release Notes

The release notes index lists every published version of the SDK.
Per `docs/032_v1_RELEASE_NOTES.md` and `docs/CHANGELOG.md`, every
release includes **Added / Changed / Deprecated / Removed / Fixed
/ Security** sections.

## Versions

| Version | Date | Highlights |
| ------- | ---- | ---------- |
| **[v1.0.1][v1]** | 2026-06-29 | Performance patch: DuckDB bulk-insert ~100×; `country_vs_country` filter fusion ~5–10×. |
| **[v1.0.0][v1]** | 2026-06-28 | First stable release. 251 public symbols; 3,117 tests passing. |

## Migration guides

- **[Migration guide][migration]** — for upgrading from pre-1.0
  development releases.

## Versioning

The SDK follows SemVer 2.0.0 (per
`docs/028_SEMANTIC_VERSION_AUDIT.md`). Compatibility score is
**96.7%** (348/360 Q-points across 13 layers).

## Version sync

The release-notes version matches `un_comtrade.__version__` per
protocol §10.2 (SDK version synchronization). The build pipeline
verifies the match.

## Related API

- [`un_comtrade.__version__`][api-version] — the package version
  constant.

## Related Guides

- **[v1 release notes][v1]** — what's in v1.
- **[Migration guide][migration]** — for pre-1.0 users.

## Next steps

- **[v1 release notes][v1]** — read this first.

[v1]: v1/
[migration]: migration/
[api-version]: ../api/models/