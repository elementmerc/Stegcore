# Copyright (C) 2026 Daniel Iwugo
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: tests/test_crypto.py
# Unit tests for core/crypto.py — encrypt, decrypt, and key derivation.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from core import crypto


_PASSPHRASE = "hunter2-stegcore-tests"
_PLAINTEXT  = b"The quick brown fox jumps over the lazy dog."


# ---------------------------------------------------------------------------
# Round-trip: encrypt then decrypt returns original plaintext
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cipher", crypto.SUPPORTED_CIPHERS)
def test_encrypt_decrypt_roundtrip(cipher):
    """Encrypt then decrypt returns the original plaintext for every supported cipher."""
    result    = crypto.encrypt(_PLAINTEXT, _PASSPHRASE, cipher)
    recovered = crypto.decrypt(result, _PASSPHRASE)
    assert recovered == _PLAINTEXT


# ---------------------------------------------------------------------------
# Wrong passphrase must raise ValueError (AEAD auth tag fails)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cipher", crypto.SUPPORTED_CIPHERS)
def test_wrong_passphrase_raises(cipher):
    """Decryption with a wrong passphrase raises ValueError — never silently succeeds."""
    result = crypto.encrypt(_PLAINTEXT, _PASSPHRASE, cipher)
    with pytest.raises(ValueError):
        crypto.decrypt(result, "absolutely-wrong-passphrase")


# ---------------------------------------------------------------------------
# Empty plaintext (b"") must survive the compress → encrypt → decrypt → decompress cycle
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cipher", crypto.SUPPORTED_CIPHERS)
def test_empty_plaintext_roundtrip(cipher):
    """b'' plaintext encrypts and decrypts back to b'' without error."""
    result    = crypto.encrypt(b"", _PASSPHRASE, cipher)
    recovered = crypto.decrypt(result, _PASSPHRASE)
    assert recovered == b""


# ---------------------------------------------------------------------------
# Ciphertext must differ from plaintext
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cipher", crypto.SUPPORTED_CIPHERS)
def test_ciphertext_differs_from_plaintext(cipher):
    """The ciphertext bytes must not equal the plaintext bytes."""
    result = crypto.encrypt(_PLAINTEXT, _PASSPHRASE, cipher)
    assert result["ciphertext"] != _PLAINTEXT


# ---------------------------------------------------------------------------
# Each encryption call generates a unique nonce
# ---------------------------------------------------------------------------

def test_nonces_are_unique():
    """Two separate calls to encrypt() produce different nonces (probabilistic guarantee)."""
    r1 = crypto.encrypt(_PLAINTEXT, _PASSPHRASE, "Ascon-128")
    r2 = crypto.encrypt(_PLAINTEXT, _PASSPHRASE, "Ascon-128")
    assert r1["nonce"] != r2["nonce"]


# ---------------------------------------------------------------------------
# Tampered ciphertext must not decrypt successfully
# ---------------------------------------------------------------------------

def test_tampered_ciphertext_raises():
    """Flipping a byte in the ciphertext causes decrypt() to raise ValueError."""
    result = crypto.encrypt(_PLAINTEXT, _PASSPHRASE, "Ascon-128")
    tampered = bytearray(result["ciphertext"])
    tampered[0] ^= 0xFF
    bad_result = dict(result, ciphertext=bytes(tampered))
    with pytest.raises(ValueError):
        crypto.decrypt(bad_result, _PASSPHRASE)


# ---------------------------------------------------------------------------
# Unsupported cipher name raises ValueError at encrypt time
# ---------------------------------------------------------------------------

def test_unknown_cipher_raises():
    """encrypt() raises ValueError immediately if the cipher name is unrecognised."""
    with pytest.raises(ValueError, match="Unsupported cipher"):
        crypto.encrypt(_PLAINTEXT, _PASSPHRASE, "ROT13")


# ---------------------------------------------------------------------------
# Empty passphrase is rejected before any crypto work
# ---------------------------------------------------------------------------

def test_empty_passphrase_raises():
    """encrypt() raises ValueError for an empty passphrase string."""
    with pytest.raises(ValueError):
        crypto.encrypt(_PLAINTEXT, "", "Ascon-128")


# ---------------------------------------------------------------------------
# Public derive_key returns bytes of the correct length for each cipher
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cipher,expected_len", [
    ("Ascon-128",         16),
    ("ChaCha20-Poly1305", 32),
    ("AES-256-GCM",       32),
])
def test_derive_key_length(cipher, expected_len):
    """derive_key() returns a byte string of the length expected by the cipher."""
    import os
    salt = os.urandom(16)
    key  = crypto.derive_key(_PASSPHRASE, salt, cipher)
    assert isinstance(key, bytes)
    assert len(key) == expected_len


# ---------------------------------------------------------------------------
# Deniable key file missing partition fields raises ValueError on read
# ---------------------------------------------------------------------------

def test_read_deniable_key_missing_partition_raises(tmp_path):
    """read_key_file raises ValueError for a deniable=true file without partition_seed."""
    import json
    path = tmp_path / "incomplete_deniable.json"
    # Write a key file that claims deniable=true but omits partition_seed/partition_half
    path.write_text(json.dumps({
        "cipher":    "Ascon-128",
        "steg_mode": "adaptive",
        "deniable":  True,
        "nonce":     "AAAAAAAAAAAAAAAAAAAAAA==",
        "salt":      "AAAAAAAAAAAAAAAAAAAAAA==",
        "info_type": "text",
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="[Pp]artition"):
        crypto.read_key_file(path)
