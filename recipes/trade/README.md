# Cookbook — `trade/` Category

Recipes that exercise the **`client.trade` service** —
the trade-data fetchers (T01–T13 in
`007_SDK_SPECIFICATION.md` §3.4). The trade service is
the **primary** consumer of the upstream UN Comtrade
API; recipes in this category always call the network
and almost always write their result to a storage
backend.

## Purpose

A consumer should be able to read this category and
understand:

- How to fetch exports / imports / re-exports for a
  given reporter, partner, period, and flow.
- How to paginate through a large result set.
- How to filter by HS code at the chapter / heading /
  subheading level.
- How to combine multiple periods (annual, monthly).
- How to write trade data to Parquet, CSV, JSON, and
  DuckDB.

## SDK services exercised

| Service / symbol                        | Used in planned recipes |
| --------------------------------------- | ------------------------ |
| `client.trade.get_exports()`            | ✓                        |
| `client.trade.get_imports()`            | ✓                        |
| `client.trade.get_re_exports()`         | ✓                        |
| `client.trade.get_re_imports()`         | ✓                        |
| `client.trade.get_trade_data()`         | ✓                        |
| `client.trade.get_last_updates()`       | ✓                        |
| `client.trade.get_tariffline()`         | ✓                        |
| `client.trade.validate_query()`         | ✓                        |
| `client.trade.preview_query()`          | ✓                        |

## API key policy

| `requires_api_key` | Default for this category |
| ------------------ | ------------------------- |
| `yes`              | ✓ (per `recipes/README.md` §8.2) |

Every recipe in this category reads the API key from
`UN_COMTRADE_KEY` and exits with code `4` when the
key is missing or rejected.

## Estimated runtime band

| `estimated_runtime` | Typical recipes in this category             |
| ------------------- | --------------------------------------------- |
| `<10s`              | one trade query returning < 1k records        |
| `<1min`             | one trade query for a single reporter / year  |
| `1-10min`           | multi-year or multi-reporter queries          |
| `10-60min`          | full-year multi-reporter pipelines            |

A cold cache adds ~1s to the first request. Recipes
that paginate through > 100k records are typically in
the `1-10min` band.

## Planned recipe roster

| Recipe ID     | Title                                                                  | Difficulty      | Runtime   | API key | Status   | Source file                  |
| ------------- | ---------------------------------------------------------------------- | --------------- | --------- | ------- | -------- | ---------------------------- |
| `RECIPE-011`  | Fetch annual exports (T01) to Parquet                                  | beginner        | `<1min`   | yes     | DRAFT    | `01_exports.py`              |
| `RECIPE-012`  | Fetch annual imports for one partner (T02) to CSV                      | beginner        | `<1min`   | yes     | DRAFT    | `02_imports.py`               |
| `RECIPE-013`  | Fetch world aggregate trade (T05) to JSON                             | beginner        | `<10s`    | yes     | DRAFT    | `03_world_trade.py`           |
| `RECIPE-014`  | Compute trade balance (composed T01+T02) into DuckDB                    | intermediate    | `<1min`   | yes     | DRAFT    | `04_trade_balance.py`        |
| `RECIPE-015`  | Fetch line-level tariffline (F02) to JSON, with full error handling     | advanced        | `1-10min` | yes     | DRAFT    | `05_tariffline.py`            |
| `RECIPE-016`  | Fetch monthly exports (T09) to Parquet                                 | beginner        | `<1min`   | yes     | PROPOSED | —                            |
| `RECIPE-017`  | Fetch the last-updates timeline for a dataset                          | beginner        | `<10s`    | yes     | PROPOSED | —                            |
| `RECIPE-018`  | Multi-year / multi-reporter batch pipeline                              | advanced        | `10-60min`| yes     | PROPOSED | —                            |
| `RECIPE-019`  | Walk a single reporter's bilateral matrix (T07)                         | intermediate    | `<1min`   | yes     | PROPOSED | —                            |
| `RECIPE-020`  | Trade matrix (T08) for a fixed period                                   | intermediate    | `<1min`   | yes     | PROPOSED | —                            |

**CB-003 (DRAFT).** Recipes `RECIPE-011` through
`RECIPE-015` are the first batch of trade recipes.
They cover all four pillars from the brief:

- **Authentication** — every recipe reads the key
  from ``UN_COMTRADE_KEY`` and exits with code 4
  when missing; recipe 05 makes the gating pattern
  explicit and reusable.
- **Filtering** — recipes 01, 02, 04, 05 each
  show a different filter (period only, period +
  partner, period + HS chapter, line-level HS).
- **Output formats** — recipes 01 / 02 / 03 / 04
  / 05 cover **five distinct output paths**
  between them: Parquet (recipe 01), CSV
  (recipe 02), JSON (recipes 03 and 05), DuckDB
  (recipe 04), and the structured `TradeRecord`
  projection used in each writer.
- **Error handling** — every recipe wires the
  full CB-001 §7 error-handling contract via
  `_exit_code_for(exc)`. Recipe 05 is the
  error-handling showcase: it adds
  `--validate-only` and `--dry-run` flags, exits
  with code 2 for invalid arguments, exits with
  code 8 for an empty result, and renders the
  exit-code table in its `--help` output.

The 23-test regression suite
(`tests/test_recipes_trade.py`) is green. The
on-screen output has been smoke-checked against
the recorded fixtures; the recipes have NOT been
exercised against the live upstream API in CI.

**Recipe 04 design note.** The dedicated T06
balance endpoint's records do not carry a single
``flowCode`` (the balance spans every flow), but
the SDK's ``TradeRecord`` model requires one. The
parser therefore drops every balance record. The
recipe works around that gap by **composing**
T01 (``get_exports``) and T02 (``get_imports``)
client-side and joining on partner code. The
composition is documented in the recipe's
docstring; the alternative — bypassing the SDK to
hit the transport directly — is left as a
follow-up.

**Note on file naming.** As with CB-002, the
file names use the shorter ``NN_<slug>.py`` form
rather than ``RECIPE_NNN_<slug>.py``. See CB-002's
delivery report for the convention amendment.

## Per-recipe cross-references

A `trade/` recipe that needs to explain a behaviour
links to:

- `docs/007_SDK_SPECIFICATION.md` §3.4 (T01–T13)
- `docs/009_TRADE_LAYER_SPEC.md`
- `docs/010_INFRASTRUCTURE_SPEC.md` §3 (rate limits)
- `docs/011_ETL_SPECIFICATION.md` (when the recipe
  uses the ETL pipeline rather than `client.trade`
  directly — see `etl/`)
- `docs/012_STORAGE_SPECIFICATION.md` (when the recipe
  writes to a storage backend)
- `docs/030_PERFORMANCE_BASELINE.md` (for recipes
  whose declared band is `1-10min` or higher)

## Category-specific notes

- **Storage is part of the recipe.** A `trade/` recipe
  that does not persist its result is incomplete. The
  output is always written through a documented SDK
  storage backend (`storage.parquet`, `storage.csv`,
  `storage.json`, `storage.duckdb`).
- **Pagination is automatic.** The SDK hides
  pagination behind the `client.trade.*` methods; a
  recipe MUST NOT call the upstream API directly.
  Recipes that demonstrate pagination (e.g.
  `RECIPE-014`) print the page count and the records
  per page.
- **Rate limits are honoured.** The SDK honours the
  upstream's `Retry-After: 1` header on HTTP 429
  (ADR-0035). A recipe that exhausts the retry budget
  exits with code `5` per `recipes/README.md` §6.4.
- **Result size matters.** Recipes that fetch
  > 100k records SHOULD prefer Parquet or DuckDB
  output. A recipe that writes CSV for a 100k-row
  result is rejected at review.

## How to add a recipe to this category

1. Choose the next free `RECIPE-NNN` ID from the
   roster above. If the recipe is not on the roster,
   add it to the roster first.
2. Copy `recipes/_TEMPLATE.py` to
   `recipes/trade/RECIPE_NNN_<slug>.py`.
3. Implement the body per `recipes/_TEMPLATE.md`.
   The body MUST:
   - Set `requires_api_key: yes` in the frontmatter.
   - Read the key from `os.environ["UN_COMTRADE_KEY"]`.
   - Persist the result through a documented SDK
     storage backend.
4. Update this README's roster table with the new
   recipe's status.
5. Submit a pull request.

A recipe that does not call `client.trade.*` is not
a `trade/` recipe and belongs in another category.
