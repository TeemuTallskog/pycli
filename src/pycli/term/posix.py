"""POSIX terminal backend built on termios, select, and ANSI escapes."""

from __future__ import annotations

import atexit
import errno
import os
import select
import signal
import sys
import termios
import threading
from contextlib import suppress
from types import FrameType
from typing import Any, BinaryIO, Self

from ..errors import NotInteractive
from . import ansi
from .base import ReadResult, Size

_TERM_SIGNALS = tuple(
    getattr(signal, name) for name in ("SIGTERM", "SIGHUP") if hasattr(signal, name)
)


def _is_main_thread() -> bool:
    return threading.current_thread() is threading.main_thread()


class Terminal:
    """An interactive POSIX terminal.

    Entering the terminal puts stdin into raw mode, hides the cursor, enables
    bracketed paste, and installs resize/signal handling. `restore` is
    idempotent and runs from ``finally``, ``atexit``, and termination-signal
    handlers so a crash does not leave the user's terminal broken.

    Raw mode disables canonical input, echo, output post-processing, and signal
    generation. As a result newlines must be written as ``"\\r\\n"``, and
    Ctrl-C is read as a byte rather than delivered as a signal.

    Args:
        stdin: Binary input stream. Defaults to `sys.stdin.buffer`.
        stdout: Binary output stream. Defaults to `sys.stdout.buffer`.
        alt_screen: Enter the alternate screen buffer on `enter`. Cannot be
            changed afterwards.

    Example:
        ```python
        from pycli.term import Terminal, ansi

        with Terminal() as term:
            term.write("working...\\r\\n")
            term.write(ansi.cursor_up() + ansi.erase_line())
            term.write("done!\\r\\n")
        ```
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
        self._fd_in = stdin.fileno()
        self._fd_out = stdout.fileno()
        self._alt_screen = alt_screen
        self._saved_attrs: list[Any] | None = None
        self._active = False
        self._restoring = False
        self._atexit_registered = False
        self._resize_r: int | None = None
        self._resize_w: int | None = None
        self._resized = False
        self._old_wakeup_fd = -1
        self._old_handlers: dict[int, Any] = {}

    # -- lifecycle ---------------------------------------------------------

    def __enter__(self) -> Self:
        self.enter()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.restore()

    def enter(self) -> None:
        """Put the terminal into interactive mode. Safe to call twice.

        Raises:
            NotInteractive: stdin or stdout is not a TTY, or the terminal
                attributes cannot be read or changed. No state is modified in
                that case.
        """
        if self._active:
            return
        if not os.isatty(self._fd_in) or not os.isatty(self._fd_out):
            raise NotInteractive("stdin and stdout must both be terminals")

        try:
            saved = termios.tcgetattr(self._fd_in)
            raw = termios.tcgetattr(self._fd_in)
        except termios.error as exc:  # pragma: no cover - unusual TTY setups
            raise NotInteractive(f"cannot read terminal attributes: {exc}") from exc

        # Disable canonical mode (line buffering), echo, signal generation, and
        # output post-processing. ISIG off means Ctrl-C arrives as a byte, so we
        # can clean up before re-raising KeyboardInterrupt. OPOST off keeps our
        # explicit \r\n from being expanded to \r\r\n.
        raw[0] &= ~(
            termios.IGNBRK
            | termios.BRKINT
            | termios.PARMRK
            | termios.ISTRIP
            | termios.INLCR
            | termios.IGNCR
            | termios.ICRNL
            | termios.IXON
        )
        raw[1] &= ~termios.OPOST
        raw[2] &= ~(termios.CSIZE | termios.PARENB)
        raw[2] |= termios.CS8
        raw[3] &= ~(termios.ECHO | termios.ECHONL | termios.ICANON | termios.IEXTEN | termios.ISIG)
        raw[6][termios.VMIN] = 0
        raw[6][termios.VTIME] = 0

        try:
            termios.tcsetattr(self._fd_in, termios.TCSAFLUSH, raw)
        except termios.error as exc:  # pragma: no cover - unusual TTY setups
            raise NotInteractive(f"cannot enable raw mode: {exc}") from exc

        self._saved_attrs = saved
        self._active = True
        atexit.register(self.restore)
        self._atexit_registered = True

        try:
            self._install_signal_handlers()
            if self._alt_screen:
                self.write(ansi.ALT_SCREEN_ENTER)
            self.write(ansi.HIDE_CURSOR)
            self.write(ansi.BRACKETED_PASTE_ON)
        except BaseException:
            self.restore()
            raise

    def restore(self) -> None:
        """Restore the terminal. Idempotent and safe to call from a signal.

        Disables bracketed paste, shows the cursor, leaves the alternate screen
        if one was entered, and restores the saved terminal attributes.
        """
        if self._restoring:
            return
        self._restoring = True
        try:
            was_active = self._active
            self._active = False

            if was_active:
                with suppress(OSError):
                    if self._alt_screen:
                        self.write(ansi.ALT_SCREEN_LEAVE)
                    self.write(ansi.BRACKETED_PASTE_OFF)
                    self.write(ansi.SHOW_CURSOR)

            if self._saved_attrs is not None:
                with suppress(OSError, termios.error):
                    termios.tcsetattr(self._fd_in, termios.TCSAFLUSH, self._saved_attrs)
                self._saved_attrs = None

            self._remove_signal_handlers()
            if self._atexit_registered:
                atexit.unregister(self.restore)
                self._atexit_registered = False
        finally:
            self._restoring = False

    # -- I/O ---------------------------------------------------------------

    def write(self, text: str) -> None:
        """Write UTF-8 text to stdout, retrying partial writes.

        Args:
            text: Text to write. Newlines are not translated because output
                post-processing is disabled, so use ``"\\r\\n"`` explicitly.
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
        except OSError:
            try:
                size = os.get_terminal_size()
            except OSError:
                return Size(rows=24, columns=80)
        return Size(rows=size.lines, columns=size.columns)

    def read(self, timeout: float | None = None) -> ReadResult:
        """Wait for input bytes, a resize signal, or EOF.

        Args:
            timeout: Seconds to wait, or `None` to block until input, resize,
                or EOF occurs.

        Returns:
            A `ReadResult` carrying raw bytes, a resize flag, an EOF flag, or
            nothing when the timeout expired. EOF is reported both for a clean
            zero-byte read and for ``EIO``/``EBADF``.
        """
        watched = [self._fd_in]
        if self._resize_r is not None:
            watched.append(self._resize_r)

        try:
            ready, _, _ = select.select(watched, [], [], timeout)
        except InterruptedError:  # pragma: no cover - PEP 475 normally retries
            return ReadResult()

        resized = False
        if self._resize_r is not None and self._resize_r in ready:
            with suppress(BlockingIOError, OSError):
                while os.read(self._resize_r, 4096):
                    pass
            self._resized = False
            resized = True

        if self._fd_in in ready:
            try:
                data = os.read(self._fd_in, 4096)
            except BlockingIOError:  # pragma: no cover - stdin is blocking
                data = b""
            except OSError as exc:
                if exc.errno in (errno.EIO, errno.EBADF):
                    return ReadResult(resized=resized, eof=True)
                raise
            if not data:
                return ReadResult(resized=resized, eof=True)
            return ReadResult(data=data, resized=resized)

        return ReadResult(resized=resized)

    # -- signal handling ---------------------------------------------------

    def _install_signal_handlers(self) -> None:
        if not _is_main_thread():
            return
        try:
            resize_r, resize_w = os.pipe()
            os.set_blocking(resize_r, False)
            os.set_blocking(resize_w, False)
            self._resize_r, self._resize_w = resize_r, resize_w
            self._old_wakeup_fd = signal.set_wakeup_fd(resize_w)

            self._old_handlers[signal.SIGWINCH] = signal.getsignal(signal.SIGWINCH)
            signal.signal(signal.SIGWINCH, self._on_winch)

            for signum in _TERM_SIGNALS:
                self._old_handlers[signum] = signal.getsignal(signum)
                signal.signal(signum, self._on_terminate)
        except (OSError, ValueError):  # pragma: no cover - restricted runtime
            self._remove_signal_handlers()

    def _remove_signal_handlers(self) -> None:
        if _is_main_thread():
            with suppress(ValueError, OSError):
                signal.set_wakeup_fd(self._old_wakeup_fd)
            for signum, handler in self._old_handlers.items():
                with suppress(ValueError, OSError, TypeError):
                    signal.signal(signum, handler)
        self._old_handlers.clear()
        self._old_wakeup_fd = -1
        for fd in (self._resize_r, self._resize_w):
            if fd is not None:
                with suppress(OSError):
                    os.close(fd)
        self._resize_r = self._resize_w = None

    def _on_winch(self, signum: int, frame: FrameType | None) -> None:
        self._resized = True

    def _on_terminate(self, signum: int, frame: FrameType | None) -> None:
        old_handler = self._old_handlers.get(signum, signal.SIG_DFL)
        self.restore()
        with suppress(ValueError, OSError, TypeError):
            signal.signal(signum, old_handler)
        os.kill(os.getpid(), signum)
