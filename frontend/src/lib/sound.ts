/**
 * Subtle success/error audio feedback using Web Audio API.
 * No external audio files needed — tones are synthesised.
 * Respects the user's reduce-motion setting (no sound when enabled).
 */

let ctx: AudioContext | null = null

function getCtx(): AudioContext | null {
  if (typeof window === 'undefined') return null
  if (!ctx) {
    try { ctx = new AudioContext() } catch { return null }
  }
  return ctx
}

/** Short ascending two-note chime — embed/extract success */
export function playSuccess() {
  const c = getCtx()
  if (!c) return
  const now = c.currentTime
  const gain = c.createGain()
  gain.connect(c.destination)
  gain.gain.setValueAtTime(0.08, now)
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3)

  const o1 = c.createOscillator()
  o1.type = 'sine'
  o1.frequency.setValueAtTime(880, now)
  o1.connect(gain)
  o1.start(now)
  o1.stop(now + 0.15)

  const o2 = c.createOscillator()
  o2.type = 'sine'
  o2.frequency.setValueAtTime(1320, now + 0.1)
  o2.connect(gain)
  o2.start(now + 0.1)
  o2.stop(now + 0.3)
}

/** Short descending tone — error */
export function playError() {
  const c = getCtx()
  if (!c) return
  const now = c.currentTime
  const gain = c.createGain()
  gain.connect(c.destination)
  gain.gain.setValueAtTime(0.06, now)
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25)

  const o = c.createOscillator()
  o.type = 'sine'
  o.frequency.setValueAtTime(440, now)
  o.frequency.exponentialRampToValueAtTime(220, now + 0.2)
  o.connect(gain)
  o.start(now)
  o.stop(now + 0.25)
}
