# Copyright (C) 2026 Daniel Iwugo
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: main.py
# Description: Entry point. Launches the Stegcore GUI.

import os
import sys
from pathlib import Path


def _is_gui_invocation() -> bool:
    """Determine whether we were invoked as stegcore-gui (or with --gui flag)."""
    name = Path(sys.argv[0]).stem.lower()
    return name == "stegcore-gui" or "--gui" in sys.argv


def _suppress_console() -> None:
    """
    Hide the console window when launching in GUI mode.

    - Windows: FreeConsole() detaches the process from its console window
      immediately. Must be called before any GUI toolkit is imported.
    - Linux/macOS: os.setsid() creates a new session so the terminal doesn't
      wait for the process to exit, but the window itself was never visible
      (the terminal just returns to its prompt). No visual suppression needed.
    """
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.kernel32.FreeConsole()
    else:
        # Detach from the controlling terminal so the shell prompt returns
        # immediately when the user runs `stegcore-gui` from a terminal.
        try:
            os.setsid()
        except OSError:
            pass  # already a session leader (e.g. launched from .app or IDE)


def _launch_gui() -> None:
    from ui.app import StegApp
    app = StegApp()
    app.mainloop()


def _launch_cli() -> None:
    from cli import app
    app()


def main() -> None:
    if _is_gui_invocation():
        _suppress_console()
        _launch_gui()
    else:
        _launch_cli()


if __name__ == "__main__":
    main()