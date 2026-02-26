# Stegcore v2 — Security

What Stegcore protects against, what it doesn't, and how to use it sensibly. Worth reading before you use it for anything that actually matters.

---

## What Stegcore is

Stegcore is a **crypto-steganography** tool. It combines two distinct techniques:

**Cryptography**: Your payload is encrypted before it's embedded. Even if someone extracts the hidden data, they can't read it without the correct passphrase. All three supported ciphers (Ascon-128, ChaCha20-Poly1305, AES-256-GCM) are AEAD schemes. Any tampering with the ciphertext is detected on decryption.

**Steganography**: The encrypted payload is hidden inside an ordinary image or audio file. The cover file looks and sounds completely normal. The goal is that someone who intercepts or examines it has no reason to suspect a hidden message exists.

Used together, these give you two independent layers of protection: concealment (they don't know there's a message) and confidentiality (even if they suspect there is one, they can't read it).

---

## Threat model

Stegcore is designed to hold up against the following:

**Passive observer**: Someone who can see the stego file but isn't actively looking for hidden data. The stego image is visually indistinguishable from the original.

**Casual forensic examiner**: Someone running basic file analysis (strings, exiftool, hex dump). Encrypted payloads produce high-entropy output with no readable strings or obvious structure.

**Automated file scanning**: Content scanners, email gateways, or cloud services checking for known file signatures or patterns. The embedded data has no fixed signature.

**Coercion, with deniable mode**: If you're forced to reveal a passphrase, deniable mode lets you hand over the decoy passphrase and decoy key file. The real payload stays hidden and inaccessible. Neither key file is structurally distinguishable as real or fake.

---

## What Stegcore doesn't protect against

Let me be real with you about relying on this software for anything high-stakes

**Dedicated steganalysis tools**

Tools like StegExpose, zsteg, and ML-based detectors (SRM, SPAM, GFR) analyse the statistical properties of pixel distributions rather than looking for visible changes. Standard LSB steganography is reliably detected by these tools. Stegcore's adaptive mode with spread spectrum significantly raises the detection threshold, but doesn't make detection impossible - particularly at high payload density on low-quality covers. If your adversary is running automated ML-based steganalysis across a large corpus of files, Stegcore provides meaningful but not absolute resistance.

*Stegcore Pro (currently in the works) will include a built-in self-test that runs detectors against your own output and reports a detection risk score before you share anything.*

**Traffic analysis and metadata**

Stegcore doesn't touch file metadata (EXIF, creation timestamps, file sizes). Sending a 4.2 MB PNG that's exactly 4.2 MB larger than any photo you've previously shared may itself be a signal. Normalise file sizes if this matters to your threat model.

**Endpoint compromise**

If an adversary has access to the machine where you run Stegcore, they can recover the passphrase from memory, keyloggers, or process inspection. Stegcore clears passphrases from its own variables after use, but can't protect against OS-level compromise.

**Key file exposure**

The key file contains the nonce, salt, and cipher metadata. Without the passphrase it's useless. However, its existence confirms that steganographic embedding occurred. Don't store the key file alongside the stego file if concealing the operation itself matters.

**Passphrase weakness**

Argon2id makes brute-forcing expensive, but a short or common passphrase can still be cracked with sufficient motivation and computing power. Use a strong, unique passphrase of at least 14 characters.

**WAV transcoding**

WAV sample LSB embedding won't survive conversion to MP3, AAC, or any other lossy audio format. Only use WAV covers when you control the file from embed to extract with no transcoding in between.

**Network-level analysis**

Stegcore hides data inside files. It doesn't protect the transmission of those files. If you send a stego file over an unencrypted channel, it can be intercepted and analysed. Use Stegcore alongside secure transport (Signal, encrypted email, HTTPS) — not instead of it.

---

## Cryptographic decisions

**Key derivation:** Argon2id with `time_cost=3`, `memory_cost=65536` (64 MB), `parallelism=4`, `hash_len=32`. These are above the current OWASP minimum recommendations. A single password guess requires 64 MB of RAM for roughly 50 ms on a modern CPU. GPU cracking is constrained by the memory requirement.

**Ciphers:** All three ciphers are AEAD (Authenticated Encryption with Associated Data). The ciphertext includes an authentication tag. Decryption fails with an explicit error if the ciphertext has been modified or if the wrong passphrase is used. There's no "partial decryption" that produces garbled output. Only clean success, or clean failure.

**Nonces:** Generated with `os.urandom()` per operation, never reused, stored in the key file for extraction.

**No passphrase storage:** The passphrase is never written to disk, logged, or included in the key file. It exists only in memory for the duration of the operation and is explicitly cleared from Python variables afterwards. Python string interning means cleared variables may still linger in memory temporarily. That's a Python-level limitation, not something specific to Stegcore.

---

## Deniable mode — The realistic assessment

Deniable mode provides **technical deniability**, not legal immunity. A few things worth thinking through honestly:

The existence of two key files for one stego image may itself raise suspicion with a sophisticated adversary. Deniable mode works best when:
- The decoy content is genuinely plausible (not obviously fabricated)
- The decoy passphrase is as strong as the real one
- The adversary doesn't already know the real content exists

Deniable mode doesn't protect against an adversary who can observe you using Stegcore and knows you embedded two payloads. It protects against one who only has access to the files themselves.

In jurisdictions with key disclosure laws (e.g. the UK's RIPA Part III), you may be legally required to disclose encryption keys. In such cases, deniable mode provides plausible cover for handing over the decoy passphrase. If this is relevant to your situation, stop reading this, pick up the phone, and call your lawyer.

---

## Responsible use

Stegcore is a neutral technology. It can protect privacy, secure intellectual property, support journalism, and enable digital rights. It can also be misused.

By using Stegcore you agree to:

- Use it only in ways that are lawful in your jurisdiction
- Not use it to facilitate harm to others
- Not use it to circumvent legitimate law enforcement activity where you have no right to do so

In the UK (where this software was developed), steganography is not illegal. The Computer Misuse Act 1990 applies to unauthorised access to computer systems, but not to the use of privacy tools on your own files. The Investigatory Powers Act 2016 covers surveillance, not the development of privacy software. If you're unsure about the legal position in your jurisdiction, once again, stop reading this, pick up the phone, and call your lawyer.

---

## Reporting security issues

If you discover a security vulnerability in Stegcore, please report it privately rather than opening a public issue. Use the repository's security advisory system or the contact address listed in the repository. And for the love of everything on God's green earth, please don't disclose vulnerabilities publicly until they've been assessed and a fix is available.

---

## What the Pro version adds

Stegcore Pro will include a **built-in steganalysis self-test, batch processing, and a scripting API among other things**. These directly address some of the limitations described above and are the most significant security improvements over the free version.