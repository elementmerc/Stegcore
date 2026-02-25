# Changelog

All notable changes to Stegcore are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] — 2026-02

Complete rewrite of Stegcore. Everything from the core cryptography to the
GUI and CLI is new. There is no upgrade path from v1 and stego files produced
by v1 cannot be extracted with v2.

### Added

**Core**
- `core/crypto.py` — encryption, decryption, Argon2id key derivation, and key file I/O
- `core/steg.py` — multi-format steganographic embed and extract (PNG, BMP, JPEG, WAV)
- `core/utils.py` — shared helpers (asset paths, temp files, dialog wrappers)
- Ascon-128 cipher support (NIST lightweight standard, default)
- ChaCha20-Poly1305 cipher support
- AES-256-GCM cipher support
- Argon2id key derivation (`time_cost=3`, `memory_cost=65536`, `parallelism=4`)
- AEAD authenticated encryption on all ciphers — wrong passphrase exits cleanly with no partial output
- Zstandard compression of payloads before encryption
- Adaptive LSB steganography with spread spectrum (PNG/BMP)
- Sequential LSB steganography (PNG/BMP, debugging/scripting)
- DCT-domain coefficient embedding (JPEG)
- Audio sample LSB embedding (WAV/PCM)
- Deniable dual-payload mode — two independent encrypted payloads in one cover image, two structurally identical key files
- Cover image scoring — entropy, texture density, resolution, 0–100 score with Excellent/Good/Fair/Poor label
- `get_capacity()` — returns available bytes for a given cover and mode
- Key file JSON schema with base64-encoded nonce, salt, cipher, steg mode, and deniable partition metadata

**GUI**
- `ui/app.py` — main CustomTkinter window with step-dot navigation indicator
- `ui/embed_flow.py` — 4-step guided embed flow (source, cover, options, confirm)
- `ui/extract_flow.py` — 3-step guided extract flow (image, key file, passphrase)
- `ui/theme.py` — dark and light themes
- Cover score shown inline during embed flow with colour-coded label
- Passphrase strength hint during entry
- Indeterminate progress bar during steg operations (runs in a background thread)
- Success and error screens with file paths shown on completion
- Stag.ico application icon

**CLI**
- `cli.py` — Typer application with `embed`, `extract`, `score`, `info`, `ciphers` commands
- `wizard` command — guided interactive mode for users new to the terminal
- Wizard embed flow: cover scoring inline, cipher picker, deniable option, passphrase strength hint, summary table, spinner during operation
- Wizard extract flow: key metadata preview, passphrase prompt
- Retry logic on all prompts (3 attempts before exit) with clear per-attempt messages
- `_read_secret()` — uses `Prompt.ask(password=True)` on a real terminal; falls back to `sys.stdin.readline()` when stdin is a pipe or redirect, preventing the `/dev/tty` hang in automated test harnesses
- `--force` flag to suppress all confirmation prompts for scripting
- `--no-score` flag to skip cover scoring
- JPEG cover with non-`.jpg` output path is auto-corrected with a warning rather than failing silently

**Documentation**
- `README.md` — project overview, quick start, format table, deniable mode, project structure
- `USAGE.md` — full CLI reference, wizard walkthrough, cipher/mode selection, deniable mode, scripting, passphrase guidance, file management
- `ARCHITECTURE.md` — layer overview, module responsibilities, data flow diagrams, dependency graph, design decisions
- `SECURITY.md` — threat model, honest limitations, cryptographic decisions, deniable mode assessment, responsible use, reporting

---

### Fixed

- **`munmap_chunk(): invalid pointer` crash (Linux glibc)** — three separate root causes, all in `core/steg.py`:
  - `ravel()`/`reshape()` on a C-contiguous array created two Python objects aliasing the same `malloc()` block; the second `free()` triggered the abort. Fixed by using `np.unravel_index` for all pixel access, writing directly into the original 3-D array.
  - `Image.fromarray(img_array)` exposed numpy's heap allocation to PIL's `ImagingCore` C struct via the buffer protocol. PIL's encoder could reallocate that pointer in C; numpy's subsequent `free()` caused the same abort. Fixed by using `img_array.tobytes()` + `Image.frombytes()` so PIL and numpy never share an allocation.
  - `np.array(pil_image)` — on modern Pillow, `__array_interface__` returns a raw C pointer into `ImagingCore`. If the data is already contiguous uint8, numpy skips the copy and creates a view. Fixed by `_load_img_array()`: calls `pil.tobytes()`, immediately `pil.close()` and `del pil`, then `np.frombuffer(...).copy()`. PIL's allocation is freed cleanly before numpy ever touches the data.

---

### Changed

- Copyright updated to 2026 Daniel Iwugo across all source files
- Key file schema version bumped — v1 key files are not compatible

---

## [1.0.0] — 2023

Initial release. Basic LSB steganography, single cipher (AES-256), no GUI, no deniable mode.