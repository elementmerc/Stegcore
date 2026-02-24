# Copyright (C) 2026 Daniel Iwugo
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: ui/extract_flow.py

from pathlib import Path
from tkinter import filedialog

import customtkinter as customtk

from core import crypto, steg, utils
from ui.theme import get_theme


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
        text_color=t["ACCENT2"], font=("Consolas", 12),
        command=pick_fn,
    ).pack(side="right", padx=8, pady=8)


class ExtractFlow:
    action_label = "Extract"

    def __init__(self, app):
        self.app = app

        self.stego_path = None
        self.key_path   = None
        self.passphrase = customtk.StringVar(value="")
        self._show_pw   = customtk.BooleanVar(value=False)

        self._stego_disp = customtk.StringVar(value="No file selected")
        self._key_disp   = customtk.StringVar(value="No file selected")

        self.steps = [
            ("Image",      self._build_step1),
            ("Key File",   self._build_step2),
            ("Passphrase", self._build_step3),
        ]

    # ------------------------------------------------------------------
    # Step 1 — stego file
    # ------------------------------------------------------------------

    def _build_step1(self) -> customtk.CTkFrame:
        t = get_theme()
        frame = customtk.CTkFrame(self.app._content_area,
                                  fg_color=t["BG"], corner_radius=0)
        customtk.CTkLabel(
            frame, text="Select stego file",
            font=("Consolas", 17, "bold"), text_color=t["TEXT"],
        ).pack(padx=24, pady=(24, 4), anchor="w")
        customtk.CTkLabel(
            frame, text="The file containing the hidden message.",
            font=("Consolas", 12), text_color=t["MUTED"],
        ).pack(padx=24, pady=(0, 16), anchor="w")

        customtk.CTkLabel(
            frame, text="STEGO FILE",
            font=("Consolas", 12, "bold"), text_color=t["TEXT2"], anchor="w",
        ).pack(fill="x", padx=24, pady=(0, 4))
        _file_row(frame, "File", self._stego_disp, self._pick_stego)

        return frame

    def _pick_stego(self) -> None:
        p = filedialog.askopenfilename(
            title="Select stego file",
            filetypes=[
                ("All supported", "*.png *.jpg *.jpeg *.wav"),
                ("PNG image",     "*.png"),
                ("JPEG image",    "*.jpg *.jpeg"),
                ("WAV audio",     "*.wav"),
            ],
        )
        if p:
            self.stego_path = Path(p)
            self._stego_disp.set(self.stego_path.name)
            self.app._render_step()

    # ------------------------------------------------------------------
    # Step 2 — key file
    # ------------------------------------------------------------------

    def _build_step2(self) -> customtk.CTkFrame:
        t = get_theme()
        frame = customtk.CTkFrame(self.app._content_area,
                                  fg_color=t["BG"], corner_radius=0)
        customtk.CTkLabel(
            frame, text="Select key file",
            font=("Consolas", 17, "bold"), text_color=t["TEXT"],
        ).pack(padx=24, pady=(24, 4), anchor="w")
        customtk.CTkLabel(
            frame,
            text="The .json key file saved when the message was embedded.",
            font=("Consolas", 12), text_color=t["MUTED"],
            wraplength=400, justify="left",
        ).pack(padx=24, pady=(0, 16), anchor="w")

        customtk.CTkLabel(
            frame, text="KEY FILE",
            font=("Consolas", 12, "bold"), text_color=t["TEXT2"], anchor="w",
        ).pack(fill="x", padx=24, pady=(0, 4))
        _file_row(frame, "File", self._key_disp, self._pick_key)

        if self.key_path:
            try:
                kd = crypto.read_key_file(self.key_path)
                card = customtk.CTkFrame(
                    frame, fg_color=t["CARD2"], corner_radius=10,
                    border_width=1, border_color=t["BORDER"],
                )
                card.pack(fill="x", padx=24, pady=(8, 0))
                for k, v in [
                    ("Cipher",    kd["cipher"]),
                    ("Mode",      kd.get("steg_mode", "—")),
                    ("Deniable",  "Yes" if kd.get("deniable") else "No"),
                    ("File type", kd.get("info_type", "—")),
                ]:
                    row = customtk.CTkFrame(card, fg_color="transparent")
                    row.pack(fill="x", padx=14, pady=6)
                    customtk.CTkLabel(
                        row, text=k, font=("Consolas", 12),
                        text_color=t["MUTED"], width=80, anchor="w",
                    ).pack(side="left")
                    customtk.CTkLabel(
                        row, text=v, font=("Consolas", 12, "bold"),
                        text_color=t["TEXT2"], anchor="w",
                    ).pack(side="left")
            except ValueError:
                customtk.CTkLabel(
                    frame,
                    text="⚠  Could not read key file. May be malformed or v1 format.",
                    font=("Consolas", 11), text_color=t["WARN"],
                ).pack(padx=24, pady=(6, 0), anchor="w")

        return frame

    def _pick_key(self) -> None:
        p = filedialog.askopenfilename(
            title="Select key file",
            filetypes=[("Key file", "*.json"), ("All files", "*.*")],
        )
        if p:
            self.key_path = Path(p)
            self._key_disp.set(self.key_path.name)
            self.app._render_step()

    # ------------------------------------------------------------------
    # Step 3 — passphrase
    # ------------------------------------------------------------------

    def _build_step3(self) -> customtk.CTkFrame:
        t = get_theme()
        frame = customtk.CTkFrame(self.app._content_area,
                                  fg_color=t["BG"], corner_radius=0)
        customtk.CTkLabel(
            frame, text="Enter passphrase",
            font=("Consolas", 17, "bold"), text_color=t["TEXT"],
        ).pack(padx=24, pady=(24, 4), anchor="w")
        customtk.CTkLabel(
            frame, text="The passphrase used when the message was embedded.",
            font=("Consolas", 12), text_color=t["MUTED"],
            wraplength=400, justify="left",
        ).pack(padx=24, pady=(0, 16), anchor="w")

        customtk.CTkLabel(
            frame, text="PASSPHRASE",
            font=("Consolas", 12, "bold"), text_color=t["TEXT2"], anchor="w",
        ).pack(fill="x", padx=24, pady=(0, 4))

        pw_row = customtk.CTkFrame(
            frame, fg_color=t["CARD2"], corner_radius=8,
            border_width=1, border_color=t["BORDER"],
        )
        pw_row.pack(fill="x", padx=24)
        self._pw_entry = customtk.CTkEntry(
            pw_row, textvariable=self.passphrase,
            placeholder_text="Enter passphrase…",
            show="●", font=("Consolas", 13),
            fg_color="transparent", border_width=0,
            text_color=t["TEXT"], height=40,
        )
        self._pw_entry.pack(fill="x", padx=12, pady=4)

        customtk.CTkCheckBox(
            frame, text="Show passphrase",
            variable=self._show_pw,
            font=("Consolas", 11), text_color=t["MUTED"],
            fg_color=t["ACCENT2"], hover_color=t["ACCENT2"],
            command=self._toggle_pw,
        ).pack(padx=24, pady=(6, 0), anchor="w")

        # Summary
        summary = customtk.CTkFrame(
            frame, fg_color=t["CARD2"], corner_radius=10,
            border_width=1, border_color=t["BORDER"],
        )
        summary.pack(fill="x", padx=24, pady=(16, 0))
        for k, v in [
            ("Stego file", self.stego_path.name if self.stego_path else "—"),
            ("Key file",   self.key_path.name   if self.key_path   else "—"),
        ]:
            row = customtk.CTkFrame(summary, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=7)
            customtk.CTkLabel(
                row, text=k, font=("Consolas", 12),
                text_color=t["MUTED"], width=80, anchor="w",
            ).pack(side="left")
            customtk.CTkLabel(
                row, text=v, font=("Consolas", 12, "bold"),
                text_color=t["TEXT2"], anchor="w",
            ).pack(side="left")

        customtk.CTkLabel(
            frame,
            text="You will be prompted to choose a save location\n"
                 "for the recovered text file after clicking Extract.",
            font=("Consolas", 11), text_color=t["MUTED"], justify="left",
        ).pack(padx=24, pady=(12, 0), anchor="w")

        return frame

    def _toggle_pw(self) -> None:
        self._pw_entry.configure(show="" if self._show_pw.get() else "●")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_step(self, step: int) -> bool:
        if step == 0 and not self.stego_path:
            utils.show_error("Please select a stego file.")
            return False
        if step == 1 and not self.key_path:
            utils.show_error("Please select a key file.")
            return False
        if step == 2 and not self.passphrase.get().strip():
            utils.show_error("A passphrase is required.")
            return False
        return True

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    def execute(self, app) -> None:
        """
        File dialogs run on the main (Tk) thread.
        The heavy steg.extract call is threaded, then save dialog continues on main.
        """
        import threading

        def _restore_nav():
            app._continue_btn.configure(text="Extract", state="normal")
            app._back_flow_btn.configure(state="normal")

        def _err(msg):
            def _on_main():
                _restore_nav()
                utils.show_error(msg)
                app.show_home()
            app.after(0, _on_main)

        # ── Stage 1: read key file (fast, main thread) ───────────────
        try:
            key_data = crypto.read_key_file(self.key_path)
        except ValueError as exc:
            _restore_nav()
            utils.show_error(str(exc))
            app.show_home()
            return

        passphrase = self.passphrase.get().strip()
        steg_mode  = key_data.get("steg_mode", "sequential")
        deniable   = key_data.get("deniable", False)

        steg_key = (
            crypto.derive_key(passphrase, key_data["salt"], key_data["cipher"])
            if steg_mode == "adaptive" else None
        )

        # ── Stage 2: heavy steg extract in worker thread ─────────────
        app._show_working()

        def _do_extract():
            try:
                if deniable:
                    raw_payload = steg.extract_deniable(
                        self.stego_path,
                        key=steg_key,
                        partition_seed=key_data["partition_seed"],
                        partition_half=key_data["partition_half"],
                    )
                    payload   = {**key_data, "ciphertext": raw_payload}
                    plaintext = crypto.decrypt(payload, passphrase)
                else:
                    with utils.temp_file(".bin") as tmp:
                        steg.extract(self.stego_path, tmp,
                                     key=steg_key, mode=steg_mode)
                        ciphertext = tmp.read_bytes()
                        payload    = {**key_data, "ciphertext": ciphertext}
                        plaintext  = crypto.decrypt(payload, passphrase)

                recovered = plaintext.decode("utf-8")
                # Back to main thread for save dialog
                app.after(0, lambda: _save_output(recovered))

            except ValueError as exc:
                app.after(0, lambda msg=str(exc): _err(msg))
            except Exception as exc:
                app.after(0, lambda msg=str(exc):
                    _err(f"Unexpected error during extraction:\n{msg}"))

        def _save_output(recovered: str):
            """Runs on main thread after extraction completes."""
            out_file = filedialog.asksaveasfilename(
                title="Save recovered text as",
                defaultextension=key_data.get("info_type", ".txt"),
                filetypes=[("Text file", "*.txt")],
            )
            if not out_file:
                _restore_nav()
                utils.show_error("Operation cancelled. Output file not saved.")
                app.show_home()
                return

            try:
                from pathlib import Path as _Path
                _Path(out_file).write_text(recovered, encoding="utf-8")
            except OSError as exc:
                _restore_nav()
                utils.show_error(f"Could not write output file:\n{exc}")
                app.show_home()
                return

            # Clear passphrase from memory
            self.passphrase.set("")

            app.show_success("extract")

        threading.Thread(target=_do_extract, daemon=True).start()