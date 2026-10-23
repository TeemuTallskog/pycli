"""Prompt styling and color capability handling."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from .term import ansi


@dataclass(frozen=True, slots=True)
class Theme:
    """ANSI codes used by the built-in widgets.

    Attributes:
        accent: Highlight for the active option and its pointer.
        bold: Emphasis for messages and the active confirm choice.
        dim: Secondary text such as help lines and inactive choices.
        error: Inline validation errors.
        reset: Sequence appended after every styled run.
    """

    accent: str = ansi.CYAN
    bold: str = ansi.BOLD
    dim: str = ansi.DIM
    error: str = ansi.RED
    reset: str = ansi.RESET


def default_theme() -> Theme:
    """Return a theme honoring ``NO_COLOR``, ``TERM=dumb``, and non-TTY output.

    Returns:
        A `Theme` whose fields are all empty strings when colours should be
        disabled, otherwise the default coloured theme.

    Note:
        The TTY check inspects `sys.stdout`, not the output stream of a
        terminal passed to a prompt, so supplying a custom terminal does not
        change the decision.
    """
    if "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb" or not sys.stdout.isatty():
        return Theme(accent="", bold="", dim="", error="", reset="")
    return Theme()
