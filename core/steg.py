# Copyright (C) 2026 Daniel Iwugo
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: core/steg.py
# Description: Multi-format steganography. PNG/BMP via LSB, JPEG via DCT,
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
# Safe PIL → numpy loader
# ---------------------------------------------------------------------------

def _load_img_array(path: Path) -> np.ndarray:
    """
    Load an image as a writable (H, W, 3) uint8 numpy array with NO shared
    pointer to the PIL ImagingCore C struct.

    The unsafe pattern is:
        img       = Image.open(path).convert("RGB")
        img_array = np.array(img, dtype=np.uint8)   # looks like a copy

    In modern Pillow, Image.__array_interface__ returns
        {"data": (self.im.unsafe_ptrs["image32"], False), ...}
    — a raw C pointer into PIL's ImagingCore heap allocation.  When the
    source data is already contiguous uint8, numpy skips the copy and creates
    a VIEW of that allocation.  The PIL Image object and the numpy array then
    share the same malloc() block.  glibc detects the double-free and aborts
    with "munmap_chunk(): invalid pointer" at some later, apparently unrelated
    point (often during .save() or the next GC cycle).

    Safe pattern:
        1. img.tobytes() — copies all pixel data into a Python-owned bytes obj
        2. img.close() / del img — PIL's ImagingCore is freed HERE, cleanly,
           while only Python's bytes object still exists.  No more shared ptr.
        3. np.frombuffer(...).copy() — builds a writable array from the bytes.
           frombuffer alone gives a read-only view of the bytes object, so the
           .copy() makes it writable and gives numpy its own allocation.

    After this call, numpy and PIL own entirely separate heap allocations.
    """
    pil_img = Image.open(path).convert("RGB")
    w, h    = pil_img.size
    raw     = pil_img.tobytes()
    pil_img.close()           
    del pil_img
    # frombuffer → read-only view of `raw`; .copy() → writable, owned array
    return np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3).copy()


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
# PNG/BMP — bit-level read/write via unravel_index + frombytes save
#
# Two memory-safety rules are enforced throughout:
#
# 1. INDEX ARITHMETIC — np.unravel_index is used for all pixel access.
#    Earlier versions called img_array.ravel() to get a flat view, wrote
#    bits into it, then reshaped back to (H,W,C). On Linux glibc, numpy's
#    ravel() can return a view sharing the same allocation as img_array.
#    When PIL later received the reshaped array via fromarray(), two
#    independent Python objects referenced the same malloc() block. The
#    second free() triggered munmap_chunk(). unravel_index converts flat
#    indices to (row,col,channel) tuples and writes directly into the
#    original 3-D array — no second reference to the allocation ever exists.
#
# 2. PIL SAVE — Image.frombytes() is used instead of Image.fromarray().
#    fromarray() exposes numpy's raw data pointer to PIL's ImagingCore via
#    the buffer protocol. PIL's C encoder (ImagingEncoder / ImagingCopy)
#    can internally reallocate or free that pointer independently of
#    Python's reference counting. When numpy's own refcount later hits 0
#    and it calls free(), glibc detects the invalid pointer and aborts with
#    munmap_chunk(). frombytes() is given an explicit bytes object produced
#    by img_array.tobytes(), which copies the pixels into a fresh allocation
#    owned solely by PIL. numpy and PIL never share a pointer.
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
    img_array = _load_img_array(cover_path)

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

    # .tobytes() creates an explicit copy of the pixel data, severing the
    # shared-memory relationship between the numpy array and PIL's ImagingCore.
    # Image.fromarray() exposes numpy's raw pointer via the buffer protocol;
    # PIL's C encoder can then reallocate that pointer independently of Python's
    # refcount, causing glibc to detect a double-free (munmap_chunk: invalid
    # pointer) on .save(). frombytes() owns its own allocation. No shared ptr.
    h, w = img_array.shape[:2]
    Image.frombytes("RGB", (w, h), img_array.tobytes()).save(
        str(output_path), format="PNG"
    )


def _extract_png(stego_path: Path, key: bytes, mode: str) -> bytes:
    img_array = _load_img_array(stego_path)

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

def _jpeg_usable_positions(component: np.ndarray) -> np.ndarray:
    mask = (component != 0) & (component != 1) & (component != -1) & (component != -2)
    return np.argwhere(mask)   # shape (N, 2), dtype int64


def _embed_jpeg(cover_path: Path, payload: bytes, output_path: Path) -> None:
    if not _JPEGIO_AVAILABLE:
        raise RuntimeError("jpegio is not installed. Run: pip install jpegio")

    jpeg     = jpegio.read(str(cover_path))
    all_bits = np.concatenate([
        _int_to_bits(len(payload), _HEADER_BITS),
        _bytes_to_bits(payload),
    ])
    n_bits   = len(all_bits)
    bit_idx  = 0

    # Capacity check using the same position-selection logic as the write loop.
    capacity = sum(len(_jpeg_usable_positions(c)) for c in jpeg.coef_arrays)
    if n_bits > capacity:
        raise ValueError(
            f"JPEG has insufficient DCT capacity.\n"
            f"Available: ~{capacity // 8:,} bytes | Required: ~{len(payload):,} bytes.\n"
            "Try a larger or higher-quality JPEG."
        )

    # Write loop — direct 2D indexing, never ravel().
    #
    # The root-cause of the previous silent round-trip failure:
    # jpegio stores DCT coefficient arrays in Fortran (column-major) order.
    # numpy's ravel() on a Fortran-order array returns a copy, not a view.
    # Every write to that copy was silently discarded; jpegio.write then saved
    # the original unmodified coefficients.  On extract, the header read back
    # as garbage and the length check failed.
    #
    # Direct indexing — comp[r, c] = x — always writes into the live array
    # regardless of its memory layout, because it goes through numpy's item
    # setter which resolves the actual address from strides + offsets.
    for component in jpeg.coef_arrays:
        if bit_idx >= n_bits:
            break
        positions = _jpeg_usable_positions(component)
        for r, c in positions:
            if bit_idx >= n_bits:
                break
            coef = int(component[r, c])
            component[r, c] = np.int16((coef & ~1) | int(all_bits[bit_idx]))
            bit_idx += 1

    jpegio.write(jpeg, str(output_path))


def _extract_jpeg(stego_path: Path) -> bytes:
    if not _JPEGIO_AVAILABLE:
        raise RuntimeError("jpegio is not installed. Run: pip install jpegio")

    jpeg = jpegio.read(str(stego_path))
    bits = []

    for component in jpeg.coef_arrays:
        for r, c in _jpeg_usable_positions(component):
            bits.append(int(component[r, c]) & 1)

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
    Returns copies — not views — so each half owns its memory.
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

    img_array  = _load_img_array(cover_path)
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

    # Both write passes on the same img_array. unravel_index is safe.
    _write_bits_img(img_array, real_indices,  real_bits)
    _write_bits_img(img_array, decoy_indices, decoy_bits)

    h, w = img_array.shape[:2]
    Image.frombytes("RGB", (w, h), img_array.tobytes()).save(
        str(output_path), format="PNG"
    )
    return output_path


def extract_deniable(stego_path:     str | Path,
                     key:            bytes,
                     partition_seed: bytes,
                     partition_half: int) -> bytes:
    stego_path = Path(stego_path)
    img_array  = _load_img_array(stego_path)
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
            # JPEG DCT embedding rewrites the DCT coefficient tables.
            # The output file MUST be saved as JPEG to preserve those
            # tables. Saving as PNG would discard them entirely, making
            # extraction impossible. Catching the mistake early.
            if output_path.suffix.lower() not in {".jpg", ".jpeg"}:
                raise ValueError(
                    f"JPEG cover requires a JPEG output file.\n"
                    f"Output path '{output_path.name}' has extension "
                    f"'{output_path.suffix}' — change it to '.jpg'."
                )
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
        img_array = _load_img_array(path)
        if mode == "adaptive":
            n_indices = int(_compute_embedding_map(img_array).sum()) * 3
        else:
            n_indices = img_array.size
        available = max(0, (n_indices - _HEADER_BITS) // 8)

    elif fmt == "jpeg":
        if not _JPEGIO_AVAILABLE:
            return {"available_bytes": 0, "mode": "dct"}
        jpeg      = jpegio.read(str(path))
        capacity  = sum(len(_jpeg_usable_positions(c)) for c in jpeg.coef_arrays)
        available = max(0, (capacity - _HEADER_BITS) // 8)
        mode = "dct"

    else:
        available = 0

    return {"available_bytes": available, "mode": mode}


def score_cover_image(image_path: str | Path) -> dict:
    img_array = _load_img_array(Path(image_path))
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