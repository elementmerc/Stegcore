import { useState, useCallback } from 'react'
import { ShieldCheck, ShieldAlert, ShieldX, FileDown, ChevronDown, ChevronUp, ScanSearch } from 'lucide-react'
import { DropZone } from '../components/DropZone'
import { useFooter } from '../App'
import { analyzeBatch, exportReport } from '../lib/ipc'
import { useSettingsStore } from '../lib/stores/settingsStore'
import type { AnalysisReport, Verdict } from '../lib/ipc'

// ── Verdict helpers ───────────────────────────────────────────────────────

const VERDICT_CONFIG: Record<Verdict, { icon: React.ReactNode; label: string; color: string }> = {
  clean:        { icon: <ShieldCheck size={18} />,  label: 'Clean',                   color: 'var(--ui-success)' },
  suspicious:   { icon: <ShieldAlert size={18} />,  label: 'Suspicious',              color: 'var(--ui-warn)'    },
  likely_stego: { icon: <ShieldX size={18} />,      label: 'Likely Contains Hidden Data', color: 'var(--ui-danger)' },
}

function VerdictBadge({ verdict, large = false }: { verdict: Verdict; large?: boolean }) {
  const { icon, label, color } = VERDICT_CONFIG[verdict]
  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      padding: large ? '8px 18px' : '4px 12px',
      borderRadius: large ? 10 : 20,
      background: `color-mix(in srgb, ${color} 15%, var(--ui-surface))`,
      border: `1.5px solid color-mix(in srgb, ${color} 40%, transparent)`,
      color,
      fontSize: large ? 15 : 13,
      fontWeight: large ? 700 : 500,
    }}>
      {icon}
      <span>{label}</span>
    </div>
  )
}

// ── Score bar ─────────────────────────────────────────────────────────────

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color = score < 0.25 ? 'var(--ui-success)' : score < 0.55 ? 'var(--ui-warn)' : 'var(--ui-danger)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
      <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'var(--ui-border)', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, borderRadius: 3, background: color, transition: 'width var(--sc-t-base)' }} />
      </div>
      <span style={{ fontSize: 11, color: 'var(--ui-text2)', width: 30, textAlign: 'right', fontFamily: "'Space Mono', monospace" }}>{pct}%</span>
    </div>
  )
}

// ── Single file result card ───────────────────────────────────────────────

function ResultCard({ report }: { report: AnalysisReport }) {
  const [expanded, setExpanded] = useState(false)
  const fileName = report.file.split('/').pop() ?? report.file

  return (
    <div style={{
      background: 'var(--ui-surface)',
      border: '1px solid var(--ui-border)',
      borderRadius: 10,
      overflow: 'hidden',
      marginBottom: '0.75rem',
    }}>
      {/* Summary row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--ui-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{fileName}</p>
          <p style={{ fontSize: 11, color: 'var(--ui-text2)' }}>{report.format}</p>
        </div>

        {report.tool_fingerprint && (
          <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 20, background: 'color-mix(in srgb, var(--ui-warn) 15%, var(--ui-surface))', color: 'var(--ui-warn)', whiteSpace: 'nowrap' }}>
            {report.tool_fingerprint}
          </span>
        )}

        <VerdictBadge verdict={report.verdict} />

        <button
          onClick={() => setExpanded(v => !v)}
          aria-label={expanded ? 'Collapse' : 'Expand'}
          style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--ui-text2)', display: 'flex', alignItems: 'center', flexShrink: 0 }}
        >
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      {/* Detector rows */}
      {expanded && (
        <div style={{ borderTop: '1px solid var(--ui-border)', padding: '12px 16px' }}>
          {report.tests.map((t) => (
            <div key={t.name} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
              <span style={{ fontSize: 12, color: 'var(--ui-text2)', width: 180, flexShrink: 0 }}>{t.name}</span>
              <ScoreBar score={t.score} />
              <span style={{ fontSize: 11, color: 'var(--ui-text2)', width: 40, textAlign: 'right', flexShrink: 0, textTransform: 'capitalize' }}>{t.confidence}</span>
            </div>
          ))}

          {/* What does this mean? */}
          <ExplainSection verdict={report.verdict} />
        </div>
      )}
    </div>
  )
}

function ExplainSection({ verdict }: { verdict: Verdict }) {
  const [open, setOpen] = useState(false)

  const text = {
    clean: 'No significant anomalies were detected in this file. It shows normal statistical properties consistent with an unmodified file.',
    suspicious: 'Some anomalies were detected that could indicate hidden content, but the result is inconclusive. This could be a false positive.',
    likely_stego: 'Multiple detectors found strong evidence of hidden content in this file. It is likely that data has been embedded using a steganographic tool.',
  }[verdict]

  return (
    <div style={{ marginTop: 8 }}>
      <button
        onClick={() => setOpen(v => !v)}
        style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: 'var(--ui-accent)', background: 'transparent', border: 'none', cursor: 'pointer', padding: 0 }}
      >
        {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        What does this mean?
      </button>
      {open && (
        <p style={{ marginTop: 6, fontSize: 12, color: 'var(--ui-text2)', lineHeight: 1.6, paddingLeft: 17 }}>
          {text}
        </p>
      )}
    </div>
  )
}

// ── Analyze route ─────────────────────────────────────────────────────────

export default function Analyze() {
  const [files, setFiles] = useState<File[]>([])
  const [reports, setReports] = useState<AnalysisReport[]>([])
  const [errors, setErrors] = useState<string[]>([])
  const [running, setRunning] = useState(false)
  const [sortKey, setSortKey] = useState<'score' | 'name'>('score')
  const [filterVerdict, setFilterVerdict] = useState<Verdict | 'all'>('all')
  const { settings } = useSettingsStore()
  useFooter({
    backLabel: 'Home',
    backAction: () => { window.history.back() },
    steps: undefined,
    currentStep: undefined,
  })

  const handleFiles = useCallback((dropped: File[]) => {
    setFiles(prev => {
      const names = new Set(prev.map(f => f.name))
      return [...prev, ...dropped.filter(f => !names.has(f.name))]
    })
  }, [])

  const handleAnalyze = useCallback(async () => {
    if (!files.length) return
    setRunning(true)
    setReports([])
    setErrors([])
    try {
      const paths = files.map(f => f.name)
      const results = await analyzeBatch(paths)
      const ok: AnalysisReport[] = []
      const errs: string[] = []
      for (const r of results) {
        if (typeof r === 'string') errs.push(r)
        else ok.push(r)
      }
      setReports(ok)
      setErrors(errs)
    } finally {
      setRunning(false)
    }
  }, [files])

  const handleExport = useCallback(async () => {
    if (!reports.length) return
    const paths = reports.map(r => r.file)
    try {
      const content = await exportReport(paths, settings.defaultReportFormat)
      const blob = new Blob([content], { type: 'text/html' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `stegcore-report.${settings.defaultReportFormat}`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      // silently ignore in dev
    }
  }, [reports, settings.defaultReportFormat])

  const sortedReports = [...reports].sort((a, b) =>
    sortKey === 'score'
      ? b.overall_score - a.overall_score
      : a.file.localeCompare(b.file)
  ).filter(r => filterVerdict === 'all' || r.verdict === filterVerdict)

  return (
    <div style={{ maxWidth: 700, margin: '0 auto', padding: '2rem 1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: '0.5rem' }}>
        <span style={{ color: 'var(--ui-accent)' }}><ScanSearch size={20} /></span>
        <h2 style={{ fontSize: 20, fontWeight: 600, color: 'var(--ui-text)' }}>Analyse</h2>
      </div>
      <p style={{ fontSize: 13, color: 'var(--ui-text2)', marginBottom: '1.5rem' }}>
        Drop one or more files to scan for hidden content.
      </p>

      <DropZone
        accept={['.png', '.bmp', '.jpg', '.jpeg', '.webp', '.wav', '.flac']}
        onFiles={handleFiles}
        multiple
        label="Drop files to analyse"
        sublabel={files.length > 0 ? `${files.length} file${files.length > 1 ? 's' : ''} selected` : 'PNG, BMP, JPEG, WebP, WAV, FLAC'}
      />

      {/* File list */}
      {files.length > 0 && (
        <div style={{ marginTop: 10 }}>
          {files.map((f, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid var(--ui-border)', fontSize: 12 }}>
              <span style={{ color: 'var(--ui-text)' }}>{f.name}</span>
              <button
                onClick={() => setFiles(prev => prev.filter((_, j) => j !== i))}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--ui-text2)', fontSize: 12, padding: 0 }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Analyse button */}
      <button
        onClick={handleAnalyze}
        disabled={!files.length || running}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 8,
          width: '100%',
          marginTop: '1rem',
          padding: '11px',
          background: 'var(--ui-accent)',
          border: 'none',
          borderRadius: 'var(--sc-radius-btn)',
          color: '#ffffff',
          fontSize: 14,
          fontWeight: 600,
          cursor: !files.length || running ? 'default' : 'pointer',
          opacity: !files.length || running ? 0.45 : 1,
          transition: 'opacity var(--sc-t-fast)',
        }}
      >
        {running ? 'Analysing…' : `Analyse ${files.length > 0 ? `${files.length} file${files.length > 1 ? 's' : ''}` : ''}`}
      </button>

      {/* Results */}
      {reports.length > 0 && (
        <div style={{ marginTop: '1.75rem' }}>
          {/* Toolbar */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={{ fontSize: 12, color: 'var(--ui-text2)' }}>Sort:</span>
              {(['score', 'name'] as const).map(k => (
                <button key={k} onClick={() => setSortKey(k)} style={{ fontSize: 12, padding: '3px 10px', borderRadius: 20, border: 'none', cursor: 'pointer', background: sortKey === k ? 'var(--ui-accent)' : 'var(--ui-border)', color: sortKey === k ? '#fff' : 'var(--ui-text)' }}>
                  {k === 'score' ? 'Score' : 'Name'}
                </button>
              ))}
              <span style={{ fontSize: 12, color: 'var(--ui-text2)', marginLeft: 8 }}>Filter:</span>
              {(['all', 'clean', 'suspicious', 'likely_stego'] as const).map(v => (
                <button key={v} onClick={() => setFilterVerdict(v)} style={{ fontSize: 12, padding: '3px 10px', borderRadius: 20, border: 'none', cursor: 'pointer', background: filterVerdict === v ? 'var(--ui-accent)' : 'var(--ui-border)', color: filterVerdict === v ? '#fff' : 'var(--ui-text)', textTransform: 'capitalize' }}>
                  {v === 'likely_stego' ? 'Stego' : v}
                </button>
              ))}
            </div>

            <button
              onClick={handleExport}
              style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--ui-text)', background: 'var(--ui-surface)', border: '1px solid var(--ui-border)', borderRadius: 6, padding: '6px 12px', cursor: 'pointer' }}
            >
              <FileDown size={14} /> Export report
            </button>
          </div>

          {sortedReports.map((r, i) => <ResultCard key={i} report={r} />)}

          {errors.map((e, i) => (
            <div key={i} style={{ padding: '10px 14px', borderRadius: 8, background: 'color-mix(in srgb, var(--ui-danger) 10%, var(--ui-surface))', border: '1px solid color-mix(in srgb, var(--ui-danger) 25%, transparent)', marginBottom: 8, fontSize: 13, color: 'var(--ui-danger)' }}>
              {e}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
