# Copyright (C) 2026 Daniel Iwugo
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: core/utils.py
# Description: Shared helpers — path resolution, temp file management, error display.

import sys
import tempfile
import tkinter.messagebox as tkMessageBox
from contextlib import contextmanager
from pathlib import Path


# ---------------------------------------------------------------------------
# Asset path resolution
# ---------------------------------------------------------------------------

BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent))


def asset(filename: str) -> Path:
    """Return the absolute path to a bundled asset file."""
    return BASE_DIR / filename


# ---------------------------------------------------------------------------
# Temp file management
# ---------------------------------------------------------------------------

@contextmanager
def temp_file(suffix: str = ".bin"):
    """
    Context manager that creates a named temporary file and guarantees
    cleanup on exit, even if an exception is raised.

    Uses mkstemp rather than mktemp — mktemp is deprecated and can cause
    memory allocation issues on Linux via glibc.

    Usage:
        with temp_file(".bin") as tmp:
            tmp.write_bytes(data)
            do_something(tmp)
        # file is deleted here automatically
    """
    fd, tmp_str = tempfile.mkstemp(suffix=suffix)
    tmp = Path(tmp_str)
    try:
        # Close the file descriptor immediately — we'll use Path.write_bytes
        # and Path.read_bytes for all I/O, which open/close cleanly each time
        import os
        os.close(fd)
        yield tmp
    finally:
        if tmp.exists():
            tmp.unlink()


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def show_error(message: str) -> None:
    """Display a modal error dialog."""
    tkMessageBox.showerror(title="Stegcore", message=message)


def show_info(message: str) -> None:
    """Display a modal info dialog."""
    tkMessageBox.showinfo(title="Stegcore", message=message)


def ask_confirm(message: str) -> bool:
    """Display a yes/no confirmation dialog. Returns True if user clicked Yes."""
    return tkMessageBox.askyesno(title="Stegcore", message=message)