"""Free-form single-line text prompt."""

from __future__ import annotations

from ..errors import Cancelled
from ..input.keys import Key, KeyType
from ..style import Theme, default_theme
from ..term.base import Size, TerminalProtocol
from ._run import run_prompt
from ._text import TextField


class TextboxPrompt:
    """A single-line text field with cursor navigation.

    Args:
        message: Prompt text shown above the field. May be empty.
        default: Initial field contents. The cursor starts at the end.
        placeholder: Hint shown dimmed while the field is empty.
        allow_empty: Whether Enter may submit an empty value. When `False`, an
            empty submission shows an inline error and keeps the field active.
        theme: Styling to use. Defaults to `default_theme`.
    """

    def __init__(
        self,
        message: str,
        *,
        default: str = "",
        placeholder: str = "",
        allow_empty: bool = False,
        theme: Theme | None = None,
    ) -> None:
        self._message = message
        self._field = TextField(default, placeholder=placeholder, allow_empty=allow_empty)
        self._theme = theme or default_theme()

    def render(self, size: Size) -> list[str]:
        """Build the message, current value, optional error, and help line.

        Args:
            size: Current terminal size, used to scroll long values horizontally.

        Returns:
            One line per element, with the caret kept inside the terminal width.
        """
        theme = self._theme
        lines: list[str] = []
        if self._message:
            lines.append(f"{theme.bold}{self._message}{theme.reset}")

        width = max(1, size.columns - 3)
        value = self._field.render_value(width, theme)
        lines.append(f"{theme.accent}❯ {theme.reset}{value}")

        if self._field.error:
            lines.append(f"{theme.error}{self._field.error}{theme.reset}")

        lines.append(
            f"{theme.dim}←/→ move · Home/End jump · Enter submit · Esc cancel{theme.reset}"
        )
        return lines

    def handle_key(self, key: Key) -> str | None:
        """Edit the value and return it on Enter.

        Args:
            key: The decoded key event.

        Returns:
            The submitted text, or `None` while editing.

        Raises:
            Cancelled: Escape was pressed.
            KeyboardInterrupt: Ctrl-C was pressed.
        """
        if key.is_ctrl_c:
            raise KeyboardInterrupt
        if key.type == KeyType.ESC:
            raise Cancelled
        if key.type == KeyType.ENTER:
            return self._field.submit()
        self._field.handle_key(key)
        return None


def textbox(
    message: str,
    *,
    default: str = "",
    placeholder: str = "",
    allow_empty: bool = False,
    terminal: TerminalProtocol | None = None,
    theme: Theme | None = None,
) -> str:
    """Ask the user to type a single line of text.

    Arrow keys move the cursor, Home/End jump to either end, and Backspace or
    Delete remove text. Bracketed pastes are flattened into one sanitized line.
    Long values scroll horizontally so the caret stays visible.

    Args:
        message: Prompt text shown above the field.
        default: Initial field contents. Defaults to empty.
        placeholder: Hint shown dimmed while the field is empty.
        allow_empty: Whether an empty value may be submitted. Defaults to
            `False`, which shows an inline error instead of returning.
        terminal: An already-entered terminal to run on. When omitted, a
            terminal is created, entered, and restored for the duration of the
            prompt.
        theme: Styling to use. Defaults to `default_theme`.

    Returns:
        The text entered by the user.

    Raises:
        Cancelled: The user pressed Escape, or the input stream closed.
        NotInteractive: No terminal is available and ``terminal`` was omitted.
        KeyboardInterrupt: The user pressed Ctrl-C.

    Example:
        ```python
        from pycli import textbox

        name = textbox("Project name", placeholder="my-project")
        ```
    """
    prompt = TextboxPrompt(
        message,
        default=default,
        placeholder=placeholder,
        allow_empty=allow_empty,
        theme=theme,
    )
    return run_prompt(prompt, terminal)
