"""Option normalization shared by select-style widgets."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Option[T]:
    """A value paired with the label shown to the user.

    Attributes:
        value: The object returned to the caller when this option is chosen.
        label: The text displayed in the prompt. Converted with `str` and
            sanitized before rendering.
    """

    value: T
    label: str


def normalize_options(options: Sequence[object]) -> list[Option[object]]:
    """Accept strings, ``(value, label)`` pairs, or `Option` objects.

    The three forms may be mixed in one sequence. Strings use the string as
    both value and label; pairs use the second item as the label after
    converting it with `str`.

    Args:
        options: The sequence supplied by the caller.

    Returns:
        A list of `Option` objects in input order.

    Raises:
        TypeError: An item is not a string, a two-item tuple, or an `Option`.
    """
    normalized: list[Option[object]] = []
    for item in options:
        if isinstance(item, Option):
            normalized.append(item)
        elif isinstance(item, str):
            normalized.append(Option(item, item))
        elif isinstance(item, tuple) and len(item) == 2:
            value, label = item
            normalized.append(Option(value, str(label)))
        else:
            raise TypeError(
                f"options must be strings, (value, label) pairs, or Option objects; got {item!r}"
            )
    return normalized
