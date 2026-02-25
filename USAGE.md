# Stegcore v2 — Usage Guide

Full reference for the Stegcore CLI. For the GUI, the interface is pretty self-explanatory. This doc covers the terminal.

---

## Two ways to use the CLI

**New to the terminal, or just getting started:**
```bash
stegcore wizard
```
The wizard walks you through every step with plain-English prompts, inline explanations, and multiple chances to correct mistakes. No flags, no arguments, no manuals required. It covers embedding, extracting, and scoring.

**Experienced users / scripting / automation:**
```bash
stegcore embed photo.png secret.txt stego.png --cipher AES-256-GCM
stegcore extract stego.png stego.key.json recovered.txt --force
```
Single-line commands with explicit flags. All prompts can be bypassed with `--passphrase` and `--force` for use in scripts.

Both modes call the same underlying code — the wizard just handles all the option-picking interactively.

---

## Installation

```bash
pip install -e .
```

Two entry points are installed:

- `stegcore` — the CLI
- `stegcore-gui` — launches the desktop GUI

You can also run directly without installing:
```bash
python cli.py wizard
python cli.py embed ...
python main.py
```

---

## Wizard mode

```bash
stegcore wizard
```

At launch, the wizard shows a numbered menu:

```
  1  Embed   — hide an encrypted message inside a file
  2  Extract — recover a hidden message from a file
  3  Score   — check how good a file is as a cover
  4  Exit
```

**Embed flow:**
1. Prompts for the cover file path — shows the score inline and warns if it's poor
2. Prompts for the message file path — shows file size
3. Prompts for the output path — warns if the file already exists
4. Asks you to choose a cipher from a numbered list (press Enter for the default)
5. Asks about deniable mode (yes/no)
6. Prompts for a passphrase twice, with a strength hint
7. Shows a full summary and asks for confirmation before doing anything
8. Shows a spinner during the embed

**Extract flow:**
1. Prompts for the stego file path
2. Prompts for the key file path — shows key metadata so you can confirm it's the right one
3. Prompts for the output path
4. Prompts for the passphrase

**Error handling:** Every prompt retries up to 3 times on bad input (empty path, file not found, wrong extension, passphrase mismatch) with a clear explanation each time, before giving up and exiting cleanly.

---

## Command reference

### `score`

Analyse a cover image before embedding.

```bash
stegcore score <image>
```

**Example:**
```bash
stegcore score photo.png
```

Outputs a score out of 100 (Excellent / Good / Fair / Poor) with entropy, texture density, and capacity breakdown. Aim for 55 or above. Below 35 is usable but increasingly detectable by steganalysis tools.

---

### `embed`

Hide an encrypted payload inside a cover file.

```bash
stegcore embed <cover> <payload> <output> [options]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `cover`  | Cover file (.png, .bmp, .jpg, .jpeg, .wav) |
| `payload`| Text file to hide |
| `output` | Output stego file path |

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--key` | `-k` | `<output>.key.json` | Key file save path |
| `--cipher` | `-c` | `Ascon-128` | Cipher: Ascon-128, ChaCha20-Poly1305, AES-256-GCM |
| `--mode` | `-m` | `adaptive` | Steg mode for PNG/BMP: adaptive or sequential |
| `--deniable` | `-d` | off | Deniable dual-payload (adaptive PNG/BMP only) |
| `--passphrase` | `-p` | prompted | Passphrase (see security note below) |
| `--force` | `-f` | off | Skip overwrite confirmation |
| `--no-score` | — | off | Skip cover image scoring |

**Examples:**
```bash
# Basic — passphrase prompted securely
stegcore embed photo.png secret.txt stego.png

# Specify cipher and save key to a custom path
stegcore embed photo.png secret.txt stego.png \
  --cipher AES-256-GCM \
  --key ~/keys/session1.json

# Non-interactive for scripts
stegcore embed photo.png secret.txt stego.png \
  --passphrase "YourPassphrase" \
  --force \
  --no-score

# WAV cover
stegcore embed recording.wav secret.txt stego.wav

# JPEG cover (output must also be .jpg)
stegcore embed photo.jpg secret.txt stego.jpg

# Deniable mode
stegcore embed photo.png real.txt stego.png --deniable
# Prompts: real passphrase ×2, decoy file path, decoy passphrase
```

⚠ Passing `--passphrase` as a command-line argument makes it visible in shell history and `ps` output. Use interactively or pipe from a secrets manager for anything sensitive.

---

### `extract`

Recover a hidden payload from a stego file.

```bash
stegcore extract <stego> <key-file> <output> [options]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `stego`    | Stego file |
| `key-file` | Key file (.json) from embedding |
| `output`   | Where to save the recovered text |

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--passphrase` | `-p` | prompted | Passphrase used during embedding |
| `--force` | `-f` | off | Overwrite output without prompting |

**Example:**
```bash
stegcore extract stego.png stego.key.json recovered.txt
```

**Wrong passphrase behaviour:** All three ciphers use authenticated encryption (AEAD). A wrong passphrase produces a clean authentication error and exits with code 1. There's no partial decryption or garbled output.

---

### `info`

Inspect a key file without performing extraction.

```bash
stegcore info <key-file>
```

Shows cipher, steg mode, deniable flag, payload type, and (for deniable files) whether this is the real or decoy key. Doesn't require the stego file or passphrase.

---

### `ciphers`

List all supported ciphers.

```bash
stegcore ciphers
```

---

## Cipher selection

All three ciphers are AEAD with Argon2id key derivation. The choice has no effect on steganalysis resistance.

| Cipher | Best for |
|--------|----------|
| `Ascon-128` | Default. Lightweight, NIST standard, good on all hardware |
| `ChaCha20-Poly1305` | Systems without AES hardware acceleration |
| `AES-256-GCM` | Systems with AES-NI (most modern x86 / ARM64 CPUs) |

---

## Steg mode (PNG and BMP only)

| Mode | How it works | When to use |
|------|-------------|-------------|
| `adaptive` | Bits scattered via spread spectrum in high-texture regions | Always — default, much harder to detect |
| `sequential` | Bits written from top-left in raster order | Debugging only — detectable by basic tools |

JPEG and WAV ignore `--mode` — they always use their own format-appropriate algorithm.

---

## Deniable mode

Two payloads, one cover file. Two key files produced — structurally identical, neither self-identifying as real or fake.

```bash
stegcore embed cover.png real.txt stego.png --deniable
# Prompts:
#   1. Real passphrase (twice to confirm)
#   2. Path to decoy text file
#   3. Decoy passphrase (must differ from real passphrase)
# Saves:
#   stego.png              — the cover with both payloads
#   stego.key.json         — real key file
#   stego.key.decoy.json   — decoy key file
```

**To extract the real message:**
```bash
stegcore extract stego.png stego.key.json recovered.txt
# Enter the real passphrase
```

**To extract the decoy (under coercion):**
```bash
stegcore extract stego.png stego.key.decoy.json recovered.txt
# Enter the decoy passphrase
```

**Requirements:**
- Cover must be PNG or BMP with adaptive mode
- Decoy passphrase must differ from the real one
- Decoy content should be genuinely plausible

---

## Scripting and automation

The `--force` and `--passphrase` flags make Stegcore usable in automated pipelines.

```bash
# Batch embed in a shell loop
for f in documents/*.txt; do
  stegcore embed cover.png "$f" "stego_$(basename "$f" .txt).png" \
    --passphrase "$STEG_PASS" \
    --force \
    --no-score
done
```

Exit codes: `0` on success, `1` on any error. All error messages go to stderr.

---

## Passphrase guidance

- Minimum 4 characters; 14+ strongly recommended
- Wizard and interactive prompts show a strength hint as you type
- Don't reuse steganography passphrases elsewhere
- For deniable mode: make both passphrases strong — a weak decoy looks suspicious
- Interactive prompts retry 3 times on empty or short input before exiting

---

## File management

| File | Keep? | Notes |
|------|-------|-------|
| `stego.png` | Share freely | Looks like an ordinary image |
| `stego.key.json` | Keep secure | Required for extraction — store separately from stego |
| `stego.key.decoy.json` | Keep separate (deniable only) | The key you hand over under coercion |
| Original `cover.png` | Optional | Not needed for extraction |
| Original `secret.txt` | Your choice | Stegcore doesn't delete or modify it |