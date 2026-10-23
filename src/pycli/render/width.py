"""Display-width helpers for terminal text.

Styled strings contain SGR escape sequences (``\\x1b[1m`` and friends). Those
sequences occupy no terminal cells but *do* contain control bytes, so width
calculations and control-character sanitizing have to understand them instead
of blindly stripping ``ESC``.
"""

from __future__ import annotations

import re

from wcwidth import wcswidth, wcwidth

from ..term.ansi import RESET

# Only SGR sequences are preserved. Other escape sequences (cursor movement,
# screen clearing, OSC, ...) are dropped so untrusted labels cannot move the
# cursor or otherwise corrupt the rendered frame.
_SGR_RE = re.compile(r"\x1b\[[0-9;:]*m")
_ESCAPE_RE = re.compile(
    r"\x1b\[[0-?]*[ -/]*[@-~]"  # CSI
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC
    r"|\x1b[ -/]*[@-~]"  # other escapes
)


def _clean_plain(text: str) -> str:
    """Sanitize text that contains no SGR styling."""
    if not text:
        return text
    text = _ESCAPE_RE.sub("", text)
    out: list[str] = []
    for char in text:
        if char == "\t":
            out.append("    ")
        elif char == "\r" or ord(char) < 32 or ord(char) == 127:
            continue
        else:
            out.append(char)
    return "".join(out)


def sanitize(text: str) -> str:
    """Replace tabs, drop stray control characters, and keep SGR styling.

    Only SGR sequences (colours and text styles) survive. Cursor movement,
    screen clearing, and OSC sequences are removed so untrusted labels cannot
    corrupt the rendered frame. Tabs expand to four spaces, and carriage
    returns plus other control characters are dropped.

    Args:
        text: Text to sanitize, possibly containing escape sequences.

    Returns:
        The sanitized text.
    """
    if not text:
        return text
    out: list[str] = []
    position = 0
    for match in _SGR_RE.finditer(text):
        out.append(_clean_plain(text[position : match.start()]))
        out.append(match.group())
        position = match.end()
    out.append(_clean_plain(text[position:]))
    return "".join(out)


def display_width(text: str) -> int:
    """Return the number of terminal cells ``text`` occupies, ignoring SGR.

    Wide characters and emoji are measured with `wcwidth`, so this is not the
    same as `len(text)`.

    Args:
        text: Text to measure, possibly containing SGR sequences.

    Returns:
        The number of cells the visible text occupies.
    """
    visible = _clean_plain(_SGR_RE.sub("", text))
    width = wcswidth(visible)
    if width >= 0:
        return width
    # wcswidth returns -1 for strings containing unprintable characters.
    return sum(max(wcwidth(char), 0) or 1 for char in visible)


def _take_plain(text: str, remaining: int) -> tuple[str, int, bool]:
    """Take as many characters as fit in ``remaining`` cells."""
    used = 0
    out: list[str] = []
    for char in text:
        width = wcwidth(char)
        if width < 0:
            width = 0
        if used + width > remaining:
            return "".join(out), used, True
        out.append(char)
        used += width
    return "".join(out), used, False


def truncate(text: str, max_width: int, ellipsis: str = "…") -> str:
    """Truncate ``text`` to at most ``max_width`` visible cells.

    SGR sequences are preserved, and a reset is appended when truncation might
    have left a style active. Text that already fits is returned unchanged.

    Args:
        text: Text to truncate, possibly containing SGR sequences.
        max_width: Maximum visible width in cells. Values of 0 or less return
            an empty string.
        ellipsis: Marker appended when text was cut. Defaults to ``"…"``. If
            the marker itself is wider than ``max_width``, the result is empty.

    Returns:
        The truncated text, including the ellipsis. Text that already fits is
        returned unchanged, apart from sanitization.

    Example:
        ```python
        from pycli.render import truncate

        truncate("abcdef", 4)  # "abc…"
        ```
    """
    if max_width <= 0:
        return ""

    text = sanitize(text)
    if display_width(text) <= max_width:
        return text

    ellipsis_width = display_width(ellipsis)
    if ellipsis_width > max_width:
        return ""

    budget = max_width - ellipsis_width
    out: list[str] = []
    used = 0
    styled = False
    position = 0
    overflow = False

    for match in _SGR_RE.finditer(text):
        chunk, taken, overflow = _take_plain(text[position : match.start()], budget - used)
        out.append(chunk)
        used += taken
        if overflow:
            break
        out.append(match.group())
        styled = True
        position = match.end()

    if not overflow:
        chunk, taken, overflow = _take_plain(text[position:], budget - used)
        out.append(chunk)

    out.append(ellipsis)
    if styled:
        out.append(RESET)
    return "".join(out)
