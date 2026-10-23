from __future__ import annotations

from pycli.render.screen import LiveRegion
from pycli.term.base import Size


class FakeTerminal:
    def __init__(self, size: Size | None = None) -> None:
        self.writes: list[str] = []
        self._size = size or Size(rows=24, columns=80)

    def size(self) -> Size:
        return self._size

    def write(self, text: str) -> None:
        self.writes.append(text)


def test_first_draw() -> None:
    terminal = FakeTerminal()
    region = LiveRegion(terminal)
    region.draw(["one", "two"])
    assert terminal.writes == ["one\r\ntwo\r\n"]
    assert region.height == 2


def test_redraw_moves_up_and_erases() -> None:
    terminal = FakeTerminal()
    region = LiveRegion(terminal)
    region.draw(["one", "two"])
    region.draw(["three"])
    assert terminal.writes[-1] == "\x1b[2F\x1b[0Jthree\r\n"
    assert region.height == 1


def test_clear() -> None:
    terminal = FakeTerminal()
    region = LiveRegion(terminal)
    region.draw(["one", "two"])
    region.clear()
    assert terminal.writes[-1] == "\x1b[2F\x1b[0J"
    assert region.height == 0


def test_clear_is_idempotent() -> None:
    terminal = FakeTerminal()
    region = LiveRegion(terminal)
    region.clear()
    assert terminal.writes == []


def test_lines_are_truncated_to_terminal_width() -> None:
    terminal = FakeTerminal(Size(rows=10, columns=10))
    region = LiveRegion(terminal)
    region.draw(["x" * 40])
    rendered = terminal.writes[0].split("\r\n")[0]
    assert rendered == "x" * 8 + "…"


def test_styling_is_preserved() -> None:
    terminal = FakeTerminal()
    region = LiveRegion(terminal)
    region.draw(["\x1b[1mbold\x1b[0m"])
    assert terminal.writes[0] == "\x1b[1mbold\x1b[0m\r\n"
