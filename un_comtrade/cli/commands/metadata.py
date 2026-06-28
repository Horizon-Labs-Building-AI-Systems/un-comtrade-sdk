"""``un-comtrade metadata ...`` subcommands.

Implements six list-style commands that fetch
reference catalogues via the public
:mod:`un_comtrade.metadata` API:

- ``countries``       — ``MetadataService.get_countries()``
- ``partners``        — ``MetadataService.get_partners()``
- ``hs``              — ``MetadataService.get_hs_codes(edition)``
- ``classifications`` — ``MetadataService.get_classifications()``
- ``frequencies``     — ``MetadataService.get_frequencies()``
- ``transport-modes`` — ``MetadataService.get_transport_modes()``

The module registers a single ``metadata`` outer
command with the CLI's :mod:`commands` registry.
The outer command builds its own sub-subparser
hierarchy at registration time (see
:func:`_install_metadata_commands`).

All six share the same execution shape:

1. Construct a public
   :class:`un_comtrade.client.ComtradeClient` from
   the configuration the CLI loaded.
2. Call the corresponding list method on
   ``client.metadata``.
3. Render the resulting records with the chosen
   formatter (``--output-format``).
4. Write to ``--output`` or stdout.

Public SDK only — no internal imports.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, Callable

import un_comtrade
from un_comtrade.client import ComtradeClient
from un_comtrade.cli.commands import register_command
from un_comtrade.cli.formatting import get_formatter
from un_comtrade.cli.utils import (
    EXIT_GENERIC_ERROR,
    EXIT_OK,
    CLIError,
    render_to_destination,
)
from un_comtrade.exceptions import (
    ComtradeError,
)


# ---------------------------------------------------------------------------
# Command descriptor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ListCommandSpec:
    """Static description of one metadata list
    sub-subcommand.
    """

    name: str
    help: str
    method_name: str
    # Positional args the SDK method accepts when
    # the user did NOT supply ``--edition``. For
    # ``hs`` this is ``("HS",)``.
    default_args: tuple[str, ...] = ()
    # When ``True`` the sub-subcommand takes an
    # optional ``--edition`` flag. Currently only
    # ``hs`` does.
    has_edition_flag: bool = False


_SPECS: tuple[_ListCommandSpec, ...] = (
    _ListCommandSpec(
        name="countries",
        help=(
            "List all reporter countries (R01). "
            "Equivalent to "
            "``MetadataService.get_countries()``."
        ),
        method_name="get_countries",
    ),
    _ListCommandSpec(
        name="partners",
        help=(
            "List all partner countries (R02). "
            "Equivalent to "
            "``MetadataService.get_partners()``."
        ),
        method_name="get_partners",
    ),
    _ListCommandSpec(
        name="classifications",
        help=(
            "List all classification systems (R03). "
            "Equivalent to "
            "``MetadataService.get_classifications()``."
        ),
        method_name="get_classifications",
    ),
    _ListCommandSpec(
        name="frequencies",
        help=(
            "List all reporting frequencies (R04). "
            "Equivalent to "
            "``MetadataService.get_frequencies()``."
        ),
        method_name="get_frequencies",
    ),
    _ListCommandSpec(
        name="transport-modes",
        help=(
            "List all modes of transport (R12). "
            "Equivalent to "
            "``MetadataService.get_transport_modes()``."
        ),
        method_name="get_transport_modes",
    ),
    _ListCommandSpec(
        name="hs",
        help=(
            "List HS commodity codes for the chosen "
            "edition (R05). Equivalent to "
            "``MetadataService.get_hs_codes(edition)``. "
            "Use ``--edition`` to override the "
            "default (``HS``)."
        ),
        method_name="get_hs_codes",
        default_args=("HS",),
        has_edition_flag=True,
    ),
)


# ---------------------------------------------------------------------------
# Dispatch helpers
# ---------------------------------------------------------------------------


def _add_global_options(parser: argparse.ArgumentParser) -> None:
    """Attach the full set of CLI-wide options to
    ``parser``: ``--api-key``, ``--log-level``,
    ``--output-format``, ``--output``.

    argparse does NOT propagate parent options
    across sub-subparser boundaries, so every
    level that takes these flags must re-attach
    them. ``--output-format`` uses the full
    set of formats declared in
    :data:`un_comtrade.cli.utils.OUTPUT_FORMATS`.
    """
    parser.add_argument(
        "--api-key",
        dest="api_key",
        default=None,
        help="Override the UN_COMTRADE_KEY env var.",
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
        choices=("json", "table", "csv", "markdown", "text"),
        help=(
            "Render command output in the chosen "
            f"format. Default: json. Choices: "
            f"{', '.join(('json','table','csv','markdown','text'))}."
        ),
    )
    parser.add_argument(
        "--output",
        dest="output",
        default=None,
        help=(
            "Write the rendered output to PATH "
            "instead of stdout."
        ),
    )


def _build_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Install the ``metadata`` outer subparser
    plus its six sub-subparsers.

    Called by :func:`un_comtrade.cli.main.build_parser`
    via the registry's introspection.
    """
    outer = subparsers.add_parser(
        "metadata",
        help="Reference catalogue commands.",
        description=(
            "Fetch UN Comtrade reference catalogues "
            "(countries, partners, HS codes, "
            "classifications, frequencies, "
            "transport modes) via the public "
            "MetadataService API."
        ),
        add_help=True,
    )
    # The metadata outer subparser accepts the
    # same global options as the root parser.
    _add_global_options(outer)
    inner = outer.add_subparsers(
        title="metadata commands",
        dest="metadata_command",
        metavar="<command>",
        required=True,
    )
    for spec in _SPECS:
        sub = inner.add_parser(
            spec.name,
            help=spec.help,
            description=spec.help,
            add_help=True,
        )
        # Each sub-subparser also needs the global
        # options because argparse does not
        # propagate parent arguments.
        _add_global_options(sub)
        if spec.has_edition_flag:
            sub.add_argument(
                "--edition",
                dest="edition",
                default=None,
                help=(
                    "HS classification edition (e.g. "
                    "'HS', 'H0', 'H1', ...). Default: "
                    "'HS'."
                ),
            )


def _resolve_args(args: Any, spec: _ListCommandSpec) -> tuple[str, ...]:
    """Build the positional-argument tuple for the
    SDK method call.

    When the user supplied ``--edition`` we use
    that value; otherwise the spec's default
    applies (e.g. ``("HS",)``).
    """
    edition = getattr(args, "edition", None)
    if edition is not None:
        return (edition,)
    return spec.default_args


def _render_and_emit(records: Any, args: Any) -> int:
    """Render ``records`` with the chosen formatter
    and write to ``--output`` (or stdout).

    ``records`` is whatever the SDK returned:
    typically ``list[dataclass]`` but the CLI
    accepts any iterable of records.
    """
    fmt_name = getattr(args, "output_format", None) or "json"
    try:
        formatter = get_formatter(fmt_name)
    except KeyError:
        raise CLIError(
            f"unknown output format {fmt_name!r}"
        )
    rendered = formatter.render(records)
    output = getattr(args, "output", None)
    render_to_destination(rendered, output=output)
    return EXIT_OK


def _stderr_write(msg: str) -> None:
    """Internal helper: write to stderr without
    depending on the :mod:`un_comtrade.cli.main`
    private ``_stderr`` symbol.
    """
    import sys
    sys.stderr.write(msg)


# ---------------------------------------------------------------------------
# Outer command
# ---------------------------------------------------------------------------


class MetadataCommand:
    """Outer ``metadata`` command.

    The CLI registers this single command. Its
    ``__call__`` inspects ``args.metadata_command``
    and dispatches to the right SDK method.
    """

    name: str = "metadata"
    help: str = "Reference catalogue commands."

    def install_subparser(
        self, subparsers: argparse._SubParsersAction
    ) -> None:
        """Install the ``metadata`` subparser tree
        on the given subparsers action.
        """
        _build_subparser(subparsers)

    def __call__(self, args: Any) -> int:
        sub_name = getattr(args, "metadata_command", None)
        if sub_name is None:
            # argparse will only invoke __call__
            # when a sub-subcommand was supplied
            # (we set ``required=True``), so this
            # is defensive.
            raise CLIError(
                "metadata: missing subcommand; "
                "run `un-comtrade metadata --help`"
            )
        spec = _SPECS_BY_NAME.get(sub_name)
        if spec is None:
            raise CLIError(f"unknown metadata subcommand {sub_name!r}")
        return self._dispatch(args, spec)

    def _dispatch(self, args: Any, spec: _ListCommandSpec) -> int:
        try:
            cfg = getattr(args, "_cli_configuration", None)
            client = ComtradeClient(configuration=cfg)
            try:
                method: Callable[..., list[Any]] = getattr(
                    client.metadata, spec.method_name
                )
                positional = _resolve_args(args, spec)
                records = method(*positional)
            finally:
                client.close()
            return _render_and_emit(records, args)
        except CLIError:
            # CLI-level errors (e.g. unknown output
            # format, output-file write failure)
            # MUST propagate to the main dispatcher
            # so it can map to EXIT_CONFIG_ERROR /
            # EXIT_USER_ERROR. Catching them here
            # would shadow the higher-priority
            # mapping.
            raise
        except ComtradeError as exc:
            _stderr_write(f"un-comtrade: SDK error: {exc}\n")
            return EXIT_GENERIC_ERROR


_SPECS_BY_NAME = {s.name: s for s in _SPECS}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def _install_metadata_commands() -> None:
    """Register the ``metadata`` outer command.

    The outer command is one entry in the global
    commands registry. Its sub-subcommands are
    wired up by :meth:`MetadataCommand.install_subparser`,
    which :func:`un_comtrade.cli.main.build_parser`
    calls during subparser construction.
    """
    _instance = MetadataCommand()

    def _factory() -> MetadataCommand:
        return _instance

    register_command(
        "metadata",
        _factory,
        help=_instance.help,
    )


_install_metadata_commands()


__all__ = [
    "MetadataCommand",
    "_install_metadata_commands",
]