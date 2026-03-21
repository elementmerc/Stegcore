# Stegcore — CLI Usage Guide

Full reference for the Stegcore CLI. The GUI is self-explanatory with
step-by-step wizards. This document covers the terminal.

---

## Two ways to use the CLI

**Guided wizard (beginners):**
```bash
stegcore-cli wizard
```
Walks you through every step with plain-English prompts. No flags
needed. Covers embedding, extracting, scoring, and analysis.

**Power-user commands (scripting):**
```bash
stegcore-cli embed cover.png secret.txt -o stego.png --cipher chacha20-poly1305
stegcore-cli extract stego.png -o recovered.txt --passphrase "$PASS"
```

Both modes call the same underlying code.

---

## Commands

### `embed` — Hide a file inside a cover

```bash
stegcore-cli embed <cover> <payload> -o <output> [options]
```

| Flag | Default | Description |
|---|---|---|
| `-o, --output` | required | Output stego file path |
| `--cipher` | `chacha20-poly1305` | Cipher: `ascon-128`, `aes-256-gcm`, `chacha20-poly1305` |
| `--mode` | `adaptive` | Embedding mode: `adaptive` (secure) or `sequential` (high capacity) |
| `--deniable` | off | Enable deniable dual-payload mode |
| `--decoy` | — | Decoy payload file (required with `--deniable`) |
| `--export-key` | off | Export a `.json` key file alongside the output |
| `--passphrase` | prompt | Passphrase (omit for interactive prompt) |
| `--json` | off | Output result as JSON |
| `--verbose` | off | Show detailed error chains |

**Examples:**
```bash
# Basic embed
stegcore-cli embed photo.png secret.txt -o stego.png

# With specific cipher and key export
stegcore-cli embed photo.png secret.txt -o stego.png --cipher aes-256-gcm --export-key

# Deniable mode
stegcore-cli embed photo.png real.txt -o stego.png --deniable --decoy decoy.txt

# Scripted (passphrase via flag, JSON output)
stegcore-cli embed photo.png secret.txt -o stego.png --passphrase "my passphrase" --json
```

### `extract` — Recover a hidden file

```bash
stegcore-cli extract <stego> -o <output> [options]
```

| Flag | Default | Description |
|---|---|---|
| `-o, --output` | required | Output recovered file path |
| `--key-file` | none | Optional key file for extraction |
| `--passphrase` | prompt | Passphrase |
| `--json` | off | Output result as JSON |

**Examples:**
```bash
stegcore-cli extract stego.png -o recovered.txt
stegcore-cli extract stego.png -o recovered.txt --key-file stego.key.json
```

### `analyse` — Detect hidden content

```bash
stegcore-cli analyse <file>... [options]
```

| Flag | Default | Description |
|---|---|---|
| `--json` | off | Output results as JSON |
| `--verbose` | off | Show per-test details |

Runs the full steganalysis suite: Chi-Squared, SPA, RS Analysis, LSB
Entropy, and tool fingerprinting. Returns a verdict (Clean / Suspicious /
Likely Stego) with an overall score.

**Examples:**
```bash
# Single file
stegcore-cli analyse suspect.png

# Batch (parallel processing)
stegcore-cli analyse *.png --json

# Verbose with per-test breakdown
stegcore-cli analyse suspect.png --verbose
```

### `score` — Rate a cover file

```bash
stegcore-cli score <cover>
```

Returns a 0.0–1.0 suitability score. Higher is better. Considers
entropy, texture density, and resolution.

### `ciphers` — List available ciphers

```bash
stegcore-cli ciphers
```

### `wizard` — Interactive guided mode

```bash
stegcore-cli wizard
```

---

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | User error (bad input, insufficient capacity, empty payload) |
| 2 | Crypto error (wrong passphrase, decryption failed) |
| 3 | I/O error (file not found, permission denied) |
| 4 | Format error (unsupported format, corrupted file) |

---

## JSON output

All commands support `--json` for scripted pipelines:

```bash
stegcore-cli embed cover.png secret.txt -o stego.png --json --passphrase "$PASS"
```

```json
{
  "ok": true,
  "data": {
    "outputPath": "stego.png",
    "keyFilePath": null
  }
}
```

Errors:
```json
{
  "ok": false,
  "error": "Insufficient capacity: payload requires 45 KB but cover supports 12 KB"
}
```
