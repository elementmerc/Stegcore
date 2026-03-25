// Copyright (C) 2026 Daniel Iwugo — elementmerc
// SPDX-License-Identifier: AGPL-3.0-or-later OR LicenseRef-Stegcore-Commercial
//
// This file is part of Stegcore. Stegcore is free software: you can
// redistribute it and/or modify it under the terms of the GNU Affero
// General Public License as published by the Free Software Foundation,
// either version 3 of the License, or (at your option) any later version.
//
// Commercial licensing: daniel@themalwarefiles.com

use crate::errors::StegError;
use crate::keyfile::KeyFile;
use std::path::Path;

// ── Cipher string → engine enum conversion ───────────────────────────────────

/// Parse a cipher identifier string into the engine's enum.
/// Accepted values: "ascon-128", "chacha20-poly1305", "aes-256-gcm".
#[cfg(engine)]
fn parse_cipher(s: &str) -> Result<stegcore_engine::crypto::Cipher, StegError> {
    match s {
        "ascon-128" => Ok(stegcore_engine::crypto::Cipher::Ascon128),
        "chacha20-poly1305" => Ok(stegcore_engine::crypto::Cipher::ChaCha20Poly1305),
        "aes-256-gcm" => Ok(stegcore_engine::crypto::Cipher::Aes256Gcm),
        other => Err(StegError::UnsupportedFormat(format!(
            "unknown cipher: {other}"
        ))),
    }
}

/// Convert an engine `KeyFile` into the public `KeyFile` via JSON round-trip.
/// Both types serialise identically, so this is always safe.
#[cfg(engine)]
fn convert_keyfile(engine_kf: stegcore_engine::keyfile::KeyFile) -> Result<KeyFile, StegError> {
    let json = serde_json::to_vec(&engine_kf)?;
    let kf: KeyFile = serde_json::from_slice(&json)?;
    Ok(kf)
}

/// Convert a public `KeyFile` into the engine's `KeyFile` via JSON round-trip.
#[cfg(engine)]
fn to_engine_keyfile(kf: &KeyFile) -> Result<stegcore_engine::keyfile::KeyFile, StegError> {
    let json = serde_json::to_vec(kf)?;
    let engine_kf: stegcore_engine::keyfile::KeyFile = serde_json::from_slice(&json)?;
    Ok(engine_kf)
}

// ── Public API ───────────────────────────────────────────────────────────────

/// Score a cover file for embedding suitability. Returns 0.0–1.0.
#[cfg(engine)]
pub fn assess(path: &Path) -> Result<f64, StegError> {
    stegcore_engine::steg::assess(path).map_err(StegError::from)
}

#[cfg(not(engine))]
pub fn assess(_path: &Path) -> Result<f64, StegError> {
    Err(StegError::EngineAbsent)
}

/// Embed payload using adaptive mode.
#[cfg(engine)]
pub fn embed_adaptive(
    cover: &Path,
    payload: &[u8],
    passphrase: &[u8],
    cipher: &str,
    out: &Path,
    export_key: bool,
) -> Result<Option<KeyFile>, StegError> {
    let c = parse_cipher(cipher)?;
    let result =
        stegcore_engine::steg::embed(cover, payload, passphrase, c, "adaptive", out, export_key)
            .map_err(StegError::from)?;
    match result {
        Some(kf) => Ok(Some(convert_keyfile(kf)?)),
        None => Ok(None),
    }
}

#[cfg(not(engine))]
pub fn embed_adaptive(
    _cover: &Path,
    _payload: &[u8],
    _passphrase: &[u8],
    _cipher: &str,
    _out: &Path,
    _export_key: bool,
) -> Result<Option<KeyFile>, StegError> {
    Err(StegError::EngineAbsent)
}

/// Embed payload using sequential LSB mode.
#[cfg(engine)]
pub fn embed_sequential(
    cover: &Path,
    payload: &[u8],
    passphrase: &[u8],
    cipher: &str,
    out: &Path,
    export_key: bool,
) -> Result<Option<KeyFile>, StegError> {
    let c = parse_cipher(cipher)?;
    let result =
        stegcore_engine::steg::embed(cover, payload, passphrase, c, "sequential", out, export_key)
            .map_err(StegError::from)?;
    match result {
        Some(kf) => Ok(Some(convert_keyfile(kf)?)),
        None => Ok(None),
    }
}

#[cfg(not(engine))]
pub fn embed_sequential(
    _cover: &Path,
    _payload: &[u8],
    _passphrase: &[u8],
    _cipher: &str,
    _out: &Path,
    _export_key: bool,
) -> Result<Option<KeyFile>, StegError> {
    Err(StegError::EngineAbsent)
}

/// Embed payload into a WAV audio file (always sequential).
#[cfg(engine)]
pub fn embed_wav(
    cover: &Path,
    payload: &[u8],
    passphrase: &[u8],
    cipher: &str,
    out: &Path,
    export_key: bool,
) -> Result<Option<KeyFile>, StegError> {
    let c = parse_cipher(cipher)?;
    let result =
        stegcore_engine::steg::embed(cover, payload, passphrase, c, "sequential", out, export_key)
            .map_err(StegError::from)?;
    match result {
        Some(kf) => Ok(Some(convert_keyfile(kf)?)),
        None => Ok(None),
    }
}

#[cfg(not(engine))]
pub fn embed_wav(
    _cover: &Path,
    _payload: &[u8],
    _passphrase: &[u8],
    _cipher: &str,
    _out: &Path,
    _export_key: bool,
) -> Result<Option<KeyFile>, StegError> {
    Err(StegError::EngineAbsent)
}

/// Embed two independent payloads (deniable mode).
#[cfg(engine)]
pub fn embed_deniable(
    cover: &Path,
    real_payload: &[u8],
    decoy_payload: &[u8],
    real_pass: &[u8],
    decoy_pass: &[u8],
    cipher: &str,
    out: &Path,
) -> Result<(KeyFile, KeyFile), StegError> {
    let c = parse_cipher(cipher)?;
    let (real_kf, decoy_kf) = stegcore_engine::steg::embed_deniable(
        cover,
        real_payload,
        decoy_payload,
        real_pass,
        decoy_pass,
        c,
        out,
    )
    .map_err(StegError::from)?;
    Ok((convert_keyfile(real_kf)?, convert_keyfile(decoy_kf)?))
}

#[cfg(not(engine))]
pub fn embed_deniable(
    _cover: &Path,
    _real_payload: &[u8],
    _decoy_payload: &[u8],
    _real_pass: &[u8],
    _decoy_pass: &[u8],
    _cipher: &str,
    _out: &Path,
) -> Result<(KeyFile, KeyFile), StegError> {
    Err(StegError::EngineAbsent)
}

/// Extract hidden payload using only passphrase.
#[cfg(engine)]
pub fn extract(stego: &Path, passphrase: &[u8]) -> Result<Vec<u8>, StegError> {
    stegcore_engine::steg::extract(stego, passphrase).map_err(StegError::from)
}

#[cfg(not(engine))]
pub fn extract(_stego: &Path, _passphrase: &[u8]) -> Result<Vec<u8>, StegError> {
    Err(StegError::EngineAbsent)
}

/// Extract hidden payload using an external key file.
#[cfg(engine)]
pub fn extract_with_keyfile(
    stego: &Path,
    keyfile: &KeyFile,
    passphrase: &[u8],
) -> Result<Vec<u8>, StegError> {
    let engine_kf = to_engine_keyfile(keyfile)?;
    stegcore_engine::steg::extract_with_keyfile(stego, &engine_kf, passphrase)
        .map_err(StegError::from)
}

#[cfg(not(engine))]
pub fn extract_with_keyfile(
    _stego: &Path,
    _keyfile: &KeyFile,
    _passphrase: &[u8],
) -> Result<Vec<u8>, StegError> {
    Err(StegError::EngineAbsent)
}

/// Read the embedded metadata header without decrypting the payload.
#[cfg(engine)]
pub fn read_meta(path: &Path, passphrase: &[u8]) -> Result<serde_json::Value, StegError> {
    let json_str = stegcore_engine::steg::read_meta(path, passphrase).map_err(StegError::from)?;
    serde_json::from_str::<serde_json::Value>(&json_str).map_err(StegError::Json)
}

#[cfg(not(engine))]
pub fn read_meta(_path: &Path, _passphrase: &[u8]) -> Result<serde_json::Value, StegError> {
    Err(StegError::EngineAbsent)
}

#[cfg(test)]
mod tests {
    use super::*;

    // These tests run in both engine and stub mode.
    // In stub mode (CI), all calls must return EngineAbsent.
    // In engine mode (local), they return real results.

    #[cfg(not(engine))]
    mod stub_tests {
        use super::*;

        #[test]
        fn assess_returns_engine_absent() {
            let r = assess(Path::new("/tmp/any.png"));
            assert!(matches!(r, Err(StegError::EngineAbsent)));
        }

        #[test]
        fn embed_adaptive_returns_engine_absent() {
            let r = embed_adaptive(
                Path::new("/tmp/c.png"), b"data", b"pass", "chacha20-poly1305",
                Path::new("/tmp/o.png"), false,
            );
            assert!(matches!(r, Err(StegError::EngineAbsent)));
        }

        #[test]
        fn embed_sequential_returns_engine_absent() {
            let r = embed_sequential(
                Path::new("/tmp/c.png"), b"data", b"pass", "aes-256-gcm",
                Path::new("/tmp/o.png"), false,
            );
            assert!(matches!(r, Err(StegError::EngineAbsent)));
        }

        #[test]
        fn embed_wav_returns_engine_absent() {
            let r = embed_wav(
                Path::new("/tmp/c.wav"), b"data", b"pass", "ascon-128",
                Path::new("/tmp/o.wav"), false,
            );
            assert!(matches!(r, Err(StegError::EngineAbsent)));
        }

        #[test]
        fn embed_deniable_returns_engine_absent() {
            let r = embed_deniable(
                Path::new("/tmp/c.png"), b"real", b"decoy",
                b"rpass", b"dpass", "chacha20-poly1305",
                Path::new("/tmp/o.png"),
            );
            assert!(matches!(r, Err(StegError::EngineAbsent)));
        }

        #[test]
        fn extract_returns_engine_absent() {
            let r = extract(Path::new("/tmp/s.png"), b"pass");
            assert!(matches!(r, Err(StegError::EngineAbsent)));
        }

        #[test]
        fn extract_with_keyfile_returns_engine_absent() {
            let kf = KeyFile {
                engine: "rust-v1".into(), cipher: "chacha20-poly1305".into(),
                nonce: "dA==".into(), salt: "dA==".into(),
                deniable: false, partition_seed: None, partition_half: None,
            };
            let r = extract_with_keyfile(Path::new("/tmp/s.png"), &kf, b"pass");
            assert!(matches!(r, Err(StegError::EngineAbsent)));
        }

        #[test]
        fn read_meta_returns_engine_absent() {
            let r = read_meta(Path::new("/tmp/s.png"), b"pass");
            assert!(matches!(r, Err(StegError::EngineAbsent)));
        }
    }
}
