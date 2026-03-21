# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [3.0.0-dev] — 2026-03-20

Complete rewrite. Rust + Tauri v2 replaces Python + PyInstaller.

- Full Rust engine with three AEAD ciphers + Argon2id
- Tauri v2 desktop app (~10 MB native binary)
- React + TypeScript frontend with step-by-step wizards
- Built-in steganalysis suite (Chi-Squared, SPA, RS, LSB Entropy, tool fingerprinting)
- Progressive two-phase analysis (fast preliminary + background full)
- Interactive scatter plots, radar charts, and entropy heatmaps
- WebP and JPEG DCT (JSteg) embedding support
- First-run installer wizard
- Keyboard shortcuts (E/X/A/L/R/?)
- Interface size scaling, reduce-motion, clipboard auto-clear
- PDF/HTML/JSON/CSV export from cached reports
- Parallel per-test analysis (~3-4x speedup)
- Async Tauri commands (no UI freezes)
- Release profile: LTO + codegen-units=1

Bug fixes and improvements.

---

## [2.0.12] — 2026-03-12

- Passphrase memory hardening (zeroed after use)
- Full pytest suite (64 tests, 93.73% coverage)
- CI test job on every push

Bug fixes and improvements.

---

## [2.0.11] — 2026-03

- Asset path resolution fix for pip installs
- Lazy imports in GUI (eliminates 3-5s startup delay)
- CONTRIBUTING.md and CI licence check

Bug fixes and improvements.

---

## [2.0.10] — 2026-03

- Unified binary (CLI + GUI from single entrypoint)
- `--onedir` distribution (no per-launch extraction overhead)
- Lazy core imports in CLI (near-instant startup)
- Comparison table in README

Bug fixes and improvements.

---

## [2.0.6] — 2026-02

- JPEG support restored without `jpegio` (pixel-domain LSB, output as PNG)

---

## [2.0.0] — 2026-02

Complete rewrite of v1.

- Three AEAD ciphers (Ascon-128, ChaCha20-Poly1305, AES-256-GCM)
- Argon2id key derivation
- Adaptive LSB steganography with spread spectrum
- Deniable dual-payload mode
- Cover image scoring
- Desktop GUI (dark + light themes)
- CLI with wizard and power modes
- PNG, BMP, JPEG, WAV format support

---

## [1.0.0] — 2023

Initial release. Basic LSB, single cipher (AES-256), CLI only.
