# Custom widgets

The built-in prompts are small objects driven by a shared loop. You can write
your own prompt by implementing the [`Prompt`][pycli.widgets.base.Prompt]
protocol and running it with [`App`][pycli.app.App].

## The `Prompt` protocol

A prompt is any object with two methods:

```python
class Prompt(Protocol[T_co]):
    def render(self, size: Size) -> list[str]: ...
    def handle_key(self, key: Key) -> T_co | None: ...
```

- `render(size)` returns the lines for the current state. It is called on every
  redraw, including after a resize, so it should be cheap and side-effect free.
- `handle_key(key)` mutates the prompt state and returns the final value when
  the user submits, or `None` to keep going.
- Cancellation is signalled by raising [`Cancelled`][pycli.Cancelled].
  `Ctrl-C` should raise `KeyboardInterrupt`.

`App` owns the loop:

1. Render the prompt into a [`LiveRegion`][pycli.render.LiveRegion].
2. Read input until data, a resize, or EOF arrives.
3. Feed bytes to a [`Parser`][pycli.input.Parser].
4. Dispatch each complete [`Key`][pycli.input.Key] to `handle_key`.
5. Redraw after every batch of keys or resize.
6. Clear the region on the way out, including on exceptions.

```python
from __future__ import annotations

from pycli.app import App
from pycli.errors import Cancelled
from pycli.input.keys import Key, KeyType
from pycli.term import Size, Terminal


class NamePrompt:
    def __init__(self, message: str) -> None:
        self._message = message
        self._value = ""

    def render(self, size: Size) -> list[str]:
        return [self._message, f"> {self._value}_"]

    def handle_key(self, key: Key) -> str | None:
        if key.is_ctrl_c:
            raise KeyboardInterrupt
        if key.type == KeyType.ESC:
            raise Cancelled
        if key.type == KeyType.ENTER:
            return self._value
        if key.type == KeyType.BACKSPACE:
            self._value = self._value[:-1]
        elif key.type == KeyType.CHAR:
            self._value += key.char
        return None


with Terminal() as term:
    name = App(NamePrompt("Your name?"), term).run()

print(f"Hello, {name}!")
```

`App(prompt, terminal)` takes an already-entered
[`TerminalProtocol`][pycli.term.TerminalProtocol]; it never enters or restores
the terminal itself. The built-in prompt functions do that bookkeeping for you
unless you pass `terminal=`.

Keys typed ahead of the next prompt are buffered in a module-global queue, so
chaining `App` instances does not drop input. The queue is cleared whenever a
prompt raises, and it is not thread-safe.

## The inline renderer

[`LiveRegion`][pycli.render.LiveRegion] owns a block of lines and redraws it in
place:

```python
from pycli.render import LiveRegion

region = LiveRegion(term)
region.draw(["Downloading...", "  42%"])
region.draw(["Downloading...", "  67%"])
region.clear()
```

The contract:

- After `draw()`, the cursor sits on the line **below** the block.
- The next `draw()` moves back up by the previous height, erases below, and
  writes the new block.
- `clear()` erases the block and leaves the cursor where the block started.
  It is idempotent.
- Lines are sanitized and truncated to `columns - 1` cells so the terminal
  never auto-wraps. A wrapped line would make the height accounting wrong and
  corrupt the next redraw.
- `region.height` is the number of lines currently drawn.
- Erasing uses `CSI 0J`, so nothing else may be printed below the region while
  it is active.

`LiveRegion` is deliberately not a full-screen layout engine: it redraws the
whole block rather than diffing lines.

## The input parser

[`Parser`][pycli.input.Parser] turns arbitrary byte chunks into key events. It
buffers incomplete escape sequences and partial UTF-8 code points between
calls.

```python
from pycli.input import Parser

parser = Parser()
keys = parser.feed(b"\x1b[B")     # [Key(type=KeyType.DOWN)]
keys = parser.tick()               # releases a lone Esc after esc_timeout
```

- `feed(data)` returns every key that became complete. It accepts `bytes` or
  `bytearray`.
- `tick()` returns keys released by the Escape timeout. A lone `Esc` byte is
  indistinguishable from the start of an escape sequence, so it is only
  reported after `esc_timeout` seconds (default `0.05`). Call `tick()` when
  `read()` times out.
- `pending` exposes the bytes still waiting for more input.
- `feed(..., now=...)` and `tick(now=...)` accept an explicit monotonic clock
  value, which makes timeout behaviour testable.

[`Key`][pycli.input.Key] is a frozen dataclass:

| Field | Meaning |
|---|---|
| `type` | a [`KeyType`][pycli.input.KeyType] member |
| `char` | the printable character for `KeyType.CHAR` |
| `text` | payload for `KeyType.PASTE`, or the raw sequence for unknown keys |
| `ctrl` / `alt` / `shift` | modifier flags decoded from the sequence |

`Key.is_ctrl_c` and `Key.is_ctrl_d` are convenience properties. Bracketed paste
produces a single `KeyType.PASTE` event with the pasted text in `text`, so a
paste containing `\r` cannot submit a prompt. Unrecognized sequences are
reported as `KeyType.UNKNOWN` with the raw bytes decoded into `text` rather than
being silently dropped.

## Text measurement

Terminal output is cell-based, not character-based, so use the helpers in
[`pycli.render`][pycli.render] instead of `len()`:

- [`sanitize()`][pycli.render.sanitize] expands tabs to four spaces, strips
  control characters, and drops all escape sequences except SGR colour/style
  codes.
- [`display_width()`][pycli.render.display_width] returns the number of cells a
  string occupies, ignoring SGR sequences and accounting for wide characters
  and emoji via `wcwidth`.
- [`truncate()`][pycli.render.truncate] cuts a string to at most `max_width`
  cells, appends an ellipsis (default `…`), preserves SGR styling, and appends
  a reset when styling might still be active. `max_width <= 0` returns `""`.

```python
from pycli.render import display_width, truncate

display_width("日本")        # 4
display_width("\x1b[1mHi\x1b[0m")  # 2
truncate("abcdef", 4)        # "abc…"
```

## Colours and the terminal

[`pycli.term.ansi`][pycli.term.ansi] contains the escape sequences and cursor
helpers used by the renderer. Cursor helpers clamp their arguments to at least
1, so `cursor_up(0)` still moves one row.

[`Theme`][pycli.style.Theme] groups the codes widgets use (accent, bold, dim,
error, reset). Build one directly to customize a prompt, or use
[`default_theme()`][pycli.style.default_theme], which disables colours under
`NO_COLOR`, `TERM=dumb`, or when stdout is not a TTY.
