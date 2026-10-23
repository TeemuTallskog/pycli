"""Minimal PTY harness for integration tests.

Spawns a child process on a pseudo-terminal, waits for a known prompt marker,
writes keystrokes, and returns the raw output.
"""

from __future__ import annotations

import contextlib
import fcntl
import os
import pty
import select
import struct
import subprocess
import sys
import termios
import time
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"


def run_pty(
    code: str,
    keys: bytes,
    *,
    marker: bytes = b"",
    rows: int = 24,
    columns: int = 80,
    timeout: float = 8.0,
) -> tuple[int, bytes]:
    master, slave = pty.openpty()
    fcntl.ioctl(
        slave,
        termios.TIOCSWINSZ,
        struct.pack("HHHH", rows, columns, 0, 0),
    )

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["PYTHONPATH"] = str(SRC)
    env.pop("NO_COLOR", None)
    env.pop("CI", None)

    process = subprocess.Popen(
        [sys.executable, "-c", code],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        env=env,
        close_fds=True,
    )
    os.close(slave)

    output = bytearray()
    sent = False
    started = time.monotonic()
    deadline = started + timeout

    def drain() -> None:
        while True:
            ready, _, _ = select.select([master], [], [], 0.1)
            if not ready:
                return
            try:
                chunk = os.read(master, 65536)
            except OSError:
                return
            if not chunk:
                return
            output.extend(chunk)

    try:
        while time.monotonic() < deadline:
            ready, _, _ = select.select([master], [], [], 0.05)
            if ready:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                output.extend(chunk)

            if not sent:
                ready_to_type = (marker and marker in output) or (time.monotonic() - started >= 1.5)
                if ready_to_type:
                    os.write(master, keys)
                    sent = True

            if process.poll() is not None:
                drain()
                break
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        with contextlib.suppress(OSError):
            os.close(master)

    return process.returncode, bytes(output)
