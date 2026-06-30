"""CLI subcommand registry.

Foundation phase: this module exposes the
:class:`Command` Protocol and a registry that
:func:`un_comtrade.cli.main._build_parser` uses
to install subparsers.

The foundation ships ZERO business commands.
P7-002+ will register metadata, trade, storage,
ETL, and analytics commands here.

Public surface:

- :class:`Command` (protocol)
- :func:`register_command`
- :func:`iter_commands`
- :func:`get_command`
"""


from __future__ import annotations

from typing import (
    Any,
    Callable,
    Iterator,
    Mapping,
    Protocol,
    runtime_checkable,
)


@runtime_checkable
class Command(Protocol):
    """Protocol every CLI subcommand must implement.

    A command is a callable that receives the
    parsed argparse namespace and returns an exit
    code (``int``).

    Attributes
    ----------
    name
        The subcommand name as it appears on the
        command line (e.g. ``"metadata"``).
    help
        Short help text shown in the parent
        parser's help output.

    Optional Methods
    ----------------
    install_subparser(subparsers)
        Commands that own nested sub-subcommands
        (e.g. ``metadata``) implement this to add
        their own subparser tree to the parent
        subparsers action. The default top-level
        single-command case does NOT implement
        this — :func:`un_comtrade.cli.main.build_parser`
        adds a flat subparser for it instead.
    """

    name: str
    help: str

    def __call__(self, args: Any) -> int: ...


#: Internal registry: name -> command factory.
#: Factories are zero-arg callables returning a
#: :class:`Command` instance; this indirection
#: keeps registration cheap (no instantiation at
#: import time).
_FACTORIES: dict[str, Callable[[], Command]] = {}


def register_command(
    name: str,
    factory: Callable[[], Command],
    *,
    help: str = "",
) -> None:
    """Register a command factory under ``name``.

    Re-registering an existing name overwrites the
    previous factory. The CLI uses this on startup
    to install business commands.
    """
    _FACTORIES[name] = factory
    # `help` is stashed on the factory's closure
    # for introspection; the protocol's `help`
    # attribute is set when the factory is invoked.
    if help:
        factory.__doc__ = help


def iter_commands() -> Iterator[tuple[str, Callable[[], Command]]]:
    """Yield ``(name, factory)`` pairs in
    insertion order.
    """
    for name, factory in _FACTORIES.items():
        yield name, factory


def get_command(name: str) -> Command | None:
    """Return the registered :class:`Command` for
    ``name``, or ``None`` if not registered.
    """
    factory = _FACTORIES.get(name)
    if factory is None:
        return None
    return factory()


def known_command_names() -> tuple[str, ...]:
    """Return the sorted tuple of registered
    command names. Used by ``--help`` to render
    the available-subcommands section.
    """
    return tuple(sorted(_FACTORIES.keys()))


def reset_registry() -> None:
    """Clear the registry. Tests use this to keep
    command-registration state from leaking
    between cases.
    """
    _FACTORIES.clear()


__all__ = [
    "Command",
    "get_command",
    "iter_commands",
    "known_command_names",
    "register_command",
    "reset_registry",
]