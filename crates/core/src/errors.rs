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

    /// Returned when the prebuilt engine library is not present in this build.
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

/// Serialize to a plain string for Tauri IPC.
impl Serialize for StegError {
    fn serialize<S: serde::Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        s.serialize_str(&self.to_string())
    }
}
