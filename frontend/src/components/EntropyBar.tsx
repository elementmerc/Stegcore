import { useMemo } from 'react'

interface EntropyBarProps {
  value: string
  className?: string
}

function shannonEntropy(s: string): number {
  if (!s.length) return 0
  const freq = new Map<string, number>()
  for (const ch of s) freq.set(ch, (freq.get(ch) ?? 0) + 1)
  let entropy = 0
  for (const count of freq.values()) {
    const p = count / s.length
    entropy -= p * Math.log2(p)
  }
  return entropy
}

const SEGMENTS = 10

export function EntropyBar({ value, className = '' }: EntropyBarProps) {
  const { filled, tier, barColor } = useMemo(() => {
    const entropy = shannonEntropy(value)
    // Cap at 4.5 bits for "strong"
    const capped = Math.min(entropy / 4.5, 1)
    const pct = Math.round(capped * 100)
    const t = pct < 30 ? 'Weak' : pct < 60 ? 'Fair' : 'Strong'
    const f = Math.round(capped * SEGMENTS)
    const c =
      t === 'Strong' ? 'var(--ui-success)' :
      t === 'Fair'   ? 'var(--ui-warn)' :
                       'var(--ui-danger)'
    return { filled: f, tier: t, barColor: c }
  }, [value])

  if (!value) return null

  return (
    <div className={className}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
        <span style={{ fontSize: 11, color: 'var(--ui-text2)' }}>Passphrase strength</span>
        <span style={{ fontSize: 11, color: barColor, fontWeight: 600 }}>{tier}</span>
      </div>
      <div style={{ display: 'flex', gap: 3 }}>
        {Array.from({ length: SEGMENTS }, (_, i) => (
          <div
            key={i}
            style={{
              flex: 1,
              height: 4,
              borderRadius: 2,
              background: i < filled ? barColor : 'var(--ui-border2)',
              transition: 'background var(--sc-t-base)',
            }}
          />
        ))}
      </div>
    </div>
  )
}
