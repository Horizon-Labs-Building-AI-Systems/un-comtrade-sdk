"""Command-line entry point for un-comtrade.

This module is the single ``main(argv=None)`` entry
point of the CLI. It is registered as the
``un-comtrade`` console script in
``pyproject.toml``.

C-001 (Foundation):

- argparse root parser
- ``--help`` / ``--version``
- ``--api-key`` override
- ``--log-level`` override
- ``--output-format`` override
- exit-code handling
- no business commands

C-002 (Metadata commands):

- ``--output PATH`` global flag (write to file).
- ``metadata`` outer command with six
  sub-subcommands: ``countries``, ``partners``,
  ``hs``, ``classifications``, ``frequencies``,
  ``transport-modes``.
- ``metadata <sub>`` calls the corresponding
  public ``MetadataService`` method via
  ``ComtradeClient(configuration=...).metadata``.

The CLI consumes ONLY public SDK APIs.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

import un_comtrade
from un_comtrade.cli.utils import (
    EXIT_AUTH_ERROR,
    EXIT_CONFIG_ERROR,
    EXIT_GENERIC_ERROR,
    EXIT_NETWORK_ERROR,
    EXIT_OK,
    EXIT_USER_ERROR,
    OUTPUT_FORMATS,
    CLIConfigurationError,
    CLIError,
    load_cli_configuration,
    render_to_destination,
)
from un_comtrade.cli.commands import (
    get_command,
    iter_commands,
    known_command_names,
    register_command,
)
from un_comtrade.cli.commands.metadata import (
    _install_metadata_commands as _install_metadata,
)
from un_comtrade.cli.commands.trade import (
    _install_trade_commands as _install_trade,
)
from un_comtrade.cli.commands.analytics import (
    _install_analytics_commands as _install_analytics,
)
from un_comtrade.cli.commands.storage import (
    _install_storage_commands as _install_storage,
)
from un_comtrade.cli.commands.etl import (
    _install_etl_commands as _install_etl,
)
from un_comtrade.cli.formatting import get_formatter
from un_comtrade.exceptions import (
    AuthenticationError,
    ComtradeError,
    ConfigurationError,
    NetworkError,
)


__all__ = [
    "build_parser",
    "main",
]


# Register built-in business commands at import
# time. C-002 adds the ``metadata`` family; C-003
# adds the ``trade`` family; C-004 adds the
# ``analytics`` family; C-005 adds ``storage`` +
# ``etl``.
_install_metadata()
_install_trade()
_install_analytics()
_install_storage()
_install_etl()


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------


def build_parser(
    *,
    prog: str = "un-comtrade",
    description: str = (
        "Command-line interface for the un-comtrade-sdk. "
        "The CLI is a thin consumer of the SDK's public "
        "API surface; the SDK itself is fully usable "
        "from Python."
    ),
) -> argparse.ArgumentParser:
    """Construct the root argparse parser.

    Returns a parser with global options and
    subparsers for every registered command. Tests
    use this to construct the parser without
    running :func:`main`.
    """
    parser = argparse.ArgumentParser(
        prog=prog,
        description=description,
        add_help=True,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"un-comtrade {un_comtrade.__version__} "
        f"(un-comtrade-sdk {un_comtrade.__version__})",
    )

    # ----- Global options ----------------------------------------------

    parser.add_argument(
        "--api-key",
        dest="api_key",
        default=None,
        help=(
            "Override the UN_COMTRADE_KEY env var. "
            "Useful when running one-shot commands "
            "without persisting the key in your "
            "environment."
        ),
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        default=None,
        help=(
            "Override the configured log level. "
            "One of DEBUG / INFO / WARNING / "
            "ERROR / CRITICAL."
        ),
    )
    parser.add_argument(
        "--output-format",
        dest="output_format",
        default=None,
        choices=OUTPUT_FORMATS,
        help=(
            "Render command output in the chosen "
            f"format. Default: json. Choices: "
            f"{', '.join(OUTPUT_FORMATS)}."
        ),
    )
    parser.add_argument(
        "--output",
        dest="output",
        default=None,
        help=(
            "Write the rendered output to PATH "
            "instead of stdout. Useful for "
            "redirecting into scripts / pipes."
        ),
    )

    # ----- Subparsers --------------------------------------------------

    names = known_command_names()
    if names:
        sub = parser.add_subparsers(
            title="commands",
            dest="command",
            metavar="<command>",
            help="Available subcommands.",
        )
        for name in names:
            cmd = get_command(name)
            if cmd is None:
                continue
            # Group commands (``metadata`` and
            # future siblings) expose
            # ``install_subparser`` and own their
            # own sub-subparsers. Single-shot
            # commands get a flat subparser that
            # forwards all args to ``__call__``.
            install = getattr(cmd, "install_subparser", None)
            if callable(install):
                install(sub)
            else:
                sub.add_parser(
                    name,
                    help=cmd.help,
                    description=cmd.help,
                    add_help=True,
                )

    return parser


# ---------------------------------------------------------------------------
# Default command (no business commands yet)
# ---------------------------------------------------------------------------


def _default_root_command(_args: argparse.Namespace) -> int:
    """The default action when the user runs
    ``un-comtrade`` with no subcommand.
    """
    sys.stdout.write(
        "un-comtrade — UN Comtrade Python SDK CLI\n"
        f"version: {un_comtrade.__version__}\n"
        "\n"
        "Run `un-comtrade --help` for the global "
        "options.\n"
        "Run `un-comtrade <command> --help` for "
        "details on a specific subcommand.\n"
    )
    return EXIT_OK


register_command(
    "root",
    lambda: _RootCommand(),
    help=(
        "Default action: print the CLI banner "
        "and exit. Reached when no subcommand "
        "is supplied."
    ),
)


class _RootCommand:
    """Internal command-protocol wrapper for the
    default banner-printing action.
    """

    name: str = "root"
    help: str = (
        "Default action: print the CLI banner "
        "and exit."
    )

    def __call__(self, _args: argparse.Namespace) -> int:
        return _default_root_command(_args)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI.

    Parameters
    ----------
    argv
        Argument vector to parse. When ``None``
        (the default), ``sys.argv[1:]`` is used.

    Returns
    -------
    int
        The exit code. By convention:

        - ``0`` — success.
        - ``1`` — generic / unspecified error.
        - ``2`` — user argument error (argparse).
        - ``69`` — network error.
        - ``77`` — authentication error.
        - ``78`` — configuration error.
    """
    parser = build_parser()

    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else EXIT_USER_ERROR
        return code

    # Apply the configuration overrides BEFORE
    # invoking the command.
    try:
        cfg = load_cli_configuration(
            api_key=args.api_key,
            log_level=args.log_level,
        )
    except CLIConfigurationError as exc:
        sys.stderr.write(f"un-comtrade: configuration error: {exc}\n")
        return EXIT_CONFIG_ERROR
    except ConfigurationError as exc:
        sys.stderr.write(f"un-comtrade: configuration error: {exc}\n")
        return EXIT_CONFIG_ERROR

    # Make the configuration available to
    # commands via ``args._cli_configuration``.
    setattr(args, "_cli_configuration", cfg)

    # Resolve the formatter up front. The command
    # body chooses how to apply it, but resolving
    # here gives us a single exit-code mapping.
    fmt_name = args.output_format or "json"
    try:
        get_formatter(fmt_name)
    except KeyError:
        sys.stderr.write(
            f"un-comtrade: unknown output format {fmt_name!r}\n"
        )
        return EXIT_USER_ERROR

    # Dispatch.
    command_name = getattr(args, "command", None)
    if command_name is None:
        command_name = "root"

    try:
        cmd = _resolve_command(command_name)
    except KeyError:
        sys.stderr.write(
            f"un-comtrade: unknown command {command_name!r}. "
            f"Run `un-comtrade --help` for the list.\n"
        )
        return EXIT_USER_ERROR

    try:
        code = cmd(args)
    except AuthenticationError as exc:
        sys.stderr.write(f"un-comtrade: authentication failed: {exc}\n")
        return EXIT_AUTH_ERROR
    except NetworkError as exc:
        sys.stderr.write(f"un-comtrade: network error: {exc}\n")
        return EXIT_NETWORK_ERROR
    except CLIConfigurationError as exc:
        sys.stderr.write(f"un-comtrade: {exc}\n")
        return EXIT_CONFIG_ERROR
    except CLIError as exc:
        sys.stderr.write(f"un-comtrade: {exc}\n")
        return EXIT_USER_ERROR
    except ComtradeError as exc:
        sys.stderr.write(f"un-comtrade: SDK error: {exc}\n")
        return EXIT_GENERIC_ERROR
    except KeyboardInterrupt:
        sys.stderr.write("\nun-comtrade: interrupted\n")
        return EXIT_GENERIC_ERROR

    if code is None:
        return EXIT_OK
    try:
        return int(code)
    except (TypeError, ValueError):
        return EXIT_GENERIC_ERROR


def _resolve_command(name: str):
    """Internal helper: look up a command and
    raise ``KeyError`` if unknown.
    """
    cmd = get_command(name)
    if cmd is None:
        raise KeyError(name)
    return cmd


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())