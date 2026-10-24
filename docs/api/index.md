# API reference

Everything documented here is part of the public surface. The import name
`pycli` is stable; the distribution may be renamed before its first release.

## Modules

| Module | What it contains |
|---|---|
| [`pycli`][pycli.select] | The prompts, `clear_lines`, and the exception hierarchy |
| [`pycli.term`][pycli.term] | `Terminal`, the backend protocol, `Size`, `ReadResult` |
| [`pycli.term.ansi`][pycli.term.ansi] | ANSI constants and cursor helpers |
| [`pycli.input`][pycli.input] | `Parser`, `Key`, `KeyType` |
| [`pycli.render`][pycli.render] | `LiveRegion`, `display_width`, `sanitize`, `truncate` |
| [`pycli.widgets`][pycli.widgets] | Prompt classes, `Option`, `FreeText`, `normalize_options` |
| [`pycli.widgets.base`][pycli.widgets.base.Prompt] | The `Prompt` protocol for custom widgets |
| [`pycli.style`][pycli.style] | `Theme`, `default_theme` |
| [`pycli.app`][pycli.app] | `App`, the prompt event loop |

## Top-level names

| Name | Kind |
|---|---|
| [`select`][pycli.select] | function |
| [`checkbox`][pycli.checkbox] | function |
| [`textbox`][pycli.textbox] | function |
| [`confirm`][pycli.confirm] | function |
| [`clear_lines`][pycli.clear_lines] | function |
| [`PycliError`][pycli.PycliError] | exception |
| [`Cancelled`][pycli.Cancelled] | exception |
| [`NotInteractive`][pycli.NotInteractive] | exception |
| `__version__` | `str`, currently `"0.1.0"` |

## Stability

The package is at M0. The documented names are the intended public API and are
unlikely to disappear, but signatures may still gain keyword-only arguments.
Anything whose name starts with an underscore is internal and may change
without notice, including the platform modules `pycli.term.posix` and
`pycli.term.windows`.
