"""Watches for anything written to disk, using Python's audit hooks.

Audit hooks see every file opened for writing and every temporary file created,
anywhere in the process. The hook is idle except inside watch_disk_writes().
"""

import os
import sys
from contextlib import contextmanager

WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND
_watching = False
_writes: list[tuple] = []


def _hook(event: str, args: tuple) -> None:
    if not _watching:
        return
    if event == "open":
        path, mode, flags = args
        if isinstance(path, int):
            # Reopening an already-open descriptor, such as the pipe to a helper program.
            # It can't create a file: making one needs a path, and those are all checked.
            return
        if isinstance(mode, str) and any(c in mode for c in "wax+"):
            _writes.append((event, path, mode))
        elif mode is None and isinstance(flags, int) and flags & WRITE_FLAGS:
            _writes.append((event, path, flags))
    elif event in ("tempfile.mkstemp", "tempfile.mkdtemp", "os.mkdir"):
        _writes.append((event, *args))


sys.addaudithook(_hook)  # audit hooks can't be removed, so this one is switched on and off


@contextmanager
def watch_disk_writes():
    """Collects every disk write made inside the block into the list it yields."""
    global _watching
    _writes.clear()
    _watching = True
    try:
        yield _writes
    finally:
        _watching = False
