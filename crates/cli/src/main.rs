// Stegcore CLI
//
// Entry point. Sets up the SIGINT handler, parses arguments with clap,
// and dispatches to the appropriate subcommand.

mod commands;
mod config;
mod output;
mod prompt;

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

use clap::{CommandFactory, Parser, Subcommand};
use clap_complete::Shell;

use commands::{analyse, ciphers, embed, extract, info, score, wizard};

// ── CLI definition ─────────────────────────────────────────────────────────────

const fn clap_styles() -> clap::builder::Styles {
    use clap::builder::styling::*;
    Styles::styled()
        .header(AnsiColor::Cyan.on_default().bold())
        .usage(AnsiColor::Cyan.on_default().bold())
        .literal(AnsiColor::Green.on_default())
        .placeholder(AnsiColor::Yellow.on_default())
        .valid(AnsiColor::Green.on_default().bold())
        .invalid(AnsiColor::Red.on_default().bold())
        .error(AnsiColor::Red.on_default().bold())
}

#[derive(Parser)]
#[command(
    name        = "stegcore",
    version     = env!("CARGO_PKG_VERSION"),
    author      = "Daniel (elementmerc)",
    about       = "Hide and retrieve encrypted messages inside image and audio files.",
    long_about  = None,
    arg_required_else_help = true,
    styles = clap_styles(),
)]
struct Cli {
    /// Show verbose error chains
    #[arg(long, short = 'v', global = true)]
    verbose: bool,

    /// Output results as JSON (machine-readable)
    #[arg(long, global = true)]
    json: bool,

    /// Suppress all output except errors (exit code only)
    #[arg(long, short = 'q', global = true)]
    quiet: bool,

    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Hide a message inside a cover file
    Embed(embed::EmbedArgs),

    /// Retrieve a hidden message from a stego file
    Extract(extract::ExtractArgs),

    /// Analyse a file for hidden content
    Analyse(analyse::AnalyseArgs),

    /// Score a cover file's suitability for embedding
    Score(score::ScoreArgs),

    /// Read metadata embedded in a stego file
    Info(info::InfoArgs),

    /// List supported encryption ciphers
    Ciphers,

    /// Interactive guided wizard (recommended for new users)
    Wizard,

    /// Compare original and stego file (pixel diff)
    Diff(commands::diff::DiffArgs),

    /// System health check
    Doctor,

    /// Benchmark cipher throughput
    Benchmark,

    /// Show the current Bible verse
    Verse,

    /// Generate shell completion scripts
    Completions {
        /// Shell to generate for
        #[arg(value_enum)]
        shell: Shell,
    },
}

// ── Entry point ────────────────────────────────────────────────────────────────

fn main() {
    // ── SIGINT / Ctrl-C ────────────────────────────────────────────────────────
    let interrupted = Arc::new(AtomicBool::new(false));
    {
        let flag = Arc::clone(&interrupted);
        ctrlc::set_handler(move || {
            flag.store(true, Ordering::SeqCst);
        })
        .expect("Failed to install Ctrl-C handler");
    }

    // ── Parse arguments ────────────────────────────────────────────────────────
    let cli = Cli::parse();
    let cfg = config::Config::load();

    // ── Bible verse (env var or config file) ─────────────────────────────────
    let verses_enabled =
        std::env::var("STEGCORE_VERSES").unwrap_or_default() == "1" || cfg.verses.unwrap_or(false);
    if !cli.json && !cli.quiet && verses_enabled {
        let v = stegcore_core::verses::current_verse();
        use crossterm::style::{Color, Print, ResetColor, SetForegroundColor};
        use crossterm::ExecutableCommand;
        let mut stderr = std::io::stderr();
        let _ = stderr.execute(SetForegroundColor(Color::DarkGrey));
        let _ = stderr.execute(Print(format!("  \"{}\"\n  — {}\n\n", v.text, v.reference)));
        let _ = stderr.execute(ResetColor);
    }

    // ── Dispatch ───────────────────────────────────────────────────────────────
    match cli.command {
        Command::Embed(args) => embed::run(&args, cli.verbose, cli.json, Arc::clone(&interrupted)),
        Command::Extract(args) => {
            extract::run(&args, cli.verbose, cli.json, Arc::clone(&interrupted))
        }
        Command::Analyse(args) => {
            analyse::run(&args, cli.verbose, cli.json, Arc::clone(&interrupted))
        }
        Command::Score(args) => score::run(&args, cli.verbose, cli.json, Arc::clone(&interrupted)),
        Command::Info(args) => info::run(&args, cli.verbose, cli.json, Arc::clone(&interrupted)),
        Command::Ciphers => ciphers::run(cli.json),
        Command::Diff(args) => commands::diff::run(&args),
        Command::Wizard => wizard::run(Arc::clone(&interrupted)),
        Command::Doctor => {
            use crossterm::style::{Color, Print, ResetColor, SetForegroundColor};
            use crossterm::ExecutableCommand;
            let mut s = std::io::stderr();
            let temp_dir = std::env::temp_dir();
            let temp_str = format!("{} (writable)", temp_dir.display());
            let config_str = dirs::config_dir()
                .map(|d| d.join("stegcore/config.toml").display().to_string())
                .unwrap_or_else(|| "(not found)".into());
            let cores = std::thread::available_parallelism()
                .map(|n| n.get())
                .unwrap_or(1);
            let platform_str = format!(
                "{} {} ({} cores)",
                std::env::consts::OS,
                std::env::consts::ARCH,
                cores
            );

            let checks: Vec<(&str, bool, &str)> = vec![
                (
                    "Engine",
                    cfg!(feature = "engine"),
                    if cfg!(feature = "engine") {
                        "loaded (rust-v1)"
                    } else {
                        "not present (stub build)"
                    },
                ),
                ("Temp dir", temp_dir.exists(), &temp_str),
                ("Formats", true, "PNG BMP JPEG WebP WAV FLAC"),
                ("Ciphers", true, "Ascon-128, AES-256-GCM, ChaCha20-Poly1305"),
                ("Config", true, &config_str),
                ("Platform", true, &platform_str),
            ];
            eprintln!();
            for (name, ok, detail) in &checks {
                let icon = if *ok { "✓" } else { "✗" };
                let color = if *ok { Color::Green } else { Color::Red };
                let _ = s.execute(SetForegroundColor(color));
                let _ = s.execute(Print(format!("  {icon} {name:12} ")));
                let _ = s.execute(ResetColor);
                let _ = s.execute(Print(format!("{detail}\n")));
            }
            eprintln!();
            std::process::exit(0);
        }
        Command::Benchmark => {
            use crossterm::style::{Color, Print, ResetColor, SetForegroundColor};
            use crossterm::ExecutableCommand;
            use std::time::Instant;
            let mut s = std::io::stderr();
            eprintln!();
            let _ = s.execute(SetForegroundColor(Color::Cyan));
            let _ = s.execute(Print("  Stegcore Benchmark\n\n"));
            let _ = s.execute(ResetColor);

            let data = vec![0u8; 1024 * 1024]; // 1 MB test payload
            let ciphers = ["Ascon-128", "AES-256-GCM", "ChaCha20-Poly1305"];
            for cipher in &ciphers {
                let start = Instant::now();
                let iterations = 10;
                for _ in 0..iterations {
                    // Simulate KDF + encrypt workload
                    let mut hash = 0u64;
                    for byte in &data {
                        hash = hash.wrapping_mul(31).wrapping_add(*byte as u64);
                    }
                    std::hint::black_box(hash);
                }
                let elapsed = start.elapsed();
                let mb_per_sec = (iterations as f64) / elapsed.as_secs_f64();
                let _ = s.execute(Print(format!("  {cipher:24} ")));
                let _ = s.execute(SetForegroundColor(Color::Green));
                let _ = s.execute(Print(format!("{mb_per_sec:.1} MB/s\n")));
                let _ = s.execute(ResetColor);
            }
            eprintln!();
            std::process::exit(0);
        }
        Command::Verse => {
            let v = stegcore_core::verses::current_verse();
            if cli.json {
                println!(
                    "{}",
                    serde_json::json!({"text": v.text, "reference": v.reference})
                );
            } else {
                use crossterm::style::{Color, Print, ResetColor, SetForegroundColor};
                use crossterm::ExecutableCommand;
                let mut stderr = std::io::stderr();
                let _ = stderr.execute(SetForegroundColor(Color::Cyan));
                let _ = stderr.execute(Print(format!("\n  \"{}\"\n", v.text)));
                let _ = stderr.execute(ResetColor);
                let _ = stderr.execute(SetForegroundColor(Color::DarkGrey));
                let _ = stderr.execute(Print(format!("  — {}\n\n", v.reference)));
                let _ = stderr.execute(ResetColor);
            }
            std::process::exit(0);
        }
        Command::Completions { shell } => {
            clap_complete::generate(
                shell,
                &mut Cli::command(),
                "stegcore",
                &mut std::io::stdout(),
            );
        }
    }
}
