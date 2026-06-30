# un-comtrade-sdk

[![CI](https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/actions/workflows/quality.yml/badge.svg)](https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/actions/workflows/quality.yml)
[![Security](https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/actions/workflows/security.yml/badge.svg)](https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/actions/workflows/security.yml)
[![Package](https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/actions/workflows/package.yml/badge.svg)](https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/actions/workflows/package.yml)
[![Docs](https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/actions/workflows/docs.yml/badge.svg)](https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/actions/workflows/docs.yml)
[![Release](https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/actions/workflows/release.yml/badge.svg)](https://github.com/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk/actions/workflows/release.yml)
[![PyPI version](https://img.shields.io/pypi/v/un-comtrade-sdk.svg)](https://pypi.org/project/un-comtrade-sdk/)
[![Python versions](https://img.shields.io/pypi/pyversions/un-comtrade-sdk.svg)](https://pypi.org/project/un-comtrade-sdk/#files)
[![License](https://img.shields.io/github/license/Horizon-Labs-Building-AI-Systems/un-comtrade-sdk.svg)](./LICENSE)

Python SDK for the UN Comtrade (UNSD) trade statistics API.

> **Status:** Project bootstrap. The package skeleton exists; no
> functional layers are implemented yet. See
> `IMPLEMENTATION_BACKLOG.md` for the implementation roadmap.

## Installation (planned)

The package is not yet published. Once published:

```bash
pip install un-comtrade-sdk
```

## Quick start (planned)

```python
from un_comtrade import ComtradeClient

client = ComtradeClient(api_key="<your-subscription-key>")
countries = client.metadata.get_countries()
```

## Documentation

- `IMPLEMENTATION_BASELINE_v1.md` — single entry point for future
  implementation sessions.
- `IMPLEMENTATION_ROADMAP.md` — 10-phase roadmap.
- `DECISIONS.md` — 36 architectural decisions, all `Accepted`.
- `PROJECT_CLARIFICATION_REGISTER.md` — every pending engineering
  decision.

## Project status

| Component | Status |
| --------- | ------ |
| Documentation | Complete (21 docs in `docs/`) |
| Architecture | Frozen (36 ADRs) |
| External verification | Complete (4 reports) |
| Implementation | In progress (Phase 1) |

## License

MIT — see `LICENSE`.