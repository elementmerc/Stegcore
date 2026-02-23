# Stegcore

<img width="509" alt="Stegcore" src="https://user-images.githubusercontent.com/121883945/230636687-20e27227-23be-4a5e-9905-2122f49d1dd7.png">

A steganography tool that hides encrypted text inside images using Ascon-128 authenticated encryption and least significant bit (LSB) embedding.

![Python](https://img.shields.io/badge/Python-3.12+-blue?style=flat-square)
![License](https://img.shields.io/badge/License-AGPL--3.0-green?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=flat-square)

---

## What is Stegcore?

Stegcore is a crypto-steganography application. It combines cryptography and steganography to conceal sensitive text data inside ordinary image files. The hidden data is both encrypted and invisible to casual inspection, making it suitable for protecting IP addresses, credentials, source code, and other critical information.

Unlike conventional steganography tools that embed data without encryption, Stegcore encrypts your payload with Ascon-128 (the NIST lightweight cryptography standard) before hiding it. An attacker who extracts the embedded data still cannot read it without the correct passphrase.

---

## How it works

![Proposed Model](https://user-images.githubusercontent.com/121883945/230630515-d4cab07b-2983-4418-a7d0-2ac5b00b19e4.png)

1. Your text file is encrypted using **Ascon-128** with a passphrase you provide
2. The ciphertext is embedded into the cover image using **3-bit LSB** steganography
3. A key file is exported containing the nonce and metadata needed for extraction
4. To recover the data, you supply the stego image, the key file, and the original passphrase

The cover image appears visually identical to the original — changes to the least significant bits of pixel values are imperceptible to the human eye.

---

## Requirements

```
Python 3.12+
customtkinter
Pillow
stego-lsb
ascon
```

Install dependencies:

```bash
pip install customtkinter Pillow stego-lsb ascon
```

---

## Getting started

Clone the repository and run the main script from the `Stegcore scripts` directory:

```bash
git clone https://github.com/elementmerc/stegcore.git
cd stegcore/Stegcore\ scripts
python main.py
```

On Windows, a pre-built executable is available — download it from the [releases page](https://github.com/elementmerc/stegcore/releases) and run directly, no Python required.

---

## Usage

### Embed

Hides encrypted text inside a cover image.

1. Click **Embed**
2. Select a `.txt` file containing the text to hide
3. Select a cover image (`.png` or `.jpg`)
4. Enter a passphrase when prompted
5. Choose where to save the output stego image
6. Choose where to save the key file — **keep this safe**, it is required for extraction

### Extract

Recovers hidden text from a stego image.

1. Click **Extract**
2. Select the stego image
3. Select the key file
4. Enter the original passphrase
5. Choose where to save the recovered text file

---

## Supported formats

| Format | Embed | Extract |
|--------|-------|---------|
| PNG | ✓ | ✓ |
| JPG / JPEG | ✓ | ✓ |

---

## Image analysis tools

The `Image Tests` directory contains a standalone script for evaluating image quality and capacity metrics before embedding.

**SSIM** (Structural Similarity Index) compares structural information between the original and stego image across luminance, contrast, and structure. Target range: `0.95 – 1.00`

**PSNR** (Peak Signal-to-Noise Ratio) measures signal quality relative to noise introduced by embedding. Higher is better. Target range: `≥ 35 dB`

**Payload capacity** calculates the maximum amount of data that can be embedded in a given image without significant visual degradation.

---

## Security notes

- Ascon-128 is an authenticated encryption scheme. The integrity of the ciphertext is verified on decryption, so tampered or corrupted stego images will be rejected
- The key file does not contain your passphrase; it stores only the nonce and metadata. Losing the key file means the data cannot be recovered
- LSB steganography is detectable by dedicated steganalysis tools on carefully chosen images. Use high-entropy images with natural textures (photographs rather than flat illustrations) for best concealment

---

## Roadmap

Stegcore v2 is in active development. Planned features include steganalysis-resistant adaptive LSB, spread spectrum embedding, deniable dual payloads, additional ciphers (ChaCha20-Poly1305, AES-256-GCM), JPEG DCT embedding, WAV support, a redesigned GUI, and a full CLI for scripting and automation.

---

## License
[GNU Affero General Public License v3.0](LICENSE)