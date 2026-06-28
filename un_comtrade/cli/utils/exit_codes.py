"""Exit codes for the un-comtrade CLI.

These follow POSIX / BSD `sysexits.h` conventions
where applicable. They are exposed via
:mod:`un_comtrade.cli.utils` and consumed by
:func:`un_comtrade.cli.main.main`.
"""

#: Success — command completed without error.
EXIT_OK: int = 0

#: Generic / unspecified error.
EXIT_GENERIC_ERROR: int = 1

#: User-supplied argument is invalid
#: (``argparse`` exits with 2 by default;
#: we re-export this constant for symmetry with
#: Python's own ``argparse`` convention).
EXIT_USER_ERROR: int = 2

#: Configuration could not be loaded or is invalid.
EXIT_CONFIG_ERROR: int = 78

#: Network / upstream failure (timeout, connection
#: reset, non-retryable 5xx, etc.).
EXIT_NETWORK_ERROR: int = 69

#: Authentication / authorization failure (401 / 403).
EXIT_AUTH_ERROR: int = 77


__all__ = [
    "EXIT_AUTH_ERROR",
    "EXIT_CONFIG_ERROR",
    "EXIT_GENERIC_ERROR",
    "EXIT_NETWORK_ERROR",
    "EXIT_OK",
    "EXIT_USER_ERROR",
]