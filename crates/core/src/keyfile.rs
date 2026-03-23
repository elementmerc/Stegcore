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
use serde::{Deserialize, Serialize};
use std::path::Path;

/// Optional export format. Stego files are self-contained; this is only
/// produced when the user explicitly requests key file export.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KeyFile {
    pub engine: String,
    /// Cipher identifier string (e.g. "chacha20-poly1305").
    pub cipher: String,
    /// Base64-encoded nonce.
    pub nonce: String,
    /// Base64-encoded salt.
    pub salt: String,
    pub deniable: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub partition_seed: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub partition_half: Option<u8>,
}

/// Write a key file to disk as JSON with restricted permissions (0o600 on Unix).
pub fn write_key_file(path: &Path, keyfile: &KeyFile) -> Result<(), StegError> {
    let json = serde_json::to_string_pretty(keyfile)?;
    std::fs::write(path, json).map_err(StegError::Io)?;

    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let perms = std::fs::Permissions::from_mode(0o600);
        std::fs::set_permissions(path, perms).map_err(StegError::Io)?;
    }
    Ok(())
}

/// Read a key file from disk, detecting legacy Python format.
pub fn read_key_file(path: &Path) -> Result<KeyFile, StegError> {
    if !path.exists() {
        return Err(StegError::FileNotFound(path.display().to_string()));
    }
    let raw = std::fs::read(path).map_err(StegError::Io)?;

    // Detect legacy Python key files: they lack the "engine" field.
    let probe: serde_json::Value =
        serde_json::from_slice(&raw).map_err(|_| StegError::CorruptedFile)?;
    if probe.get("engine").is_none() {
        return Err(StegError::LegacyKeyFile);
    }
    let engine = probe["engine"].as_str().unwrap_or("");
    if !engine.starts_with("rust-") {
        return Err(StegError::LegacyKeyFile);
    }

    let kf: KeyFile = serde_json::from_slice(&raw)?;
    Ok(kf)
}
