---
title: Contributing
description: How to add a new analytics function, a new storage backend, or a new CLI command; the PR checklist.
audience: contributor
prerequisites:
  - architecture/sdk_overview/
skips:
  - Prerequisites
  - Walkthrough
  - Examples
related_recipes:
  - _TEMPLATE
related_api:
  - un_comtrade.ComtradeClient
related_guides:
  - architecture/testing/
  - architecture/cookbook/
---

# Contributing

The SDK is **contributor-friendly**: adding a new analytics
function, a new storage backend, or a new CLI command is a small,
self-contained change. The PR checklist below applies to every
contribution.

## Purpose

This page covers:

1. The setup (clone, install, test).
2. How to add a new analytics function.
3. How to add a new storage backend.
4. How to add a new CLI command.
5. The PR checklist.

## Setup

```bash
git clone https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk.git
cd un-comtrade-sdk
pip install -e .[all,dev]
pytest tests/ -x
```

The full test suite currently runs **3,117** tests across 38 modules.

## Adding a new analytics function

1. Pick a submodule under `un_comtrade/analytics/`
   (`country.py`, `partner.py`, `commodity.py`, `timeseries.py`,
   `balance.py`, `compare.py`).
2. Add the function. It MUST accept a `CanonicalDataset` (or any
   `Iterable[TradeRecord]`) and return a tuple of frozen dataclasses
   with `Decimal` arithmetic.
3. Add unit tests in `tests/test_analytics_<submodule>.py`.
4. Add a recipe in `recipes/<category>/<file>.py` (use
   `recipes/_TEMPLATE.py`).
5. Add a regression test in
   `tests/test_recipes_verification.py`.
6. Update the documentation page under
   `website/docs/guides/python/analytics.md`.

## Adding a new storage backend

1. Create `un_comtrade/storage/<backend>.py` exposing a class with
   `read(config) -> CanonicalDataset` and `write(config, dataset) ->
   None`.
2. Register the backend in `un_comtrade/storage/__init__.py`'s
   `StorageRegistry`.
3. Add unit tests in `tests/test_storage_<backend>.py`.
4. Add cross-backend round-trip tests in
   `tests/test_storage_round_trip.py`.
5. Add a recipe in `recipes/storage/`.
6. Update `website/docs/guides/python/storage.md` and
   `website/docs/api/storage.md`.

## Adding a new CLI command

1. Add the command module under `un_comtrade/cli/`.
2. Wire it up in `un_comtrade/cli/__init__.py`'s
   `COMMAND_MODULES` registry.
3. Add CLI integration tests in `tests/test_cli_<command>.py`.
4. Add a recipe in `recipes/cli/`.
5. Update `website/docs/guides/cli/<command>.md`.

## PR checklist

Every PR MUST include:

- [ ] Source code change with type hints.
- [ ] Unit tests covering the happy path + at least one failure
      mode.
- [ ] Recipe demonstrating the new feature (if user-facing).
- [ ] Regression test in `tests/test_recipes_verification.py`.
- [ ] Documentation update under `website/docs/`.
- [ ] Changelog entry in `docs/CHANGELOG.md` (CHG-NNNN).
- [ ] Task log entry in `docs/TASK_LOG.md` (TASK-NNN).
- [ ] Context update in `docs/002_CONTEXT.md`.

## Code style

- Maximum line length: **100 characters** (per
  `docs/015_CODING_STANDARD.md`).
- Maximum module size: **500 lines**.
- Type hints mandatory on every public interface.
- `Decimal` arithmetic only — no `float()` for monetary values.
- Imports only public SDK symbols; no `from un_comtrade._foo import
  ...`.

## Testing

Run the full suite:

```bash
pytest tests/ -x
```

Run only the recipes:

```bash
pytest tests/test_recipes_verification.py -v
```

Run with coverage:

```bash
pytest tests/ --cov=un_comtrade --cov-report=term-missing
```

## Related Recipes

- **[RECIPE template][recipe-template]** — the canonical recipe
  scaffold.

## Related API

- [`un_comtrade.ComtradeClient`][api-client] — the entry point your
  code extends.

## Related Guides

- **[SDK overview][sdk-overview]** — read this first.
- **[Testing][testing]** — the testing standard.
- **[Cookbook][cookbook]** — the recipe contract.

## Next steps

- **[Testing][testing]** — the quality bar.
- **[Cookbook][cookbook]** — the executable source.

[api-client]: ../api/client/
[recipe-template]: ../../recipes/_TEMPLATE.py
[sdk-overview]: sdk_overview/
[testing]: testing/
[cookbook]: cookbook/