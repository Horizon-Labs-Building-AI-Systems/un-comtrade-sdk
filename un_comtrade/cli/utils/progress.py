"""Progress reporting for the CLI.

The ``--progress`` flag in trade commands
triggers lightweight progress reporting to
**stderr** (so it doesn't pollute the data
stream on stdout / ``--output PATH``).

The reporter is TTY-aware: when stderr is not a
TTY (e.g. piping into a file), the reporter is
silent by default. Tests use
``force=True`` to capture progress output.
"""

from __future__ import annotations

import sys
from typing import Callable, Optional


class ProgressReporter:
    """Minimal progress reporter.

    Output shape::

        [trade/exports] page 1: 250 records (total 250)

    The reporter writes to stderr (not stdout) so
    that the data stream on stdout remains
    machine-readable when ``--output-format
    json`` is used.
    """

    def __init__(
        self,
        *,
        label: str,
        enabled: bool,
        stream=None,
        force: bool = False,
    ) -> None:
        self._label = label
        self._enabled = enabled
        self._stream = stream if stream is not None else sys.stderr
        # ``force=True`` bypasses the TTY check so
        # tests can capture progress output
        # regardless of pytest's stream state.
        self._force = force
        self._total = 0

    def update(self, current_total: int, *, page: int | None = None) -> None:
        """Update the running total and (optionally)
        the page number. Writes a single line to
        the configured stream.
        """
        self._total = current_total
        if not self._should_write():
            return
        suffix = (
            f" page {page}: "
            if page is not None
            else " "
        )
        self._stream.write(
            f"[{self._label}]{suffix}{current_total} records\n"
        )
        self._stream.flush()

    def finish(self, total: int) -> None:
        """Final summary line.
        """
        if not self._should_write():
            return
        self._stream.write(
            f"[{self._label}] done: {total} records\n"
        )
        self._stream.flush()

    def _should_write(self) -> bool:
        if not self._enabled:
            return False
        if self._force:
            return True
        stream = self._stream
        # ``isatty`` is on the IO base class; some
        # wrappers (e.g. pytest's capture) return
        # False. In that case we honour the user's
        # ``enabled`` flag rather than guessing.
        return bool(getattr(stream, "isatty", lambda: False)())


def make_progress_reporter(
    *,
    label: str,
    enabled: bool,
    force: bool = False,
    stream=None,
) -> ProgressReporter:
    """Factory that returns either a real
    :class:`ProgressReporter` or a no-op stub.

    Always returns a reporter object so callers
    can invoke ``.update(...)`` unconditionally.
    """
    if not enabled and not force:
        return _NullReporter(label)
    return ProgressReporter(
        label=label,
        enabled=enabled,
        force=force,
        stream=stream,
    )


class _NullReporter:
    """No-op reporter used when ``--progress`` is
    absent and tests do not force it.
    """

    def __init__(self, label: str) -> None:
        self._label = label

    def update(self, current_total: int, *, page: int | None = None) -> None:
        pass

    def finish(self, total: int) -> None:
        pass


__all__ = [
    "ProgressReporter",
    "make_progress_reporter",
]