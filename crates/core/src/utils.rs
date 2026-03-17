use std::path::Path;
use crate::errors::StegError;

/// All supported image file extensions (lowercase).
pub fn supported_image_extensions() -> &'static [&'static str] {
    &["png", "bmp", "jpg", "jpeg", "webp"]
}

/// All supported audio file extensions (lowercase).
pub fn supported_audio_extensions() -> &'static [&'static str] {
    &["wav", "flac"]
}

/// All supported extensions for embedding (FLAC is analyze/extract only).
pub fn supported_embed_extensions() -> &'static [&'static str] {
    &["png", "bmp", "jpg", "jpeg", "webp", "wav"]
}

/// All extensions accepted by the application (embed + analyze).
pub fn supported_extensions() -> Vec<&'static str> {
    let mut all: Vec<&'static str> = supported_image_extensions().to_vec();
    all.extend_from_slice(supported_audio_extensions());
    all
}

/// Detect canonical format string from file extension.
pub fn detect_format(path: &Path) -> Result<String, StegError> {
    let ext = path
        .extension()
        .and_then(|e| e.to_str())
        .map(|e| e.to_lowercase())
        .ok_or_else(|| StegError::UnsupportedFormat("(no extension)".to_string()))?;

    match ext.as_str() {
        "png" => Ok("png".to_string()),
        "bmp" => Ok("bmp".to_string()),
        "jpg" | "jpeg" => Ok("jpeg".to_string()),
        "webp" => Ok("webp".to_string()),
        "wav" => Ok("wav".to_string()),
        "flac" => Ok("flac".to_string()),
        other => Err(StegError::UnsupportedFormat(other.to_string())),
    }
}

/// Create a temporary file with the given suffix. Permissions: owner-only (0o600).
pub fn temp_file(_suffix: &str) -> Result<tempfile::NamedTempFile, StegError> {
    todo!("Session 3: implement temp_file")
}
