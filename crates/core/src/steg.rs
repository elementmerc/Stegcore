use std::path::Path;
use crate::errors::StegError;
use crate::keyfile::KeyFile;

// ── Cipher string → engine enum conversion ───────────────────────────────────

/// Parse a cipher identifier string into the engine's enum.
/// Accepted values: "ascon-128", "chacha20-poly1305", "aes-256-gcm".
#[cfg(engine)]
fn parse_cipher(s: &str) -> Result<stegcore_engine::crypto::Cipher, StegError> {
    match s {
        "ascon-128"         => Ok(stegcore_engine::crypto::Cipher::Ascon128),
        "chacha20-poly1305" => Ok(stegcore_engine::crypto::Cipher::ChaCha20Poly1305),
        "aes-256-gcm"       => Ok(stegcore_engine::crypto::Cipher::Aes256Gcm),
        other               => Err(StegError::UnsupportedFormat(format!("unknown cipher: {other}"))),
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
    let result = stegcore_engine::steg::embed(
        cover, payload, passphrase, c, "adaptive", out, export_key,
    ).map_err(StegError::from)?;
    match result {
        Some(kf) => Ok(Some(convert_keyfile(kf)?)),
        None => Ok(None),
    }
}

#[cfg(not(engine))]
pub fn embed_adaptive(
    _cover: &Path, _payload: &[u8], _passphrase: &[u8],
    _cipher: &str, _out: &Path, _export_key: bool,
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
    let result = stegcore_engine::steg::embed(
        cover, payload, passphrase, c, "sequential", out, export_key,
    ).map_err(StegError::from)?;
    match result {
        Some(kf) => Ok(Some(convert_keyfile(kf)?)),
        None => Ok(None),
    }
}

#[cfg(not(engine))]
pub fn embed_sequential(
    _cover: &Path, _payload: &[u8], _passphrase: &[u8],
    _cipher: &str, _out: &Path, _export_key: bool,
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
    let result = stegcore_engine::steg::embed(
        cover, payload, passphrase, c, "sequential", out, export_key,
    ).map_err(StegError::from)?;
    match result {
        Some(kf) => Ok(Some(convert_keyfile(kf)?)),
        None => Ok(None),
    }
}

#[cfg(not(engine))]
pub fn embed_wav(
    _cover: &Path, _payload: &[u8], _passphrase: &[u8],
    _cipher: &str, _out: &Path, _export_key: bool,
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
        cover, real_payload, decoy_payload, real_pass, decoy_pass, c, out,
    ).map_err(StegError::from)?;
    Ok((convert_keyfile(real_kf)?, convert_keyfile(decoy_kf)?))
}

#[cfg(not(engine))]
pub fn embed_deniable(
    _cover: &Path, _real_payload: &[u8], _decoy_payload: &[u8],
    _real_pass: &[u8], _decoy_pass: &[u8], _cipher: &str, _out: &Path,
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
    _stego: &Path, _keyfile: &KeyFile, _passphrase: &[u8],
) -> Result<Vec<u8>, StegError> {
    Err(StegError::EngineAbsent)
}

/// Read the embedded metadata header without decrypting the payload.
#[cfg(engine)]
pub fn read_meta(path: &Path, passphrase: &[u8]) -> Result<serde_json::Value, StegError> {
    let json_str = stegcore_engine::steg::read_meta(path, passphrase)
        .map_err(StegError::from)?;
    serde_json::from_str::<serde_json::Value>(&json_str).map_err(StegError::Json)
}

#[cfg(not(engine))]
pub fn read_meta(_path: &Path, _passphrase: &[u8]) -> Result<serde_json::Value, StegError> {
    Err(StegError::EngineAbsent)
}
