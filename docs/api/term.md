# pycli.term

Terminal lifecycle and the platform backend interface.

```python
from pycli.term import Terminal, ansi
```

`Terminal` is chosen at import time: the POSIX backend on POSIX systems, the
experimental `msvcrt` backend on Windows. Both implement
[`TerminalProtocol`][pycli.term.TerminalProtocol].

!!! note

    `clear_lines` is also importable from `pycli.term`. It is documented once,
    under [`pycli.clear_lines`][pycli.clear_lines].

::: pycli.term
    options:
      show_root_heading: false
      members:
        - Terminal
        - TerminalProtocol
        - Size
        - ReadResult
