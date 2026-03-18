// ── Safe invoke — degrades to mock when Tauri is unavailable (browser dev) ──

async function safeInvoke<T>(cmd: string, args?: unknown, mock?: T): Promise<T> {
  try {
    const { invoke } = await import('@tauri-apps/api/core')
    return await invoke<T>(cmd, args as Record<string, unknown>)
  } catch (e) {
    if (mock !== undefined) return mock
    throw e
  }
}

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

// ── Mock responses for dev mode ─────────────────────────────────────────

const MOCK_REPORT: AnalysisReport = {
  file: '/mock/image.png',
  format: 'PNG',
  tests: [
    { name: 'Chi-Squared', score: 0.12, confidence: 'high', detail: 'LSB histogram within expected range' },
    { name: 'Sample Pair Analysis', score: 0.08, confidence: 'medium', detail: 'No fill ratio anomaly detected' },
    { name: 'RS Analysis', score: 0.11, confidence: 'high', detail: 'R/S ratio ≈ 1.0 — no asymmetry' },
    { name: 'LSB Entropy', score: 0.09, confidence: 'medium', detail: 'Entropy consistent with natural image noise' },
  ],
  verdict: 'clean',
  overall_score: 0.10,
  tool_fingerprint: null,
}

// ── Typed invoke() wrappers ──────────────────────────────────────────────

/** Returns the list of supported file extensions. */
export function getSupportedFormats(): Promise<string[]> {
  return safeInvoke<string[]>('get_supported_formats', undefined, ['png', 'bmp', 'jpg', 'jpeg', 'wav', 'webp', 'flac'])
}

/** Score a cover file for embedding suitability (0.0–1.0). */
export function scoreCover(path: string): Promise<number> {
  return safeInvoke<number>('score_cover', { path }, 0.72)
}

/** Embed a payload into a cover file. */
export function embed(opts: EmbedOptions): Promise<EmbedResult> {
  return safeInvoke<EmbedResult>('embed', {
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
  }, { outputPath: '/mock/output.png' })
}

/** Extract hidden payload from a stego file. Returns raw bytes. */
export function extract(opts: ExtractOptions): Promise<Uint8Array> {
  return safeInvoke<Uint8Array>('extract', {
    stego: opts.stego,
    passphrase: opts.passphrase,
    keyFile: opts.keyFile ?? null,
  }, new TextEncoder().encode('Hello from Stegcore (mock)'))
}

/** Analyze a single file for hidden content. */
export function analyzeFile(path: string): Promise<AnalysisReport> {
  return safeInvoke<AnalysisReport>('analyze_file', { path }, { ...MOCK_REPORT, file: path })
}

/** Analyze multiple files. */
export function analyzeBatchFiles(paths: string[]): Promise<Array<AnalysisReport | string>> {
  return safeInvoke<Array<AnalysisReport | string>>(
    'analyze_batch_files',
    { paths },
    paths.map((p) => ({ ...MOCK_REPORT, file: p })),
  )
}

/** Export an HTML report for the given file paths. Returns HTML string. */
export function exportHtmlReport(paths: string[]): Promise<string> {
  return safeInvoke<string>('export_html_report', { paths }, '<html><body><p>Mock report</p></body></html>')
}

// ── Settings ─────────────────────────────────────────────────────────────

export interface Settings {
  theme?: 'dark' | 'light' | 'system'
  reduceMotion?: boolean
  defaultCipher?: Cipher
  defaultMode?: EmbedMode
  defaultOutputFolder?: string
  autoExportKey?: boolean
  autoScoreOnDrop?: boolean
  passphraseMinLen?: number
  clearClipboardSecs?: number
  sessionTimeoutMins?: number
  showTechnicalErrors?: boolean
  defaultReportFormat?: 'html' | 'json' | 'csv'
  reportOutputFolder?: string
}

/** Load persisted settings from the Tauri app config dir. */
export function getSettings(): Promise<Settings> {
  return safeInvoke<Settings>('get_settings', undefined, {})
}

/** Persist a partial settings update. */
export function setSettings(partial: Partial<Settings>): Promise<void> {
  return safeInvoke<void>('set_settings', { settings: partial }, undefined)
}

// ── Aliases for sprint naming consistency ────────────────────────────────

export const analyzeBatch = analyzeBatchFiles

export function exportReport(paths: string[], format: 'html' | 'json' | 'csv' = 'html'): Promise<string> {
  if (format === 'html') return exportHtmlReport(paths)
  return safeInvoke<string>('export_report', { paths, format }, `[mock ${format} report]`)
}
