"""Single-choice prompt."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast, overload

from ..errors import Cancelled
from ..input.keys import Key, KeyType
from ..render.width import display_width
from ..style import Theme, default_theme
from ..term.base import Size, TerminalProtocol
from ._run import run_prompt
from ._text import TextField
from .options import FreeText, Option, _free_text, _is_free_text, normalize_options


def _is_char(key: Key, char: str) -> bool:
    return key.type == KeyType.CHAR and key.char == char and not key.ctrl and not key.alt


class SelectPrompt[T]:
    """Arrow-key list with a highlighted current option.

    A `FreeText` option opens an inline single-line editor when selected with
    Enter. Escape in that editor returns to the list instead of cancelling the
    prompt.

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
        self._editing: int | None = None
        self._field: TextField | None = None
        self._theme = theme or default_theme()

    def render(self, size: Size) -> list[str]:
        """Build the visible lines for the current selection.

        At most 12 options are shown, further limited by the terminal height.
        The selection is kept centered while scrolling, and hidden options are
        summarized with ``↑ N more`` / ``↓ N more``. A free-text option shows
        ``…`` until it is activated, then renders its editable value.

        Args:
            size: Current terminal size.

        Returns:
            The message, the visible options, an optional error, and the help
            line.
        """
        theme = self._theme
        lines: list[str] = []
        if self._message:
            lines.append(f"{theme.bold}{self._message}{theme.reset}")

        count = len(self._options)
        reserve = 5 if self._editing is not None else 4
        room = max(1, size.rows - reserve)
        visible = max(1, min(count, room, 12))
        start = max(0, min(self._index - visible // 2, count - visible))
        end = start + visible

        if start > 0:
            lines.append(f"{theme.dim}  ↑ {start} more{theme.reset}")
        for position in range(start, end):
            option = self._options[position]
            active = position == self._index
            if self._editing == position and self._field is not None:
                prefix = f"❯ {option.label}: "
                width = max(1, size.columns - 1 - display_width(prefix))
                value = self._field.render_value(width, theme)
                lines.append(f"{theme.accent}{prefix}{theme.reset}{value}")
                continue

            label = f"{option.label}…" if _is_free_text(option) else option.label
            if active:
                lines.append(f"{theme.accent}❯ {label}{theme.reset}")
            else:
                lines.append(f"  {label}")
        if end < count:
            lines.append(f"{theme.dim}  ↓ {count - end} more{theme.reset}")

        if self._editing is not None and self._field is not None and self._field.error:
            lines.append(f"{theme.error}{self._field.error}{theme.reset}")

        if self._editing is not None:
            help_text = "←/→ move · Home/End jump · Enter submit · Esc back"
        elif _is_free_text(self._options[self._index]):
            help_text = "Enter edit · ↑/↓ move · Esc cancel"
        else:
            help_text = "↑/↓ or j/k move · Enter select · Esc cancel"
        lines.append(f"{theme.dim}{help_text}{theme.reset}")
        return lines

    def handle_key(self, key: Key) -> T | str | None:
        """Update the selection or edit a free-text value.

        Args:
            key: The decoded key event.

        Returns:
            The selected option's value or the typed text when submitted,
            otherwise `None`.

        Raises:
            Cancelled: Escape was pressed outside free-text edit mode.
            KeyboardInterrupt: Ctrl-C was pressed.
        """
        if key.is_ctrl_c:
            raise KeyboardInterrupt
        if self._editing is not None:
            return self._handle_edit_key(key)
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
            option = self._options[self._index]
            if _is_free_text(option):
                self._begin_edit(_free_text(option))
                return None
            return option.value
        return None

    def _handle_edit_key(self, key: Key) -> str | None:
        """Apply a key while a free-text option is active."""
        if key.type == KeyType.ESC:
            self._editing = None
            self._field = None
            return None
        if key.type == KeyType.ENTER:
            if self._field is None:
                return None
            value = self._field.submit()
            if value is None:
                return None
            self._editing = None
            self._field = None
            return value
        if self._field is not None:
            self._field.handle_key(key)
        return None

    def _begin_edit(self, marker: FreeText) -> None:
        """Open the inline editor for ``marker`` at the current position."""
        self._editing = self._index
        self._field = TextField(
            marker.default,
            placeholder=marker.placeholder,
            allow_empty=marker.allow_empty,
        )


@overload
def select(
    message: str,
    options: Sequence[str | FreeText],
    *,
    default: str | None = None,
    terminal: TerminalProtocol | None = None,
    theme: Theme | None = None,
) -> str: ...


@overload
def select[T](
    message: str,
    options: Sequence[tuple[T, str] | FreeText],
    *,
    default: T | None = None,
    terminal: TerminalProtocol | None = None,
    theme: Theme | None = None,
) -> T | str: ...


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
    A `FreeText` option opens an inline editor; the typed text is returned
    directly.

    Args:
        message: Prompt text shown above the list.
        options: Strings, ``(value, label)`` pairs, `Option` objects, or
            `FreeText` markers. Values may be any object.
        default: Value to highlight initially. It must compare equal to one of
            the fixed option values. `None` means "no default", so an option
            whose value is `None` cannot be preselected this way. Use
            ``FreeText(default=...)`` to pre-fill a text field.
        terminal: An already-entered terminal to run on. When omitted, a
            terminal is created, entered, and restored for the duration of the
            prompt.
        theme: Styling to use. Defaults to `default_theme`.

    Returns:
        The value of the chosen option, or the typed text for a `FreeText`
        option.

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
        from pycli.widgets import FreeText

        region = select(
            "Region",
            [("eu", "Europe"), ("us", "United States"), FreeText("Other")],
        )
        ```
    """
    normalized = cast(
        "list[Option[Any]]",
        normalize_options(options, allow_free_text=True),
    )
    if not normalized:
        raise ValueError("select() requires at least one option")

    index = 0
    if default is not None:
        for position, option in enumerate(normalized):
            if _is_free_text(option):
                continue
            if option.value == default:
                index = position
                break
        else:
            raise ValueError(f"default {default!r} is not one of the options")

    prompt: SelectPrompt[Any] = SelectPrompt(message, normalized, index=index, theme=theme)
    return run_prompt(prompt, terminal)
