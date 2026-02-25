# Copyright (C) 2026 Daniel Iwugo
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: main.py
# Description: Entry point. Launches the Stegcore GUI.

from ui.app import StegApp

def _launch() -> None:
    """Entry point for the stegcore-gui console script."""
    app = StegApp()
    app.mainloop()


if __name__ == "__main__":
    _launch()