# Stegcore v2 — Architecture

How Stegcore is put together: layer responsibilities, data flow, module contracts, and the reasoning behind key technical decisions.

---

## Layer overview

Stegcore is split into three strictly separated layers. Nothing in a lower layer knows about anything above it.

```
┌─────────────────────────────────────────────┐
│  Interfaces (cli.py, ui/)                   │  User-facing. No crypto or steg logic.
│  app.py  embed_flow.py  extract_flow.py     │  Delegates everything down to core/.
├─────────────────────────────────────────────┤
│  Core (core/)                               │  All crypto, steg, and I/O logic.
│  crypto.py   steg.py   utils.py             │  Pure functions. No Tk or Typer imports.
├─────────────────────────────────────────────┤
│  Theme (ui/theme.py)                        │  Shared UI state. Imported by ui/ only.
│                                             │  No core/ or interface imports.
└─────────────────────────────────────────────┘
```

`core/` works perfectly well from plain Python with no UI dependency, and the interface layer can be swapped out or extended without touching a single line of crypto or steg code.

---

## Module responsibilities

### `core/crypto.py`

Handles all encryption, decryption, and key material management.

**Key functions:**
- `encrypt(plaintext, passphrase, cipher)` — derives a key via Argon2id, encrypts with the chosen cipher, returns `{ciphertext, nonce, salt, key, cipher}`
- `decrypt(payload_dict, passphrase)` — re-derives the key from the salt, decrypts, returns plaintext bytes
- `write_key_file(path, ...)` — serialises nonce, salt, cipher, and steg metadata to JSON (base64-encoded)
- `read_key_file(path)` — deserialises and validates a key file, raises `ValueError` on missing or malformed fields
- `derive_key(passphrase, salt, cipher)` — public wrapper for key re-derivation (used by the extract flow for the adaptive steg key)

**Supported ciphers:**

| Cipher | Library | Key size | Notes |
|--------|---------|----------|-------|
| Ascon-128 | `ascon` | 128-bit | NIST lightweight standard, default |
| ChaCha20-Poly1305 | `cryptography` | 256-bit | Fast in software |
| AES-256-GCM | `cryptography` | 256-bit | Hardware-accelerated on modern CPUs |

**KDF:** Argon2id via `argon2-cffi`. Parameters: `time_cost=3`, `memory_cost=65536` (64 MB), `parallelism=4`, `hash_len=32`.

**Key file schema:**
```json
{
  "cipher":         "Ascon-128",
  "steg_mode":      "adaptive",
  "deniable":       false,
  "nonce":          "<base64>",
  "salt":           "<base64>",
  "info_type":      ".txt",         
  "partition_seed": "<base64>",     //deny-only
  "partition_half": 0               //deny-only
}
```
The last two fields only appear in deniable key files. The passphrase and derived key are never written anywhere.

---

### `core/steg.py`

All steganographic embedding, extraction, and analysis. Format is auto-detected from the file extension.

**Format routing:**
```
.png / .bmp  →  _embed_png  /  _extract_png
.jpg / .jpeg →  _embed_jpeg /  _extract_jpeg
.wav         →  _embed_wav  /  _extract_wav
```

**PNG/BMP — Adaptive LSB with spread spectrum:**

1. Compute an embedding map using local variance (3×3 sliding window). Pixels in flat, low-variance regions are excluded. Embedding there would be trivially detectable.
2. Generate a pseudorandom index permutation seeded from the steg key. This is the spread spectrum part. Bits are scattered across the image rather than written sequentially.
3. Each bit of the payload goes into the LSB of one colour channel of one pixel, selected by the permuted index.
4. A 32-bit payload length header is prepended using the same mechanism.

In sequential mode (no key), bits are written in raster order with no permutation. Less secure, but simpler and handy for debugging.

**JPEG — DCT-domain:**

Uses `jpegio` to access raw DCT coefficient arrays. Payload bits are embedded in the LSBs of usable AC coefficients. A coefficient is considered usable if its value is not in `{0, 1, −1, −2}`:

- `0` — skipping avoids creating energy in dead coefficients
- `±1` — skipping prevents underflow/overflow that would produce `0` or sign-flip to `∓1`
- `−2` — critical exclusion: `(−2 & ~1) | 1 == −1` in two's-complement. Writing bit `1` to coefficient `−2` produces `−1`, which is in the skip list. The extractor would then miss that position, desyncing the bit streams from that point onwards and silently corrupting the extracted ciphertext. Excluding `−2` at both ends makes the position sets provably identical.

`np.argwhere` is used to find usable positions. It returns row-major `[row, col]` pairs regardless of the array's own memory order, guaranteeing identical traversal on both sides. Direct 2D indexing (`component[r, c] = x`) handles all writes, avoiding `ravel()` which returns a copy on Fortran-order arrays and silently discards everything you write into it.

**WAV — Audio sample LSB:**

Opens the WAV with Python's `wave` module and embeds payload bits into the LSBs of the raw sample bytes. A 32-bit length header is written first.


**Deniable mode:**

Two payloads share one cover image. The spread spectrum index is split into two non-overlapping halves using a random `partition_seed`. The real payload uses the first half; the decoy uses the second. `split_indices()` handles the deterministic partition so both halves can be reconstructed from the same seed.

**Public API:**
- `embed(cover_path, payload_path, output_path, key, mode)` — format-dispatched embed
- `extract(stego_path, output_path, key, mode)` — format-dispatched extract
- `embed_deniable(cover_path, real_payload, decoy_payload, output_path, ...)` — dual embed
- `extract_deniable(stego_path, key, partition_seed, partition_half)` — dual extract
- `score_cover_image(image_path)` — returns a score dict
- `get_capacity(image_path, mode)` — returns available bytes for a given cover

**Cover score components:**
- Entropy (40%) — Shannon entropy of pixel value distribution, normalised to 0–8 bits
- Texture density (40%) — fraction of pixels in high-variance regions
- Resolution (20%) — normalised to 1920×1080

Score 0–100. Labels: Excellent (≥75), Good (≥55), Fair (≥35), Poor (<35).

---

### `core/utils.py`

Thin shared utilities with no logic of their own.

- `asset(filename)` — resolves a path to the `assets/` directory relative to the project root
- `temp_file(suffix)` — context manager wrapping `tempfile.NamedTemporaryFile`, ensures cleanup
- `show_error(msg)` — Tkinter messagebox wrapper (GUI only; CLI raises instead)
- `show_info(msg)` — Tkinter info dialog wrapper
- `ask_confirm(msg)` — Tkinter yes/no dialog wrapper

---

### `ui/theme.py`

Module-level theme state — the only shared UI state that crosses module boundaries.

- `THEMES` — two complete palettes (dark, light)
- `get_theme()` — returns the active palette dict
- `toggle()` — switches theme, calls `customtkinter.set_appearance_mode`, returns the new name
- `current_name()` — returns `"dark"` or `"light"`
- `apply_initial()` — called once at startup to initialise customtkinter appearance

Kept as a standalone module to avoid circular imports. Both `embed_flow` and `extract_flow` need theme access, but they're imported by `app.py` — so they can't import from `app.py` without creating a cycle. Importing from `theme.py` (which imports nothing from `ui/`) breaks the cycle cleanly.

---

### `ui/app.py`

The main `customtkinter.CTk` window. Owns navigation state, the top bar, and the bottom nav bar.

**Navigation model:**
```
show_home()
    │
    ├─ _start_embed()   →  EmbedFlow   ─┐
    └─ _start_extract() →  ExtractFlow  ├─ _steps list
                                         │
                          _render_step() ←─ step index
                               │
                          _on_continue() → validate_step → next step or execute()
                          _on_back()     → previous step or show_home()
```

**Threading model:**

File dialogs must run on the main Tk thread. The heavy numpy/PIL steg operation runs in a `threading.Thread`. The sequence is:

1. `_on_continue()` disables nav, calls `flow.execute(app)` on the main thread
2. `execute()` runs all file dialogs on the main thread
3. `execute()` calls `app._show_working()` to swap in the progress screen
4. `execute()` launches `threading.Thread(target=_do_embed)` for the steg operation
5. `_do_embed` calls `app.after(0, callback)` to return to the main thread for key-saving dialogs and the success screen

This keeps the UI responsive during the steg operation whilst respecting Tkinter's single-thread requirement.

**Progress indicator:**

The top bar has a segmented dot indicator (`_update_dots`). Each step is one dot: 8 px wide when inactive, 22 px wide and coloured for the current step, coloured and 8 px for completed steps. Rebuilt on every step transition.

---

### `ui/embed_flow.py` and `ui/extract_flow.py`

Flow classes that own the step UIs and validation logic. They don't interact with Tkinter directly except to build frames — all navigation is delegated back to `app.py`.

Each flow has:
- `steps` — list of `(label, builder_fn)` tuples
- `action_label` — string shown on the final Continue button
- `validate_step(n)` — returns bool, shows an error dialog on failure
- `execute(app)` — runs the full operation (dialogs + steg, as above)

---

### `cli.py`

Typer application wrapping the same `core/` functions as the GUI. No UI imports.

**Commands:**

| Command | Description |
|---------|-------------|
| `wizard` | Guided interactive mode for new users |
| `embed` | Full embed pipeline with optional deniable mode |
| `extract` | Full extract pipeline |
| `score` | Cover image analysis report |
| `info` | Inspect a key file without extracting |
| `ciphers` | List supported ciphers |

Passphrases are read via `_read_secret()`, which uses `rich.prompt.Prompt.ask(password=True)` when stdin is a real terminal, and falls back to `sys.stdin.readline()` when stdin is a pipe or redirect. This is what makes the CLI work correctly in automated test harnesses without hanging on `/dev/tty`.

The `--force` flag suppresses all confirmation prompts for scripting.

---

## Data flow: embed

```
User input (GUI or CLI)
    │  passphrase, cover path, payload path, cipher, mode
    ▼
crypto.encrypt(plaintext, passphrase, cipher)
    │  returns: ciphertext, nonce, salt, key
    ▼
[deniable: crypto.encrypt(decoy_text, decoy_pass, cipher)]
    │
    ▼
steg.embed(cover, ciphertext_file, output, key=steg_key, mode=mode)
    │  PNG:  adaptive LSB via np.unravel_index
    │  JPEG: DCT coefficient LSB via np.argwhere direct indexing
    │  WAV:  audio sample LSB
    ▼
crypto.write_key_file(key_path, nonce, salt, cipher, ...)
    │
    ▼
stego file  +  key file(s) on disk
```

## Data flow: extract

```
stego file  +  key file  +  passphrase
    │
    ▼
crypto.read_key_file(key_path)
    │  returns: cipher, nonce, salt, steg_mode, deniable, ...
    ▼
crypto.derive_key(passphrase, salt, cipher)   [adaptive mode only]
    │  re-derives steg_key for spread-spectrum index reconstruction
    ▼
steg.extract(stego, tmp_file, key=steg_key, mode=steg_mode)
    │
    ▼
crypto.decrypt({ciphertext, nonce, salt, cipher}, passphrase)
    │  wrong passphrase → ValueError (AEAD authentication fails cleanly)
    ▼
recovered plaintext → output file
```

---

## Dependency graph

```
cli.py  ─────────────────────────────────┐
main.py  →  ui/app.py                    │
                │                        │
                ├─→  ui/theme.py         │  (no core imports)
                ├─→  ui/embed_flow.py   ─┤
                └─→  ui/extract_flow.py ─┤
                          │              │
                          └─────────────┴──→  core/crypto.py
                                              core/steg.py
                                              core/utils.py
```

No cycles. `core/` has no knowledge of `ui/` or `cli.py`.

---

## Key design decisions

**Why Argon2id and not PBKDF2 or scrypt?**
Argon2id won the Password Hashing Competition and is the current OWASP recommendation. It's memory-hard (resistant to GPU cracking) and combines the side-channel resistance of Argon2i with the GPU resistance of Argon2d. At 64 MB memory cost, a single password guess takes roughly 50 ms on a modern CPU and is constrained by memory bandwidth on a GPU.

**Why Zstandard and not zlib/gzip?**
Better compression ratios at comparable or faster speeds, and higher entropy uniformity in the output. Compressed data looks more random, which is desirable when hiding it inside image noise.

**Why is the key file JSON and not binary?**
Human-readable format makes debugging and auditing straightforward. The only sensitive values (nonce, salt) are base64-encoded and useless without the passphrase, which is never stored.

**Why AGPL-3.0 and not MIT or GPL?**
AGPL ensures that anyone deploying a modified Stegcore as a network service must publish their modifications. This protects the research value of the project and prevents closed-source forks in the privacy tooling space.