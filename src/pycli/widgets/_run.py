"""Shared prompt runner and terminal ownership."""

from __future__ import annotations

import sys

from ..app import App
from ..errors import NotInteractive
from ..term import Terminal
from ..term.base import TerminalProtocol
from .base import Prompt


def run_prompt[T](prompt: Prompt[T], terminal: TerminalProtocol | None) -> T:
    """Run ``prompt``, creating and owning a terminal when none is supplied.

    Args:
        prompt: The widget to drive.
        terminal: An already-entered terminal, or `None` to create one from
            stdin/stdout.

    Returns:
        The value produced by the prompt.

    Raises:
        NotInteractive: ``terminal`` is `None` and stdin or stdout is not a
            TTY.
        Cancelled: The user cancelled, or the input stream closed.
        KeyboardInterrupt: The user pressed Ctrl-C.
    """
    if terminal is not None:
        return App(prompt, terminal).run()

    stdin = getattr(sys.stdin, "buffer", None)
    stdout = getattr(sys.stdout, "buffer", None)
    if stdin is None or stdout is None or not sys.stdin.isatty() or not sys.stdout.isatty():
        raise NotInteractive("interactive prompt requires stdin and stdout to be terminals")

    owned = Terminal(stdin=stdin, stdout=stdout)
    owned.enter()
    try:
        return App(prompt, owned).run()
    finally:
        owned.restore()
