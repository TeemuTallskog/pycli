# Errors

All pycli-specific exceptions derive from [`PycliError`][pycli.PycliError]:

```
Exception
└── PycliError
    ├── Cancelled
    └── NotInteractive
```

Interruption is not a `PycliError`: `Ctrl-C` deliberately raises the built-in
`KeyboardInterrupt` so normal Python signal handling and exit codes keep
working. Invalid arguments use the built-in `ValueError` / `TypeError`.

## Exceptions

### [`PycliError`][pycli.PycliError]

Base class. Catch it to handle every pycli-specific failure at once.

```python
from pycli import PycliError

try:
    env = select("Env", ["dev", "prod"])
except PycliError as exc:
    print(f"prompt failed: {exc}")
```

### [`Cancelled`][pycli.Cancelled]

The user dismissed the prompt, typically with `Esc`, or the input stream
closed. It is a normal control-flow signal, not a crash.

```python
from pycli import Cancelled, select

try:
    env = select("Env", ["dev", "prod"])
except Cancelled:
    env = "dev"
```

The message is `"terminal input closed"` when the cause was EOF.

### [`NotInteractive`][pycli.NotInteractive]

An interactive prompt was requested without a usable terminal. Raised before
any terminal state is modified, so it is safe to catch in scripts that may run
under cron, CI, or a pipe.

```python
from pycli import NotInteractive, select

try:
    env = select("Env", ["dev", "prod"])
except NotInteractive:
    env = "dev"  # non-interactive fallback
```

## What raises what

| Condition | Exception |
|---|---|
| `Esc` pressed | `Cancelled` |
| stdin reaches EOF | `Cancelled("terminal input closed")` |
| `Ctrl-C` pressed | `KeyboardInterrupt` |
| stdin or stdout is not a TTY | `NotInteractive` |
| `Terminal.enter()` cannot read or set terminal attributes | `NotInteractive` |
| Prompt gets an empty option sequence | `ValueError` |
| `select(default=...)` is not one of the option values | `ValueError` |
| `select` / `checkbox` gets an unrecognized option item | `TypeError` |
| `checkbox(min_selected=-1)` | `ValueError` |
| `checkbox(max_selected=...)` is less than `min_selected` | `ValueError` |
| `checkbox(min_selected=...)` exceeds the option count | `ValueError` |
| `checkbox(preselected=...)` contains an unknown value | `ValueError` |
| More values are preselected than `max_selected` allows | `ValueError` |

Validation errors are raised before the terminal is entered, so they never
leave the user's terminal in a modified state.
