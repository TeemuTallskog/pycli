"""Output-clearing helpers for inline CLI tools."""

from __future__ import annotations

import sys
from typing import TextIO

from . import ansi


def clear_lines(count: int, *, stream: TextIO | None = None) -> None:
    """Erase ``count`` previously written lines.

    Intended for output that is still visible: the cursor is expected to sit at
    the beginning of the line *after* the block. Everything below the cursor is
    erased as well. Lines that have already scrolled into the terminal's
    scrollback cannot be reclaimed.

    ANSI output is suppressed when writing to a non-TTY, unless ``stream`` is
    passed explicitly.

    Args:
        count: Number of lines to erase. Zero and negative values are ignored.
        stream: Stream to write the escape sequences to. Defaults to
            `sys.stdout`. Passing a stream explicitly bypasses the TTY check.

    Example:
        ```python
        from pycli import clear_lines

        print("step 1\\nstep 2")
        clear_lines(2)
        ```
    """
    if count <= 0:
        return

    target = stream if stream is not None else sys.stdout
    if stream is None and not target.isatty():
        return

    target.write(ansi.cursor_prev_line(count) + ansi.ERASE_BELOW)
    target.flush()
