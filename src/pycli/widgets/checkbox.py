"""Multi-select checkbox prompt."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast, overload

from ..errors import Cancelled
from ..input.keys import Key, KeyType
from ..style import Theme, default_theme
from ..term.base import Size, TerminalProtocol
from ._run import run_prompt
from .options import Option, normalize_options


def _is_space(key: Key) -> bool:
    return key.type == KeyType.CHAR and key.char == " " and not key.ctrl and not key.alt


class CheckboxPrompt[T]:
    """A list where Space toggles options and Enter submits.

    Args:
        message: Prompt text shown above the list. May be empty.
        options: Normalized options to display.
        checked: Positions that start selected.
        min_selected: Minimum number of selections required to submit.
        max_selected: Maximum number of selections allowed, or `None` for no
            limit.
        theme: Styling to use. Defaults to `default_theme`.
    """

    def __init__(
        self,
        message: str,
        options: Sequence[Option[T]],
        *,
        checked: set[int] | None = None,
        min_selected: int = 0,
        max_selected: int | None = None,
        theme: Theme | None = None,
    ) -> None:
        self._message = message
        self._options = options
        self._index = 0
        self._checked = set(checked or ())
        self._min_selected = min_selected
        self._max_selected = max_selected
        self._error: str | None = None
        self._theme = theme or default_theme()

    def render(self, size: Size) -> list[str]:
        """Build the visible lines for the current selection.

        At most 12 options are shown, further limited by the terminal height.
        When a selection limit is violated, an inline error line is included.

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
        room = max(1, size.rows - 5)
        visible = max(1, min(count, room, 12))
        start = max(0, min(self._index - visible // 2, count - visible))
        end = start + visible

        if start > 0:
            lines.append(f"{theme.dim}  ↑ {start} more{theme.reset}")
        for position in range(start, end):
            option = self._options[position]
            mark = "x" if position in self._checked else " "
            label = f"[{mark}] {option.label}"
            if position == self._index:
                lines.append(f"{theme.accent}❯ {label}{theme.reset}")
            else:
                lines.append(f"  {label}")
        if end < count:
            lines.append(f"{theme.dim}  ↓ {count - end} more{theme.reset}")

        if self._error:
            lines.append(f"{theme.error}{self._error}{theme.reset}")

        lines.append(f"{theme.dim}↑/↓ move · Space toggle · Enter submit · Esc cancel{theme.reset}")
        return lines

    def handle_key(self, key: Key) -> list[T] | None:
        """Toggle options, validate the selection, and submit on Enter.

        Args:
            key: The decoded key event.

        Returns:
            The selected values in display order when Enter is pressed and the
            limits are satisfied, otherwise `None`.

        Raises:
            Cancelled: Escape was pressed.
            KeyboardInterrupt: Ctrl-C was pressed.
        """
        if key.is_ctrl_c:
            raise KeyboardInterrupt
        if key.type == KeyType.ESC:
            raise Cancelled

        if key.type == KeyType.UP or (
            key.type == KeyType.CHAR and key.char == "k" and not key.ctrl
        ):
            self._index = (self._index - 1) % len(self._options)
            self._error = None
        elif key.type == KeyType.DOWN or (
            key.type == KeyType.CHAR and key.char == "j" and not key.ctrl
        ):
            self._index = (self._index + 1) % len(self._options)
            self._error = None
        elif key.type == KeyType.HOME:
            self._index = 0
            self._error = None
        elif key.type == KeyType.END:
            self._index = len(self._options) - 1
            self._error = None
        elif _is_space(key):
            self._toggle(self._index)
        elif key.type == KeyType.ENTER:
            if len(self._checked) < self._min_selected:
                self._error = f"Select at least {self._min_selected} option(s)"
                return None
            if self._max_selected is not None and len(self._checked) > self._max_selected:
                self._error = f"Select at most {self._max_selected} option(s)"
                return None
            return [self._options[position].value for position in sorted(self._checked)]
        return None

    def _toggle(self, position: int) -> None:
        self._error = None
        if position in self._checked:
            self._checked.remove(position)
            return
        if self._max_selected is not None and len(self._checked) >= self._max_selected:
            self._error = f"Select at most {self._max_selected} option(s)"
            return
        self._checked.add(position)


@overload
def checkbox(
    message: str,
    options: Sequence[str],
    *,
    min_selected: int = 0,
    max_selected: int | None = None,
    preselected: Sequence[str] = (),
    terminal: TerminalProtocol | None = None,
    theme: Theme | None = None,
) -> list[str]: ...


@overload
def checkbox[T](
    message: str,
    options: Sequence[tuple[T, str]],
    *,
    min_selected: int = 0,
    max_selected: int | None = None,
    preselected: Sequence[T] = (),
    terminal: TerminalProtocol | None = None,
    theme: Theme | None = None,
) -> list[T]: ...


def checkbox(
    message: str,
    options: Sequence[Any],
    *,
    min_selected: int = 0,
    max_selected: int | None = None,
    preselected: Sequence[Any] = (),
    terminal: TerminalProtocol | None = None,
    theme: Theme | None = None,
) -> list[Any]:
    """Ask the user to toggle any number of options with Space.

    Returns the selected values in display order, regardless of the order the
    user toggled them. ``min_selected`` and ``max_selected`` are validated up
    front and enforced again on submit, where a violation shows an inline error
    instead of returning.

    Args:
        message: Prompt text shown above the list.
        options: Strings, ``(value, label)`` pairs, or `Option` objects. Values
            may be any object.
        min_selected: Minimum number of selections required to submit.
            Defaults to 0.
        max_selected: Maximum number of selections allowed, or `None` for no
            limit. Defaults to `None`.
        preselected: Values checked initially. Each must compare equal to an
            option value. Defaults to empty.
        terminal: An already-entered terminal to run on. When omitted, a
            terminal is created, entered, and restored for the duration of the
            prompt.
        theme: Styling to use. Defaults to `default_theme`.

    Returns:
        The selected values in display order.

    Raises:
        ValueError: ``options`` is empty; ``min_selected`` is negative, larger
            than the option count, or greater than ``max_selected``; a
            preselected value is not an option; or more values are preselected
            than ``max_selected`` allows.
        TypeError: An item in ``options`` has an unsupported form.
        Cancelled: The user pressed Escape, or the input stream closed.
        NotInteractive: No terminal is available and ``terminal`` was omitted.
        KeyboardInterrupt: The user pressed Ctrl-C.

    Example:
        ```python
        from pycli import checkbox

        services = checkbox(
            "Services",
            ["api", "web", "worker"],
            min_selected=1,
            preselected=["api"],
        )
        ```
    """
    normalized = cast("list[Option[Any]]", normalize_options(options))
    if not normalized:
        raise ValueError("checkbox() requires at least one option")
    if min_selected < 0:
        raise ValueError("min_selected cannot be negative")
    if max_selected is not None and max_selected < min_selected:
        raise ValueError("max_selected cannot be less than min_selected")
    if min_selected > len(normalized):
        raise ValueError("min_selected is larger than the number of options")

    selected: set[int] = set()
    for value in preselected:
        for position, option in enumerate(normalized):
            if option.value == value:
                selected.add(position)
                break
        else:
            raise ValueError(f"preselected value {value!r} is not an option")

    if max_selected is not None and len(selected) > max_selected:
        raise ValueError("more values are preselected than max_selected allows")

    prompt: CheckboxPrompt[Any] = CheckboxPrompt(
        message,
        normalized,
        checked=selected,
        min_selected=min_selected,
        max_selected=max_selected,
        theme=theme,
    )
    return run_prompt(prompt, terminal)
