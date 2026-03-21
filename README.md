# Stegcore

**Crypto-steganography toolkit. Hide encrypted messages inside ordinary files.**

![Rust](https://img.shields.io/badge/Rust-2021-orange?style=flat-square)
![Tauri](https://img.shields.io/badge/Tauri-v2-blue?style=flat-square)
![Licence](https://img.shields.io/badge/Licence-AGPL--3.0-green?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=flat-square)

---

## What is Stegcore?

Stegcore combines **encryption** and **steganography** into a single
cross-platform toolkit. It encrypts your payload and hides the
ciphertext inside an ordinary image or audio file. The result looks and
sounds completely normal. Only someone with the correct passphrase can
recover what's inside.

Unlike basic steganography tools that hide data without encrypting it,
Stegcore ensures the payload is unreadable even if someone extracts it.
Unlike basic encryption tools, Stegcore ensures the payload isn't even
visible.

---

## Key features

- **Three authenticated ciphers** — Ascon-128 (NIST lightweight
  standard), ChaCha20-Poly1305, AES-256-GCM. All use Argon2id key
  derivation.
- **Adaptive LSB steganography** — Payload bits are scattered across
  high-entropy regions using texture-aware embedding, significantly
  harder to detect than standard LSB.
- **Deniable dual payload** — Embed two separately encrypted messages
  in one cover file. Two passphrases, two messages. Neither key file
  identifies which is real.
- **Built-in steganalysis suite** — Chi-squared, Sample Pair Analysis,
  RS Analysis, LSB Entropy, and tool fingerprinting. Detects Steghide,
  OpenStego, OutGuess, and generic LSB.
- **Multiple formats** — PNG, BMP, JPEG (JSteg DCT), WebP, WAV for
  embedding. FLAC for analysis and extraction.
- **Cover scoring** — Scores your cover file before embedding. Poor
  covers are flagged before you commit.
- **Progressive analysis** — Preliminary results in under a second,
  full accuracy analysis runs in the background.
- **Desktop GUI** — Step-by-step wizards for embed, extract, and
  analyse. Dark and light themes. Interface size scaling.
- **Full CLI** — Wizard mode for beginners, power-user flags for
  scripting. JSON output on all commands.

---

## Installation

### Pre-built binaries (recommended)

Download from the [releases page](https://github.com/elementmerc/Stegcore/releases).
Available for Windows, Linux, and macOS. No runtime required.

Pre-built binaries include the full steganographic engine. This is the
recommended way to install Stegcore.

### Building from source

The public repository compiles without the proprietary engine, but
steganographic operations will be unavailable (the binary returns a
message directing you to download a pre-built release). This is intentional 🙃,
and by design. See [Architecture](#architecture) for details.

If you want to build the UI shell or contribute to the public codebase:

```bash
git clone https://github.com/elementmerc/Stegcore.git
cd Stegcore
cd frontend && npm install && cd ..
cargo build --release --no-default-features
```

**Linux dependencies:**
```bash
sudo apt install libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev
```

---

## Quick start

**GUI:**
```bash
stegcore          # launches the desktop application
```

**CLI wizard (guided):**
```bash
stegcore-cli wizard
```

**CLI power mode:**
```bash
# Score a cover
stegcore-cli score cover.png

# Embed
stegcore-cli embed cover.png secret.txt -o stego.png

# Extract
stegcore-cli extract stego.png -o recovered.txt

# Analyse for hidden content
stegcore-cli analyse suspect.png

# Batch analyse
stegcore-cli analyse *.png --json

# List ciphers
stegcore-cli ciphers
```

See [USAGE.md](USAGE.md) for the complete CLI reference.

---

## How it works

```
secret.txt
    |
    v
[ Argon2id key derivation (passphrase + random salt) ]
    |
    v
[ Zstandard compression ]
    |
    v
[ Encrypt: Ascon-128 / ChaCha20-Poly1305 / AES-256-GCM ]
    |
    v
[ Score cover — entropy, texture, capacity ]
    |
    v
[ Adaptive LSB / DCT / WAV sample embedding ]
    |
    v
stego.png  (+ optional key file)
```

Extraction requires the stego file and passphrase. No key file needed
by default — metadata is embedded in the payload. The key file is an
optional export for out-of-band sharing or backup.

---

## Supported formats

| Format | Embed | Extract | Analyse | Notes |
|--------|-------|---------|---------|-------|
| PNG    | Yes   | Yes     | Yes     | Best capacity and concealment |
| BMP    | Yes   | Yes     | Yes     | Lossless, same as PNG |
| JPEG   | Yes   | Yes     | Yes     | JSteg DCT coefficient LSB |
| WebP   | Yes   | Yes     | Yes     | Lossless WebP |
| WAV    | Yes   | Yes     | Yes     | PCM audio sample LSB |
| FLAC   | No    | Yes     | Yes     | Decode-only (no mature Rust encoder) |

---

## Steganalysis

Stegcore includes a built-in detection suite:

- **Chi-Squared** — Tests LSB pair-of-values distribution uniformity
- **Sample Pair Analysis (SPA)** — Measures adjacent pixel correlation
- **RS Analysis** — Detects Regular/Singular group asymmetry
- **LSB Entropy** — Measures randomness of the least significant bits
- **Tool Fingerprinting** — Identifies Steghide, OpenStego, OutGuess signatures

Ensemble verdict: Clean / Suspicious / Likely Stego.

Interactive scatter plots and entropy heatmaps in the GUI detail view.
Export as PDF, HTML, JSON, or CSV.

---

## Comparison

| Feature | Stegcore | Steghide | OpenStego |
|---|---|---|---|
| Licence | AGPL-3.0 | GPL | GPL |
| Platform | Windows, Linux, macOS | Linux, Windows | Java (cross-platform) |
| Encryption | 3 AEAD ciphers + Argon2id | Rijndael + MD5 | AES-128 |
| Deniable mode | Yes | No | No |
| Built-in steganalysis | Yes | No | No |
| Cover scoring | Yes | No | No |
| GUI + CLI | Yes | CLI only | GUI only |
| Active development | Yes (2026) | No (2003) | No (2016) |

---

## Architecture

Stegcore is a multi-crate Rust workspace:

```
Cargo.toml                    — workspace root
crates/core/                  — public library: errors, crypto wrappers, FFI
crates/cli/                   — CLI binary (clap v4)
src-tauri/                    — Tauri v2 desktop app
frontend/                     — React + TypeScript + Vite
libstegcore/                  — private engine (proprietary, not published)
```

The steganographic engine (`libstegcore`) is a separate private
repository linked as a Rust crate dependency. Public builds without the
engine compile cleanly and return user-friendly error messages.

---

## Security

Stegcore is a defensive privacy tool for journalists, activists,
security researchers, and CTF players. See [SECURITY.md](SECURITY.md)
for the threat model and responsible use guidance.

---

## Licence

[GNU Affero General Public Licence v3.0](LICENSE)

Free to use, modify, and distribute. If you deploy a modified version
as a network service, you must make the modified source available.
Commercial licensing available for organisations that cannot comply with
AGPL terms.
