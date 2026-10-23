# pycli.input

Incremental decoding of raw terminal bytes into key events.

```python
from pycli.input import Key, KeyType, Parser

parser = Parser()
for key in parser.feed(chunk):
    ...
```

`KeyType` covers printable characters, editing keys, navigation keys, function
keys, and paste events:

| Group | Members |
|---|---|
| Text | `CHAR`, `PASTE` |
| Editing | `ENTER`, `TAB`, `BACKSPACE`, `INSERT`, `DELETE` |
| Navigation | `ESC`, `UP`, `DOWN`, `LEFT`, `RIGHT`, `HOME`, `END`, `PAGE_UP`, `PAGE_DOWN` |
| Function keys | `F1` … `F12` |
| Fallback | `UNKNOWN` |

::: pycli.input
    options:
      show_root_heading: false
      members:
        - Parser
        - Key
        - KeyType
