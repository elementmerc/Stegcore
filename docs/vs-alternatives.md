# Stegcore vs. Alternatives

The steganography tools most people find first — Steghide, OpenStego — were groundbreaking when they were written. But they were written for a different era. Steghide hasn't been updated since 2003. OpenStego requires Java. Neither offers deniable mode, built-in detection, or encryption that would survive a modern audit.

Stegcore exists because the people who need steganography most — journalists, activists, researchers — deserve a tool that's been built with today's threats in mind, not yesterday's.

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

Every design decision in Stegcore starts with the same question: *what does someone in a dangerous situation actually need?*

**They need deniability.** If you can be forced to hand over your passphrase, encryption alone isn't enough. Deniable mode gives you two passphrases and two messages. One is real. One is a decoy. They're structurally identical — there's no way to prove the second exists. No other open-source tool offers this.

**They need to know if they've been caught.** The same tool that hides your data can also detect hidden data in other files. Stegcore's analysis suite runs five independent detectors and identifies which tool was used. If you receive a file and want to know whether it's been tampered with, you can check — without a separate tool.

**They need encryption that actually works.** Steghide uses DES. That was deprecated before most of its current users were born. Stegcore uses three modern authenticated ciphers backed by the RustCrypto project, with Argon2id key derivation. Every primitive has a published security proof and is actively maintained.

**They need simplicity.** One file in, one file out, one passphrase. No key files to manage, lose, or accidentally disclose. The metadata is embedded in the output. You only need your passphrase to recover your data.

**They need it to just work.** One binary, no dependencies. No Python version conflicts, no Java runtime, no Electron eating your RAM. Runs on Windows, macOS, and Linux. Desktop GUI for beginners, CLI for power users.

---

## Acknowledgements

Steghide and OpenStego laid the conceptual foundation that Stegcore builds on. Their authors made real contributions to the field. Stegcore does not dismiss that work — it carries it forward.
