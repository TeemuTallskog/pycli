"""Shared terminal types and the backend protocol."""

from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType
from typing import Protocol, Self


@dataclass(frozen=True, slots=True)
class Size:
    """Terminal dimensions in character cells.

    Attributes:
        rows: Number of visible lines.
        columns: Number of visible character cells per line.
    """

    rows: int
    columns: int


@dataclass(frozen=True, slots=True)
class ReadResult:
    """One result from reading terminal input.

    Attributes:
        data: Raw bytes read. Empty when only a resize or EOF was observed.
        resized: Whether a ``SIGWINCH`` (terminal resize) arrived.
        eof: Whether the input stream closed or became unreadable.
    """

    data: bytes = b""
    resized: bool = False
    eof: bool = False


class TerminalProtocol(Protocol):
    """The interface every platform backend implements.

    The protocol is useful for faking a terminal in tests. Implementations are
    responsible for their own lifecycle; `App` only calls `read`, `write`, and
    `size`.
    """

    def enter(self) -> None:
        """Switch the terminal into interactive mode.

        Raises:
            NotInteractive: stdin or stdout is not a TTY, or the terminal
                attributes cannot be changed.
        """
        ...

    def restore(self) -> None:
        """Undo everything `enter` changed.

        Must be idempotent and safe to call from a signal handler.
        """
        ...

    def write(self, text: str) -> None:
        """Write text to the terminal.

        Args:
            text: Text to output. Newlines are not translated, so callers
                should use ``"\\r\\n"`` for full line breaks.
        """
        ...

    def size(self) -> Size:
        """Return the current terminal size.

        Implementations should return a sensible fallback (24x80) when the size
        cannot be determined.

        Returns:
            The terminal dimensions in character cells.
        """
        ...

    def read(self, timeout: float | None = None) -> ReadResult:
        """Wait for terminal input or a resize event.

        Args:
            timeout: Seconds to wait, or `None` to block until something
                happens. A finite timeout returns an empty result when idle.

        Returns:
            Raw bytes, a resize notification, an EOF marker, or an empty
            result on timeout.
        """
        ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
