# Copyright (C) 2025 Mercury
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.

# File: core/steg.py
# Description: LSB steganography — embed and extract logic.
#              Wraps stego_lsb and provides a clean interface.
#              Structured for Phase 4 expansion to adaptive LSB and
#              spread spectrum embedding.

from pathlib import Path
from stego_lsb import LSBSteg

# LSB bits used for embedding. 3 bits per channel gives a good
# balance between capacity and visual imperceptibility.
LSB_BITS = 3


# ---------------------------------------------------------------------------
# Embed
# ---------------------------------------------------------------------------

def embed(cover_image_path: str | Path,
          payload_path: str | Path,
          output_path: str | Path) -> Path:
    """
    Embed a payload file into a cover image using LSB steganography.

    Args:
        cover_image_path: Path to the original cover image (.png or .jpg).
        payload_path:     Path to the binary payload file to hide.
        output_path:      Path where the stego image will be saved (.png).

    Returns:
        Path to the saved stego image.

    Raises:
        ValueError: If the image is too small to hold the payload.
        RuntimeError: If embedding fails for another reason.
    """
    cover_image_path = Path(cover_image_path)
    payload_path     = Path(payload_path)
    output_path      = Path(output_path)

    try:
        LSBSteg.hide_data(
            str(cover_image_path),
            str(payload_path),
            str(output_path),
            LSB_BITS,
            9,
        )
    except Exception as exc:
        error_msg = str(exc).lower()
        if "small" in error_msg or "size" in error_msg or "capacity" in error_msg:
            raise ValueError(
                "Image is too small to hold the payload. "
                "Choose a larger cover image or a shorter message."
            ) from exc
        raise RuntimeError(f"Embedding failed: {exc}") from exc

    return output_path


# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------

def extract(stego_image_path: str | Path, output_path: str | Path) -> Path:
    """
    Extract a hidden payload from a stego image.

    Args:
        stego_image_path: Path to the stego image.
        output_path:      Path where the extracted payload will be written.

    Returns:
        Path to the extracted payload file.

    Raises:
        ValueError: If no hidden data is detected in the image.
        RuntimeError: If extraction fails for another reason.
    """
    stego_image_path = Path(stego_image_path)
    output_path      = Path(output_path)

    try:
        LSBSteg.recover_data(
            str(stego_image_path),
            str(output_path),
            LSB_BITS,
        )
    except IndexError as exc:
        raise ValueError(
            "No hidden data detected in this image. "
            "Ensure you have selected the correct stego image."
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Extraction failed: {exc}") from exc

    return output_path