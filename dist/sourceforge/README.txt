STEGCORE
========

Crypto-steganography toolkit. Hide encrypted messages inside ordinary files.

Website:  https://github.com/elementmerc/Stegcore
Licence:  AGPL-3.0

WHAT IS THIS?

Stegcore combines encryption and steganography into a single cross-platform
toolkit. It encrypts your payload and hides the ciphertext inside ordinary
image or audio files. The result looks and sounds completely normal. Only
someone with the correct passphrase can recover what's inside.

FEATURES

- Three authenticated ciphers (Ascon-128, ChaCha20-Poly1305, AES-256-GCM)
- Adaptive LSB steganography (texture-aware, detection-resistant)
- Deniable dual-payload mode (two messages, two passphrases)
- Built-in steganalysis suite (five detectors + tool fingerprinting)
- Desktop GUI with dark/light themes
- Full CLI with wizard mode
- PNG, BMP, JPEG, WebP, WAV format support

INSTALLATION

Download the binary for your platform and run it. No installation required.
Or use the one-liner:

  curl -fsSL https://raw.githubusercontent.com/elementmerc/Stegcore/main/install.sh | bash

For more information, visit the GitHub repository.
