"""CLI-side exception hierarchy.

The CLI catches these and translates them into
exit codes via :mod:`un_comtrade.cli.utils.exit_codes`.

All exceptions inherit from
:class:`un_comtrade.exceptions.ComtradeError` so
that callers may use a single ``except`` clause
to catch both SDK and CLI errors.
"""

from un_comtrade.exceptions import ComtradeError


class CLIError(ComtradeError):
    """Base class for CLI-raised errors.

    Inherits from :class:`ComtradeError` so that
    callers may catch SDK and CLI errors with the
    same ``except`` clause.
    """


class CLIConfigurationError(CLIError):
    """Raised when the CLI cannot load or apply
    a configuration (missing API key, malformed
    ``~/.un_comtrade`` config, etc.).
    """


__all__ = [
    "CLIConfigurationError",
    "CLIError",
]