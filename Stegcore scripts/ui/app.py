# Copyright (C) 2025 Mercury
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: ui/app.py
# Description: Main application window.
#              Owns the root CTk window and delegates all flow logic
#              to ui/embed_flow.py and ui/extract_flow.py.

import customtkinter as customtk
from PIL import Image, ImageTk

from core.utils import asset
from ui import embed_flow, extract_flow

customtk.set_appearance_mode("System")
customtk.set_default_color_theme("dark-blue")


class StegApp(customtk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Stegcore")
        self.resizable(False, False)
        self._load_icon()
        self._build_ui()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _load_icon(self) -> None:
        """Load the app icon, compatible with both script and PyInstaller exe."""
        try:
            icon_image = Image.open(asset("Stag.ico"))
            self._icon = ImageTk.PhotoImage(icon_image)
            self.iconphoto(True, self._icon)
        except Exception:
            pass  # Icon is cosmetic — silently skip if missing

    def _build_ui(self) -> None:
        frame = customtk.CTkFrame(self)
        frame.pack(pady=20, padx=20, fill="both", expand=True)

        customtk.CTkLabel(
            master=frame,
            text="Stegcore",
            font=("Consolas", 22, "bold"),
        ).pack(pady=(20, 4))

        customtk.CTkLabel(
            master=frame,
            text="Crypto-steganography for sensitive data",
            font=("Consolas", 11),
            text_color="gray",
        ).pack(pady=(0, 24))

        customtk.CTkButton(
            master=frame,
            command=self._on_embed,
            text="Embed",
            font=("Consolas", 19),
            width=200,
        ).pack(padx=60, pady=(0, 14))

        customtk.CTkButton(
            master=frame,
            command=self._on_extract,
            text="Extract",
            font=("Consolas", 19),
            width=200,
        ).pack(padx=60, pady=(0, 24))

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_embed(self) -> None:
        embed_flow.run(parent=self)

    def _on_extract(self) -> None:
        extract_flow.run()