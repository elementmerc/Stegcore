use std::path::PathBuf;
use std::sync::Arc;

use stegcore_core::steg;

use crate::output::{self, JsonOut, Spinner};
use crate::prompt;

#[derive(Debug, clap::Args)]
pub struct EmbedArgs {
    /// Cover file (PNG, BMP, JPEG, WAV, WebP)
    pub cover: PathBuf,
    /// Message file to hide
    pub payload: PathBuf,
    /// Output stego file path
    pub output: PathBuf,

    /// Embedding mode
    #[arg(long, default_value = "adaptive", value_parser = ["adaptive", "sequential"])]
    pub mode: String,

    /// Cipher to use
    #[arg(long, default_value = "chacha20-poly1305",
          value_parser = ["chacha20-poly1305", "ascon-128", "aes-256-gcm"])]
    pub cipher: String,

    /// Passphrase (omit to be prompted securely)
    #[arg(long, env = "STEGCORE_PASSPHRASE")]
    pub passphrase: Option<String>,

    /// Enable deniable dual-payload mode
    #[arg(long)]
    pub deniable: bool,

    /// Decoy message file (required when --deniable is set)
    #[arg(long, requires = "deniable")]
    pub decoy: Option<PathBuf>,

    /// Decoy passphrase (omit to be prompted when --deniable is set)
    #[arg(long, requires = "deniable", env = "STEGCORE_DECOY_PASSPHRASE")]
    pub decoy_passphrase: Option<String>,

    /// Export a .json key file alongside the output
    #[arg(long)]
    pub export_key: bool,
}

pub fn run(
    args: &EmbedArgs,
    verbose: bool,
    json: bool,
    interrupted: Arc<std::sync::atomic::AtomicBool>,
) -> ! {
    // ── Validate inputs ───────────────────────────────────────────────────────
    if !args.cover.exists() {
        let e = stegcore_core::errors::StegError::FileNotFound(
            args.cover.display().to_string(),
        );
        if json {
            output::emit_json(&JsonOut::<()>::failure(&e.to_string()), output::exit_code(&e));
        }
        output::die(&e, verbose);
    }
    if !args.payload.exists() {
        let e = stegcore_core::errors::StegError::FileNotFound(
            args.payload.display().to_string(),
        );
        if json {
            output::emit_json(&JsonOut::<()>::failure(&e.to_string()), output::exit_code(&e));
        }
        output::die(&e, verbose);
    }
    if args.deniable {
        match &args.decoy {
            None => {
                output::print_error("--deniable requires --decoy <file>", None);
                std::process::exit(1);
            }
            Some(p) if !p.exists() => {
                let e = stegcore_core::errors::StegError::FileNotFound(p.display().to_string());
                if json { output::emit_json(&JsonOut::<()>::failure(&e.to_string()), 3); }
                output::die(&e, verbose);
            }
            _ => {}
        }
    }

    // ── Read payload ──────────────────────────────────────────────────────────
    let payload_bytes = match std::fs::read(&args.payload) {
        Ok(b) if b.is_empty() => {
            let e = stegcore_core::errors::StegError::EmptyPayload;
            if json { output::emit_json(&JsonOut::<()>::failure(&e.to_string()), 1); }
            output::die(&e, verbose);
        }
        Ok(b) => b,
        Err(e) => {
            let err = stegcore_core::errors::StegError::Io(e);
            if json { output::emit_json(&JsonOut::<()>::failure(&err.to_string()), 3); }
            output::die(&err, verbose);
        }
    };

    // ── Passphrases ───────────────────────────────────────────────────────────
    let passphrase = match &args.passphrase {
        Some(p) => p.as_bytes().to_vec(),
        None    => prompt::prompt_passphrase_confirmed("Passphrase", &interrupted),
    };
    if passphrase.is_empty() {
        output::print_error("Passphrase cannot be empty.", None);
        std::process::exit(1);
    }

    // ── Embed ─────────────────────────────────────────────────────────────────
    let spinner = Spinner::new("Embedding…", Arc::clone(&interrupted));

    if args.deniable {
        let decoy_path = args.decoy.as_ref().unwrap();
        let decoy_bytes = match std::fs::read(decoy_path) {
            Ok(b) if b.is_empty() => {
                drop(spinner);
                let e = stegcore_core::errors::StegError::EmptyPayload;
                if json { output::emit_json(&JsonOut::<()>::failure(&e.to_string()), 1); }
                output::die(&e, verbose);
            }
            Ok(b) => b,
            Err(e) => {
                drop(spinner);
                let err = stegcore_core::errors::StegError::Io(e);
                if json { output::emit_json(&JsonOut::<()>::failure(&err.to_string()), 3); }
                output::die(&err, verbose);
            }
        };
        let decoy_pass = match &args.decoy_passphrase {
            Some(p) => p.as_bytes().to_vec(),
            None    => prompt::prompt_passphrase_confirmed("Decoy passphrase", &interrupted),
        };
        if decoy_pass.is_empty() {
            drop(spinner);
            output::print_error("Decoy passphrase cannot be empty.", None);
            std::process::exit(1);
        }

        match steg::embed_deniable(
            &args.cover, &payload_bytes, &decoy_bytes,
            &passphrase, &decoy_pass, &args.cipher, &args.output,
        ) {
            Ok((real_kf, decoy_kf)) => {
                // Write both key files alongside output.
                let real_path  = args.output.with_extension("real.json");
                let decoy_path = args.output.with_extension("decoy.json");
                let _ = stegcore_core::keyfile::write_key_file(&real_path,  &real_kf);
                let _ = stegcore_core::keyfile::write_key_file(&decoy_path, &decoy_kf);
                spinner.success(&format!(
                    "Embedded (deniable) → {}",
                    args.output.display()
                ));
                output::print_info(&format!("Real key file  → {}", real_path.display()));
                output::print_info(&format!("Decoy key file → {}", decoy_path.display()));
                if json {
                    #[derive(serde::Serialize)]
                    struct Out { output: String, real_key: String, decoy_key: String }
                    output::emit_json(
                        &JsonOut::success(Out {
                            output:    args.output.display().to_string(),
                            real_key:  real_path.display().to_string(),
                            decoy_key: decoy_path.display().to_string(),
                        }),
                        0,
                    );
                }
                std::process::exit(0);
            }
            Err(e) => {
                spinner.fail(&e.to_string());
                if json { output::emit_json(&JsonOut::<()>::failure(&e.to_string()), output::exit_code(&e)); }
                if verbose { output::print_error(&e.to_string(), Some(&format!("{e:#}"))); } else { output::print_error(&e.to_string(), None); }
                std::process::exit(output::exit_code(&e));
            }
        }
    }

    // Non-deniable embed (adaptive or sequential).
    let embed_fn = if args.mode == "sequential" {
        steg::embed_sequential
    } else {
        steg::embed_adaptive
    };

    match embed_fn(
        &args.cover, &payload_bytes, &passphrase,
        &args.cipher, &args.output, args.export_key,
    ) {
        Ok(kf_opt) => {
            let key_path = kf_opt.as_ref().and_then(|kf| {
                let p = args.output.with_extension("json");
                stegcore_core::keyfile::write_key_file(&p, kf).ok()?;
                Some(p)
            });
            spinner.success(&format!("Embedded → {}", args.output.display()));
            if let Some(ref kp) = key_path {
                output::print_info(&format!("Key file → {}", kp.display()));
            }
            if json {
                #[derive(serde::Serialize)]
                struct Out { output: String, #[serde(skip_serializing_if = "Option::is_none")] key_file: Option<String> }
                output::emit_json(
                    &JsonOut::success(Out {
                        output: args.output.display().to_string(),
                        key_file: key_path.map(|p| p.display().to_string()),
                    }),
                    0,
                );
            }
            std::process::exit(0);
        }
        Err(e) => {
            spinner.fail(&e.to_string());
            if json { output::emit_json(&JsonOut::<()>::failure(&e.to_string()), output::exit_code(&e)); }
            if verbose { output::print_error(&e.to_string(), Some(&format!("{e:#}"))); } else { output::print_error(&e.to_string(), None); }
            std::process::exit(output::exit_code(&e));
        }
    }
}
