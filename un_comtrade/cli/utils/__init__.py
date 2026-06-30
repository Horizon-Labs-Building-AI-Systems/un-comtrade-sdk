"""Helpers for the un-comtrade CLI.

Public surface:

- Exit codes: :data:`EXIT_OK`, :data:`EXIT_GENERIC_ERROR`,
  :data:`EXIT_USER_ERROR`, :data:`EXIT_CONFIG_ERROR`,
  :data:`EXIT_NETWORK_ERROR`, :data:`EXIT_AUTH_ERROR`.
- Errors: :class:`CLIError`, :class:`CLIConfigurationError`.
- Configuration: :func:`load_cli_configuration`.
- Output formats: :data:`OUTPUT_FORMATS`.

CLI internals only — no business logic.
"""

from .exit_codes import (
    EXIT_AUTH_ERROR,
    EXIT_CONFIG_ERROR,
    EXIT_GENERIC_ERROR,
    EXIT_NETWORK_ERROR,
    EXIT_OK,
    EXIT_USER_ERROR,
)
from .exceptions import (
    CLIConfigurationError,
    CLIError,
)
from .config_loader import (
    OUTPUT_FORMATS,
    load_cli_configuration,
)
from .output import render_to_destination
from .progress import (
    ProgressReporter,
    make_progress_reporter,
)
from .dataset_loader import (
    load_dataset,
)


__all__ = [
    "CLIConfigurationError",
    "CLIError",
    "EXIT_AUTH_ERROR",
    "EXIT_CONFIG_ERROR",
    "EXIT_GENERIC_ERROR",
    "EXIT_NETWORK_ERROR",
    "EXIT_OK",
    "EXIT_USER_ERROR",
    "OUTPUT_FORMATS",
    "ProgressReporter",
    "load_cli_configuration",
    "load_dataset",
    "make_progress_reporter",
    "render_to_destination",
]