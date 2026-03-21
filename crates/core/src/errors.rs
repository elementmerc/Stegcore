use serde::Serialize;

#[derive(thiserror::Error, Debug)]
pub enum StegError {
    #[error(
        "Cover file is too small to hold this payload (need {required} bytes, have {available})"
    )]
    InsufficientCapacity { required: usize, available: usize },

    #[error("Wrong passphrase or corrupted stego file")]
    DecryptionFailed,

    #[error("This file was created with an older version of Stegcore and cannot be used here")]
    LegacyKeyFile,

    #[error("Unsupported file format: {0}")]
    UnsupportedFormat(String),

    #[error("Cover file is not suitable for embedding")]
    PoorCoverQuality { score: f64 },

    #[error("File not found: {0}")]
    FileNotFound(String),

    #[error("Payload file is empty")]
    EmptyPayload,

    /// Same user-facing text as DecryptionFailed — prevents oracle attacks.
    #[error("Wrong passphrase or corrupted stego file")]
    NoPayloadFound,

    #[error("Invalid or corrupted stego file")]
    CorruptedFile,

    #[error("File is too large ({size_mb} MB). Maximum supported size is {max_mb} MB.")]
    FileTooLarge { size_mb: u64, max_mb: u64 },

    /// Returned when the engine feature is not compiled into this build.
    #[error(
        "The steganographic engine is not present in this build. \
         Download a prebuilt release from the releases page."
    )]
    EngineAbsent,

    #[error(transparent)]
    Io(#[from] std::io::Error),

    #[error("Image error: {0}")]
    Image(String),

    #[error(transparent)]
    Json(#[from] serde_json::Error),
}

/// Convert from the engine's error type into the public error type.
/// This replaces the old `from_ffi_code()` integer-based mapping with
/// a proper Rust enum-to-enum conversion.
#[cfg(engine)]
impl From<stegcore_engine::errors::StegError> for StegError {
    fn from(e: stegcore_engine::errors::StegError) -> Self {
        use stegcore_engine::errors::StegError as E;
        match e {
            E::InsufficientCapacity {
                required,
                available,
            } => StegError::InsufficientCapacity {
                required,
                available,
            },
            E::DecryptionFailed => StegError::DecryptionFailed,
            E::LegacyKeyFile => StegError::LegacyKeyFile,
            E::UnsupportedFormat(s) => StegError::UnsupportedFormat(s),
            E::PoorCoverQuality { score } => StegError::PoorCoverQuality { score },
            E::FileNotFound(s) => StegError::FileNotFound(s),
            E::EmptyPayload => StegError::EmptyPayload,
            E::NoPayloadFound => StegError::NoPayloadFound,
            E::CorruptedFile => StegError::CorruptedFile,
            E::EngineAbsent => StegError::EngineAbsent,
            E::Io(e) => StegError::Io(e),
            E::Image(e) => StegError::Image(e.to_string()),
            E::Json(e) => StegError::Json(e),
        }
    }
}

impl StegError {
    /// Actionable suggestion for the user. Helps them recover from the error
    /// instead of just showing "something went wrong".
    pub fn suggestion(&self) -> Option<&'static str> {
        match self {
            StegError::InsufficientCapacity { .. } => Some(
                "Try a larger cover file, switch to sequential mode (+30% capacity), or compress your payload first.",
            ),
            StegError::DecryptionFailed | StegError::NoPayloadFound => Some(
                "Double-check your passphrase. If using a key file, ensure it matches the stego file.",
            ),
            StegError::PoorCoverQuality { .. } => Some(
                "Use a high-resolution photo with natural texture (landscapes, cityscapes work well). Avoid flat-colour or synthetic images.",
            ),
            StegError::EmptyPayload => Some(
                "The payload file is empty. Check the file path and ensure it contains data.",
            ),
            StegError::UnsupportedFormat(_) => Some(
                "Supported formats: PNG, BMP, JPEG, WebP, WAV. FLAC is supported for analysis and extraction only.",
            ),
            StegError::FileTooLarge { .. } => Some(
                "Cover files up to 2 GB and payloads up to 500 MB are supported. Try a smaller file.",
            ),
            StegError::CorruptedFile => Some(
                "The file may be truncated or damaged. Try re-downloading or using a different file.",
            ),
            StegError::EngineAbsent => Some(
                "This build does not include the steganographic engine. Download a prebuilt release from GitHub.",
            ),
            StegError::LegacyKeyFile => Some(
                "This key file was created by an older version. Re-embed with the current version to generate a compatible key file.",
            ),
            _ => None,
        }
    }
}

/// Serialise to a plain string for Tauri IPC.
impl Serialize for StegError {
    fn serialize<S: serde::Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        s.serialize_str(&self.to_string())
    }
}
