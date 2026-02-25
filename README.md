# Stegcore v2

**Crypto-steganography toolkit. Hide encrypted messages inside ordinary files.**

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)
![License](https://img.shields.io/badge/Licence-AGPL--3.0-green?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=flat-square)
![Version](https://img.shields.io/badge/Version-2.0.0-orange?style=flat-square)

---

## What is Stegcore?

Stegcore combines **cryptography** and **steganography**. It encrypts your payload and hides the ciphertext inside an ordinary image or audio file. The result looks and sounds completely normal. Only someone with the correct passphrase and key file can recover what's inside.

Unlike basic steganography tools that hide data without encrypting it, Stegcore ensures the payload is unreadable even if someone extracts it. Unlike basic encryption tools, Stegcore ensures the payload isn't even visible.

---

## Key features

**Three ciphers**: Ascon-128 (NIST lightweight standard), ChaCha20-Poly1305, and AES-256-GCM. All use Argon2id key derivation.

**Adaptive LSB steganography**: Payload bits are scattered across high-entropy, high-texture regions of the cover image using spread spectrum techniques, making detection significantly harder than standard LSB.

**Deniable dual payload**: Embed two separately encrypted payloads into one cover image. One passphrase reveals the real message; another reveals a plausible decoy. Neither key file identifies itself.

**Multiple formats**: PNG and BMP via adaptive or sequential LSB, JPEG via DCT-domain embedding, WAV via audio sample LSB.

**Cover image scoring**: Before embedding, Stegcore scores the cover on entropy, texture density, and resolution. Poor covers are flagged before you commit.

**Zstandard compression**: Payloads are compressed before encryption, improving both capacity efficiency and entropy uniformity.

**Desktop GUI**: A step-by-step interface with dark and light modes.

**Full CLI with two modes:**
- **Wizard mode**: Guided step-by-step prompts, ideal if you're new to the terminal. Run `stegcore wizard`.
- **Power mode**: Single-line commands with flags for scripting and experienced users.

---

## Installation

**From source:**
```bash
git clone https://github.com/elementmerc/stegcore.git
cd stegcore
pip install -e .
```

**Dependencies only:**
```bash
pip install customtkinter Pillow numpy ascon cryptography argon2-cffi pyzstd jpegio typer rich
```

**Pre-built binaries** are available on the [releases page](https://github.com/elementmerc/stegcore/releases) for Windows, Linux, and macOS. No Python required.

---

## Quick start

**New to the terminal? Use the wizard:**
```bash
stegcore wizard
```
The wizard walks you through everything step by step from cover selection, scoring, cipher choice, passphrase, and embedding. No flags needed.

**GUI:**
```bash
python main.py
# or after pip install:
stegcore-gui
```

**Power-user CLI:**
```bash
# Score a cover image
stegcore score photo.png

# Embed
stegcore embed photo.png secret.txt stego.png

# Extract
stegcore extract stego.png stego.key.json recovered.txt

# Inspect a key file
stegcore info stego.key.json

# List ciphers
stegcore ciphers

# Full help
stegcore --help
stegcore embed --help
```

See [USAGE.md](USAGE.md) for the complete CLI reference.

---

## How it works

```
secret.txt
    │
    ▼
[ Argon2id key derivation (passphrase + random salt) ]
    │
    ▼
[ Encrypt: Ascon-128 / ChaCha20-Poly1305 / AES-256-GCM ]
    │
    ▼
[ Zstandard compress ciphertext ]
    │
    ▼
[ Score cover image — entropy, texture, capacity ]
    │
    ▼
[ Adaptive LSB / DCT / WAV sample embedding ]
    │
    ▼
stego.png  +  stego.key.json
```

The key file contains only the nonce, salt, cipher name, and steg metadata. **Never** change the passphrase or derived key. Without both the key file **and** the correct passphrase, extraction isn't possible.

---

## Supported formats

| Format | Algorithm | Notes |
|--------|-----------|-------|
| PNG | Adaptive LSB + spread spectrum | Best capacity and concealment |
| BMP | Adaptive LSB + spread spectrum | Lossless, same as PNG |
| JPEG | DCT-domain coefficient embedding | Survives JPEG recompression |
| WAV | Audio sample LSB | PCM audio only |

---

## Deniable mode

Two payloads, one cover file. Two key files produced that are structurally identical, neither self-identifying as real or fake.

```bash
stegcore embed cover.png real_message.txt stego.png --deniable
# Wizard mode will ask you about this interactively.
```

Under coercion you hand over the decoy key file and decoy passphrase. The real message remains inaccessible and undetectable.

---

## Project structure

```
stegcore/
├── main.py              # GUI entry point
├── cli.py               # CLI entry point (wizard + power commands)
├── pyproject.toml
├── core/
│   ├── crypto.py        # Encryption, key derivation, key file I/O
│   ├── steg.py          # Steganographic embed/extract, cover scoring
│   └── utils.py         # Shared helpers
├── ui/
│   ├── theme.py         # Theme definitions and switcher
│   ├── app.py           # Main window and navigation
│   ├── embed_flow.py    # 4-step embed wizard
│   └── extract_flow.py  # 3-step extract wizard
└── assets/
    └── Stag.ico
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for a full technical breakdown.

---

## Security

Stegcore is a defensive privacy tool. See [SECURITY.md](SECURITY.md) for the full threat model, honest limitations, and responsible use guidance.

---

## Pro version

Stegcore Pro is a work in progress, and extends the free version with:

- **Built-in steganalysis self-test**
- **PDF and DOCX cover format support**
- **Batch processing and scripting API**

---

## Licence

[GNU Affero General Public Licence v3.0](LICENSE)

Free to use, study, modify, and distribute under the terms of the AGPL-3.0. If you deploy a modified version as a network service, you must make the modified source available.