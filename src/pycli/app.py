"""The prompt event loop."""

from __future__ import annotations

from collections import deque

from .errors import Cancelled
from .input.keys import Key
from .input.parser import Parser
from .render.screen import LiveRegion
from .term.base import TerminalProtocol
from .widgets.base import Prompt

# Keys typed ahead of the next prompt are kept here so chaining prompts does not
# silently drop input that arrived in the same terminal read as the submit key.
_pending_keys: deque[Key] = deque()


class App[T]:
    """Run one prompt until it returns a value or is cancelled.

    The loop draws the prompt into a `LiveRegion`, waits for input, decodes it
    with a `Parser`, and dispatches keys to the prompt. Keys typed ahead of the
    next prompt are buffered at module level so chained prompts do not drop
    input that arrived in the same terminal read. That buffer is cleared when a
    prompt raises, and it is not thread-safe.

    Args:
        prompt: The widget to drive. Any object implementing `Prompt` works.
        terminal: An already-entered terminal. `App` never calls `enter` or
            `restore`; the caller owns the lifecycle.
        poll_interval: How long each input read waits before the parser is
            ticked for a timed-out Escape. Defaults to 0.05 seconds.

    Example:
        ```python
        from pycli.app import App
        from pycli.term import Terminal

        with Terminal() as term:
            value = App(MyPrompt(), term).run()
        ```
    """

    def __init__(
        self,
        prompt: Prompt[T],
        terminal: TerminalProtocol,
        *,
        poll_interval: float = 0.05,
    ) -> None:
        self._prompt = prompt
        self._terminal = terminal
        self._poll_interval = poll_interval

    def run(self) -> T:
        """Run the prompt until it produces a value.

        Returns:
            The value returned by `Prompt.handle_key`.

        Raises:
            Cancelled: The prompt cancelled, or the input stream closed.
            KeyboardInterrupt: The user pressed Ctrl-C.
        """
        parser = Parser()
        region = LiveRegion(self._terminal)
        try:
            while True:
                region.draw(self._prompt.render(self._terminal.size()))
                while True:
                    keys = self._next_keys(parser)
                    if keys is None:
                        break
                    for index, key in enumerate(keys):
                        value = self._prompt.handle_key(key)
                        if value is not None:
                            _pending_keys.extend(keys[index + 1 :])
                            return value
                    if keys:
                        break
        except BaseException:
            _pending_keys.clear()
            raise
        finally:
            region.clear()

    def _next_keys(self, parser: Parser) -> list[Key] | None:
        """Return keys, ``[]`` when idle, or ``None`` when a redraw is needed."""
        if _pending_keys:
            keys = list(_pending_keys)
            _pending_keys.clear()
            return keys

        result = self._terminal.read(self._poll_interval)
        if result.eof:
            raise Cancelled("terminal input closed")
        if result.resized:
            return None
        return parser.feed(result.data) if result.data else parser.tick()
