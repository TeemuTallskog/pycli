from __future__ import annotations

import textwrap

import pytest
from pty_harness import run_pty

from pycli import NotInteractive, select


def test_select_arrow_and_enter() -> None:
    code = textwrap.dedent(
        """
        from pycli import select
        value = select("Pick one", ["dev", "staging", "prod"])
        print("RESULT:" + value)
        """
    )
    status, output = run_pty(code, b"\x1b[B\r", marker=b"Pick one")
    assert status == 0, output.decode("utf-8", "replace")
    assert b"RESULT:staging" in output, output.decode("utf-8", "replace")
    # Styling must survive rendering: the message is bold and the pointer cyan.
    assert b"\x1b[1mPick one" in output
    assert b"\x1b[36m" in output
    assert output.count(b"[1mPick one") == output.count(b"\x1b[1mPick one")
    assert b"\r\r\n" not in output


def test_select_value_label_pairs() -> None:
    code = textwrap.dedent(
        """
        from pycli import select
        value = select("Pick one", [("eu", "Europe"), ("us", "United States")])
        print("RESULT:" + value)
        """
    )
    status, output = run_pty(code, b"\x1b[B\r", marker=b"Pick one")
    assert status == 0, output.decode("utf-8", "replace")
    assert b"RESULT:us" in output


def test_escape_cancels_and_restores_terminal() -> None:
    code = textwrap.dedent(
        """
        import termios
        from pycli import Cancelled, select

        before = termios.tcgetattr(0)
        try:
            select("Pick one", ["a", "b"])
        except Cancelled:
            print("CANCELLED")

        after = termios.tcgetattr(0)
        print("RESTORED" if before == after else "BROKEN")
        """
    )
    status, output = run_pty(code, b"\x1b", marker=b"Pick one")
    assert status == 0, output.decode("utf-8", "replace")
    assert b"CANCELLED" in output
    assert b"RESTORED" in output


def test_ctrl_c_restores_terminal() -> None:
    code = textwrap.dedent(
        """
        import termios
        from pycli import select

        before = termios.tcgetattr(0)
        try:
            select("Pick one", ["a"])
        except KeyboardInterrupt:
            pass

        after = termios.tcgetattr(0)
        print("RESTORED" if before == after else "BROKEN")
        """
    )
    status, output = run_pty(code, b"\x03", marker=b"Pick one")
    assert status == 0, output.decode("utf-8", "replace")
    assert b"RESTORED" in output


def test_checkbox_toggles_multiple_options() -> None:
    code = textwrap.dedent(
        """
        from pycli import checkbox
        values = checkbox("Pick many", ["api", "web", "worker"])
        print("RESULT:" + ",".join(values))
        """
    )
    keys = b"\x1b[B \x1b[B \r"
    status, output = run_pty(code, keys, marker=b"Pick many")
    assert status == 0, output.decode("utf-8", "replace")
    assert b"RESULT:web,worker" in output


def test_confirm_accepts_y() -> None:
    code = textwrap.dedent(
        """
        from pycli import confirm
        print("RESULT:" + ("yes" if confirm("Deploy?") else "no"))
        """
    )
    status, output = run_pty(code, b"y", marker=b"Deploy?")
    assert status == 0, output.decode("utf-8", "replace")
    assert b"RESULT:yes" in output


def test_chained_prompts_keep_typeahead() -> None:
    code = textwrap.dedent(
        """
        from pycli import checkbox, confirm, select
        env = select("Env", ["dev", "prod"])
        services = checkbox("Services", ["api", "web"])
        ok = confirm("Go?")
        print(f"RESULT:{env}:{','.join(services)}:{ok}")
        """
    )
    status, output = run_pty(code, b"\x1b[B\r \ry", marker=b"Env")
    assert status == 0, output.decode("utf-8", "replace")
    assert b"RESULT:prod:api:True" in output


def test_not_interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    class NonTTY:
        def isatty(self) -> bool:
            return False

    monkeypatch.setattr("sys.stdin", NonTTY())
    monkeypatch.setattr("sys.stdout", NonTTY())
    with pytest.raises(NotInteractive):
        select("Pick one", ["a", "b"])


def test_select_free_text_option() -> None:
    code = textwrap.dedent(
        """
        from pycli import select
        from pycli.widgets import FreeText
        value = select("Pick one", ["dev", FreeText("Other")])
        print("RESULT:" + value)
        """
    )
    status, output = run_pty(code, b"\x1b[B\r\rcustom\r", marker=b"Pick one")
    assert status == 0, output.decode("utf-8", "replace")
    assert b"RESULT:custom" in output, output.decode("utf-8", "replace")


def test_textbox_edits_and_submits() -> None:
    code = textwrap.dedent(
        """
        from pycli import textbox
        value = textbox("Name")
        print("RESULT:" + value)
        """
    )
    status, output = run_pty(code, b"apiX\x7f\r", marker=b"Name")
    assert status == 0, output.decode("utf-8", "replace")
    assert b"RESULT:api" in output, output.decode("utf-8", "replace")
