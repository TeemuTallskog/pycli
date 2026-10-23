"""Incremental parser turning raw terminal bytes into :class:`Key` events.

The parser is fed arbitrary chunks from ``os.read`` and keeps incomplete escape
sequences and partial UTF-8 code points buffered until the rest arrives. A lone
Escape key is only reported after ``esc_timeout`` seconds, because the terminal
sends the same byte whether the user pressed Escape or the start of a sequence.
"""

from __future__ import annotations

import time
from dataclasses import replace

from .keys import Key, KeyType

_PASTE_START = b"\x1b[200~"
_PASTE_END = b"\x1b[201~"

_CSI_FINALS: dict[str, KeyType] = {
    "A": KeyType.UP,
    "B": KeyType.DOWN,
    "C": KeyType.RIGHT,
    "D": KeyType.LEFT,
    "H": KeyType.HOME,
    "F": KeyType.END,
}

_SS3_FINALS: dict[str, KeyType] = {
    "A": KeyType.UP,
    "B": KeyType.DOWN,
    "C": KeyType.RIGHT,
    "D": KeyType.LEFT,
    "H": KeyType.HOME,
    "F": KeyType.END,
    "P": KeyType.F1,
    "Q": KeyType.F2,
    "R": KeyType.F3,
    "S": KeyType.F4,
}

_TILDE_FINALS: dict[int, KeyType] = {
    1: KeyType.HOME,
    2: KeyType.INSERT,
    3: KeyType.DELETE,
    4: KeyType.END,
    5: KeyType.PAGE_UP,
    6: KeyType.PAGE_DOWN,
    7: KeyType.HOME,
    8: KeyType.END,
    11: KeyType.F1,
    12: KeyType.F2,
    13: KeyType.F3,
    14: KeyType.F4,
    15: KeyType.F5,
    17: KeyType.F6,
    18: KeyType.F7,
    19: KeyType.F8,
    20: KeyType.F9,
    21: KeyType.F10,
    23: KeyType.F11,
    24: KeyType.F12,
}


class Parser:
    """A stateful, incremental terminal input parser.

    Feed it arbitrary chunks from ``os.read``. Incomplete escape sequences and
    partial UTF-8 code points stay buffered until the rest arrives. A lone
    Escape key is only reported after `esc_timeout` seconds, because the
    terminal sends the same byte whether the user pressed Escape or started a
    sequence.

    Args:
        esc_timeout: Seconds to wait before interpreting a lone ``ESC`` byte as
            the Escape key. Defaults to 0.05.

    Example:
        ```python
        from pycli.input import Parser

        parser = Parser()
        keys = parser.feed(b"\\x1b[B")  # one DOWN key
        keys = parser.tick()           # releases a pending Escape
        ```
    """

    def __init__(self, *, esc_timeout: float = 0.05) -> None:
        self._buf = bytearray()
        self._pending_since: float | None = None
        self._esc_timeout = esc_timeout

    @property
    def pending(self) -> bytes:
        """Bytes currently buffered waiting for more input."""
        return bytes(self._buf)

    def feed(self, data: bytes | bytearray, *, now: float | None = None) -> list[Key]:
        """Add bytes and return all keys that became complete.

        Args:
            data: Raw bytes from the terminal. Empty input still advances the
                Escape timeout.
            now: Monotonic timestamp to use instead of `time.monotonic`, for
                deterministic tests.

        Returns:
            The keys completed by this chunk, in input order. A partial
            sequence at the end of the chunk yields no key and remains
            buffered.
        """
        moment = time.monotonic() if now is None else now
        keys: list[Key] = []

        if self._buf and self._expired(moment):
            keys.extend(self._flush())
        if data:
            if self._pending_since is None:
                self._pending_since = moment
            self._buf.extend(data)

        keys.extend(self._drain(moment))
        return keys

    def tick(self, *, now: float | None = None) -> list[Key]:
        """Return keys released by the Escape timeout, if any.

        Call this when the terminal read times out so a lone Escape is not held
        forever.

        Args:
            now: Monotonic timestamp to use instead of `time.monotonic`, for
                deterministic tests.

        Returns:
            The keys released by the timeout. Usually empty, or a single
            `KeyType.ESC`.
        """
        moment = time.monotonic() if now is None else now
        keys = self._drain(moment)
        if not keys and self._buf and self._expired(moment):
            keys = self._flush()
        return keys

    # -- internals ---------------------------------------------------------

    def _expired(self, moment: float) -> bool:
        return self._pending_since is not None and moment - self._pending_since >= self._esc_timeout

    def _flush(self) -> list[Key]:
        data = bytes(self._buf)
        self._buf.clear()
        self._pending_since = None
        if data == b"\x1b":
            return [Key(KeyType.ESC)]
        return [Key(KeyType.UNKNOWN, text=data.decode("utf-8", "replace"))]

    def _drain(self, moment: float) -> list[Key]:
        keys: list[Key] = []
        while self._buf:
            if self._buf.startswith(_PASTE_START):
                end = self._buf.find(_PASTE_END, len(_PASTE_START))
                if end < 0:
                    break
                text = bytes(self._buf[len(_PASTE_START) : end]).decode("utf-8", "replace")
                del self._buf[: end + len(_PASTE_END)]
                keys.append(Key(KeyType.PASTE, text=text))
                continue

            if self._buf[0] == 0x1B:
                key = self._parse_escape()
                if key is None:
                    break
                keys.append(key)
                continue

            parsed = self._parse_plain(bytes(self._buf))
            if parsed is None:
                break
            key, size = parsed
            del self._buf[:size]
            keys.append(key)

        if self._buf:
            if self._pending_since is None or keys:
                self._pending_since = moment
        else:
            self._pending_since = None
        return keys

    def _parse_escape(self) -> Key | None:
        if len(self._buf) < 2:
            return None

        second = self._buf[1]
        if second == 0x5B:  # '['
            index = 2
            while index < len(self._buf) and 0x20 <= self._buf[index] <= 0x3F:
                index += 1
            if index >= len(self._buf):
                return None
            final = self._buf[index]
            sequence = bytes(self._buf[: index + 1])
            del self._buf[: index + 1]
            if not 0x40 <= final <= 0x7E:
                return Key(KeyType.UNKNOWN, text=sequence.decode("utf-8", "replace"))
            return _csi_key(sequence)

        if second == 0x4F:  # 'O' (SS3)
            if len(self._buf) < 3:
                return None
            final = self._buf[2]
            del self._buf[:3]
            return _ss3_key(final)

        if second == 0x1B:
            del self._buf[:2]
            return Key(KeyType.UNKNOWN, text="\x1b\x1b")

        # Alt + key: decode the remainder as a normal key and mark it.
        parsed = self._parse_plain(bytes(self._buf[1:]))
        if parsed is None:
            return None
        key, size = parsed
        del self._buf[: size + 1]
        return replace(key, alt=True)

    @staticmethod
    def _parse_plain(data: bytes) -> tuple[Key, int] | None:
        if not data:
            return None
        first = data[0]

        if first in (0x0D, 0x0A):
            return Key(KeyType.ENTER), 1
        if first == 0x09:
            return Key(KeyType.TAB), 1
        if first in (0x7F, 0x08):
            return Key(KeyType.BACKSPACE), 1
        if first == 0x00:
            return Key(KeyType.CHAR, char="@", ctrl=True), 1
        if 0x01 <= first <= 0x1A:
            return Key(KeyType.CHAR, char=chr(first + 0x60), ctrl=True), 1
        if 0x1C <= first <= 0x1F:
            return Key(KeyType.CHAR, char=chr(first + 0x40), ctrl=True), 1
        if first == 0x1B:
            return None

        if first < 0x80:
            return Key(KeyType.CHAR, char=chr(first)), 1

        length = _utf8_length(first)
        if length is None:
            return Key(KeyType.UNKNOWN, text=chr(first)), 1
        if len(data) < length:
            return None

        chunk = data[:length]
        try:
            char = chunk.decode("utf-8")
        except UnicodeDecodeError:
            return Key(KeyType.UNKNOWN, text=chunk.decode("utf-8", "replace")), 1
        return Key(KeyType.CHAR, char=char), length


def _utf8_length(first: int) -> int | None:
    if first & 0xE0 == 0xC0:
        return 2
    if first & 0xF0 == 0xE0:
        return 3
    if first & 0xF8 == 0xF0:
        return 4
    return None


def _modifiers(body: str) -> tuple[bool, bool, bool]:
    """Return (shift, alt, ctrl) from a CSI parameter body."""
    if ";" not in body:
        return False, False, False
    parts = body.split(";")
    if len(parts) < 2:
        return False, False, False
    try:
        value = int(parts[1])
    except ValueError:
        return False, False, False
    bits = max(1, value) - 1
    return bool(bits & 1), bool(bits & 2), bool(bits & 4)


def _csi_key(sequence: bytes) -> Key:
    body = sequence[2:-1].decode("ascii", "replace")
    final = chr(sequence[-1])

    if final == "~":
        return _tilde_key(body)
    if final == "Z":
        return Key(KeyType.TAB, shift=True)

    key_type = _CSI_FINALS.get(final)
    if key_type is None:
        return Key(KeyType.UNKNOWN, text=sequence.decode("utf-8", "replace"))

    shift, alt, ctrl = _modifiers(body)
    return Key(key_type, shift=shift, alt=alt, ctrl=ctrl)


def _tilde_key(body: str) -> Key:
    parts = body.split(";")
    try:
        number = int(parts[0]) if parts[0] else 0
    except ValueError:
        return Key(KeyType.UNKNOWN, text=f"~{body}")

    shift, alt, ctrl = _modifiers(body)
    if number == 200 or number == 201:
        # Bare paste markers are handled by the buffer scanner; if one shows up
        # here it was malformed or the paste was empty.
        return Key(KeyType.PASTE, text="")

    key_type = _TILDE_FINALS.get(number)
    if key_type is None:
        return Key(KeyType.UNKNOWN, text=f"~{body}")
    return Key(key_type, shift=shift, alt=alt, ctrl=ctrl)


def _ss3_key(final: int) -> Key:
    key_type = _SS3_FINALS.get(chr(final))
    if key_type is None:
        return Key(KeyType.UNKNOWN, text=f"\x1bO{chr(final)}")
    return Key(key_type)
