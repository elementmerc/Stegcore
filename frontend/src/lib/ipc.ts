import { invoke } from '@tauri-apps/api/core'

export type Cipher = 'ascon-128' | 'chacha20-poly1305' | 'aes-256-gcm'
export type EmbedMode = 'adaptive' | 'sequential'

export interface EmbedOptions {
  cover: string
  payload: string
  passphrase: string
  cipher: Cipher
  mode: EmbedMode
  deniable: boolean
  decoyPayload?: string
  decoyPassphrase?: string
  exportKey: boolean
  output: string
}

export interface EmbedResult {
  outputPath: string
  keyFilePath?: string
}

export interface ExtractOptions {
  stego: string
  passphrase: string
  keyFile?: string
}

export type TestConfidence = 'low' | 'medium' | 'high'
export type Verdict = 'clean' | 'suspicious' | 'likely_stego'

export interface TestResult {
  name: string
  score: number
  confidence: TestConfidence
  detail: string
}

export interface AnalysisReport {
  file: string
  format: string
  tests: TestResult[]
  verdict: Verdict
  overall_score: number
  tool_fingerprint: string | null
}

// ── Typed invoke() wrappers ──────────────────────────────────────────────

/** Returns the list of supported file extensions. */
export function getSupportedFormats(): Promise<string[]> {
  return invoke<string[]>('get_supported_formats')
}

/** Score a cover file for embedding suitability (0.0–1.0). */
export function scoreCover(path: string): Promise<number> {
  return invoke<number>('score_cover', { path })
}

/** Embed a payload into a cover file. */
export function embed(opts: EmbedOptions): Promise<EmbedResult> {
  return invoke<EmbedResult>('embed', {
    cover: opts.cover,
    payload: opts.payload,
    passphrase: opts.passphrase,
    cipher: opts.cipher,
    mode: opts.mode,
    deniable: opts.deniable,
    decoyPayload: opts.decoyPayload ?? null,
    decoyPassphrase: opts.decoyPassphrase ?? null,
    exportKey: opts.exportKey,
    output: opts.output,
  })
}

/** Extract hidden payload from a stego file. Returns raw bytes. */
export function extract(opts: ExtractOptions): Promise<Uint8Array> {
  return invoke<Uint8Array>('extract', {
    stego: opts.stego,
    passphrase: opts.passphrase,
    keyFile: opts.keyFile ?? null,
  })
}

/** Analyze a single file for hidden content. */
export function analyzeFile(path: string): Promise<AnalysisReport> {
  return invoke<AnalysisReport>('analyze_file', { path })
}

/** Analyze multiple files. */
export function analyzeBatchFiles(paths: string[]): Promise<Array<AnalysisReport | string>> {
  return invoke<Array<AnalysisReport | string>>('analyze_batch_files', { paths })
}

/** Export an HTML report for the given file paths. Returns HTML string. */
export function exportHtmlReport(paths: string[]): Promise<string> {
  return invoke<string>('export_html_report', { paths })
}
