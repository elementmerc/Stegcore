# Copyright (C) 2025 Mercury
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: ui/embed_flow.py
# Description: Embed workflow — file selection, cover scoring, cipher/mode
#              choice, deniability, and orchestration.

import os
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
    Displays cover image analysis and asks the user to confirm or cancel
    before proceeding.
    """

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
        self.confirmed = False

        try:
            metrics = steg.score_cover_image(image_path)
        except Exception as exc:
            utils.show_error(f"Could not analyse image:\n{exc}")
            self.destroy()
            return

        label_colour = self._LABEL_COLOUR.get(metrics["label"], "white")

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

        frame = customtk.CTkFrame(self)
        frame.pack(padx=24, fill="x")

        for col, header in enumerate(["Mode", "Max capacity"]):
            customtk.CTkLabel(
                frame, text=header,
                font=("Consolas", 11, "bold"),
            ).grid(row=0, column=col, padx=12, pady=(8, 4), sticky="w")

        for r, (mode, cap) in enumerate([
            ("Adaptive (spread spectrum)", self._fmt_bytes(metrics["adaptive_capacity"])),
            ("Sequential (standard LSB)",  self._fmt_bytes(metrics["sequential_capacity"])),
        ], start=1):
            customtk.CTkLabel(frame, text=mode, font=("Consolas", 11)).grid(
                row=r, column=0, padx=12, pady=3, sticky="w")
            customtk.CTkLabel(frame, text=cap, font=("Consolas", 11)).grid(
                row=r, column=1, padx=12, pady=3, sticky="w")

        if metrics["score"] < 35:
            customtk.CTkLabel(
                self,
                text="⚠  Low cover score. Embedding may be more detectable.\n"
                     "   Consider using a more textured photograph.",
                font=("Consolas", 10),
                text_color="#e67e22",
                justify="left",
            ).pack(padx=24, pady=(12, 0))

        if metrics["adaptive_capacity"] < 1024:
            customtk.CTkLabel(
                self,
                text="⚠  Adaptive capacity is very low for this image.\n"
                     "   Sequential mode is recommended.",
                font=("Consolas", 10),
                text_color="#e67e22",
                justify="left",
            ).pack(padx=24, pady=(6, 0))

        btn_frame = customtk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=24, pady=(16, 20), fill="x")

        customtk.CTkButton(
            btn_frame, text="Continue", command=self._confirm,
            font=("Consolas", 13),
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))

        customtk.CTkButton(
            btn_frame, text="Cancel", command=self.destroy,
            font=("Consolas", 13), fg_color="gray30", hover_color="gray40",
        ).pack(side="left", expand=True, fill="x", padx=(6, 0))

        if parent is not None:
            self.withdraw()
            self.update_idletasks()
            self.deiconify()
            self.grab_set()
            px = parent.winfo_rootx() + (parent.winfo_width()  - self.winfo_width())  // 2
            py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
            self.geometry(f"+{px}+{py}")

        self.update()
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
# Options dialog  (cipher + steg mode + deniability)
# ---------------------------------------------------------------------------

class _EmbedOptionsDialog(customtk.CTkToplevel):
    """Modal dialog for choosing cipher, steganography mode, and deniability."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Embed options")
        self.resizable(False, False)

        self.cipher    = None
        self.steg_mode = None
        self.deniable  = False

        # Cipher
        customtk.CTkLabel(
            self, text="Encryption cipher",
            font=("Consolas", 13, "bold"),
        ).pack(anchor="w", padx=24, pady=(20, 6))

        self._cipher_var = tk.StringVar(value=crypto.SUPPORTED_CIPHERS[0])
        for cipher in crypto.SUPPORTED_CIPHERS:
            customtk.CTkRadioButton(
                self, text=cipher,
                variable=self._cipher_var, value=cipher,
                font=("Consolas", 12),
            ).pack(anchor="w", padx=36, pady=3)

        customtk.CTkFrame(self, height=1, fg_color="gray30").pack(
            fill="x", padx=24, pady=(14, 0))

        # Steg mode
        customtk.CTkLabel(
            self, text="Steganography mode",
            font=("Consolas", 13, "bold"),
        ).pack(anchor="w", padx=24, pady=(14, 2))

        self._mode_var = tk.StringVar(value="adaptive")

        customtk.CTkRadioButton(
            self,
            text="Adaptive  (spread spectrum — steganalysis resistant)",
            variable=self._mode_var, value="adaptive",
            font=("Consolas", 12),
        ).pack(anchor="w", padx=36, pady=3)

        customtk.CTkRadioButton(
            self,
            text="Sequential  (standard LSB — maximum capacity)",
            variable=self._mode_var, value="sequential",
            font=("Consolas", 12),
        ).pack(anchor="w", padx=36, pady=3)

        customtk.CTkLabel(
            self,
            text="Adaptive mode requires a textured cover image.\n"
                 "Sequential mode works on any image but is detectable.",
            font=("Consolas", 10), text_color="gray", justify="left",
        ).pack(anchor="w", padx=36, pady=(2, 10))

        customtk.CTkFrame(self, height=1, fg_color="gray30").pack(
            fill="x", padx=24, pady=(6, 0))

        # Deniability
        customtk.CTkLabel(
            self, text="Deniability",
            font=("Consolas", 13, "bold"),
        ).pack(anchor="w", padx=24, pady=(14, 2))

        self._deniable_var = tk.BooleanVar(value=False)
        customtk.CTkCheckBox(
            self,
            text="Enable deniable dual payload",
            variable=self._deniable_var,
            font=("Consolas", 12),
        ).pack(anchor="w", padx=36, pady=3)

        customtk.CTkLabel(
            self,
            text="Embeds a decoy message unlocked by a second passphrase.\n"
                 "Only available with adaptive PNG mode.",
            font=("Consolas", 10), text_color="gray", justify="left",
        ).pack(anchor="w", padx=36, pady=(2, 10))

        customtk.CTkButton(
            self, text="Confirm", command=self._confirm,
            font=("Consolas", 13),
        ).pack(pady=(6, 20), padx=24, fill="x")

        if parent is not None:
            self.withdraw()
            self.update_idletasks()
            self.deiconify()
            self.grab_set()
            px = parent.winfo_rootx() + (parent.winfo_width()  - self.winfo_width())  // 2
            py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
            self.geometry(f"+{px}+{py}")

        self.update()
        self.wait_window()

    def _confirm(self):
        self.cipher    = self._cipher_var.get()
        self.steg_mode = self._mode_var.get()
        self.deniable  = self._deniable_var.get()
        self.destroy()


# ---------------------------------------------------------------------------
# Embed flow
# ---------------------------------------------------------------------------

def run(parent=None) -> None:
    """
    Drive the full embed flow:
      1.  Select text file
      2.  Select cover file
      3.  Show cover score — confirm or cancel
      4.  Choose cipher, steg mode, and deniability
      5.  Enter real passphrase
      6.  Encrypt real payload
      7.  If deniable: collect decoy file + passphrase, encrypt decoy
      8.  Choose output path and embed
      9.  Save real key file
      10. If deniable: save decoy key file
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

    # Step 2 — select cover file
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

    # Step 3 — cover score (images only, skip for WAV)
    if image_path.suffix.lower() != ".wav":
        score_dialog = _CoverScoreDialog(parent, image_path)
        if not score_dialog.confirmed:
            return

    # Step 4 — options
    options = _EmbedOptionsDialog(parent)
    if options.cipher is None:
        return

    cipher    = options.cipher
    steg_mode = options.steg_mode

    fmt            = image_path.suffix.lower()
    # Adaptive/sequential only applies to PNG — JPEG uses DCT, WAV uses sample LSB
    effective_mode = steg_mode if fmt in {".png", ".bmp"} else "sequential"
    # Deniability only works with adaptive PNG
    deniable       = options.deniable and effective_mode == "adaptive"

    # Step 5 — real passphrase
    dialog = customtk.CTkInputDialog(text="Enter a passphrase:", title="Passphrase")
    passphrase = dialog.get_input()
    if not passphrase:
        utils.show_error("A passphrase is required.")
        return

    # Step 6 — encrypt real payload
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

    steg_key = result["key"] if effective_mode == "adaptive" else None

    # Step 7 — if deniable, collect and encrypt decoy
    decoy_result   = None
    decoy_key      = None
    partition_seed = None

    if deniable:
        decoy_file = filedialog.askopenfilename(
            title="Select decoy text file",
            filetypes=[("Text files", "*.txt")],
        )
        if not decoy_file:
            utils.show_error("No decoy file selected. Deniability requires a decoy message.")
            return

        decoy_dialog = customtk.CTkInputDialog(
            text="Enter the DECOY passphrase\n(must differ from the real passphrase):",
            title="Decoy Passphrase",
        )
        decoy_passphrase = decoy_dialog.get_input()
        if not decoy_passphrase:
            utils.show_error("A decoy passphrase is required.")
            return
        if decoy_passphrase == passphrase:
            utils.show_error("Decoy passphrase must differ from the real passphrase.")
            return

        try:
            decoy_text   = Path(decoy_file).read_text(errors="ignore").encode("utf-8")
            decoy_result = crypto.encrypt(decoy_text, decoy_passphrase, cipher)
            decoy_key    = decoy_result["key"]
            partition_seed = os.urandom(16)
        except (ValueError, RuntimeError, OSError) as exc:
            utils.show_error(f"Could not encrypt decoy payload:\n{exc}")
            return

    # Step 8 — choose output path and embed
    out_ext       = ".wav" if fmt == ".wav" else ".png"
    out_filetypes = (
        [("WAV audio", "*.wav")] if fmt == ".wav"
        else [("PNG image", "*.png")]
    )
    output_image = filedialog.asksaveasfilename(
        title="Save stego file as",
        defaultextension=out_ext,
        filetypes=out_filetypes,
    )
    if not output_image:
        utils.show_error("Operation cancelled — no output file path chosen.")
        return

    if deniable:
        # Pass ciphertext bytes directly — no temp files needed
        try:
            steg.embed_deniable(
                cover_path=image_path,
                real_payload=result["ciphertext"],
                decoy_payload=decoy_result["ciphertext"],
                output_path=output_image,
                real_key=steg_key,
                decoy_key=decoy_key,
                partition_seed=partition_seed,
            )
        except (ValueError, RuntimeError) as exc:
            utils.show_error(str(exc))
            return
    else:
        with utils.temp_file(".bin") as tmp:
            tmp.write_bytes(result["ciphertext"])
            try:
                steg.embed(image_path, tmp, output_image, key=steg_key, mode=effective_mode)
            except (ValueError, RuntimeError) as exc:
                utils.show_error(str(exc))
                return

    # Step 9 — save real key file
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
            deniable=deniable,
            partition_seed=partition_seed if deniable else None,
            partition_half=0 if deniable else None,
        )
    except Exception as exc:
        utils.show_error(f"Could not save key file:\n{exc}")
        return

    # Step 10 — if deniable, save decoy key file
    if deniable:
        utils.show_info(
            "Real key file saved.\n\n"
            "Now save the DECOY key file.\n"
            "Keep both — each unlocks a different message."
        )
        decoy_key_file = filedialog.asksaveasfilename(
            title="Save DECOY key file as",
            defaultextension=".json",
            filetypes=[("Key file", "*.json")],
        )
        if not decoy_key_file:
            utils.show_error("Operation cancelled — decoy key file not saved.")
            return
        try:
            crypto.write_key_file(
                decoy_key_file,
                nonce=decoy_result["nonce"],
                salt=decoy_result["salt"],
                cipher=cipher,
                info_type=info_type,
                steg_mode=effective_mode,
                deniable=deniable,
                partition_seed=partition_seed,
                partition_half=1,
            )
        except Exception as exc:
            utils.show_error(f"Could not save decoy key file:\n{exc}")
            return

    utils.show_info(
        f"Embedding complete.\n"
        f"Cipher: {cipher}  |  Mode: {effective_mode}"
        + ("  |  Deniable: yes" if deniable else "") +
        "\n\nKeep the key file(s) safe — they are required for extraction."
    )