"""Single-line text editing shared by text boxes and free-text options."""

from __future__ import annotations

import re

from ..input.keys import Key, KeyType
from ..render.width import display_width, sanitize, truncate
from ..style import Theme

_SGR_RE = re.compile(r"\x1b\[[0-9;:]*m")
_CARET = "▏"


def clean_paste(text: str) -> str:
    """Flatten pasted text into a single sanitized line.

    Args:
        text: Raw bracketed-paste payload.

    Returns:
        The text with line breaks replaced by spaces, tabs expanded, and all
        escape sequences and control characters removed.
    """
    text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    text = text.replace("\t", "    ")
    return _SGR_RE.sub("", sanitize(text))


def _tail_fit(text: str, budget: int) -> str:
    """Return the longest suffix of ``text`` that fits in ``budget`` cells."""
    width = display_width(text)
    if width <= budget:
        return text
    if budget <= 0:
        return ""

    marker = "…"
    limit = budget if budget == 1 else budget - 1
    used = 0
    out: list[str] = []
    for char in reversed(text):
        char_width = display_width(char)
        if used + char_width > limit:
            break
        out.append(char)
        used += char_width
    return marker + "".join(reversed(out)) if budget > 1 else "".join(reversed(out))


def _head_fit(text: str, budget: int) -> str:
    """Return the longest prefix of ``text`` that fits in ``budget`` cells."""
    width = display_width(text)
    if width <= budget:
        return text
    if budget <= 0:
        return ""

    marker = "…"
    limit = budget if budget == 1 else budget - 1
    used = 0
    out: list[str] = []
    for char in text:
        char_width = display_width(char)
        if used + char_width > limit:
            break
        out.append(char)
        used += char_width
    return "".join(out) + marker if budget > 1 else "".join(out)


class TextField:
    """Editable single-line value with a cursor.

    The field is a pure state object: it never reads or writes a terminal. The
    owning prompt turns key events into edits and renders `render_value`.

    Args:
        value: Initial text. Line breaks and control characters are cleaned the
            same way as a paste.
        placeholder: Hint shown while the value is empty.
        allow_empty: Whether `submit` accepts an empty value.
    """

    def __init__(
        self,
        value: str = "",
        *,
        placeholder: str = "",
        allow_empty: bool = False,
    ) -> None:
        self.value = clean_paste(value)
        self.cursor = len(self.value)
        self.placeholder = placeholder
        self.allow_empty = allow_empty
        self.error: str | None = None

    def insert(self, text: str) -> None:
        """Insert ``text`` at the cursor.

        Args:
            text: Text to insert. Callers should sanitize untrusted payloads;
                `handle_key` does so for bracketed paste.
        """
        if not text:
            return
        self.value = f"{self.value[: self.cursor]}{text}{self.value[self.cursor :]}"
        self.cursor += len(text)
        self.error = None

    def delete_before(self) -> None:
        """Delete the character before the cursor, if any."""
        if self.cursor == 0:
            return
        self.value = f"{self.value[: self.cursor - 1]}{self.value[self.cursor :]}"
        self.cursor -= 1
        self.error = None

    def delete_at(self) -> None:
        """Delete the character at the cursor, if any."""
        if self.cursor >= len(self.value):
            return
        self.value = f"{self.value[: self.cursor]}{self.value[self.cursor + 1 :]}"
        self.error = None

    def move(self, offset: int) -> None:
        """Move the cursor by ``offset`` characters, clamped to the value."""
        self.cursor = max(0, min(len(self.value), self.cursor + offset))
        self.error = None

    def home(self) -> None:
        """Move the cursor to the start of the value."""
        self.cursor = 0
        self.error = None

    def end(self) -> None:
        """Move the cursor to the end of the value."""
        self.cursor = len(self.value)
        self.error = None

    def handle_key(self, key: Key) -> bool:
        """Apply an editing or cursor key.

        Enter, Escape, and Ctrl-C are handled by the owning prompt because they
        mean different things in a text box and a free-text option.

        Args:
            key: The decoded key event.

        Returns:
            `True` when the key changed the field or cursor, otherwise `False`.
        """
        if key.type == KeyType.CHAR and not key.ctrl and not key.alt:
            self.insert(key.char)
            return True
        if key.type == KeyType.PASTE:
            self.insert(clean_paste(key.text))
            return True
        if key.type == KeyType.BACKSPACE:
            self.delete_before()
            return True
        if key.type == KeyType.DELETE:
            self.delete_at()
            return True
        if key.type == KeyType.LEFT:
            self.move(-1)
            return True
        if key.type == KeyType.RIGHT:
            self.move(1)
            return True
        if key.type == KeyType.HOME:
            self.home()
            return True
        if key.type == KeyType.END:
            self.end()
            return True
        return False

    def submit(self) -> str | None:
        """Validate and return the value.

        Returns:
            The value when it is acceptable, otherwise `None`. An empty value is
            rejected with an inline error unless ``allow_empty`` is set.
        """
        if not self.value and not self.allow_empty:
            self.error = "Value cannot be empty"
            return None
        self.error = None
        return self.value

    def render_value(self, width: int, theme: Theme) -> str:
        """Render the value with a caret, horizontally scrolled to fit.

        Args:
            width: Available cells for the value and caret.
            theme: Styling to use for the caret and placeholder.

        Returns:
            The visible value with a caret at the cursor. Long values are cut
            with ellipses so the caret stays visible.
        """
        width = max(1, width)
        if not self.value:
            if self.placeholder:
                return truncate(
                    f"{theme.accent}{_CARET}{theme.reset}{theme.dim}{self.placeholder}",
                    width,
                )
            return f"{theme.accent}{_CARET}{theme.reset}"

        budget = max(0, width - 1)
        left = _tail_fit(self.value[: self.cursor], budget)
        remaining = max(0, budget - display_width(left))
        right = _head_fit(self.value[self.cursor :], remaining)
        return f"{left}{theme.accent}{_CARET}{theme.reset}{right}"
