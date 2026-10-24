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


@dataclass(frozen=True, slots=True)
class FreeText:
    """An option that opens an inline text field instead of returning a value.

    The typed text is returned directly. See
    [`select`][pycli.select] and [`textbox`][pycli.textbox].

    Attributes:
        label: The text displayed in the option list.
        placeholder: Hint shown dimmed while the field is empty.
        default: Initial field contents.
        allow_empty: Whether submitting an empty value is allowed.
    """

    label: str = "Other"
    placeholder: str = ""
    default: str = ""
    allow_empty: bool = False


def _is_free_text(option: Option[object]) -> bool:
    """Whether a normalized option is a `FreeText` marker.

    Args:
        option: A normalized option.

    Returns:
        `True` when the option's value is a `FreeText` marker.
    """
    return isinstance(option.value, FreeText)


def _free_text(option: Option[object]) -> FreeText:
    """Return the `FreeText` marker carried by a normalized option.

    Args:
        option: A normalized option created from a `FreeText` marker.

    Returns:
        The marker with its label, placeholder, default, and empty-value policy.

    Raises:
        TypeError: ``option`` is not a free-text option.
    """
    if not isinstance(option.value, FreeText):
        raise TypeError("option is not a FreeText option")
    return option.value


def normalize_options(
    options: Sequence[object],
    *,
    allow_free_text: bool = False,
) -> list[Option[object]]:
    """Accept strings, ``(value, label)`` pairs, `Option`, or `FreeText`.

    Strings use the string as both value and label; pairs use the second item
    as the label after converting it with `str`. A `FreeText` marker is stored
    as an option whose value is the marker itself, so widgets can recognize it
    without changing `Option`.

    Args:
        options: The sequence supplied by the caller.
        allow_free_text: Whether `FreeText` markers are accepted. Widgets that
            cannot return typed text leave this `False`.

    Returns:
        A list of `Option` objects in input order.

    Raises:
        TypeError: An item is not a supported form, or a `FreeText` marker was
            supplied while ``allow_free_text`` is `False`.
    """
    normalized: list[Option[object]] = []
    for item in options:
        if isinstance(item, FreeText):
            if not allow_free_text:
                raise TypeError("FreeText options are not supported by this prompt")
            normalized.append(Option(item, item.label))
        elif isinstance(item, Option):
            normalized.append(item)
        elif isinstance(item, str):
            normalized.append(Option(item, item))
        elif isinstance(item, tuple) and len(item) == 2:
            value, label = item
            normalized.append(Option(value, str(label)))
        else:
            raise TypeError(
                "options must be strings, (value, label) pairs, Option objects, "
                f"or FreeText markers; got {item!r}"
            )
    return normalized
