# CLI Reference

## Global flags

| Flag | Description |
|------|-------------|
| `--version` | Print version and exit |
| `--help` | Show help for any command |
| `--json` | Output results as JSON (all commands) |
| `--verbose` | Show full error chain on failure |

---

## stegcore embed

Hide a file inside a cover image or audio file.

```
stegcore embed <cover> <payload> <output> [options]
```

| Argument | Description |
|----------|-------------|
| `<cover>` | Cover file (PNG, BMP, JPEG, WAV, WebP) |
| `<payload>` | File to hide |
| `<output>` | Path for the output stego file |

| Option | Default | Description |
|--------|---------|-------------|
| `--passphrase <phrase>` | (prompted) | Encryption passphrase |
| `--mode adaptive\|sequential` | `adaptive` | Embedding mode |
| `--cipher chacha20-poly1305\|ascon-128\|aes-256-gcm` | `chacha20-poly1305` | Cipher |
| `--export-key <path>` | (none) | Export a key file alongside the output |
| `--deniable` | off | Enable dual-payload mode |
| `--decoy <file>` | (required with `--deniable`) | Decoy message file |
| `--decoy-passphrase <phrase>` | (prompted with `--deniable`) | Decoy passphrase |
| `--decoy-key <path>` | (none) | Export key file for decoy half |
| `--json` | off | JSON output |

**Examples:**

```bash
# Basic embed
stegcore embed photo.png secret.txt output.png

# With all options
stegcore embed photo.png secret.txt output.png \
  --passphrase "my passphrase" \
  --mode adaptive \
  --cipher chacha20-poly1305 \
  --export-key output.json

# Deniable mode
stegcore embed photo.png real.txt output.png \
  --passphrase "real-pass" \
  --deniable \
  --decoy decoy.txt \
  --decoy-passphrase "decoy-pass"
```

**JSON output shape:**
```json
{
  "output": "/path/to/output.png",
  "cipher": "chacha20-poly1305",
  "mode": "adaptive",
  "key_file": "/path/to/output.json"
}
```

---

## stegcore extract

Recover hidden data from a stego file.

```
stegcore extract <stego> [output] [options]
```

| Argument | Description |
|----------|-------------|
| `<stego>` | Stego file to extract from |
| `[output]` | Save extracted data to this path (default: print to stdout) |

| Option | Default | Description |
|--------|---------|-------------|
| `--passphrase <phrase>` | (prompted) | Passphrase used during embedding |
| `--key-file <path>` | (none) | Optional key file (not required for standard embeds) |
| `--json` | off | JSON output |

**Examples:**

```bash
# Extract and print to stdout
stegcore extract output.png

# Save to file
stegcore extract output.png recovered.txt --passphrase "my passphrase"

# With key file
stegcore extract output.png recovered.txt --key-file output.json
```

**JSON output shape:**
```json
{
  "bytes": 42,
  "output": "/path/to/recovered.txt"
}
```

---

## stegcore analyze

Analyse a file for signs of hidden content.

```
stegcore analyze <file> [options]
stegcore analyze --batch <glob> [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--batch <glob>` | (none) | Scan multiple files matching a glob pattern |
| `--report html\|json\|csv` | (none) | Generate a report |
| `-o <path>` | (required with `--report`) | Report output path |
| `--json` | off | JSON output |

**Examples:**

```bash
stegcore analyze photo.png
stegcore analyze photo.png --json
stegcore analyze photo.png --report html -o report.html
stegcore analyze --batch "downloads/*.png" --report html -o scan.html
```

**JSON output shape:**
```json
{
  "file": "photo.png",
  "format": "png",
  "verdict": "Clean",
  "overall_score": 0.12,
  "tool_fingerprint": null,
  "tests": [
    { "name": "Chi-Squared", "score": 0.10, "confidence": "High", "detail": "LSB distribution normal" },
    { "name": "Sample Pair Analysis", "score": 0.14, "confidence": "Medium", "detail": "No significant embedding detected" }
  ]
}
```

Verdict values: `"Clean"` · `"Suspicious"` · `"LikelyStego"`

---

## stegcore score

Score a cover file's suitability for embedding.

```
stegcore score <file> [--json]
```

Returns a quality score between 0.0 (poor) and 1.0 (excellent). Files scoring below 0.25 will be refused by `embed`.

---

## stegcore info

Show metadata embedded in a stego file without extracting.

```
stegcore info <stego> [--json]
```

Displays the cipher, mode, and whether deniable mode was used — without requiring the passphrase.

---

## stegcore ciphers

List available ciphers.

```
stegcore ciphers [--json]
```

---

## stegcore wizard

Interactive guided embed/extract workflow.

```
stegcore wizard
```

Prompts for each step interactively. Useful if you prefer not to pass options on the command line.

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | User error (wrong passphrase, payload too large, poor cover quality, etc.) |
| `2` | Encryption error (decryption failed, unsupported cipher) |
| `3` | I/O error (file not found, permission denied, disk full) |
| `4` | Format error (unsupported extension, corrupted file) |

---

## Docker

```bash
# Single file
docker run --rm -v $(pwd):/data ghcr.io/elementmerc/stegcore \
  embed /data/cover.png /data/secret.txt /data/output.png

# Batch scan
docker run --rm -v $(pwd)/photos:/data ghcr.io/elementmerc/stegcore \
  analyze --batch "/data/*.png" --report html -o /data/report.html
```
