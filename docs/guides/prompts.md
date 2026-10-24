# Prompts

pycli ships four ready-made prompts:

| Prompt | Returns | Use it for |
|---|---|---|
| [`select`][pycli.select] | one option value or typed text | choosing from a list |
| [`checkbox`][pycli.checkbox] | `list` of option values | choosing any number of items |
| [`textbox`][pycli.textbox] | `str` | free-form single-line input |
| [`confirm`][pycli.confirm] | `bool` | yes/no decisions |

```python
from pycli import checkbox, confirm, select, textbox

env = select("Deploy to?", ["development", "staging", "production"])
services = checkbox("Services", ["api", "web", "worker"], min_selected=1)

if confirm(f"Deploy {', '.join(services)} to {env}?"):
    print(f"Deploying {services} to {env}...")
```

## Passing options

Every prompt accepts the same three option forms, mixed freely:

```python
# Plain strings: the value and the label are the same.
select("Region", ["eu-west-1", "us-east-1"])

# (value, label) pairs: the user sees the label, you get the value back.
select("Region", [("eu-west-1", "Europe"), ("us-east-1", "United States")])

# Option objects, if you prefer an explicit type.
from pycli.widgets import Option

select("Region", [Option("eu-west-1", "Europe"), Option("us-east-1", "United States")])
```

Values can be any object, not just strings. Labels are converted with `str()`
and sanitized before rendering: tabs become four spaces, control characters are
stripped, and only SGR colour/bold sequences are preserved. This means an
untrusted label cannot move the cursor or corrupt the frame.

Passing anything else raises `TypeError`; passing an empty sequence raises
`ValueError`.

[`select`][pycli.select] additionally accepts
[`FreeText`][pycli.widgets.FreeText] markers, which open an inline text field
instead of returning a fixed value. `checkbox` rejects them because it has no
single place to return typed text.

## `select`

```python
from pycli import select

env = select(
    "Deploy to?",
    ["development", "staging", "production"],
    default="staging",
)
```

- Returns the **value** of the highlighted option.
- `default=` must compare equal (`==`) to one of the option values, otherwise
  `ValueError` is raised. Because `None` means "no default", an option whose
  value is actually `None` cannot be preselected this way. Free-text markers are
  not valid `default=` targets; use their own `default=` field instead.
- The list wraps: moving up from the first option lands on the last.
- At most 12 options are shown at once, further limited by the terminal height.
  Hidden options are summarized with `↑ N more` / `↓ N more`, and the selection
  stays centered while scrolling.

| Key | Action |
|---|---|
| `↑` / `k` | move up (wraps) |
| `↓` / `j` | move down (wraps) |
| `Home` / `g` | jump to the first option |
| `End` / `G` | jump to the last option |
| `Page Up` | move up five options |
| `Page Down` | move down five options |
| `Enter` | submit |
| `Esc` | cancel with [`Cancelled`][pycli.Cancelled] |
| `Ctrl-C` | raise `KeyboardInterrupt` |

### Free-text choices

Add a [`FreeText`][pycli.widgets.FreeText] marker when the list should also
accept a value that is not known up front:

```python
from pycli import select
from pycli.widgets import FreeText

env = select(
    "Deploy to?",
    [
        "development",
        "staging",
        FreeText("Other", placeholder="custom environment"),
    ],
)
```

Selecting the marker with Enter opens a single-line editor in place. The typed
text is returned directly, so this example returns either one of the fixed
strings or the custom value. Multiple markers can be mixed with ordinary
options.

`FreeText` accepts these fields:

| Field | Meaning |
|---|---|
| `label` | text shown in the list, default `"Other"` |
| `placeholder` | dimmed hint shown while the field is empty |
| `default` | initial field contents |
| `allow_empty` | allow submitting an empty string, default `False` |

While editing:

| Key | Action |
|---|---|
| `←` / `→` | move the cursor |
| `Home` / `End` | jump to the start / end |
| `Backspace` / `Delete` | delete before / at the cursor |
| `Enter` | submit the typed text |
| `Esc` | leave the editor and return to the list |
| `Ctrl-C` | raise `KeyboardInterrupt` |

A second `Esc`, after leaving the editor, cancels the prompt. Empty submissions
show an inline `Value cannot be empty` error unless `allow_empty=True` is set.
Existing text is discarded when the editor is closed with `Esc`.

## `checkbox`

```python
from pycli import checkbox

services = checkbox(
    "Services",
    ["api", "web", "worker"],
    min_selected=1,
    max_selected=3,
    preselected=["api"],
)
```

- Returns the selected **values** in display order, regardless of the order the
  user toggled them.
- `preselected=` is matched against option values with `==`. An unknown value
  raises `ValueError`.
- `min_selected` and `max_selected` are validated up front (`min_selected` may
  not be negative, exceed the number of options, or exceed `max_selected`) and
  enforced again while the user interacts. Submitting with too few selections
  shows an inline error instead of returning; so does trying to toggle past
  `max_selected`.
- `max_selected=None` (the default) means unlimited.

| Key | Action |
|---|---|
| `↑` / `k` | move up (wraps) |
| `↓` / `j` | move down (wraps) |
| `Home` | jump to the first option |
| `End` | jump to the last option |
| `Space` | toggle the highlighted option |
| `Enter` | submit |
| `Esc` | cancel with [`Cancelled`][pycli.Cancelled] |
| `Ctrl-C` | raise `KeyboardInterrupt` |

Unlike `select`, the checkbox prompt has no `Page Up` / `Page Down` / `g` / `G`
bindings.

## `textbox`

```python
from pycli import textbox

name = textbox(
    "Project name",
    placeholder="my-project",
    default="",
)
```

- Returns the typed `str`.
- `default=` pre-fills the field with the cursor at the end.
- `placeholder=` is shown dimmed while the field is empty.
- `allow_empty=False` (the default) keeps the prompt open and shows an inline
  error when Enter is pressed with no text.
- Long values scroll horizontally, and the caret stays visible on narrow
  terminals.
- Bracketed paste is flattened to one line: line breaks become spaces, tabs
  become four spaces, and escape/control sequences are removed.

| Key | Action |
|---|---|
| printable characters | insert at the cursor |
| `←` / `→` | move the cursor |
| `Home` / `End` | jump to the start / end |
| `Backspace` / `Delete` | delete before / at the cursor |
| `Enter` | submit |
| `Esc` | cancel with [`Cancelled`][pycli.Cancelled] |
| `Ctrl-C` | raise `KeyboardInterrupt` |

## `confirm`

```python
from pycli import confirm

if confirm("Overwrite the file?", default=False):
    ...
```

- `y` / `Y` returns `True` immediately; `n` / `N` returns `False` immediately,
  even when `default` says otherwise.
- `Enter` returns the currently selected value, which starts at `default`.
- `←`, `→`, `Tab`, and `Space` toggle between Yes and No.

## Cancellation and interruption

All four prompts behave the same way:

- `Esc` raises [`Cancelled`][pycli.Cancelled]. The exception is a `select`
  free-text editor, where the first `Esc` returns to the list and the second
  cancels the prompt.
- `Ctrl-C` raises `KeyboardInterrupt` (the terminal has already been restored
  by the time you see it).
- If the input stream closes (`EOF`), the prompt raises `Cancelled("terminal
  input closed")`.
- If stdin or stdout is not a TTY and no terminal was supplied, the prompt
  raises [`NotInteractive`][pycli.NotInteractive] before touching terminal
  state.

```python
from pycli import Cancelled, select

try:
    env = select("Deploy to?", ["development", "production"])
except Cancelled:
    print("nothing to do")
```

Catch `KeyboardInterrupt` separately if you want to exit with a specific status
code instead of a traceback.

## Keys typed ahead

When several prompts run back to back, bytes that arrive in the same terminal
read as the submit key are kept for the next prompt instead of being dropped:

```python
env = select("Env", ["dev", "prod"])
services = checkbox("Services", ["api", "web"])
ok = confirm("Go?")
# Pasting "↓ Enter Space Enter y" fills all three prompts.
```

The type-ahead buffer is module-global. It is cleared when a prompt raises, but
it is not thread-safe, so do not run prompts concurrently in one process.

## Using your own terminal

By default each prompt creates a [`Terminal`][pycli.term.Terminal], enters it,
and restores it afterwards. Pass `terminal=` to reuse an existing one, for
example to run several prompts inside one alternate screen:

```python
from pycli import confirm, select
from pycli.term import Terminal

with Terminal(alt_screen=True) as term:
    env = select("Env", ["dev", "prod"], terminal=term)
    ok = confirm(f"Deploy to {env}?", terminal=term)
```

When you pass `terminal=`, you own its lifecycle: pycli assumes it has already
been entered and will not restore it. This is also the hook used by the test
suite to drive prompts against a fake terminal.

## Theming

Widgets accept a [`Theme`][pycli.style.Theme], a frozen dataclass of ANSI
codes:

```python
from pycli import select
from pycli.style import Theme

theme = Theme(accent="\x1b[35m", bold="\x1b[1m", dim="\x1b[2m")
select("Pick", ["one", "two"], theme=theme)
```

The default is [`default_theme()`][pycli.style.default_theme], which returns a
theme with every code set to `""` when `NO_COLOR` is set, `TERM=dumb`, or
stdout is not a TTY. Note that this checks `sys.stdout`, not a custom terminal's
output stream.
