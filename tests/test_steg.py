# Copyright (C) 2026 Daniel Iwugo
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: tests/test_steg.py
# Unit tests for core/steg.py — standard embed/extract and deniable mode.

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from core import crypto, steg


_PAYLOAD = b"stegcore test payload 1234"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_payload(tmp_path: Path) -> Path:
    p = tmp_path / "payload.bin"
    p.write_bytes(_PAYLOAD)
    return p


# ---------------------------------------------------------------------------
# Standard embed/extract — PNG cover, adaptive mode
# ---------------------------------------------------------------------------

def test_embed_extract_png_adaptive(cover_png, tmp_path):
    """PNG cover + adaptive mode: extracted bytes exactly match the original payload."""
    key          = os.urandom(32)
    payload_file = _write_payload(tmp_path)
    stego        = steg.embed(cover_png, payload_file, tmp_path / "stego.png",
                               key=key, mode="adaptive")
    out = tmp_path / "extracted.bin"
    steg.extract(stego, out, key=key, mode="adaptive")
    assert out.read_bytes() == _PAYLOAD


# ---------------------------------------------------------------------------
# Standard embed/extract — PNG cover, sequential mode
# ---------------------------------------------------------------------------

def test_embed_extract_png_sequential(cover_png, tmp_path):
    """PNG cover + sequential mode: extracted bytes exactly match the original payload."""
    payload_file = _write_payload(tmp_path)
    stego        = steg.embed(cover_png, payload_file, tmp_path / "stego.png",
                               key=None, mode="sequential")
    out = tmp_path / "extracted.bin"
    steg.extract(stego, out, key=None, mode="sequential")
    assert out.read_bytes() == _PAYLOAD


# ---------------------------------------------------------------------------
# JPEG cover → output is always PNG
# ---------------------------------------------------------------------------

def test_embed_extract_jpeg_output_is_png(cover_jpeg, tmp_path):
    """JPEG cover: embed() auto-corrects output extension to .png; round-trip succeeds."""
    key          = os.urandom(32)
    payload_file = _write_payload(tmp_path)
    # Request .jpg output — should be silently rewritten to .png
    returned_path = steg.embed(cover_jpeg, payload_file, tmp_path / "stego.jpg",
                                key=key, mode="adaptive")
    assert returned_path.suffix.lower() == ".png", (
        f"Expected .png output for JPEG cover, got '{returned_path.suffix}'"
    )
    out = tmp_path / "extracted.bin"
    steg.extract(returned_path, out, key=key, mode="adaptive")
    assert out.read_bytes() == _PAYLOAD


# ---------------------------------------------------------------------------
# WAV cover
# ---------------------------------------------------------------------------

def test_embed_extract_wav(cover_wav, tmp_path):
    """WAV cover: embed/extract round-trip returns the exact original payload bytes."""
    payload_file = _write_payload(tmp_path)
    stego = steg.embed(cover_wav, payload_file, tmp_path / "stego.wav")
    out   = tmp_path / "extracted.bin"
    steg.extract(stego, out)
    assert out.read_bytes() == _PAYLOAD


# ---------------------------------------------------------------------------
# Deniable mode — real payload recoverable with real key + real partition half
# ---------------------------------------------------------------------------

def test_deniable_real_extraction(cover_png, tmp_path):
    """Deniable embed: extract with real key and real partition half returns real payload."""
    real_payload   = b"real secret message"
    decoy_payload  = b"nothing here"
    real_key       = os.urandom(16)
    decoy_key      = os.urandom(16)
    partition_seed = os.urandom(16)

    stego = steg.embed_deniable(
        cover_png, real_payload, decoy_payload,
        tmp_path / "stego.png", real_key, decoy_key, partition_seed
    )
    recovered = steg.extract_deniable(stego, real_key, partition_seed, partition_half=0)
    assert recovered == real_payload


# ---------------------------------------------------------------------------
# Deniable mode — decoy payload recoverable with decoy key + decoy partition half
# ---------------------------------------------------------------------------

def test_deniable_decoy_extraction(cover_png, tmp_path):
    """Deniable embed: extract with decoy key and decoy partition half returns decoy payload."""
    real_payload   = b"real secret message"
    decoy_payload  = b"nothing here"
    real_key       = os.urandom(16)
    decoy_key      = os.urandom(16)
    partition_seed = os.urandom(16)

    stego = steg.embed_deniable(
        cover_png, real_payload, decoy_payload,
        tmp_path / "stego.png", real_key, decoy_key, partition_seed
    )
    recovered = steg.extract_deniable(stego, decoy_key, partition_seed, partition_half=1)
    assert recovered == decoy_payload


# ---------------------------------------------------------------------------
# Deniable key files — real and decoy have the same set of JSON fields
# ---------------------------------------------------------------------------

def test_deniable_key_files_structurally_identical(tmp_path):
    """Real and decoy deniable key files expose the same JSON keys — neither is distinguishable."""
    partition_seed = os.urandom(16)
    real_kf  = tmp_path / "real.json"
    decoy_kf = tmp_path / "decoy.json"

    crypto.write_key_file(
        real_kf,
        nonce=os.urandom(16), salt=os.urandom(16),
        cipher="Ascon-128", info_type="text",
        steg_mode="adaptive", deniable=True,
        partition_seed=partition_seed, partition_half=0,
    )
    crypto.write_key_file(
        decoy_kf,
        nonce=os.urandom(16), salt=os.urandom(16),
        cipher="Ascon-128", info_type="text",
        steg_mode="adaptive", deniable=True,
        partition_seed=os.urandom(16), partition_half=1,
    )

    real_d  = json.loads(real_kf.read_text())
    decoy_d = json.loads(decoy_kf.read_text())
    assert set(real_d.keys()) == set(decoy_d.keys()), (
        "Real and decoy key files must expose the same JSON field names"
    )


# ---------------------------------------------------------------------------
# Deniable mode — real payload must not emerge from the wrong partition half
# ---------------------------------------------------------------------------

def test_deniable_wrong_half_does_not_return_real_payload(cover_png, tmp_path):
    """Using the real key but wrong partition half must not recover the real payload."""
    real_payload   = b"real secret message"
    decoy_payload  = b"nothing here"
    real_key       = os.urandom(16)
    decoy_key      = os.urandom(16)
    partition_seed = os.urandom(16)

    stego = steg.embed_deniable(
        cover_png, real_payload, decoy_payload,
        tmp_path / "stego.png", real_key, decoy_key, partition_seed
    )

    # Attempt extraction from the wrong half (half=1 belongs to the decoy key's region)
    try:
        wrong = steg.extract_deniable(stego, real_key, partition_seed, partition_half=1)
        assert wrong != real_payload, (
            "Real payload must not be extractable from the decoy partition half"
        )
    except ValueError:
        pass  # Header validation correctly rejected the garbage data — also acceptable


# ---------------------------------------------------------------------------
# score_cover_image — all returned fields present and in expected ranges
# ---------------------------------------------------------------------------

def test_score_cover_image_fields(cover_png):
    """score_cover_image returns all expected keys with values in documented ranges."""
    s = steg.score_cover_image(cover_png)

    expected_keys = {"entropy", "texture_density", "adaptive_capacity",
                     "sequential_capacity", "score", "label", "width", "height"}
    assert expected_keys == s.keys()

    assert isinstance(s["score"], int) and 0 <= s["score"] <= 100
    assert s["label"] in ("Excellent", "Good", "Fair", "Poor")
    assert isinstance(s["entropy"], float) and 0.0 <= s["entropy"] <= 8.0
    assert isinstance(s["texture_density"], float) and 0.0 <= s["texture_density"] <= 1.0
    assert isinstance(s["adaptive_capacity"], int) and s["adaptive_capacity"] >= 0
    assert isinstance(s["sequential_capacity"], int) and s["sequential_capacity"] >= 0
    assert s["width"] == 800
    assert s["height"] == 600


# ---------------------------------------------------------------------------
# get_capacity — WAV returns 0 (not image-based)
# ---------------------------------------------------------------------------

def test_get_capacity_wav_returns_zero(cover_wav):
    """get_capacity on a WAV file returns available_bytes=0 (WAV not capacity-tracked)."""
    cap = steg.get_capacity(cover_wav, mode="adaptive")
    assert cap["available_bytes"] == 0


# ---------------------------------------------------------------------------
# Error paths: unsupported format, bad mode, adaptive without key
# ---------------------------------------------------------------------------

def test_embed_unsupported_format_raises(tmp_path):
    """embed() on an unrecognised file extension raises ValueError immediately."""
    bad = tmp_path / "cover.xyz"
    bad.write_bytes(b"not an image")
    payload_file = tmp_path / "payload.bin"
    payload_file.write_bytes(b"x")
    with pytest.raises(ValueError, match="[Uu]nsupported"):
        steg.embed(bad, payload_file, tmp_path / "out.png")


def test_embed_unsupported_mode_raises(cover_png, tmp_path):
    """embed() with an unrecognised mode name raises ValueError."""
    payload_file = tmp_path / "payload.bin"
    payload_file.write_bytes(b"x")
    with pytest.raises(ValueError, match="[Uu]nsupported mode"):
        steg.embed(cover_png, payload_file, tmp_path / "out.png",
                   key=b"\x00" * 16, mode="lsb_magic")


def test_embed_adaptive_without_key_raises(cover_png, tmp_path):
    """embed() in adaptive mode without a key raises ValueError."""
    payload_file = tmp_path / "payload.bin"
    payload_file.write_bytes(b"x")
    with pytest.raises(ValueError, match="[Kk]ey"):
        steg.embed(cover_png, payload_file, tmp_path / "out.png",
                   key=None, mode="adaptive")


def test_embed_payload_too_large_raises(tmp_path):
    """embed() raises ValueError when the payload exceeds cover capacity."""
    import numpy as np
    from PIL import Image

    # A tiny 20×20 cover — sequential capacity ≈ (20*20*3 - 32) / 8 = 145 bytes
    arr = np.zeros((20, 20, 3), dtype=np.uint8)
    tiny = tmp_path / "tiny.png"
    Image.frombytes("RGB", (20, 20), arr.tobytes()).save(str(tiny), format="PNG")

    big_payload = tmp_path / "big.bin"
    big_payload.write_bytes(b"x" * 500)   # definitely too large
    with pytest.raises(ValueError, match="[Cc]apacity|[Ss]ufficient"):
        steg.embed(tiny, big_payload, tmp_path / "out.png",
                   key=None, mode="sequential")


def test_extract_no_payload_raises(tmp_path):
    """extract() on an all-zero (non-stego) PNG raises ValueError — no valid payload."""
    import numpy as np
    from PIL import Image

    # All-zero pixels → all LSBs = 0 → decoded header = 0 → no payload
    arr = np.zeros((64, 64, 3), dtype=np.uint8)
    blank = tmp_path / "blank.png"
    Image.frombytes("RGB", (64, 64), arr.tobytes()).save(str(blank), format="PNG")

    with pytest.raises(ValueError, match="[Pp]ayload"):
        steg.extract(blank, tmp_path / "out.bin", key=os.urandom(16), mode="adaptive")
