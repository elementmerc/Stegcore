// Coloured terminal output, RAII spinner, exit-code mapping.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

use crossterm::style::{Color, Print, ResetColor, SetForegroundColor};
use crossterm::ExecutableCommand;
use indicatif::{ProgressBar, ProgressStyle};
use stegcore_core::errors::StegError;

// ── Colours ───────────────────────────────────────────────────────────────────

pub fn print_success(msg: &str) {
    let mut stderr = std::io::stderr();
    let _ = stderr.execute(SetForegroundColor(Color::Green));
    let _ = stderr.execute(Print(format!("✓ {msg}\n")));
    let _ = stderr.execute(ResetColor);
}

pub fn print_error(msg: &str, chain: Option<&str>) {
    let mut stderr = std::io::stderr();
    let _ = stderr.execute(SetForegroundColor(Color::Red));
    let _ = stderr.execute(Print(format!("✗ Error: {msg}\n")));
    let _ = stderr.execute(ResetColor);
    if let Some(c) = chain {
        let _ = stderr.execute(SetForegroundColor(Color::DarkGrey));
        let _ = stderr.execute(Print(format!("  {c}\n")));
        let _ = stderr.execute(ResetColor);
    }
}

pub fn print_warn(msg: &str) {
    let mut stderr = std::io::stderr();
    let _ = stderr.execute(SetForegroundColor(Color::Yellow));
    let _ = stderr.execute(Print(format!("⚠  Warning: {msg}\n")));
    let _ = stderr.execute(ResetColor);
}

pub fn print_info(msg: &str) {
    let mut stderr = std::io::stderr();
    let _ = stderr.execute(SetForegroundColor(Color::Cyan));
    let _ = stderr.execute(Print(format!("  {msg}\n")));
    let _ = stderr.execute(ResetColor);
}

// ── Exit codes ────────────────────────────────────────────────────────────────

pub fn exit_code(e: &StegError) -> i32 {
    match e {
        StegError::InsufficientCapacity { .. }
        | StegError::EmptyPayload
        | StegError::LegacyKeyFile
        | StegError::PoorCoverQuality { .. }
        | StegError::FileTooLarge { .. }
        | StegError::EngineAbsent => 1,

        StegError::DecryptionFailed | StegError::NoPayloadFound => 2,

        StegError::Io(_) | StegError::FileNotFound(_) => 3,

        StegError::UnsupportedFormat(_)
        | StegError::CorruptedFile
        | StegError::Image(_)
        | StegError::Json(_) => 4,
    }
}

/// Print a `StegError` with optional verbose chain, then exit.
pub fn die(e: &StegError, verbose: bool) -> ! {
    let chain = if verbose {
        Some(format!("{e:#}"))
    } else {
        None
    };
    print_error(&e.to_string(), chain.as_deref());
    if let Some(hint) = e.suggestion() {
        print_info(&format!("Suggestion: {hint}"));
    }
    std::process::exit(exit_code(e));
}

// ── RAII Spinner ──────────────────────────────────────────────────────────────

pub struct Spinner {
    pb: ProgressBar,
    #[allow(dead_code)]
    interrupted: Arc<AtomicBool>,
}

impl Spinner {
    pub fn new(msg: &str, interrupted: Arc<AtomicBool>) -> Self {
        let pb = ProgressBar::new_spinner();
        pb.set_style(
            ProgressStyle::with_template("{spinner:.cyan} {msg}")
                .unwrap()
                .tick_strings(&["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]),
        );
        pb.set_message(msg.to_owned());
        pb.enable_steady_tick(std::time::Duration::from_millis(80));
        Spinner { pb, interrupted }
    }

    /// Check if Ctrl-C was pressed; if so, clean up and exit 130.
    #[allow(dead_code)]
    pub fn check_interrupt(&self) {
        if self.interrupted.load(Ordering::SeqCst) {
            self.pb.finish_and_clear();
            eprintln!();
            std::process::exit(130);
        }
    }

    pub fn success(self, msg: &str) {
        self.pb.finish_and_clear();
        print_success(msg);
    }

    pub fn fail(self, msg: &str) {
        self.pb.finish_and_clear();
        let mut stderr = std::io::stderr();
        let _ = stderr.execute(SetForegroundColor(Color::Red));
        let _ = stderr.execute(Print(format!("✗ {msg}\n")));
        let _ = stderr.execute(ResetColor);
    }
}

impl Drop for Spinner {
    fn drop(&mut self) {
        // Ensure spinner never leaks if the owner panics or returns early.
        self.pb.finish_and_clear();
    }
}

// ── JSON output helper ────────────────────────────────────────────────────────

use serde::Serialize;

#[derive(Serialize)]
pub struct JsonOut<T: Serialize> {
    pub ok: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<T>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

impl<T: Serialize> JsonOut<T> {
    pub fn success(data: T) -> Self {
        JsonOut {
            ok: true,
            data: Some(data),
            error: None,
        }
    }
    pub fn failure(msg: &str) -> JsonOut<T> {
        JsonOut {
            ok: false,
            data: None,
            error: Some(msg.to_owned()),
        }
    }
}

pub fn emit_json<T: Serialize>(v: &JsonOut<T>, code: i32) -> ! {
    println!(
        "{}",
        serde_json::to_string_pretty(v).unwrap_or_else(|_| "{}".into())
    );
    std::process::exit(code);
}
