"""Inline rendering of a replaceable block of terminal lines."""

from __future__ import annotations

from collections.abc import Sequence

from ..term import ansi
from ..term.base import TerminalProtocol
from .width import sanitize, truncate


class LiveRegion:
    """A block of lines that can be redrawn in place.

    The region always leaves the cursor on the line below its last line. The
    next `draw` moves back up, erases the old block, and writes the new one.
    Lines are truncated one cell short of the terminal width so the terminal
    never auto-wraps and desynchronizes the height accounting.

    Erasing uses ``CSI 0J`` (erase below), so nothing else may be printed below
    the region while it is active.

    Args:
        terminal: The terminal to render into. The region never enters or
            restores it.

    Example:
        ```python
        from pycli.render import LiveRegion

        region = LiveRegion(term)
        region.draw(["Downloading...", "  42%"])
        region.draw(["Downloading...", "  67%"])
        region.clear()
        ```
    """

    def __init__(self, terminal: TerminalProtocol) -> None:
        self._terminal = terminal
        self._height = 0

    @property
    def height(self) -> int:
        """Number of lines currently drawn, or 0 after `clear`."""
        return self._height

    def draw(self, lines: Sequence[str]) -> None:
        """Replace the region contents with ``lines``.

        Args:
            lines: One string per terminal line. Each line is sanitized and
                truncated to one cell less than the terminal width. An empty
                sequence erases the region and resets the height to 0.
        """
        width = max(1, self._terminal.size().columns)
        rendered = [truncate(sanitize(line), max(1, width - 1)) for line in lines]

        chunks: list[str] = []
        if self._height:
            chunks.append(ansi.cursor_prev_line(self._height))
            chunks.append(ansi.ERASE_BELOW)
        if rendered:
            chunks.append("\r\n".join(rendered))
            chunks.append("\r\n")

        if chunks:
            self._terminal.write("".join(chunks))
        self._height = len(rendered)

    def clear(self) -> None:
        """Erase the region and leave the cursor where it started.

        Idempotent: clearing an empty region writes nothing.
        """
        if not self._height:
            return
        self._terminal.write(ansi.cursor_prev_line(self._height) + ansi.ERASE_BELOW)
        self._height = 0
