// Copyright (C) 2026 Daniel Iwugo — elementmerc
// SPDX-License-Identifier: AGPL-3.0-or-later OR LicenseRef-Stegcore-Commercial
//
// This file is part of Stegcore. Stegcore is free software: you can
// redistribute it and/or modify it under the terms of the GNU Affero
// General Public License as published by the Free Software Foundation,
// either version 3 of the License, or (at your option) any later version.
//
// Commercial licensing: daniel@themalwarefiles.com

//! CLI configuration file support.
//!
//! Reads `~/.config/stegcore/config.toml` (Linux/macOS) or
//! `%APPDATA%/stegcore/config.toml` (Windows). Values act as defaults
//! that CLI flags override.

use serde::Deserialize;
use std::path::PathBuf;

#[derive(Debug, Default, Deserialize)]
#[serde(default)]
pub struct Config {
    pub default_cipher: Option<String>,
    pub default_mode: Option<String>,
    pub default_output_folder: Option<String>,
    pub export_key: Option<bool>,
    pub verbose: Option<bool>,
    pub verses: Option<bool>,
}

impl Config {
    /// Load config from the platform-specific path. Returns defaults if
    /// the file doesn't exist or can't be parsed.
    pub fn load() -> Self {
        let Some(path) = config_path() else {
            return Self::default();
        };
        let Ok(content) = std::fs::read_to_string(&path) else {
            return Self::default();
        };
        toml::from_str(&content).unwrap_or_default()
    }
}

fn config_path() -> Option<PathBuf> {
    dirs::config_dir().map(|d| d.join("stegcore").join("config.toml"))
}
