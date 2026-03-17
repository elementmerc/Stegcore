use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use crate::errors::StegError;

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

/// Analyze a single file for steganographic content.
pub fn analyze(_path: &Path) -> Result<AnalysisReport, StegError> {
    todo!("Session 5: implement analyze via FFI")
}

/// Analyze multiple files.
pub fn analyze_batch(paths: &[&Path]) -> Vec<Result<AnalysisReport, StegError>> {
    paths.iter().map(|p| analyze(p)).collect()
}

/// Generate a self-contained HTML report from a set of analysis results.
pub fn generate_html_report(_reports: &[AnalysisReport]) -> String {
    todo!("Session 5: implement HTML report generation")
}
