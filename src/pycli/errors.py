"""Exceptions raised by pycli."""

from __future__ import annotations


class PycliError(Exception):
    """Base class for all pycli errors.

    Catching this handles every pycli-specific failure, including `Cancelled`
    and `NotInteractive`. Invalid arguments raise the built-in `ValueError` or
    `TypeError` instead, and Ctrl-C raises the built-in `KeyboardInterrupt`.
    """


class Cancelled(PycliError):
    """The user cancelled the prompt (typically with Escape).

    Also raised when the input stream closes while a prompt is waiting. Treat
    it as normal control flow rather than a crash: the terminal has already
    been restored when it propagates.
    """


class NotInteractive(PycliError):
    """An interactive prompt was requested without a usable terminal.

    Raised before any terminal state is modified, so callers running under a
    pipe, cron, or CI can catch it and fall back to non-interactive defaults.
    """
