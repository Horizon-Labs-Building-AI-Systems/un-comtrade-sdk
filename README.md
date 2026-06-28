# un-comtrade-sdk

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