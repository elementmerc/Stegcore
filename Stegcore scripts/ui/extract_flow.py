# Copyright (C) 2025 Mercury
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: ui/extract_flow.py
# Description: Extract workflow — file selection dialogs and orchestration.
#              Cipher is detected automatically from the key file.

from pathlib import Path
from tkinter import filedialog

import customtkinter as customtk

from core import crypto, steg, utils


def run() -> None:
    """
    Drive the full extract flow:
      1. Select stego image
      2. Select key file
      3. Enter passphrase
      4. Extract ciphertext → decrypt → save recovered text
    """

    # Step 1 — select stego image
    image_file = filedialog.askopenfilename(
        title="Select the stego file",
        filetypes=[
            ("All supported", "*.png *.jpg *.jpeg *.wav"),
            ("PNG image",     "*.png"),
            ("JPEG image",    "*.jpg *.jpeg"),
            ("WAV audio",     "*.wav"),
        ],
    )
    if not image_file:
        utils.show_error("No stego file selected.")
        return

    image_path = Path(image_file)
    if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".wav"}:
        utils.show_error("Unsupported format. Please select a .png, .jpg, or .wav file.")
        return

    # Step 2 — select key file
    key_file = filedialog.askopenfilename(
        title="Select the key file",
        filetypes=[("Key file", "*.json"), ("Legacy key file", "*.bin")],
    )
    if not key_file:
        utils.show_error("No key file selected.")
        return

    try:
        key_data = crypto.read_key_file(key_file)
    except ValueError as exc:
        utils.show_error(str(exc))
        return

    # Step 3 — passphrase
    dialog = customtk.CTkInputDialog(text="Enter the passphrase:", title="Passphrase")
    passphrase = dialog.get_input()
    if not passphrase:
        utils.show_error("A passphrase is required.")
        return

    steg_mode = key_data.get("steg_mode", "sequential")

    # Derive key for spread-spectrum index reconstruction (adaptive mode only)
    steg_key = (
        crypto.derive_key(passphrase, key_data["salt"], key_data["cipher"])
        if steg_mode == "adaptive"
        else None
    )

    # Step 4 — extract and decrypt
    deniable = key_data.get("deniable", False)

    try:
        if deniable:
            partition_seed = key_data["partition_seed"]
            partition_half = key_data["partition_half"]
            raw_payload = steg.extract_deniable(
                image_path,
                key=steg_key,
                partition_seed=partition_seed,
                partition_half=partition_half,
            )
            payload  = {**key_data, "ciphertext": raw_payload}
            plaintext = crypto.decrypt(payload, passphrase)
            recovered = plaintext.decode("utf-8")
        else:
            with utils.temp_file(".bin") as tmp:
                steg.extract(image_path, tmp, key=steg_key, mode=steg_mode)
                ciphertext = tmp.read_bytes()
                payload    = {**key_data, "ciphertext": ciphertext}
                plaintext  = crypto.decrypt(payload, passphrase)
                recovered  = plaintext.decode("utf-8")
    except ValueError as exc:
        utils.show_error(str(exc))
        return
    except Exception as exc:
        utils.show_error(f"Unexpected error during extraction:\n{exc}")
        return

    # Save recovered text
    info_type   = key_data.get("info_type", ".txt")
    output_file = filedialog.asksaveasfilename(
        title="Save recovered text as",
        defaultextension=info_type,
        filetypes=[("Text file", "*.txt")],
    )
    if not output_file:
        utils.show_error("Operation cancelled — no output path chosen.")
        return

    try:
        Path(output_file).write_text(recovered, encoding="utf-8")
    except OSError as exc:
        utils.show_error(f"Could not save output file:\n{exc}")
        return

    utils.show_info("Extraction complete.")