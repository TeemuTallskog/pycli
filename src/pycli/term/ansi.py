"""ANSI escape sequence constants and cursor helpers.

The constants are grouped by purpose:

- Styling: `RESET`, `BOLD`, `DIM`, `REVERSE`, `CYAN`, `RED`.
- Erasing: `CLEAR_SCREEN`, `CLEAR_LINE`, `ERASE_BELOW`.
- Cursor visibility: `HIDE_CURSOR`, `SHOW_CURSOR`.
- Screen and input modes: `ALT_SCREEN_ENTER` / `ALT_SCREEN_LEAVE`,
  `BRACKETED_PASTE_ON` / `BRACKETED_PASTE_OFF`, `SYNC_UPDATE_ON` /
  `SYNC_UPDATE_OFF`, `WRAP_OFF` / `WRAP_ON`.

Cursor helpers clamp their argument to at least 1, mirroring the behaviour of
the escape sequences themselves.
"""

from __future__ import annotations

ESC = "\x1b"
CSI = f"{ESC}["

RESET = f"{CSI}0m"
BOLD = f"{CSI}1m"
DIM = f"{CSI}2m"
REVERSE = f"{CSI}7m"
CYAN = f"{CSI}36m"
RED = f"{CSI}31m"

CLEAR_SCREEN = f"{CSI}2J"
CLEAR_LINE = f"{CSI}2K"
ERASE_BELOW = f"{CSI}0J"

HIDE_CURSOR = f"{CSI}?25l"
SHOW_CURSOR = f"{CSI}?25h"

ALT_SCREEN_ENTER = f"{CSI}?1049h"
ALT_SCREEN_LEAVE = f"{CSI}?1049l"

BRACKETED_PASTE_ON = f"{CSI}?2004h"
BRACKETED_PASTE_OFF = f"{CSI}?2004l"

SYNC_UPDATE_ON = f"{CSI}?2026h"
SYNC_UPDATE_OFF = f"{CSI}?2026l"

# Disable automatic line wrapping. Useful when writing the last column.
WRAP_OFF = f"{CSI}?7l"
WRAP_ON = f"{CSI}?7h"


def cursor_up(lines: int = 1) -> str:
    """Move the cursor up ``lines`` rows, keeping its column.

    Args:
        lines: Rows to move. Values below 1 are treated as 1.

    Returns:
        The escape sequence as a string.
    """
    return f"{CSI}{max(1, lines)}A"


def cursor_down(lines: int = 1) -> str:
    """Move the cursor down ``lines`` rows, keeping its column.

    Args:
        lines: Rows to move. Values below 1 are treated as 1.

    Returns:
        The escape sequence as a string.
    """
    return f"{CSI}{max(1, lines)}B"


def cursor_prev_line(lines: int = 1) -> str:
    """Move to the beginning of the line ``lines`` rows above.

    Args:
        lines: Rows to move. Values below 1 are treated as 1.

    Returns:
        The escape sequence as a string.
    """
    return f"{CSI}{max(1, lines)}F"


def cursor_next_line(lines: int = 1) -> str:
    """Move to the beginning of the line ``lines`` rows below.

    Args:
        lines: Rows to move. Values below 1 are treated as 1.

    Returns:
        The escape sequence as a string.
    """
    return f"{CSI}{max(1, lines)}E"


def move_to(row: int, column: int) -> str:
    """Move the cursor to a 1-based row and column.

    Args:
        row: Target row, clamped to at least 1.
        column: Target column, clamped to at least 1.

    Returns:
        The escape sequence as a string.
    """
    return f"{CSI}{max(1, row)};{max(1, column)}H"


def erase_line(mode: int = 2) -> str:
    """Erase the current line.

    Args:
        mode: ``0`` erases to the end of the line, ``1`` to the start, and
            ``2`` the whole line.

    Returns:
        The escape sequence as a string.
    """
    return f"{CSI}{mode}K"
