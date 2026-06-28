"""``un-comtrade storage ...`` subcommands.

Implements four storage-write sub-subcommands.
Each delegates to the corresponding public
storage backend:

- ``storage parquet`` — ``ParquetWriter().store``
- ``storage csv``     — ``CSVWriter().store``
- ``storage json``    — ``JSONWriter().store``
- ``storage duckdb``  — ``DuckDBWriter().store``

The CLI does NOT implement storage; every
command body constructs a
:class:`StorageConfig`, instantiates the
corresponding writer, and calls ``store(...)``.
The writer is registered in the public
``StorageRegistry`` so the lookup is
configurable (e.g. for custom backends).

The dataset is loaded via the public Storage
layer's ``read()`` path (``load_dataset``
helper) — the same path analytics commands use.
This means the CLI round-trips a stored
dataset into another format without ever
opening the file itself.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import Any

import un_comtrade
from un_comtrade.cli.commands import register_command
from un_comtrade.cli.formatting import get_formatter
from un_comtrade.cli.utils import (
    EXIT_GENERIC_ERROR,
    EXIT_OK,
    CLIError,
    load_dataset,
    render_to_destination,
)
from un_comtrade.exceptions import ComtradeError
from un_comtrade.storage import (
    StorageBackend,
    StorageConfig,
    StorageRegistry,
    StorageResult,
)


# ---------------------------------------------------------------------------
# Command descriptors
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _StorageCommandSpec:
    """Static description of one storage-write
    sub-subcommand.
    """

    name: str
    help: str
    backend: StorageBackend
    # Optional writer-class import path so the
    # CLI can instantiate the backend directly
    # (avoids a second registry round-trip when
    # we want the concrete class).
    writer_path: str | None = None


_SPECS: tuple[_StorageCommandSpec, ...] = (
    _StorageCommandSpec(
        name="parquet",
        help=(
            "Persist a dataset to a Parquet file "
            "(via the public ParquetWriter)."
        ),
        backend=StorageBackend.PARQUET,
        writer_path="un_comtrade.storage.parquet.ParquetWriter",
    ),
    _StorageCommandSpec(
        name="csv",
        help=(
            "Persist a dataset to a CSV file "
            "(via the public CSVWriter)."
        ),
        backend=StorageBackend.CSV,
        writer_path="un_comtrade.storage.file.CSVWriter",
    ),
    _StorageCommandSpec(
        name="json",
        help=(
            "Persist a dataset to a JSON file "
            "(via the public JSONWriter)."
        ),
        backend=StorageBackend.JSON,
        writer_path="un_comtrade.storage.file.JSONWriter",
    ),
    _StorageCommandSpec(
        name="duckdb",
        help=(
            "Persist a dataset to a DuckDB file "
            "(via the public DuckDBWriter)."
        ),
        backend=StorageBackend.DUCKDB,
        writer_path="un_comtrade.storage.duckdb.DuckDBWriter",
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
    """Install the ``storage`` outer subparser
    plus its four sub-subparsers.
    """
    outer = subparsers.add_parser(
        "storage",
        help="Storage commands.",
        description=(
            "Persist datasets via the public "
            "Storage layer. The CLI orchestrates "
            "the write; the SDK does the work."
        ),
        add_help=True,
    )
    _add_global_options(outer)
    inner = outer.add_subparsers(
        title="storage commands",
        dest="storage_command",
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
        sub.add_argument(
            "--dataset",
            dest="dataset",
            required=True,
            help=(
                "Path to a stored dataset to read. "
                "Format is auto-detected from the "
                "file extension or directory contents."
            ),
        )
        sub.add_argument(
            "--output-path",
            dest="output_path",
            required=True,
            help=(
                "Destination path for the new "
                "store. Format matches the "
                "subcommand (e.g. ``--output-path "
                "data.parquet`` for the parquet "
                "subcommand)."
            ),
        )
        sub.add_argument(
            "--overwrite",
            dest="overwrite",
            action="store_true",
            default=False,
            help="Overwrite the destination if it exists.",
        )
        sub.add_argument(
            "--table-name",
            dest="table_name",
            default="trade_records",
            help=(
                "Table name (DuckDB only). Default: "
                "``trade_records``."
            ),
        )
        _add_global_options(sub)


# ---------------------------------------------------------------------------
# Dispatch helpers
# ---------------------------------------------------------------------------


def _stderr_write(msg: str) -> None:
    import sys
    sys.stderr.write(msg)


def _render_and_emit(result: StorageResult, args: Any) -> int:
    fmt_name = getattr(args, "output_format", None) or "json"
    try:
        formatter = get_formatter(fmt_name)
    except KeyError:
        raise CLIError(
            f"unknown output format {fmt_name!r}"
        )
    payload = {
        "backend": result.backend.value,
        "destination": result.destination,
        "record_count": result.metadata.record_count,
        "byte_size": result.byte_size,
        "stored_at": (
            result.metadata.stored_at.isoformat()
            if result.metadata.stored_at is not None
            else None
        ),
        "partition_keys": [
            list(k) for k in result.metadata.partition_keys
        ],
    }
    rendered = formatter.render(payload)
    output = getattr(args, "output", None)
    render_to_destination(rendered, output=output)
    return EXIT_OK


def _build_writer(spec: _StorageCommandSpec):
    """Import and instantiate the writer class
    named by ``spec.writer_path``.

    Direct instantiation (rather than
    ``StorageRegistry.get(spec.backend)``) keeps
    the CLI close to the public writer class and
    matches how the tests will patch the SDK
    surface.
    """
    if spec.writer_path is None:
        raise CLIError(
            f"storage command {spec.name!r} has no "
            f"writer_path configured"
        )
    module_path, _, class_name = spec.writer_path.rpartition(".")
    import importlib

    try:
        mod = importlib.import_module(module_path)
    except ImportError as exc:
        raise CLIError(
            f"could not import writer module "
            f"{module_path!r}: {exc}. Install the "
            f"required optional dependency."
        ) from exc
    cls = getattr(mod, class_name, None)
    if cls is None:
        raise CLIError(
            f"writer class {class_name!r} not found "
            f"in module {module_path!r}"
        )
    return cls()


# ---------------------------------------------------------------------------
# Outer command
# ---------------------------------------------------------------------------


class StorageCommand:
    """Outer ``storage`` command.
    """

    name: str = "storage"
    help: str = "Storage commands."

    def install_subparser(
        self, subparsers: argparse._SubParsersAction
    ) -> None:
        _build_subparser(subparsers)

    def __call__(self, args: Any) -> int:
        sub_name = getattr(args, "storage_command", None)
        if sub_name is None:
            raise CLIError(
                "storage: missing subcommand; "
                "run `un-comtrade storage --help`"
            )
        spec = _SPECS_BY_NAME.get(sub_name)
        if spec is None:
            raise CLIError(
                f"unknown storage subcommand {sub_name!r}"
            )
        return self._dispatch(args, spec)

    def _dispatch(self, args: Any, spec: _StorageCommandSpec) -> int:
        # 1. Load the dataset via the public
        #    Storage layer (analytics-style).
        try:
            dataset = load_dataset(args.dataset)
        except CLIError:
            raise
        except Exception as exc:
            raise CLIError(
                f"failed to load dataset {args.dataset}: {exc}"
            ) from exc
        # 2. Construct the writer (the public
        #    ``un_comtrade.storage.<backend>``
        #    writer class).
        writer = _build_writer(spec)
        # 3. Build the public ``StorageConfig``.
        config = StorageConfig(
            root=args.output_path,
            overwrite=bool(getattr(args, "overwrite", False)),
            table_name=getattr(args, "table_name", None)
            or "trade_records",
        )
        # 4. Delegate the write to the SDK.
        try:
            result: StorageResult = writer.store(dataset, config)
        except CLIError:
            raise
        except ComtradeError as exc:
            _stderr_write(f"un-comtrade: SDK error: {exc}\n")
            return EXIT_GENERIC_ERROR
        return _render_and_emit(result, args)


_SPECS_BY_NAME = {s.name: s for s in _SPECS}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def _install_storage_commands() -> None:
    _instance = StorageCommand()

    def _factory() -> StorageCommand:
        return _instance

    register_command(
        "storage",
        _factory,
        help=_instance.help,
    )


_install_storage_commands()


__all__ = [
    "StorageCommand",
    "_install_storage_commands",
]