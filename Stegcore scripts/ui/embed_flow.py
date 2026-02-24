# Copyright (C) 2025 Mercury
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: ui/embed_flow.py
# Description: Embed workflow — file selection, cover scoring, cipher/mode
#              choice, and orchestration.

import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import customtkinter as customtk

from core import crypto, steg, utils


# ---------------------------------------------------------------------------
# Cover score dialog
# ---------------------------------------------------------------------------

class _CoverScoreDialog(customtk.CTkToplevel):
    """
    Displays cover image analysis results and asks the user to confirm
    or cancel before proceeding to the options dialog.
    """

    # Colour per label
    _LABEL_COLOUR = {
        "Excellent": "#2ecc71",
        "Good":      "#3498db",
        "Fair":      "#e67e22",
        "Poor":      "#e74c3c",
    }

    def __init__(self, parent, image_path: Path):
        super().__init__(parent)
        self.title("Cover image analysis")
        self.resizable(False, False)
        self.withdraw()
        self.update_idletasks()
        self.deiconify()
        self.grab_set()

        self.confirmed = False

        try:
            metrics = steg.score_cover_image(image_path)
        except Exception as exc:
            utils.show_error(f"Could not analyse image:\n{exc}")
            self.destroy()
            return

        label_colour = self._LABEL_COLOUR.get(metrics["label"], "white")

        # Header
        customtk.CTkLabel(
            self,
            text=f"Cover Score:  {metrics['score']}/100  —  {metrics['label']}",
            font=("Consolas", 14, "bold"),
            text_color=label_colour,
        ).pack(padx=24, pady=(20, 4))

        customtk.CTkLabel(
            self,
            text=f"{metrics['width']} × {metrics['height']} px  "
                 f"|  Entropy: {metrics['entropy']:.2f} / 8.00  "
                 f"|  Texture: {metrics['texture_density']*100:.1f}%",
            font=("Consolas", 11),
            text_color="gray",
        ).pack(padx=24, pady=(0, 12))

        # Capacity table
        frame = customtk.CTkFrame(self)
        frame.pack(padx=24, fill="x")

        headers = ["Mode", "Max capacity"]
        rows = [
            ["Adaptive (spread spectrum)",
             self._fmt_bytes(metrics["adaptive_capacity"])],
            ["Sequential (standard LSB)",
             self._fmt_bytes(metrics["sequential_capacity"])],
        ]

        for col, header in enumerate(headers):
            customtk.CTkLabel(
                frame, text=header,
                font=("Consolas", 11, "bold"),
            ).grid(row=0, column=col, padx=12, pady=(8, 4), sticky="w")

        for r, row in enumerate(rows, start=1):
            for col, val in enumerate(row):
                customtk.CTkLabel(
                    frame, text=val,
                    font=("Consolas", 11),
                ).grid(row=r, column=col, padx=12, pady=3, sticky="w")

        # Warning if poor
        if metrics["score"] < 35:
            customtk.CTkLabel(
                self,
                text="⚠  Low cover score. Embedding may be more detectable.\n"
                     "   Consider using a more textured photograph.",
                font=("Consolas", 10),
                text_color="#e67e22",
                justify="left",
            ).pack(padx=24, pady=(12, 0))

        # Low adaptive capacity warning
        if metrics["adaptive_capacity"] < 1024:
            customtk.CTkLabel(
                self,
                text="⚠  Adaptive capacity is very low for this image.\n"
                     "   Sequential mode is recommended.",
                font=("Consolas", 10),
                text_color="#e67e22",
                justify="left",
            ).pack(padx=24, pady=(6, 0))

        # Buttons
        btn_frame = customtk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=24, pady=(16, 20), fill="x")

        customtk.CTkButton(
            btn_frame,
            text="Continue",
            command=self._confirm,
            font=("Consolas", 13),
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))

        customtk.CTkButton(
            btn_frame,
            text="Cancel",
            command=self.destroy,
            font=("Consolas", 13),
            fg_color="gray30",
            hover_color="gray40",
        ).pack(side="left", expand=True, fill="x", padx=(6, 0))

        if parent is not None:
            self.update_idletasks()
            px = parent.winfo_rootx() + (parent.winfo_width()  - self.winfo_width())  // 2
            py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
            self.geometry(f"+{px}+{py}")

        self.update()  # force render before blocking
        self.wait_window()

    def _confirm(self):
        self.confirmed = True
        self.destroy()

    @staticmethod
    def _fmt_bytes(n: int) -> str:
        if n >= 1_048_576:
            return f"{n / 1_048_576:.2f} MB"
        if n >= 1024:
            return f"{n / 1024:.1f} KB"
        return f"{n} B"


# ---------------------------------------------------------------------------
# Options dialog  (cipher + steg mode)
# ---------------------------------------------------------------------------

class _EmbedOptionsDialog(customtk.CTkToplevel):
    """Modal dialog for choosing cipher and steganography mode."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Embed options")
        self.resizable(False, False)
        # After
        self.withdraw()
        self.update_idletasks()
        self.deiconify()
        self.grab_set()

        self.cipher    = None
        self.steg_mode = None

        customtk.CTkLabel(
            self,
            text="Encryption cipher",
            font=("Consolas", 13, "bold"),
        ).pack(anchor="w", padx=24, pady=(20, 6))

        self._cipher_var = tk.StringVar(value=crypto.SUPPORTED_CIPHERS[0])
        for cipher in crypto.SUPPORTED_CIPHERS:
            customtk.CTkRadioButton(
                self,
                text=cipher,
                variable=self._cipher_var,
                value=cipher,
                font=("Consolas", 12),
            ).pack(anchor="w", padx=36, pady=3)

        customtk.CTkFrame(self, height=1, fg_color="gray30").pack(
            fill="x", padx=24, pady=(14, 0))

        customtk.CTkLabel(
            self,
            text="Steganography mode",
            font=("Consolas", 13, "bold"),
        ).pack(anchor="w", padx=24, pady=(14, 2))

        self._mode_var = tk.StringVar(value="adaptive")

        customtk.CTkRadioButton(
            self,
            text="Adaptive  (spread spectrum — steganalysis resistant)",
            variable=self._mode_var,
            value="adaptive",
            font=("Consolas", 12),
        ).pack(anchor="w", padx=36, pady=3)

        customtk.CTkRadioButton(
            self,
            text="Sequential  (standard LSB — maximum capacity)",
            variable=self._mode_var,
            value="sequential",
            font=("Consolas", 12),
        ).pack(anchor="w", padx=36, pady=3)

        customtk.CTkLabel(
            self,
            text="Adaptive mode requires a textured cover image.\n"
                 "Sequential mode works on any image but is detectable.",
            font=("Consolas", 10),
            text_color="gray",
            justify="left",
        ).pack(anchor="w", padx=36, pady=(2, 10))

        customtk.CTkButton(
            self,
            text="Confirm",
            command=self._confirm,
            font=("Consolas", 13),
        ).pack(pady=(6, 20), padx=24, fill="x")

        if parent is not None:
            self.update_idletasks()
            px = parent.winfo_rootx() + (parent.winfo_width()  - self.winfo_width())  // 2
            py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
            self.geometry(f"+{px}+{py}")

        self.update()  # force render before blocking
        self.wait_window()

    def _confirm(self):
        self.cipher    = self._cipher_var.get()
        self.steg_mode = self._mode_var.get()
        self.destroy()


# ---------------------------------------------------------------------------
# Embed flow
# ---------------------------------------------------------------------------

def run(parent=None) -> None:
    """
    Drive the full embed flow:
      1. Select text file
      2. Select cover image
      3. Show cover score — user confirms or cancels
      4. Choose cipher and steg mode
      5. Enter passphrase
      6. Encrypt → embed → save stego image → save key file
    """

    # Step 1 — select text file
    text_file = filedialog.askopenfilename(
        title="Select a text file",
        filetypes=[("Text files", "*.txt")],
    )
    if not text_file:
        utils.show_error("No text file selected.")
        return

    text_path = Path(text_file)
    if text_path.suffix.lower() != ".txt":
        utils.show_error("Invalid file format. Please select a .txt file.")
        return

    info_type = text_path.suffix

    # Step 2 — select cover image
    image_file = filedialog.askopenfilename(
        title="Select a cover file",
        filetypes=[
            ("All supported", "*.png *.jpg *.jpeg *.bmp *.wav"),
            ("PNG image",     "*.png"),
            ("JPEG image",    "*.jpg *.jpeg"),
            ("WAV audio",     "*.wav"),
        ],
    )
    if not image_file:
        utils.show_error("No cover file selected.")
        return

    image_path = Path(image_file)
    if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".bmp", ".wav"}:
        utils.show_error("Unsupported format. Please select a .png, .jpg, .bmp, or .wav file.")
        return

    # Step 3 — cover score
    score_dialog = _CoverScoreDialog(parent, image_path)
    if not score_dialog.confirmed:
        return

    # Step 4 — options
    options = _EmbedOptionsDialog(parent)
    if options.cipher is None:
        return

    cipher    = options.cipher
    steg_mode = options.steg_mode

    # Step 5 — passphrase
    dialog = customtk.CTkInputDialog(text="Enter a passphrase:", title="Passphrase")
    passphrase = dialog.get_input()
    if not passphrase:
        utils.show_error("A passphrase is required.")
        return

    # Step 6 — encrypt, embed, save
    try:
        plaintext = text_path.read_text(errors="ignore").encode("utf-8")
    except OSError as exc:
        utils.show_error(f"Could not read text file:\n{exc}")
        return

    try:
        result = crypto.encrypt(plaintext, passphrase, cipher)
    except (ValueError, RuntimeError) as exc:
        utils.show_error(str(exc))
        return

    with utils.temp_file(".bin") as tmp:
        tmp.write_bytes(result["ciphertext"])

        fmt            = image_path.suffix.lower()
        out_ext        = ".wav" if fmt == ".wav" else ".png"
        out_filetypes  = (
            [("WAV audio", "*.wav")] if fmt == ".wav"
            else [("PNG image", "*.png")]
        )
        output_image = filedialog.asksaveasfilename(
            title="Save stego file as",
            defaultextension=out_ext,
            filetypes=out_filetypes,
        )
        if not output_image:
            utils.show_error("Operation cancelled — no output image path chosen.")
            return

        # Adaptive/sequential mode only applies to PNG — JPEG uses DCT, WAV uses sample LSB
        effective_mode = steg_mode if fmt in {".png", ".bmp"} else "sequential"
        steg_key = result["key"] if effective_mode == "adaptive" else None

        try:
            steg.embed(image_path, tmp, output_image, key=steg_key, mode=effective_mode)
        except (ValueError, RuntimeError) as exc:
            utils.show_error(str(exc))
            return

    key_file = filedialog.asksaveasfilename(
        title="Save key file as",
        defaultextension=".json",
        filetypes=[("Key file", "*.json")],
    )
    if not key_file:
        utils.show_error("Operation cancelled — no key file path chosen.")
        return

    try:
        crypto.write_key_file(
            key_file,
            nonce=result["nonce"],
            salt=result["salt"],
            cipher=cipher,
            info_type=info_type,
            steg_mode=effective_mode,
        )
    except Exception as exc:
        utils.show_error(f"Could not save key file:\n{exc}")
        return

    utils.show_info(
        f"Embedding complete.\n"
        f"Cipher: {cipher}  |  Mode: {steg_mode}\n\n"
        "Keep the key file safe — it is required for extraction."
    )