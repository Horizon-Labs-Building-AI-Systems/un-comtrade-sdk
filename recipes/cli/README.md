# Cookbook — `cli/` Category

Recipes that exercise the **`un-comtrade` command-line
interface** (the entry point defined in
`un_comtrade/cli/main.py`).

A `cli/` recipe is a **shell session transcript** that
demonstrates one CLI command end-to-end: the invocation,
the expected output, and the exit code. The recipe is
delivered as a single shell script (a `.sh` file on
POSIX; a `.ps1` file on Windows) that the consumer can
copy, paste, and run.

## Purpose

A consumer should be able to read this category and
understand:

- How to invoke each CLI command.
- What the command's output looks like in practice.
- How to chain CLI commands in a shell pipeline.
- How to handle CLI errors (exit codes, error
  messages).
- How the CLI maps to the SDK's library surface.

## SDK services exercised

| CLI command group       | Library surface            | Used in planned recipes |
| ----------------------- | -------------------------- | ------------------------ |
| `un-comtrade metadata`  | `client.metadata.*`        | ✓                        |
| `un-comtrade trade`     | `client.trade.*`           | ✓                        |
| `un-comtrade analytics` | `client.analytics.*`       | ✓                        |
| `un-comtrade etl`       | `client.etl.*`             | ✓                        |
| `un-comtrade storage`   | `client.storage.*`         | ✓                        |

## API key policy

| `requires_api_key` | Default for this category |
| ------------------ | ------------------------- |
| depends on command | (declared per recipe)     |

A `cli/` recipe declares `requires_api_key` based on
the underlying command's library surface:

- `un-comtrade metadata *` → `no`
- `un-comtrade trade *` → `yes`
- `un-comtrade analytics *` → `no`
- `un-comtrade etl *` → `yes` (typically)
- `un-comtrade storage *` → `no`

A recipe that mixes commands (a shell pipeline) sets
`requires_api_key` to the **maximum** of the commands
in the pipeline.

## Estimated runtime band

| `estimated_runtime` | Typical recipes in this category                  |
| ------------------- | ------------------------------------------------- |
| `<1s`               | metadata subcommands, `--help`                    |
| `<10s`              | one trade query                                   |
| `<1min`             | one trade query returning > 1k records            |
| `1-10min`           | multi-command pipelines                           |

A `cli/` recipe inherits the runtime of its underlying
command(s). The recipe's frontmatter records the
**end-to-end** runtime of the shell script, not the
per-command runtime.

## Shipped recipe roster (CB-006 batch 1)

| Recipe ID     | File                                  | Title                                                          | Difficulty      | Runtime   | API key |
| ------------- | ------------------------------------- | -------------------------------------------------------------- | --------------- | --------- | ------- |
| `RECIPE-091`  | `01_metadata_cli.py`                  | List reporter countries via the CLI                             | beginner        | `<1s`     | no      |
| `RECIPE-095`  | `02_trade_cli.py`                     | Fetch export records via the CLI                                | beginner        | `<1min`   | yes     |
| `RECIPE-099`  | `03_analytics_cli.py`                 | Run country-summary analytics via the CLI                       | intermediate    | `<10s`    | no      |
| `RECIPE-100`  | `04_storage_cli.py` (RECIPE-101 slot) | Persist a dataset via the CLI (Parquet writer)                  | beginner        | `<30s`    | no      |
| `RECIPE-101`  | `05_etl_cli.py` (RECIPE-100 slot)     | Run an ETL pipeline via the CLI                                 | intermediate    | `1-10min` | yes     |
| `RECIPE-104`  | `06_output_formats_cli.py`            | Render the same command in five output formats                  | beginner        | `<1s`     | no      |

**Coverage of the four Cookbook pillars:**

- **Authentication** — recipe 02 (trade) and recipe 05 (etl)
  declare `requires_api_key: yes` because their CLI
  commands call `ComtradeClient` to hit the live API.
  Recipes 01/03/04/06 are key-free (`no`) — they read
  from cached catalogues, stored datasets, or mock
  responses.
- **Filtering** — recipe 02 demonstrates `--reporter`,
  `--year`, `--partner`, `--classification`,
  `--max-records` (the full trade filter surface).
- **Output formats** — recipe 06 explicitly exercises all
  five CLI output formats (`json`, `table`, `csv`,
  `markdown`, `text`); every other recipe defaults to
  `table` for legibility.
- **Error handling** — recipes' `main()` functions
  inherit the CLI's documented exit codes (0 success,
  2 user-error, 78 config-error, 77 auth-error, 69
  network-error). The recipes surface CLI exit codes
  unchanged through their own return values.

## Planned recipe roster

The following recipes are planned for future batches
(RECIPE-090, 092-094, 096-098, 102-103) and have not yet
been shipped. They cover specialised scenarios
(get-country, search-hs, validate-query, error-path
recipes, shell-pipeline chaining, etc.).

| Recipe ID     | Title                                                                | Difficulty      | Runtime   | API key |
| ------------- | -------------------------------------------------------------------- | --------------- | --------- | ------- |
| `RECIPE-090`  | `un-comtrade --help` and `--version`                                 | beginner        | `<1s`     | no      |
| `RECIPE-092`  | `un-comtrade metadata get-country 699`                               | beginner        | `<1s`     | no      |
| `RECIPE-093`  | `un-comtrade metadata list-classifications`                          | beginner        | `<1s`     | no      |
| `RECIPE-094`  | `un-comtrade metadata search-hs "electric vehicles"`                 | intermediate    | `<1s`     | no      |
| `RECIPE-096`  | `un-comtrade trade get-exports 699 --year 2022 --format parquet`     | beginner        | `<1min`   | yes     |
| `RECIPE-097`  | `un-comtrade trade get-exports 699 --year 2022 --partner 0`          | intermediate    | `<1min`   | yes     |
| `RECIPE-098`  | `un-comtrade trade validate-query ...`                               | beginner        | `<1s`     | yes     |
| `RECIPE-102`  | Chain `trade get-exports` into `analytics country-summary`           | intermediate    | `1-10min` | yes     |
| `RECIPE-103`  | Handle a `RateLimitError` from the CLI (retry, exit code)             | intermediate    | `<1min`   | yes     |

## Per-recipe cross-references

A `cli/` recipe that needs to explain a behaviour
links to:

- `docs/007_SDK_SPECIFICATION.md` §3.4 (the
  underlying library surface)
- `docs/032_CLI_REVIEW.md`
- `docs/033_CLI_CONTRACT_VERIFICATION.md`
- `docs/008_METADATA_LAYER_SPEC.md` (for
  `metadata` subcommands)
- `docs/009_TRADE_LAYER_SPEC.md` (for `trade`
  subcommands)
- `docs/011_ETL_SPECIFICATION.md` (for `etl`
  subcommands)
- `docs/012_STORAGE_SPECIFICATION.md` (for `storage`
  subcommands)

## Category-specific notes

- **Shell scripts are first-class recipes.** A
  `cli/` recipe is a single shell script
  (`RECIPE_NNN_<slug>.sh` on POSIX, `.ps1` on
  Windows). The script:
  - Sets up a clean environment (`set -euo pipefail`
    on POSIX; `$ErrorActionPreference = "Stop"` on
    Windows).
  - Runs one or more `un-comtrade` commands.
  - Asserts on the exit code (`$?` on POSIX;
    `$LASTEXITCODE` on Windows).
  - Asserts on a substring of the output (using
    `grep` / `Select-String`).
  - Prints a final summary line.
- **Exit codes match the library.** The CLI's exit
  codes follow the same map as the library
  (`recipes/README.md` §6.4). A `cli/` recipe that
  demonstrates an error path exits with the
  documented code.
- **Platform is declared.** A recipe's frontmatter
  records the platform it targets. Cross-platform
  recipes ship as two files: `RECIPE_NNN.sh` and
  `RECIPE_NNN.ps1`, sharing the same recipe_id
  frontmatter.

## CLI exit code map (normative)

The CLI's exit codes match the library's exit codes
(`recipes/README.md` §6.4):

| Exit code | Meaning                                                  |
| --------- | -------------------------------------------------------- |
| `0`       | success                                                  |
| `1`       | generic failure                                          |
| `2`       | invalid arguments                                        |
| `3`       | SDK `ValidationError`                                    |
| `4`       | SDK `AuthenticationError` / `AuthorizationError`         |
| `5`       | SDK `RateLimitError` (after retries exhausted)           |
| `6`       | SDK `NetworkError` / `TimeoutError` / `RetryError`       |
| `7`       | SDK `ServerError` (after retries exhausted)              |
| `8`       | recipe-specific business-rule failure                    |

A `cli/` recipe that uses a different exit code is
rejected at review.

## How to add a recipe to this category

1. Choose the next free `RECIPE-NNN` ID from the
   roster above.
2. Copy the appropriate skeleton to
   `recipes/cli/RECIPE_NNN_<slug>.sh` (POSIX) or
   `.ps1` (Windows).
3. Implement the body per `recipes/_TEMPLATE.md`
   (adapted for shell).
4. Update this README's roster table.
5. Submit a pull request.

A `cli/` recipe that does not invoke the
`un-comtrade` binary belongs in another category
(typically `end_to_end/` or the relevant library
category).
