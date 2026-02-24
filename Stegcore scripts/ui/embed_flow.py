# Copyright (C) 2025 Mercury
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: ui/embed_flow.py
# Description: Embed workflow — file selection, cipher choice, and orchestration.

import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import customtkinter as customtk

from core import crypto, steg, utils


# ---------------------------------------------------------------------------
# Cipher selection dialog
# ---------------------------------------------------------------------------

class _CipherDialog(customtk.CTkToplevel):
    """
    A small modal dialog for choosing a cipher before embedding.
    Blocks until the user confirms or cancels.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Choose cipher")
        self.resizable(False, False)
        self.grab_set()  # modal

        self.result = None  # set on confirm

        customtk.CTkLabel(
            self,
            text="Select encryption cipher:",
            font=("Consolas", 13),
        ).pack(padx=24, pady=(20, 10))

        self._var = tk.StringVar(value=crypto.SUPPORTED_CIPHERS[0])

        for cipher in crypto.SUPPORTED_CIPHERS:
            customtk.CTkRadioButton(
                self,
                text=cipher,
                variable=self._var,
                value=cipher,
                font=("Consolas", 12),
            ).pack(anchor="w", padx=32, pady=4)

        customtk.CTkButton(
            self,
            text="Confirm",
            command=self._confirm,
            font=("Consolas", 13),
        ).pack(pady=(16, 20), padx=24, fill="x")

       # Centre over parent if one was provided
        if parent is not None:
            self.update_idletasks()
            px = parent.winfo_rootx() + (parent.winfo_width()  - self.winfo_width())  // 2
            py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
            self.geometry(f"+{px}+{py}")

        self.wait_window()

    def _confirm(self):
        self.result = self._var.get()
        self.destroy()


def _pick_cipher(parent) -> str | None:
    """Show the cipher dialog and return the chosen cipher, or None if cancelled."""
    dialog = _CipherDialog(parent)
    return dialog.result


# ---------------------------------------------------------------------------
# Embed flow
# ---------------------------------------------------------------------------

def run(parent=None) -> None:
    """
    Drive the full embed flow:
      1. Select text file
      2. Select cover image
      3. Choose cipher
      4. Enter passphrase
      5. Encrypt → embed → save stego image → save key file
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
        title="Select a cover image",
        filetypes=[("Image files", "*.png *.jpg *.jpeg")],
    )
    if not image_file:
        utils.show_error("No image selected.")
        return

    image_path = Path(image_file)
    if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        utils.show_error("Invalid image format. Please select a .png or .jpg file.")
        return

    # Step 3 — choose cipher
    cipher = _pick_cipher(parent)
    if not cipher:
        # User closed the dialog without confirming — default gracefully
        cipher = "Ascon-128"

    # Step 4 — passphrase
    dialog = customtk.CTkInputDialog(text="Enter a passphrase:", title="Passphrase")
    passphrase = dialog.get_input()
    if not passphrase:
        utils.show_error("A passphrase is required.")
        return

    # Step 5 — encrypt, embed, save
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

        output_image = filedialog.asksaveasfilename(
            title="Save stego image as",
            defaultextension=".png",
            filetypes=[("PNG image", "*.png")],
        )
        if not output_image:
            utils.show_error("Operation cancelled — no output image path chosen.")
            return

        try:
            steg.embed(image_path, tmp, output_image)
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
            cipher=result["cipher"],
            info_type=info_type,
        )
    except Exception as exc:
        utils.show_error(f"Could not save key file:\n{exc}")
        return

    utils.show_info(
        f"Embedding complete.\nCipher used: {cipher}\n\n"
        "Keep the key file safe — it is required for extraction."
    )