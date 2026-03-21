# Architecture

How Stegcore is built.

---

## Overview

Stegcore is a Rust workspace with four crates and a React frontend:

```
Cargo.toml              root workspace
├── crates/core/        public library (errors, wrappers, keyfile, utils, verses)
├── crates/cli/         CLI binary (clap v4)
├── src-tauri/          Tauri v2 desktop app shell
├── frontend/           React + TypeScript + Vite
└── libstegcore/        private engine
```

The engine (`libstegcore`) contains the steganographic algorithms and
steganalysis suite. It's a standard Rust crate linked as an optional
dependency. Public builds without it compile cleanly — all engine calls
return a user-friendly "engine absent" error.

---

## Data flow

### Embedding

```
User input (GUI or CLI)
  → passphrase + payload file + cover file + cipher + mode
  → Argon2id KDF derives encryption key from passphrase + random salt
  → Zstandard compresses the payload
  → AEAD cipher encrypts (ChaCha20-Poly1305 / AES-256-GCM / Ascon-128)
  → Metadata header prepended (cipher, mode, nonce, salt)
  → Engine embeds ciphertext into cover file LSBs
  → Output: stego file (+ optional key file)
```

### Extraction

```
Stego file + passphrase (+ optional key file)
  → Engine reads embedded bits from LSBs
  → Parse metadata header
  → Argon2id KDF re-derives key from passphrase + stored salt
  → AEAD cipher decrypts (fails cleanly on wrong passphrase)
  → Zstandard decompresses
  → Output: recovered payload
```

### Analysis

```
Target file
  → Detect format (magic bytes + extension)
  → Run detectors in parallel (rayon):
      Chi-Squared, SPA, RS Analysis, LSB Entropy
  → Tool fingerprinting (Steghide, OutGuess, OpenStego signatures)
  → Block entropy heatmap (images) or waveform analysis (audio)
  → Ensemble scoring → verdict (Clean / Suspicious / Likely Stego)
  → Output: AnalysisReport with distribution data
```

---

## Crate responsibilities

### `crates/core` — Public library

- **errors.rs** — `StegError` enum with recovery suggestions
- **steg.rs** — Safe wrappers for engine embed/extract/assess functions
- **analysis.rs** — Safe wrappers for analysis + HTML/CSV/JSON report
  generation
- **keyfile.rs** — KeyFile serialisation (JSON + base64)
- **utils.rs** — Format detection (magic bytes), file validation, temp files
- **verses.rs** — 30 NLT Bible verses, time-based rotation

### `crates/cli` — CLI binary

- **main.rs** — Clap argument parsing, command dispatch, coloured help
- **commands/** — One file per subcommand (embed, extract, analyse, score,
  info, ciphers, wizard, doctor, benchmark)
- **output.rs** — Coloured terminal output, RAII spinner, exit codes,
  JSON output helper
- **prompt.rs** — Secure passphrase input
- **config.rs** — TOML config file (~/.config/stegcore/config.toml)

### `src-tauri` — Desktop app

- **lib.rs** — Tauri IPC commands (all async with `spawn_blocking`),
  settings persistence, first-run detection, verse command, progressive
  analysis with event emission
- All CPU-heavy operations run on tokio's blocking thread pool to prevent
  GTK event loop starvation

### `frontend` — React UI

- **Routes:** Home, Embed (4-step), Extract (3-step), Analyse, Learn
- **State:** Zustand stores (embed, extract, settings, drag)
- **Dashboard:** Canvas-based animated charts (Chi-Squared, RS, SPA gauge,
  LSB heatmap / Oscilloscope trace)
- **Design:** CSS custom properties (`--sc-*` / `--ui-*`), dark + light
  themes, interface size scaling via CSS zoom

---

## Key design decisions

1. **Two repositories** — Public code (AGPL) and private engine
   (proprietary) are separate crates. The FFI boundary was replaced with
   a direct Rust dependency gated behind an optional feature flag.

2. **Self-contained payload** — Metadata (cipher, nonce, salt) is embedded
   in the payload itself. No key file required for extraction. The key
   file is an optional export for backup or out-of-band sharing.

3. **Async Tauri commands** — Every IPC command that touches the engine
   uses `tauri::async_runtime::spawn_blocking()` to avoid blocking the
   GTK main thread.

4. **Progressive analysis** — Fast preliminary results from 10% sampling,
   full accuracy runs in background. Tauri event (`analysis_complete`)
   notifies the frontend when done.

5. **Canvas charts** — The steganalysis dashboard uses HTML5 Canvas (not
   SVG) for frame-precise animation control. Each chart manages its own
   `requestAnimationFrame` loop with a frame counter.

6. **No network calls** — The application is fully offline. No telemetry,
   no analytics, no CDN fonts, no update checks. Fonts are bundled as
   local WOFF2 files.

---

## Build

```bash
# Development (GUI + hot reload)
cargo tauri dev

# Release binary
cargo build --release

# Without engine (public build)
cargo build --release --no-default-features

# Run tests
cargo test --workspace

# Type check frontend
cd frontend && npx tsc --noEmit
```
