# Copyright (C) 2026 Daniel Iwugo
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: ui/embed_flow.py

import os
from pathlib import Path
from tkinter import filedialog

import customtkinter as customtk

from core import crypto, steg, utils
from ui.theme import get_theme


def _fmt_bytes(n: int) -> str:
    if n >= 1_048_576:
        return f"{n / 1_048_576:.2f} MB"
    if n >= 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n} B"


def _section_label(parent, title: str) -> None:
    customtk.CTkLabel(
        parent, text=title,
        font=("Consolas", 12, "bold"),
        text_color=get_theme()["TEXT2"], anchor="w",
    ).pack(fill="x", padx=24, pady=(16, 4))


def _file_row(parent, label: str, path_var, pick_fn) -> None:
    t = get_theme()
    row = customtk.CTkFrame(parent, fg_color=t["CARD2"], corner_radius=8,
                            border_width=1, border_color=t["BORDER"])
    row.pack(fill="x", padx=24, pady=(0, 4))
    customtk.CTkLabel(
        row, text=label, font=("Consolas", 12),
        text_color=t["MUTED"], width=56, anchor="w",
    ).pack(side="left", padx=(12, 6), pady=10)
    customtk.CTkLabel(
        row, textvariable=path_var,
        font=("Consolas", 12), text_color=t["TEXT2"],
        anchor="w", wraplength=240,
    ).pack(side="left", fill="x", expand=True)
    customtk.CTkButton(
        row, text="Browse", width=72, height=28,
        fg_color=t["DIM"], hover_color=t["BORDER2"],
        text_color=t["ACCENT"], font=("Consolas", 12),
        command=pick_fn,
    ).pack(side="right", padx=8, pady=8)


LABEL_COLOUR_KEY = {
    "Excellent": "GOOD", "Good": "ACCENT",
    "Fair": "WARN",      "Poor": "DANGER",
}


class EmbedFlow:
    action_label = "Embed"

    def __init__(self, app):
        self.app = app

        self.text_path  = None
        self.cover_path = None
        self.metrics    = None

        self.cipher     = customtk.StringVar(value=crypto.SUPPORTED_CIPHERS[0])
        self.mode       = customtk.StringVar(value="adaptive")
        self.deniable   = customtk.BooleanVar(value=False)
        self.passphrase = customtk.StringVar(value="")
        self.pw_confirm = customtk.StringVar(value="")
        self._show_pw   = customtk.BooleanVar(value=False)

        self._text_disp  = customtk.StringVar(value="No file selected")
        self._cover_disp = customtk.StringVar(value="No file selected")

        self.steps = [
            ("Source",  self._build_step1),
            ("Cover",   self._build_step2),
            ("Options", self._build_step3),
            ("Confirm", self._build_step4),
        ]

    # ------------------------------------------------------------------
    # Step 1 — source file
    # ------------------------------------------------------------------

    def _build_step1(self) -> customtk.CTkFrame:
        t = get_theme()
        frame = customtk.CTkFrame(self.app._content_area,
                                  fg_color=t["BG"], corner_radius=0)
        customtk.CTkLabel(
            frame, text="Select source file",
            font=("Consolas", 17, "bold"), text_color=t["TEXT"],
        ).pack(padx=24, pady=(24, 4), anchor="w")
        customtk.CTkLabel(
            frame, text="The text file you want to hide.",
            font=("Consolas", 12), text_color=t["MUTED"],
        ).pack(padx=24, pady=(0, 16), anchor="w")

        _section_label(frame, "TEXT FILE")
        _file_row(frame, "File", self._text_disp, self._pick_text)

        if self.text_path:
            try:
                sz = self.text_path.stat().st_size
                customtk.CTkLabel(
                    frame,
                    text=f"  {self.text_path.name}  ·  {_fmt_bytes(sz)}",
                    font=("Consolas", 11), text_color=t["GOOD"],
                ).pack(padx=24, pady=(2, 0), anchor="w")
            except Exception:
                pass

        return frame

    def _pick_text(self) -> None:
        p = filedialog.askopenfilename(
            title="Select text file",
            filetypes=[("Text files", "*.txt")],
        )
        if p:
            self.text_path = Path(p)
            self._text_disp.set(self.text_path.name)
            self.app._render_step()

    # ------------------------------------------------------------------
    # Step 2 — cover file + score
    # ------------------------------------------------------------------

    def _build_step2(self) -> customtk.CTkFrame:
        t = get_theme()
        frame = customtk.CTkFrame(self.app._content_area,
                                  fg_color=t["BG"], corner_radius=0)
        customtk.CTkLabel(
            frame, text="Select cover file",
            font=("Consolas", 17, "bold"), text_color=t["TEXT"],
        ).pack(padx=24, pady=(24, 4), anchor="w")
        customtk.CTkLabel(
            frame, text="The file your message will be hidden inside.",
            font=("Consolas", 12), text_color=t["MUTED"],
        ).pack(padx=24, pady=(0, 16), anchor="w")

        _section_label(frame, "COVER FILE")
        _file_row(frame, "File", self._cover_disp, self._pick_cover)

        if self.cover_path and self.metrics:
            m     = self.metrics
            col_k = LABEL_COLOUR_KEY.get(m["label"], "TEXT2")
            col   = t[col_k]

            card = customtk.CTkFrame(
                frame, fg_color=t["CARD2"], corner_radius=10,
                border_width=1, border_color=t["BORDER"],
            )
            card.pack(fill="x", padx=24, pady=(8, 0))

            top = customtk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=14, pady=(12, 4))
            customtk.CTkLabel(
                top, text="Cover Score",
                font=("Consolas", 12), text_color=t["MUTED"], anchor="w",
            ).pack(side="left")
            customtk.CTkLabel(
                top, text=f"{m['score']}/100  —  {m['label']}",
                font=("Consolas", 13, "bold"), text_color=col, anchor="e",
            ).pack(side="right")

            bar = customtk.CTkProgressBar(
                card, height=5, corner_radius=2,
                fg_color=t["DIM"], progress_color=col,
            )
            bar.pack(fill="x", padx=14, pady=(0, 10))
            bar.set(m["score"] / 100)

            stats = customtk.CTkFrame(card, fg_color="transparent")
            stats.pack(fill="x", padx=14, pady=(0, 12))
            for lbl, val in [
                ("Entropy",  f"{m['entropy']:.2f}/8"),
                ("Texture",  f"{m['texture_density']*100:.0f}%"),
                ("Adaptive", _fmt_bytes(m["adaptive_capacity"])),
                ("Seq.",     _fmt_bytes(m["sequential_capacity"])),
            ]:
                cf = customtk.CTkFrame(stats, fg_color="transparent")
                cf.pack(side="left", expand=True)
                customtk.CTkLabel(cf, text=lbl, font=("Consolas", 10),
                                  text_color=t["MUTED"]).pack()
                customtk.CTkLabel(cf, text=val, font=("Consolas", 12, "bold"),
                                  text_color=t["TEXT2"]).pack()

            if m["score"] < 35:
                customtk.CTkLabel(
                    frame, text="⚠  Low score. Embedding may be more detectable",
                    font=("Consolas", 11), text_color=t["WARN"],
                ).pack(padx=24, pady=(8, 0), anchor="w")
            if m["adaptive_capacity"] < 1024:
                customtk.CTkLabel(
                    frame,
                    text="⚠  Very low adaptive capacity. Use sequential mode",
                    font=("Consolas", 11), text_color=t["WARN"],
                ).pack(padx=24, pady=(4, 0), anchor="w")

        elif self.cover_path and self.metrics is None:
            customtk.CTkLabel(
                frame, text="Cover scoring not available for this file type.",
                font=("Consolas", 11), text_color=get_theme()["MUTED"],
            ).pack(padx=24, pady=(6, 0), anchor="w")

        return frame

    def _pick_cover(self) -> None:
        p = filedialog.askopenfilename(
            title="Select cover file",
            filetypes=[
                ("All supported", "*.png *.jpg *.jpeg *.bmp *.wav"),
                ("PNG image",     "*.png"),
                ("JPEG image",    "*.jpg *.jpeg"),
                ("WAV audio",     "*.wav"),
            ],
        )
        if p:
            self.cover_path  = Path(p)
            self._cover_disp.set(self.cover_path.name)
            if self.cover_path.suffix.lower() != ".wav":
                try:
                    self.metrics = steg.score_cover_image(self.cover_path)
                except Exception:
                    self.metrics = None
            else:
                self.metrics = None
            self.app._render_step()

    # ------------------------------------------------------------------
    # Step 3 — options
    # ------------------------------------------------------------------

    def _build_step3(self) -> customtk.CTkFrame:
        t = get_theme()
        frame = customtk.CTkFrame(self.app._content_area,
                                  fg_color=t["BG"], corner_radius=0)
        customtk.CTkLabel(
            frame, text="Options",
            font=("Consolas", 17, "bold"), text_color=t["TEXT"],
        ).pack(padx=24, pady=(24, 4), anchor="w")
        customtk.CTkLabel(
            frame, text="Configure encryption and steganography settings.",
            font=("Consolas", 12), text_color=t["MUTED"],
        ).pack(padx=24, pady=(0, 8), anchor="w")

        # Cipher pills
        _section_label(frame, "CIPHER")
        pill_row = customtk.CTkFrame(frame, fg_color="transparent")
        pill_row.pack(fill="x", padx=24, pady=(0, 4))
        for c in crypto.SUPPORTED_CIPHERS:
            is_sel = self.cipher.get() == c
            customtk.CTkButton(
                pill_row, text=c, width=0, height=30,
                fg_color=t["ACCENT"] if is_sel else t["DIM"],
                hover_color=t["BORDER2"],
                text_color=t["TEXT"] if is_sel else t["MUTED"],
                font=("Consolas", 12), border_width=1,
                border_color=t["ACCENT"] if is_sel else t["BORDER"],
                corner_radius=6,
                command=lambda v=c: self._set_cipher(v),
            ).pack(side="left", padx=(0, 6))

        # Steg mode
        _section_label(frame, "STEGANOGRAPHY MODE")
        for val, label, sub in [
            ("adaptive",   "Adaptive",   "Spread spectrum · Steganalysis resistant"),
            ("sequential", "Sequential", "Standard LSB · Maximum capacity"),
        ]:
            is_sel = self.mode.get() == val
            row = customtk.CTkFrame(
                frame,
                fg_color=t["CARD2"] if is_sel else t["CARD"],
                corner_radius=8, border_width=1,
                border_color=t["ACCENT"] if is_sel else t["BORDER"],
            )
            row.pack(fill="x", padx=24, pady=(0, 4))
            customtk.CTkRadioButton(
                row, text="", variable=self.mode, value=val,
                width=0, fg_color=t["ACCENT"], hover_color=t["ACCENT"],
                command=lambda v=val: self._set_mode(v),
            ).pack(side="left", padx=(12, 4), pady=12)
            inner = customtk.CTkFrame(row, fg_color="transparent")
            inner.pack(side="left", pady=12, fill="x", expand=True)
            customtk.CTkLabel(
                inner, text=label,
                font=("Consolas", 13, "bold"),
                text_color=t["TEXT"] if is_sel else t["TEXT2"], anchor="w",
            ).pack(anchor="w")
            customtk.CTkLabel(
                inner, text=sub,
                font=("Consolas", 11), text_color=t["MUTED"], anchor="w",
            ).pack(anchor="w")

        # Deniability
        fmt = self.cover_path.suffix.lower() if self.cover_path else ".png"
        deniable_ok = fmt in {".png", ".bmp"} and self.mode.get() == "adaptive"

        _section_label(frame, "DENIABILITY")
        den_row = customtk.CTkFrame(
            frame, fg_color=t["CARD2"], corner_radius=8,
            border_width=1, border_color=t["BORDER"],
        )
        den_row.pack(fill="x", padx=24, pady=(0, 4))
        customtk.CTkSwitch(
            den_row, text="Dual payload",
            variable=self.deniable,
            font=("Consolas", 13), text_color=t["TEXT2"],
            fg_color=t["DIM"], progress_color=t["ACCENT"],
            state="normal" if deniable_ok else "disabled",
        ).pack(side="left", padx=12, pady=12)
        customtk.CTkLabel(
            den_row,
            text="Adaptive PNG only" if not deniable_ok
                 else "Decoy file + passphrase required",
            font=("Consolas", 11), text_color=t["MUTED"],
        ).pack(side="right", padx=12)

        # Passphrase + confirmation + show/hide toggle
        _section_label(frame, "PASSPHRASE")
        for var, placeholder in [
            (self.passphrase, "Enter passphrase…"),
            (self.pw_confirm, "Confirm passphrase…"),
        ]:
            pw_row = customtk.CTkFrame(
                frame, fg_color=t["CARD2"], corner_radius=8,
                border_width=1, border_color=t["BORDER"],
            )
            pw_row.pack(fill="x", padx=24, pady=(0, 4))

            entry = customtk.CTkEntry(
                pw_row, textvariable=var,
                placeholder_text=placeholder,
                show="●", font=("Consolas", 13),
                fg_color="transparent", border_width=0,
                text_color=t["TEXT"], height=40,
            )
            entry.pack(side="left", fill="x", expand=True, padx=12, pady=4)

            # Store reference so toggle can find it
            if var is self.passphrase:
                self._pw_entry = entry
            else:
                self._pw_confirm_entry = entry

        # Show/hide toggle (shared for both fields)
        toggle_row = customtk.CTkFrame(frame, fg_color="transparent")
        toggle_row.pack(fill="x", padx=24, pady=(0, 4))
        customtk.CTkCheckBox(
            toggle_row, text="Show passphrase",
            variable=self._show_pw,
            font=("Consolas", 11), text_color=t["MUTED"],
            fg_color=t["ACCENT"], hover_color=t["ACCENT"],
            command=self._toggle_pw_visibility,
        ).pack(anchor="w")

        # Passphrase strength hint
        pw = self.passphrase.get()
        if pw:
            if len(pw) < 8:
                hint, col = "Weak. Use at least 8 characters", t["WARN"]
            elif len(pw) < 14:
                hint, col = "Moderate", t["WARN"]
            else:
                hint, col = "Strong", t["GOOD"]
            customtk.CTkLabel(
                frame, text=f"Strength: {hint}",
                font=("Consolas", 11), text_color=col,
            ).pack(padx=24, anchor="w")

        return frame

    def _toggle_pw_visibility(self) -> None:
        show = "" if self._show_pw.get() else "●"
        self._pw_entry.configure(show=show)
        self._pw_confirm_entry.configure(show=show)

    def _set_cipher(self, val: str) -> None:
        self.cipher.set(val)
        self.app._render_step()

    def _set_mode(self, val: str) -> None:
        self.mode.set(val)
        self.app._render_step()

    # ------------------------------------------------------------------
    # Step 4 — confirm
    # ------------------------------------------------------------------

    def _build_step4(self) -> customtk.CTkFrame:
        t = get_theme()
        frame = customtk.CTkFrame(self.app._content_area,
                                  fg_color=t["BG"], corner_radius=0)
        customtk.CTkLabel(
            frame, text="Ready to embed",
            font=("Consolas", 17, "bold"), text_color=t["TEXT"],
        ).pack(padx=24, pady=(24, 4), anchor="w")
        customtk.CTkLabel(
            frame, text="Review your settings before proceeding.",
            font=("Consolas", 12), text_color=t["MUTED"],
        ).pack(padx=24, pady=(0, 16), anchor="w")

        fmt            = self.cover_path.suffix.lower() if self.cover_path else ".png"
        effective_mode = self.mode.get() if fmt in {".png", ".bmp"} else "sequential"
        deniable       = self.deniable.get() and effective_mode == "adaptive"

        rows = [
            ("Source",    self.text_path.name  if self.text_path  else "—"),
            ("Cover",     self.cover_path.name if self.cover_path else "—"),
            ("Cipher",    self.cipher.get()),
            ("Mode",      effective_mode.capitalize()),
            ("Deniable",  "Yes" if deniable else "No"),
            ("Passphrase","Set ✓" if self.passphrase.get() else "⚠  Not set"),
        ]

        card = customtk.CTkFrame(
            frame, fg_color=t["CARD2"], corner_radius=10,
            border_width=1, border_color=t["BORDER"],
        )
        card.pack(fill="x", padx=24)

        for i, (k, v) in enumerate(rows):
            if i > 0:
                customtk.CTkFrame(
                    card, height=1, fg_color=t["BORDER"],
                ).pack(fill="x", padx=14)
            row = customtk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=10)
            customtk.CTkLabel(
                row, text=k, font=("Consolas", 12),
                text_color=t["MUTED"], anchor="w", width=90,
            ).pack(side="left")
            customtk.CTkLabel(
                row, text=v, font=("Consolas", 12, "bold"),
                text_color=(
                    t["GOOD"] if v == "Set ✓" else
                    t["WARN"] if v.startswith("⚠") else t["TEXT2"]
                ),
                anchor="w",
            ).pack(side="left")

        customtk.CTkLabel(
            frame,
            text="You will be prompted to save the stego file\n"
                 "and key file(s) after clicking Embed.",
            font=("Consolas", 11), text_color=t["MUTED"], justify="left",
        ).pack(padx=24, pady=(14, 0), anchor="w")

        return frame

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_step(self, step: int) -> bool:
        if step == 0 and not self.text_path:
            utils.show_error("Please select a source text file.")
            return False
        if step == 1 and not self.cover_path:
            utils.show_error("Please select a cover file.")
            return False
        if step == 2:
            pw = self.passphrase.get().strip()
            if not pw:
                utils.show_error("A passphrase is required.")
                return False
            if pw != self.pw_confirm.get().strip():
                utils.show_error(
                    "Passphrases do not match.\n"
                    "Please re-enter them both carefully.")
                return False
            if len(pw) < 4:
                utils.show_error(
                    "Passphrase is too short.\n"
                    "Use at least 4 characters (8+ recommended).")
                return False
        return True

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    def execute(self, app) -> None:
        """
        All file dialogs run on the main (Tk) thread.
        Only the heavy steg.embed call is dispatched to a worker thread,
        after which remaining dialogs continue on the main thread.
        """
        import threading

        fmt            = self.cover_path.suffix.lower()
        effective_mode = self.mode.get() if fmt in {".png", ".bmp"} else "sequential"
        deniable       = self.deniable.get() and effective_mode == "adaptive"
        cipher         = self.cipher.get()
        passphrase     = self.passphrase.get().strip()
        info_type      = self.text_path.suffix

        def _err(msg):
            """Re-enable nav and show error from any context."""
            def _on_main():
                app._continue_btn.configure(text="Embed", state="normal")
                app._back_flow_btn.configure(state="normal")
                utils.show_error(msg)
                app.show_home()
            app.after(0, _on_main)

        # ── Stage 1: encrypt (fast, main thread) ────────────────────
        try:
            plaintext = self.text_path.read_text(errors="ignore").encode("utf-8")
            result    = crypto.encrypt(plaintext, passphrase, cipher)
        except (ValueError, RuntimeError, OSError) as exc:
            app._continue_btn.configure(text="Embed", state="normal")
            app._back_flow_btn.configure(state="normal")
            utils.show_error(str(exc))
            app.show_home()
            return

        steg_key = result["key"] if effective_mode == "adaptive" else None

        # ── Stage 2: deniable decoy dialogs (main thread) ───────────
        decoy_result   = None
        decoy_key      = None
        partition_seed = None

        if deniable:
            decoy_file = filedialog.askopenfilename(
                title="Select decoy text file",
                filetypes=[("Text files", "*.txt")],
            )
            if not decoy_file:
                app._continue_btn.configure(text="Embed", state="normal")
                app._back_flow_btn.configure(state="normal")
                utils.show_error("No decoy file selected.")
                app._render_step()
                return

            d_dlg = customtk.CTkInputDialog(
                text="Enter the DECOY passphrase\n(must differ from real passphrase):",
                title="Decoy Passphrase",
            )
            decoy_pass = d_dlg.get_input()
            if not decoy_pass or decoy_pass.strip() == passphrase:
                app._continue_btn.configure(text="Embed", state="normal")
                app._back_flow_btn.configure(state="normal")
                utils.show_error(
                    "Decoy passphrase is missing or identical to real passphrase.")
                app._render_step()
                return

            try:
                decoy_text   = Path(decoy_file).read_text(errors="ignore").encode("utf-8")
                decoy_result = crypto.encrypt(decoy_text, decoy_pass.strip(), cipher)
                decoy_key    = decoy_result["key"]
                partition_seed = os.urandom(16)
            except (ValueError, RuntimeError, OSError) as exc:
                app._continue_btn.configure(text="Embed", state="normal")
                app._back_flow_btn.configure(state="normal")
                utils.show_error(f"Could not encrypt decoy: {exc}")
                app.show_home()
                return

        # ── Stage 3: choose output path (main thread) ────────────────
        out_ext = ".wav" if fmt == ".wav" else ".png"
        output_image = filedialog.asksaveasfilename(
            title="Save stego file as",
            defaultextension=out_ext,
            filetypes=(
                [("WAV audio", "*.wav")] if fmt == ".wav"
                else [("PNG image", "*.png")]
            ),
        )
        if not output_image:
            app._continue_btn.configure(text="Embed", state="normal")
            app._back_flow_btn.configure(state="normal")
            app._render_step()
            return

        if Path(output_image).exists():
            if not utils.ask_confirm(
                    f"'{Path(output_image).name}' already exists.\nOverwrite it?"):
                app._continue_btn.configure(text="Embed", state="normal")
                app._back_flow_btn.configure(state="normal")
                app._render_step()
                return

        # ── Stage 4: heavy steg operation in worker thread ──────────
        app._show_working()

        def _do_embed():
            try:
                if deniable:
                    steg.embed_deniable(
                        cover_path=self.cover_path,
                        real_payload=result["ciphertext"],
                        decoy_payload=decoy_result["ciphertext"],
                        output_path=output_image,
                        real_key=steg_key,
                        decoy_key=decoy_key,
                        partition_seed=partition_seed,
                    )
                else:
                    with utils.temp_file(".bin") as tmp:
                        tmp.write_bytes(result["ciphertext"])
                        steg.embed(self.cover_path, tmp, output_image,
                                   key=steg_key, mode=effective_mode)
                # Back on main thread for key file dialogs
                app.after(0, lambda: _save_keys())
            except (ValueError, RuntimeError) as exc:
                app.after(0, lambda msg=str(exc): _err(msg))

        def _save_keys():
            """Runs on main thread after steg completes."""
            key_file = filedialog.asksaveasfilename(
                title="Save key file as",
                defaultextension=".json",
                filetypes=[("Key file", "*.json")],
            )
            if not key_file:
                app._continue_btn.configure(text="Embed", state="normal")
                app._back_flow_btn.configure(state="normal")
                utils.show_error("Operation cancelled. Key file not saved.")
                app.show_home()
                return

            try:
                crypto.write_key_file(
                    key_file,
                    nonce=result["nonce"], salt=result["salt"],
                    cipher=cipher, info_type=info_type,
                    steg_mode=effective_mode, deniable=deniable,
                    partition_seed=partition_seed if deniable else None,
                    partition_half=0 if deniable else None,
                )
            except Exception as exc:
                _err(f"Could not save key file: {exc}")
                return

            if deniable:
                utils.show_info("Real key file saved.\n\nNow save the DECOY key file.")
                decoy_key_file = filedialog.asksaveasfilename(
                    title="Save DECOY key file as",
                    defaultextension=".json",
                    filetypes=[("Key file", "*.json")],
                )
                if not decoy_key_file:
                    app._continue_btn.configure(text="Embed", state="normal")
                    app._back_flow_btn.configure(state="normal")
                    utils.show_error("Decoy key file not saved.")
                    app.show_home()
                    return
                try:
                    crypto.write_key_file(
                        decoy_key_file,
                        nonce=decoy_result["nonce"], salt=decoy_result["salt"],
                        cipher=cipher, info_type=info_type,
                        steg_mode=effective_mode, deniable=deniable,
                        partition_seed=partition_seed, partition_half=1,
                    )
                except Exception as exc:
                    _err(f"Could not save decoy key file: {exc}")
                    return

            # Clear passphrases from memory
            self.passphrase.set("")
            self.pw_confirm.set("")

            app.show_success("embed")

        import threading as _threading
        _threading.Thread(target=_do_embed, daemon=True).start()