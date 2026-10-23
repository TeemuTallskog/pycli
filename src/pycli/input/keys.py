"""Key event types produced by the input parser."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class KeyType(StrEnum):
    """Logical key names.

    ``CHAR`` covers printable characters, with modifiers described by the
    separate flags on `Key`. ``PASTE`` is emitted once per bracketed paste and
    carries the pasted text in `Key.text`. Anything the parser cannot decode is
    reported as ``UNKNOWN`` rather than dropped.
    """

    CHAR = "char"
    ENTER = "enter"
    TAB = "tab"
    BACKSPACE = "backspace"
    ESC = "esc"
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    HOME = "home"
    END = "end"
    PAGE_UP = "page_up"
    PAGE_DOWN = "page_down"
    INSERT = "insert"
    DELETE = "delete"
    PASTE = "paste"
    UNKNOWN = "unknown"
    F1 = "f1"
    F2 = "f2"
    F3 = "f3"
    F4 = "f4"
    F5 = "f5"
    F6 = "f6"
    F7 = "f7"
    F8 = "f8"
    F9 = "f9"
    F10 = "f10"
    F11 = "f11"
    F12 = "f12"


@dataclass(frozen=True, slots=True)
class Key:
    """A single decoded key press or paste event.

    Attributes:
        type: The logical key, a `KeyType` member.
        char: The printable character for `KeyType.CHAR`.
        text: Payload for `KeyType.PASTE`, or the raw sequence for unknown
            keys.
        ctrl: Whether Ctrl was held.
        alt: Whether Alt was held.
        shift: Whether Shift was held.
    """

    type: KeyType
    char: str = ""
    text: str = ""
    ctrl: bool = False
    alt: bool = False
    shift: bool = False

    @property
    def is_ctrl_c(self) -> bool:
        """Whether this event is Ctrl-C.

        Prompts turn this into `KeyboardInterrupt` after restoring the
        terminal.
        """
        return self.ctrl and self.char.lower() == "c"

    @property
    def is_ctrl_d(self) -> bool:
        """Whether this event is Ctrl-D (end of input in many shells)."""
        return self.ctrl and self.char.lower() == "d"
