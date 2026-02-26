# Copyright (C) 2026 Daniel Iwugo
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: ui/app.py
# Description: Main application window and navigation controller.

import threading
import customtkinter as customtk
from PIL import Image, ImageTk

from core.utils import asset
from ui.theme import get_theme, toggle, current_name, apply_initial

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

apply_initial()

# Deferred — embed_flow / extract_flow import from ui.theme only (no circular dep)
from ui import embed_flow, extract_flow 


class StegApp(customtk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Stegcore")
        self.resizable(True, True)
        self.minsize(480, 640)
        self.geometry("500x700")

        t = get_theme()
        self.configure(fg_color=t["BG"])

        self._flow  = None
        self._step  = 0
        self._steps = []

        self._load_icon()
        self._build_chrome()
        self.show_home()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _load_icon(self) -> None:
        try:
            icon_image = Image.open(asset("Stag.ico"))
            self._icon = ImageTk.PhotoImage(icon_image)
            self.iconphoto(True, self._icon)
        except Exception:
            pass

    def _build_chrome(self) -> None:
        t = get_theme()

        # Top bar
        self._topbar = customtk.CTkFrame(
            self, fg_color=t["CARD"], height=54, corner_radius=0)
        self._topbar.pack(fill="x", side="top")
        self._topbar.pack_propagate(False)

        # Logo
        logo = customtk.CTkFrame(self._topbar, fg_color="transparent")
        logo.pack(side="left", padx=(12, 0), pady=11)

        badge = customtk.CTkFrame(
            logo, width=28, height=28, corner_radius=7,
            fg_color=t["ACCENT"])
        badge.pack(side="left")
        badge.pack_propagate(False)
        try:
            _ico = Image.open(asset("Stag.ico")).convert("RGBA").resize((20, 20), Image.LANCZOS)
            _ctk_ico = customtk.CTkImage(light_image=_ico, dark_image=_ico, size=(20, 20))
            customtk.CTkLabel(badge, image=_ctk_ico, text="").pack(expand=True)
        except Exception:
            customtk.CTkLabel(
                badge, text="S", font=("Consolas", 12, "bold"), text_color="white",
            ).pack(expand=True)

        customtk.CTkLabel(
            logo, text="stegcore",
            font=("Consolas", 15, "bold"),
            text_color="#000000" if t["mode"] == "light" else t["TEXT"],
        ).pack(side="left", padx=(8, 0))

        # Theme toggle
        self._theme_btn = customtk.CTkButton(
            self._topbar,
            text="☀" if current_name() == "dark" else "☾",
            width=32, height=32,
            fg_color="transparent", hover_color=t["CARD2"],
            text_color=t["TEXT2"], font=("Consolas", 15),
            command=self._on_toggle_theme,
        )
        self._theme_btn.pack(side="right", padx=(0, 10))

        # Step progress bar — right of top bar
        self._progress_frame = customtk.CTkFrame(
            self._topbar, fg_color="transparent")
        self._progress_frame.pack(side="right", padx=10, fill="y")

        # Content area
        self._content_area = customtk.CTkFrame(
            self, fg_color=t["BG"], corner_radius=0)
        self._content_area.pack(fill="both", expand=True)
        self._current_frame = None

        # Bottom navigation bar — shown only during flows
        self._bottombar = customtk.CTkFrame(
            self, fg_color=t["CARD"], height=62, corner_radius=0)

        self._back_flow_btn = customtk.CTkButton(
            self._bottombar, text="← Back", width=110, height=38,
            fg_color=t["CARD2"], hover_color=t["BORDER2"],
            text_color=t["TEXT2"], border_width=1, border_color=t["BORDER2"],
            font=("Consolas", 13), command=self._on_back,
        )
        self._continue_btn = customtk.CTkButton(
            self._bottombar, text="Continue", width=150, height=38,
            fg_color=t["ACCENT"], hover_color="#3a8fff",
            text_color="white", font=("Consolas", 14, "bold"),
            command=self._on_continue,
        )

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _on_toggle_theme(self) -> None:
        new = toggle()
        self._theme_btn.configure(text="☀" if new == "dark" else "☾")
        self._rebuild_theme()

    def _rebuild_theme(self) -> None:
        t = get_theme()
        self.configure(fg_color=t["BG"])
        self._topbar.configure(fg_color=t["CARD"])
        self._content_area.configure(fg_color=t["BG"])
        self._bottombar.configure(fg_color=t["CARD"])
        self._theme_btn.configure(hover_color=t["CARD2"], text_color=t["TEXT2"])
        self._back_flow_btn.configure(
            fg_color=t["CARD2"], hover_color=t["BORDER2"],
            text_color=t["TEXT2"], border_color=t["BORDER2"])
        if self._flow is None:
            self.show_home()
        else:
            self._render_step()

    # ------------------------------------------------------------------
    # Frame management
    # ------------------------------------------------------------------

    def set_frame(self, frame: customtk.CTkFrame) -> None:
        if self._current_frame is not None:
            self._current_frame.destroy()
        frame.pack(fill="both", expand=True)
        self._current_frame = frame

    # ------------------------------------------------------------------
    # Progress bar
    # ------------------------------------------------------------------

    def _update_dots(self, step: int, total: int, color: str) -> None:
        # Clean segmented dot bar
        for w in self._progress_frame.winfo_children():
            w.destroy()

        t = get_theme()
        row = customtk.CTkFrame(self._progress_frame, fg_color="transparent")
        row.pack(fill="both", expand=True)

        dots = customtk.CTkFrame(row, fg_color="transparent")
        dots.place(relx=0.5, rely=0.5, anchor="center")

        for i in range(total):
            is_done    = i < step
            is_current = i == step
            w   = 22 if is_current else 8
            col = color if (is_done or is_current) else t["DIM"]
            customtk.CTkFrame(
                dots, width=w, height=4,
                corner_radius=2, fg_color=col,
            ).pack(side="left", padx=2)

    # ------------------------------------------------------------------
    # Nav show/hide
    # ------------------------------------------------------------------

    def _show_nav(self, step: int, total: int, color: str) -> None:
        self._update_dots(step, total, color)

        self._bottombar.pack(fill="x", side="bottom")
        self._bottombar.pack_propagate(False)
        self._bottombar.update_idletasks()

        # Back button always visible in bottom bar so the user can return to 
        # home if they chose the wrong flow
        self._back_flow_btn.pack(side="left", padx=(14, 8), pady=12)

        self._continue_btn.pack(side="right", padx=(8, 14), pady=12)
        t = get_theme()
        self._continue_btn.configure(
            fg_color=color,
            hover_color="#3a8fff" if color == t["ACCENT"] else "#1abc8f",
        )

    def _hide_nav(self) -> None:
        for w in self._progress_frame.winfo_children():
            w.destroy()
        self._bottombar.pack_forget()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _render_step(self) -> None:
        t     = get_theme()
        total = len(self._steps)
        step  = self._step
        color = t["ACCENT"] if isinstance(self._flow, embed_flow.EmbedFlow) else t["ACCENT2"]
        self._show_nav(step, total, color)
        is_last = step == total - 1
        self._continue_btn.configure(
            text=self._flow.action_label if is_last else "Continue",
            state="normal",
        )
        self._back_flow_btn.configure(state="normal")
        _, builder = self._steps[step]
        self.set_frame(builder())

    def _on_back(self) -> None:
        if self._flow is None or self._step == 0:
            self.show_home()
            return
        self._step -= 1
        self._render_step()

    def _on_continue(self) -> None:
        if self._flow is None:
            return
        if not self._flow.validate_step(self._step):
            return
        if self._step < len(self._steps) - 1:
            self._step += 1
            self._render_step()
        else:
            # Disable nav. execute() re-enables on completion or error
            self._continue_btn.configure(text="Working…", state="disabled")
            self._back_flow_btn.configure(state="disabled")
            self.update()
            # execute() does file dialogs on main thread then threads only the
            # heavy steg computation, calling finish_working when done
            self._flow.execute(self)

    # ------------------------------------------------------------------
    # Working screen (shown while execute runs in background)
    # ------------------------------------------------------------------

    def _show_working(self) -> None:
        t     = get_theme()
        color = t["ACCENT"] if isinstance(self._flow, embed_flow.EmbedFlow) else t["ACCENT2"]
        verb  = "Embedding" if isinstance(self._flow, embed_flow.EmbedFlow) else "Extracting"

        frame = customtk.CTkFrame(
            self._content_area, fg_color=t["BG"], corner_radius=0)

        inner = customtk.CTkFrame(frame, fg_color="transparent")
        inner.place(relx=0.5, rely=0.42, anchor="center")

        customtk.CTkLabel(
            inner, text=verb + "…",
            font=("Consolas", 16, "bold"), text_color=t["TEXT"],
        ).pack(pady=(0, 20))

        bar = customtk.CTkProgressBar(
            inner, width=300, height=6, corner_radius=3,
            fg_color=t["DIM"], progress_color=color,
            mode="indeterminate",
        )
        bar.pack()
        bar.start()

        customtk.CTkLabel(
            inner,
            text="Please wait. This may take a moment\nfor large files.",
            font=("Consolas", 11), text_color=t["MUTED"],
            justify="center",
        ).pack(pady=(16, 0))

        self.set_frame(frame)

    def finish_working(self, success: bool, mode: str, error_msg: str = "") -> None:
        # Called via self.after() from the execute thread.
        # Restores nav state then shows success or error.
        self._back_flow_btn.configure(state="normal")
        if success:
            self.show_success(mode)
        else:
            from core.utils import show_error
            show_error(error_msg)
            self.show_home()

    # ------------------------------------------------------------------
    # Screens
    # ------------------------------------------------------------------

    def show_home(self) -> None:
        self._hide_nav()
        self._flow  = None
        self._step  = 0
        self._steps = []
        t = get_theme()

        frame = customtk.CTkFrame(
            self._content_area, fg_color=t["BG"], corner_radius=0)

        # Bottom items packed FIRST so expand=True content doesn't displace them
        #  when window is resized
        customtk.CTkLabel(
            frame, text="v2.0.6",
            font=("Consolas", 10), text_color=t["DIM"],
        ).pack(side="bottom", pady=(0, 6))

        notice_wrapper = customtk.CTkFrame(
            frame, fg_color="transparent", corner_radius=0)
        notice_wrapper.pack(side="bottom", fill="x")

        customtk.CTkFrame(
            notice_wrapper, height=1, fg_color=t["BORDER"],
        ).pack(fill="x")

        customtk.CTkLabel(
            notice_wrapper,
            text="Ascon-128  ·  ChaCha20-Poly1305  ·  AES-256-GCM  ·  Argon2id  ·  Adaptive LSB  ·  Spread Spectrum",
            font=("Consolas", 10), text_color=t["MUTED"],
            justify="center", wraplength=460,
        ).pack(pady=8)

        # The Main Event

        customtk.CTkLabel(
            frame, text="What would you like to do?",
            font=("Consolas", 17, "bold"), text_color=t["TEXT"],
        ).pack(pady=(28, 4), padx=24, anchor="w")
        customtk.CTkLabel(
            frame,
            text="Hide encrypted data inside files, or extract hidden data.",
            font=("Consolas", 12), text_color=t["MUTED"],
            wraplength=420, justify="left",
        ).pack(pady=(0, 20), padx=24, anchor="w")

        for label, sub, color, cmd in [
            ("Embed",   "Hide encrypted text inside a cover file", t["ACCENT"],  self._start_embed),
            ("Extract", "Recover hidden text from a stego file",   t["ACCENT2"], self._start_extract),
        ]:
            card = customtk.CTkFrame(
                frame, fg_color=t["CARD2"], corner_radius=12,
                border_width=1, border_color=t["BORDER"],
            )
            card.pack(fill="x", padx=20, pady=6)

            badge = customtk.CTkFrame(
                card, width=46, height=46, corner_radius=10,
                fg_color=t["DIM"],
            )
            badge.pack(side="left", padx=(16, 12), pady=14)
            badge.pack_propagate(False)
            customtk.CTkLabel(
                badge,
                text="+" if label == "Embed" else "—",
                font=("Consolas", 21, "bold"), text_color=color,
            ).pack(expand=True)

            inner = customtk.CTkFrame(card, fg_color="transparent")
            inner.pack(side="left", fill="both", expand=True, pady=14)
            customtk.CTkLabel(
                inner, text=label,
                font=("Consolas", 15, "bold"), text_color=t["TEXT2"], anchor="w",
            ).pack(anchor="w")
            customtk.CTkLabel(
                inner, text=sub,
                font=("Consolas", 12), text_color=t["MUTED"], anchor="w",
            ).pack(anchor="w", pady=(2, 0))

            customtk.CTkLabel(
                card, text="›", font=("Consolas", 19), text_color=t["BORDER2"],
            ).pack(side="right", padx=14)

            for w in [card, badge, inner]:
                w.bind("<Button-1>", lambda e, c=cmd: c())
                w.bind("<Enter>",
                    lambda e, c=card, col=color: c.configure(border_color=col))
                w.bind("<Leave>",
                    lambda e, c=card: c.configure(border_color=t["BORDER"]))

        self.set_frame(frame)

    def _start_embed(self) -> None:
        self._flow  = embed_flow.EmbedFlow(self)
        self._step  = 0
        self._steps = self._flow.steps
        self._render_step()

    def _start_extract(self) -> None:
        self._flow  = extract_flow.ExtractFlow(self)
        self._step  = 0
        self._steps = self._flow.steps
        self._render_step()

    def show_success(self, mode: str) -> None:
        self._hide_nav()
        t     = get_theme()
        color = t["ACCENT"] if mode == "embed" else t["ACCENT2"]
        label = "Embedding complete" if mode == "embed" else "Extraction complete"
        sub   = "Stego file and key file saved." if mode == "embed" else "Text file saved."

        frame = customtk.CTkFrame(
            self._content_area, fg_color=t["BG"], corner_radius=0)

        inner = customtk.CTkFrame(frame, fg_color="transparent")
        inner.place(relx=0.5, rely=0.42, anchor="center")

        circle = customtk.CTkFrame(
            inner, width=70, height=70, corner_radius=35,
            fg_color="transparent", border_width=2, border_color=color,
        )
        circle.pack(pady=(0, 18))
        circle.pack_propagate(False)
        customtk.CTkLabel(
            circle, text="✓",
            font=("Consolas", 27, "bold"), text_color=color,
        ).pack(expand=True)

        customtk.CTkLabel(
            inner, text=label,
            font=("Consolas", 18, "bold"), text_color=t["TEXT"],
        ).pack()
        customtk.CTkLabel(
            inner, text=sub,
            font=("Consolas", 13), text_color=t["MUTED"],
        ).pack(pady=(4, 28))

        customtk.CTkButton(
            inner, text="Back to Home", width=160, height=38,
            fg_color=color, hover_color=color,
            font=("Consolas", 14, "bold"), text_color="white",
            command=self.show_home,
        ).pack()

        self.set_frame(frame)