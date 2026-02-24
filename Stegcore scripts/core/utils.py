# Copyright (C) 2025 Mercury
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
# Resolves correctly both when running as a plain script and as a
# PyInstaller bundle (_MEIPASS is set by PyInstaller at runtime).
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

    Usage:
        with temp_file(".bin") as tmp:
            tmp.write_bytes(data)
            do_something(tmp)
        # file is deleted here automatically
    """
    tmp = Path(tempfile.mktemp(suffix=suffix))
    try:
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