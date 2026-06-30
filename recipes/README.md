```
Document ID
034

Title
Cookbook — Architecture and Conventions

Version
0.1.0

Status
DRAFT

Created
2026-06-29T20:30:00Z

Last Updated
2026-06-29T20:30:00Z

Author
Mavis (CB-001)

Project
UN Comtrade Python SDK

Dependencies
003_ARCHITECTURE.md,
007_SDK_SPECIFICATION.md,
008_METADATA_LAYER_SPEC.md,
009_TRADE_LAYER_SPEC.md,
010_INFRASTRUCTURE_SPEC.md,
011_ETL_SPECIFICATION.md,
012_STORAGE_SPECIFICATION.md,
025_ANALYTICS_REVIEW_REPORT.md,
032_CLI_REVIEW.md,
033_CLI_CONTRACT_VERIFICATION.md

Supersedes
None
```

---

# Cookbook

The Cookbook is the **consumer-facing example set** for the
`un-comtrade-sdk`. It complements the specification documents in
`docs/` (the architectural contract) and the test suite in
`tests/` (the behavioural contract) by showing the SDK in
realistic, end-to-end uses.

A **recipe** is a single, self-contained, runnable example that
demonstrates one specific capability of the SDK in a way that a
consumer can copy, modify, and embed.

This document defines:

- The directory layout of `recipes/`.
- The naming convention for recipes.
- The required header every recipe MUST carry.
- The conventions for inputs, outputs, error handling,
  API-key usage, and runtime estimation.
- The relationship between the Cookbook and the rest of
  the documentation set.

No recipe bodies are produced by this document. Recipe
specifications land in subsequent `CB-NNN` tasks.

---

# 1. Scope and Purpose

## 1.1 What the Cookbook is

The Cookbook is the **practical companion** to the SDK. Each
recipe is a small, runnable program that demonstrates one
specific capability of the SDK. The Cookbook is the first
place a consumer should look after reading the README.

The Cookbook is the canonical demonstration of the
**documented public surface**. A consumer who can run every
recipe in the Cookbook has a working tour of the SDK.

The Cookbook is also a **regression artefact**. Recipes that
exercise a public method double as smoke tests; if a recipe
breaks, the SDK has regressed.

## 1.2 What the Cookbook is not

The Cookbook is not:

- A replacement for the specification documents in `docs/`.
  Recipes illustrate behaviour; they do not define it.
- A replacement for the test suite in `tests/`. The test
  suite enforces the contract; recipes demonstrate the
  contract. A recipe is allowed to skip edge cases that the
  test suite covers.
- A benchmark. Recipes are not used to measure performance;
  performance is the responsibility of
  `docs/030_PERFORMANCE_BASELINE.md`.
- A tutorial. The Cookbook is **task-oriented** (one recipe
  per task), not **narrative** (no sequential walk-through).
  Tutorials are out of scope.

## 1.3 Relationship to the documentation set

The Cookbook does not duplicate the specification documents.
A recipe that needs to explain *why* the SDK behaves a certain
way links to the relevant `docs/00N_*.md` page rather than
re-explain the behaviour.

The traceability chain is:

```
docs/  (architectural contract)
   ↓
recipes/  (consumer-facing examples)
   ↓
tests/  (behavioural contract)
```

A change to the public SDK surface MUST update the
specification document first, then the relevant recipe(s),
then the relevant test(s). Out-of-order changes are
rejected at review.

---

# 2. Directory Layout

The Cookbook lives at the repository root under `recipes/`.

```
recipes/
├── README.md             # this document — cookbook contract
├── _TEMPLATE.md          # recipe-format specification
├── _TEMPLATE.py          # importable recipe skeleton
├── metadata/             # recipes that exercise client.metadata
├── trade/                # recipes that exercise client.trade
├── analytics/            # recipes that exercise client.analytics
├── etl/                  # recipes that exercise client.etl
├── storage/              # recipes that exercise client.storage
├── cli/                  # recipes that exercise the CLI surface
└── end_to_end/           # recipes that compose ≥ 2 services
```

## 2.1 Category purpose

| Category      | Primary SDK surface                              | Common shape                                |
| ------------- | ------------------------------------------------ | ------------------------------------------- |
| `metadata/`   | `client.metadata` (M01–M18)                      | one catalogue fetch + optional persistence  |
| `trade/`      | `client.trade` (T01–T13)                         | one trade query + one storage write         |
| `analytics/`  | `client.analytics` (engine + helpers)            | one `AnalyticsEngine` run + tabular output  |
| `etl/`        | `client.etl` (pipeline factory)                  | one pipeline build + one pipeline run       |
| `storage/`    | `client.storage` (5 backends)                    | one read + one write per backend            |
| `cli/`        | `un-comtrade` command-line entry point           | one shell script + one expected output      |
| `end_to_end/` | ≥ 2 of the above                                 | one script that chains ≥ 2 stages           |

The category a recipe belongs to is the **dominant** SDK
surface. A recipe that primarily writes to Parquet but also
runs an `AnalyticsEngine` belongs in `analytics/`, not in
`storage/`.

## 2.2 Per-category content

Every category directory contains exactly one `README.md` and
zero or more recipe files. The `README.md`:

- Restates the category's scope and the SDK services it
  exercises.
- Lists the planned recipe roster (recipe IDs and titles).
- Records the category's API-key policy and runtime band.
- Cross-references the relevant `docs/` pages.

A category that has no recipes yet is allowed to ship with
its `README.md` only. A category is **populated** when it
contains at least one recipe file.

## 2.3 Files that MUST NOT live in `recipes/`

The Cookbook directory is reserved for recipes and their
index documents. The following are explicitly out of scope
and MUST live elsewhere:

- **Hand-written data fixtures** (large JSON / CSV / Parquet
  fixtures) — `tests/fixtures/`.
- **Test code** — `tests/`.
- **Long-form tutorials** — `docs/` (future
  `docs/0NN_TUTORIALS.md`).
- **Performance benchmarks** — `tools/` or
  `docs/030_PERFORMANCE_BASELINE.md`.
- **Generated API reference** — `docs/` (auto-generated
  from docstrings; see ADR-0017).

A pull request that introduces one of the above under
`recipes/` is rejected at review.

---

# 3. Naming Conventions

## 3.1 Recipe file names

Every recipe is a Python file. The naming format is:

```
RECIPE_<NNN>_<snake_case_slug>.py
```

Where:

- `<NNN>` is a **three-digit** zero-padded numeric ID.
  The ID is **globally unique** across the entire cookbook,
  not unique per category.
- `<snake_case_slug>` is a short, descriptive name in
  `snake_case`. The slug is **lower-case**, uses ASCII
  letters, digits, and underscores only, and is between
  three and forty characters long.
- The `.py` extension is mandatory. Markdown-only recipes
  are not allowed; the executable form is the contract.

Examples:

- `RECIPE_001_list_all_countries.py`
- `RECIPE_002_fetch_india_exports_2022.py`
- `RECIPE_007_top_export_partners_duckdb.py`
- `RECIPE_013_full_yearly_pipeline_to_parquet.py`

## 3.2 Recipe IDs

Recipe IDs are formatted `RECIPE-NNN`. The dash, not the
underscore, is the public-facing separator in documentation,
in changelogs, and in cross-references. The Python file name
uses an underscore instead because Python identifiers cannot
contain a dash.

A recipe ID is **assigned at the moment the recipe is
committed**. IDs are monotonic: the next recipe ID is the
largest in-use ID plus one. IDs are never reused; a recipe
that is deprecated retains its ID and gains a `DEPRECATED`
frontmatter field.

## 3.3 Directory names

Directory names are **lower-case** ASCII with underscores.
No hyphens, no CamelCase, no abbreviations beyond what is
already in the SDK (`etl`, `cli`). The current set is fixed:

```
metadata, trade, analytics, etl, storage, cli, end_to_end
```

Adding a new category is a **breaking change** to the
Cookbook contract and requires a recorded decision in
`docs/DECISIONS.md`.

## 3.4 Reserved file names

The following file names are reserved and MUST NOT be used
for recipes:

- `README.md` — category index, exactly one per directory.
- `_TEMPLATE.md` — recipe format specification (this directory).
- `_TEMPLATE.py` — importable recipe skeleton.
- Anything starting with `_` (double-underscore not required;
  a single leading underscore is enough to mark a private
  file in the Cookbook, mirroring the Python convention).

---

# 4. Recipe Header

Every recipe is a Python module whose **first** statement is a
module-level docstring. The docstring is structured and acts
as the recipe's metadata header. The full schema is defined
in `recipes/_TEMPLATE.md`; the fields are summarised here.

## 4.1 Required frontmatter fields

Every recipe header MUST carry the following fields. A
recipe that omits any of them is rejected at review.

| Field              | Type        | Meaning                                                   |
| ------------------ | ----------- | --------------------------------------------------------- |
| `recipe_id`        | string      | `RECIPE-NNN` (matches the file name's `<NNN>`)            |
| `title`            | string      | short human-readable title (≤ 80 chars)                   |
| `category`         | enum        | one of the seven cookbook categories                      |
| `difficulty`       | enum        | `beginner` \| `intermediate` \| `advanced`                |
| `sdk_version`      | string      | `>=X.Y.Z` semver constraint (lowest tested version)      |
| `requires_api_key` | enum        | `yes` \| `no` \| `optional`                               |
| `estimated_runtime`| enum        | `<1s` \| `<10s` \| `<1min` \| `1-10min` \| `10-60min` \| `>1h` |
| `inputs`           | list        | required and optional input parameters                    |
| `outputs`          | list        | artefacts the recipe produces                             |
| `related_docs`     | list        | absolute or repo-relative paths to `docs/*.md` pages      |
| `related_recipes`  | list        | `RECIPE-NNN` references to other recipes                  |
| `tags`             | list        | free-form lowercase search tags                           |

## 4.2 Optional frontmatter fields

A recipe MAY carry the following fields when relevant.

| Field           | Type   | Meaning                                                    |
| --------------- | ------ | ---------------------------------------------------------- |
| `author`        | string | original author of the recipe                              |
| `created`       | string | ISO-8601 UTC timestamp                                     |
| `last_updated`  | string | ISO-8601 UTC timestamp                                     |
| `deprecated`    | string | deprecation message; presence marks the recipe as DEPRECATED |
| `superseded_by` | string | `RECIPE-NNN` of the replacement recipe                     |

## 4.3 Frontmatter format

The frontmatter is encoded as **structured Python** inside the
module docstring, using `key: value` lines and indented
sub-lists. The first non-blank line of the docstring is
`---`; the frontmatter terminates at the next `---`. The
remainder of the docstring is the long-form description.

The exact grammar is specified in `recipes/_TEMPLATE.md`. A
recipe is considered **non-conformant** when its frontmatter
cannot be parsed by the cookbook linter (future tool).

## 4.4 Why a Python docstring (not a `.md` companion)

The recipe header is embedded in the `.py` file itself for
three reasons:

- A single file is the runnable artefact. The consumer
  reads and runs the same file.
- A single file travels cleanly through the package
  distribution (a recipe bundled with the wheel carries
  its documentation with it).
- A single file is reviewable as a single diff.

A future `cookbook build` command MAY emit a `.md` companion
from the docstring for the static documentation site. That
is an output of the build, not a hand-maintained source
file.

---

# 5. Inputs

## 5.1 Categories of input

Every recipe accepts zero or more inputs. Inputs are
categorised as follows.

- **API key.** The `UN_COMTRADE_KEY` environment variable is
  the only supported source. Recipes MUST NOT hard-code an
  API key; recipes MUST NOT read a key from a file. A recipe
  whose frontmatter declares `requires_api_key: no` MUST
  work with no key configured.
- **Output directory.** A recipe that writes files accepts
  an `--output` argument (default `./output`). The recipe
  MUST create the directory if it does not exist.
- **Domain parameters.** Country codes, reporter codes,
  partner codes, commodity codes, period codes, and similar
  UN Comtrade identifiers are passed as CLI arguments or
  module-level constants at the top of the recipe body.
- **Environment configuration.** Tunables (cache directory,
  log level, request timeout) are read from the standard
  SDK configuration env vars (`UN_COMTRADE_CACHE_DIR`,
  `UN_COMTRADE_LOG_LEVEL`, `UN_COMTRADE_TIMEOUT_SECONDS`).
  A recipe MUST NOT introduce a new env var without a
  corresponding entry in
  `010_INFRASTRUCTURE_SPEC.md` §3.

## 5.2 Argument conventions

Recipes expose a `parse_args()` helper that returns a
typed namespace. The helper:

- Reads from `sys.argv[1:]`.
- Provides a `--output DIR` flag with default `./output`.
- Provides a `--verbose` / `-v` flag that sets the SDK
  logger level to `DEBUG`.
- Parses domain parameters (e.g. `--reporter 699 --year
  2022`) into typed values.
- Exits with code 0 on `--help`.

A recipe that takes no arguments MAY omit `parse_args()`,
but the resulting script MUST still be importable as a
module (no top-level side effects).

## 5.3 Sample data and fixtures

A recipe that needs sample data fetches it from the upstream
API or generates it at runtime. Hand-curated JSON fixtures
are out of scope for the Cookbook (see §2.3). A recipe that
cannot run without fixtures is not yet a recipe and is not
accepted.

---

# 6. Outputs

## 6.1 File outputs

A recipe that writes a file:

- Writes into the directory passed to `--output` (default
  `./output/`).
- Names the file with the pattern
  `<recipe_id>_<UTC-timestamp>.<ext>` where the timestamp
  is `YYYYMMDDTHHMMSSZ`. Example:
  `RECIPE_002_20260629T103000Z.parquet`.
- Writes a JSON sidecar
  `<recipe_id>_<UTC-timestamp>.meta.json` containing the
  recipe's `recipe_id`, the run timestamp, the SDK
  version, and a SHA-256 digest of the data file.
- Writes to a **temporary file** in the same directory and
  renames atomically. A recipe that writes partial files
  is rejected at review.

A recipe that produces tabular output uses the SDK's
`storage.parquet` or `storage.csv` writer rather than
`pandas.to_csv` or hand-rolled JSON encoding.

## 6.2 Stdout

A recipe prints a **single-line summary** to stdout at the
end of a successful run. The line is `key=value` pairs
separated by spaces, e.g.:

```
recipe=RECIPE_002 records=18342 primary_value_usd=1234567890.00 output=output/RECIPE_002_20260629T103000Z.parquet
```

The line is machine-parseable by the cookbook CI smoke
tests. Recipes that print progress to stdout do so on
stderr only (see §6.3).

## 6.3 Stderr and logging

A recipe configures the SDK logger with the level passed to
`--verbose` (default `WARNING`). The recipe does not
configure `logging.basicConfig`; it uses
`logging.getLogger("un_comtrade")` to obtain the SDK-named
logger. All progress messages, retries, and warnings go
through this logger.

A recipe that needs to print human-readable tables prints
to **stdout** (the table IS the artefact). A recipe that
needs to print progress prints to **stderr** (progress is
not an artefact).

## 6.4 Exit codes

A recipe exits with:

- `0` — success.
- `1` — generic failure (default).
- `2` — invalid arguments (raised by `parse_args()`).
- `3` — SDK `ValidationError`.
- `4` — SDK `AuthenticationError` or `AuthorizationError`.
- `5` — SDK `RateLimitError` (after retries exhausted).
- `6` — SDK `NetworkError` / `TimeoutError` /
  `RetryError` (after retries exhausted).
- `7` — SDK `ServerError` (after retries exhausted).
- `8` — recipe-specific business-rule failure (e.g. empty
  result when the recipe requires a non-empty result).

The exit-code map is normative; a recipe that uses a
different map is rejected at review. The full table is
reproduced in `recipes/cli/README.md` (the CLI recipes
documentation, which is also the source of truth for the
Cookbook's exit codes).

---

# 7. Error Handling

## 7.1 The exception hierarchy

The SDK raises exceptions from the hierarchy defined in
`un_comtrade.exceptions` (see
`007_SDK_SPECIFICATION.md` §10):

```
ComtradeError                     ← base
├── ConfigurationError
├── AuthenticationError
│   └── AuthorizationError
├── ValidationError
├── NetworkError
│   ├── TimeoutError
│   ├── RetryError
│   └── RateLimitError
├── SerializationError
├── APIError
│   └── ServerError
└── UnknownError
```

Recipes catch only what they can handle.

## 7.2 What recipes MUST catch

- `ConfigurationError` — raised before the first network
  call. The recipe SHOULD print a human-readable hint
  (`set UN_COMTRADE_KEY=...`) and exit with code `3`.
- `AuthenticationError` / `AuthorizationError` — the key
  is missing or rejected. The recipe SHOULD print a hint
  and exit with code `4`.
- `ValidationError` — the input is invalid. The recipe
  SHOULD print the offending parameter and exit with
  code `3`.
- `RateLimitError` — raised after the SDK has honoured
  `Retry-After` and exhausted the retry budget. The
  recipe SHOULD print the retry budget and exit with
  code `5`.
- `NetworkError` (and its subclasses) — the network is
  down. The recipe SHOULD print a hint and exit with
  code `6`.
- `ServerError` — upstream is unhealthy. The recipe
  SHOULD print the status code and exit with code `7`.

The recipe's `main()` function wraps the entire body in
`try` / `except ComtradeError as exc` and maps the
exception to the exit code in §6.4. The `except` block
prints `recipe=<id> error_class=<ClassName>
error_message=<str(exc)>` to stderr and exits.

## 7.3 What recipes MUST NOT catch

A recipe MUST NOT catch `Exception` or `BaseException`
broadly. A recipe MUST NOT silently swallow an exception
(an empty `except` block is rejected at review). A recipe
MUST NOT re-raise a caught `ComtradeError` after the
exit-code mapping; the recipe's job is to translate the
error into a machine-readable exit code, not to retry.

A recipe that needs to recover from a transient error
(partial download, intermittent 503) lets the SDK's
built-in retry handle it. The recipe does not implement
its own retry loop.

## 7.4 Timeouts and cancellation

A recipe that runs longer than 60 seconds prints a
progress line to stderr every 10 seconds. The progress
line format is:

```
recipe=<id> status=running elapsed=<seconds>s
```

The recipe does not implement its own timeout. The
SDK-level timeout (`UN_COMTRADE_TIMEOUT_SECONDS`) is the
single source of truth for request-level timeouts.

## 7.5 Reproducibility

A failed run MUST be reproducible. The recipe prints
the **command line** that was used to invoke it (e.g. via
`logging` at `INFO` level) so a consumer can re-run with
the same arguments. A recipe that uses randomness
samples the seed from `UN_COMTRADE_RECIPE_SEED` (default
`42`); a recipe that does not use randomness omits this
behaviour.

---

# 8. API Key Policy

## 8.1 Per-recipe flag

The frontmatter field `requires_api_key` records whether
the recipe needs a configured API key.

| Value      | Meaning                                                       |
| ---------- | ------------------------------------------------------------- |
| `yes`      | the recipe calls a `client.trade.*` method that requires a key |
| `no`       | the recipe uses only metadata or storage backends             |
| `optional` | the recipe works without a key, but uses a key when present (e.g. for higher rate limits) |

## 8.2 Per-category default

The following categories default to `requires_api_key: yes`:

- `trade/`
- `etl/`
- `end_to_end/` (when it composes trade)

The following categories default to `requires_api_key: no`:

- `metadata/` (metadata is publicly cached, no key needed)
- `analytics/` (operates on a `CanonicalDataset`, no network)
- `storage/` (operates on local files, no network)
- `cli/` (depends on the subcommand; declared per recipe)
- `end_to_end/` (when it does not compose trade)

A category's default is the rule; a recipe that deviates
records `requires_api_key` explicitly in its frontmatter.

## 8.3 Key handling

A recipe reads the key from the environment:

```python
import os
api_key = os.environ.get("UN_COMTRADE_KEY")
```

A recipe MUST NOT:

- Hard-code a key.
- Read a key from a file.
- Echo a key to stdout or stderr (even partially).
- Write a key to a log file.
- Pass a key to a third-party HTTP endpoint.

A recipe that detects a key is configured but the SDK
rejected it exits with code `4` per §7.2.

## 8.4 Local development keys

A consumer iterating locally sets the key in their shell:

```bash
export UN_COMTRADE_KEY="<your-key>"
```

The `un-comtrade` CLI also accepts the key on the command
line (`--api-key`), but recipes (which are library code)
do not. Recipes treat the CLI as a thin wrapper and
delegate argument handling to it.

---

# 9. Runtime Estimation

## 9.1 The six-band scale

The `estimated_runtime` frontmatter field uses a six-band
scale that maps to the upper-bound wall-clock time of a
single invocation of the recipe on a modern laptop with a
warm cache.

| Band        | Upper bound | Typical examples                                      |
| ----------- | ----------- | ----------------------------------------------------- |
| `<1s`       | 1 second    | metadata fetch with warm cache, in-memory transform   |
| `<10s`      | 10 seconds  | one trade query (small dataset), one storage write    |
| `<1min`     | 1 minute    | trade query for a single country + year               |
| `1-10min`   | 10 minutes  | trade query for many reporters, Parquet build         |
| `10-60min`  | 1 hour      | full-year dataset for one reporter, DuckDB ingest     |
| `>1h`       | unbounded   | multi-reporter / multi-decade pipelines               |

The band is the **expected upper bound**, not the typical
value. A recipe that is normally `<10s` but can spike to
`1-10min` under adversarial conditions is recorded as
`1-10min`.

## 9.2 What drives the band

- **Network latency.** The dominant cost for any recipe
  that calls the upstream API.
- **Cache state.** A cold cache adds one or two seconds
  per catalogue fetch.
- **Dataset size.** A recipe that fetches 100k records is
  in a different band from one that fetches 100 records.
- **Storage backend.** Parquet and DuckDB writes are
  fast; CSV and JSON writes are slower. The band
  reflects the typical backend.

A recipe that runs longer than its declared band is a
**performance regression** and SHOULD be reported in the
issue tracker.

## 9.3 Per-category typical band

| Category      | Typical band  | Notes                                   |
| ------------- | ------------- | --------------------------------------- |
| `metadata/`   | `<1s`         | warm cache; `<10s` cold                 |
| `trade/`      | `<1min`       | one reporter / one year                 |
| `analytics/`  | `<10s`        | in-memory; depends on dataset size      |
| `etl/`        | `1-10min`     | depends on staging                      |
| `storage/`    | `<10s`        | local I/O                               |
| `cli/`        | inherits      | inherits from the underlying command    |
| `end_to_end/` | `1-10min`     | composes ≥ 2 stages                     |

These are the **expected** bands; per-recipe bands are
declared in the frontmatter and may differ.

---

# 10. Related Documentation Pages

The Cookbook is the consumer's on-ramp; the `docs/` tree is
the source of truth. A recipe that needs to explain a
behaviour links to the relevant page. The pages most often
referenced are listed below.

| Page                                       | Recipes that link to it                              |
| ------------------------------------------ | ----------------------------------------------------- |
| `docs/003_ARCHITECTURE.md`                 | every category (general orientation)                  |
| `docs/007_SDK_SPECIFICATION.md`            | every recipe (the public surface)                     |
| `docs/008_METADATA_LAYER_SPEC.md`          | `metadata/`, `cli/` (metadata commands)              |
| `docs/009_TRADE_LAYER_SPEC.md`             | `trade/`, `end_to_end/`                               |
| `docs/010_INFRASTRUCTURE_SPEC.md`          | every recipe that uses the SDK logger or transport    |
| `docs/011_ETL_SPECIFICATION.md`            | `etl/`, `end_to_end/`                                 |
| `docs/012_STORAGE_SPECIFICATION.md`        | `storage/`, `end_to_end/`                             |
| `docs/025_ANALYTICS_REVIEW_REPORT.md`      | `analytics/`                                          |
| `docs/032_CLI_REVIEW.md`                   | `cli/`                                                |
| `docs/033_CLI_CONTRACT_VERIFICATION.md`    | `cli/`                                                |
| `docs/030_PERFORMANCE_BASELINE.md`         | any recipe whose declared band is `1-10min` or higher |

A recipe that cites a page uses a **repo-relative** path
(`docs/007_SDK_SPECIFICATION.md`), not an absolute path
or a URL. The cookbook build is responsible for resolving
repo-relative paths to canonical URLs at publication time.

---

# 11. How to Add a New Recipe

A new recipe is added by:

1. Choosing the **next free** `RECIPE-NNN` ID.
2. Choosing the **category** that matches the dominant
   SDK service.
3. Copying `recipes/_TEMPLATE.py` to the chosen category
   directory and renaming it.
4. Filling the frontmatter (see `recipes/_TEMPLATE.md`).
5. Implementing the body in the standard sections
   (imports, configuration, build, run, output, cleanup,
   error handling).
6. Adding the recipe to the **per-category `README.md`**
   roster.
7. Running the recipe locally with a configured key to
   confirm it produces the declared outputs.
8. Submitting a pull request that links the recipe's
   `RECIPE-NNN` to the relevant `docs/` page in the
   pull-request description.

A recipe is **accepted** when:

- The frontmatter passes the cookbook linter.
- The body compiles, runs, and produces the declared
  outputs.
- The exit codes match the map in §6.4.
- The README of the parent category is updated.
- The pull request links the relevant `docs/` page.

A recipe is **rejected** when:

- The frontmatter is missing a required field.
- The body contains a hard-coded API key.
- The body catches `Exception` or `BaseException` broadly.
- The body writes a partial file (non-atomic write).
- The body prints an API key to stdout or stderr.
- The body introduces a new env var without a
  `010_INFRASTRUCTURE_SPEC.md` entry.
- The body does not declare its outputs in frontmatter.

---

# 12. Cookbook Lifecycle

The Cookbook is itself versioned. The lifecycle of a recipe
is:

```
PROPOSED   →   DRAFT   →   STABLE   →   DEPRECATED
```

- **PROPOSED** — the recipe is filed as an issue or listed
  in a category `README.md` without a corresponding file.
- **DRAFT** — the recipe file exists but has not been
  reviewed or is known to be flaky.
- **STABLE** — the recipe file has been reviewed and runs
  green in CI.
- **DEPRECATED** — the recipe is superseded. The file
  remains in the cookbook with a `deprecated` field in
  its frontmatter; the recipe's body exits with a
  deprecation warning at run time.

The lifecycle state is **not** a frontmatter field. It is
recorded in the category `README.md` and in the pull
request that introduces the recipe. Recipes that are
`STABLE` participate in the cookbook CI smoke run.

---

# 13. Open Questions

The following questions are open at the time of writing.
Each is tracked as a `CLAR-NNN` entry in
`docs/PROJECT_CLARIFICATION_REGISTER.md`.

- **OQ-CB-001.** Should the Cookbook ship a `pyproject`
  extra (`pip install un-comtrade-sdk[cookbook]`) that
  pulls in the optional dependencies recipes use
  (e.g. `duckdb`, `pyarrow`, `matplotlib`)? Currently
  recipes assume the consumer installs them; the extra
  would make the Cookbook a one-step setup.
- **OQ-CB-002.** Should a recipe be allowed to call
  multiple SDK services, or is single-service a hard
  rule (compositions belong in `end_to_end/` only)?
  Currently the rule is "dominant service wins" per
  §2.1; an explicit decision could lock this in.
- **OQ-CB-003.** Should recipes be runnable as
  `python -m un_comtrade.recipes.<id>` rather than as
  standalone scripts? The current design favours
  standalone scripts, but module-based invocation
  aligns better with the package distribution.

These questions are not blocking the architecture; the
architecture is valid under all three answers.

---

# 14. Task Family

The Cookbook is delivered under the `CB-NNN` task family
(parallel to `T-NNN` for implementation tasks). The first
task in the family is `CB-001` — this document. Subsequent
tasks add recipes one (or a small batch) at a time.

| Task ID   | Title                                                | Status   |
| --------- | ---------------------------------------------------- | -------- |
| CB-001    | Cookbook Architecture and Conventions                | DRAFT    |
| CB-002    | Metadata recipes (5 shipped)                         | STABLE   |
| CB-003    | Trade recipes (5 shipped)                            | STABLE   |
| CB-004    | Analytics recipes (5 shipped)                        | STABLE   |
| CB-005    | Storage + ETL recipes (6 shipped)                    | STABLE   |
| CB-006    | CLI recipes (6 shipped)                              | STABLE   |
| CB-007    | End-to-end workflows (2 shipped)                     | STABLE   |
| CB-008    | Recipe verification (regression suite)               | STABLE   |

The task family is recorded in
`docs/IMPLEMENTATION_BACKLOG.md` once a recipe is filed.

---

# 15. Verification

CB-008 introduces `tests/test_recipes_verification.py`,
a **regression suite** that enforces four invariants
on every shipped recipe. When a new recipe is added,
the verification layer automatically picks it up;
when a recipe drifts, the suite flags it.

## 15.1 The four rules

| Rule | Test class                                  | What it enforces                                                                 |
| ---- | ------------------------------------------- | -------------------------------------------------------------------------------- |
| 1    | `TestRecipeExecutes`                        | Every recipe has at least one `*_demo(...)` seam — the testable surface.        |
| 2    | `TestRecipeImports`                         | Every recipe's AST-imports only **public** SDK modules (no underscore-prefix).    |
| 3    | `TestRecipeArgparseValid`                   | Every recipe's `main()` parses argv; every documented CLI flag exists in parser. |
| 4    | `TestRecipeInternalsForbidden`              | No recipe imports `un_comtrade.storage._base` or `tests.*` helpers.             |

The suite uses `pytest.mark.parametrize` over a
**discovered recipe roster** (`RECIPES = _discover_recipes()`),
so adding a new recipe file automatically produces
new test ids without any test-file edits.

## 15.2 How a recipe passes

A passing recipe must:

1. Have a frontmatter `recipe_id:` field.
2. Have at least one `*_demo(...)` callable.
3. Import only `un_comtrade.<public_module>`.
4. If it has an argparse parser, expose every
   flag documented in its frontmatter `inputs:`
   block.
5. Not reach into `un_comtrade.storage._base` or
   `tests.*`.

## 15.3 Running the verification suite

```bash
$ pytest tests/test_recipes_verification.py -v
```

Expected output: ~200 tests pass, ~30 skipped
(recipes without argparse parsers skip the
parser-shape tests; recipes whose frontmatter
has no CLI flags skip the flag-consistency test).

The verification suite is **fast** (~1s for 230 tests).
It runs as part of the standard `pytest tests/` CI
job; a failing test indicates a recipe drift that
must be fixed before the next release.

---

# 16. Summary

The Cookbook is a **structured example set**, not a
free-form scratch pad. Every recipe carries a structured
header, declares its inputs and outputs, follows the SDK
error hierarchy, and lives in a category directory whose
purpose maps to a documented SDK service. The naming,
frontmatter, error-handling, and API-key conventions
above are normative; a recipe that violates them is
rejected at review.

The next step in the Cookbook plan is to file the first
recipe under `CB-002` (or whichever task ID is assigned).
