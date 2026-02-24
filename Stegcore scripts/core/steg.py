# Copyright (C) 2025 Mercury
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: core/steg.py
# Description: LSB steganography with two modes:
#
#   "adaptive"   — Adaptive LSB + spread spectrum. Only embeds in high-variance
#                  (textured/edge) pixels, bits scattered pseudo-randomly via a
#                  key-seeded PRNG. Defeats standard steganalysis tools.
#                  Requires a textured cover image; lower raw capacity.
#
#   "sequential" — Standard sequential LSB across all pixels. Higher capacity,
#                  works on any image, but detectable by steganalysis tools.
#
# The mode used during embedding is stored in the key file and read back
# automatically on extraction — users never need to specify it twice.

import numpy as np
from pathlib import Path
from PIL import Image
from numpy.lib.stride_tricks import sliding_window_view


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SUPPORTED_MODES = ["adaptive", "sequential"]

_VARIANCE_THRESHOLD = 10.0
_HEADER_BITS        = 32   # 32-bit payload length header


# ---------------------------------------------------------------------------
# Bit manipulation helpers
# ---------------------------------------------------------------------------

def _bytes_to_bits(data: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def _bits_to_bytes(bits: np.ndarray) -> bytes:
    remainder = len(bits) % 8
    if remainder:
        bits = np.concatenate([bits, np.zeros(8 - remainder, dtype=np.uint8)])
    return np.packbits(bits).tobytes()


def _int_to_bits(value: int, n_bits: int) -> np.ndarray:
    bits = np.zeros(n_bits, dtype=np.uint8)
    for i in range(n_bits):
        bits[n_bits - 1 - i] = (value >> i) & 1
    return bits


def _bits_to_int(bits: np.ndarray) -> int:
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return value


# ---------------------------------------------------------------------------
# Embedding map  (adaptive mode)
# ---------------------------------------------------------------------------

def _compute_embedding_map(img_array: np.ndarray,
                            threshold: float = _VARIANCE_THRESHOLD) -> np.ndarray:
    """
    Compute a boolean pixel mask for adaptive embedding.

    IMPORTANT: LSBs are zeroed before variance computation so the map is
    identical whether called on the original image or the stego image.
    This is what makes round-trip extraction reliable.

    Args:
        img_array: uint8 image array of shape (H, W, C).
        threshold: Local variance threshold.

    Returns:
        Boolean mask of shape (H, W).
    """
    # Zero the LSB of every channel — makes the map invariant to embedding
    baseline = (img_array & np.uint8(0xFE)).astype(np.float32)

    gray   = baseline.mean(axis=2)
    padded = np.pad(gray, 1, mode="reflect")

    windows   = sliding_window_view(padded, (3, 3))
    local_var = windows.reshape(*windows.shape[:2], -1).var(axis=2)

    return local_var > threshold


# ---------------------------------------------------------------------------
# Index generation
# ---------------------------------------------------------------------------

def _get_indices_adaptive(img_array: np.ndarray,
                           pixel_mask: np.ndarray,
                           key: bytes) -> np.ndarray:
    """
    Shuffled flat indices of eligible channels, seeded from key.
    Identical key + identical image always produces identical ordering.
    """
    H, W, C      = img_array.shape
    channel_mask = np.stack([pixel_mask] * C, axis=2)
    flat_indices = np.where(channel_mask.ravel())[0]

    seed = int.from_bytes(key[:8], "big")
    rng  = np.random.default_rng(seed)
    rng.shuffle(flat_indices)

    return flat_indices


def _get_indices_sequential(img_array: np.ndarray) -> np.ndarray:
    """All flat channel indices in natural order."""
    return np.arange(img_array.size, dtype=np.int64)


# ---------------------------------------------------------------------------
# Low-level read / write
# ---------------------------------------------------------------------------

def _write_bits(img_flat: np.ndarray,
                indices: np.ndarray,
                bits: np.ndarray) -> None:
    n = len(bits)
    img_flat[indices[:n]] = (img_flat[indices[:n]] & np.uint8(0xFE)) | bits.astype(np.uint8)


def _read_bits(img_flat: np.ndarray,
               indices: np.ndarray,
               n: int) -> np.ndarray:
    return (img_flat[indices[:n]] & np.uint8(1)).astype(np.uint8)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def embed(cover_image_path: str | Path,
          payload_path:     str | Path,
          output_path:      str | Path,
          key:  bytes = None,
          mode: str   = "adaptive") -> Path:
    """
    Embed a payload into a cover image using LSB steganography.

    Args:
        cover_image_path: Path to the cover image (.png or .jpg).
        payload_path:     Path to the binary payload to hide.
        output_path:      Destination path for the stego image (.png).
        key:              Key bytes for spread-spectrum seeding (adaptive mode).
        mode:             "adaptive" or "sequential".

    Returns:
        Path to the saved stego image.

    Raises:
        ValueError:   Insufficient capacity or unsupported mode.
        RuntimeError: Unexpected failure.
    """
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported steg mode '{mode}'. Choose from: {SUPPORTED_MODES}")

    cover_image_path = Path(cover_image_path)
    payload_path     = Path(payload_path)
    output_path      = Path(output_path)

    payload   = payload_path.read_bytes()
    img       = Image.open(cover_image_path).convert("RGB")
    img_array = np.array(img, dtype=np.uint8)

    if mode == "adaptive":
        if key is None:
            raise ValueError("Adaptive mode requires a key for spread-spectrum seeding.")
        pixel_mask = _compute_embedding_map(img_array)
        indices    = _get_indices_adaptive(img_array, pixel_mask, key)
    else:
        indices = _get_indices_sequential(img_array)

    header_bits  = _int_to_bits(len(payload), _HEADER_BITS)
    payload_bits = _bytes_to_bits(payload)
    all_bits     = np.concatenate([header_bits, payload_bits])

    if len(all_bits) > len(indices):
        available_bytes = (len(indices) - _HEADER_BITS) // 8
        raise ValueError(
            f"Insufficient capacity in this image for the given payload.\n"
            f"Available: ~{available_bytes:,} bytes  |  "
            f"Required: ~{len(payload):,} bytes.\n"
            + (
                "In adaptive mode, try a larger or more textured cover image, "
                "or switch to sequential mode for higher raw capacity."
                if mode == "adaptive"
                else "Try a larger cover image."
            )
        )

    img_flat = img_array.ravel()
    _write_bits(img_flat, indices, all_bits)
    Image.fromarray(img_array).save(str(output_path), format="PNG")

    return output_path


def extract(stego_image_path: str | Path,
            output_path:      str | Path,
            key:  bytes = None,
            mode: str   = "adaptive") -> Path:
    """
    Extract a hidden payload from a stego image.

    Args:
        stego_image_path: Path to the stego image.
        output_path:      Path where the extracted payload will be written.
        key:              Key bytes matching those used during embedding.
        mode:             Must match the mode used during embedding.

    Returns:
        Path to the extracted payload file.

    Raises:
        ValueError:   No valid payload detected, or wrong mode/key.
        RuntimeError: Unexpected failure.
    """
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported steg mode '{mode}'. Choose from: {SUPPORTED_MODES}")

    stego_image_path = Path(stego_image_path)
    output_path      = Path(output_path)

    img       = Image.open(stego_image_path).convert("RGB")
    img_array = np.array(img, dtype=np.uint8)

    if mode == "adaptive":
        if key is None:
            raise ValueError("Adaptive mode requires a key for spread-spectrum seeding.")
        pixel_mask = _compute_embedding_map(img_array)
        indices    = _get_indices_adaptive(img_array, pixel_mask, key)
    else:
        indices = _get_indices_sequential(img_array)

    img_flat = img_array.ravel()

    # Read 32-bit length header
    header_bits = _read_bits(img_flat, indices, _HEADER_BITS)
    payload_len = _bits_to_int(header_bits)

    max_possible = (len(indices) - _HEADER_BITS) // 8
    if payload_len == 0 or payload_len > max_possible:
        raise ValueError(
            "No valid payload detected in this image.\n"
            "Check that you are using the correct stego image and key file."
        )

    payload_bits = _read_bits(img_flat, indices[_HEADER_BITS:], payload_len * 8)
    payload      = _bits_to_bytes(payload_bits)[:payload_len]

    output_path.write_bytes(payload)
    return output_path


def get_capacity(image_path: str | Path, mode: str = "adaptive") -> dict:
    """
    Calculate the embedding capacity of an image.

    Args:
        image_path: Path to the image.
        mode:       "adaptive" or "sequential".

    Returns:
        Dict with keys: available_bytes (int), mode (str).
    """
    img       = Image.open(Path(image_path)).convert("RGB")
    img_array = np.array(img, dtype=np.uint8)

    if mode == "adaptive":
        pixel_mask = _compute_embedding_map(img_array)
        H, W, C    = img_array.shape
        n_indices  = int(pixel_mask.sum()) * C
    else:
        n_indices = img_array.size

    available_bytes = max(0, (n_indices - _HEADER_BITS) // 8)
    return {"available_bytes": available_bytes, "mode": mode}


def score_cover_image(image_path: str | Path) -> dict:
    """
    Analyse a cover image and return suitability metrics for steganography.

    Scores are computed for both adaptive and sequential modes since capacity
    differs significantly between them.

    Args:
        image_path: Path to the candidate cover image.

    Returns:
        Dict with keys:
            entropy (float):            Shannon entropy of the image (0–8).
            texture_density (float):    Fraction of pixels suitable for adaptive mode (0–1).
            adaptive_capacity (int):    Max payload bytes in adaptive mode.
            sequential_capacity (int):  Max payload bytes in sequential mode.
            score (int):                Composite cover quality score (0–100).
            label (str):                "Poor" | "Fair" | "Good" | "Excellent".
            width (int):                Image width in pixels.
            height (int):               Image height in pixels.
    """
    img       = Image.open(Path(image_path)).convert("RGB")
    img_array = np.array(img, dtype=np.uint8)
    H, W, C   = img_array.shape

    # --- Entropy ---
    # Shannon entropy across all pixel values gives a measure of
    # information density. Higher entropy = more natural noise = better cover.
    flat          = img_array.ravel()
    value_counts  = np.bincount(flat, minlength=256).astype(np.float64)
    probabilities = value_counts / flat.size
    probabilities = probabilities[probabilities > 0]
    entropy       = float(-np.sum(probabilities * np.log2(probabilities)))
    # Normalise to 0–1  (theoretical max is 8 for uniform uint8)
    entropy_norm  = entropy / 8.0

    # --- Texture density ---
    pixel_mask       = _compute_embedding_map(img_array)
    texture_density  = float(pixel_mask.sum()) / (H * W)

    # --- Capacity ---
    adaptive_cap    = get_capacity(image_path, mode="adaptive")["available_bytes"]
    sequential_cap  = get_capacity(image_path, mode="sequential")["available_bytes"]

    # --- Composite score (0–100) ---
    # Weights: entropy 40%, texture density 40%, dimension bonus 20%
    dimension_score = min(1.0, (H * W) / (1920 * 1080))  # full marks at 1080p+
    raw_score       = (
        0.40 * entropy_norm +
        0.40 * min(1.0, texture_density / 0.5) +  # 50% texture = full marks
        0.20 * dimension_score
    )
    score = int(round(raw_score * 100))

    if score >= 75:
        label = "Excellent"
    elif score >= 55:
        label = "Good"
    elif score >= 35:
        label = "Fair"
    else:
        label = "Poor"

    return {
        "entropy":              round(entropy, 2),
        "texture_density":      round(texture_density, 3),
        "adaptive_capacity":    adaptive_cap,
        "sequential_capacity":  sequential_cap,
        "score":                score,
        "label":                label,
        "width":                W,
        "height":               H,
    }