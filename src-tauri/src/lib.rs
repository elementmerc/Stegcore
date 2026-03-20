use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use tauri::Manager;

use stegcore_core::{analysis, errors::StegError, steg, utils};

// ── Settings ─────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Settings {
    #[serde(default = "default_theme")]
    pub theme: String,
    #[serde(default)]
    pub reduce_motion: bool,
    #[serde(default = "default_cipher")]
    pub default_cipher: String,
    #[serde(default = "default_mode")]
    pub default_mode: String,
    #[serde(default)]
    pub default_output_folder: Option<String>,
    #[serde(default)]
    pub auto_export_key: bool,
    #[serde(default = "default_true")]
    pub auto_score_on_drop: bool,
    #[serde(default = "default_passphrase_min_len")]
    pub passphrase_min_len: u32,
    #[serde(default = "default_clear_clipboard_secs")]
    pub clear_clipboard_secs: u32,
    #[serde(default)]
    pub session_timeout_mins: u32,
    #[serde(default)]
    pub show_technical_errors: bool,
    #[serde(default = "default_report_format")]
    pub default_report_format: String,
    #[serde(default)]
    pub report_output_folder: Option<String>,
}

fn default_theme()             -> String { "system".into() }
fn default_cipher()            -> String { "chacha20-poly1305".into() }
fn default_mode()              -> String { "adaptive".into() }
fn default_true()              -> bool   { true }
fn default_passphrase_min_len()-> u32    { 12 }
fn default_clear_clipboard_secs()->u32  { 30 }
fn default_report_format()     -> String { "html".into() }

impl Default for Settings {
    fn default() -> Self {
        Settings {
            theme:                  default_theme(),
            reduce_motion:          false,
            default_cipher:         default_cipher(),
            default_mode:           default_mode(),
            default_output_folder:  None,
            auto_export_key:        false,
            auto_score_on_drop:     true,
            passphrase_min_len:     default_passphrase_min_len(),
            clear_clipboard_secs:   default_clear_clipboard_secs(),
            session_timeout_mins:   0,
            show_technical_errors:  false,
            default_report_format:  default_report_format(),
            report_output_folder:   None,
        }
    }
}

fn settings_path(app: &tauri::AppHandle) -> Option<PathBuf> {
    app.path().app_config_dir().ok().map(|d| d.join("settings.json"))
}

fn load_settings(app: &tauri::AppHandle) -> Settings {
    let Some(path) = settings_path(app) else { return Settings::default() };
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default()
}

fn save_settings(app: &tauri::AppHandle, s: &Settings) -> Result<(), StegError> {
    let Some(path) = settings_path(app) else {
        return Err(StegError::Io(std::io::Error::other(
            "Could not resolve app config directory",
        )));
    };
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(StegError::Io)?;
    }
    let json = serde_json::to_string_pretty(s).map_err(StegError::Json)?;
    std::fs::write(&path, json).map_err(StegError::Io)
}

// ── Tauri IPC commands ────────────────────────────────────────────────────────

#[tauri::command]
fn get_supported_formats() -> Vec<String> {
    utils::supported_extensions()
        .iter()
        .map(|s| s.to_string())
        .collect()
}

#[tauri::command]
fn score_cover(path: String) -> Result<f64, StegError> {
    steg::assess(Path::new(&path))
}

#[tauri::command]
#[allow(clippy::too_many_arguments)]
fn embed(
    cover:           String,
    payload:         String,
    passphrase:      String,
    cipher:          String,
    mode:            String,
    deniable:        bool,
    decoy_payload:   Option<String>,
    decoy_passphrase:Option<String>,
    export_key:      bool,
    output:          String,
) -> Result<serde_json::Value, StegError> {
    let cover_path   = Path::new(&cover);
    let out_path     = Path::new(&output);
    let pass_bytes   = passphrase.as_bytes();
    let payload_bytes= std::fs::read(Path::new(&payload)).map_err(StegError::Io)?;

    if deniable {
        let decoy_path = decoy_payload.as_deref().ok_or(StegError::EmptyPayload)?;
        let decoy_pass = decoy_passphrase.as_deref().unwrap_or("").as_bytes().to_vec();
        let decoy_bytes = std::fs::read(Path::new(decoy_path)).map_err(StegError::Io)?;

        let (real_kf, decoy_kf) = steg::embed_deniable(
            cover_path,
            &payload_bytes,
            &decoy_bytes,
            pass_bytes,
            &decoy_pass,
            &cipher,
            out_path,
        )?;

        let real_kf_path = format!("{}.real.json", output);
        let decoy_kf_path= format!("{}.decoy.json", output);
        stegcore_core::keyfile::write_key_file(Path::new(&real_kf_path), &real_kf)?;
        stegcore_core::keyfile::write_key_file(Path::new(&decoy_kf_path), &decoy_kf)?;

        return Ok(serde_json::json!({
            "outputPath":     output,
            "keyFilePath":    real_kf_path,
            "decoyKeyPath":   decoy_kf_path,
        }));
    }

    let maybe_kf = if mode == "sequential" {
        steg::embed_sequential(cover_path, &payload_bytes, pass_bytes, &cipher, out_path, export_key)?
    } else {
        steg::embed_adaptive(cover_path, &payload_bytes, pass_bytes, &cipher, out_path, export_key)?
    };

    let key_file_path = if export_key {
        if let Some(kf) = maybe_kf {
            let p = format!("{output}.json");
            stegcore_core::keyfile::write_key_file(Path::new(&p), &kf)?;
            Some(p)
        } else {
            None
        }
    } else {
        None
    };

    Ok(serde_json::json!({
        "outputPath":  output,
        "keyFilePath": key_file_path,
    }))
}

#[tauri::command]
fn extract(
    stego:      String,
    passphrase: String,
    key_file:   Option<String>,
) -> Result<Vec<u8>, StegError> {
    let stego_path = Path::new(&stego);
    let pass_bytes = passphrase.as_bytes();

    if let Some(kf_path) = key_file.as_deref() {
        let kf = stegcore_core::keyfile::read_key_file(Path::new(kf_path))?;
        steg::extract_with_keyfile(stego_path, &kf, pass_bytes)
    } else {
        steg::extract(stego_path, pass_bytes)
    }
}

#[tauri::command]
fn analyze_file(path: String) -> Result<analysis::AnalysisReport, StegError> {
    analysis::analyze(Path::new(&path))
}

#[tauri::command]
fn analyze_batch_files(
    paths: Vec<String>,
) -> Vec<Result<analysis::AnalysisReport, StegError>> {
    let path_refs: Vec<&Path> = paths.iter().map(|s| Path::new(s.as_str())).collect();
    analysis::analyze_batch(&path_refs)
}

#[tauri::command]
fn export_html_report(paths: Vec<String>) -> Result<String, StegError> {
    let path_refs: Vec<&Path> = paths.iter().map(|s| Path::new(s.as_str())).collect();
    let results = analysis::analyze_batch(&path_refs);
    let reports: Vec<analysis::AnalysisReport> = results
        .into_iter()
        .filter_map(|r| r.ok())
        .collect();
    Ok(analysis::generate_html_report(&reports))
}

#[tauri::command]
fn get_settings(app: tauri::AppHandle) -> Settings {
    load_settings(&app)
}

#[tauri::command]
fn set_settings(app: tauri::AppHandle, settings: Settings) -> Result<(), StegError> {
    save_settings(&app, &settings)
}

// ── App entry point ───────────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            get_supported_formats,
            score_cover,
            embed,
            extract,
            analyze_file,
            analyze_batch_files,
            export_html_report,
            get_settings,
            set_settings,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Stegcore");
}
