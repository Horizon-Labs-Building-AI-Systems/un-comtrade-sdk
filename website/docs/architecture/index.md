---
title: Architecture
description: SDK design overview; contributing guide; release process; testing standard; cookbook contract.
audience: contributor
prerequisites: []
skips:
  - Prerequisites
  - Walkthrough
  - Examples
related_recipes: []
related_api: []
related_guides:
  - architecture/sdk_overview/
  - architecture/contributing/
  - architecture/cookbook/
  - architecture/testing/
---

# Architecture

The Architecture section is the **engineering view** of the SDK. It
exists for **contributors** and **maintainers** — not for consumers.
The four pages cover the design overview, the contributing guide,
the cookbook contract, and the testing standard.

## Path

| Page | Audience | What it covers |
| ---- | -------- | -------------- |
| **[SDK overview][sdk-overview]** | Contributors, maintainers | The 10-layer decomposition, the public SDK philosophy, the dependency direction. |
| **[Contributing][contributing]** | Contributors | How to add a new analytics function, a new storage backend, or a new CLI command; the PR checklist. |
| **[Cookbook][cookbook]** | Contributors, maintainers | The cookbook contract (CB-001..CB-008), the recipe verification suite, the regression guards. |
| **[Testing][testing]** | Contributors | The testing standard, the 5-defect-category taxonomy, the continuous verification mechanisms. |

## Public SDK philosophy

Per `docs/000_PROJECT_CHARTER.md` and `docs/007_SDK_SPECIFICATION.md`,
the SDK exposes a stable, typed, public surface — the symbols
exported via `un_comtrade/__init__.py`'s `__all__` and the public
submodules. Internal modules (anything prefixed with `_`) are
**not part of the contract**; they can change without notice.

This documentation site documents **only the public SDK**. Internal
modules (`un_comtrade._foo`, `un_comtrade.storage._base`,
`un_comtrade.analytics._query_engine`) are excluded by the
mkdocstrings configuration (`filters: ["!^_"]`).

## Related API

- [`un_comtrade.ComtradeClient`][api-client] — the single public
  entry point.

## Related Guides

- **[SDK overview][sdk-overview]**
- **[Contributing][contributing]**
- **[Cookbook][cookbook]**
- **[Testing][testing]**

## Next steps

- **[SDK overview][sdk-overview]** — read this first.
- **[Contributing][contributing]** — if you're contributing code.

[sdk-overview]: sdk_overview/
[contributing]: contributing/
[cookbook]: cookbook/
[testing]: testing/
[api-client]: ../api/client/