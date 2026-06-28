"""``un-comtrade analytics ...`` subcommands.

Implements six analytics outer commands. Each
delegates ENTIRELY to the public
:mod:`un_comtrade.analytics` surface — the CLI
performs no analytics logic of its own.

The CLI loads a :class:`CanonicalDataset` via
the public Storage layer, calls the
corresponding public analytics function, and
serialises the result.

Mapping:

- ``analytics country summary`` →
  ``country.country_summary(dataset, reporter_code)``
- ``analytics partner top`` →
  ``partner.top_partners(dataset, reporter_code=...)``
- ``analytics commodity top-hs`` →
  ``commodity.top_hs_codes(dataset, ...)``
- ``analytics trend annual`` →
  ``timeseries.annual_trend(dataset, ...)``
- ``analytics balance country`` →
  ``balance.country_balance(dataset, ...)``
- ``analytics compare country-vs-country`` →
  ``compare.country_vs_country(dataset, reporter_codes=[...])``
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

import un_comtrade
from un_comtrade.cli.commands import register_command
from un_comtrade.cli.formatting import get_formatter
from un_comtrade.cli.utils import (
    EXIT_GENERIC_ERROR,
    EXIT_OK,
    EXIT_USER_ERROR,
    CLIError,
    load_dataset,
    render_to_destination,
)
from un_comtrade.exceptions import ComtradeError


# ---------------------------------------------------------------------------
# Command descriptors
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _AnalyticsCommandSpec:
    """Static description of one analytics outer
    command (each with one representative
    sub-subcommand).

    The CLI carries the entire flag set in
    :attr:`cli_flags` so the parser-build step
    can register them programmatically. Each
    flag has a ``(name, kwargs)`` shape; the
    builder maps ``str`` to ``int`` for
    ``--reporter`` / ``--partner`` etc. via the
    parser's ``type=`` callable.

    ``param_name`` (optional) overrides the SDK
    keyword-argument name. By default the CLI
    forwards the argparse ``dest`` value as the
    keyword-argument name.
    """

    name: str
    help: str
    method_name: str
    # Public submodule path inside
    # ``un_comtrade.analytics`` — e.g.
    # ``"un_comtrade.analytics.country"``.
    module_path: str
    # CLI flag spec: list of ``(dest, kwargs)``
    # tuples. The builder adds the standard
    # ``--dataset`` flag and the global
    # ``--output-format`` / ``--output`` flags
    # automatically.
    cli_flags: tuple[dict[str, Any], ...] = ()
    # Whether the command requires ``--dataset``.
    # Always True for analytics.
    requires_dataset: bool = True
    # Map of argparse dest → SDK kwarg name. When
    # omitted, the dest is used as-is.
    param_name: dict[str, str] = field(
        default_factory=dict
    )


_SPECS: tuple[_AnalyticsCommandSpec, ...] = (
    _AnalyticsCommandSpec(
        name="country",
        help=(
            "Country-level analytics. Subcommand: "
            "``summary`` — delegates to "
            "``country.country_summary``."
        ),
        method_name="summary",
        module_path="un_comtrade.analytics.country",
        cli_flags=(
            {
                "name": "--reporter",
                "dest": "reporter",
                "type": int,
                "required": True,
                "help": (
                    "Reporter country code (e.g. "
                    "699 for India)."
                ),
            },
        ),
        param_name={"reporter": "reporter_code"},
    ),
    _AnalyticsCommandSpec(
        name="partner",
        help=(
            "Partner-level analytics. Subcommand: "
            "``top`` — delegates to "
            "``partner.top_partners``."
        ),
        method_name="top",
        module_path="un_comtrade.analytics.partner",
        cli_flags=(
            {
                "name": "--reporter",
                "dest": "reporter",
                "type": int,
                "required": True,
                "help": "Reporter country code.",
            },
            {
                "name": "--flow",
                "dest": "flow",
                "choices": ("X", "M"),
                "default": None,
                "help": "Restrict to exports / imports.",
            },
            {
                "name": "--limit",
                "dest": "limit",
                "type": int,
                "default": None,
                "help": "Limit the number of rows.",
            },
        ),
        param_name={"reporter": "reporter_code"},
    ),
    _AnalyticsCommandSpec(
        name="commodity",
        help=(
            "Commodity / HS analytics. Subcommand: "
            "``top-hs`` — delegates to "
            "``commodity.top_hs_codes``."
        ),
        method_name="top_hs",
        module_path="un_comtrade.analytics.commodity",
        cli_flags=(
            {
                "name": "--reporter",
                "dest": "reporter",
                "type": int,
                "default": None,
                "help": "Restrict to a reporter.",
            },
            {
                "name": "--flow",
                "dest": "flow",
                "choices": ("X", "M"),
                "default": None,
                "help": "Restrict to exports / imports.",
            },
            {
                "name": "--limit",
                "dest": "limit",
                "type": int,
                "default": None,
                "help": "Limit the number of rows.",
            },
        ),
        param_name={"reporter": "reporter_code"},
    ),
    _AnalyticsCommandSpec(
        name="trend",
        help=(
            "Time-series analytics. Subcommand: "
            "``annual`` — delegates to "
            "``timeseries.annual_trend``."
        ),
        method_name="annual",
        module_path="un_comtrade.analytics.timeseries",
        cli_flags=(
            {
                "name": "--reporter",
                "dest": "reporter",
                "type": int,
                "default": None,
                "help": "Restrict to a reporter.",
            },
            {
                "name": "--flow",
                "dest": "flow",
                "choices": ("X", "M"),
                "default": None,
                "help": "Restrict to exports / imports.",
            },
            {
                "name": "--partner",
                "dest": "partner",
                "type": int,
                "default": None,
                "help": "Restrict to a partner.",
            },
        ),
        param_name={
            "reporter": "reporter_code",
            "partner": "partner_code",
        },
    ),
    _AnalyticsCommandSpec(
        name="balance",
        help=(
            "Trade-balance analytics. Subcommand: "
            "``country`` — delegates to "
            "``balance.country_balance``."
        ),
        method_name="country",
        module_path="un_comtrade.analytics.balance",
        cli_flags=(
            {
                "name": "--reporter",
                "dest": "reporter",
                "type": int,
                "default": None,
                "help": "Restrict to a reporter.",
            },
            {
                "name": "--limit",
                "dest": "limit",
                "type": int,
                "default": None,
                "help": "Limit the number of rows.",
            },
        ),
        param_name={"reporter": "reporter_code"},
    ),
    _AnalyticsCommandSpec(
        name="compare",
        help=(
            "Comparative analytics. Subcommand: "
            "``country-vs-country`` — delegates to "
            "``compare.country_vs_country``."
        ),
        method_name="country_vs_country",
        module_path="un_comtrade.analytics.compare",
        cli_flags=(
            {
                "name": "--reporter",
                "dest": "reporters",
                "type": int,
                "nargs": "+",
                "required": True,
                "help": (
                    "Two or more reporter codes "
                    "(space-separated). The first "
                    "is the baseline."
                ),
            },
            {
                "name": "--breakdown-by",
                "dest": "breakdown_by",
                "choices": ("commodity", "partner", "period"),
                "default": "commodity",
                "help": "Group-by dimension.",
            },
        ),
        param_name={"reporters": "reporter_codes"},
    ),
)


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------


def _add_global_options(parser: argparse.ArgumentParser) -> None:
    """Attach the full set of CLI-wide options to
    ``parser``.
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
            "format. Default: json."
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
    """Install the ``analytics`` outer subparser
    plus its six sub-subparsers.
    """
    outer = subparsers.add_parser(
        "analytics",
        help="Analytics commands.",
        description=(
            "Run analytics over a previously-"
            "stored dataset via the public "
            "``un_comtrade.analytics`` API. The "
            "CLI performs no analytics logic of "
            "its own; everything delegates."
        ),
        add_help=True,
    )
    _add_global_options(outer)
    inner = outer.add_subparsers(
        title="analytics commands",
        dest="analytics_command",
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
        # Every analytics command requires
        # ``--dataset PATH``.
        sub.add_argument(
            "--dataset",
            dest="dataset",
            required=True,
            help=(
                "Path to a previously-stored "
                "CanonicalDataset. Format is "
                "auto-detected from the file "
                "extension (.csv, .json, .parquet, "
                ".duckdb)."
            ),
        )
        # Subcommand-specific flags.
        for flag_spec in spec.cli_flags:
            kwargs = {
                k: v for k, v in flag_spec.items()
                if k != "name"
            }
            sub.add_argument(flag_spec["name"], **kwargs)
        # Global flags.
        _add_global_options(sub)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def _resolve_kwargs(
    args: Any, spec: _AnalyticsCommandSpec
) -> dict[str, Any]:
    """Build the kwargs dict from the parsed
    argparse namespace. Only NON-None values are
    forwarded (the public API treats ``None`` as
    'use default').

    The SDK kwarg name may differ from the CLI
    argparse ``dest``; ``spec.param_name`` is the
    mapping (``{"reporter": "reporter_code"}``).
    """
    result: dict[str, Any] = {}
    for flag_spec in spec.cli_flags:
        dest = flag_spec["dest"]
        value = getattr(args, dest, None)
        if value is None:
            continue
        # Look up the SDK kwarg name.
        sdk_kw = spec.param_name.get(dest, dest)
        result[sdk_kw] = value
    return result


def _resolve_positional(
    args: Any, spec: _AnalyticsCommandSpec
) -> tuple[Any, ...]:
    """Most analytics functions take only keyword
    arguments; ``country_summary`` is the one
    exception in this set (it takes
    ``(dataset, reporter_code)``).

    All kwargs including ``reporter_code`` are
    forwarded by :func:`_resolve_kwargs` (with the
    ``param_name`` mapping), so this helper returns
    an empty tuple for every spec — including
    ``summary``. The CLI never passes reporter
    positionally; the SDK signature binds the
    kwarg unambiguously to ``reporter_code``.
    """
    return ()


def _stderr_write(msg: str) -> None:
    import sys
    sys.stderr.write(msg)


def _render_and_emit(value: Any, args: Any) -> int:
    fmt_name = getattr(args, "output_format", None) or "json"
    try:
        formatter = get_formatter(fmt_name)
    except KeyError:
        raise CLIError(
            f"unknown output format {fmt_name!r}"
        )
    rendered = formatter.render(value)
    output = getattr(args, "output", None)
    render_to_destination(rendered, output=output)
    return EXIT_OK


# ---------------------------------------------------------------------------
# Outer command
# ---------------------------------------------------------------------------


class AnalyticsCommand:
    """Outer ``analytics`` command.
    """

    name: str = "analytics"
    help: str = "Analytics commands."

    def install_subparser(
        self, subparsers: argparse._SubParsersAction
    ) -> None:
        _build_subparser(subparsers)

    def __call__(self, args: Any) -> int:
        sub_name = getattr(args, "analytics_command", None)
        if sub_name is None:
            raise CLIError(
                "analytics: missing subcommand; "
                "run `un-comtrade analytics --help`"
            )
        spec = _SPECS_BY_NAME.get(sub_name)
        if spec is None:
            raise CLIError(
                f"unknown analytics subcommand {sub_name!r}"
            )
        return self._dispatch(args, spec)

    def _dispatch(self, args: Any, spec: _AnalyticsCommandSpec) -> int:
        # 1. Load the dataset via the public
        #    Storage layer (StorageRegistry ->
        #    backend.read(config)).
        try:
            dataset = load_dataset(args.dataset)
        except CLIError:
            raise
        except Exception as exc:
            raise CLIError(
                f"failed to load dataset {args.dataset}: {exc}"
            ) from exc
        # 2. Import the analytics submodule
        #    dynamically; the CLI carries no
        #    analytics logic of its own.
        try:
            import importlib
            mod = importlib.import_module(spec.module_path)
            method = getattr(mod, _SPEC_METHODS[spec.method_name])
        except (ImportError, AttributeError) as exc:
            raise CLIError(
                f"failed to import analytics function "
                f"{spec.module_path}.{spec.method_name}: {exc}"
            ) from exc
        # 3. Build the call.
        try:
            positional = _resolve_positional(args, spec)
            kwargs = _resolve_kwargs(args, spec)
            return _render_and_emit(
                method(dataset, *positional, **kwargs),
                args,
            )
        except CLIError:
            raise
        except ComtradeError as exc:
            _stderr_write(f"un-comtrade: SDK error: {exc}\n")
            return EXIT_GENERIC_ERROR


#: Mapping from ``spec.method_name`` (the CLI
#: subcommand suffix) to the **public** function
#: name on the analytics submodule. The CLI
#: short-names these; the SDK functions keep
#: their descriptive names.
_SPEC_METHODS = {
    "summary": "country_summary",
    "top": "top_partners",
    "top_hs": "top_hs_codes",
    "annual": "annual_trend",
    "country": "country_balance",
    "country_vs_country": "country_vs_country",
}


_SPECS_BY_NAME = {s.name: s for s in _SPECS}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def _install_analytics_commands() -> None:
    """Register the ``analytics`` outer command.
    """
    _instance = AnalyticsCommand()

    def _factory() -> AnalyticsCommand:
        return _instance

    register_command(
        "analytics",
        _factory,
        help=_instance.help,
    )


_install_analytics_commands()


__all__ = [
    "AnalyticsCommand",
    "_install_analytics_commands",
]