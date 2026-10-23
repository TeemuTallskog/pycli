# pycli.app

The event loop that drives a [`Prompt`][pycli.widgets.base.Prompt].

```python
from pycli.app import App
from pycli.term import Terminal

with Terminal() as term:
    value = App(MyPrompt(), term).run()
```

`App` does not enter or restore the terminal; the caller owns its lifecycle.

::: pycli.app
    options:
      show_root_heading: false
      members:
        - App
