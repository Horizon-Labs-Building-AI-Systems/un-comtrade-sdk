---
title: SDK overview
description: The 10-layer decomposition, the public SDK philosophy, the dependency direction.
audience: contributor
prerequisites: []
skips:
  - Prerequisites
  - Walkthrough
  - Examples
related_recipes: []
related_api:
  - un_comtrade.ComtradeClient
related_guides:
  - architecture/contributing/
---

# SDK overview

The SDK is organised into **10 layers** with **strict downward
dependency direction**. The architectural detail lives in
`docs/003_ARCHITECTURE.md`; this page is the contributor-facing
summary.

## The 10 layers

1. **Transport** — `httpx`-backed HTTP client with retry + timeout
   middleware.
2. **SDK Client** — `ComtradeClient` facade; owns one
   `HttpTransport` per session.
3. **Metadata** — `MetadataService`; reference catalogues
   (countries, partners, HS codes, units).
4. **Trade** — `TradeService`; annual / monthly / tariffline
   queries, auto-paginated.
5. **Validation** — input validation against the canonical model.
6. **Normalisation** — upstream wire format → canonical model.
7. **Export** — serialisation helpers (Decimal, dates, enums).
8. **Storage** — CSV / JSON / Parquet / DuckDB writers and
   readers.
9. **Analytics** — typed, frozen, Decimal-safe analytics on top of
   `CanonicalDataset`.
10. **Application** — CLI + Cookbook + documentation site.

## Dependency direction

Strict downward: a layer at depth N may only depend on layers at
depth > N. No cycles; no layer skipping. The 10-layer decomposition
is enforced by an AST-based audit tool
(`tools/audit_layer_boundaries.py`).

## Public SDK

The public SDK is the symbols exported via `un_comtrade/__init__.py`
(`__all__`) plus the public submodules. Everything prefixed with `_`
is internal.

The 251 public symbols (per `docs/027_PUBLIC_API_AUDIT.md`) include:

- 1 facade (`ComtradeClient`)
- 5 service attributes (`metadata`, `trade`, `analytics`, `etl`,
  `storage`)
- 35 public analytics functions
- 57 frozen result dataclasses
- 13 exception types
- 7 configuration categories

## Versioning

The SDK follows SemVer 2.0.0 (per
`docs/028_SEMANTIC_VERSION_AUDIT.md`). The current version is
**1.0.1** — a stable release with two performance patches from
1.0.0 (DuckDB bulk-insert speedup ~100×; `country_vs_country`
filter fusion ~5–10×).

## Related Recipes

None — this is an architecture overview, not a recipe index.

## Related API

- [`un_comtrade.ComtradeClient`][api-client] — the single public
  entry point.

## Related Guides

- **[Contributing][contributing]** — how to add code.
- **[Testing][testing]** — the testing standard.

## Next steps

- **[Contributing][contributing]** — the PR checklist.
- **[Cookbook][cookbook]** — if you're writing recipes.

[api-client]: ../api/client/
[contributing]: contributing/
[testing]: testing/
[cookbook]: cookbook/