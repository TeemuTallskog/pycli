# pycli

Pure-Python building blocks for interactive command-line tools: arrow-key menus,
checkboxes, confirmations, and the terminal primitives underneath them.

No C extensions, no curses, no required UI framework. The only runtime
dependency is [`wcwidth`](https://pypi.org/project/wcwidth/) for correct display
width of wide characters and emoji.

> Status: early M0 spike. The core terminal layer, escape-sequence parser,
> inline renderer, `clear_lines`, and `select` / `confirm` / `checkbox` prompts
> are working. `text`, spinners, and full-screen layout are next.

## Quick start

```bash
# SSH (requires a key on your GitHub account)
git clone git@github.com:TeemuTallskog/pycli.git

# ...or HTTPS (no SSH key needed)
git clone https://github.com/TeemuTallskog/pycli.git

cd pycli
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python examples/spike.py
```

```python
from pycli import checkbox, confirm, select

env = select("Deploy to?", ["development", "staging", "production"])
services = checkbox("Services", ["api", "web", "worker"], min_selected=1)

if confirm(f"Deploy {', '.join(services)} to {env}?"):
    print(f"Deploying {services} to {env}...")
```

`select` accepts either a sequence of strings or `(value, label)` pairs:

```python
region = select("Region", [("eu-west-1", "Europe"), ("us-east-1", "US")])
```

The user can cancel with `Esc`, which raises `pycli.Cancelled`; `Ctrl-C` raises
`KeyboardInterrupt` after the terminal has been restored. When stdin is not a
TTY, prompts raise `pycli.NotInteractive` rather than silently choosing a value.

## Documentation

The API reference and guides live in `docs/` and are built with MkDocs and
mkdocstrings:

```bash
.venv/bin/pip install -e ".[docs]"
.venv/bin/mkdocs serve
```

The generated site covers the prompts, the terminal layer, input decoding,
inline rendering, and every public symbol. `mkdocs build --strict` is the
link-checking build used before release.

## Terminal primitives

```python
from pycli.term import Terminal

with Terminal() as term:
    term.write("working...\r\n")
    term.write("\x1b[1A\x1b[2K")  # move up, erase line
    term.write("done!\r\n")
```

`Terminal` handles raw mode, cursor visibility, bracketed paste, `SIGWINCH`
resize wakeups, and guarantees restoration via `finally`, `atexit`, and
`SIGTERM`/`SIGHUP` handlers.

For the common "replace the last N lines" case there is a one-liner:

```python
from pycli import clear_lines

print("step 1\nstep 2")
clear_lines(2)  # cursor is now where "step 1" started
```

This only works while the lines are still in the viewport; anything that has
already scrolled into the terminal's scrollback is gone. Use
`Terminal(alt_screen=True)` for full-screen applications.

## Design

- **Zero C/C++.** Raw mode via `termios`, rendering via ANSI escape sequences.
- **Diff-free inline rendering for now.** `LiveRegion` tracks its height and
  erases/redraws only its own block; a line-level diff renderer comes next.
- **Viewport-safe.** `clear_lines` style operations only touch what is still on
  screen; content that scrolled into scrollback cannot be restored.
- **Non-TTY aware.** Interactive prompts refuse to corrupt pipes and CI logs.
- **Platform-isolated.** POSIX is the supported backend. A best-effort Windows
  backend lives in `pycli/term/windows.py` behind the same interface.
- **Python 3.12+.**

## Layout

```
src/pycli/
  term/      Terminal lifecycle, ANSI primitives, platform backends
  input/     Incremental byte -> key parser
  render/    Inline live region, width-aware truncation
  widgets/   select, checkbox, confirm
tests/       Parser fixtures, renderer snapshots, real-PTY integration tests
```

## Roadmap

| Milestone | Scope |
|---|---|
| M0 | Terminal core, parser, inline renderer, `clear_lines`, `select` / `confirm` / `checkbox` (current) |
| M1 | Line-level diff rendering, resize robustness, full-screen alt-buffer helpers |
| M2 | `text` input with validation and secret mode |
| M3 | `spinner` / `progress`, theme and color downgrade |
| M4 | Windows backend hardening, mouse, bracketed-paste edge cases |
| M5 | Docs, examples, CI matrix, PyPI release |

The distribution name `pycli` is already used on PyPI; a release name will be
chosen before publishing. The import name stays `pycli`.

## Tests

```bash
.venv/bin/pytest
```

The suite includes real PTY integration tests: a child process is spawned on a
pseudo-terminal, keys are sent, and the rendered output plus terminal-state
restoration are asserted.
