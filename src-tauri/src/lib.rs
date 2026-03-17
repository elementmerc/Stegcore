use stegcore_core::{analysis, errors::StegError, utils};

// ── Tauri IPC commands ──────────────────────────────────────────────────────

#[tauri::command]
fn get_supported_formats() -> Vec<String> {
    utils::supported_extensions()
        .iter()
        .map(|s| s.to_string())
        .collect()
}

#[tauri::command]
fn score_cover(path: String) -> Result<f64, StegError> {
    stegcore_core::steg::assess(std::path::Path::new(&path))
}

#[tauri::command]
fn embed(
    _cover: String,
    _payload: String,
    _passphrase: String,
    _cipher: String,
    _mode: String,
    _deniable: bool,
    _decoy_payload: Option<String>,
    _decoy_passphrase: Option<String>,
    _export_key: bool,
    _output: String,
) -> Result<serde_json::Value, StegError> {
    todo!("Session 6: implement embed Tauri command")
}

#[tauri::command]
fn extract(
    _stego: String,
    _passphrase: String,
    _key_file: Option<String>,
) -> Result<Vec<u8>, StegError> {
    todo!("Session 6: implement extract Tauri command")
}

#[tauri::command]
fn analyze_file(path: String) -> Result<analysis::AnalysisReport, StegError> {
    analysis::analyze(std::path::Path::new(&path))
}

#[tauri::command]
fn analyze_batch_files(
    paths: Vec<String>,
) -> Vec<Result<analysis::AnalysisReport, StegError>> {
    let path_refs: Vec<&std::path::Path> =
        paths.iter().map(|s| std::path::Path::new(s.as_str())).collect();
    analysis::analyze_batch(&path_refs)
}

#[tauri::command]
fn export_html_report(_paths: Vec<String>) -> Result<String, StegError> {
    todo!("Session 6: implement HTML report export command")
}

// ── App entry point ─────────────────────────────────────────────────────────

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
        ])
        .run(tauri::generate_context!())
        .expect("error while running Stegcore");
}
