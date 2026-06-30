# un-comtrade-sdk

[![TestPyPI](https://img.shields.io/pypi/v/un-comtrade-sdk.svg?pypiBaseUrl=https%3A%2F%2Ftest.pypi.org&label=testpypi&color=blue)](https://test.pypi.org/project/un-comtrade-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/un-comtrade-sdk.svg?pypiBaseUrl=https%3A%2F%2Ftest.pypi.org&label=python)](https://test.pypi.org/project/un-comtrade-sdk/#files)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)

Production-ready Python SDK for the UN Comtrade (UNSD) trade statistics API.
Typed. Documented. Tested. Validated on every push to `main`.

## Status

The latest development release is published on **TestPyPI**. The same source
builds cleanly on every push; CI is the gate. Production PyPI mirrors the
release once a stable cut is tagged.

| Quality gate | What it proves | Last run on `main` |
| --- | --- | --- |
| [Quality](https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/actions/workflows/quality.yml) | `ruff`, `mypy`, automated test suite | passing |
| [Documentation](https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/actions/workflows/docs.yml) | `mkdocs build --strict` | passing |
| [Package](https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/actions/workflows/package.yml) | `python -m build` (wheel + sdist), `twine check` | passing |
| [Security](https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/actions/workflows/security.yml) | TruffleHog secret scan, `pip-audit` across Python 3.11–3.13 | passing |
| [Release](https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/actions/workflows/release.yml) | tag-driven TestPyPI publication | passing |

## Install

```bash
pip install \
  --index-url https://test.pypi.org/simple \
  --extra-index-url https://pypi.org/simple \
  un-comtrade-sdk
```

Check the import:

```python
>>> import un_comtrade
```

If the import succeeds, the install worked. The package version is exposed via
`un_comtrade.__version__` and is also reported by the `un-comtrade --version`
console script.

## Quick start

```python
from un_comtrade import ComtradeClient

# Reads UN_COMTRADE_KEY from the environment by default.
client = ComtradeClient()

# Reference metadata.
countries = client.metadata.get_countries()
classifications = client.metadata.get_classifications()

# Trade flows.
exports = client.trade.get_exports(reporter_code=699, period="2022")
imports  = client.trade.get_imports(reporter_code=699, period="2022")
```

The single public entry point is `un_comtrade.client.ComtradeClient`. Endpoints
are grouped by domain: `metadata`, `trade`, `etl`, `analytics`, `storage`. See
[the SDK specification](docs/007_SDK_SPECIFICATION.md) for the full surface.

A minimal CLI is shipped as the `un-comtrade` console script:

```bash
un-comtrade --version     # prints the installed version
un-comtrade metadata countries
```

## Documentation

- API reference + cookbook — built with [mkdocs](https://www.mkdocs.org/) from
  [`website/`](website/). Local preview:

  ```bash
  cd website && python -m mkdocs serve
  ```

- Design documents — [`docs/`](docs/): specification, architecture, ADRs,
  ETL / storage / packaging / testing standards.
- [Release notes](docs/032_v1_RELEASE_NOTES.md) — historical record of
  changes shipped in the v1.x series.
- [Engineering change log](docs/CHANGELOG.md) — every CHG entry since
  project start.

## Project metadata

| Field | Value |
| --- | --- |
| Distribution name | `un-comtrade-sdk` |
| License | MIT |
| Python | `>= 3.11` |
| Classifier | `Development Status :: 5 - Production/Stable` |
| Latest release | [GitHub Releases](https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/releases) |
| Homepage | https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk |
| Repository | https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk |
| Issues | https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/issues |
| Changelog | https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/blob/main/docs/CHANGELOG.md |
| Release notes (v1.x series) | https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/blob/main/docs/032_v1_RELEASE_NOTES.md |
| TestPyPI index | https://test.pypi.org/project/un-comtrade-sdk/ |
| Documentation site | https://horizon-labs-building-ai-systems.github.io/un-comtrade-sdk/ |

## License

[MIT](LICENSE).
