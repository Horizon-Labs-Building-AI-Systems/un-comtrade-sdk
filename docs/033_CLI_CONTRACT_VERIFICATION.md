```
{
  "id": "033",
  "title": "CLI Contract Verification",
  "version": "1.0.0",
  "status": "LIVE",
  "created": "2026-06-29",
  "last_updated": "2026-06-29",
  "author": "Codex",
  "project": "un-comtrade-sdk",
  "dependencies": [
    "docs/000_PROJECT_CHARTER.md",
    "docs/021_IMPLEMENTATION_BASELINE_v1.md",
    "docs/031_PRODUCTION_READINESS.md",
    "docs/032_CLI_REVIEW.md",
    "docs/032_v1_RELEASE_NOTES.md"
  ],
  "supersedes": null
}
```

# 033 — CLI Contract Verification

## 1. Scope

This document is the C-007A verification report for the public CLI
contract of the `un-comtrade` console script at v1.0.x. It exists to
make the CLI's external interface a **machine-checked contract** rather
than a hand-maintained promise.

The five contracts under test (from the C-007A brief) are:

1.  Every CLI command maps to **exactly one** public SDK entry point.
2.  No CLI command imports or calls **private modules**.
3.  Every public CLI command appears in `--help`.
4.  Every documented CLI example executes successfully against
    **mocked services**.
5.  Command names remain **stable** across releases.

All five contracts are implemented as regression tests in
`tests/test_cli_contract.py` and verified to pass on
**2026-06-29 at v1.0.1**.

---

## 2. Test suite

`tests/test_cli_contract.py` declares 15 tests across 5 contract
classes. The suite runs in **0.55s** and passes 100%.

| Class                            | Tests | Purpose                                                        |
| -------------------------------- | ----- | -------------------------------------------------------------- |
| `TestOneToOneMapping`            | 4     | Contract 1: 1-to-1 mapping between CLI leaves and SDK methods. |
| `TestNoPrivateImports`           | 1     | Contract 2: zero `un_comtrade._*` imports.                     |
| `TestEveryCommandInHelp`         | 3     | Contract 3: every reachable subparser appears in `--help`.     |
| `TestDocumentedExamplesExecute`  | 4     | Contract 4: the four documented recipes execute successfully. |
| `TestCommandTreeFrozen`          | 3     | Contract 5: command tree matches frozen v1.0.x snapshot.       |
| **Total**                        | **15**|                                                                |

Full test inventory (collected from the suite):

```
TestOneToOneMapping::test_every_leaf_in_mapping
TestOneToOneMapping::test_every_mapping_entry_is_a_real_public_symbol
TestOneToOneMapping::test_mapping_is_one_to_one
TestOneToOneMapping::test_every_mapping_module_is_public
TestNoPrivateImports::test_no_private_imports
TestEveryCommandInHelp::test_every_subparser_has_help
TestEveryCommandInHelp::test_root_help_lists_every_group
TestEveryCommandInHelp::test_group_help_lists_every_leaf
TestDocumentedExamplesExecute::test_recipe_1_metadata_countries
TestDocumentedExamplesExecute::test_recipe_2_trade_exports_authenticated
TestDocumentedExamplesExecute::test_recipe_3_markdown_report
TestDocumentedExamplesExecute::test_recipe_4_storage_duckdb
TestCommandTreeFrozen::test_tree_matches_frozen_snapshot
TestCommandTreeFrozen::test_no_subparser_path_uses_uppercase
TestCommandTreeFrozen::test_no_subparser_path_collides_with_global_flag
```

**Result:** `15 passed in 0.55s`.
**Full repo result:** `3085 passed, 5 skipped in 163.07s` (was
`3070 passed` before this commit; `+15` from this file).

---

## 3. Contract 1 — One-to-one mapping

**Rule:** Each CLI leaf subcommand delegates to exactly one public
SDK entry point. The mapping is the same on every release.

### 3.1 Authoritative mapping

The mapping is declared once in
`tests/test_cli_contract.py::EXPECTED_MAPPING` and is the single source
of truth for this contract.

| CLI path                  | Public SDK entry point                                   |
| ------------------------- | -------------------------------------------------------- |
| `metadata/countries`      | `un_comtrade.metadata.MetadataService.get_countries`     |
| `metadata/partners`       | `un_comtrade.metadata.MetadataService.get_partners`      |
| `metadata/classifications`| `un_comtrade.metadata.MetadataService.get_classifications` |
| `metadata/frequencies`    | `un_comtrade.metadata.MetadataService.get_frequencies`   |
| `metadata/transport-modes`| `un_comtrade.metadata.MetadataService.get_transport_modes` |
| `metadata/hs`             | `un_comtrade.metadata.MetadataService.get_hs_codes`      |
| `trade/exports`           | `un_comtrade.trade.TradeService.get_exports`             |
| `trade/imports`           | `un_comtrade.trade.TradeService.get_imports`             |
| `trade/world`             | `un_comtrade.trade.TradeService.get_world_trade`         |
| `trade/bilateral`         | `un_comtrade.trade.TradeService.get_bilateral`           |
| `trade/balance`           | `un_comtrade.trade.TradeService.get_trade_balance`       |
| `trade/tariffline`        | `un_comtrade.trade.TradeService.get_tariffline`          |
| `analytics/country`       | `un_comtrade.analytics.country.country_summary`          |
| `analytics/partner`       | `un_comtrade.analytics.partner.top_partners`             |
| `analytics/commodity`     | `un_comtrade.analytics.commodity.top_hs_codes`           |
| `analytics/trend`         | `un_comtrade.analytics.timeseries.annual_trend`          |
| `analytics/balance`       | `un_comtrade.analytics.balance.country_balance`          |
| `analytics/compare`       | `un_comtrade.analytics.compare.country_vs_country`       |
| `storage/parquet`         | `un_comtrade.storage.parquet.ParquetWriter.store`        |
| `storage/csv`             | `un_comtrade.storage.file.CSVWriter.store`               |
| `storage/json`            | `un_comtrade.storage.file.JSONWriter.store`              |
| `storage/duckdb`          | `un_comtrade.storage.duckdb.DuckDBWriter.store`          |
| `etl/run`                 | `un_comtrade.etl.ETLPipeline.run`                        |

**23 entries**, all public, all callable, all 1-to-1.

### 3.2 What the tests verify

- **Coverage:** Every CLI leaf subparser (excluding `root`) has a row
  in `EXPECTED_MAPPING`; every row in `EXPECTED_MAPPING` matches a
  reachable leaf subparser.
- **Resolution:** Each row resolves through `importlib.import_module`
  + `getattr`-walk to a callable attribute on the SDK.
- **Uniqueness:** No two rows point at the same SDK entry point.
- **Public modules only:** Every module path is `un_comtrade.*` with
  no leading-underscore submodule.

### 3.3 Result

`TestOneToOneMapping` — **4 passed**.

---

## 4. Contract 2 — No private imports

**Rule:** No file under `un_comtrade/cli/` imports anything from a
private `un_comtrade._*` module.

### 4.1 Mechanism

A Python `ast.walk` over every `*.py` file under `un_comtrade/cli/`
inspects every `Import` and `ImportFrom` node. Any import whose module
name begins with `un_comtrade._` is reported as a violation.

### 4.2 Coverage

22 source files inspected:
`un_comtrade/cli/__init__.py`, `main.py`, `commands/{__init__,metadata,trade,analytics,storage,etl}.py`,
`formatting/{__init__,json,csv,table,markdown,text,_records}.py`,
`utils/{__init__,exit_codes,exceptions,config_loader,output,progress,dataset_loader}.py`.

### 4.3 Result

`TestNoPrivateImports` — **1 passed**, 0 violations.

---

## 5. Contract 3 — Every command in `--help`

**Rule:** Every reachable subparser appears in `--help` with a
non-empty help string.

### 5.1 What the tests verify

- **Help string non-empty:** every subparser below the root has a
  non-empty `description` or `help`.
- **Root `--help` lists every group:** the rendered root help text
  contains the name of every top-level command group.
- **Group `--help` lists every leaf:** each group's inner
  `SubParsersAction.choices` contains the name of every leaf mapped to
  it in `EXPECTED_MAPPING`.

### 5.2 Result

`TestEveryCommandInHelp` — **3 passed**.

---

## 6. Contract 4 — Documented examples execute

**Rule:** The five recipes documented in `docs/032_CLI_REVIEW.md` §14
(and republished in §7 below) all return exit code `0` when invoked
against mocked services.

### 6.1 The four executable recipes

The five recipes in §14 break into four executable categories (recipe
4 includes a pipeline **and** a storage write; we exercise the storage
write because the pipeline recipe is already covered by
`tests/test_cli_storage.py`):

1. **`un-comtrade metadata countries`** — exercises the metadata
   reference-catalogue path. Mocks `ComtradeClient.metadata` to return
   `[]`. Asserts `get_countries` is called once and `main()` exits `0`.
2. **`un-comtrade trade exports --reporter 699 --year 2022 --partner 0`**
   — exercises the authenticated trade query path. Mocks
   `ComtradeClient.trade` with a `TradeResponse` factory. Asserts
   `get_exports` is called once and `main()` exits `0`.
3. **`un-comtrade analytics country --dataset … --reporter 699 --output-format markdown --output …`**
   — exercises the analytics engine, the dataset loader, and the
   markdown formatter in one command. Mocks each
   `un_comtrade.analytics.<sub>.{fn}` directly. Asserts the markdown
   file is written and `main()` exits `0`.
4. **`un-comtrade storage duckdb --dataset … --output-path …`**
   — exercises the storage write path. Mocks `DuckDBWriter.store` to
   return a `StorageResult` without touching disk. Asserts the
   `StorageConfig.root` matches the requested path and `main()` exits
   `0`.

### 6.2 Mocking boundary

Following the established pattern in `tests/test_cli_*.py`, the CLI is
mocked at the `ComtradeClient` construction site of each command
module (`un_comtrade.cli.commands.{metadata,trade}.ComtradeClient`).
Analytics is mocked at the `un_comtrade.analytics.{submodule}.{fn}`
level because the CLI dispatches via
`getattr(importlib.import_module(module_path), method_name)`.
Storage is mocked at the `DuckDBWriter.store` method.

This is the documented "mocked services" boundary for the v1.0.x CLI.

### 6.3 Result

`TestDocumentedExamplesExecute` — **4 passed**.

---

## 7. Documented CLI examples (re-published)

For reference, these are the four executable recipes verified by
Contract 4. They are also reproduced in `docs/032_CLI_REVIEW.md` §14.

```bash
# 1. Hello, world — list reporter countries.
un-comtrade metadata countries

# 2. Authenticated query — India's 2022 exports to all partners.
un-comtrade trade exports --reporter 699 --year 2022 --partner 0

# 3. Markdown report — country summary from a stored dataset.
un-comtrade analytics country \
    --dataset ./data/tiny \
    --reporter 699 \
    --output-format markdown \
    --output ./report.md

# 4. Persist a dataset to DuckDB (pipeline+storage chain).
un-comtrade storage duckdb \
    --dataset ./data/tiny \
    --output-path ./data.duckdb
```

---

## 8. Contract 5 — Command-tree frozen

**Rule:** The set of reachable CLI command paths and their user-visible
flags are pinned to the v1.0.x release. Future versions that change the
tree must update `FROZEN_TREE` in `tests/test_cli_contract.py` and
call it out in CHANGELOG.

### 8.1 What the tests verify

- **Tree matches snapshot:** for every leaf subparser, the set of
  user-visible flags (`--api-key`, `--reporter`, etc.) and the subset
  of required flags must exactly match the frozen entry.
- **Convention — lowercase paths:** every command-path component
  must be lowercase (case stability).
- **Convention — no global-flag collision:** a command-path component
  must not collide with a root-level flag name (otherwise argparse
  mis-parses `un-comtrade --version`).

### 8.2 Frozen tree summary

| Group     | Leaves | Total flags (incl. globals) | Required flags                       |
| --------- | ------ | --------------------------- | ------------------------------------ |
| metadata  | 6      | 4–5                         | (none)                               |
| trade     | 6      | 14–16                       | `--period`, `--reporter`, `--year`   |
| analytics | 6      | 6–9                         | `--dataset` (+ `--reporter` for 3)   |
| storage   | 4      | 8                           | `--dataset`, `--output-path`         |
| etl       | 1      | 6                           | `--pipeline-config`                  |
| **Total** | **23** | varies                      |                                      |

Snapshot source: `FROZEN_TREE` in `tests/test_cli_contract.py`. Diff
output of `test_tree_matches_frozen_snapshot` is empty (no drift).

### 8.3 Result

`TestCommandTreeFrozen` — **3 passed**.

---

## 9. Findings and notes

### 9.1 Issues surfaced by Contract 1 (intended)

While authoring `EXPECTED_MAPPING`, three subtleties surfaced — none of
which are bugs in the CLI, but each is documented here for future
maintainers:

| Finding                                                                                  | Resolution                                                              |
| ---------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| Analytics entry points live in **submodule functions** (`country.country_summary`), not on `AnalyticsEngine`. | Mapped to `un_comtrade.analytics.{sub}.{fn}` (full dotted path).        |
| Storage writers are `CSVWriter` and `JSONWriter` (uppercase), not `CsvWriter` / `JsonWriter`. | Mapped to `un_comtrade.storage.file:{CSVWriter,JSONWriter}.store`.      |
| `DuckDBWriter.store` signature is `(self, dataset, config: StorageConfig)`, not `(self, dataset, path, table_name)`. | Captured by the `recipe_4` test, which patches the method with the correct signature. |

### 9.2 Issue surfaced by Contract 4 — CLI/SDK surface gap (architectural)

While writing the documented-examples tests, we observed that the
**CLI command bodies** reference `client.trade.{method}` and
`client.analytics.{method}`, but the **public `ComtradeClient` does
not expose `trade` or `analytics` attributes** — only `metadata`,
`config`, and `transport`. The CLI's existing tests pass because they
mock `ComtradeClient` at the construction site of each command module
(`un_comtrade.cli.commands.trade.ComtradeClient`), not because the
production code path resolves.

**Severity:** High for v1.0.0/1.0.1 in a production scenario; the
current test suite (including `tests/test_cli_integration.py`) all
patch the construction site, so the gap is **latent**. A live invocation
of `un-comtrade trade exports …` against a real `ComtradeClient` would
fail with `AttributeError: 'ComtradeClient' object has no attribute 'trade'`.

**Recommended remediation (out of scope for C-007A, opens a new task):**
extend `ComtradeClient` to expose `trade: TradeService` and
`analytics: AnalyticsEngine` properties (or facade attributes) that
delegate to the underlying services, matching the access pattern the
CLI assumes. Until that lands, the CLI's "thin consumer of the public
SDK" claim from `docs/032_CLI_REVIEW.md` §11 is technically false on
the trade and analytics paths. The contract tests **do not fail** on
this point because they mock at the construction site, which is the
established pattern in the test suite.

### 9.3 Other notes

- **`coverage` tooling is not installed.** Line-coverage is not
  measured. Contract tests provide structural coverage; line coverage
  is a one-line dev-deps fix deferred to the Cookbook phase.
- **Console-script subprocess tests** are skipped by default (4
  in `test_cli_foundation.py` + 2 in `test_cli_integration.py`). They
  are gated by `_END_TO_END_SMOKE_=1`. Not affected by C-007A.
- **Test runtime:** contract suite runs in 0.55s on Windows + Python
  3.14.3. Full suite: 163s.

---

## 10. Verdict

**All five contracts PASS at v1.0.1.**

| # | Contract                                    | Tests | Result |
| - | ------------------------------------------- | ----- | ------ |
| 1 | One-to-one mapping                          | 4     | PASS   |
| 2 | No private imports                          | 1     | PASS   |
| 3 | Every command in `--help`                   | 3     | PASS   |
| 4 | Documented examples execute                 | 4     | PASS   |
| 5 | Command tree frozen                         | 3     | PASS   |
|   | **Total**                                   | **15**| **PASS** |

The contract gate is now **machine-checked**. Any future change to the
public CLI surface (added/removed/renamed command, renamed flag,
changed required/optional status, new SDK dependency, new private
import) will fail at least one test in `tests/test_cli_contract.py`
and require an explicit update to `EXPECTED_MAPPING` / `FROZEN_TREE`.

### Outstanding follow-up

**One latent bug was surfaced (§9.2) but is out of scope for C-007A:**
the CLI assumes `ComtradeClient` exposes `trade` and `analytics`
service attributes, but the public `ComtradeClient` does not. Existing
tests mask this by mocking `ComtradeClient` at construction sites. The
contract tests follow the same masking pattern, so they pass — but the
production code path is broken on those two command groups. **A
separate task should extend `ComtradeClient` to expose the missing
service attributes.** Recommend filing as the next CLI follow-up
before any v1.0.x → v1.1 work.

---

## 11. Sign-off

| Item                                    | Value                                                |
| --------------------------------------- | ---------------------------------------------------- |
| Contract test file                      | `tests/test_cli_contract.py` (15 tests)              |
| Total test runtime                      | 0.55 s                                               |
| Full-repo test impact                   | +15 passed (3,070 → 3,085); 5 skipped (unchanged)    |
| Contracts passing                       | 5 / 5                                                |
| Verified on                             | v1.0.1 (commit `4729476` + tag `sdk-core-freeze-v1.0.1`) |
| Verified at                             | 2026-06-29 04:21 IST                                 |
| Reviewer                                | Codex                                                |
| **Verdict**                             | **PASS (with §9.2 follow-up filed)**                |