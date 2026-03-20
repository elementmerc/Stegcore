// Passphrase prompting and file-picker helpers.

use std::io::{self, BufRead, Write};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

// ── Display detection ─────────────────────────────────────────────────────────

/// Returns true when a graphical display is available.
pub fn has_display() -> bool {
    // Linux / BSD: DISPLAY (X11) or WAYLAND_DISPLAY
    if std::env::var_os("DISPLAY").is_some()
        || std::env::var_os("WAYLAND_DISPLAY").is_some()
    {
        return true;
    }
    // macOS and Windows always have a display when running interactively.
    cfg!(target_os = "macos") || cfg!(target_os = "windows")
}

// ── File picker ───────────────────────────────────────────────────────────────

pub struct PickerConfig<'a> {
    pub title: &'a str,
    pub filters: &'a [(&'a str, &'a [&'a str])], // (name, extensions)
}

/// Pick a single file. Uses a native file dialog when a display is available;
/// falls back to a stdin path prompt otherwise, with an explanation.
pub fn pick_file(cfg: &PickerConfig<'_>) -> Option<PathBuf> {
    if has_display() {
        #[cfg(not(target_os = "linux"))]
        {
            let mut dialog = rfd::FileDialog::new().set_title(cfg.title);
            for (name, exts) in cfg.filters {
                dialog = dialog.add_filter(*name, exts);
            }
            return dialog.pick_file();
        }
        // On Linux rfd may still fail if running in a terminal without dbus.
        // Fall through to the stdin path below if rfd returns None.
        #[cfg(target_os = "linux")]
        {
            let mut dialog = rfd::FileDialog::new().set_title(cfg.title);
            for (name, exts) in cfg.filters {
                dialog = dialog.add_filter(*name, exts);
            }
            if let Some(p) = dialog.pick_file() {
                return Some(p);
            }
            eprintln!(
                "ℹ  No graphical file picker available — please type the path manually."
            );
        }
    } else {
        eprintln!(
            "ℹ  No display detected (headless/SSH environment). \
             A graphical file picker is not available — please type the path manually."
        );
    }
    read_path_from_stdin(cfg.title)
}

/// Prompt for a directory path. Same display-availability logic as `pick_file`.
#[allow(dead_code)]
pub fn pick_folder(title: &str) -> Option<PathBuf> {
    if has_display() {
        #[cfg(not(target_os = "linux"))]
        {
            return rfd::FileDialog::new().set_title(title).pick_folder();
        }
        #[cfg(target_os = "linux")]
        {
            if let Some(p) = rfd::FileDialog::new().set_title(title).pick_folder() {
                return Some(p);
            }
            eprintln!("ℹ  No graphical file picker — please type the path manually.");
        }
    }
    read_path_from_stdin(title)
}

fn read_path_from_stdin(prompt: &str) -> Option<PathBuf> {
    let stdin = io::stdin();
    print!("  {}: ", prompt);
    let _ = io::stdout().flush();
    let mut line = String::new();
    match stdin.lock().read_line(&mut line) {
        Ok(0) | Err(_) => None,
        Ok(_) => {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                None
            } else {
                Some(PathBuf::from(trimmed))
            }
        }
    }
}

// ── Passphrase prompting ──────────────────────────────────────────────────────

/// Prompt for a passphrase securely (no echo).
///
/// If `interrupted` is set (Ctrl-C handler) during the prompt, exits 130.
pub fn prompt_passphrase(label: &str, interrupted: &Arc<AtomicBool>) -> Vec<u8> {
    if interrupted.load(Ordering::SeqCst) {
        eprintln!();
        std::process::exit(130);
    }
    match rpassword::prompt_password(format!("  {label}: ")) {
        Ok(s) => s.into_bytes(),
        Err(e) => {
            eprintln!("✗ Failed to read passphrase: {e}");
            std::process::exit(1);
        }
    }
}

/// Prompt for a passphrase with confirmation (used during embed).
/// Re-prompts until both entries match or the user hits Ctrl-C.
pub fn prompt_passphrase_confirmed(
    label: &str,
    interrupted: &Arc<AtomicBool>,
) -> Vec<u8> {
    loop {
        if interrupted.load(Ordering::SeqCst) {
            eprintln!();
            std::process::exit(130);
        }
        let first = match rpassword::prompt_password(format!("  {label}: ")) {
            Ok(s) => s,
            Err(e) => {
                eprintln!("✗ Failed to read passphrase: {e}");
                std::process::exit(1);
            }
        };
        if first.is_empty() {
            eprintln!("  ⚠  Passphrase cannot be empty. Please try again.");
            continue;
        }
        let second = match rpassword::prompt_password(format!("  Confirm {label}: ")) {
            Ok(s) => s,
            Err(e) => {
                eprintln!("✗ Failed to read passphrase: {e}");
                std::process::exit(1);
            }
        };
        if first == second {
            return first.into_bytes();
        }
        eprintln!("  ✗ Passphrases do not match. Please try again.");
    }
}

// ── Stdin helpers for wizard ──────────────────────────────────────────────────

/// Read a single trimmed line from stdin. Returns `None` on EOF.
pub fn read_line(prompt: &str) -> Option<String> {
    print!("  {prompt}: ");
    let _ = io::stdout().flush();
    let mut line = String::new();
    match io::stdin().lock().read_line(&mut line) {
        Ok(0) | Err(_) => None,
        Ok(_) => Some(line.trim().to_owned()),
    }
}

/// Read a yes/no answer. Accepts y/yes/n/no (case-insensitive).
/// Re-prompts on invalid input. Returns `None` on EOF.
pub fn read_yes_no(prompt: &str, default: Option<bool>) -> Option<bool> {
    let hint = match default {
        Some(true)  => " [Y/n]",
        Some(false) => " [y/N]",
        None        => " [y/n]",
    };
    loop {
        print!("  {prompt}{hint}: ");
        let _ = io::stdout().flush();
        let mut line = String::new();
        match io::stdin().lock().read_line(&mut line) {
            Ok(0) | Err(_) => return None,
            Ok(_) => {}
        }
        match line.trim().to_lowercase().as_str() {
            "y" | "yes" => return Some(true),
            "n" | "no"  => return Some(false),
            "" => {
                if let Some(d) = default {
                    return Some(d);
                }
                eprintln!("  Please enter y or n.");
            }
            _ => eprintln!("  Please enter y or n."),
        }
    }
}

/// Read a menu choice (1-based) from stdin. Re-prompts on out-of-range input.
pub fn read_menu(prompt: &str, options: &[&str]) -> Option<usize> {
    for (i, opt) in options.iter().enumerate() {
        println!("  {}. {}", i + 1, opt);
    }
    loop {
        let answer = read_line(prompt)?;
        match answer.trim().parse::<usize>() {
            Ok(n) if n >= 1 && n <= options.len() => return Some(n - 1),
            _ => eprintln!(
                "  Please enter a number between 1 and {}.",
                options.len()
            ),
        }
    }
}
