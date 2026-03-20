use serde::Serialize;

#[derive(thiserror::Error, Debug)]
pub enum StegError {
    #[error("Cover file is too small to hold this payload (need {required} bytes, have {available})")]
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
            E::InsufficientCapacity { required, available } => {
                StegError::InsufficientCapacity { required, available }
            }
            E::DecryptionFailed        => StegError::DecryptionFailed,
            E::LegacyKeyFile           => StegError::LegacyKeyFile,
            E::UnsupportedFormat(s)    => StegError::UnsupportedFormat(s),
            E::PoorCoverQuality { score } => StegError::PoorCoverQuality { score },
            E::FileNotFound(s)         => StegError::FileNotFound(s),
            E::EmptyPayload            => StegError::EmptyPayload,
            E::NoPayloadFound          => StegError::NoPayloadFound,
            E::CorruptedFile           => StegError::CorruptedFile,
            E::EngineAbsent            => StegError::EngineAbsent,
            E::Io(e)                   => StegError::Io(e),
            E::Image(e)               => StegError::Image(e.to_string()),
            E::Json(e)                 => StegError::Json(e),
        }
    }
}

/// Serialise to a plain string for Tauri IPC.
impl Serialize for StegError {
    fn serialize<S: serde::Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        s.serialize_str(&self.to_string())
    }
}
