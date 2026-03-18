use std::path::PathBuf;
use std::sync::Arc;

use stegcore_core::analysis::{self, AnalysisReport, Verdict};

use crate::output::{self, JsonOut, Spinner};

#[derive(Debug, clap::Args)]
pub struct AnalyzeArgs {
    /// File to analyse (omit when using --batch)
    pub file: Option<PathBuf>,

    /// Glob pattern for batch analysis (e.g. "*.png")
    #[arg(long)]
    pub batch: Option<String>,

    /// Report format
    #[arg(long, default_value = "table",
          value_parser = ["table", "html", "json", "csv"])]
    pub report: String,

    /// Output path for the report file (required for html/csv; optional for json)
    #[arg(long, short = 'o')]
    pub output: Option<PathBuf>,
}

pub fn run(
    args: &AnalyzeArgs,
    verbose: bool,
    json: bool,
    interrupted: Arc<std::sync::atomic::AtomicBool>,
) -> ! {
    // ── Collect paths ─────────────────────────────────────────────────────────
    let paths: Vec<PathBuf> = collect_paths(args, verbose, json);

    if paths.is_empty() {
        output::print_error("No files to analyse. Provide a file argument or --batch <glob>.", None);
        std::process::exit(1);
    }

    // ── Run analysis ──────────────────────────────────────────────────────────
    let spinner = Spinner::new(
        &format!("Analysing {} file(s)…", paths.len()),
        Arc::clone(&interrupted),
    );

    let path_refs: Vec<&std::path::Path> = paths.iter().map(PathBuf::as_path).collect();
    let results = analysis::analyze_batch(&path_refs);
    drop(spinner);

    let reports: Vec<AnalysisReport> = results
        .into_iter()
        .enumerate()
        .filter_map(|(i, r)| match r {
            Ok(rep) => Some(rep),
            Err(e) => {
                output::print_warn(&format!(
                    "{}: {}",
                    paths[i].display(),
                    e
                ));
                if verbose {
                    output::print_info(&format!("{e:#}"));
                }
                None
            }
        })
        .collect();

    if reports.is_empty() {
        output::print_error("All files failed to analyse.", None);
        std::process::exit(1);
    }

    // ── Output ────────────────────────────────────────────────────────────────
    match args.report.as_str() {
        "table" => {
            if json {
                let data: Vec<serde_json::Value> = reports
                    .iter()
                    .map(|r| serde_json::to_value(r).unwrap_or_default())
                    .collect();
                output::emit_json(&JsonOut::success(data), 0);
            }
            print_table(&reports);
            std::process::exit(0);
        }
        "html" => {
            let html = analysis::generate_html_report(&reports);
            save_or_print(&html, args.output.as_deref(), "report.html", verbose, json);
        }
        "json" => {
            let body = serde_json::to_string_pretty(&reports)
                .unwrap_or_else(|_| "[]".into());
            save_or_print(&body, args.output.as_deref(), "report.json", verbose, json);
        }
        "csv" => {
            let csv = build_csv(&reports);
            save_or_print(&csv, args.output.as_deref(), "report.csv", verbose, json);
        }
        _ => unreachable!(),
    }

    std::process::exit(0);
}

// ── helpers ───────────────────────────────────────────────────────────────────

fn collect_paths(args: &AnalyzeArgs, verbose: bool, json: bool) -> Vec<PathBuf> {
    let mut paths = Vec::new();

    if let Some(f) = &args.file {
        if f.exists() {
            paths.push(f.clone());
        } else {
            let e = stegcore_core::errors::StegError::FileNotFound(f.display().to_string());
            if json { output::emit_json(&JsonOut::<()>::failure(&e.to_string()), 3); }
            output::die(&e, verbose);
        }
    }

    if let Some(pattern) = &args.batch {
        match glob::glob(pattern) {
            Ok(entries) => {
                for entry in entries.flatten() {
                    if entry.is_file() {
                        paths.push(entry);
                    }
                }
            }
            Err(e) => {
                output::print_error(&format!("Invalid glob pattern: {e}"), None);
                std::process::exit(1);
            }
        }
    }

    paths
}

fn save_or_print(
    content: &str,
    out: Option<&std::path::Path>,
    default_name: &str,
    verbose: bool,
    json: bool,
) {
    let path = out
        .map(|p| p.to_path_buf())
        .unwrap_or_else(|| PathBuf::from(default_name));

    if let Err(e) = std::fs::write(&path, content) {
        let err = stegcore_core::errors::StegError::Io(e);
        if json { output::emit_json(&JsonOut::<()>::failure(&err.to_string()), 3); }
        output::die(&err, verbose);
    }
    output::print_success(&format!("Report saved → {}", path.display()));
    if json {
        #[derive(serde::Serialize)]
        struct Out { report: String }
        output::emit_json(&JsonOut::success(Out { report: path.display().to_string() }), 0);
    }
}

fn verdict_str(v: &Verdict) -> &'static str {
    match v {
        Verdict::Clean       => "Clean",
        Verdict::Suspicious  => "Suspicious",
        Verdict::LikelyStego => "Likely stego",
    }
}

fn print_table(reports: &[AnalysisReport]) {
    for r in reports {
        let verdict = verdict_str(&r.verdict);
        let colour = match r.verdict {
            Verdict::Clean       => crossterm::style::Color::Green,
            Verdict::Suspicious  => crossterm::style::Color::Yellow,
            Verdict::LikelyStego => crossterm::style::Color::Red,
        };
        use crossterm::style::{Print, ResetColor, SetForegroundColor};
        use crossterm::ExecutableCommand;
        let mut stderr = std::io::stderr();
        let _ = stderr.execute(SetForegroundColor(colour));
        let _ = stderr.execute(Print(format!(
            "{} — {} (score: {:.2})\n",
            r.file.display(),
            verdict,
            r.overall_score
        )));
        let _ = stderr.execute(ResetColor);

        for t in &r.tests {
            eprintln!(
                "  {:20} {:5.2}  {}",
                t.name, t.score, t.detail
            );
        }
        if let Some(fp) = &r.tool_fingerprint {
            eprintln!("  Signature: {fp}");
        }
        eprintln!();
    }
}

fn build_csv(reports: &[AnalysisReport]) -> String {
    let mut out = String::from("file,format,verdict,score,fingerprint\n");
    for r in reports {
        out.push_str(&format!(
            "{},{},{},{:.4},{}\n",
            csv_escape(&r.file.display().to_string()),
            csv_escape(&r.format),
            verdict_str(&r.verdict),
            r.overall_score,
            csv_escape(r.tool_fingerprint.as_deref().unwrap_or("")),
        ));
    }
    out
}

fn csv_escape(s: &str) -> String {
    if s.contains(',') || s.contains('"') || s.contains('\n') {
        format!("\"{}\"", s.replace('"', "\"\""))
    } else {
        s.to_owned()
    }
}
