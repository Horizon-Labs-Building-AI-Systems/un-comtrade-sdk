"""Output routing for the CLI.

The CLI uses :func:`render_to_destination` to
write the formatted payload to either ``stdout``
or a user-supplied file path (``--output``).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, IO

from un_comtrade.cli.utils.exceptions import CLIConfigurationError


def render_to_destination(
    text: str,
    *,
    output: str | None,
) -> None:
    """Write ``text`` to ``output`` (a file path)
    or to ``stdout`` when ``output`` is ``None``.

    Raises
    ------
    CLIConfigurationError
        When ``output`` cannot be opened for
        writing (permission, missing parent dir,
        etc.).
    """
    if output is None:
        sys.stdout.write(text)
        return
    path = Path(output)
    try:
        # ``newline=""`` keeps csv / json content
        # byte-identical (no extra newline on
        # Windows).
        with path.open("w", encoding="utf-8", newline="") as f:
            f.write(text)
    except OSError as exc:
        raise CLIConfigurationError(
            f"cannot write output file {output}: {exc}"
        ) from exc


__all__ = ["render_to_destination"]