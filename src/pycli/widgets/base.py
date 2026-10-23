"""Widget protocol shared by all prompts."""

from __future__ import annotations

from typing import Protocol, TypeVar

from ..input.keys import Key
from ..term.base import Size

T_co = TypeVar("T_co", covariant=True)


class Prompt(Protocol[T_co]):
    """A stateful prompt rendered inside an `App`.

    Renders the current state, consumes key events, and returns a result when
    the user submits. Cancellation is signalled by raising `Cancelled`.
    """

    def render(self, size: Size) -> list[str]:
        """Return the lines for the current state.

        Called on every redraw, including after a resize, so it should be cheap
        and free of side effects.

        Args:
            size: Current terminal size, for viewport decisions.

        Returns:
            One string per line to draw, without trailing newlines.
        """
        ...

    def handle_key(self, key: Key) -> T_co | None:
        """Apply a key press to the prompt state.

        Args:
            key: The decoded key event.

        Returns:
            The prompt result when the user submits, or `None` to keep running.

        Raises:
            Cancelled: The user cancelled the prompt.
            KeyboardInterrupt: The user pressed Ctrl-C.
        """
        ...
