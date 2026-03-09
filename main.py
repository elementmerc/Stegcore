# Copyright (C) 2026 Daniel Iwugo
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: main.py
# Description: Entry point. Launches the Stegcore GUI.

import sys
from pathlib import Path

def _launch_gui() -> None:
    from ui.app import StegApp
    app = StegApp()
    app.mainloop()

def _launch_cli() -> None:
    from cli import app
    app()

def main() -> None:
    name = Path(sys.argv[0]).stem.lower()
    if name == "stegcore-gui" or "--gui" in sys.argv:
        _launch_gui()
    else:
        _launch_cli()

if __name__ == "__main__":
    main()