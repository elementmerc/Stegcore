# Copyright (C) 2026 Daniel Iwugo
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: tests/conftest.py
# Shared pytest fixtures for the Stegcore test suite.

import wave

import numpy as np
import pytest
from pathlib import Path
from PIL import Image


@pytest.fixture()
def cover_png(tmp_path) -> Path:
    """800×600 random-pixel PNG.  High local variance gives good adaptive capacity."""
    rng = np.random.default_rng(42)
    arr = rng.integers(0, 256, (600, 800, 3), dtype=np.uint8)
    p = tmp_path / "cover.png"
    Image.frombytes("RGB", (800, 600), arr.tobytes()).save(str(p), format="PNG")
    return p


@pytest.fixture()
def cover_jpeg(tmp_path) -> Path:
    """800×600 random-pixel JPEG cover. steg.embed() auto-corrects output to .png."""
    rng = np.random.default_rng(43)
    arr = rng.integers(0, 256, (600, 800, 3), dtype=np.uint8)
    p = tmp_path / "cover.jpg"
    Image.frombytes("RGB", (800, 600), arr.tobytes()).save(str(p), format="JPEG", quality=95)
    return p


@pytest.fixture()
def cover_wav(tmp_path) -> Path:
    """2-second 44100 Hz 16-bit mono WAV with pseudo-random samples (~176 KB capacity)."""
    rng = np.random.default_rng(44)
    samples = rng.integers(-32768, 32767, 44100 * 2, dtype=np.int16)
    p = tmp_path / "cover.wav"
    with wave.open(str(p), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(samples.tobytes())
    return p
