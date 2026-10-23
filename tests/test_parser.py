from __future__ import annotations

from pycli.input.keys import Key, KeyType
from pycli.input.parser import Parser


def test_plain_characters() -> None:
    parser = Parser()
    keys = parser.feed(b"ab", now=0.0)
    assert keys == [
        Key(KeyType.CHAR, char="a"),
        Key(KeyType.CHAR, char="b"),
    ]


def test_navigation_sequences() -> None:
    parser = Parser()
    keys = parser.feed(b"\x1b[A\x1b[B\x1b[C\x1b[D\x1b[H\x1b[F", now=0.0)
    assert [key.type for key in keys] == [
        KeyType.UP,
        KeyType.DOWN,
        KeyType.RIGHT,
        KeyType.LEFT,
        KeyType.HOME,
        KeyType.END,
    ]


def test_split_escape_sequence() -> None:
    parser = Parser()
    assert parser.feed(b"\x1b", now=0.0) == []
    assert parser.feed(b"[A", now=0.01) == [Key(KeyType.UP)]


def test_lone_escape_waits_for_timeout() -> None:
    parser = Parser(esc_timeout=0.05)
    assert parser.feed(b"\x1b", now=0.0) == []
    assert parser.tick(now=0.04) == []
    assert parser.tick(now=0.06) == [Key(KeyType.ESC)]


def test_modified_arrow() -> None:
    parser = Parser()
    assert parser.feed(b"\x1b[1;5A", now=0.0) == [Key(KeyType.UP, ctrl=True)]
    assert parser.feed(b"\x1b[1;2B", now=0.0) == [Key(KeyType.DOWN, shift=True)]


def test_alt_character() -> None:
    parser = Parser()
    assert parser.feed(b"\x1bb", now=0.0) == [Key(KeyType.CHAR, char="b", alt=True)]


def test_ctrl_letters() -> None:
    parser = Parser()
    assert parser.feed(b"\x03", now=0.0) == [Key(KeyType.CHAR, char="c", ctrl=True)]
    assert parser.feed(b"\x04", now=0.0)[0].is_ctrl_d


def test_enter_and_editing_keys() -> None:
    parser = Parser()
    keys = parser.feed(b"\r\n\t\x7f\x08", now=0.0)
    assert [key.type for key in keys] == [
        KeyType.ENTER,
        KeyType.ENTER,
        KeyType.TAB,
        KeyType.BACKSPACE,
        KeyType.BACKSPACE,
    ]


def test_tilde_sequences() -> None:
    parser = Parser()
    keys = parser.feed(b"\x1b[2~\x1b[3~\x1b[5~\x1b[6~\x1b[1~\x1b[4~", now=0.0)
    assert [key.type for key in keys] == [
        KeyType.INSERT,
        KeyType.DELETE,
        KeyType.PAGE_UP,
        KeyType.PAGE_DOWN,
        KeyType.HOME,
        KeyType.END,
    ]


def test_ss3_sequences() -> None:
    parser = Parser()
    keys = parser.feed(b"\x1bOA\x1bOH\x1bOP", now=0.0)
    assert [key.type for key in keys] == [
        KeyType.UP,
        KeyType.HOME,
        KeyType.F1,
    ]


def test_shift_tab() -> None:
    parser = Parser()
    assert parser.feed(b"\x1b[Z", now=0.0) == [Key(KeyType.TAB, shift=True)]


def test_utf8_split_across_reads() -> None:
    parser = Parser()
    assert parser.feed(b"\xc3", now=0.0) == []
    assert parser.feed(b"\xa9", now=0.01) == [Key(KeyType.CHAR, char="é")]


def test_bracketed_paste() -> None:
    parser = Parser()
    keys = parser.feed(b"\x1b[200~hello\nworld\x1b[201~", now=0.0)
    assert keys == [Key(KeyType.PASTE, text="hello\nworld")]


def test_paste_split_across_reads() -> None:
    parser = Parser()
    assert parser.feed(b"\x1b[200~hel", now=0.0) == []
    assert parser.feed(b"lo\x1b[201~", now=0.01) == [Key(KeyType.PASTE, text="hello")]


def test_incomplete_sequence_flushes_as_unknown() -> None:
    parser = Parser(esc_timeout=0.05)
    assert parser.feed(b"\x1b[", now=0.0) == []
    assert parser.tick(now=0.06) == [Key(KeyType.UNKNOWN, text="\x1b[")]
