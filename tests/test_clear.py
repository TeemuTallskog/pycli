from __future__ import annotations

import io

from pycli import clear_lines


def test_clear_lines_writes_ansi() -> None:
    stream = io.StringIO()
    clear_lines(3, stream=stream)
    assert stream.getvalue() == "\x1b[3F\x1b[0J"


def test_clear_lines_is_noop_for_zero_or_negative() -> None:
    stream = io.StringIO()
    clear_lines(0, stream=stream)
    clear_lines(-2, stream=stream)
    assert stream.getvalue() == ""
