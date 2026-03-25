# Stegcore vs. Alternatives

A comparison of Stegcore with the most widely used open-source steganography tools.

---

## Overview

| Feature | Steghide | OpenStego | Stegcore |
|---------|----------|-----------|---------|
| **Formats** | JPEG, BMP, WAV, AU | BMP, PNG | PNG, BMP, JPEG, WAV, WebP, FLAC |
| **Encryption** | DES / RC4 (obsolete) | AES-128 | Ascon-128, ChaCha20-Poly1305, AES-256-GCM |
| **Key derivation** | 32-bit PRNG seed (crackable) | Undocumented | Argon2id (memory-hard) |
| **Deniable mode** | None | None | Dual-payload |
| **GUI** | CLI only | Java Swing | Native desktop (Windows, macOS, Linux) |
| **Built-in steganalysis** | No | No | Yes (5 detectors + tool fingerprinting) |
| **Key file required** | Yes | N/A | No (optional export) |
| **Active maintenance** | Abandoned 2003 | Active | Active |
| **Runtime dependency** | C libraries | Java 11+ | None (native binary) |
| **Docker** | No | No | Yes (multi-arch) |
| **Licence** | GPL-2.0 | GPL-2.0 | AGPL-3.0-or-later + commercial |

---

## Steghide

Steghide is the most widely referenced steganography tool in security documentation and CTF write-ups. It introduced many people to the concept.

However, it has not been updated since 2008 and carries a known vulnerability: **CVE-2021-27211**. The root cause is that Steghide uses a 32-bit PRNG seed derived from the passphrase. An attacker can enumerate all ~4 billion possible seeds in a few hours on consumer hardware, regardless of passphrase length. A passphrase that takes decades to brute-force directly can be bypassed in the time it takes to watch a film.

Steghide also predates modern authenticated encryption. It uses DES (deprecated) and RC4 (broken). It does not verify data integrity, so a corrupted stego file may silently produce garbled output.

For historical research, CTF challenges where the challenge is intentionally solvable, or understanding the field: Steghide is fine. For any genuine operational use: do not use Steghide.

Stegcore exists in part as a tribute to Steghide's legacy and as an answer to the question of what a secure replacement looks like.

---

## OpenStego

OpenStego is actively maintained and takes a more considered approach than Steghide. It supports PNG and BMP, offers basic watermarking functionality, and its GUI, while dated, works.

Its limitations:

- Requires Java 11 or later, adding a significant runtime dependency
- Supports only BMP and PNG (no audio, no JPEG, no WebP)
- No deniable mode
- No built-in steganalysis
- Key derivation function internals are not published, making independent security review difficult
- The GUI does not feel native on any platform — Java Swing has not aged well

---

## Other tools surveyed

| Tool | Status | Notes |
|------|--------|-------|
| SilentEye | Unmaintained (last release 2019) | Qt GUI, limited formats |
| DeepSound | Windows-only, closed source | Notable for FLAC/MP3 support |
| Stegosuite | Maintenance uncertain | Java, BMP/GIF/PNG only |
| OutGuess | Unmaintained | JPEG-specific DCT method |
| SNOW | Niche | Text-based whitespace steganography only |

---

## Detection resistance

Stegcore's adaptive embedding mode was tested against Aletheia, the most
sophisticated open-source steganalysis toolkit. Results on a real-world
cover image:

| Aletheia test | Result |
|---------------|--------|
| Sample Pair Analysis (SPA) | **No hidden data found** |
| RS Analysis | **No hidden data found** |
| Weighted Stego (WS) | **No hidden data found** |
| Triples | **No hidden data found** |

All four of Aletheia's classical statistical detectors failed to detect
Stegcore's adaptive embedding. By comparison, Aletheia detects Steghide
and sequential LSB tools reliably.

---

## What Stegcore adds

Beyond matching the best features of each tool, Stegcore introduces capabilities not found in any open-source steganography tool:

**Dual-payload deniable mode.** No other open-source tool offers this. Two separate messages in one file, two passphrases, structurally indistinguishable halves.

**Built-in steganalysis.** The same tool that embeds can also detect. Stegcore's analysis suite runs Chi-squared, Sample Pair Analysis, RS Analysis, LSB Entropy, and audio-specific variants, plus a tool fingerprinting module that identifies the likely embedder. No other open-source steganography tool includes this.

**Modern, auditable cryptography.** All primitives are from the RustCrypto project, with published security proofs and active maintenance. Argon2id key derivation is memory-hard by design.

**No key file required.** Metadata is embedded in the stego file. You only need your passphrase to extract — there is no separate file to manage, lose, or disclose.

**Native binary.** No Python, no Java, no Electron. A single executable that runs on Windows, macOS, and Linux without any runtime dependencies.

---

## Acknowledgements

Steghide and OpenStego laid the conceptual foundation that Stegcore builds on. Their authors made real contributions to the field. Stegcore does not dismiss that work — it carries it forward.
