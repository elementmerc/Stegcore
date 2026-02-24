# Copyright (C) 2026 Daniel Iwugo
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: core/steg.py
# Description: Multi-format steganography — PNG/BMP via LSB, JPEG via DCT,
#              WAV via sample LSB. Format is detected automatically from the
#              file extension and routed to the correct algorithm.
#
#   PNG/BMP  — Adaptive or sequential LSB (lossless, LSB survives)
#   JPEG     — DCT-domain embedding (survives JPEG recompression)
#   WAV      — Audio sample LSB

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

SUPPORTED_MODES     = ["adaptive", "sequential"]
_VARIANCE_THRESHOLD = 10.0
_HEADER_BITS        = 32          # 32-bit payload length prefix


# ---------------------------------------------------------------------------
# Format routing
# ---------------------------------------------------------------------------

def _get_format(path: Path) -> str:
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
# Bit helpers
# ---------------------------------------------------------------------------

def _bytes_to_bits(data: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def _bits_to_bytes(bits: np.ndarray) -> bytes:
    rem = len(bits) % 8
    if rem:
        bits = np.concatenate([bits, np.zeros(8 - rem, dtype=np.uint8)])
    return np.packbits(bits).tobytes()


def _int_to_bits(value: int, n: int) -> np.ndarray:
    bits = np.zeros(n, dtype=np.uint8)
    for i in range(n):
        bits[n - 1 - i] = (value >> i) & 1
    return bits


def _bits_to_int(bits: np.ndarray) -> int:
    v = 0
    for b in bits:
        v = (v << 1) | int(b)
    return v


# ---------------------------------------------------------------------------
# PNG/BMP — bit-level read/write via unravel_index
#
# Using np.unravel_index keeps img_array as a proper (H,W,C) array
# throughout. PIL always receives the original, never a reshaped copy.
# This eliminates the ravel/reshape double-buffer that was causing
# munmap_chunk() crashes on Linux.
# ---------------------------------------------------------------------------

def _write_bits_img(img_array: np.ndarray,
                    flat_indices: np.ndarray,
                    bits: np.ndarray) -> None:
    """Write bits into img_array LSBs using 3-D indexing (in-place)."""
    n = len(bits)
    rs, cs, chs = np.unravel_index(flat_indices[:n], img_array.shape)
    img_array[rs, cs, chs] = (
        (img_array[rs, cs, chs] & np.uint8(0xFE)) | bits[:n].astype(np.uint8)
    )


def _read_bits_img(img_array: np.ndarray,
                   flat_indices: np.ndarray,
                   n: int) -> np.ndarray:
    """Read n bits from img_array LSBs using 3-D indexing."""
    rs, cs, chs = np.unravel_index(flat_indices[:n], img_array.shape)
    return (img_array[rs, cs, chs] & np.uint8(1)).astype(np.uint8)


# ---------------------------------------------------------------------------
# Embedding map (adaptive mode)
# ---------------------------------------------------------------------------

def _compute_embedding_map(img_array: np.ndarray,
                            threshold: float = _VARIANCE_THRESHOLD) -> np.ndarray:
    """
    Boolean (H,W) mask of pixels suitable for embedding.
    LSBs are zeroed first so the map is identical on both the original
    and the stego image, guaranteeing round-trip index consistency.
    """
    baseline  = (img_array & np.uint8(0xFE)).astype(np.float32)
    gray      = baseline.mean(axis=2)
    padded    = np.pad(gray, 1, mode="reflect")
    windows   = sliding_window_view(padded, (3, 3))
    local_var = windows.reshape(*windows.shape[:2], -1).var(axis=2)
    return local_var > threshold


# ---------------------------------------------------------------------------
# Index generation
# ---------------------------------------------------------------------------

def _get_indices_adaptive(img_array: np.ndarray,
                           pixel_mask: np.ndarray,
                           key: bytes) -> np.ndarray:
    """Shuffled flat indices of eligible channels, seeded from key."""
    C            = img_array.shape[2]
    channel_mask = np.stack([pixel_mask] * C, axis=2)
    flat_indices = np.where(channel_mask.ravel())[0].copy()
    seed         = int.from_bytes(key[:8], "big")
    np.random.default_rng(seed).shuffle(flat_indices)
    return flat_indices


def _get_indices_sequential(img_array: np.ndarray) -> np.ndarray:
    return np.arange(img_array.size, dtype=np.int64)


# ---------------------------------------------------------------------------
# PNG/BMP embed / extract
# ---------------------------------------------------------------------------

def _embed_png(cover_path: Path, payload: bytes, output_path: Path,
               key: bytes, mode: str) -> None:
    img       = Image.open(cover_path).convert("RGB")
    img_array = np.array(img, dtype=np.uint8)   # owned copy

    indices = (
        _get_indices_adaptive(img_array, _compute_embedding_map(img_array), key)
        if mode == "adaptive" else
        _get_indices_sequential(img_array)
    )

    all_bits = np.concatenate([
        _int_to_bits(len(payload), _HEADER_BITS),
        _bytes_to_bits(payload),
    ])

    if len(all_bits) > len(indices):
        avail = (len(indices) - _HEADER_BITS) // 8
        raise ValueError(
            f"Insufficient image capacity.\n"
            f"Available: ~{avail:,} bytes | Required: ~{len(payload):,} bytes.\n"
            + ("Try a larger or more textured cover image, or use sequential mode."
               if mode == "adaptive" else "Try a larger cover image.")
        )

    _write_bits_img(img_array, indices, all_bits)
    Image.fromarray(img_array).save(str(output_path), format="PNG")


def _extract_png(stego_path: Path, key: bytes, mode: str) -> bytes:
    img       = Image.open(stego_path).convert("RGB")
    img_array = np.array(img, dtype=np.uint8)

    indices = (
        _get_indices_adaptive(img_array, _compute_embedding_map(img_array), key)
        if mode == "adaptive" else
        _get_indices_sequential(img_array)
    )

    header_bits = _read_bits_img(img_array, indices, _HEADER_BITS)
    payload_len = _bits_to_int(header_bits)
    max_pos     = (len(indices) - _HEADER_BITS) // 8

    if payload_len == 0 or payload_len > max_pos:
        raise ValueError(
            "No valid payload detected.\n"
            "Check you are using the correct stego image and key file."
        )

    payload_bits = _read_bits_img(img_array, indices[_HEADER_BITS:], payload_len * 8)
    return _bits_to_bytes(payload_bits)[:payload_len]


# ---------------------------------------------------------------------------
# JPEG — DCT-domain embedding
# ---------------------------------------------------------------------------

def _embed_jpeg(cover_path: Path, payload: bytes, output_path: Path) -> None:
    if not _JPEGIO_AVAILABLE:
        raise RuntimeError("jpegio is not installed. Run: pip install jpegio")

    jpeg     = jpegio.read(str(cover_path))
    all_bits = np.concatenate([
        _int_to_bits(len(payload), _HEADER_BITS),
        _bytes_to_bits(payload),
    ])
    bit_idx  = 0
    capacity = sum(
        int(np.sum((c.ravel() != 0) & (c.ravel() != 1) & (c.ravel() != -1)))
        for c in jpeg.coef_arrays
    )

    if len(all_bits) > capacity:
        raise ValueError(
            f"JPEG has insufficient DCT capacity.\n"
            f"Available: ~{capacity // 8:,} bytes | Required: ~{len(payload):,} bytes.\n"
            "Try a larger or higher-quality JPEG."
        )

    for component in jpeg.coef_arrays:
        if bit_idx >= len(all_bits):
            break
        flat = component.ravel()
        for i in range(len(flat)):
            if bit_idx >= len(all_bits):
                break
            coef = flat[i]
            if coef != 0 and coef != 1 and coef != -1:
                flat[i] = (coef & ~1) | int(all_bits[bit_idx])
                bit_idx += 1

    jpegio.write(jpeg, str(output_path))


def _extract_jpeg(stego_path: Path) -> bytes:
    if not _JPEGIO_AVAILABLE:
        raise RuntimeError("jpegio is not installed. Run: pip install jpegio")

    jpeg = jpegio.read(str(stego_path))
    bits = []
    for component in jpeg.coef_arrays:
        for coef in component.ravel():
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

    return _bits_to_bytes(bits_arr[_HEADER_BITS: _HEADER_BITS + payload_len * 8])[:payload_len]


# ---------------------------------------------------------------------------
# WAV — sample LSB
# ---------------------------------------------------------------------------

def _embed_wav(cover_path: Path, payload: bytes, output_path: Path) -> None:
    with wave.open(str(cover_path), "rb") as wf:
        params   = wf.getparams()
        raw      = wf.readframes(wf.getnframes())

    samples  = np.frombuffer(raw, dtype=np.uint8).copy()
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

    n = len(all_bits)
    samples[:n] = (samples[:n] & np.uint8(0xFE)) | all_bits.astype(np.uint8)

    with wave.open(str(output_path), "wb") as wf:
        wf.setparams(params)
        wf.writeframes(samples.tobytes())


def _extract_wav(stego_path: Path) -> bytes:
    with wave.open(str(stego_path), "rb") as wf:
        raw = wf.readframes(wf.getnframes())

    samples     = np.frombuffer(raw, dtype=np.uint8)
    header_bits = (samples[:_HEADER_BITS] & np.uint8(1)).astype(np.uint8)
    payload_len = _bits_to_int(header_bits)
    max_pos     = (len(samples) - _HEADER_BITS) // 8

    if payload_len == 0 or payload_len > max_pos:
        raise ValueError(
            "No valid payload detected in this WAV file.\n"
            "Check you are using the correct stego file and key file."
        )

    payload_bits = (
        samples[_HEADER_BITS: _HEADER_BITS + payload_len * 8] & np.uint8(1)
    ).astype(np.uint8)
    return _bits_to_bytes(payload_bits)[:payload_len]


# ---------------------------------------------------------------------------
# Deniable dual payload
# ---------------------------------------------------------------------------

def split_indices(all_indices: np.ndarray,
                  partition_seed: bytes) -> tuple[np.ndarray, np.ndarray]:
    """
    Deterministically split indices into two disjoint halves.
    Returns copies so each half owns its memory.
    """
    rng      = np.random.default_rng(int.from_bytes(partition_seed, "big"))
    shuffled = all_indices.copy()
    rng.shuffle(shuffled)
    mid = len(shuffled) // 2
    return shuffled[:mid].copy(), shuffled[mid:].copy()


def _get_deniable_indices(img_array: np.ndarray,
                           pixel_mask: np.ndarray,
                           key: bytes,
                           partition_seed: bytes,
                           partition_half: int) -> np.ndarray:
    C            = img_array.shape[2]
    channel_mask = np.stack([pixel_mask] * C, axis=2)
    flat_indices = np.where(channel_mask.ravel())[0].copy()
    half_0, half_1 = split_indices(flat_indices, partition_seed)
    half = (half_0 if partition_half == 0 else half_1).copy()
    np.random.default_rng(int.from_bytes(key[:8], "big")).shuffle(half)
    return half


def embed_deniable(cover_path:    str | Path,
                   real_payload:  bytes,
                   decoy_payload: bytes,
                   output_path:   str | Path,
                   real_key:      bytes,
                   decoy_key:     bytes,
                   partition_seed: bytes) -> Path:
    cover_path  = Path(cover_path)
    output_path = Path(output_path)

    img        = Image.open(cover_path).convert("RGB")
    img_array  = np.array(img, dtype=np.uint8)
    pixel_mask = _compute_embedding_map(img_array)

    real_indices  = _get_deniable_indices(img_array, pixel_mask, real_key,  partition_seed, 0)
    decoy_indices = _get_deniable_indices(img_array, pixel_mask, decoy_key, partition_seed, 1)

    def _make_bits(payload, indices, label):
        bits = np.concatenate([
            _int_to_bits(len(payload), _HEADER_BITS),
            _bytes_to_bits(payload),
        ])
        if len(bits) > len(indices):
            avail = (len(indices) - _HEADER_BITS) // 8
            raise ValueError(
                f"Insufficient capacity for {label} payload."
                f"Available per half: ~{avail:,} bytes | "
                f"Required: ~{len(payload):,} bytes."
                "Try a larger or more textured cover image, or shorter messages."
            )
        return bits

    real_bits  = _make_bits(real_payload,  real_indices,  "real")
    decoy_bits = _make_bits(decoy_payload, decoy_indices, "decoy")

    # Both write passes on the same img_array — unravel_index is safe
    _write_bits_img(img_array, real_indices,  real_bits)
    _write_bits_img(img_array, decoy_indices, decoy_bits)

    Image.fromarray(img_array).save(str(output_path), format="PNG")
    return output_path


def extract_deniable(stego_path:     str | Path,
                     key:            bytes,
                     partition_seed: bytes,
                     partition_half: int) -> bytes:
    stego_path = Path(stego_path)
    img        = Image.open(stego_path).convert("RGB")
    img_array  = np.array(img, dtype=np.uint8)
    pixel_mask = _compute_embedding_map(img_array)
    indices    = _get_deniable_indices(img_array, pixel_mask, key,
                                       partition_seed, partition_half)

    header_bits = _read_bits_img(img_array, indices, _HEADER_BITS)
    payload_len = _bits_to_int(header_bits)
    max_pos     = (len(indices) - _HEADER_BITS) // 8

    if payload_len == 0 or payload_len > max_pos:
        raise ValueError(
            "No valid payload detected."
            "Check you are using the correct stego image and key file."
        )

    payload_bits = _read_bits_img(img_array, indices[_HEADER_BITS:], payload_len * 8)
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
    Embed payload_path into cover_path. Format auto-detected from extension.
    PNG/BMP → adaptive or sequential LSB.
    JPEG    → DCT-domain.
    WAV     → sample LSB.
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
    """Extract payload from stego_path. Format auto-detected from extension."""
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
    path = Path(image_path)
    fmt  = _get_format(path)

    if fmt == "png":
        img_array = np.array(Image.open(path).convert("RGB"), dtype=np.uint8)
        if mode == "adaptive":
            n_indices = int(_compute_embedding_map(img_array).sum()) * 3
        else:
            n_indices = img_array.size
        available = max(0, (n_indices - _HEADER_BITS) // 8)

    elif fmt == "jpeg":
        if not _JPEGIO_AVAILABLE:
            return {"available_bytes": 0, "mode": "dct"}
        jpeg      = jpegio.read(str(path))
        capacity  = sum(
            int(np.sum((c.ravel() != 0) & (c.ravel() != 1) & (c.ravel() != -1)))
            for c in jpeg.coef_arrays
        )
        available = max(0, (capacity - _HEADER_BITS) // 8)
        mode = "dct"

    else:
        available = 0

    return {"available_bytes": available, "mode": mode}


def score_cover_image(image_path: str | Path) -> dict:
    img_array = np.array(Image.open(Path(image_path)).convert("RGB"), dtype=np.uint8)
    H, W, C   = img_array.shape

    flat          = img_array.ravel()
    counts        = np.bincount(flat, minlength=256).astype(np.float64)
    probs         = counts / flat.size
    probs         = probs[probs > 0]
    entropy       = float(-np.sum(probs * np.log2(probs)))
    entropy_norm  = entropy / 8.0

    pixel_mask      = _compute_embedding_map(img_array)
    texture_density = float(pixel_mask.sum()) / (H * W)

    adaptive_cap   = get_capacity(image_path, mode="adaptive")["available_bytes"]
    sequential_cap = get_capacity(image_path, mode="sequential")["available_bytes"]

    raw_score = (
        0.40 * entropy_norm +
        0.40 * min(1.0, texture_density / 0.5) +
        0.20 * min(1.0, (H * W) / (1920 * 1080))
    )
    score = int(round(raw_score * 100))

    return {
        "entropy":             round(entropy, 2),
        "texture_density":     round(texture_density, 3),
        "adaptive_capacity":   adaptive_cap,
        "sequential_capacity": sequential_cap,
        "score":               score,
        "label":               (
            "Excellent" if score >= 75 else
            "Good"      if score >= 55 else
            "Fair"      if score >= 35 else "Poor"
        ),
        "width":  W,
        "height": H,
    }