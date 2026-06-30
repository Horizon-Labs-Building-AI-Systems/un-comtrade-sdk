"""Top-level package for the un-comtrade CLI.

The CLI is the first consumer of the public SDK
API surface (per `031_PRODUCTION_READINESS.md` §9
and `docs/IMPLEMENTATION_BASELINE_v1.md` §7
"Application").

The foundation phase (C-001) ships:

- A argparse-based root parser
  (:func:`un_comtrade.cli.main.build_parser`).
- A ``main(argv)`` entry point
  (:func:`un_comtrade.cli.main.main`).
- Exit codes (:data:`EXIT_OK`, ...).
- Configuration loader
  (:func:`un_comtrade.cli.utils.load_cli_configuration`).
- Output formatters: JSON (functional), TABLE
  and CSV (placeholders for P7-002+).
- Zero business commands. The CLI is ready for
  P7-002 to register ``metadata``, ``trade``,
  ``storage``, ``etl``, and ``analytics`` commands.

Public surface (re-exported for convenience):

- :func:`build_parser`
- :func:`main`
- :data:`EXIT_OK` / :data:`EXIT_GENERIC_ERROR` /
  :data:`EXIT_USER_ERROR` / :data:`EXIT_CONFIG_ERROR` /
  :data:`EXIT_NETWORK_ERROR` / :data:`EXIT_AUTH_ERROR`
- :class:`CLIError` / :class:`CLIConfigurationError`
- :func:`load_cli_configuration`
- :data:`OUTPUT_FORMATS`
"""

from .main import build_parser, main
from .utils import (
    EXIT_AUTH_ERROR,
    EXIT_CONFIG_ERROR,
    EXIT_GENERIC_ERROR,
    EXIT_NETWORK_ERROR,
    EXIT_OK,
    EXIT_USER_ERROR,
    OUTPUT_FORMATS,
    CLIConfigurationError,
    CLIError,
    ProgressReporter,
    load_cli_configuration,
    load_dataset,
    make_progress_reporter,
    render_to_destination,
)


__all__ = [
    "build_parser",
    "main",
    # Exit codes
    "EXIT_AUTH_ERROR",
    "EXIT_CONFIG_ERROR",
    "EXIT_GENERIC_ERROR",
    "EXIT_NETWORK_ERROR",
    "EXIT_OK",
    "EXIT_USER_ERROR",
    # Errors
    "CLIConfigurationError",
    "CLIError",
    # Configuration
    "OUTPUT_FORMATS",
    "ProgressReporter",
    "load_cli_configuration",
    "load_dataset",
    "make_progress_reporter",
    "render_to_destination",
]