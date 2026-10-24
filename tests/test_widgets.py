from __future__ import annotations

import pytest

from pycli import Cancelled, checkbox, select
from pycli.input.keys import Key, KeyType
from pycli.render import display_width
from pycli.style import Theme
from pycli.term.base import Size
from pycli.widgets.checkbox import CheckboxPrompt
from pycli.widgets.confirm import ConfirmPrompt
from pycli.widgets.options import FreeText, Option, normalize_options
from pycli.widgets.select import SelectPrompt
from pycli.widgets.textbox import TextboxPrompt

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


def _free_text_prompt(**marker_options: object) -> SelectPrompt[object]:
    options = normalize_options(
        ["fixed", FreeText("Other", **marker_options)],
        allow_free_text=True,
    )
    return SelectPrompt("Pick", options, index=1, theme=PLAIN)


def test_normalize_free_text_option() -> None:
    options = normalize_options(
        ["a", FreeText("Other", placeholder="custom")],
        allow_free_text=True,
    )
    assert [option.label for option in options] == ["a", "Other"]
    assert isinstance(options[1].value, FreeText)
    assert options[1].value.placeholder == "custom"


def test_normalize_rejects_free_text_by_default() -> None:
    with pytest.raises(TypeError):
        normalize_options([FreeText("Other")])


def test_checkbox_rejects_free_text() -> None:
    with pytest.raises(TypeError):
        checkbox("Pick", ["a", FreeText("Other")])


def test_select_free_text_renders_marker_and_enters_edit_mode() -> None:
    prompt = _free_text_prompt()
    lines = prompt.render(SIZE)
    assert "❯ Other…" in lines
    assert "Enter edit" in lines[-1]

    assert prompt.handle_key(Key(KeyType.ENTER)) is None
    assert "❯ Other: " in prompt.render(SIZE)[2]
    assert "▏" in prompt.render(SIZE)[2]
    assert "Enter submit" in prompt.render(SIZE)[-1]


def test_select_free_text_typing_and_submit() -> None:
    prompt = _free_text_prompt()
    prompt.handle_key(Key(KeyType.ENTER))
    for char in "custom":
        prompt.handle_key(Key(KeyType.CHAR, char=char))
    assert "custom▏" in prompt.render(SIZE)[2]
    assert prompt.handle_key(Key(KeyType.ENTER)) == "custom"


def test_select_free_text_empty_value_shows_error() -> None:
    prompt = _free_text_prompt()
    prompt.handle_key(Key(KeyType.ENTER))
    assert prompt.handle_key(Key(KeyType.ENTER)) is None
    lines = prompt.render(SIZE)
    assert any("Value cannot be empty" in line for line in lines)

    prompt.handle_key(Key(KeyType.CHAR, char="x"))
    assert not any("Value cannot be empty" in line for line in prompt.render(SIZE))
    assert prompt.handle_key(Key(KeyType.ENTER)) == "x"


def test_select_free_text_allows_empty_when_requested() -> None:
    prompt = _free_text_prompt(allow_empty=True)
    prompt.handle_key(Key(KeyType.ENTER))
    assert prompt.handle_key(Key(KeyType.ENTER)) == ""


def test_select_free_text_uses_default_value() -> None:
    prompt = _free_text_prompt(default="staging")
    prompt.handle_key(Key(KeyType.ENTER))
    assert prompt.handle_key(Key(KeyType.ENTER)) == "staging"


def test_select_free_text_cursor_editing() -> None:
    prompt = _free_text_prompt(default="abc")
    prompt.handle_key(Key(KeyType.ENTER))
    prompt.handle_key(Key(KeyType.LEFT))
    prompt.handle_key(Key(KeyType.BACKSPACE))
    prompt.handle_key(Key(KeyType.DELETE))
    prompt.handle_key(Key(KeyType.HOME))
    prompt.handle_key(Key(KeyType.CHAR, char="z"))
    prompt.handle_key(Key(KeyType.END))
    prompt.handle_key(Key(KeyType.CHAR, char="x"))
    assert prompt.handle_key(Key(KeyType.ENTER)) == "zax"


def test_select_free_text_cleans_paste() -> None:
    prompt = _free_text_prompt()
    prompt.handle_key(Key(KeyType.ENTER))
    prompt.handle_key(Key(KeyType.PASTE, text="a\nb\tc\x1b[31mred"))
    assert prompt.handle_key(Key(KeyType.ENTER)) == "a b    cred"


def test_select_free_text_escape_returns_to_list() -> None:
    prompt = _free_text_prompt()
    prompt.handle_key(Key(KeyType.ENTER))
    prompt.handle_key(Key(KeyType.CHAR, char="x"))
    assert prompt.handle_key(Key(KeyType.ESC)) is None
    assert "❯ Other…" in prompt.render(SIZE)

    with pytest.raises(Cancelled):
        prompt.handle_key(Key(KeyType.ESC))

    prompt.handle_key(Key(KeyType.ENTER))
    assert prompt.handle_key(Key(KeyType.ENTER)) is None
    assert any("Value cannot be empty" in line for line in prompt.render(SIZE))


def test_select_free_text_ignores_navigation_keys_while_editing() -> None:
    prompt = _free_text_prompt()
    prompt.handle_key(Key(KeyType.ENTER))
    prompt.handle_key(Key(KeyType.CHAR, char="a"))
    prompt.handle_key(Key(KeyType.DOWN))
    prompt.handle_key(Key(KeyType.CHAR, char="b"))
    assert prompt.handle_key(Key(KeyType.ENTER)) == "ab"


def test_select_free_text_scrolls_to_keep_caret_visible() -> None:
    prompt = _free_text_prompt(default="x" * 100)
    prompt.handle_key(Key(KeyType.ENTER))
    lines = prompt.render(Size(rows=10, columns=20))
    line = next(line for line in lines if "Other:" in line)
    assert "…" in line
    assert "▏" in line
    assert display_width(line) <= 19


def test_select_default_cannot_target_free_text() -> None:
    with pytest.raises(ValueError):
        select("Pick", [FreeText("Other")], default="Other")


def test_textbox_renders_placeholder_and_helper() -> None:
    prompt = TextboxPrompt("Name", placeholder="type here", theme=PLAIN)
    lines = prompt.render(SIZE)
    assert lines[0] == "Name"
    assert "type here" in lines[1]
    assert "▏" in lines[1]
    assert "Enter submit" in lines[-1]


def test_textbox_typing_and_submit() -> None:
    prompt = TextboxPrompt("Name", theme=PLAIN)
    for char in "Ann":
        prompt.handle_key(Key(KeyType.CHAR, char=char))
    assert "Ann▏" in prompt.render(SIZE)[1]
    assert prompt.handle_key(Key(KeyType.ENTER)) == "Ann"


def test_textbox_empty_value_shows_error() -> None:
    prompt = TextboxPrompt("Name", theme=PLAIN)
    assert prompt.handle_key(Key(KeyType.ENTER)) is None
    assert any("Value cannot be empty" in line for line in prompt.render(SIZE))

    prompt.handle_key(Key(KeyType.CHAR, char="x"))
    assert not any("Value cannot be empty" in line for line in prompt.render(SIZE))
    assert prompt.handle_key(Key(KeyType.ENTER)) == "x"


def test_textbox_allows_empty_when_requested() -> None:
    prompt = TextboxPrompt("Name", allow_empty=True, theme=PLAIN)
    assert prompt.handle_key(Key(KeyType.ENTER)) == ""


def test_textbox_escape_and_ctrl_c() -> None:
    prompt = TextboxPrompt("Name", theme=PLAIN)
    with pytest.raises(Cancelled):
        prompt.handle_key(Key(KeyType.ESC))
    with pytest.raises(KeyboardInterrupt):
        prompt.handle_key(Key(KeyType.CHAR, char="c", ctrl=True))


def test_textbox_cleans_paste() -> None:
    prompt = TextboxPrompt("Name", theme=PLAIN)
    prompt.handle_key(Key(KeyType.PASTE, text="line one\nline two"))
    assert prompt.handle_key(Key(KeyType.ENTER)) == "line one line two"


def test_textbox_scrolls_long_value() -> None:
    prompt = TextboxPrompt("Name", default="x" * 100, theme=PLAIN)
    line = prompt.render(Size(rows=10, columns=20))[1]
    assert "…" in line
    assert "▏" in line
    assert display_width(line) <= 19
