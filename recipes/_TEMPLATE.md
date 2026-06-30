# Recipe Format Specification

This document is the **canonical grammar** for a recipe file.
The top-level `recipes/README.md` describes the cookbook at
large; this document describes what one recipe file must
look like.

The grammar is normative. A recipe that does not conform is
rejected at review.

---

# 1. File Layout

A recipe is a single Python file with the following layout:

```
1.  Module docstring (the recipe header).
2.  Standard library imports.
3.  Third-party imports.
4.  SDK imports.
5.  Module-level constants (recipe tunables).
6.  parse_args() — argparse helper.
7.  main() — the body.
8.  if __name__ == "__main__": main()
```

The recipe body is split into these named **sections** (see
§5). Every section appears in the order listed, and every
section is preceded by a one-line comment that names it
(e.g. `# ---- build ----`). The cookbook linter checks the
section order.

The file MUST be importable as a Python module. A recipe
that performs side effects at import time (network calls,
filesystem writes) is rejected.

---

# 2. Module Docstring

The first statement in the file is a module-level docstring.
The docstring contains:

- The **frontmatter** (structured metadata, see §3).
- A blank line.
- A **long-form description** of what the recipe does.

```
"""
---
<frontmatter>
---

<long-form description, ≤ 30 lines>
"""
```

The frontmatter is encoded in `key: value` lines. The
opening `---` MUST be the first non-blank line of the
docstring. The closing `---` MUST be on its own line.
The long-form description follows the closing `---` and
runs until the closing `"""`.

---

# 3. Frontmatter

## 3.1 Field table

| Field              | Type    | Required | Format / constraint                                      |
| ------------------ | ------- | -------- | -------------------------------------------------------- |
| `recipe_id`        | string  | yes      | `RECIPE-NNN` where `NNN` is the file's numeric ID        |
| `title`            | string  | yes      | ≤ 80 characters, no trailing colon                       |
| `category`         | enum    | yes      | one of the seven cookbook categories                     |
| `difficulty`       | enum    | yes      | `beginner` \| `intermediate` \| `advanced`               |
| `sdk_version`      | string  | yes      | `>=X.Y.Z` semver constraint                              |
| `requires_api_key` | enum    | yes      | `yes` \| `no` \| `optional`                              |
| `estimated_runtime`| enum    | yes      | `<1s` \| `<10s` \| `<1min` \| `1-10min` \| `10-60min` \| `>1h` |
| `inputs`           | block   | yes      | see §3.2                                                 |
| `outputs`          | block   | yes      | see §3.3                                                 |
| `related_docs`     | list    | yes      | repo-relative paths to `docs/*.md` pages                 |
| `related_recipes`  | list    | yes      | `RECIPE-NNN` references (may be empty)                   |
| `tags`             | list    | yes      | lowercase ASCII tags, hyphen-separated within a tag      |
| `author`           | string  | no       | original author                                          |
| `created`          | string  | no       | ISO-8601 UTC timestamp                                   |
| `last_updated`     | string  | no       | ISO-8601 UTC timestamp                                   |
| `deprecated`       | string  | no       | deprecation message; presence marks the recipe DEPRECATED |
| `superseded_by`    | string  | no       | `RECIPE-NNN` of the replacement recipe                   |

## 3.2 `inputs` block

The `inputs` block is a YAML-like block with two indented
sub-blocks: `required` and `optional`. Each sub-block lists
the input parameters and their types.

```
inputs:
  required:
    - name: reporter_code
      type: int
      description: UN Comtrade reporter code (e.g. 699 for India)
    - name: period
      type: str
      description: ISO-8601 year or year-month (e.g. "2022" or "202205")
  optional:
    - name: partner_code
      type: int
      default: 0
      description: 0 means "all partners"
```

Each input MUST declare `name`, `type`, and `description`.
Optional inputs MUST declare `default`.

## 3.3 `outputs` block

The `outputs` block lists the artefacts the recipe produces.
Each output declares `kind`, `path`, and `description`.

```
outputs:
  - kind: file
    path: output/RECIPE_002_<timestamp>.parquet
    description: Parquet dataset, one row per trade record
  - kind: file
    path: output/RECIPE_002_<timestamp>.meta.json
    description: Metadata sidecar (run info + SHA-256 digest)
  - kind: stdout
    path: null
    description: Single-line summary of the run
```

`kind` is one of `file`, `stdout`, `stderr`. A recipe that
writes no files declares only the `stdout` entry.

## 3.4 Lists

A list frontmatter field is encoded as a YAML block
sequence:

```
related_docs:
  - docs/007_SDK_SPECIFICATION.md
  - docs/008_METADATA_LAYER_SPEC.md
```

The cookbook linter parses lists by indentation.

## 3.5 Tags

`tags` is a list of lowercase ASCII tokens, each token
being 2–24 characters. Tokens MAY contain a hyphen
(`top-exports`) or an underscore (`partner_growth`) but
not both. Tags are used by the cookbook search index.

```
tags:
  - metadata
  - countries
  - cached
```

---

# 4. Body Sections

A recipe's body is organised into six named sections, in
the order shown.

## 4.1 Section: imports

Standard library imports first, third-party second, SDK
last. SDK imports use the documented public surface only
(`un_comtrade`, `un_comtrade.config`,
`un_comtrade.exceptions`, `un_comtrade.analytics.*`,
`un_comtrade.storage.*`). Reaching into `un_comtrade.*`
internals is rejected.

## 4.2 Section: configuration

Build the SDK's `Configuration` object. The recipe:

- Reads the API key from `os.environ["UN_COMTRADE_KEY"]`
  (or skips the read when `requires_api_key: no`).
- Resolves `--output` (default `./output`).
- Resolves `--verbose` / `-v`.
- Creates the output directory if it does not exist.

The configuration is **immutable** after this section.
A recipe that mutates configuration after construction is
rejected.

## 4.3 Section: build

Construct the SDK objects (typically `ComtradeClient` and
the service the recipe demonstrates). The construction is
declarative; no method calls happen here.

## 4.4 Section: run

Call the SDK methods the recipe demonstrates. This is the
**only** section that makes network calls. Progress and
debug logging belong here.

## 4.5 Section: output

Persist results, emit the stdout summary line, and clean
up. The output section:

- Writes data files using SDK storage backends
  (never hand-rolled JSON / CSV).
- Writes the sidecar JSON file.
- Prints the single-line summary to stdout.
- Closes the client (or exits the `with` block).

## 4.6 Section: cleanup

Release SDK resources. For recipes that use
`ComtradeClient` directly, this is the `with` block's
`__exit__`. For recipes that use a different resource
(an open file, a temporary directory), this is the
context manager that releases it.

## 4.7 Section: error handling

The error-handling section wraps the entire `main()` in
a single `try` / `except ComtradeError` block that maps
the exception to the exit code in §6.4 of
`recipes/README.md`. The mapping is codified in a small
helper `_exit_code_for(exc)` at the top of the section.

---

# 5. Imports Standard

Recipes use a fixed import style:

```python
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from un_comtrade import ComtradeClient
from un_comtrade.config import Configuration
from un_comtrade.exceptions import (
    APIError,
    AuthenticationError,
    ComtradeError,
    ConfigurationError,
    NetworkError,
    RateLimitError,
    ServerError,
    ValidationError,
)
```

Third-party imports (`pandas`, `pyarrow`, `duckdb`, …) are
added only when the recipe needs them. The recipe's
`pyproject.toml` entry MUST list the third-party
dependency, and the recipe's frontmatter `tags` SHOULD
include the dependency name.

---

# 6. parse_args() Standard

A `parse_args()` helper returns an `argparse.Namespace`.
The helper accepts:

- `--output DIR` (default `./output`)
- `--verbose` / `-v` (boolean)
- Domain parameters as appropriate for the recipe

A recipe whose only "input" is the implicit
`UN_COMTRADE_KEY` env var is allowed to omit
`parse_args()`.

The `parse_args()` function MUST call
`parser.parse_args()` (not `parse_known_args()`); unknown
flags are an error and exit with code `2`.

---

# 7. main() Standard

`main()` is the recipe's entry point. The shape is:

```python
def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        config = build_config(args)
        with ComtradeClient(config) as client:
            result = run(client, args, output_dir)
        emit_summary(result)
    except ComtradeError as exc:
        return handle_error(exc)

    return 0
```

A recipe that does not fit this shape MUST justify the
deviation in a comment next to the deviation. The cookbook
linter flags unexplained deviations.

`main()` returns an `int` exit code. Recipes MUST NOT call
`sys.exit()` directly; they return the exit code and let
the `if __name__ == "__main__"` block translate it.

---

# 8. Output Naming Standard

File outputs follow the pattern:

```
<output-dir>/<recipe_id>_<UTC-timestamp>.<ext>
<output-dir>/<recipe_id>_<UTC-timestamp>.meta.json
```

The UTC timestamp is `datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")`.
The `meta.json` file is a flat object:

```json
{
  "recipe_id": "RECIPE_002",
  "title": "Fetch India's 2022 exports",
  "category": "trade",
  "sdk_version": "1.0.2",
  "python_version": "3.11.9",
  "run_started_at": "2026-06-29T10:30:00Z",
  "run_finished_at": "2026-06-29T10:30:42Z",
  "command_line": ["recipes/trade/RECIPE_002_fetch_india_exports_2022.py", "--reporter", "699", "--year", "2022"],
  "input_summary": {"reporter_code": 699, "year": 2022},
  "output_digests": {
    "data": "sha256:<64 hex chars>"
  },
  "warnings": [],
  "errors": []
}
```

A recipe that produces multiple data files lists each
under `output_digests` with a stable key.

---

# 9. Validation

A recipe is **conformant** when:

- The frontmatter parses with the cookbook linter.
- The body imports compile.
- The file runs end-to-end with a configured key and
  produces the declared outputs.
- The exit code is `0` on success.
- The `meta.json` sidecar is present and valid JSON.
- The recipe is referenced from its parent category
  `README.md`.

The cookbook CI (future) runs the linter and the smoke
suite on every pull request. A recipe that breaks the
linter is rejected at review.

---

# 10. Worked Example (Skeleton)

The skeleton below shows the shape of a conforming recipe.
It is **not** a runnable example — the body is intentionally
empty. The companion `recipes/_TEMPLATE.py` carries the same
shape as importable code.

```python
"""
---
recipe_id: RECIPE-XXX
title: <short human title>
category: <one of the seven categories>
difficulty: beginner | intermediate | advanced
sdk_version: >=1.0.2
requires_api_key: yes | no | optional
estimated_runtime: <1s | <10s | <1min | 1-10min | 10-60min | >1h
inputs:
  required:
    - name: <param>
      type: <int|str|...>
      description: <text>
  optional:
    - name: <param>
      type: <int|str|...>
      default: <value>
      description: <text>
outputs:
  - kind: file
    path: output/RECIPE_XXX_<timestamp>.<ext>
    description: <text>
related_docs:
  - docs/<path>.md
related_recipes: []
tags:
  - <tag>
---

<one paragraph describing what the recipe demonstrates>
"""

# ---- imports ---------------------------------------------------------------

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from un_comtrade import ComtradeClient
from un_comtrade.config import Configuration
from un_comtrade.exceptions import ComtradeError

# ---- constants -------------------------------------------------------------

LOGGER = logging.getLogger("un_comtrade")

# ---- parse_args ------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="RECIPE-XXX",
        description=__doc__,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./output"),
        help="Output directory (default: ./output).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable DEBUG-level SDK logging.",
    )
    # Add domain arguments here.
    return parser.parse_args(argv)


# ---- build -----------------------------------------------------------------


def build_config(args: argparse.Namespace) -> Configuration:
    return Configuration(api_key=os.environ.get("UN_COMTRADE_KEY", ""))


# ---- run -------------------------------------------------------------------


def run(
    client: ComtradeClient,
    args: argparse.Namespace,
    output_dir: Path,
) -> dict[str, object]:
    # Implement the recipe's main flow.
    raise NotImplementedError


# ---- output ----------------------------------------------------------------


def emit_summary(result: dict[str, object]) -> None:
    parts = [f"{k}={v}" for k, v in result.items()]
    sys.stdout.write(" ".join(parts) + "\n")


# ---- cleanup ---------------------------------------------------------------

# (handled by the `with ComtradeClient(config) as client:` block)


# ---- error handling --------------------------------------------------------


def _exit_code_for(exc: ComtradeError) -> int:
    from un_comtrade.exceptions import (
        APIError,
        AuthenticationError,
        NetworkError,
        RateLimitError,
        ServerError,
        ValidationError,
    )
    if isinstance(exc, ValidationError):
        return 3
    if isinstance(exc, AuthenticationError):
        return 4
    if isinstance(exc, RateLimitError):
        return 5
    if isinstance(exc, NetworkError):
        return 6
    if isinstance(exc, ServerError):
        return 7
    if isinstance(exc, APIError):
        return 8
    return 1


# ---- main ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    output_dir: Path = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    config = build_config(args)
    try:
        with ComtradeClient(config) as client:
            result = run(client, args, output_dir)
        emit_summary(result)
    except ComtradeError as exc:
        LOGGER.error(
            "recipe=%s error_class=%s message=%s",
            "RECIPE-XXX",
            type(exc).__name__,
            exc,
        )
        return _exit_code_for(exc)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

This is the **shape** of a recipe. Recipe bodies are added
by subsequent `CB-NNN` tasks; this document carries no
runnable example.
