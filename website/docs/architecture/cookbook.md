---
title: Cookbook contract
description: The recipe contract (CB-001..CB-008), the recipe verification suite, the regression guards.
audience: contributor
prerequisites:
  - architecture/sdk_overview/
skips:
  - Prerequisites
  - Walkthrough
  - Examples
related_recipes:
  - _TEMPLATE
related_api: []
related_guides:
  - architecture/testing/
  - architecture/contributing/
---

# Cookbook contract

The Cookbook (`recipes/`) is the **executable source of runnable
examples** for the SDK. The recipe contract is enforced by the
verification suite (`tests/test_recipes_verification.py` and
per-recipe tests). Every recipe MUST comply with **CB-001** through
**CB-008**.

## The contract

### CB-001 — public-SDK only

Every recipe MUST import only public SDK symbols. A recipe that
imports a private module (`un_comtrade._foo`,
`un_comtrade.storage._base`, `un_comtrade.analytics._query_engine`)
is rejected at review.

```python
# ALLOWED — public SDK only
from un_comtrade import ComtradeClient
from un_comtrade.config import Configuration
from un_comtrade.models import Country

# NOT ALLOWED — these would fail CB-001:
#   from un_comtrade._internal import _foo
#   from un_comtrade.storage import _base
```

### CB-002 — frontmatter

Every recipe MUST declare a `recipe_id`, `title`, `category`,
`difficulty`, `sdk_version`, `requires_api_key`, and
`estimated_runtime` in the frontmatter.

```yaml
---
recipe_id: RECIPE-NNN
title: Human-readable title
category: metadata | trade | analytics | storage | cli | end_to_end
difficulty: beginner | intermediate | advanced
sdk_version: ">=1.0.0"
requires_api_key: yes | no
estimated_runtime: <1s | 1-2s | 2-4s | 4-8s | 8-15s
---
```

### CB-003 — deterministic output

Every recipe MUST produce deterministic output under mock mode. The
regression tests inject a mock transport; the recipe MUST work
without any network call.

### CB-004 — `demo(client)` + `main()` pattern

The recipe body MUST follow the demo + main pattern:

```python
def demo(client: ComtradeClient) -> SomeResult:
    """The actual demonstration."""
    ...

def main() -> int:
    """Build a real client and run the demo."""
    config = Configuration(api_key=os.environ.get("UN_COMTRADE_KEY") or None)
    with ComtradeClient(config) as client:
        demo(client)
    return 0

if __name__ == "__main__":
    print("== Recipe NNN: Title ==")
    raise SystemExit(main())
```

The `demo(client)` function is what the regression test calls; the
`main()` function is what `python recipes/<file>.py` runs.

### CB-005 — expected output documented

The recipe docstring MUST include a documented "Expected output"
section showing the mock-mode output.

### CB-006 — `recipe_id` matches the filename

The `recipe_id` in the frontmatter MUST match the canonical RECIPE
identifier (RECIPE-NNN). The numbering is dense per category:

- 001–099: metadata + trade + analytics + storage + CLI
- 100+: end-to-end recipes

### CB-007 — referenced by documentation pages

Every recipe referenced from a documentation page (`website/docs/`)
MUST exist in `recipes/`. The link checker
(`scripts/build_docs.py` Step 6) enforces this.

### CB-008 — example compilation

Every fenced Python block in every documentation page MUST parse
without errors. The example-compile step
(`scripts/build_docs.py` Step 7) extracts the blocks, writes them
to a temporary file, and runs `python -m py_compile`.

## The verification suite

The verification suite is `tests/test_recipes_verification.py`
plus per-category modules. It enforces:

- CB-001 via AST scan of every recipe's imports.
- CB-002 via frontmatter parsing.
- CB-003 via mock-mode execution.
- CB-004 via `inspect.signature(demo)` matching the expected
  signature.
- CB-005 via doctest-style comparison.
- CB-006 via regex match against the recipe filename.

Run the suite:

```bash
pytest tests/test_recipes_verification.py -v
```

## Adding a new recipe

1. Copy `recipes/_TEMPLATE.py` to `recipes/<category>/<NN>_<slug>.py`.
2. Fill in the frontmatter (CB-002).
3. Implement `demo(client)` and `main()` (CB-004).
4. Document the expected output (CB-005).
5. Run `pytest tests/test_recipes_verification.py -v` to verify.
6. Add a regression test in the per-category module if the recipe
   has any non-trivial behaviour.

## Related Recipes

- **[RECIPE template][recipe-template]** — the canonical recipe
  scaffold.

## Related Guides

- **[Testing][testing]** — the testing standard.
- **[Contributing][contributing]** — the PR checklist.

## Next steps

- **[Testing][testing]** — the quality bar.

[recipe-template]: ../../recipes/_TEMPLATE.py
[testing]: testing/
[contributing]: contributing/