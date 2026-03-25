# Security Model

Privacy is a right, not a feature. This document describes who Stegcore is built for, what it protects against, and — just as importantly — what it does not.

---

## Who is this for?

A journalist carrying interview recordings across a border checkpoint. An activist coordinating in a country where WhatsApp is monitored. A domestic abuse survivor who needs to keep evidence on a shared device. A whistleblower exfiltrating documents from an organisation that inspects outgoing files.

These people don't need another encryption tutorial. They need a tool that works, that doesn't require a security background, and that holds up when someone is looking.

---

## Threat model

### 1. Someone who can see your files

A cloud storage provider, an email gateway, a family member, a border agent scrolling through your gallery.

**How Stegcore helps:** The output file looks and sounds completely ordinary. A photo of a sunset is still a photo of a sunset. There is no visual or audible difference. No metadata changes, no suspicious file extensions, no extra files to explain.

### 2. Someone who suspects you're hiding data

A forensic examiner who runs your files through statistical analysis tools — chi-squared tests, sample pair analysis, RS analysis.

**How Stegcore helps:** Adaptive embedding mode concentrates modifications in areas of natural texture where statistical tests can't distinguish them from normal image noise. In testing against Aletheia (the most sophisticated open-source steganalysis toolkit), all four classical detectors failed to detect Stegcore's adaptive embedding.

No tool can promise absolute invisibility against unlimited analysis. What Stegcore does is raise the cost of detection to the point where it exceeds the cost of targeted, warrant-based investigation — which is how privacy *should* work.

### 3. Someone who demands your passphrase

A government agent, an abusive partner, or anyone with the leverage to force you to reveal what's hidden.

**How Stegcore helps:** Deniable mode embeds two separate messages with two separate passphrases. Give them one passphrase — they get a plausible decoy message. The real message stays hidden behind the other passphrase. The two halves of the file are structurally identical. There is no way to prove the second message exists.

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
