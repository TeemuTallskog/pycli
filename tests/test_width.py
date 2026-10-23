from __future__ import annotations

from pycli.render.width import display_width, sanitize, truncate


def test_ascii_width() -> None:
    assert display_width("hello") == 5


def test_wide_characters() -> None:
    assert display_width("日本") == 4
    assert display_width("a日b") == 4


def test_truncate_ascii() -> None:
    result = truncate("abcdef", 4)
    assert result == "abc…"
    assert display_width(result) <= 4


def test_truncate_wide_characters() -> None:
    result = truncate("こんにちは", 5)
    assert display_width(result) <= 5


def test_truncate_zero_width() -> None:
    assert truncate("hello", 0) == ""


def test_sanitize_controls_and_tabs() -> None:
    assert sanitize("a\tb\r") == "a    b"
    assert sanitize("a\x00b") == "ab"


def test_sanitize_preserves_sgr_styling() -> None:
    styled = "\x1b[1mDeploy?\x1b[0m"
    assert sanitize(styled) == styled


def test_sanitize_drops_non_sgr_escape_sequences() -> None:
    assert sanitize("\x1b[2Jhello\x1b[H") == "hello"


def test_display_width_ignores_sgr() -> None:
    assert display_width("\x1b[1mHi\x1b[0m") == 2


def test_truncate_preserves_styling_and_resets() -> None:
    styled = "\x1b[31mabcdef\x1b[0m"
    result = truncate(styled, 4)
    assert result.startswith("\x1b[31m")
    assert result.endswith("\x1b[0m")
    assert display_width(result) <= 4
    assert "abc" in result


def test_no_truncation_when_it_fits() -> None:
    assert truncate("abc", 3) == "abc"
