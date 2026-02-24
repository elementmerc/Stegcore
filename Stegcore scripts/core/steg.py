# Copyright (C) 2025 Mercury
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: core/steg.py
# Description: Multi-format steganography — PNG/JPG via LSB, JPEG via DCT,
#              WAV via sample LSB. Format is detected automatically from file
#              extension and routed to the appropriate algorithm.
#
#   PNG/BMP  — Adaptive or sequential LSB (lossless, LSB changes survive)
#   JPEG     — DCT-domain embedding (survives JPEG compression)
#   WAV      — Sample LSB (same principle as image LSB, on audio samples)

import wave
import numpy as np
from pathlib import Path
from PIL import Image
from numpy.lib.stride_tricks import sliding_window_view

try:
    import jpegio
    _JPEGIO_AVAILABLE = True
except ImportError:
    _JPEGIO_AVAILABLE = False


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SUPPORTED_MODES    = ["adaptive", "sequential"]
_VARIANCE_THRESHOLD = 10.0
_HEADER_BITS        = 32   # 32-bit payload length header

# DCT coefficients to skip — 0 (DC component) should never be modified
# as it controls block brightness and changes are very visible
_DCT_SKIP_ZERO = True


# ---------------------------------------------------------------------------
# Format routing helpers
# ---------------------------------------------------------------------------

def _get_format(path: Path) -> str:
    """Return normalised format string from file extension."""
    ext = path.suffix.lower()
    if ext in {".png", ".bmp"}:
        return "png"
    if ext in {".jpg", ".jpeg"}:
        return "jpeg"
    if ext == ".wav":
        return "wav"
    raise ValueError(
        f"Unsupported format '{ext}'.\n"
        "Supported: .png, .bmp, .jpg, .jpeg, .wav"
    )


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
# PNG / BMP — Adaptive LSB + spread spectrum
# ---------------------------------------------------------------------------

def _compute_embedding_map(img_array: np.ndarray,
                            threshold: float = _VARIANCE_THRESHOLD) -> np.ndarray:
    """
    Boolean pixel mask for adaptive embedding.
    LSBs are zeroed before variance computation so the map is identical
    on both the original and stego image.
    """
    baseline  = (img_array & np.uint8(0xFE)).astype(np.float32)
    gray      = baseline.mean(axis=2)
    padded    = np.pad(gray, 1, mode="reflect")
    windows   = sliding_window_view(padded, (3, 3))
    local_var = windows.reshape(*windows.shape[:2], -1).var(axis=2)
    return local_var > threshold


def _get_indices_adaptive(img_array, pixel_mask, key):
    H, W, C      = img_array.shape
    channel_mask = np.stack([pixel_mask] * C, axis=2)
    flat_indices = np.where(channel_mask.ravel())[0]
    seed         = int.from_bytes(key[:8], "big")
    rng          = np.random.default_rng(seed)
    rng.shuffle(flat_indices)
    return flat_indices


def _get_indices_sequential(img_array):
    return np.arange(img_array.size, dtype=np.int64)


def _write_bits(img_flat, indices, bits):
    n = len(bits)
    img_flat[indices[:n]] = (img_flat[indices[:n]] & np.uint8(0xFE)) | bits.astype(np.uint8)


def _read_bits(img_flat, indices, n):
    return (img_flat[indices[:n]] & np.uint8(1)).astype(np.uint8)


def _embed_png(cover_path, payload, output_path, key, mode):
    img       = Image.open(cover_path).convert("RGB")
    img_array = np.array(img, dtype=np.uint8)

    if mode == "adaptive":
        pixel_mask = _compute_embedding_map(img_array)
        indices    = _get_indices_adaptive(img_array, pixel_mask, key)
    else:
        indices = _get_indices_sequential(img_array)

    header_bits  = _int_to_bits(len(payload), _HEADER_BITS)
    payload_bits = _bytes_to_bits(payload)
    all_bits     = np.concatenate([header_bits, payload_bits])

    if len(all_bits) > len(indices):
        available = (len(indices) - _HEADER_BITS) // 8
        raise ValueError(
            f"Insufficient image capacity.\n"
            f"Available: ~{available:,} bytes | Required: ~{len(payload):,} bytes.\n"
            + ("Try a larger or more textured cover image, or use sequential mode."
               if mode == "adaptive" else "Try a larger cover image.")
        )

    img_flat = img_array.ravel()
    _write_bits(img_flat, indices, all_bits)
    Image.fromarray(img_array).save(str(output_path), format="PNG")


def _extract_png(stego_path, key, mode):
    img       = Image.open(stego_path).convert("RGB")
    img_array = np.array(img, dtype=np.uint8)

    if mode == "adaptive":
        pixel_mask = _compute_embedding_map(img_array)
        indices    = _get_indices_adaptive(img_array, pixel_mask, key)
    else:
        indices = _get_indices_sequential(img_array)

    img_flat    = img_array.ravel()
    header_bits = _read_bits(img_flat, indices, _HEADER_BITS)
    payload_len = _bits_to_int(header_bits)
    max_pos     = (len(indices) - _HEADER_BITS) // 8

    if payload_len == 0 or payload_len > max_pos:
        raise ValueError(
            "No valid payload detected.\n"
            "Check you are using the correct stego image and key file."
        )

    payload_bits = _read_bits(img_flat, indices[_HEADER_BITS:], payload_len * 8)
    return _bits_to_bytes(payload_bits)[:payload_len]


# ---------------------------------------------------------------------------
# JPEG — DCT-domain embedding
# ---------------------------------------------------------------------------

def _embed_jpeg(cover_path, payload, output_path):
    if not _JPEGIO_AVAILABLE:
        raise RuntimeError(
            "jpegio is not installed. Run: pip install jpegio"
        )

    jpeg    = jpegio.read(str(cover_path))
    all_bits = np.concatenate([
        _int_to_bits(len(payload), _HEADER_BITS),
        _bytes_to_bits(payload),
    ])
    bit_idx  = 0
    capacity = 0

    # Count capacity first
    for component in jpeg.coef_arrays:
        flat = component.ravel()
        for coef in flat:
            if coef != 0 and coef != 1 and coef != -1:
                capacity += 1

    if len(all_bits) > capacity:
        raise ValueError(
            f"JPEG has insufficient DCT capacity.\n"
            f"Available: ~{capacity // 8:,} bytes | Required: ~{len(payload):,} bytes.\n"
            "Try a larger or higher-quality JPEG."
        )

    # Embed into non-zero, non-one AC coefficients
    for component in jpeg.coef_arrays:
        if bit_idx >= len(all_bits):
            break
        flat = component.ravel()
        for i in range(len(flat)):
            if bit_idx >= len(all_bits):
                break
            coef = flat[i]
            if coef != 0 and coef != 1 and coef != -1:
                # Embed in LSB of coefficient, preserving sign
                flat[i] = (coef & ~1) | int(all_bits[bit_idx])
                bit_idx += 1

    jpegio.write(jpeg, str(output_path))


def _extract_jpeg(stego_path):
    if not _JPEGIO_AVAILABLE:
        raise RuntimeError(
            "jpegio is not installed. Run: pip install jpegio"
        )

    jpeg    = jpegio.read(str(stego_path))
    bits    = []

    for component in jpeg.coef_arrays:
        flat = component.ravel()
        for coef in flat:
            if coef != 0 and coef != 1 and coef != -1:
                bits.append(int(coef) & 1)

    if len(bits) < _HEADER_BITS:
        raise ValueError("No valid payload detected in this JPEG.")

    bits_arr    = np.array(bits, dtype=np.uint8)
    payload_len = _bits_to_int(bits_arr[:_HEADER_BITS])
    max_pos     = (len(bits) - _HEADER_BITS) // 8

    if payload_len == 0 or payload_len > max_pos:
        raise ValueError(
            "No valid payload detected in this JPEG.\n"
            "Check you are using the correct stego image and key file."
        )

    payload_bits = bits_arr[_HEADER_BITS: _HEADER_BITS + payload_len * 8]
    return _bits_to_bytes(payload_bits)[:payload_len]


# ---------------------------------------------------------------------------
# WAV — Sample LSB
# ---------------------------------------------------------------------------

def _embed_wav(cover_path, payload, output_path):
    with wave.open(str(cover_path), "rb") as wf:
        params      = wf.getparams()
        n_frames    = wf.getnframes()
        sample_width = wf.getsampwidth()
        raw_bytes   = wf.readframes(n_frames)

    samples = np.frombuffer(raw_bytes, dtype=np.uint8).copy()

    all_bits = np.concatenate([
        _int_to_bits(len(payload), _HEADER_BITS),
        _bytes_to_bits(payload),
    ])

    if len(all_bits) > len(samples):
        raise ValueError(
            f"WAV file has insufficient sample capacity.\n"
            f"Available: ~{(len(samples) - _HEADER_BITS) // 8:,} bytes | "
            f"Required: ~{len(payload):,} bytes.\n"
            "Try a longer audio file."
        )

    indices = np.arange(len(all_bits), dtype=np.int64)
    _write_bits(samples, indices, all_bits)

    with wave.open(str(output_path), "wb") as wf:
        wf.setparams(params)
        wf.writeframes(samples.tobytes())


def _extract_wav(stego_path):
    with wave.open(str(stego_path), "rb") as wf:
        raw_bytes = wf.readframes(wf.getnframes())

    samples     = np.frombuffer(raw_bytes, dtype=np.uint8)
    header_bits = (samples[:_HEADER_BITS] & np.uint8(1)).astype(np.uint8)
    payload_len = _bits_to_int(header_bits)
    max_pos     = (len(samples) - _HEADER_BITS) // 8

    if payload_len == 0 or payload_len > max_pos:
        raise ValueError(
            "No valid payload detected in this WAV file.\n"
            "Check you are using the correct stego audio and key file."
        )

    payload_bits = (
        samples[_HEADER_BITS: _HEADER_BITS + payload_len * 8] & np.uint8(1)
    ).astype(np.uint8)
    return _bits_to_bytes(payload_bits)[:payload_len]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def embed(cover_path:   str | Path,
          payload_path: str | Path,
          output_path:  str | Path,
          key:  bytes = None,
          mode: str   = "adaptive") -> Path:
    """
    Embed a payload into a cover file. Format is detected automatically
    from the cover file extension.

    PNG/BMP  → Adaptive or sequential LSB
    JPEG     → DCT-domain embedding
    WAV      → Sample LSB

    Args:
        cover_path:   Path to the cover file.
        payload_path: Path to the binary payload.
        output_path:  Destination path for stego file.
        key:          Key bytes (required for adaptive PNG mode).
        mode:         "adaptive" or "sequential" (PNG only).

    Returns:
        Path to the saved stego file.
    """
    cover_path   = Path(cover_path)
    payload_path = Path(payload_path)
    output_path  = Path(output_path)
    fmt          = _get_format(cover_path)
    payload      = payload_path.read_bytes()

    try:
        if fmt == "png":
            if mode not in SUPPORTED_MODES:
                raise ValueError(f"Unsupported mode '{mode}'.")
            if mode == "adaptive" and key is None:
                raise ValueError("Adaptive mode requires a key.")
            _embed_png(cover_path, payload, output_path, key, mode)

        elif fmt == "jpeg":
            # JPEG always uses DCT — mode and key are not used
            _embed_jpeg(cover_path, payload, output_path)

        elif fmt == "wav":
            _embed_wav(cover_path, payload, output_path)

    except (ValueError, RuntimeError):
        raise
    except Exception as exc:
        raise RuntimeError(f"Embedding failed: {exc}") from exc

    return output_path


def extract(stego_path:  str | Path,
            output_path: str | Path,
            key:  bytes = None,
            mode: str   = "adaptive") -> Path:
    """
    Extract a hidden payload from a stego file. Format is detected
    automatically from the file extension.

    Args:
        stego_path:  Path to the stego file.
        output_path: Path where the extracted payload will be written.
        key:         Key bytes matching those used during embedding (PNG adaptive).
        mode:        Must match the mode used during embedding (PNG only).

    Returns:
        Path to the extracted payload file.
    """
    stego_path  = Path(stego_path)
    output_path = Path(output_path)
    fmt         = _get_format(stego_path)

    try:
        if fmt == "png":
            payload = _extract_png(stego_path, key, mode)
        elif fmt == "jpeg":
            payload = _extract_jpeg(stego_path)
        elif fmt == "wav":
            payload = _extract_wav(stego_path)
    except (ValueError, RuntimeError):
        raise
    except Exception as exc:
        raise RuntimeError(f"Extraction failed: {exc}") from exc

    output_path.write_bytes(payload)
    return output_path


def get_capacity(image_path: str | Path, mode: str = "adaptive") -> dict:
    """
    Calculate embedding capacity. Supports PNG and JPEG.

    Returns dict with: available_bytes (int), mode (str).
    """
    path = Path(image_path)
    fmt  = _get_format(path)

    if fmt == "png":
        img       = Image.open(path).convert("RGB")
        img_array = np.array(img, dtype=np.uint8)
        if mode == "adaptive":
            pixel_mask = _compute_embedding_map(img_array)
            n_indices  = int(pixel_mask.sum()) * 3
        else:
            n_indices = img_array.size
        available = max(0, (n_indices - _HEADER_BITS) // 8)

    elif fmt == "jpeg":
        if not _JPEGIO_AVAILABLE:
            return {"available_bytes": 0, "mode": "dct"}
        jpeg     = jpegio.read(str(path))
        capacity = 0
        for component in jpeg.coef_arrays:
            flat = component.ravel()
            capacity += int(np.sum((flat != 0) & (flat != 1) & (flat != -1)))
        available = max(0, (capacity - _HEADER_BITS) // 8)
        mode = "dct"

    else:
        available = 0

    return {"available_bytes": available, "mode": mode}


def score_cover_image(image_path: str | Path) -> dict:
    """
    Analyse a cover image and return suitability metrics.

    Returns dict with: entropy, texture_density, adaptive_capacity,
    sequential_capacity, score (0–100), label, width, height.
    """
    img       = Image.open(Path(image_path)).convert("RGB")
    img_array = np.array(img, dtype=np.uint8)
    H, W, C   = img_array.shape

    flat          = img_array.ravel()
    value_counts  = np.bincount(flat, minlength=256).astype(np.float64)
    probabilities = value_counts / flat.size
    probabilities = probabilities[probabilities > 0]
    entropy       = float(-np.sum(probabilities * np.log2(probabilities)))
    entropy_norm  = entropy / 8.0

    pixel_mask      = _compute_embedding_map(img_array)
    texture_density = float(pixel_mask.sum()) / (H * W)

    adaptive_cap   = get_capacity(image_path, mode="adaptive")["available_bytes"]
    sequential_cap = get_capacity(image_path, mode="sequential")["available_bytes"]

    dimension_score = min(1.0, (H * W) / (1920 * 1080))
    raw_score       = (
        0.40 * entropy_norm +
        0.40 * min(1.0, texture_density / 0.5) +
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
        "entropy":             round(entropy, 2),
        "texture_density":     round(texture_density, 3),
        "adaptive_capacity":   adaptive_cap,
        "sequential_capacity": sequential_cap,
        "score":               score,
        "label":               label,
        "width":               W,
        "height":              H,
    }