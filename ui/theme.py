# Copyright (C) 2026 Daniel Iwugo
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: ui/theme.py
# Description: Centralised theme definitions and active-theme accessor.
#              Imported by app.py, embed_flow.py, and extract_flow.py.
#              Kept as a standalone module to avoid circular imports.

import customtkinter as customtk

THEMES = {
    "dark": {
        "BG":      "#070d14",
        "CARD":    "#0a1520",
        "CARD2":   "#0d1a26",
        "BORDER":  "#0f1f30",
        "BORDER2": "#1a2e42",
        "ACCENT":  "#2a7fff",
        "ACCENT2": "#1aaa7f",
        "TEXT":    "#e2eaf5",
        "TEXT2":   "#8a9bb0",
        "MUTED":   "#3a5570",
        "DIM":     "#1a2a3a",
        "WARN":    "#e67e22",
        "GOOD":    "#2ecc71",
        "DANGER":  "#e03030",
        "mode":    "dark",
    },
    "light": {
        "BG":      "#f0f4fa",
        "CARD":    "#ffffff",
        "CARD2":   "#e8eef8",
        "BORDER":  "#cbd5e8",
        "BORDER2": "#a0aec0",
        "ACCENT":  "#2a7fff",
        "ACCENT2": "#0e9f6e",
        "TEXT":    "#111827",
        "TEXT2":   "#374151",
        "MUTED":   "#6b7280",
        "DIM":     "#e2e8f0",
        "WARN":    "#d97706",
        "GOOD":    "#059669",
        "DANGER":  "#cc0000",
        "mode":    "light",
    },
}

_current: str = "dark"


def get_theme() -> dict:
    # Return the currently active theme dict
    return THEMES[_current]


def current_name() -> str:
    return _current


def toggle() -> str:
    # Toggle between dark and light. Returns new theme name.
    global _current
    _current = "light" if _current == "dark" else "dark"
    customtk.set_appearance_mode(THEMES[_current]["mode"])
    return _current


def apply_initial() -> None:
    # Call once at startup to set customtkinter appearance.
    customtk.set_appearance_mode(THEMES[_current]["mode"])
    customtk.set_default_color_theme("dark-blue")