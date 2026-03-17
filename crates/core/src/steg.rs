use std::path::Path;
use crate::errors::StegError;
use crate::keyfile::KeyFile;

// ── Public API ──────────────────────────────────────────────────────────────

/// Score a cover file for embedding suitability. Returns 0.0–1.0.
pub fn assess(_path: &Path) -> Result<f64, StegError> {
    todo!("Session 5b: implement via lsc_assess FFI")
}

/// Embed payload into an image cover using adaptive mode.
pub fn embed_adaptive(
    _cover: &Path,
    _payload: &[u8],
    _passphrase: &[u8],
    _cipher: &str,
    _out: &Path,
    _export_key: bool,
) -> Result<Option<KeyFile>, StegError> {
    todo!("Session 5b: implement via lsc_embed FFI")
}

/// Embed payload into an image cover using sequential LSB mode.
pub fn embed_sequential(
    _cover: &Path,
    _payload: &[u8],
    _passphrase: &[u8],
    _cipher: &str,
    _out: &Path,
    _export_key: bool,
) -> Result<Option<KeyFile>, StegError> {
    todo!("Session 5b: implement via lsc_embed FFI")
}

/// Embed payload into a WAV audio file.
pub fn embed_wav(
    _cover: &Path,
    _payload: &[u8],
    _passphrase: &[u8],
    _cipher: &str,
    _out: &Path,
    _export_key: bool,
) -> Result<Option<KeyFile>, StegError> {
    todo!("Session 5b: implement via lsc_embed FFI")
}

/// Embed two independent payloads (deniable mode).
pub fn embed_deniable(
    _cover: &Path,
    _real_payload: &[u8],
    _decoy_payload: &[u8],
    _real_pass: &[u8],
    _decoy_pass: &[u8],
    _cipher: &str,
    _out: &Path,
) -> Result<(KeyFile, KeyFile), StegError> {
    todo!("Session 5b: implement via lsc_embed FFI")
}

/// Extract hidden payload using only passphrase (metadata embedded in file).
pub fn extract(_stego: &Path, _passphrase: &[u8]) -> Result<Vec<u8>, StegError> {
    todo!("Session 5b: implement via lsc_extract FFI")
}

/// Extract hidden payload using an external key file.
pub fn extract_with_keyfile(
    _stego: &Path,
    _keyfile: &KeyFile,
    _passphrase: &[u8],
) -> Result<Vec<u8>, StegError> {
    todo!("Session 5b: implement via lsc_extract FFI")
}
