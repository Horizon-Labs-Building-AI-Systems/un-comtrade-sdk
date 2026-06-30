---
title: Guides
description: Task-oriented walkthroughs grouped by audience — Python developers, CLI users, data analysts.
audience: all
prerequisites: []
skips:
  - Prerequisites
  - Walkthrough
  - Examples
related_recipes: []
related_api: []
related_guides:
  - guides/python/index/
  - guides/cli/index/
  - guides/analysts/index/
---

# Guides

The Guides section is the **task-oriented** navigation spine of this
site. Three sub-sections, one per audience emphasis:

| Sub-section | Audience | What it covers |
| ----------- | -------- | -------------- |
| **[Python SDK][python-index]** | Python developers | Idiomatic Python patterns for the SDK — type hints, dataclasses, context managers. |
| **[Command-line][cli-index]** | CLI users, shell-scripters | Drive the SDK from a terminal; pipe output to other Unix tools. |
| **[Data Analysis][analysts-index]** | Data analysts | Pandas, Jupyter, DuckDB, and Markdown report patterns. |

## Path

1. **[Python SDK][python-index]** — the most common entry point.
   Covers `ComtradeClient`, the five service facades, and idiomatic
   error handling.
2. **[Command-line][cli-index]** — for terminal-first users and
   shell-scripted pipelines. Five outer commands
   (`metadata`, `trade`, `analytics`, `storage`, `etl`),
   22 sub-subcommands, and five output formats.
3. **[Data Analysis][analysts-index]** — for analysts who want to
   explore UN Comtrade data interactively. Covers pandas, Jupyter,
   DuckDB, and Markdown report generation.

## Related API

- [`un_comtrade.ComtradeClient`][api-client] — the single public
  entry point used by every guide.

## Related Guides

- **[Python SDK][python-index]**
- **[Command-line][cli-index]**
- **[Data Analysis][analysts-index]**

## Next steps

- **[Python SDK → Trade][python-trade]** — the most common entry
  point.
- **[Command-line → Metadata][cli-metadata]** — try the CLI without
  writing any Python.

[python-index]: python/
[cli-index]: cli/
[analysts-index]: analysts/
[python-trade]: python/trade/
[cli-metadata]: cli/metadata/
[api-client]: ../api/client/