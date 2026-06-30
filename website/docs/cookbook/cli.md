---
title: CLI recipes
description: 6 runnable recipes covering every CLI command group — metadata, trade, analytics, storage, ETL, output formats.
audience: cli
prerequisites: []
related_recipes:
  - RECIPE-091
  - RECIPE-095
  - RECIPE-099
  - RECIPE-100
  - RECIPE-101
  - RECIPE-104
related_api: []
related_guides:
  - guides/cli/index/
  - cookbook/index/
---

# CLI recipes

The CLI category covers the `un-comtrade` console script: every
command group driven from a Python recipe. Each recipe invokes the
CLI as a subprocess and parses the structured output.

| ID         | Title                                       | Runtime | API key |
| ---------- | ------------------------------------------- | ------- | ------- |
| RECIPE-091 | Drive metadata commands from the CLI        | 2 – 4 s | no      |
| RECIPE-095 | Drive trade commands from the CLI           | 2 – 4 s | no      |
| RECIPE-099 | Drive analytics commands from the CLI       | 2 – 4 s | no      |
| RECIPE-100 | Drive ETL from the CLI                      | 2 – 4 s | no      |
| RECIPE-101 | Drive storage from the CLI                  | 2 – 4 s | no      |
| RECIPE-104 | Output formats from the CLI                 | 2 – 4 s | no      |

## Path

1. **[RECIPE-091][recipe-091]** — *Drive metadata commands from the CLI*.
2. **[RECIPE-095][recipe-095]** — *Drive trade commands from the CLI*.
3. **[RECIPE-099][recipe-099]** — *Drive analytics commands from the CLI*.
4. **[RECIPE-100][recipe-100]** — *Drive ETL from the CLI*.
5. **[RECIPE-101][recipe-101]** — *Drive storage from the CLI*.
6. **[RECIPE-104][recipe-104]** — *Output formats from the CLI*.

## Run them all

```bash
for recipe in recipes/cli/*.py; do
    UN_COMTRADE_MOCK=1 python "$recipe"
done
```

## Related Recipes

- **[RECIPE-091][recipe-091]** — *Drive metadata commands from the CLI*.
- **[RECIPE-095][recipe-095]** — *Drive trade commands from the CLI*.
- **[RECIPE-099][recipe-099]** — *Drive analytics commands from the CLI*.
- **[RECIPE-100][recipe-100]** — *Drive ETL from the CLI*.
- **[RECIPE-101][recipe-101]** — *Drive storage from the CLI*.
- **[RECIPE-104][recipe-104]** — *Output formats from the CLI*.

## Related Guides

- **[CLI → Index][cli-index]** — full CLI command reference.
- **[Python SDK → Trade][python-trade]** — equivalent Python API.

## Next steps

- **[End-to-end recipes][cb-end-to-end]** — full pipelines from
  query to report.

[recipe-091]: ../../recipes/cli/01_metadata_cli.py
[recipe-095]: ../../recipes/cli/02_trade_cli.py
[recipe-099]: ../../recipes/cli/03_analytics_cli.py
[recipe-100]: ../../recipes/cli/05_etl_cli.py
[recipe-101]: ../../recipes/cli/04_storage_cli.py
[recipe-104]: ../../recipes/cli/06_output_formats_cli.py
[cli-index]: ../guides/cli/
[python-trade]: ../guides/python/trade/
[cb-end-to-end]: ../end_to_end/