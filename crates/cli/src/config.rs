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
