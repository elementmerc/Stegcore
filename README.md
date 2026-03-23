<div align="center">

<img src="icon.svg" alt="Stegcore logo" width="96" height="96">

# Stegcore

**Hide encrypted messages inside ordinary files**

[![CI](https://github.com/elementmerc/Stegcore/actions/workflows/ci.yml/badge.svg)](https://github.com/elementmerc/Stegcore/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/elementmerc/Stegcore)](https://github.com/elementmerc/Stegcore/releases/latest)
[![License: AGPL-3.0](https://img.shields.io/badge/licence-AGPL--3.0-blue)](LICENSE)

<img src="docs/demo.gif" alt="Stegcore GUI demo" width="720">

</div>

---

Stegcore encrypts your payload and hides it inside an image or audio file. The result looks and sounds completely normal. Only the correct passphrase recovers what's inside. Three authenticated ciphers (Ascon-128, ChaCha20-Poly1305, AES-256-GCM), adaptive LSB steganography, deniable dual-payload mode, and a full steganalysis detection suite. Desktop GUI and CLI. Completely offline — no network connections, no telemetry, no account.

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/elementmerc/Stegcore/main/install.sh | sh
```

### Platform grid

| Platform | CLI | GUI |
|---|---|---|
| **Linux x86_64** | `.tar.gz` | `.AppImage` / `.deb` |
| **macOS (Intel + Apple Silicon)** | Universal binary | `.dmg` |
| **Windows x86_64** | `.zip` | `.msi` |

### Package managers

```bash
# Homebrew (macOS / Linux)
brew install elementmerc/tap/stegcore

# Winget (Windows)
winget install elementmerc.Stegcore
```

### Building from source

Building from source is **not supported** for public users. Stegcore relies
on a private engine that is not included in this repository. Use the
install script or pre-built releases above.

The public repository compiles cleanly without the engine — steganographic
operations return a message directing you to download a release build.

---

## CLI usage

```bash
# Guided wizard (recommended for new users)
stegcore wizard

# Embed
stegcore embed cover.png secret.txt -o stego.png

# Extract
stegcore extract stego.png -o recovered.txt

# Analyse for hidden content
stegcore analyse suspect.png

# Batch analyse with progress
stegcore analyse *.png --json

# Pipe support
echo "secret" | stegcore embed cover.png - -o stego.png
stegcore extract stego.png --raw | xxd
```

### Additional commands

```bash
# Score a cover file's suitability
stegcore score cover.png

# Compare original vs stego (pixel diff)
stegcore diff cover.png stego.png

# Read embedded metadata (requires passphrase)
stegcore info stego.png

# List available ciphers
stegcore ciphers

# System health check
stegcore doctor

# Benchmark cipher throughput
stegcore benchmark

# Generate shell completions
stegcore completions bash > ~/.local/share/bash-completion/completions/stegcore

# Bible verse
stegcore verse
```

Full flag reference: `stegcore --help`

---

## GUI

Launch Stegcore, then follow the step-by-step wizards for embedding,
extracting, or analysing files. Drag and drop works everywhere.

| Feature | What it does |
|---|---|
| Embed wizard | 4-step guided flow: message → cover → options → confirm |
| Extract wizard | 3-step flow: stego file → passphrase → recovered payload |
| Steganalysis dashboard | Animated charts: Chi-Squared, RS Analysis, SPA gauge, LSB heatmap |
| Audio analysis | Oscilloscope trace with suspicious region highlighting |
| Pixel diff | Before/after comparison on embed success |
| Export | Copy dashboard to clipboard, export as PDF/HTML/JSON/CSV |

**Keyboard shortcuts** — E (embed), X (extract), A (analyse), L (learn), R (reload), ? (shortcuts overlay).

**First-run wizard** walks new users through the acceptable use policy,
licence, and preferences (theme, default cipher).

**Settings** — theme (dark/light), interface size (small/default/large/xl),
default cipher, embedding mode, auto-score, clipboard auto-clear, reduce
motion.

Analysis history stays local. Nothing leaves your device.

---

## Supported formats

| Format | Embed | Extract | Analyse | Notes |
|---|---|---|---|---|
| PNG | ✓ | ✓ | ✓ | Best capacity and concealment |
| BMP | ✓ | ✓ | ✓ | Lossless |
| JPEG | ✓ | ✓ | ✓ | JSteg DCT coefficient LSB |
| WebP | ✓ | ✓ | ✓ | Lossless WebP |
| WAV | ✓ | ✓ | ✓ | PCM audio sample LSB |
| FLAC | — | ✓ | ✓ | Decode-only |

---

## Why Stegcore?

| | Stegcore | Steghide | OpenStego | OpenPuff |
|---|---|---|---|---|
| Offline | ✓ | ✓ | ✓ | ✓ |
| Modern encryption | 3 AEAD + Argon2id | Rijndael + MD5 | AES-128 | AES-256 |
| Deniable mode | ✓ | ✗ | ✗ | ✓ |
| Built-in steganalysis | ✓ | ✗ | ✗ | ✗ |
| Cover scoring | ✓ | ✗ | ✗ | ✗ |
| Pixel diff | ✓ | ✗ | ✗ | ✗ |
| GUI + CLI | ✓ | CLI only | GUI only | GUI only |
| Pipe support | ✓ | ✗ | ✗ | ✗ |
| Active development | ✓ (2026) | ✗ (2003) | ✗ (2016) | ✗ (2018) |

---

## Docs

- [CLI reference](USAGE.md)
- [Architecture](ARCHITECTURE.md)
- [Changelog](CHANGELOG.md)
- [Security & threat model](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

---

## Licence

Dual-licensed under AGPL-3.0-or-later and a commercial licence. See [LICENSE](LICENSE).

Commercial licensing: daniel@themalwarefiles.com
