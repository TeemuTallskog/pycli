"""Terminal backends and output helpers."""

from __future__ import annotations

import sys

from .base import ReadResult, Size, TerminalProtocol
from .clear import clear_lines

if sys.platform == "win32":  # pragma: no cover - platform dependent
    from .windows import Terminal
else:
    from .posix import Terminal

__all__ = ["ReadResult", "Size", "Terminal", "TerminalProtocol", "clear_lines"]
