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

/// Maps an FFI return code to a `StegError`.
/// Any unrecognised negative code maps to `CorruptedFile` as a safe default.
pub fn from_ffi_code(code: i32) -> StegError {
    match code {
        -1  => StegError::InsufficientCapacity { required: 0, available: 0 },
        -2  => StegError::DecryptionFailed,
        -3  => StegError::LegacyKeyFile,
        -4  => StegError::UnsupportedFormat(String::new()),
        -5  => StegError::PoorCoverQuality { score: 0.0 },
        -6  => StegError::FileNotFound(String::new()),
        -7  => StegError::EmptyPayload,
        -8  => StegError::NoPayloadFound,
        -9  => StegError::CorruptedFile,
        -10 => StegError::Io(std::io::Error::new(std::io::ErrorKind::Other, "I/O error")),
        -11 => StegError::Image("image error".into()),
        -12 => StegError::CorruptedFile,
        -99 => StegError::EngineAbsent,
        _   => StegError::CorruptedFile,
    }
}

/// Serialize to a plain string for Tauri IPC.
impl Serialize for StegError {
    fn serialize<S: serde::Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        s.serialize_str(&self.to_string())
    }
}
