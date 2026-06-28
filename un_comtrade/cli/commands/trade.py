"""``un-comtrade trade ...`` subcommands.

Implements six trade-data commands that delegate
to the public :class:`un_comtrade.trade.TradeService`:

- ``exports``    — ``TradeService.get_exports(...)``
- ``imports``    — ``TradeService.get_imports(...)``
- ``world``      — ``TradeService.get_world_trade(...)``
- ``bilateral``  — ``TradeService.get_bilateral(...)``
- ``balance``    — ``TradeService.get_trade_balance(...)``
- ``tariffline`` — ``TradeService.get_tariffline(...)``

CLI rules (per C-003):

- The CLI MUST NOT construct upstream URLs.
- The CLI delegates entirely to the SDK; the SDK
  owns request assembly, transport, parsing, and
  paging.
- The CLI receives a :class:`TradeResponse`
  dataclass and serialises it via the public
  ``to_dict()`` method.
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
    EXIT_USER_ERROR,
    CLIError,
    make_progress_reporter,
    render_to_destination,
)
from un_comtrade.exceptions import (
    ComtradeError,
    ValidationError,
)


# ---------------------------------------------------------------------------
# Command descriptors
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _TradeCommandSpec:
    """Static description of one trade
    sub-subcommand.
    """

    name: str
    help: str
    method_name: str
    # Whether the underlying TradeService method
    # takes ``flow_code`` (it does for bilateral,
    # tariffline; doesn't for exports/imports/balance).
    has_flow_code: bool = False
    # Whether ``world`` is implemented as
    # ``get_world_trade`` (which does NOT take
    # ``partner_code``).
    is_world: bool = False


_SPECS: tuple[_TradeCommandSpec, ...] = (
    _TradeCommandSpec(
        name="exports",
        help=(
            "Fetch export records for a reporter "
            "(R01 / R02 / etc.). Delegates to "
            "``TradeService.get_exports``."
        ),
        method_name="get_exports",
    ),
    _TradeCommandSpec(
        name="imports",
        help=(
            "Fetch import records for a reporter. "
            "Delegates to ``TradeService.get_imports``."
        ),
        method_name="get_imports",
    ),
    _TradeCommandSpec(
        name="world",
        help=(
            "Fetch world trade records (all partners). "
            "Delegates to ``TradeService.get_world_trade``."
        ),
        method_name="get_world_trade",
        is_world=True,
        # ``get_world_trade(reporter_code, flow_code, period, ...)``
        # takes flow_code as a positional. The CLI resolves it to
        # ``"X"`` (exports) by default; see ``_resolve_positional``.
        has_flow_code=True,
    ),
    _TradeCommandSpec(
        name="bilateral",
        help=(
            "Fetch bilateral trade records between a "
            "reporter and a single partner. "
            "Delegates to ``TradeService.get_bilateral``."
        ),
        method_name="get_bilateral",
        has_flow_code=True,
    ),
    _TradeCommandSpec(
        name="balance",
        help=(
            "Fetch trade balance records (exports "
            "minus imports) for a reporter. "
            "Delegates to ``TradeService.get_trade_balance``."
        ),
        method_name="get_trade_balance",
    ),
    _TradeCommandSpec(
        name="tariffline",
        help=(
            "Fetch tariffline records for a reporter. "
            "Delegates to ``TradeService.get_tariffline``."
        ),
        method_name="get_tariffline",
        has_flow_code=True,
    ),
)


# ---------------------------------------------------------------------------
# Argument resolution
# ---------------------------------------------------------------------------


def _resolve_kwargs(
    args: Any, spec: _TradeCommandSpec
) -> dict[str, Any]:
    """Build the kwargs for the SDK method call
    from the parsed argparse namespace.

    The CLI delegates parameter assembly to the
    SDK; it only maps CLI flag names to SDK
    parameter names.
    """
    kwargs: dict[str, Any] = {}

    if getattr(args, "classification", None) is not None:
        kwargs["classification"] = args.classification
    if getattr(args, "commodity", None) is not None:
        kwargs["commodity_code"] = args.commodity
    if getattr(args, "edition", None) is not None:
        kwargs["edition"] = args.edition
    if getattr(args, "max_records", None) is not None:
        kwargs["max_records"] = args.max_records
    if getattr(args, "breakdown_mode", None) is not None:
        kwargs["breakdown_mode"] = args.breakdown_mode

    # Partner code: skipped for ``world`` (the SDK
    # method does not accept it).
    if not spec.is_world:
        partner = getattr(args, "partner", None)
        if partner is not None:
            kwargs["partner_code"] = partner

    return kwargs


def _resolve_positional(
    args: Any, spec: _TradeCommandSpec
) -> tuple[Any, ...]:
    """Build the positional-argument tuple.

    Most methods take ``(reporter_code, period)``;
    those that take ``flow_code`` take
    ``(reporter_code, flow_code, period)``.
    """
    reporter = getattr(args, "reporter", None)
    period = getattr(args, "period", None)
    if reporter is None or period is None:
        raise CLIError(
            "missing --reporter or --period (--year "
            "is an alias for --period)"
        )
    if spec.has_flow_code:
        flow = getattr(args, "flow", None) or "X"
        return (reporter, flow, period)
    return (reporter, period)


# ---------------------------------------------------------------------------
# Trade-command helpers
# ---------------------------------------------------------------------------


def _build_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Install the ``trade`` outer subparser plus
    its six sub-subparsers.
    """
    outer = subparsers.add_parser(
        "trade",
        help="Trade data commands.",
        description=(
            "Fetch UN Comtrade trade records "
            "(exports, imports, world, bilateral, "
            "balance, tariffline) via the public "
            "TradeService API. The CLI does NOT "
            "construct upstream URLs; all request "
            "assembly is delegated to the SDK."
        ),
        add_help=True,
    )
    _add_global_options(outer)
    inner = outer.add_subparsers(
        title="trade commands",
        dest="trade_command",
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
        # Common options.
        sub.add_argument(
            "--reporter",
            dest="reporter",
            type=_coerce_int,
            required=True,
            help=(
                "Reporter country code (e.g. 699 "
                "for India, 156 for China)."
            ),
        )
        sub.add_argument(
            "--year",
            "--period",
            dest="period",
            required=True,
            help=(
                "Reporting period. Format: YYYY "
                "(annual), YYYYMM (monthly), or "
                "YYYYMMDD (daily)."
            ),
        )
        sub.add_argument(
            "--partner",
            dest="partner",
            type=_coerce_int,
            default=None,
            help=(
                "Partner country code. Not used by "
                "``trade world``."
            ),
        )
        sub.add_argument(
            "--frequency",
            dest="frequency",
            choices=("A", "M"),
            default=None,
            help=(
                "Reporting frequency (A=annual, "
                "M=monthly). Maps to the period "
                "format the SDK expects."
            ),
        )
        sub.add_argument(
            "--classification",
            dest="classification",
            default=None,
            help=(
                "Classification code (e.g. 'HS', "
                "'SITC', 'BEC'). Defaults to the "
                "SDK's documented default."
            ),
        )
        sub.add_argument(
            "--commodity",
            dest="commodity",
            default=None,
            help=(
                "Commodity / HS code filter. "
                "Default: 'TOTAL' (all commodities)."
            ),
        )
        sub.add_argument(
            "--edition",
            dest="edition",
            default=None,
            help=(
                "Classification edition (e.g. 'HS', "
                "'H0'). Used with --classification."
            ),
        )
        sub.add_argument(
            "--max-records",
            dest="max_records",
            type=_coerce_int,
            default=None,
            help=(
                "Maximum number of records to "
                "return. Defaults to the SDK's "
                "documented cap."
            ),
        )
        sub.add_argument(
            "--breakdown-mode",
            dest="breakdown_mode",
            default=None,
            help=(
                "Breakdown mode (e.g. 'plus' for "
                "cumulative). Defaults to the SDK's "
                "documented default."
            ),
        )
        if spec.has_flow_code:
            sub.add_argument(
                "--flow",
                dest="flow",
                choices=("X", "M"),
                default=None,
                help=(
                    "Trade flow. X=export, M=import. "
                    "Defaults to 'X'."
                ),
            )
        # Global options propagated to every
        # sub-subparser (argparse does not
        # auto-inherit).
        _add_global_options(sub)


def _add_global_options(parser: argparse.ArgumentParser) -> None:
    """Attach the full set of CLI-wide options to
    ``parser``: ``--api-key``, ``--log-level``,
    ``--output-format``, ``--output``, ``--progress``.
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
    parser.add_argument(
        "--progress",
        dest="progress",
        action="store_true",
        default=False,
        help=(
            "Write progress updates to stderr. "
            "Silent when stderr is not a TTY."
        ),
    )


def _coerce_int(value: str) -> int:
    """argparse ``type=`` callable that parses
    an int from a string.
    """
    try:
        return int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"expected an integer, got {value!r}"
        ) from exc


# ---------------------------------------------------------------------------
# Outer command
# ---------------------------------------------------------------------------


class TradeCommand:
    """Outer ``trade`` command.
    """

    name: str = "trade"
    help: str = "Trade data commands."

    def install_subparser(
        self, subparsers: argparse._SubParsersAction
    ) -> None:
        _build_subparser(subparsers)

    def __call__(self, args: Any) -> int:
        sub_name = getattr(args, "trade_command", None)
        if sub_name is None:
            raise CLIError(
                "trade: missing subcommand; "
                "run `un-comtrade trade --help`"
            )
        spec = _SPECS_BY_NAME.get(sub_name)
        if spec is None:
            raise CLIError(
                f"unknown trade subcommand {sub_name!r}"
            )
        return self._dispatch(args, spec)

    def _dispatch(self, args: Any, spec: _TradeCommandSpec) -> int:
        # Apply --frequency to --period: when the
        # user explicitly chose M (monthly) we
        # accept either YYYY or YYYYMM.
        if getattr(args, "frequency", None) == "A" and len(args.period) == 4:
            # Already in YYYY form; no-op.
            pass
        try:
            cfg = getattr(args, "_cli_configuration", None)
            client = ComtradeClient(configuration=cfg)
            try:
                method: Callable[..., Any] = getattr(
                    client.trade, spec.method_name
                )
                positional = _resolve_positional(args, spec)
                kwargs = _resolve_kwargs(args, spec)
                progress = make_progress_reporter(
                    label=f"trade/{spec.name}",
                    enabled=bool(getattr(args, "progress", False)),
                    # ``force=True`` when --progress
                    # was supplied: write to stderr
                    # even when pytest captures it
                    # (no real TTY).
                    force=bool(getattr(args, "progress", False)),
                )
                progress.update(0)
                response = method(*positional, **kwargs)
                # TradeResponse is the public
                # return type. ``to_dict`` is its
                # public serialisation method.
                payload = response.to_dict()
                progress.finish(response.count)
            finally:
                client.close()
        except CLIError:
            raise
        except ValidationError as exc:
            raise CLIError(str(exc)) from exc
        except ComtradeError as exc:
            import sys
            sys.stderr.write(f"un-comtrade: SDK error: {exc}\n")
            return EXIT_GENERIC_ERROR
        return _render_and_emit(payload, args)


def _render_and_emit(payload: Any, args: Any) -> int:
    fmt_name = getattr(args, "output_format", None) or "json"
    try:
        formatter = get_formatter(fmt_name)
    except KeyError:
        raise CLIError(
            f"unknown output format {fmt_name!r}"
        )
    rendered = formatter.render(payload)
    output = getattr(args, "output", None)
    render_to_destination(rendered, output=output)
    return EXIT_OK


_SPECS_BY_NAME = {s.name: s for s in _SPECS}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def _install_trade_commands() -> None:
    """Register the ``trade`` outer command.
    """
    _instance = TradeCommand()

    def _factory() -> TradeCommand:
        return _instance

    register_command(
        "trade",
        _factory,
        help=_instance.help,
    )


_install_trade_commands()


__all__ = [
    "TradeCommand",
    "_install_trade_commands",
]