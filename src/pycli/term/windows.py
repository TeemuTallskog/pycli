"""Best-effort Windows terminal backend.

Windows Terminal (and recent conhost versions) understand ANSI when virtual
terminal processing is enabled, so rendering can stay identical to POSIX. Input
is still read through ``msvcrt`` and translated from scan codes, which means
modifier combinations and bracketed paste are not yet complete. This backend is
experimental; POSIX is the supported platform for now.
"""

from __future__ import annotations

import ctypes
import msvcrt
import os
import sys
import time
from contextlib import suppress
from typing import Any, BinaryIO, Self

from ..errors import NotInteractive
from . import ansi
from .base import ReadResult, Size

_STD_INPUT_HANDLE = -10
_STD_OUTPUT_HANDLE = -11
_ENABLE_PROCESSED_INPUT = 0x0001
_ENABLE_LINE_INPUT = 0x0002
_ENABLE_ECHO_INPUT = 0x0004
_ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
_ENABLE_VIRTUAL_TERMINAL_INPUT = 0x0200

_SCAN_CODES = {
    "H": "\x1b[A",  # up
    "P": "\x1b[B",  # down
    "M": "\x1b[C",  # right
    "K": "\x1b[D",  # left
    "G": "\x1b[H",  # home
    "O": "\x1b[F",  # end
    "I": "\x1b[5~",  # page up
    "Q": "\x1b[6~",  # page down
    "R": "\x1b[2~",  # insert
    "S": "\x1b[3~",  # delete
}


def _kernel32() -> Any:
    if not hasattr(ctypes, "WinDLL"):  # pragma: no cover - non-Windows import
        return None
    return ctypes.WinDLL("kernel32", use_last_error=True)


class Terminal:
    """Interactive terminal for Windows (experimental).

    Rendering uses the same ANSI sequences as the POSIX backend, with virtual
    terminal processing enabled on the console handles. Input goes through
    ``msvcrt`` and scan-code translation, so some modifier combinations and
    bracketed paste are not yet complete.

    Args:
        stdin: Binary input stream. Defaults to `sys.stdin.buffer`.
        stdout: Binary output stream. Defaults to `sys.stdout.buffer`.
        alt_screen: Enter the alternate screen buffer on `enter`.
    """

    def __init__(
        self,
        *,
        stdin: BinaryIO | None = None,
        stdout: BinaryIO | None = None,
        alt_screen: bool = False,
    ) -> None:
        stdin = stdin if stdin is not None else sys.stdin.buffer
        stdout = stdout if stdout is not None else sys.stdout.buffer
        self._stdin = stdin
        self._stdout = stdout
        self._fd_out = stdout.fileno()
        self._alt_screen = alt_screen
        self._active = False
        self._saved_in: int | None = None
        self._saved_out: int | None = None
        self._k32 = _kernel32()
        self._h_in: Any = None
        self._h_out: Any = None

    def __enter__(self) -> Self:
        self.enter()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.restore()

    def enter(self) -> None:
        """Put the console into interactive mode. Safe to call twice.

        Raises:
            NotInteractive: stdin or stdout is not a TTY, the Win32 console API
                is unavailable, or the console mode cannot be changed.
        """
        if self._active:
            return
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise NotInteractive("stdin and stdout must both be terminals")
        if self._k32 is None:  # pragma: no cover - Windows only
            raise NotInteractive("Win32 console API is unavailable")

        self._h_in = self._k32.GetStdHandle(_STD_INPUT_HANDLE)
        self._h_out = self._k32.GetStdHandle(_STD_OUTPUT_HANDLE)
        self._saved_in = self._get_mode(self._h_in)
        self._saved_out = self._get_mode(self._h_out)
        self._active = True

        in_mode = self._saved_in & ~(
            _ENABLE_PROCESSED_INPUT | _ENABLE_LINE_INPUT | _ENABLE_ECHO_INPUT
        )
        self._set_mode(self._h_in, in_mode | _ENABLE_VIRTUAL_TERMINAL_INPUT)
        self._set_mode(self._h_out, self._saved_out | _ENABLE_VIRTUAL_TERMINAL_PROCESSING)

        try:
            if self._alt_screen:
                self.write(ansi.ALT_SCREEN_ENTER)
            self.write(ansi.HIDE_CURSOR)
            self.write(ansi.BRACKETED_PASTE_ON)
        except BaseException:
            self.restore()
            raise

    def restore(self) -> None:
        """Restore console modes and leave the alternate screen if entered."""
        if not self._active:
            return
        self._active = False
        if self._h_out is not None:
            with suppress(OSError):
                if self._alt_screen:
                    self.write(ansi.ALT_SCREEN_LEAVE)
                self.write(ansi.BRACKETED_PASTE_OFF)
                self.write(ansi.SHOW_CURSOR)
        if self._h_in is not None and self._saved_in is not None:
            self._set_mode(self._h_in, self._saved_in)
        if self._h_out is not None and self._saved_out is not None:
            self._set_mode(self._h_out, self._saved_out)

    def write(self, text: str) -> None:
        """Write UTF-8 text to stdout, retrying partial writes.

        Args:
            text: Text to write. Newlines are not translated, so use
                ``"\\r\\n"`` explicitly.
        """
        data = text.encode("utf-8", "replace")
        while data:
            written = os.write(self._fd_out, data)
            data = data[written:]

    def clear_lines(self, count: int = 1) -> None:
        """Erase ``count`` lines above the cursor and everything below it.

        Args:
            count: Number of lines to erase. Zero and negative values are
                ignored.
        """
        if count > 0:
            self.write(ansi.cursor_prev_line(count) + ansi.ERASE_BELOW)

    def size(self) -> Size:
        """Return the terminal size, falling back to 24x80.

        Returns:
            The current dimensions in character cells.
        """
        try:
            size = os.get_terminal_size(self._fd_out)
        except OSError:  # pragma: no cover - fallback for odd consoles
            return Size(rows=24, columns=80)
        return Size(rows=size.lines, columns=size.columns)

    def read(self, timeout: float | None = None) -> ReadResult:
        """Wait for input, or return an empty result after ``timeout``.

        Args:
            timeout: Seconds to wait, or `None` to wait indefinitely.

        Returns:
            Raw bytes for a decoded key, including translated scan codes for
            arrows and navigation keys.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            if msvcrt.kbhit():
                char = msvcrt.getwch()
                if char in ("\x00", "\xe0"):
                    if not msvcrt.kbhit():
                        return ReadResult()
                    code = msvcrt.getwch()
                    sequence = _SCAN_CODES.get(code)
                    return ReadResult(data=sequence.encode() if sequence else b"")
                return ReadResult(data=char.encode("utf-8", "replace"))
            if deadline is not None and time.monotonic() >= deadline:
                return ReadResult()
            time.sleep(0.005)

    # -- console modes -----------------------------------------------------

    def _get_mode(self, handle: Any) -> int:
        mode = ctypes.c_uint32()
        if not self._k32.GetConsoleMode(handle, ctypes.byref(mode)):
            raise NotInteractive("cannot read console mode")
        return int(mode.value)

    def _set_mode(self, handle: Any, mode: int) -> None:
        if not self._k32.SetConsoleMode(handle, mode):
            raise NotInteractive("cannot set console mode")
