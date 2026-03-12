# Copyright (C) 2026 Daniel Iwugo
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: tests/test_key_file.py
# Unit tests for crypto.write_key_file() and crypto.read_key_file().

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from core import crypto


# ---------------------------------------------------------------------------
# Round-trip: non-deniable key file
# ---------------------------------------------------------------------------

def test_write_read_roundtrip_non_deniable(tmp_path):
    """write_key_file + read_key_file preserves all fields exactly (non-deniable)."""
    nonce  = os.urandom(16)
    salt   = os.urandom(16)
    cipher = "ChaCha20-Poly1305"
    path   = tmp_path / "key.json"

    crypto.write_key_file(
        path, nonce=nonce, salt=salt,
        cipher=cipher, info_type="text", steg_mode="sequential",
    )
    result = crypto.read_key_file(path)

    assert result["cipher"]    == cipher
    assert result["nonce"]     == nonce
    assert result["salt"]      == salt
    assert result["info_type"] == "text"
    assert result["steg_mode"] == "sequential"
    assert result["deniable"]  is False


# ---------------------------------------------------------------------------
# Round-trip: deniable key file (includes partition_seed and partition_half)
# ---------------------------------------------------------------------------

def test_write_read_roundtrip_deniable(tmp_path):
    """write_key_file + read_key_file preserves all deniable-specific fields exactly."""
    nonce          = os.urandom(16)
    salt           = os.urandom(16)
    partition_seed = os.urandom(16)
    path           = tmp_path / "deniable_key.json"

    crypto.write_key_file(
        path, nonce=nonce, salt=salt,
        cipher="Ascon-128", info_type="text",
        steg_mode="adaptive", deniable=True,
        partition_seed=partition_seed, partition_half=0,
    )
    result = crypto.read_key_file(path)

    assert result["deniable"]        is True
    assert result["partition_seed"]  == partition_seed
    assert result["partition_half"]  == 0
    assert result["nonce"]           == nonce
    assert result["salt"]            == salt


# ---------------------------------------------------------------------------
# Missing required field raises ValueError
# ---------------------------------------------------------------------------

def test_missing_required_field_raises(tmp_path):
    """A key file missing a required field ('cipher') causes read_key_file to raise ValueError."""
    path = tmp_path / "bad_key.json"
    # Write a valid-looking JSON file but omit "cipher"
    path.write_text(json.dumps({
        "nonce":     "AAAAAAAAAAAAAAAAAAAAAA==",
        "salt":      "AAAAAAAAAAAAAAAAAAAAAA==",
        "info_type": "text",
        "steg_mode": "adaptive",
        "deniable":  False,
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="[Mm]issing"):
        crypto.read_key_file(path)


# ---------------------------------------------------------------------------
# Malformed (non-JSON) file raises ValueError
# ---------------------------------------------------------------------------

def test_malformed_json_raises(tmp_path):
    """A key file containing truncated/invalid JSON raises ValueError."""
    path = tmp_path / "truncated.json"
    path.write_bytes(b'{"cipher": "Ascon-128", "nonce":')  # incomplete JSON

    with pytest.raises(ValueError):
        crypto.read_key_file(path)


# ---------------------------------------------------------------------------
# Non-existent path raises ValueError (OSError is wrapped by read_key_file)
# ---------------------------------------------------------------------------

def test_nonexistent_path_raises(tmp_path):
    """read_key_file on a path that does not exist raises ValueError."""
    with pytest.raises(ValueError):
        crypto.read_key_file(tmp_path / "does_not_exist.json")
