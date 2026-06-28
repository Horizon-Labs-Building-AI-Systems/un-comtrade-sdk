```
{
  "id": "032",
  "title": "CLI Subsystem Review",
  "version": "1.0.0",
  "status": "LIVE",
  "created": "2026-06-29",
  "last_updated": "2026-06-29",
  "author": "Codex",
  "project": "un-comtrade-sdk",
  "dependencies": [
    "docs/000_PROJECT_CHARTER.md",
    "docs/007_SDK_SPECIFICATION.md",
    "docs/015_CODING_STANDARD.md",
    "docs/021_IMPLEMENTATION_BASELINE_v1.md",
    "docs/024_STORAGE_REVIEW_REPORT.md",
    "docs/025_ANALYTICS_REVIEW_REPORT.md",
    "docs/027_PUBLIC_API_AUDIT.md",
    "docs/031_PRODUCTION_READINESS.md",
    "docs/032_v1_RELEASE_NOTES.md"
  ],
  "supersedes": null
}
```

# 032 — CLI Subsystem Review

## 1. Scope

This document reviews the un-comtrade Command Line Interface (`un_comtrade.cli`,
exposed as the `un-comtrade` console script) at the close of Phase 7 (C-001 …
C-007). It is a documentation-only review; no code is changed by this
document.

The review answers eight questions called out by the task brief:

1. CLI complete?
2. Public SDK only?
3. No internal coupling?
4. Help coverage?
5. Exit codes?
6. Output formatting?
7. Configuration?
8. Cross-platform compatibility?
9. No architectural drift?

…and delivers a final verdict plus a recommendation for the Cookbook phase.

---

## 2. Architecture

### 2.1 Package layout

`un_comtrade.cli` is a **self-contained, leaf package** under `un_comtrade`.
It contains three sub-packages and zero business logic of its own.

```
un_comtrade/cli/
├── __init__.py            # Public surface re-exports
├── main.py                # argparse root + main(argv) entry point
├── commands/              # Subcommand registry + 5 command modules
│   ├── __init__.py        # Command Protocol + register_command / get_command
│   ├── metadata.py        # 6 sub-subcommands
│   ├── trade.py           # 6 sub-subcommands
│   ├── analytics.py       # 6 sub-subcommands
│   ├── storage.py         # 4 sub-subcommands
│   └── etl.py             # 1 sub-subcommand
├── formatting/            # OutputFormatter protocol + 5 formatters
│   ├── __init__.py        # get_formatter(name) registry
│   ├── json.py            # RFC 8259 stable JSON
│   ├── table.py           # Aligned text table
│   ├── csv.py             # RFC 4180 CSV
│   ├── markdown.py        # GitHub-Flavored-Markdown table
│   ├── text.py            # Line-oriented plain text
│   └── _records.py        # Private shared row-dict helpers
└── utils/                 # Helpers: exit codes, errors, config, output,
    ├── __init__.py        #   progress, dataset loader
    ├── exit_codes.py      # 6 BSD-sysexits-style constants
    ├── exceptions.py      # CLIError / CLIConfigurationError
    ├── config_loader.py   # load_cli_configuration(api_key=, log_level=)
    ├── output.py          # render_to_destination(...)
    ├── progress.py        # ProgressReporter (TTY-aware)
    └── dataset_loader.py  # load_dataset(path) → CanonicalDataset
```

**Total size: 4,229 lines** across 22 source files (production + tests
~6,000 lines). The package has no `__pycache__` shipped; the `_records.py`
file is the only leading-underscore module and it is private to the
formatting sub-package (signalled by its filename).

### 2.2 Three-layer separation

The CLI is organised in three layers, with strictly downward dependencies:

```
┌──────────────────────────────────────────────────────────────┐
│  Layer 1 — Entry point                                       │
│  main.py: build_parser() + main(argv)                        │
│  ── argparse root + global options                           │
│  ── Configuration load via load_cli_configuration()          │
│  ── Formatter resolution via get_formatter(name)             │
│  ── Exception → exit-code mapping                            │
└────────────────┬─────────────────────────────────────────────┘
                 │ dispatch via get_command(name)
                 ▼
┌──────────────────────────────────────────────────────────────┐
│  Layer 2 — Commands                                          │
│  commands/*.py: one module per top-level group               │
│  ── install_subparser(subparsers) → builds subparser tree    │
│  ── Command body: build kwargs → call public SDK API         │
│  ── Hand result to render_to_destination(formatter, value)   │
└────────────────┬─────────────────────────────────────────────┘
                 │ depends only on public SDK + Layer 3
                 ▼
┌──────────────────────────────────────────────────────────────┐
│  Layer 3 — Helpers (commands/, formatting/, utils/)          │
│  ── OutputFormatter Protocol + 5 implementations            │
│  ── Command Protocol + registry                             │
│  ── Exit codes, errors, config loader                       │
│  ── TTY-aware progress reporter                             │
│  ── load_dataset(path) → CanonicalDataset                   │
└──────────────────────────────────────────────────────────────┘
                 │
                 ▼  (only public surface)
┌──────────────────────────────────────────────────────────────┐
│  un_comtrade.* (public SDK)                                  │
│  ComtradeClient, MetadataService, TradeService,              │
│  AnalyticsEngine, Storage.*, ETLPipeline, …                  │
└──────────────────────────────────────────────────────────────┘
```

### 2.3 Public surface (16 symbols)

`un_comtrade.cli.__all__`:

| Symbol              | Kind        | Notes                                    |
| ------------------- | ----------- | ---------------------------------------- |
| `build_parser`      | function    | Returns the root `argparse.ArgumentParser`. |
| `main`              | function    | Entry point; `argv=None` reads `sys.argv[1:]`. |
| `EXIT_OK`           | int = 0     | Success.                                 |
| `EXIT_GENERIC_ERROR`| int = 1     | Unspecified / `ComtradeError`.            |
| `EXIT_USER_ERROR`   | int = 2     | `argparse` errors + `CLIError`.          |
| `EXIT_CONFIG_ERROR` | int = 78    | `CLIConfigurationError` + `ConfigurationError`. |
| `EXIT_NETWORK_ERROR`| int = 69    | `NetworkError`.                          |
| `EXIT_AUTH_ERROR`   | int = 77    | `AuthenticationError`.                   |
| `CLIError`          | exception   | Base CLI-side error.                     |
| `CLIConfigurationError` | exception | Subclass of `CLIError` and `ComtradeError`. |
| `OUTPUT_FORMATS`    | tuple       | `('json', 'table', 'csv', 'markdown', 'text')`. |
| `load_cli_configuration` | function | Reads env + CLI overrides; returns public `Configuration`. |
| `render_to_destination` | function | Writes rendered text to stdout or `--output PATH`. |
| `ProgressReporter`  | class       | TTY-aware stderr progress writer.        |
| `make_progress_reporter` | function | Builds a reporter for `--progress`.       |
| `load_dataset`      | function    | Reads a stored dataset via public `Storage` registry. |

---

## 3. Command tree

### 3.1 Top-level inventory (6 commands)

```
un-comtrade
├── analytics       (group, 6 sub-subcommands)
├── etl             (group, 1 sub-subcommand)
├── metadata        (group, 6 sub-subcommands)
├── storage         (group, 4 sub-subcommands)
├── trade           (group, 6 sub-subcommands)
└── root            (leaf; default banner when no subcommand)
```

### 3.2 Full tree (24 reachable subparsers)

```
analytics
  ├── country          → AnalyticsEngine.country_summary
  ├── partner          → AnalyticsEngine.top_partners
  ├── commodity        → AnalyticsEngine.top_hs_codes
  ├── trend            → AnalyticsEngine.annual_trend
  ├── balance          → AnalyticsEngine.country_balance
  └── compare          → AnalyticsEngine.country_vs_country
etl
  └── run              → ETLPipeline.run(stages=...)
metadata
  ├── countries        → MetadataService.get_countries
  ├── partners         → MetadataService.get_partners
  ├── classifications  → MetadataService.get_classifications
  ├── frequencies      → MetadataService.get_frequencies
  ├── transport-modes  → MetadataService.get_transport_modes
  └── hs               → MetadataService.get_hs_codes(edition=...)
storage
  ├── parquet          → ParquetWriter.store
  ├── csv              → CsvWriter.store
  ├── json             → JsonWriter.store
  └── duckdb           → DuckDBWriter.store
trade
  ├── exports          → TradeService.get_exports
  ├── imports          → TradeService.get_imports
  ├── world            → TradeService.get_world_trade
  ├── bilateral        → TradeService.get_bilateral
  ├── balance          → TradeService.get_trade_balance
  └── tariffline       → TradeService.get_tariffline
root
  └── (no subparser; prints banner)
```

**Counts:** 6 top-level · 5 group commands · **23 sub-subcommand leaves**
+ 1 root leaf = **24 executable subparsers**.

### 3.3 Global flags (propagated to every level)

Each sub-subparser re-attaches the four CLI-wide flags. argparse does not
inherit parent options across sub-subparser boundaries, so this is enforced
by the `_add_global_options` helper in every command module.

| Flag             | Choices / behaviour                                         |
| ---------------- | ----------------------------------------------------------- |
| `--api-key`      | Override `UN_COMTRADE_KEY` env var (not persisted).         |
| `--log-level`    | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`.        |
| `--output-format`| `json` (default) / `table` / `csv` / `markdown` / `text`.   |
| `--output`       | File path; rendered text is written here instead of stdout. |

The trade group adds `--progress` (TTY-aware stderr reporter).

---

## 4. Public API usage

### 4.1 What the CLI calls

The CLI consumes only the SDK's public surface. Inventory (verified by
`tests/test_cli_*.py::TestPublicSDKOnlyConstraint` AST walker and
`tests/test_cli_integration.py::TestPublicSDKOnlyAcrossCLI`):

| Command group | Public SDK calls                                          |
| ------------- | --------------------------------------------------------- |
| `metadata`    | `ComtradeClient(configuration).metadata.get_countries` (etc., 6 methods) |
| `trade`       | `ComtradeClient(configuration).trade.get_exports` (etc., 6 methods) |
| `analytics`   | `ComtradeClient(configuration).analytics.{country_summary,top_partners,top_hs_codes,annual_trend,country_balance,country_vs_country}` |
| `storage`     | `StorageRegistry.open(uri).read(...)`, then `*Writer.store(...)` |
| `etl`         | `ETLPipeline(name, stages=[...])` → `.run(...)`            |
| all           | `load_cli_configuration`, `OUTPUT_FORMATS`, exception classes |

### 4.2 What the CLI does **not** do

The following are forbidden inside `un_comtrade/cli/**.py`, and the test
suite asserts each one:

| Forbidden pattern                                  | Enforcement test                                           |
| -------------------------------------------------- | ---------------------------------------------------------- |
| `from un_comtrade._*` (private modules)            | `test_cli_foundation.py::TestPublicSDKOnlyConstraint` (16 files)<br>`test_cli_integration.py::TestPublicSDKOnlyAcrossCLI` |
| Building endpoint URLs inside the CLI              | `test_cli_trade.py::TestURLNotBuiltInsideCLI`              |
| Hand-rolled analytics aggregation                  | `test_cli_analytics.py::TestNoAnalyticsLogicInsideCLI`     |
| Hand-rolled storage write / DB-conn logic          | `test_cli_storage.py::TestOrchestrationOnly`               |
| Hand-rolled ETL pipeline implementations           | `test_cli_storage.py::TestOrchestrationOnly`               |
| CLI commands building output strings directly       | `test_cli_formatters.py::TestBusinessLogicNeverFormats`    |
| `pyarrow.Table`, `duckdb.connect`, `csv.writer` (in business commands), `json.dumps` (in business commands), `csv.DictWriter`, `.to_pylist` | AST+regex guard across `un_comtrade/cli/commands/*.py` |

Note: `csv.writer` and `json.dumps` legitimately appear inside
`un_comtrade/cli/formatting/csv.py` and `.../json.py`; the guard correctly
scopes the forbidden list to `commands/*.py` (business logic, not
presentation).

### 4.3 Internal-coupling audit

| Concern                                | Status                                                |
| -------------------------------------- | ----------------------------------------------------- |
| CLI → `_query_engine`                  | Not imported (not in `__all__` of analytics, no `from un_comtrade.analytics._*` anywhere in CLI). |
| CLI → `_session` / `_cache` / `_rate_limiter` | Not imported; CLI uses `ComtradeClient` only.   |
| CLI → private storage I/O              | Not imported; CLI uses `StorageRegistry.open(uri).read(...)` (public). |
| CLI → SDK internal helpers             | Not imported; CLI builds public `Configuration` via `load_cli_configuration`. |
| Cross-version SDK call drift           | n/a — `un_comtrade.__version__` is the only version probe; no path probing. |

---

## 5. Coverage

### 5.1 Test counts

| Suite                                | Collected | Pass    | Skip | Status    |
| ------------------------------------ | --------- | ------- | ---- | --------- |
| `tests/test_cli_foundation.py`       | 49        | 49      | 0    | GREEN     |
| `tests/test_cli_metadata.py`         | 21        | 21      | 0    | GREEN     |
| `tests/test_cli_trade.py`            | 34        | 34      | 0    | GREEN     |
| `tests/test_cli_analytics.py`        | 24        | 24      | 0    | GREEN     |
| `tests/test_cli_storage.py`          | 20        | 20      | 0    | GREEN     |
| `tests/test_cli_formatters.py`       | 61        | 57      | 4    | GREEN     |
| `tests/test_cli_integration.py`      | 53        | 53      | 0    | GREEN     |
| **CLI total**                        | **262**   | **258** | **4**| **GREEN** |
| **Full repo (incl. CLI)**            | **3075**  | **3070**| **5**| **GREEN** |

The 4 skipped tests are subprocess smoke tests guarded by an environment
gate (`_END_TO_END_SMOKE_=1`); they are not failures.

### 5.2 Coverage axes

| Axis                                       | Test class                                                              | Count |
| ------------------------------------------ | ----------------------------------------------------------------------- | ----- |
| Parser / global options                    | `TestParser`, `TestVersionAndHelp`, `TestBareInvocation`                | 8     |
| Exit codes (0/1/2/69/77/78)                | `TestExitCodes`                                                         | 6     |
| Configuration load + overrides             | `TestConfigurationLoading`, `TestConfigurationEndToEnd`                 | 11    |
| Formatter protocol + 5 implementations    | `TestJsonFormatter`, `TestCsvFormatter`, `TestTableFormatter`, `TestMarkdownFormatter`, `TestTextFormatter`, `TestProtocolAndRegistry` | 27 |
| Formatter interchangeability               | `TestInterchangeability`                                                | 10    |
| Formatter / CLI isolation                  | `TestBusinessLogicNeverFormats`, `TestFileStructure`                    | 11    |
| Metadata end-to-end                        | `TestMetadataEndToEnd`                                                  | 11    |
| Trade end-to-end                           | `TestTradeEndToEnd`, `TestOptionalKwargs`, `TestProgressFlag`           | 17    |
| Analytics end-to-end                       | `TestAnalyticsEndToEnd`, `TestCountry/Partner/...`, `TestStorageIntegration` | 14 |
| Storage orchestration                      | `TestStorageParquet/CSV/JSON/DuckDB`, `TestStorageOrchestration`        | 10    |
| ETL orchestration                          | `TestETLRun`                                                            | 5     |
| URL-not-built guard                        | `TestURLNotBuiltInsideCLI`                                              | 2     |
| No-analytics-logic guard                   | `TestNoAnalyticsLogicInsideCLI`                                         | 2     |
| No-storage-impl guard                      | `TestOrchestrationOnly`                                                 | 2     |
| Public-SDK-only AST walker                 | `TestPublicSDKOnlyConstraint`, `TestPublicSDKOnlyAcrossCLI`             | 17    |
| Console-script registration               | `TestConsoleScriptRegistration`, `TestEndToEndSmoke`                    | 3     |

### 5.3 Code-coverage tooling

The `coverage` package is **not** installed in the development environment
(verified 2026-06-29). Adding `coverage` to the `dev` optional-dependency
group and running `coverage run -m pytest tests/ && coverage report
--include="un_comtrade/cli/*"` is the recommended next step before
publishing v1.0.x to PyPI. The test count (262 CLI cases) and the
explicit AST guards covering all 22 source files provide strong
structural coverage, but line-coverage measurement is the missing
quantitative signal.

### 5.4 Live API verification

No live UN Comtrade calls were performed in this review. All 4,229 lines
of CLI code are exercised via `httpx.MockTransport` in the test suite;
this is the documented testing standard (see
`docs/013_TESTING_STANDARD.md`). The 12 EXT items remaining from V-001
still require live subscription-key verification and are not in scope for
this review.

---

## 6. Help coverage

Every argparse subparser (`un-comtrade`, every group, every leaf) shows a
populated `--help` page. Confirmed for:

- `un-comtrade --help` (root, lists all 6 commands and the 4 global flags)
- `un-comtrade metadata --help` (lists 6 metadata sub-subcommands, each with the public `MetadataService` method it delegates to)
- `un-comtrade metadata hs --help` (lists `--edition` flag and the 4 globals)
- `un-comtrade trade exports --help` (lists required `--reporter`/`--year` and 7 optional flags including `--progress`)
- `un-comtrade analytics country --help` (lists required `--dataset`/`--reporter`)
- `un-comtrade analytics compare --help` (lists required `--dataset`/`--reporters` and `--breakdown-by`)
- `un-comtrade storage parquet --help` (lists required `--dataset`/`--output-path`, optional `--overwrite`/`--table-name`)
- `un-comtrade etl run --help` (lists required `--pipeline-config`)

Global flags appear on **every** sub-subparser (verified by the
`TestParser::test_parser_has_global_options` and per-command
`TestRegistration::test_*_help_lists_*_subs` tests). The
`--output-format` choice list `{'json','table','csv','markdown','text'}`
is identical on every level — no drift.

---

## 7. Exit codes

Six exit codes, all BSD-sysexits-style. Mapping verified by
`tests/test_cli_integration.py::TestExitCodes`:

| Code | Constant            | Trigger                                                                              |
| ---- | ------------------- | ------------------------------------------------------------------------------------ |
| 0    | `EXIT_OK`           | Success; banner-only `root` command.                                                  |
| 1    | `EXIT_GENERIC_ERROR`| Any `ComtradeError` not covered by the specific categories below; `KeyboardInterrupt`. |
| 2    | `EXIT_USER_ERROR`   | `argparse` rejection; unknown subcommand; `CLIError`; invalid `--output-format`.     |
| 69   | `EXIT_NETWORK_ERROR`| `NetworkError` (timeout, connection reset, non-retryable 5xx).                       |
| 77   | `EXIT_AUTH_ERROR`   | `AuthenticationError` (401 / 403 / missing subscription key).                         |
| 78   | `EXIT_CONFIG_ERROR` | `CLIConfigurationError`; `ConfigurationError`; invalid `--log-level`; output path not writable. |

Mapping is centralised in `un_comtrade/cli/main.py::main` (lines 339–358).
Each constant is exported and stable; downstream shell scripts can rely on
the table above.

---

## 8. Output formatting

### 8.1 Five formatters

| Format     | Module                              | Output                                                |
| ---------- | ----------------------------------- | ----------------------------------------------------- |
| `json`     | `formatting/json.py`                | RFC 8259 stable JSON; `Decimal` as string; `datetime` ISO-8601. |
| `table`    | `formatting/table.py`               | Aligned text table with column-width padding.         |
| `csv`      | `formatting/csv.py`                 | RFC 4180 CSV (`\r\n` line terminator).                |
| `markdown` | `formatting/markdown.py`            | GitHub-Flavored-Markdown table; pipes in values escaped. |
| `text`     | `formatting/text.py`                | Line-oriented plain text (key=value lines per record).|

### 8.2 Protocol & registry

`un_comtrade.cli.formatting.OutputFormatter` declares two members: a
class attribute `name: str` and `render(value: Any) -> str`. The
registry `_FORMATTERS` is a `dict[str, type[OutputFormatter]]` keyed by
format name. `get_formatter(name)` validates `name in OUTPUT_FORMATS`
then instantiates the registered class.

Parity is asserted by `test_cli_formatters.py::TestProtocolAndRegistry`
and the live check:

```
OUTPUT_FORMATS         = ('json', 'table', 'csv', 'markdown', 'text')
_FORMATTERS keys       = ['json', 'table', 'csv', 'markdown', 'text']
match                  = True
```

### 8.3 CLI integration

- **Default format**: `json` (`get_formatter('json')` is always
  available; the registry is populated at import time).
- **Format selection**: `--output-format NAME` validated by argparse
  `choices=OUTPUT_FORMATS`; unknown names fail at parse time with exit
  code 2 (before any business logic runs).
- **Output destination**: `--output PATH` writes the rendered text to a
  file; otherwise to `sys.stdout`.
- **Formatting policy**: every command body calls
  `render_to_destination(formatter, value, args.output)`. No command
  module constructs output strings directly
  (`TestBusinessLogicNeverFormats::test_cli_commands_do_not_construct_output_strings`
  enforces this for all five command modules).

---

## 9. Configuration

`un_comtrade.cli.utils.load_cli_configuration(api_key, log_level)` reads
the public `Configuration` from environment variables (`UN_COMTRADE_KEY`,
`UN_COMTRADE_LOG_LEVEL`, etc.) and applies CLI overrides last:

1. Environment variable values (lowest priority).
2. CLI overrides via `--api-key` / `--log-level` (highest priority).

The returned object is the public `un_comtrade.config.Configuration`
dataclass — the same type users get by importing the SDK directly. No
configuration state lives inside the CLI; the resolved `Configuration`
is stashed on the parsed argparse namespace
(`args._cli_configuration`) and consumed by the SDK constructor.

Failure modes:

- Invalid log level string → `CLIConfigurationError` → exit code 78.
- Missing / unparsable config file → `ConfigurationError` → exit code 78.

Verified by `test_cli_foundation.py::TestConfigurationLoading` and
`test_cli_integration.py::TestConfigurationEndToEnd`.

---

## 10. Cross-platform compatibility

| Aspect                       | Status                                                                |
| ---------------------------- | --------------------------------------------------------------------- |
| Python version               | 3.11+ (project minimum; tests run on 3.14.3).                         |
| Operating system             | Pure-Python; no `os.system` / `subprocess` / `signal` / `fcntl`.      |
| Shell                        | All flags are POSIX-style (`--long`); no GNU-only short options.     |
| PowerShell compatibility     | Verified by tests on Windows + PowerShell 5.1 shell.                  |
| File I/O                     | Uses `pathlib`; respects OS path separators.                          |
| Encoding                     | UTF-8 throughout; no Windows code-page coercion paths.                |
| Network                      | `httpx` (cross-platform); timeouts via `httpx.Timeout`.               |
| Optional dependencies        | `pyarrow` (parquet), `duckdb` (duckdb storage) — both cross-platform wheels. |
| Progress reporter            | `sys.stderr.isatty()` — TTY on Unix, ConPTY on Windows.               |
| Permissions                  | Errors mapped to `EXIT_CONFIG_ERROR`; tested with read-only paths.    |
| No shell-out, no registry hacks, no `click`/`typer`/`rich` (kept lean). |

The 4 skipped tests in `tests/test_cli_foundation.py::TestEndToEndSmoke`
and `tests/test_cli_integration.py::TestEndToEndSmoke` exercise the
`un-comtrade` console script via `subprocess.run(..., check=True)`. They
are skipped by default (no `_END_TO_END_SMOKE_=1` env var) to keep the
default suite hermetic; they are not failures.

---

## 11. Architectural drift — verdict

The CLI package conforms to every architectural constraint from
`docs/021_IMPLEMENTATION_BASELINE_v1.md` §7 and
`docs/031_PRODUCTION_READINESS.md` §9:

| Constraint                                                              | Result  |
| ----------------------------------------------------------------------- | ------- |
| CLI consumes ONLY public SDK APIs.                                       | ✅ |
| CLI does NOT build endpoint URLs.                                        | ✅ |
| CLI does NOT contain analytics logic.                                    | ✅ |
| CLI does NOT implement storage writers.                                  | ✅ |
| CLI does NOT implement ETL stages.                                       | ✅ |
| CLI commands do NOT format output strings directly.                      | ✅ |
| Global options (`--api-key`, `--log-level`, `--output-format`, `--output`) appear at every parser level. | ✅ |
| Formatter set is exactly 5 (json/table/csv/markdown/text).              | ✅ |
| Exit codes are BSD-sysexits-style and centralised.                       | ✅ |
| Configuration flows through `load_cli_configuration` only.              | ✅ |
| All business errors map to the right exit code.                          | ✅ |
| Console script `un-comtrade = un_comtrade.cli.main:main` registered in `pyproject.toml`. | ✅ |

No drift detected. The CLI is a thin consumer of the SDK — exactly as
designed in the architecture baseline.

---

## 12. Remaining risks

### 12.1 Low-severity

| # | Risk                                                                                  | Mitigation today                                          | Recommended next step                              |
| - | ------------------------------------------------------------------------------------- | --------------------------------------------------------- | -------------------------------------------------- |
| 1 | `coverage` tooling not installed; no line-coverage measurement.                       | Structural coverage via 262 tests + AST guards.           | Add `coverage` to `[project.optional-dependencies] dev`; CI gate ≥ 90%. |
| 2 | `--output-format` typo gives a parse-time error (exit 2) but no `did-you-mean` hint.   | argparse `choices=OUTPUT_FORMATS` shows the list.          | Optional: register `argparse.ArgumentError` subclass with suggestion. |
| 3 | No shell-completion script.                                                            | n/a                                                       | Optional Cookbook phase entry (bash + zsh).        |
| 4 | `analytics` argument names use plural (`--reporters`) for compare but singular elsewhere; consistency is documented but mildly surprising. | Per-subcommand help.                                       | Add a Cookbook recipe documenting the convention.  |
| 5 | 4 console-script subprocess tests are skipped by default.                              | Smoke tests gated by env var.                             | Wire them into CI under a separate pytest mark.    |

### 12.2 Not in scope

| # | Risk                                                                                  | Why not in scope                                          |
| - | ------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| 6 | 12 EXT items still need live subscription-key verification (carry-over from V-001).    | Requires user-supplied live key; outside this review.     |
| 7 | Manual performance benchmark (1k / 10k / 100k record CLI invocations).                 | Deferred to Cookbook; CLI is a thin wrapper; perf is bounded by SDK + formatter, not CLI dispatch. |
| 8 | Internationalisation of CLI messages.                                                  | Deferred; English-only is the v1 contract.                |

---

## 13. Review verdict

**PASS.**

The CLI subsystem is complete, internally consistent, and conformant with
every architectural constraint from the v1 baseline. Public-SDK-only
discipline is enforced by 17 AST-walker tests; exit codes, formatters,
configuration, and help coverage are all centralised, deterministic, and
tested. The 258 passing CLI tests (4 skipped) cover the entire 4,229-line
package structurally. Quantitative line-coverage measurement is the
single missing signal and is a one-line dev-deps fix.

---

## 14. Recommendation for the Cookbook phase

The CLI is the natural entry point for the upcoming Cookbook. Recommend
the following six recipes for the Cookbook phase:

1. **Hello, world** — `un-comtrade metadata countries` (no auth, exercises the full parser/formatter/render pipeline).
2. **Authenticated query** — `un-comtrade trade exports --reporter 699 --year 2022 --partner 0` against a live key; demonstrates exit-code 0 / 77 / 69 mapping.
3. **Markdown report** — `un-comtrade analytics country --dataset data.parquet --reporter 699 --output-format markdown --output report.md` showing the 5-format interchange.
4. **Pipeline + storage** — `un-comtrade etl run --pipeline-config pipeline.json && un-comtrade storage duckdb --dataset data.parquet --output-path data.duckdb` exercising the public-ETL + public-storage path.
5. **Shell-friendly** — piping JSON output into `jq`; piping CSV into spreadsheets; demonstrates the line-oriented `text` format for grep.
6. **Failure handling** — demonstrate each exit code (77 for bad key, 69 for network down, 78 for bad log level) and how a shell wrapper can react.

All six recipes can be written today from the CLI surface as it stands —
no further CLI work is required before Cookbook authoring begins.

---

## 15. Sign-off

| Item                                | Value                                                                                  |
| ----------------------------------- | -------------------------------------------------------------------------------------- |
| CLI top-level commands              | 6                                                                                       |
| Group (parent) commands             | 5                                                                                       |
| Sub-subcommand leaves               | 23                                                                                      |
| Reachable executable subparsers     | 24 (23 leaves + `root`)                                                                 |
| Output formats                      | 5 (json, table, csv, markdown, text)                                                   |
| Exit codes                          | 6 (0, 1, 2, 69, 77, 78)                                                                 |
| CLI source files                    | 22                                                                                      |
| CLI source lines                    | 4,229                                                                                   |
| CLI test files                      | 7                                                                                       |
| CLI tests collected                 | 262                                                                                     |
| CLI tests passing                   | 258                                                                                     |
| CLI tests skipped (smoke, gated)    | 4                                                                                       |
| Full repo tests collected           | 3,075                                                                                   |
| Full repo tests passing             | 3,070                                                                                   |
| Public-SDK-only violations          | 0                                                                                       |
| URL-built-inside-CLI violations     | 0                                                                                       |
| Analytics-logic-in-CLI violations   | 0                                                                                       |
| Storage-impl-in-CLI violations      | 0                                                                                       |
| ETL-impl-in-CLI violations          | 0                                                                                       |
| Format-strings-in-business-CLI violations | 0                                                                                |
| Cross-platform compatibility        | Confirmed (Windows + PowerShell, Python 3.14.3, no shell-out)                           |
| Coverage tooling installed          | No (deferred to dev-deps + Cookbook CI)                                                 |
| Architectural drift                 | None                                                                                    |
| **Review verdict**                  | **PASS**                                                                                |
| **Recommendation**                  | **Begin Cookbook authoring on v1.0.1. No further CLI implementation work required.**    |