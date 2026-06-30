"""Version constant for the un-comtrade-sdk package.

This module is the single source of truth for the package
version. The version is also declared in `pyproject.toml`;
both MUST be kept in sync. The build process (F-004
regression guard) fails if they disagree.

History:

- 0.1.0 — initial development releases (Phase 1–6.5).
- 1.0.0 — first stable release (CHG-0079).
  - R1: rename ``logging.DEFAULT_LOG_LEVEL`` →
    ``LOGGING_DEFAULT_LEVEL``.
  - Production-ready: 91.4/100 readiness score.
- 1.0.1 — performance patch (CHG-0080).
  - DuckDB bulk-insert speedup ~100×.
  - ``country_vs_country`` filter-fusion ~5–10×.
- 1.0.1 — F-003 collision closure (CHG-0081).
  - Remove deprecated alias; only
    ``LOGGING_DEFAULT_LEVEL`` remains in
    ``un_comtrade.logging``.

F-004 (this version) syncs the package metadata
across ``pyproject.toml`` (canonical), this
``__version__`` module, and the published
``Development Status :: 5 - Production/Stable``
classifier.
"""

__version__ = "1.0.3"