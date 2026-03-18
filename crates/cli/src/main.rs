// Stegcore CLI — session 6
//
// Entry point. Sets up the SIGINT handler, parses arguments with clap,
// and dispatches to the appropriate subcommand.

mod commands;
mod output;
mod prompt;

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

use clap::{Parser, Subcommand};

use commands::{analyze, ciphers, embed, extract, info, score, wizard};

// ── CLI definition ─────────────────────────────────────────────────────────────

#[derive(Parser)]
#[command(
    name        = "stegcore",
    version     = env!("CARGO_PKG_VERSION"),
    author      = "Daniel (elementmerc)",
    about       = "Hide and retrieve encrypted messages inside image and audio files.",
    long_about  = None,
    arg_required_else_help = true,
)]
struct Cli {
    /// Show verbose error chains
    #[arg(long, short = 'v', global = true)]
    verbose: bool,

    /// Output results as JSON (machine-readable)
    #[arg(long, global = true)]
    json: bool,

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
    Analyze(analyze::AnalyzeArgs),

    /// Score a cover file's suitability for embedding
    Score(score::ScoreArgs),

    /// Read metadata embedded in a stego file
    Info(info::InfoArgs),

    /// List supported encryption ciphers
    Ciphers,

    /// Interactive guided wizard (recommended for new users)
    Wizard,
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

    // ── Dispatch ───────────────────────────────────────────────────────────────
    match cli.command {
        Command::Embed(args) => {
            embed::run(&args, cli.verbose, cli.json, Arc::clone(&interrupted))
        }
        Command::Extract(args) => {
            extract::run(&args, cli.verbose, cli.json, Arc::clone(&interrupted))
        }
        Command::Analyze(args) => {
            analyze::run(&args, cli.verbose, cli.json, Arc::clone(&interrupted))
        }
        Command::Score(args) => {
            score::run(&args, cli.verbose, cli.json, Arc::clone(&interrupted))
        }
        Command::Info(args) => {
            info::run(&args, cli.verbose, cli.json, Arc::clone(&interrupted))
        }
        Command::Ciphers => {
            ciphers::run(cli.json)
        }
        Command::Wizard => {
            wizard::run(Arc::clone(&interrupted))
        }
    }
}
