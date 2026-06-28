"""``un-comtrade etl run`` command.

The CLI orchestrates an ETL pipeline by:

1. Loading a JSON pipeline configuration from
   ``--pipeline-config PATH``.
2. Building the public
   :class:`un_comtrade.etl.ETLPipeline` from the
   configuration.
3. Calling :meth:`ETLPipeline.run` with the
   ``--source`` payload.

The CLI does NOT implement any pipeline
logic — every stage factory is taken verbatim
from the configuration. The CLI is a thin
loader + dispatcher.
"""

from __future__ import annotations

import argparse
import importlib
import json
from typing import Any, Callable

import un_comtrade
from un_comtrade.cli.commands import register_command
from un_comtrade.cli.formatting import get_formatter
from un_comtrade.cli.utils import (
    EXIT_GENERIC_ERROR,
    EXIT_OK,
    CLIConfigurationError,
    CLIError,
    render_to_destination,
)
from un_comtrade.etl import (
    ETLPipeline,
    PipelineResult,
    PipelineStatus,
    StageSpec,
)
from un_comtrade.exceptions import ComtradeError


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------


def _add_global_options(parser: argparse.ArgumentParser) -> None:
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
    outer = subparsers.add_parser(
        "etl",
        help="ETL commands.",
        description=(
            "Run an ETL pipeline via the public "
            "``un_comtrade.etl.ETLPipeline`` API. "
            "The CLI is a thin orchestrator; all "
            "stage logic lives in the pipeline "
            "configuration."
        ),
        add_help=True,
    )
    _add_global_options(outer)
    inner = outer.add_subparsers(
        title="etl commands",
        dest="etl_command",
        metavar="<command>",
        required=True,
    )
    sub = inner.add_parser(
        "run",
        help=(
            "Run a pipeline from a JSON config. "
            "Delegates to ``ETLPipeline.run``."
        ),
        description=(
            "Pipeline configuration JSON shape:\n\n"
            "{\n"
            '  "name": "my-pipeline",\n'
            '  "stages": [\n'
            '    {\n'
            '      "name": "load",\n'
            '      "kind": "extract",\n'
            '      "factory": "my_pkg.factories:build_load_stage"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "``factory`` is a string of the form "
            "``module.path:callable`` which the CLI "
            "imports and invokes to obtain the "
            "stage factory."
        ),
        add_help=True,
    )
    sub.add_argument(
        "--pipeline-config",
        dest="pipeline_config",
        required=True,
        help=(
            "Path to a JSON pipeline configuration "
            "(see ``un-comtrade etl run --help``)."
        ),
    )
    sub.add_argument(
        "--source",
        dest="source",
        default=None,
        help=(
            "Optional source payload (JSON "
            "literal) passed to the first stage. "
            "When omitted, the first stage "
            "receives ``None``."
        ),
    )
    _add_global_options(sub)


# ---------------------------------------------------------------------------
# Pipeline config loader
# ---------------------------------------------------------------------------


def _load_pipeline_config(path: str) -> dict[str, Any]:
    """Read a JSON pipeline config from disk.

    Raises :class:`CLIConfigurationError` on any
    I/O or parse failure.
    """
    import pathlib
    p = pathlib.Path(path)
    if not p.exists():
        raise CLIConfigurationError(
            f"pipeline config does not exist: {p}"
        )
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise CLIConfigurationError(
            f"cannot read pipeline config {p}: {exc}"
        ) from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CLIConfigurationError(
            f"pipeline config {p} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise CLIConfigurationError(
            f"pipeline config {p} must be a JSON "
            f"object (got {type(data).__name__})"
        )
    return data


def _build_pipeline(config: dict[str, Any]) -> ETLPipeline:
    """Construct an :class:`ETLPipeline` from the
    loaded config. Imports each stage factory by
    dotted path and resolves it to a
    :class:`StageSpec`.
    """
    name = config.get("name")
    if not name or not isinstance(name, str):
        raise CLIConfigurationError(
            "pipeline config 'name' must be a non-empty string"
        )
    stages_raw = config.get("stages")
    if not isinstance(stages_raw, list) or not stages_raw:
        raise CLIConfigurationError(
            "pipeline config 'stages' must be a non-empty list"
        )
    from un_comtrade.etl import StageKind

    stage_specs: list[StageSpec] = []
    for i, raw in enumerate(stages_raw):
        if not isinstance(raw, dict):
            raise CLIConfigurationError(
                f"pipeline stages[{i}] must be a JSON object"
            )
        stage_name = raw.get("name")
        stage_kind = raw.get("kind")
        factory_path = raw.get("factory")
        if not stage_name or not isinstance(stage_name, str):
            raise CLIConfigurationError(
                f"pipeline stages[{i}].name must be a "
                f"non-empty string"
            )
        if stage_kind not in {k.value for k in StageKind}:
            raise CLIConfigurationError(
                f"pipeline stages[{i}].kind must be one of "
                f"{sorted(k.value for k in StageKind)}; got "
                f"{stage_kind!r}"
            )
        if not factory_path or not isinstance(factory_path, str):
            raise CLIConfigurationError(
                f"pipeline stages[{i}].factory must be a "
                f"non-empty string of the form "
                f"'module.path:callable'"
            )
        # Import the factory by dotted path.
        factory = _import_dotted(factory_path)
        stage_specs.append(
            StageSpec(
                name=stage_name,
                kind=StageKind(stage_kind),
                factory=factory,
            )
        )
    return ETLPipeline(name=name, stages=tuple(stage_specs))


def _import_dotted(path: str) -> Callable:
    """Import ``module.path:callable`` and return
    the named attribute.

    Raises :class:`CLIConfigurationError` when the
    path is malformed or the import fails.
    """
    if ":" not in path:
        raise CLIConfigurationError(
            f"factory path must be 'module.path:callable'; "
            f"got {path!r}"
        )
    module_path, _, attr = path.partition(":")
    module_path = module_path.strip()
    attr = attr.strip()
    if not module_path or not attr:
        raise CLIConfigurationError(
            f"factory path malformed: {path!r}"
        )
    try:
        mod = importlib.import_module(module_path)
    except ImportError as exc:
        raise CLIConfigurationError(
            f"could not import factory module {module_path!r}: "
            f"{exc}"
        ) from exc
    factory = getattr(mod, attr, None)
    if factory is None:
        raise CLIConfigurationError(
            f"factory {attr!r} not found in module "
            f"{module_path!r}"
        )
    if not callable(factory):
        raise CLIConfigurationError(
            f"factory {path!r} resolved to {type(factory).__name__}; "
            f"expected callable"
        )
    return factory


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def _stderr_write(msg: str) -> None:
    import sys
    sys.stderr.write(msg)


def _render_and_emit(result: PipelineResult, args: Any) -> int:
    fmt_name = getattr(args, "output_format", None) or "json"
    try:
        formatter = get_formatter(fmt_name)
    except KeyError:
        raise CLIError(
            f"unknown output format {fmt_name!r}"
        )
    payload = {
        "pipeline_name": result.pipeline_name,
        "status": result.status.value,
        "records_in": result.records_in,
        "records_out": result.records_out,
        "warnings": list(result.warnings),
        "errors": list(result.errors),
        "stage_durations": dict(result.stage_durations),
        "started_at": (
            result.started_at.isoformat()
            if result.started_at is not None
            else None
        ),
        "finished_at": (
            result.finished_at.isoformat()
            if result.finished_at is not None
            else None
        ),
    }
    rendered = formatter.render(payload)
    output = getattr(args, "output", None)
    render_to_destination(rendered, output=output)
    return EXIT_OK if result.status == PipelineStatus.SUCCESS else EXIT_GENERIC_ERROR


# ---------------------------------------------------------------------------
# Outer command
# ---------------------------------------------------------------------------


class ETLCommand:
    """Outer ``etl`` command.
    """

    name: str = "etl"
    help: str = "ETL commands."

    def install_subparser(
        self, subparsers: argparse._SubParsersAction
    ) -> None:
        _build_subparser(subparsers)

    def __call__(self, args: Any) -> int:
        sub_name = getattr(args, "etl_command", None)
        if sub_name is None:
            raise CLIError(
                "etl: missing subcommand; "
                "run `un-comtrade etl --help`"
            )
        if sub_name != "run":
            raise CLIError(
                f"unknown etl subcommand {sub_name!r}"
            )
        return self._dispatch(args)

    def _dispatch(self, args: Any) -> int:
        # 1. Load the pipeline configuration.
        config = _load_pipeline_config(args.pipeline_config)
        # 2. Build the public ETLPipeline from
        #    the configuration. The CLI does NOT
        #    implement any stage logic — every
        #    factory is imported by dotted path.
        try:
            pipeline = _build_pipeline(config)
        except CLIError:
            raise
        except Exception as exc:
            raise CLIError(
                f"failed to build pipeline: {exc}"
            ) from exc
        # 3. Resolve the source payload.
        source = getattr(args, "source", None)
        if source is not None:
            try:
                source = json.loads(source)
            except json.JSONDecodeError as exc:
                raise CLIError(
                    f"--source is not valid JSON: {exc}"
                ) from exc
        # 4. Delegate to the SDK.
        try:
            result: PipelineResult = pipeline.run(source)
        except ComtradeError as exc:
            _stderr_write(f"un-comtrade: SDK error: {exc}\n")
            return EXIT_GENERIC_ERROR
        return _render_and_emit(result, args)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def _install_etl_commands() -> None:
    _instance = ETLCommand()

    def _factory() -> ETLCommand:
        return _instance

    register_command(
        "etl",
        _factory,
        help=_instance.help,
    )


_install_etl_commands()


__all__ = [
    "ETLCommand",
    "_install_etl_commands",
]