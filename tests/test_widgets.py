from __future__ import annotations

import pytest

from pycli import Cancelled, checkbox, select
from pycli.input.keys import Key, KeyType
from pycli.style import Theme
from pycli.term.base import Size
from pycli.widgets.checkbox import CheckboxPrompt
from pycli.widgets.confirm import ConfirmPrompt
from pycli.widgets.options import Option, normalize_options
from pycli.widgets.select import SelectPrompt

SIZE = Size(rows=24, columns=80)
PLAIN = Theme(accent="", bold="", dim="", error="", reset="")


def test_normalize_options() -> None:
    options = normalize_options(["a", ("b", "B")])
    assert [option.value for option in options] == ["a", "b"]
    assert [option.label for option in options] == ["a", "B"]


def test_select_render_and_submit() -> None:
    prompt = SelectPrompt(
        "Pick",
        [Option("a", "Alpha"), Option("b", "Bravo")],
        theme=PLAIN,
    )
    lines = prompt.render(SIZE)
    assert lines[0] == "Pick"
    assert "❯ Alpha" in lines
    assert "  Bravo" in lines

    assert prompt.handle_key(Key(KeyType.DOWN)) is None
    assert prompt.render(SIZE)[2] == "❯ Bravo"
    assert prompt.handle_key(Key(KeyType.ENTER)) == "b"


def test_select_alias_keys() -> None:
    prompt = SelectPrompt("Pick", [Option("a", "A"), Option("b", "B")], theme=PLAIN)
    prompt.handle_key(Key(KeyType.CHAR, char="j"))
    assert prompt.handle_key(Key(KeyType.ENTER)) == "b"
    prompt.handle_key(Key(KeyType.CHAR, char="g"))
    assert prompt.handle_key(Key(KeyType.ENTER)) == "a"


def test_select_escape_cancels() -> None:
    prompt = SelectPrompt("Pick", [Option("a", "A")], theme=PLAIN)
    with pytest.raises(Cancelled):
        prompt.handle_key(Key(KeyType.ESC))


def test_select_ctrl_c() -> None:
    prompt = SelectPrompt("Pick", [Option("a", "A")], theme=PLAIN)
    with pytest.raises(KeyboardInterrupt):
        prompt.handle_key(Key(KeyType.CHAR, char="c", ctrl=True))


def test_select_viewport_centers_selection() -> None:
    options = [Option(str(index), f"Item {index}") for index in range(30)]
    prompt = SelectPrompt("Pick", options, index=20, theme=PLAIN)
    lines = prompt.render(Size(rows=10, columns=80))
    assert any("more" in line for line in lines)
    assert any("Item 20" in line and line.startswith("❯") for line in lines)


def test_checkbox_toggle_and_submit() -> None:
    prompt = CheckboxPrompt("Pick", [Option("a", "A"), Option("b", "B")], theme=PLAIN)
    prompt.handle_key(Key(KeyType.DOWN))
    prompt.handle_key(Key(KeyType.CHAR, char=" "))
    assert prompt.handle_key(Key(KeyType.ENTER)) == ["b"]


def test_checkbox_minimum_selection() -> None:
    prompt = CheckboxPrompt(
        "Pick",
        [Option("a", "A"), Option("b", "B")],
        min_selected=1,
        theme=PLAIN,
    )
    assert prompt.handle_key(Key(KeyType.ENTER)) is None
    assert any("at least 1" in line for line in prompt.render(SIZE))


def test_checkbox_maximum_selection() -> None:
    prompt = CheckboxPrompt(
        "Pick",
        [Option("a", "A"), Option("b", "B")],
        max_selected=1,
        theme=PLAIN,
    )
    prompt.handle_key(Key(KeyType.CHAR, char=" "))
    prompt.handle_key(Key(KeyType.DOWN))
    prompt.handle_key(Key(KeyType.CHAR, char=" "))
    assert prompt.handle_key(Key(KeyType.ENTER)) == ["a"]


def test_confirm_yes_no_and_enter() -> None:
    prompt = ConfirmPrompt("Deploy?", theme=PLAIN)
    assert prompt.render(SIZE)[0].startswith("Deploy?")
    assert prompt.handle_key(Key(KeyType.CHAR, char="y")) is True
    assert prompt.handle_key(Key(KeyType.CHAR, char="n")) is False

    prompt = ConfirmPrompt("Deploy?", default=False, theme=PLAIN)
    assert prompt.handle_key(Key(KeyType.ENTER)) is False
    prompt.handle_key(Key(KeyType.LEFT))
    assert prompt.handle_key(Key(KeyType.ENTER)) is True


def test_select_rejects_empty_options() -> None:
    with pytest.raises(ValueError):
        select("Pick", [])


def test_checkbox_rejects_overly_large_minimum() -> None:
    with pytest.raises(ValueError):
        checkbox("Pick", ["a"], min_selected=2)


def test_checkbox_rejects_unknown_preselection() -> None:
    with pytest.raises(ValueError):
        checkbox("Pick", ["a"], preselected=["z"])


def test_checkbox_rejects_too_many_preselected() -> None:
    with pytest.raises(ValueError):
        checkbox("Pick", ["a", "b"], max_selected=1, preselected=["a", "b"])
