# Terminal

[`Terminal`][pycli.term.Terminal] is the low-level object every prompt runs on.
It puts the TTY into raw mode, hides the cursor, enables bracketed paste, and
handles resize and termination signals. You do not need it for the built-in
prompts, but it is useful for custom output.

```python
from pycli.term import Terminal, ansi

with Terminal() as term:
    term.write("working...\r\n")
    term.write(ansi.cursor_up() + ansi.erase_line())
    term.write("done!\r\n")
```

Entering is idempotent, and `restore()` undoes everything `enter()` changed.
Using the object as a context manager guarantees `restore()` runs on the way
out.

## Lifecycle

```python
term = Terminal(alt_screen=False)
term.enter()          # raw mode, hidden cursor, bracketed paste
try:
    term.write("hello\r\n")
finally:
    term.restore()    # safe to call twice, and safe from a signal handler
```

`enter()` raises [`NotInteractive`][pycli.NotInteractive] when stdin or stdout
is not a TTY, or when the terminal attributes cannot be read or changed. The
check happens before any state is modified.

### What raw mode changes

On POSIX the backend disables canonical mode, echo, signal generation, and
output post-processing (`OPOST`). Two consequences matter when you use the
terminal directly:

- **`Ctrl-C` arrives as a byte, not a signal.** The prompts translate it into
  `KeyboardInterrupt` after cleanup; a custom loop must do the same.
- **Newlines are not translated.** Write `"\r\n"` explicitly, as in the examples
  above. A bare `"\n"` moves down without returning to column zero.

`ISIG` being off also means `Ctrl-Z`, `Ctrl-\`, and friends are delivered as
input instead of signals.

`write()` encodes with UTF-8 (replacing unencodable characters) and retries
partial writes, so it never leaves half a string on the terminal. It writes
straight to the file descriptor, bypassing Python's buffered `sys.stdout`.

### Restoring

`restore()` is guarded against re-entry and is registered in three places:

1. The `finally` block of the context manager / prompt runner.
2. `atexit`, so an uncaught exception still restores the terminal.
3. `SIGTERM` and `SIGHUP` handlers, which restore and then re-raise the
   signal with its original disposition.

On restore pycli disables bracketed paste, shows the cursor again, leaves the
alternate screen if it was enabled, and restores the saved `termios` attributes.

### Alternate screen

Pass `alt_screen=True` at construction time to render on the terminal's
alternate buffer:

```python
with Terminal(alt_screen=True) as term:
    term.write("full-screen app\r\n")
```

Leaving the context manager returns the user to their previous scrollback. The
flag cannot be changed after construction.

## Size and resize

```python
size = term.size()
print(size.rows, size.columns)
```

[`Size`][pycli.term.Size] is a frozen dataclass of `rows` and `columns` in
character cells. If the size cannot be determined, pycli falls back to 24×80.

Resize events are delivered through a `SIGWINCH` handler backed by a
self-pipe, so they also wake up a blocking `read()`. `read()` reports them with
`ReadResult(resized=True)`. Signal handlers are only installed on the main
thread; a terminal created on another thread still works but will not receive
resize notifications.

## Reading input

```python
result = term.read(timeout=0.05)
if result.eof:
    ...
elif result.resized:
    ...
elif result.data:
    ...
```

[`ReadResult`][pycli.term.ReadResult] has three fields:

| Field | Meaning |
|---|---|
| `data` | raw bytes read, possibly empty |
| `resized` | a `SIGWINCH` arrived |
| `eof` | stdin closed or became unreadable |

`timeout=None` blocks until input, resize, or EOF. A finite timeout returns an
empty result when nothing happened, which is what lets the prompt loop stay
responsive.

`read()` returns raw bytes; decoding them into key presses is the job of
[`Parser`][pycli.input.Parser]. See
[Custom widgets](custom-widgets.md#the-input-parser).

## Clearing lines

[`clear_lines`][pycli.clear_lines] erases previously written output:

```python
from pycli import clear_lines

print("step 1\nstep 2")
clear_lines(2)  # cursor is now where "step 1" started
```

The cursor is expected to be at the beginning of the line *after* the block.
The helper moves up `count` lines with `CSI F` and erases everything below
with `CSI 0J`.

Limitations:

- Only lines still visible in the viewport can be erased. Content that has
  scrolled into the scrollback is gone.
- `count <= 0` is a no-op.
- When writing to a non-TTY stdout, the call is silently skipped so pipes and
  CI logs are not polluted. Pass `stream=` explicitly to override that check.
- Everything below the cursor is erased too, so do not call it while unrelated
  output sits below the block.

`Terminal` also has a `clear_lines(count=1)` method with the same semantics, for
use when you already hold the terminal.

## Platform support

`from pycli.term import Terminal` selects a backend at import time:

- **POSIX** (`termios`, `select`, `signal`) is the supported backend.
- **Windows** (`msvcrt` plus the Win32 console API) is experimental. It enables
  virtual terminal processing so rendering is identical, but input through
  `msvcrt` cannot yet report every modifier combination, and bracketed paste is
  incomplete.

Both backends implement the same
[`TerminalProtocol`][pycli.term.TerminalProtocol], which is also a convenient
surface to fake in tests.
