use serde::{Deserialize, Serialize};
use std::path::Path;
use crate::errors::StegError;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KeyFile {
    pub engine: String,
    pub cipher: String,
    pub mode: String,
    pub nonce: String,
    pub salt: String,
    pub deniable: bool,
    pub partition_seed: Option<String>,
    pub partition_half: Option<u8>,
}

/// Write a key file to disk as JSON.
pub fn write_key_file(_path: &Path, _keyfile: &KeyFile) -> Result<(), StegError> {
    todo!("Session 1b/3: implement write_key_file")
}

/// Read a key file from disk, detecting legacy Python format.
pub fn read_key_file(_path: &Path) -> Result<KeyFile, StegError> {
    todo!("Session 1b/3: implement read_key_file")
}
