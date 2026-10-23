"""Single-choice prompt."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast, overload

from ..errors import Cancelled
from ..input.keys import Key, KeyType
from ..style import Theme, default_theme
from ..term.base import Size, TerminalProtocol
from ._run import run_prompt
from .options import Option, normalize_options


def _is_char(key: Key, char: str) -> bool:
    return key.type == KeyType.CHAR and key.char == char and not key.ctrl and not key.alt


class SelectPrompt[T]:
    """Arrow-key list with a highlighted current option.

    Args:
        message: Prompt text shown above the list. May be empty.
        options: Normalized options to display.
        index: Initially highlighted position.
        theme: Styling to use. Defaults to `default_theme`.
    """

    def __init__(
        self,
        message: str,
        options: Sequence[Option[T]],
        *,
        index: int = 0,
        theme: Theme | None = None,
    ) -> None:
        self._message = message
        self._options = options
        self._index = index
        self._theme = theme or default_theme()

    def render(self, size: Size) -> list[str]:
        """Build the visible lines for the current selection.

        At most 12 options are shown, further limited by the terminal height.
        The selection is kept centered while scrolling, and hidden options are
        summarized with ``↑ N more`` / ``↓ N more``.

        Args:
            size: Current terminal size.

        Returns:
            The message, the visible options, and the help line.
        """
        theme = self._theme
        lines: list[str] = []
        if self._message:
            lines.append(f"{theme.bold}{self._message}{theme.reset}")

        count = len(self._options)
        room = max(1, size.rows - 4)
        visible = max(1, min(count, room, 12))
        start = max(0, min(self._index - visible // 2, count - visible))
        end = start + visible

        if start > 0:
            lines.append(f"{theme.dim}  ↑ {start} more{theme.reset}")
        for position in range(start, end):
            option = self._options[position]
            if position == self._index:
                lines.append(f"{theme.accent}❯ {option.label}{theme.reset}")
            else:
                lines.append(f"  {option.label}")
        if end < count:
            lines.append(f"{theme.dim}  ↓ {count - end} more{theme.reset}")

        lines.append(f"{theme.dim}↑/↓ or j/k move · Enter select · Esc cancel{theme.reset}")
        return lines

    def handle_key(self, key: Key) -> T | None:
        """Update the selection and return the value on Enter.

        Args:
            key: The decoded key event.

        Returns:
            The selected option's value when Enter is pressed, otherwise
            `None`.

        Raises:
            Cancelled: Escape was pressed.
            KeyboardInterrupt: Ctrl-C was pressed.
        """
        if key.is_ctrl_c:
            raise KeyboardInterrupt
        if key.type == KeyType.ESC:
            raise Cancelled

        count = len(self._options)
        if key.type == KeyType.UP or _is_char(key, "k"):
            self._index = (self._index - 1) % count
        elif key.type == KeyType.DOWN or _is_char(key, "j"):
            self._index = (self._index + 1) % count
        elif key.type == KeyType.HOME or _is_char(key, "g"):
            self._index = 0
        elif key.type == KeyType.END or _is_char(key, "G"):
            self._index = count - 1
        elif key.type == KeyType.PAGE_UP:
            self._index = max(0, self._index - 5)
        elif key.type == KeyType.PAGE_DOWN:
            self._index = min(count - 1, self._index + 5)
        elif key.type == KeyType.ENTER:
            return self._options[self._index].value
        return None


@overload
def select(
    message: str,
    options: Sequence[str],
    *,
    default: str | None = None,
    terminal: TerminalProtocol | None = None,
    theme: Theme | None = None,
) -> str: ...


@overload
def select[T](
    message: str,
    options: Sequence[tuple[T, str]],
    *,
    default: T | None = None,
    terminal: TerminalProtocol | None = None,
    theme: Theme | None = None,
) -> T: ...


def select(
    message: str,
    options: Sequence[Any],
    *,
    default: Any = None,
    terminal: TerminalProtocol | None = None,
    theme: Theme | None = None,
) -> Any:
    """Ask the user to choose one option with the arrow keys.

    Up and down wrap around the list. ``g``/``G`` and Home/End jump to the
    first and last option, and Page Up/Page Down move five options at a time.

    Args:
        message: Prompt text shown above the list.
        options: Strings, ``(value, label)`` pairs, or `Option` objects. Values
            may be any object.
        default: Value to highlight initially. It must compare equal to one of
            the option values. `None` means "no default", so an option whose
            value is `None` cannot be preselected this way.
        terminal: An already-entered terminal to run on. When omitted, a
            terminal is created, entered, and restored for the duration of the
            prompt.
        theme: Styling to use. Defaults to `default_theme`.

    Returns:
        The value of the chosen option.

    Raises:
        ValueError: ``options`` is empty, or ``default`` is not an option
            value.
        TypeError: An item in ``options`` has an unsupported form.
        Cancelled: The user pressed Escape, or the input stream closed.
        NotInteractive: No terminal is available and ``terminal`` was omitted.
        KeyboardInterrupt: The user pressed Ctrl-C.

    Example:
        ```python
        from pycli import select

        region = select("Region", [("eu", "Europe"), ("us", "United States")])
        ```
    """
    normalized = cast("list[Option[Any]]", normalize_options(options))
    if not normalized:
        raise ValueError("select() requires at least one option")

    index = 0
    if default is not None:
        for position, option in enumerate(normalized):
            if option.value == default:
                index = position
                break
        else:
            raise ValueError(f"default {default!r} is not one of the options")

    prompt: SelectPrompt[Any] = SelectPrompt(message, normalized, index=index, theme=theme)
    return run_prompt(prompt, terminal)
