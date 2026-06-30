---
title: Migration guide
description: Upgrade from pre-1.0 development releases; per-release breaking changes; before / after code snippets.
audience: maintainer
prerequisites: []
skips:
  - Prerequisites
  - Walkthrough
  - Examples
related_recipes: []
related_api: []
related_guides:
  - release_notes/v1/
---

# Migration guide

This guide covers breaking changes introduced between the pre-1.0
development releases and v1.0.x. Each entry has a one-paragraph
summary, the affected audience, before / after code snippets, and a
timeline.

## v1.0.0 — `un_comtrade.logging.DEFAULT_LOG_LEVEL` rename

### Summary

The default log level constant moved from
`un_comtrade.logging.DEFAULT_LOG_LEVEL` (numeric value) to
`un_comtrade.config.DEFAULT_LOG_LEVEL` (string value `"WARNING"`).
The rename aligns the constant with the configuration namespace and
makes the value directly comparable to user-supplied strings.

### Affected audience

Anyone who imported `DEFAULT_LOG_LEVEL` from `un_comtrade.logging`
to programmatically set or compare the default log level.

### Before (pre-1.0)

```python
from un_comtrade.logging import DEFAULT_LOG_LEVEL
import logging

logging.basicConfig(level=DEFAULT_LOG_LEVEL)
```

### After (v1.0.0+)

```python
from un_comtrade.config import DEFAULT_LOG_LEVEL
import logging

logging.basicConfig(level=DEFAULT_LOG_LEVEL)
```

The constant value is now a string (`"WARNING"`) rather than the
numeric `logging.WARNING`. `logging.basicConfig` accepts both
forms.

### Timeline

- **2026-06-28** (v1.0.0) — `un_comtrade.logging` gained the
  deprecation alias `DEFAULT_LOG_LEVEL` pointing at the new
  constant.
- **2026-06-29** (v1.0.1) — the deprecation alias was removed
  entirely; only `un_comtrade.config.DEFAULT_LOG_LEVEL` remains.

## v1.0.0 — `un_comtrade.storage.LocalFilesStorage` removal

### Summary

The placeholder `LocalFilesStorage` class was removed in v1.0.0.
The public storage surface is the four concrete backends
(`CSVWriter`, `JSONWriter`, `ParquetWriter`, `DuckDBWriter`)
plus the `StorageRegistry.open(uri)` auto-detect accessor.

### Affected audience

Anyone who imported `LocalFilesStorage` directly from
`un_comtrade.storage`.

### Before (pre-1.0)

```python
from un_comtrade.storage import LocalFilesStorage

storage = LocalFilesStorage(root="/data/un_comtrade")
```

### After (v1.0.0+)

Use the auto-detect accessor:

```python
from un_comtrade import ComtradeClient

with ComtradeClient() as client:
    client.storage.open("/data/un_comtrade/manifest.json").read()
```

Or one of the concrete backends:

```python
from un_comtrade.storage.csv import CSVWriter
from un_comtrade.storage import StorageConfig

config = StorageConfig(root="/data/un_comtrade")
writer = CSVWriter(config)
```

## v1.0.0 — `ComtradeClient.DECLARED_METHOD_COUNT` removal

### Summary

The decorative `DECLARED_METHOD_COUNT` constant on `ComtradeClient`
was removed in v1.0.0. It was never part of the public contract;
the 251 public symbols are documented in the API reference.

### Affected audience

Anyone who introspected `ComtradeClient.DECLARED_METHOD_COUNT`.

### Before / After

There is no public-API replacement. If you need to enumerate the
public symbols, inspect `un_comtrade.__all__` or use the
`tools/audit_public_api.py` script.

## Related Guides

- **[v1 release notes][v1]** — what's in v1.

[v1]: v1/