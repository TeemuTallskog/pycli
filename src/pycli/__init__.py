"""Interactive command-line building blocks for Python.

Quick start:

```python
from pycli import checkbox, confirm, select

env = select("Deploy to?", ["development", "staging", "production"])
services = checkbox("Services", ["api", "web", "worker"])
confirm(f"Deploy {services} to {env}?")
```

Prompts render in place, restore the terminal on every exit path, and return
plain Python values. `Esc` raises `Cancelled`, Ctrl-C raises
`KeyboardInterrupt`, and non-TTY streams raise `NotInteractive`.
"""

from __future__ import annotations

from .errors import Cancelled, NotInteractive, PycliError
from .term.clear import clear_lines
from .widgets.checkbox import checkbox
from .widgets.confirm import confirm
from .widgets.select import select

__version__ = "0.1.0"

__all__ = [
    "Cancelled",
    "NotInteractive",
    "PycliError",
    "checkbox",
    "clear_lines",
    "confirm",
    "select",
]
