# Copyright (C) 2026 Daniel Iwugo
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: core/crypto.py
# Description: Unified encryption and decryption across all supported ciphers.
#              Key derivation is handled by Argon2id — the passphrase IS the key.
#              No raw key material is ever exported to disk.
#              Payloads are Zstandard-compressed before encryption.

import base64
import json
import os
from pathlib import Path

import pyzstd

# Ascon-128
from ascon._ascon import ascon_encrypt, ascon_decrypt

# ChaCha20-Poly1305 and AES-256-GCM
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305, AESGCM

# Argon2id key derivation
from argon2.low_level import hash_secret_raw, Type


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_CIPHERS = ["Ascon-128", "ChaCha20-Poly1305", "AES-256-GCM"]

_CIPHER_PARAMS = {
    "Ascon-128":         {"key_len": 16, "nonce_len": 16},
    "ChaCha20-Poly1305": {"key_len": 32, "nonce_len": 12},
    "AES-256-GCM":       {"key_len": 32, "nonce_len": 12},
}

_ARGON2_TIME_COST   = 2
_ARGON2_MEMORY_COST = 65536   # 64 MB
_ARGON2_PARALLELISM = 2
_ARGON2_SALT_LEN    = 16


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------

def _derive_key(passphrase: str, salt: bytes, key_len: int) -> bytes:
    return hash_secret_raw(
        secret=passphrase.encode("utf-8"),
        salt=salt,
        time_cost=_ARGON2_TIME_COST,
        memory_cost=_ARGON2_MEMORY_COST,
        parallelism=_ARGON2_PARALLELISM,
        hash_len=key_len,
        type=Type.ID,
    )


# ---------------------------------------------------------------------------
# Encryption
# ---------------------------------------------------------------------------

def encrypt(plaintext: bytes, passphrase: str, cipher: str = "Ascon-128") -> dict:
    """
    Compress and encrypt plaintext with the chosen cipher and an Argon2id-derived key.

    Returns a dict with: ciphertext (bytes), nonce (bytes), salt (bytes), cipher (str).

    Raises:
        ValueError:  If passphrase is empty or cipher is unsupported.
        RuntimeError: If compression or encryption fails.
    """
    if not passphrase:
        raise ValueError("Passphrase cannot be empty.")
    if cipher not in SUPPORTED_CIPHERS:
        raise ValueError(f"Unsupported cipher '{cipher}'. Choose from: {SUPPORTED_CIPHERS}")

    params = _CIPHER_PARAMS[cipher]
    salt   = os.urandom(_ARGON2_SALT_LEN)
    nonce  = os.urandom(params["nonce_len"])
    key    = _derive_key(passphrase, salt, params["key_len"])

    try:
        compressed = pyzstd.compress(plaintext)
    except Exception as exc:
        raise RuntimeError(f"Compression failed: {exc}") from exc

    try:
        ciphertext = _encrypt_with(cipher, key, nonce, compressed)
    except Exception as exc:
        raise RuntimeError(f"Encryption failed: {exc}") from exc

    return {"ciphertext": ciphertext, "nonce": nonce, "salt": salt, "cipher": cipher, "key": key}


def _encrypt_with(cipher: str, key: bytes, nonce: bytes, plaintext: bytes) -> bytes:
    if cipher == "Ascon-128":
        return ascon_encrypt(key, nonce, b"", plaintext, "Ascon-128")
    if cipher == "ChaCha20-Poly1305":
        return ChaCha20Poly1305(key).encrypt(nonce, plaintext, None)
    if cipher == "AES-256-GCM":
        return AESGCM(key).encrypt(nonce, plaintext, None)
    raise ValueError(f"Unknown cipher: {cipher}")


# ---------------------------------------------------------------------------
# Decryption
# ---------------------------------------------------------------------------

def decrypt(payload: dict, passphrase: str) -> bytes:
    """
    Decrypt and decompress a payload dict produced by encrypt().

    Raises ValueError for wrong passphrase or corrupted data.
    """
    cipher     = payload["cipher"]
    nonce      = payload["nonce"]
    salt       = payload["salt"]
    ciphertext = payload["ciphertext"]

    if cipher not in SUPPORTED_CIPHERS:
        raise ValueError(f"Unsupported cipher in key file: '{cipher}'")

    params = _CIPHER_PARAMS[cipher]
    key    = _derive_key(passphrase, salt, params["key_len"])

    try:
        compressed = _decrypt_with(cipher, key, nonce, ciphertext)
    except Exception as exc:
        raise ValueError("Decryption failed. Invalid passphrase or corrupted data.") from exc

    if compressed is None:
        raise ValueError("Decryption failed. Invalid passphrase or corrupted data.")

    try:
        plaintext = pyzstd.decompress(compressed)
    except Exception as exc:
        raise ValueError(f"Decompression failed. Data may be corrupted: {exc}") from exc

    return plaintext


def _decrypt_with(cipher: str, key: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
    if cipher == "Ascon-128":
        return ascon_decrypt(key, nonce, b"", ciphertext, "Ascon-128")
    if cipher == "ChaCha20-Poly1305":
        return ChaCha20Poly1305(key).decrypt(nonce, ciphertext, None)
    if cipher == "AES-256-GCM":
        return AESGCM(key).decrypt(nonce, ciphertext, None)
    raise ValueError(f"Unknown cipher: {cipher}")


# ---------------------------------------------------------------------------
# Key file I/O  (JSON + base64)
# ---------------------------------------------------------------------------

def write_key_file(path, nonce: bytes, salt: bytes, cipher: str, info_type: str,
                   steg_mode: str = "adaptive", deniable: bool = False,
                   partition_seed: bytes = None, partition_half: int = None) -> None:
    """
    Write encryption metadata to a JSON key file.

    For deniable embeds, both real and decoy key files are structurally
    identical. Neither can be identified as "real" from the file alone.
    """
    data = {
        "cipher":    cipher,
        "steg_mode": steg_mode,
        "deniable":  deniable,
        "nonce":     base64.b64encode(nonce).decode("ascii"),
        "salt":      base64.b64encode(salt).decode("ascii"),
        "info_type": info_type,
    }
    if deniable and partition_seed is not None and partition_half is not None:
        data["partition_seed"] = base64.b64encode(partition_seed).decode("ascii")
        data["partition_half"] = partition_half
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def read_key_file(path) -> dict:
    """
    Read and parse a JSON key file.

    Returns dict with: cipher (str), nonce (bytes), salt (bytes), info_type (str).
    Raises ValueError if the file is missing, malformed, or a legacy v1 file.
    """
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read key file: {exc}") from exc

    required = {"cipher", "nonce", "salt", "info_type"}
    missing  = required - raw.keys()
    if missing:
        raise ValueError(
            f"Key file is malformed. Missing fields: {missing}.\n"
            "This may be a v1 key file. v2 key files are not backwards compatible."
        )

    try:
        result = {
            "cipher":    raw["cipher"],
            "steg_mode": raw.get("steg_mode", "sequential"),
            "deniable":  raw.get("deniable", False),
            "nonce":     base64.b64decode(raw["nonce"]),
            "salt":      base64.b64decode(raw["salt"]),
            "info_type": raw["info_type"],
        }
        if result["deniable"]:
            if "partition_seed" not in raw or "partition_half" not in raw:
                raise ValueError("Deniable key file is missing partition fields.")
            result["partition_seed"] = base64.b64decode(raw["partition_seed"])
            result["partition_half"] = int(raw["partition_half"])
        return result
    except (ValueError, KeyError):
        raise
    except Exception as exc:
        raise ValueError(f"Key file contains invalid data: {exc}") from exc


# ---------------------------------------------------------------------------
# Public key derivation
# Used by the extract flow to re-derive the key for spread-spectrum seeding.
# ---------------------------------------------------------------------------

def derive_key(passphrase: str, salt: bytes, cipher: str) -> bytes:
    """
    Re-derive the encryption key from a passphrase and stored salt.

    Args:
        passphrase: User passphrase.
        salt:       Salt from the key file.
        cipher:     Cipher name (determines required key length).

    Returns:
        Derived key bytes.
    """
    key_len = _CIPHER_PARAMS[cipher]["key_len"]
    return _derive_key(passphrase, salt, key_len)