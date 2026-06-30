---
title: Testing standard
description: The 9 test categories, the 3 quality gates, the 5-defect-category taxonomy, the 7 continuous verification mechanisms.
audience: contributor
prerequisites:
  - architecture/sdk_overview/
skips:
  - Prerequisites
  - Walkthrough
  - Examples
related_recipes: []
related_api: []
related_guides:
  - architecture/cookbook/
  - architecture/contributing/
---

# Testing standard

The SDK follows a **category-coverage** testing standard (per
`docs/013_TESTING_STANDARD.md`). Every category MUST have 100%
coverage; there is no percentage threshold.

## The 9 test categories

1. **Public API unit tests** — every public method, every public
   dataclass. (~ 2,500 tests)
2. **Internal layer unit tests** — every internal module. (~ 200
   tests)
3. **Cookbook verification** — every recipe runs in mock mode. (~ 100
   tests)
4. **CLI integration tests** — every CLI command, every output
   format. (~ 250 tests)
5. **Storage round-trip tests** — every backend, every shape. (~
   100 tests)
6. **Analytics equivalence tests** — every public analytics
   function. (~ 400 tests)
7. **Regression guards** — every known fix has a guard. (~ 60
   tests)
8. **Audit tool tests** — every audit script has a self-test. (~
   30 tests)
9. **Live API integration tests** — opt-in, runs against the real
   UN Comtrade API. (separate suite; not part of CI)

## The 3 quality gates

1. **Build gate** — `pip install -e .` succeeds.
2. **Test gate** — `pytest tests/ -x` passes with all tests green
   (3,117+ as of v1.0.1).
3. **Lint gate** — `ruff check un_comtrade/` and
   `mypy un_comtrade/` pass with no errors.

## The 5-defect-category taxonomy

| Severity | Definition | Action |
| -------- | ---------- | ------ |
| Critical | Crashes on a documented use path. | Block release. |
| High | Wrong output on a documented use path. | Block release. |
| Medium | Wrong output on an undocumented edge case. | Fix in patch release. |
| Low | Cosmetic or minor documentation drift. | Fix in next minor. |
| Informational | Code smell or improvement opportunity. | Track in DECISIONS. |

## The 7 continuous verification mechanisms

1. **`pytest tests/ -x`** — full unit suite on every commit.
2. **`pytest tests/test_recipes_verification.py`** — recipe contract.
3. **`python scripts/build_docs.py`** — documentation build + 8-step
   verification harness.
4. **`tools/audit_layer_boundaries.py`** — AST-based layer-boundary
   check.
5. **`tools/audit_public_api.py`** — public API surface vs.
   `__all__` reconciliation.
6. **`tools/audit_circular_deps.py`** — Tarjan SCC analysis (0
   cycles required).
7. **`tools/audit_package_hygiene.py`** — module size, docstring
   presence, import hygiene.

## Running the suite

```bash
# Full suite
pytest tests/ -x

# Only the cookbook verification
pytest tests/test_recipes_verification.py -v

# With coverage
pytest tests/ --cov=un_comtrade --cov-report=term-missing

# Only regression guards
pytest tests/ -k "regression or guard or sync" -v

# Audit tools
python tools/audit_layer_boundaries.py
python tools/audit_public_api.py
python tools/audit_circular_deps.py
python tools/audit_package_hygiene.py
```

## Defect reporting

Open an issue at
<https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/issues>. Tag the
issue with the appropriate severity and category labels.

## Related Recipes

None — this is a testing standard, not a recipe.

## Related Guides

- **[Cookbook contract][cookbook]** — recipe verification.
- **[Contributing][contributing]** — PR checklist.

## Next steps

- **[Cookbook contract][cookbook]** — if you're writing recipes.
- **[Contributing][contributing]** — the PR checklist.

[cookbook]: cookbook/
[contributing]: contributing/