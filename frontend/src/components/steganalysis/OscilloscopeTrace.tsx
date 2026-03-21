import { useRef, useEffect, useState, useCallback } from 'react'
import { getTheme, easeOut, lerp } from './analysisTheme'
import { useAnimationFrame, useContainerSize } from './useAnimationFrame'

export interface AudioAnalysisData {
  waveform_samples: number[]
  suspicious_regions: [number, number][]
  lsb_anomaly_score: number
  verdict: 'clean' | 'uncertain' | 'suspicious' | 'likely_embedded'
  duration_seconds: number
}

interface Props {
  data: AudioAnalysisData
  replay: boolean
  onReplayDone: () => void
}

const PAD = { left: 42, right: 12, top: 16, bottom: 30 }
const DPR = Math.min(typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1, 2)

function isSuspicious(i: number, regions: [number, number][]): boolean {
  return regions.some(([s, e]) => i >= s && i <= e)
}

export function OscilloscopeTrace({ data, replay, onReplayDone }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [containerRef, size] = useContainerSize()
  const [frame, resetFrame] = useAnimationFrame(200)
  const [hoverIdx, setHoverIdx] = useState<number | null>(null)

  useEffect(() => { if (replay) { resetFrame(); onReplayDone() } }, [replay, resetFrame, onReplayDone])

  const samples = data.waveform_samples
  const N = samples.length
  const regions = data.suspicious_regions

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || N === 0) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const { w, h } = size
    canvas.width = w * DPR
    canvas.height = h * DPR
    ctx.setTransform(1, 0, 0, 1, 0, 0)
    ctx.scale(DPR, DPR)
    ctx.clearRect(0, 0, w, h)
    const th = getTheme()

    const cw = w - PAD.left - PAD.right
    const ch = h - PAD.top - PAD.bottom
    const midY = PAD.top + ch / 2
    const t = frame

    const sampleX = (i: number) => PAD.left + (i / (N - 1)) * cw
    const sampleY = (v: number) => midY - v * (ch / 2) * 0.88
    const barW = Math.max(1.5, (cw / N) * 0.72)

    const textAlpha = easeOut(Math.max(0, (t - 80) / 30))

    // Grid
    ctx.strokeStyle = th.gridLine
    ctx.lineWidth = 0.5
    const yTicks = [-1.0, -0.5, 0.0, 0.5, 1.0]
    for (const tick of yTicks) {
      const y = sampleY(tick)
      ctx.beginPath(); ctx.moveTo(PAD.left, y); ctx.lineTo(PAD.left + cw, y); ctx.stroke()
    }
    for (let i = 0; i <= 4; i++) {
      const x = PAD.left + (i / 4) * cw
      ctx.beginPath(); ctx.moveTo(x, PAD.top); ctx.lineTo(x, PAD.top + ch); ctx.stroke()
    }

    // Midline
    ctx.strokeStyle = 'rgba(255,255,255,0.07)'
    ctx.beginPath(); ctx.moveTo(PAD.left, midY); ctx.lineTo(PAD.left + cw, midY); ctx.stroke()

    // Spines
    ctx.strokeStyle = th.axisLine
    ctx.beginPath(); ctx.moveTo(PAD.left, PAD.top); ctx.lineTo(PAD.left, PAD.top + ch); ctx.stroke()
    ctx.beginPath(); ctx.moveTo(PAD.left, PAD.top + ch); ctx.lineTo(PAD.left + cw, PAD.top + ch); ctx.stroke()

    // Axis labels (fade in last)
    ctx.globalAlpha = textAlpha
    ctx.font = '8px "Space Mono", monospace'
    ctx.fillStyle = th.textMuted
    ctx.textAlign = 'right'
    for (const tick of yTicks) ctx.fillText(tick.toFixed(1), PAD.left - 4, sampleY(tick) + 3)
    ctx.textAlign = 'center'
    for (let i = 0; i <= 4; i++) {
      const secs = (i / 4) * data.duration_seconds
      ctx.fillText(`${secs.toFixed(1)}s`, PAD.left + (i / 4) * cw, h - PAD.bottom + 14)
    }
    ctx.globalAlpha = 1

    // Phase 1: Trace draw-in (frames 0–100)
    const traceProgress = easeOut(Math.min(1, t / 100))
    const drawUpTo = Math.floor(traceProgress * N)

    // Phase 2: Suspicious region crossfade (frames 100–140)
    const suspectReveal = easeOut(Math.max(0, (t - 115) / 25))

    // Draw background tints for suspicious regions (BEFORE bars)
    if (suspectReveal > 0) {
      for (const [start, end] of regions) {
        const x0 = sampleX(start)
        const x1 = sampleX(end)
        const regionW = x1 - x0

        ctx.globalAlpha = suspectReveal * 0.11
        ctx.fillStyle = '#ff5c5c'
        ctx.fillRect(x0, PAD.top, regionW, ch)

        ctx.globalAlpha = suspectReveal * 0.5
        ctx.strokeStyle = 'rgba(255, 80, 80, 0.6)'
        ctx.lineWidth = 0.5
        ctx.setLineDash([3, 4])
        ctx.beginPath(); ctx.moveTo(x0, PAD.top - 2); ctx.lineTo(x0, PAD.top + ch + 2); ctx.stroke()
        ctx.beginPath(); ctx.moveTo(x1, PAD.top - 2); ctx.lineTo(x1, PAD.top + ch + 2); ctx.stroke()
        ctx.setLineDash([])

        ctx.globalAlpha = suspectReveal * 0.75
        ctx.fillStyle = 'rgba(255, 90, 90, 0.9)'
        ctx.font = '7px "Space Mono", monospace'
        ctx.textAlign = 'center'
        ctx.fillText('LSB+', x0 + regionW / 2, PAD.top - 3)
        ctx.globalAlpha = 1
      }
    }

    // Draw waveform bars
    for (let i = 0; i < drawUpTo; i++) {
      const x = sampleX(i)
      const y = sampleY(samples[i])
      const barH = Math.abs(y - midY) + 1

      if (isSuspicious(i, regions) && suspectReveal > 0) {
        const r = Math.round(lerp(77, 255, suspectReveal))
        const g = Math.round(lerp(159, 92, suspectReveal))
        const b = Math.round(lerp(255, 92, suspectReveal))
        ctx.fillStyle = `rgba(${r},${g},${b},0.88)`
      } else {
        ctx.fillStyle = 'rgba(77, 159, 255, 0.75)'
      }

      ctx.fillRect(x - barW / 2, Math.min(y, midY), barW, barH)
    }

    // Glowing tip (phase 1 only)
    if (drawUpTo > 0 && drawUpTo < N) {
      const tipX = sampleX(drawUpTo)
      const tipY = sampleY(samples[drawUpTo] ?? 0)
      ctx.save()
      ctx.shadowColor = '#4d9fff'
      ctx.shadowBlur = 14
      ctx.fillStyle = 'rgba(140, 200, 255, 0.9)'
      ctx.fillRect(tipX - 1.5, Math.min(tipY, midY), 3, Math.abs(tipY - midY) + 1)
      ctx.restore()
    }

    // Hover crosshair
    if (hoverIdx !== null && hoverIdx >= 0 && hoverIdx < N) {
      const hx = sampleX(hoverIdx)
      ctx.strokeStyle = th.textMuted
      ctx.lineWidth = 0.5
      ctx.setLineDash([3, 5])
      ctx.beginPath(); ctx.moveTo(hx, PAD.top); ctx.lineTo(hx, PAD.top + ch); ctx.stroke()
      ctx.setLineDash([])

      const hy = sampleY(samples[hoverIdx])
      ctx.fillStyle = th.textPrimary
      ctx.beginPath(); ctx.arc(hx, hy, 3, 0, Math.PI * 2); ctx.fill()
    }
  }, [frame, data, samples, N, regions, hoverIdx, size])

  const handleMove = useCallback((e: React.MouseEvent) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mx = (e.clientX - rect.left) / rect.width * size.w
    const cw = size.w - PAD.left - PAD.right
    const i = Math.round(((mx - PAD.left) / cw) * (N - 1))
    setHoverIdx(i >= 0 && i < N ? i : null)
  }, [N, size])

  const verdictConfig: Record<string, { text: string; color: string }> = {
    clean:           { text: 'No LSB anomalies detected',                          color: '#3dd6a3' },
    uncertain:       { text: `${regions.length} region(s) — inconclusive`,         color: '#f5c842' },
    suspicious:      { text: `${regions.length} suspicious region(s) flagged`,     color: '#ff7070' },
    likely_embedded: { text: `${regions.length} region(s) — likely embedded`,      color: '#ff5c5c' },
  }
  const vc = verdictConfig[data.verdict] ?? verdictConfig.clean

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div ref={containerRef} style={{ position: 'relative', flex: 1, minHeight: 120 }}>
        <canvas
          ref={canvasRef}
          style={{ width: '100%', height: '100%', display: 'block' }}
          onMouseMove={handleMove}
          onMouseLeave={() => setHoverIdx(null)}
        />
      </div>
      {/* Legend */}
      <div style={{ display: 'flex', gap: 14, marginTop: 4, flexShrink: 0 }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 9, color: 'rgba(77,159,255,0.8)' }}>
          <span style={{ width: 10, height: 4, borderRadius: 1, background: 'rgba(77,159,255,0.75)' }} />
          Normal LSB
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 9, color: 'rgba(255,92,92,0.8)' }}>
          <span style={{ width: 10, height: 4, borderRadius: 1, background: 'rgba(255,92,92,0.85)' }} />
          Anomalous region
        </span>
      </div>
      {/* Verdict badge */}
      <div style={{
        marginTop: 6, flexShrink: 0,
        display: 'inline-flex', alignItems: 'center', gap: 5,
        padding: '3px 10px', borderRadius: 12, alignSelf: 'flex-start',
        background: `${vc.color}18`, color: vc.color,
        fontSize: 9, fontWeight: 600, fontFamily: "'Space Mono', monospace",
        letterSpacing: '0.04em', textTransform: 'uppercase',
      }}>
        <span style={{ width: 5, height: 5, borderRadius: '50%', background: vc.color }} />
        {vc.text}
      </div>
    </div>
  )
}
