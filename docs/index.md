# pycli

Pure-Python building blocks for interactive command-line tools: arrow-key menus,
checkboxes, confirmations, free-form text input, and the terminal primitives
underneath them.

No C extensions, no curses, no required UI framework. The only runtime
dependency is [`wcwidth`](https://pypi.org/project/wcwidth/) for correct display
width of wide characters and emoji.

!!! note "Status"

    Early M0. The terminal layer, escape-sequence parser, inline renderer,
    `clear_lines`, and the `select` / `confirm` / `checkbox` / `textbox`
    prompts are working. Spinners and full-screen layout are not implemented
    yet.

## Install

`pycli` is not published yet, so install it from the repository:

```bash
# SSH (requires a key on your GitHub account)
git clone git@github.com:TeemuTallskog/pycli.git

# ...or HTTPS (no SSH key needed)
git clone https://github.com/TeemuTallskog/pycli.git

cd pycli
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

To build these docs locally:

```bash
.venv/bin/pip install -e ".[docs]"
.venv/bin/mkdocs serve
```

`pycli` requires Python 3.12 or newer. POSIX is the supported platform; the
Windows backend is experimental.

## Quick start

```python
from pycli import checkbox, confirm, select

env = select("Deploy to?", ["development", "staging", "production"])
services = checkbox("Services", ["api", "web", "worker"], min_selected=1)

if confirm(f"Deploy {', '.join(services)} to {env}?"):
    print(f"Deploying {services} to {env}...")
```

Prompts draw in place, clean up after themselves, and return plain Python
values. The user can cancel with `Esc`, which raises
[`Cancelled`][pycli.Cancelled]; `Ctrl-C` raises `KeyboardInterrupt` after the
terminal has been restored. When stdin or stdout is not a TTY, prompts raise
[`NotInteractive`][pycli.NotInteractive] instead of silently choosing a value.

## What is included

| Area | Entry points |
|---|---|
| Prompts | [`select`][pycli.select], [`checkbox`][pycli.checkbox], [`textbox`][pycli.textbox], [`confirm`][pycli.confirm] |
| Errors | [`PycliError`][pycli.PycliError], [`Cancelled`][pycli.Cancelled], [`NotInteractive`][pycli.NotInteractive] |
| Output helpers | [`clear_lines`][pycli.clear_lines] |
| Terminal layer | [`Terminal`][pycli.term.Terminal], [`TerminalProtocol`][pycli.term.TerminalProtocol], [`Size`][pycli.term.Size], [`ReadResult`][pycli.term.ReadResult] |
| Input decoding | [`Parser`][pycli.input.Parser], [`Key`][pycli.input.Key], [`KeyType`][pycli.input.KeyType] |
| Rendering | [`LiveRegion`][pycli.render.LiveRegion], [`display_width`][pycli.render.display_width], [`sanitize`][pycli.render.sanitize], [`truncate`][pycli.render.truncate] |
| Styling | [`Theme`][pycli.style.Theme], [`default_theme`][pycli.style.default_theme] |

## Guides

- [Prompts](guides/prompts.md) — options, defaults, validation, key bindings,
  cancellation, and custom themes.
- [Terminal](guides/terminal.md) — raw mode, restoration, resize handling,
  reading input, and `clear_lines`.
- [Custom widgets](guides/custom-widgets.md) — implementing the `Prompt`
  protocol and driving it with `App` / `LiveRegion`.
- [Errors](guides/errors.md) — the exception hierarchy and every condition that
  raises.

The full API is in the [API reference](api/index.md). For design notes, the
roadmap, and test instructions, see the project `README.md`.
