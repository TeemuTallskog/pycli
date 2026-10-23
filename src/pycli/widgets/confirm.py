"""Yes/no confirmation prompt."""

from __future__ import annotations

from ..errors import Cancelled
from ..input.keys import Key, KeyType
from ..style import Theme, default_theme
from ..term.base import Size, TerminalProtocol
from ._run import run_prompt


class ConfirmPrompt:
    """A compact yes/no prompt activated by y/n, Enter, or the arrow keys.

    ``y``/``Y`` returns `True` and ``n``/``N`` returns `False` immediately,
    ignoring ``default``. ``Enter`` returns the current value, which starts at
    ``default``. Left/Right, Tab, and Space toggle it.

    Args:
        message: The question to display.
        default: Initial choice, returned when Enter is pressed without
            toggling. Defaults to `False`.
        theme: Styling to use. Defaults to `default_theme`.
    """

    def __init__(
        self,
        message: str,
        *,
        default: bool = False,
        theme: Theme | None = None,
    ) -> None:
        self._message = message
        self._value = default
        self._theme = theme or default_theme()

    def render(self, size: Size) -> list[str]:
        """Build the question and help lines.

        Args:
            size: Current terminal size. The prompt is always two lines, so
                this argument is unused.

        Returns:
            The question with both choices, and the help line.
        """
        theme = self._theme
        yes = (
            f"{theme.accent}{theme.bold}Yes{theme.reset}"
            if self._value
            else f"{theme.dim}Yes{theme.reset}"
        )
        no = (
            f"{theme.dim}No{theme.reset}"
            if self._value
            else f"{theme.accent}{theme.bold}No{theme.reset}"
        )
        return [
            f"{theme.bold}{self._message}{theme.reset}  {yes} {theme.dim}/{theme.reset} {no}",
            f"{theme.dim}y/n or ←/→ toggle · Enter confirm · Esc cancel{theme.reset}",
        ]

    def handle_key(self, key: Key) -> bool | None:
        """Toggle or answer the question.

        Args:
            key: The decoded key event.

        Returns:
            `True` or `False` when the question is answered, otherwise `None`.

        Raises:
            Cancelled: Escape was pressed.
            KeyboardInterrupt: Ctrl-C was pressed.
        """
        if key.is_ctrl_c:
            raise KeyboardInterrupt
        if key.type == KeyType.ESC:
            raise Cancelled

        if key.type == KeyType.CHAR and not key.ctrl and not key.alt:
            if key.char in ("y", "Y"):
                return True
            if key.char in ("n", "N"):
                return False

        if key.type == KeyType.ENTER:
            return self._value
        toggles = key.type in (KeyType.LEFT, KeyType.RIGHT, KeyType.TAB) or (
            key.type == KeyType.CHAR and key.char == " " and not key.ctrl
        )
        if toggles:
            self._value = not self._value
        return None


def confirm(
    message: str,
    *,
    default: bool = False,
    terminal: TerminalProtocol | None = None,
    theme: Theme | None = None,
) -> bool:
    """Ask a yes/no question. Returns ``default`` when Enter is pressed.

    Args:
        message: The question to display.
        default: Initial choice. Defaults to `False`.
        terminal: An already-entered terminal to run on. When omitted, a
            terminal is created, entered, and restored for the duration of the
            prompt.
        theme: Styling to use. Defaults to `default_theme`.

    Returns:
        `True` for yes and `False` for no.

    Raises:
        Cancelled: The user pressed Escape, or the input stream closed.
        NotInteractive: No terminal is available and ``terminal`` was omitted.
        KeyboardInterrupt: The user pressed Ctrl-C.

    Example:
        ```python
        from pycli import confirm

        if confirm("Overwrite the file?", default=False):
            ...
        ```
    """
    return run_prompt(ConfirmPrompt(message, default=default, theme=theme), terminal)
