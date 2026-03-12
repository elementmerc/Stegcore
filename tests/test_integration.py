# Copyright (C) 2026 Daniel Iwugo
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: tests/test_integration.py
# Full pipeline integration tests: encrypt → embed → extract → decrypt.
# Parametrized over all cipher × embedding-mode combinations and multiple payload sizes.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from core import crypto, steg


_CIPHERS  = crypto.SUPPORTED_CIPHERS
_MODES    = steg.SUPPORTED_MODES
_SIZES    = [1, 1024, 102400]          # 1 B, 1 KB, 100 KB
_PASS     = "integration-test-pass-2026"


def _pipeline(cipher, mode, plaintext, cover_path, tmp_path, label=""):
    """Shared helper: encrypt → write payload → embed → extract → decrypt → return recovered."""
    enc = crypto.encrypt(plaintext, _PASS, cipher)

    payload_file = tmp_path / f"payload{label}.bin"
    payload_file.write_bytes(enc["ciphertext"])

    cap = steg.get_capacity(cover_path, mode=mode)["available_bytes"]
    if len(enc["ciphertext"]) > cap:
        pytest.skip(
            f"Ciphertext ({len(enc['ciphertext'])} B) exceeds {mode} capacity ({cap} B)"
        )

    stego = steg.embed(
        cover_path, payload_file,
        tmp_path / f"stego{label}.png",
        key=enc["key"], mode=mode,
    )

    out = tmp_path / f"extracted{label}.bin"
    steg.extract(stego, out, key=enc["key"], mode=mode)

    return crypto.decrypt(
        {
            "ciphertext": out.read_bytes(),
            "nonce":      enc["nonce"],
            "salt":       enc["salt"],
            "cipher":     enc["cipher"],
        },
        _PASS,
    )


# ---------------------------------------------------------------------------
# Full pipeline: cipher × mode × payload size
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "cipher,mode,plaintext_size",
    [(c, m, s) for c in _CIPHERS for m in _MODES for s in _SIZES],
    ids=lambda x: str(x),
)
def test_full_pipeline(cipher, mode, plaintext_size, cover_png, tmp_path):
    """End-to-end embed→extract round-trip for every cipher × mode × payload-size combination.

    Uses highly-compressible plaintext (b'x' * N) so post-encryption ciphertext
    remains small and fits within an 800×600 cover at any mode.
    """
    plaintext = b"x" * plaintext_size
    recovered = _pipeline(cipher, mode, plaintext, cover_png, tmp_path)
    assert recovered == plaintext


# ---------------------------------------------------------------------------
# Near-capacity: cipher × mode (payload = 90% of available bytes)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "cipher,mode",
    [(c, m) for c in _CIPHERS for m in _MODES],
    ids=lambda x: str(x),
)
def test_near_capacity(cipher, mode, cover_png, tmp_path):
    """Embed a payload sized at 90% of the cover's capacity and confirm exact recovery.

    Skipped gracefully when the synthetic image is too small to hold the payload.
    """
    cap          = steg.get_capacity(cover_png, mode=mode)["available_bytes"]
    payload_size = int(cap * 0.90)
    if payload_size < 1:
        pytest.skip("Cover image too small for near-capacity test")

    # Compressible plaintext: post-encryption size << plaintext size
    plaintext = b"z" * payload_size
    enc       = crypto.encrypt(plaintext, _PASS, cipher)

    if len(enc["ciphertext"]) > cap:
        pytest.skip(
            f"Encrypted ciphertext ({len(enc['ciphertext'])} B) exceeds "
            f"{mode} capacity ({cap} B) even after compression"
        )

    payload_file = tmp_path / "nc_payload.bin"
    payload_file.write_bytes(enc["ciphertext"])

    stego = steg.embed(
        cover_png, payload_file,
        tmp_path / "nc_stego.png",
        key=enc["key"], mode=mode,
    )

    out = tmp_path / "nc_extracted.bin"
    steg.extract(stego, out, key=enc["key"], mode=mode)

    recovered = crypto.decrypt(
        {
            "ciphertext": out.read_bytes(),
            "nonce":      enc["nonce"],
            "salt":       enc["salt"],
            "cipher":     enc["cipher"],
        },
        _PASS,
    )
    assert recovered == plaintext
