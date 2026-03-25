# Security Model

This document describes what Stegcore protects against and what it does not.

---

## Threat model

Stegcore is designed to protect against three classes of adversary:

### 1. Passive observer

Someone who can see your files but is not specifically looking for hidden data — for example, a cloud storage provider, an email gateway, or someone who briefly has access to your device.

**Protection:** The output file looks identical to an ordinary image or audio file. There is no visible difference.

### 2. Active forensic examiner

Someone who actively suspects you are hiding data and applies statistical analysis tools to your files.

**Protection:** Adaptive embedding mode is designed to resist the statistical tests used by common steganalysis tools. Files embedded in adaptive mode score low on the built-in analysis suite.

No steganographic tool can guarantee invisibility against a determined examiner with unlimited time. The goal is to make your files indistinguishable from unmodified ones at a practical cost. For strong operational security, choose cover files with rich, natural texture; avoid low-detail or synthetic images.

### 3. Coerced disclosure

Someone who has your files and demands your passphrase under threat.

**Protection:** Deniable mode lets you embed two separate messages — one real, one innocuous — each accessible with a different passphrase. The two halves of the file are structurally identical. There is no way to determine which passphrase is "real" by examining the file alone.

---

## Encryption

Your data is encrypted before it is hidden. If the hidden data were somehow extracted without the passphrase, it would be unreadable ciphertext.

Stegcore uses authenticated encryption: the passphrase not only encrypts your data but also authenticates it. Any modification to the stego file — even a single bit — will cause extraction to fail with an error rather than returning corrupted data.

Your passphrase is processed through a memory-hard key derivation function (Argon2id) before use. This makes brute-force attacks significantly harder than attacking a simple password hash.

---

## What Stegcore does not protect against

- **Metadata:** file creation times, EXIF data, and operating system metadata are not modified. If your cover file contains identifying metadata, that metadata may remain.
- **Traffic analysis:** Stegcore does not hide that you are sending a file — only that the file contains hidden data. Use appropriate transport security for your channel.
- **Device compromise:** if your device is compromised before embedding or after extraction, an attacker may have access to your plaintext data regardless of what Stegcore does.
- **Cover file selection:** embedding always modifies the cover file in some way. If you share the same cover image before and after embedding, a forensic examiner could detect that the file changed. Always embed into a fresh copy of a cover file.
- **Passphrase strength:** no encryption protects a short or guessable passphrase. Use a long, random passphrase.

---

## Supported ciphers

All three ciphers provide authenticated encryption with additional data (AEAD). They are all considered secure for the purpose of protecting personal data.

| Cipher | Notes |
|--------|-------|
| ChaCha20-Poly1305 | Default. Fast on all hardware including devices without AES acceleration. |
| Ascon-128 | Compact. Designed for constrained environments. |
| AES-256-GCM | Standard. Hardware-accelerated on most modern CPUs. |

---

## Steganalysis suite

Stegcore includes a built-in steganalysis suite with the following detectors:

- **Chi-Squared** (block-based) — tests LSB pair distribution uniformity across image blocks
- **Sample Pair Analysis** (DWW quadratic estimator) — estimates embedding rate from trace multiset asymmetry
- **RS Analysis** (per-channel) — Regular/Singular group asymmetry detection with correct F₋₁ mask
- **LSB Entropy** (per-channel autocorrelation) — measures spatial correlation of least significant bits
- **Tool Fingerprinting** — identifies likely embedder (Steghide, OpenStego, generic sequential LSB)

Results are combined into an ensemble verdict: Clean (<0.25), Suspicious (0.25–0.55), or Likely Stego (>0.55).

---

## Reporting a vulnerability

See [SECURITY.md](../SECURITY.md) for the responsible disclosure process.
