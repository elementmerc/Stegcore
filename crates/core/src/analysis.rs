use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use crate::errors::StegError;

// ── Types (mirrored from libstegcore) ─────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum Verdict {
    Clean,
    Suspicious,
    LikelyStego,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Confidence {
    Low,
    Medium,
    High,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestResult {
    pub name: String,
    pub score: f64,
    pub confidence: Confidence,
    pub detail: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalysisReport {
    pub file: PathBuf,
    pub format: String,
    pub tests: Vec<TestResult>,
    pub verdict: Verdict,
    pub overall_score: f64,
    pub tool_fingerprint: Option<String>,
}

// ── Public API ───────────────────────────────────────────────────────────────

/// Analyse a single file for steganographic content.
#[cfg(engine)]
pub fn analyze(path: &Path) -> Result<AnalysisReport, StegError> {
    let json_str = stegcore_engine::analysis::analyze(path)
        .map_err(StegError::from)?;
    serde_json::from_str::<AnalysisReport>(&json_str).map_err(StegError::Json)
}

#[cfg(not(engine))]
pub fn analyze(_path: &Path) -> Result<AnalysisReport, StegError> {
    Err(StegError::EngineAbsent)
}

/// Analyse multiple files.
pub fn analyze_batch(paths: &[&Path]) -> Vec<Result<AnalysisReport, StegError>> {
    paths.iter().map(|p| analyze(p)).collect()
}

/// Generate a self-contained HTML report from a set of analysis results.
pub fn generate_html_report(reports: &[AnalysisReport]) -> String {
    let rows: String = reports.iter().map(render_report_row).collect();

    format!(
        r#"<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stegcore Analysis Report</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Ubuntu, sans-serif;
          background: #070d14; color: #e8eaf0; margin: 0; padding: 2rem; }}
  h1   {{ font-size: 1.5rem; font-weight: 500; letter-spacing: 0.1em; margin-bottom: 2rem; }}
  .file-block {{ background: #0d1520; border: 1px solid #1a2535; border-radius: 12px;
                  padding: 1.5rem; margin-bottom: 1.5rem; }}
  .file-name {{ font-size: 1rem; font-weight: 600; margin-bottom: 0.25rem; }}
  .file-meta {{ font-size: 0.8rem; color: #4a5568; margin-bottom: 1rem; }}
  .verdict {{ display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.3rem 0.8rem;
               border-radius: 6px; font-size: 0.85rem; font-weight: 600; margin-bottom: 1rem; }}
  .verdict-clean      {{ background: rgba(34,197,94,0.15); color: #22c55e; }}
  .verdict-suspicious {{ background: rgba(245,158,11,0.15); color: #f59e0b; }}
  .verdict-stego      {{ background: rgba(239,68,68,0.15);  color: #ef4444; }}
  .fingerprint {{ font-size: 0.8rem; color: #4a5568; margin-bottom: 1rem; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  th    {{ text-align: left; color: #4a5568; font-weight: 500; padding: 0.4rem 0.5rem;
            border-bottom: 1px solid #1a2535; }}
  td    {{ padding: 0.5rem; border-bottom: 1px solid #1a253544; vertical-align: middle; }}
  .bar-bg  {{ background: #1a2535; border-radius: 4px; height: 6px; width: 140px; overflow: hidden; }}
  .bar-fill {{ height: 100%; border-radius: 4px; }}
  .conf-low  {{ color: #4a5568; }} .conf-med {{ color: #f59e0b; }} .conf-high {{ color: #ef4444; }}
</style>
</head>
<body>
<h1>STEGCORE — Analysis Report</h1>
{rows}
</body>
</html>"#,
        rows = rows,
    )
}

// ── Internal HTML helpers ─────────────────────────────────────────────────────

fn render_report_row(r: &AnalysisReport) -> String {
    let verdict_class = match r.verdict {
        Verdict::Clean       => "verdict-clean",
        Verdict::Suspicious  => "verdict-suspicious",
        Verdict::LikelyStego => "verdict-stego",
    };
    let verdict_label = match r.verdict {
        Verdict::Clean       => "✓ Clean",
        Verdict::Suspicious  => "⚠ Suspicious",
        Verdict::LikelyStego => "✗ Likely Stego",
    };
    let fp = r.tool_fingerprint
        .as_deref()
        .map(|s| format!("<p class=\"fingerprint\">Signature: {}</p>", html_escape(s)))
        .unwrap_or_default();

    let test_rows: String = r.tests.iter().map(render_test_row).collect();

    format!(
        r#"<div class="file-block">
  <div class="file-name">{file}</div>
  <div class="file-meta">Format: {fmt} &nbsp;|&nbsp; Overall score: {score:.2}</div>
  <div class="verdict {vclass}">{vlabel}</div>
  {fp}
  <table>
    <tr><th>Detector</th><th>Score</th><th>Confidence</th><th>Detail</th></tr>
    {test_rows}
  </table>
</div>"#,
        file   = html_escape(&r.file.display().to_string()),
        fmt    = html_escape(&r.format),
        score  = r.overall_score,
        vclass = verdict_class,
        vlabel = verdict_label,
        fp     = fp,
        test_rows = test_rows,
    )
}

fn render_test_row(t: &TestResult) -> String {
    let score_pct = (t.score * 100.0).round() as u32;
    let bar_colour = score_colour(t.score);
    let conf_class = match t.confidence {
        Confidence::Low    => "conf-low",
        Confidence::Medium => "conf-med",
        Confidence::High   => "conf-high",
    };
    let conf_label = match t.confidence {
        Confidence::Low    => "Low",
        Confidence::Medium => "Medium",
        Confidence::High   => "High",
    };
    format!(
        r#"<tr>
  <td>{name}</td>
  <td>
    <div class="bar-bg">
      <div class="bar-fill" style="width:{pct}%;background:{colour}"></div>
    </div>
    <span style="font-size:0.75rem;color:#4a5568">{pct}%</span>
  </td>
  <td class="{cclass}">{clabel}</td>
  <td style="color:#4a5568">{detail}</td>
</tr>"#,
        name   = html_escape(&t.name),
        pct    = score_pct,
        colour = bar_colour,
        cclass = conf_class,
        clabel = conf_label,
        detail = html_escape(&t.detail),
    )
}

fn score_colour(score: f64) -> &'static str {
    if score < 0.25 {
        "#22c55e"
    } else if score < 0.55 {
        "#f59e0b"
    } else {
        "#ef4444"
    }
}

fn html_escape(s: &str) -> String {
    s.replace('&', "&amp;")
     .replace('<', "&lt;")
     .replace('>', "&gt;")
     .replace('"', "&quot;")
}
