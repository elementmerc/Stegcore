import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { KeyRound, Eye, EyeOff, FolderOpen, Copy, Lock } from 'lucide-react'
import { DropZone } from '../components/DropZone'
import { ScoreCard } from '../components/ScoreCard'
import { EntropyBar } from '../components/EntropyBar'
import { Toggle } from '../components/Toggle'
import { useEmbedStore } from '../lib/stores/embedStore'
import { useSettingsStore } from '../lib/stores/settingsStore'
import { useFooter } from '../App'
import { scoreCover, embed as ipcEmbed } from '../lib/ipc'
import type { Cipher, EmbedMode } from '../lib/ipc'

const EMBED_STEPS = ['Message', 'Cover', 'Options', 'Embed']

const CIPHER_INFO: Record<Cipher, { label: string; desc: string }> = {
  'chacha20-poly1305': { label: 'ChaCha20-Poly1305', desc: 'Fast, secure. Recommended for most uses.' },
  'aes-256-gcm':       { label: 'AES-256-GCM',       desc: 'Industry standard. Hardware-accelerated on most CPUs.' },
  'ascon-128':         { label: 'Ascon-128',          desc: 'Lightweight cipher. Excellent for constrained environments.' },
}

// ── Step wrappers ─────────────────────────────────────────────────────────

function StepShell({ title, subtitle, step, totalSteps, children }: {
  title: string
  subtitle?: string
  step: number
  totalSteps: number
  children: React.ReactNode
}) {
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    <div style={{ padding: '48px 40px 32px' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <span style={{
          display: 'block',
          fontSize: 11,
          fontFamily: "'Space Mono', monospace",
          color: 'var(--ui-text2)',
          letterSpacing: '0.1em',
          marginBottom: 8,
        }}>
          {pad(step)} / {pad(totalSteps)}
        </span>
        <h2 style={{ fontSize: 28, fontWeight: 600, color: 'var(--ui-text)', letterSpacing: '-0.02em', marginBottom: subtitle ? 6 : 0 }}>
          {title}
        </h2>
        {subtitle && <p style={{ fontSize: 13, color: 'var(--ui-text2)', lineHeight: 1.6 }}>{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

// ── Step 1: Message file ──────────────────────────────────────────────────

function Step1() {
  const { payloadFile, setPayloadFile } = useEmbedStore()
  const navigate = useNavigate()

  const handleFiles = useCallback((files: File[]) => {
    setPayloadFile(files[0])
  }, [setPayloadFile])

  useFooter({
    backLabel: 'Cancel',
    backAction: () => navigate('/'),
    continueLabel: 'Choose Cover',
    continueAction: () => useEmbedStore.getState().setStep(2),
    continueDisabled: !payloadFile,
    steps: EMBED_STEPS,
    currentStep: 1,
  })

  return (
    <StepShell title="What do you want to hide?" subtitle="Drop any file — text, binary, document." step={1} totalSteps={4}>
      <DropZone
        accept={['.txt', '.md', '.pdf', '.doc', '.docx', '.zip', '.bin']}
        onFiles={handleFiles}
        label="Drop message file here or click to browse"
        
        fileName={payloadFile?.name}
        onRemove={() => setPayloadFile(null)}
      />
      {payloadFile && (
        <p style={{ fontSize: 12, color: 'var(--ui-text2)', marginTop: 8 }}>
          {(payloadFile.size / 1024).toFixed(1)} KB
        </p>
      )}
    </StepShell>
  )
}

// ── Step 2: Cover file ────────────────────────────────────────────────────

function Step2() {
  const { coverFile, coverPreviewUrl, coverScore, coverScoring, setCoverFile, setCoverScore, setStep } = useEmbedStore()
  const { settings } = useSettingsStore()

  const isJpeg = coverFile ? /\.(jpg|jpeg)$/i.test(coverFile.name) : false

  const handleFiles = useCallback(async (files: File[]) => {
    const f = files[0]
    const url = URL.createObjectURL(f)
    setCoverFile(f, url)
    if (settings.autoScoreOnDrop) {
      setCoverScore(null, true)
      try {
        const score = await scoreCover(url)
        setCoverScore(score)
      } catch {
        setCoverScore(0, false)
      }
    }
  }, [settings.autoScoreOnDrop, setCoverFile, setCoverScore])

  const handleManualScore = useCallback(async () => {
    if (!coverPreviewUrl) return
    setCoverScore(null, true)
    try {
      const score = await scoreCover(coverPreviewUrl)
      setCoverScore(score)
    } catch {
      setCoverScore(0, false)
    }
  }, [coverPreviewUrl, setCoverScore])

  useFooter({
    backLabel: 'Message',
    backAction: () => setStep(1),
    continueLabel: 'Options',
    continueAction: () => setStep(3),
    continueDisabled: !coverFile,
    steps: EMBED_STEPS,
    currentStep: 2,
  })

  return (
    <StepShell
      title="Cover file"
      subtitle="Choose the image or audio file that will carry your hidden message."
      step={2}
      totalSteps={4}
    >
      <DropZone
        accept={['.png', '.bmp', '.jpg', '.jpeg', '.webp', '.wav']}
        onFiles={handleFiles}
        label="Drop a cover file here"
        sublabel="PNG, BMP, JPEG, WebP, WAV"
        preview={coverPreviewUrl ?? undefined}
        fileName={coverFile?.name}
        onRemove={() => { setCoverFile(null, null); setCoverScore(null) }}
      />

      {/* JPEG info */}
      {isJpeg && (
        <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 8, background: 'color-mix(in srgb, var(--ui-accent) 10%, var(--ui-surface))', border: '1px solid color-mix(in srgb, var(--ui-accent) 25%, transparent)' }}>
          <p style={{ fontSize: 12, color: 'var(--ui-text2)' }}>
            Data will be embedded in the JPEG's compression layer. Output stays a JPEG — quality is unchanged.
          </p>
        </div>
      )}

      {/* Score */}
      {coverFile && (
        <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 10 }}>
          {!settings.autoScoreOnDrop && coverScore === null && !coverScoring && (
            <button
              onClick={handleManualScore}
              style={{ fontSize: 13, color: 'var(--ui-accent)', background: 'transparent', border: 'none', cursor: 'pointer', padding: 0 }}
            >
              Score cover
            </button>
          )}
          <ScoreCard score={coverScore} loading={coverScoring} />
          {coverScore !== null && (
            <span style={{ fontSize: 12, color: 'var(--ui-text2)' }}>
              ~{Math.round(coverScore * (coverFile.size / 1024) * 0.1)} KB capacity
            </span>
          )}
        </div>
      )}
    </StepShell>
  )
}

// ── Step 3: Options ───────────────────────────────────────────────────────

function CipherPill({ cipher, selected, onSelect }: { cipher: Cipher; selected: boolean; onSelect: () => void }) {
  const info = CIPHER_INFO[cipher]
  return (
    <button
      onClick={onSelect}
      title={info.desc}
      style={{
        background: selected ? 'var(--ui-accent)' : 'var(--ui-surface2)',
        border: `1px solid ${selected ? 'var(--ui-accent)' : 'var(--ui-border)'}`,
        borderRadius: 20,
        padding: '6px 14px',
        cursor: 'pointer',
        fontSize: 12,
        fontWeight: selected ? 600 : 400,
        color: selected ? '#ffffff' : 'var(--ui-text2)',
        transition: 'background var(--sc-t-fast), border-color var(--sc-t-fast), color var(--sc-t-fast)',
        whiteSpace: 'nowrap',
      }}
    >
      {info.label}
    </button>
  )
}

function Step3() {
  const { cipher, mode, deniable, decoyFile, passphrase, decoyPassphrase, exportKey, setOptions, setStep } = useEmbedStore()
  const { settings } = useSettingsStore()
  const [showPass, setShowPass] = useState(false)
  const [showDecoyPass, setShowDecoyPass] = useState(false)

  // Apply settings defaults on mount
  useEffect(() => {
    setOptions({ cipher: settings.defaultCipher, mode: settings.defaultMode })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useFooter({
    backLabel: 'Cover',
    backAction: () => setStep(2),
    continueLabel: 'Review',
    continueAction: () => setStep(4),
    continueDisabled: passphrase.length < 1 || (deniable && decoyPassphrase.length < 1),
    steps: EMBED_STEPS,
    currentStep: 3,
  })

  return (
    <StepShell title="Encryption options" subtitle="Set your cipher, mode, and passphrase." step={3} totalSteps={4}>

      {/* Cipher */}
      <p style={{ fontSize: 11, color: 'var(--ui-text2)', marginBottom: 8, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.09em' }}>Cipher</p>
      <div style={{ display: 'flex', gap: 6, marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        {(Object.keys(CIPHER_INFO) as Cipher[]).map((c) => (
          <CipherPill key={c} cipher={c} selected={cipher === c} onSelect={() => setOptions({ cipher: c })} />
        ))}
      </div>

      {/* Mode — side-by-side cards */}
      <p style={{ fontSize: 11, color: 'var(--ui-text2)', marginBottom: 8, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.09em' }}>Embedding mode</p>
      <div style={{ display: 'flex', gap: 8, marginBottom: '1.5rem' }}>
        {(['adaptive', 'sequential'] as EmbedMode[]).map((m) => {
          const isSelected = mode === m
          return (
            <button
              key={m}
              onClick={() => setOptions({ mode: m })}
              style={{
                flex: 1,
                padding: '12px 14px',
                background: isSelected ? 'color-mix(in srgb, var(--ui-accent) 8%, var(--ui-surface2))' : 'var(--ui-surface2)',
                border: `1.5px solid ${isSelected ? 'var(--ui-accent)' : 'var(--ui-border)'}`,
                borderRadius: 10,
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'border-color var(--sc-t-fast), background var(--sc-t-fast)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: isSelected ? 'var(--ui-accent)' : 'var(--ui-text)' }}>
                  {m === 'adaptive' ? 'Adaptive' : 'Standard'}
                </span>
                {m === 'adaptive' && (
                  <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 10, background: 'color-mix(in srgb, var(--ui-accent) 15%, transparent)', color: 'var(--ui-accent)', letterSpacing: '0.05em' }}>
                    SECURE
                  </span>
                )}
              </div>
              <p style={{ fontSize: 11, color: 'var(--ui-text2)', lineHeight: 1.5 }}>
                {m === 'adaptive' ? 'Higher resistance to detection; lower capacity.' : 'More data fits; standard LSB embedding.'}
              </p>
            </button>
          )
        })}
      </div>

      {/* Deniable */}
      <div style={{ marginBottom: '1.25rem' }}>
        <Toggle
          checked={deniable}
          onChange={(v) => setOptions({ deniable: v })}
          label="Deniable mode"
          description="Hide two separate messages — one real, one decoy."
        />
        {deniable && (
          <div style={{ marginTop: 12, padding: '14px', borderRadius: 10, background: 'color-mix(in srgb, var(--ui-accent) 5%, var(--ui-surface))', border: '1px solid var(--ui-border)' }}>
            <p style={{ fontSize: 12, color: 'var(--ui-text2)', marginBottom: 10 }}>Decoy message file</p>
            <DropZone
              accept={['.txt', '.md', '.pdf', '.doc', '.docx', '.zip', '.bin']}
              onFiles={(files) => setOptions({ decoyFile: files[0] })}
              label="Drop decoy file"
              fileName={decoyFile?.name}
              onRemove={() => setOptions({ decoyFile: null })}
            />
            <div style={{ marginTop: 12 }}>
              <label style={{ fontSize: 12, color: 'var(--ui-text2)', display: 'block', marginBottom: 4 }}>Decoy passphrase</label>
              <PassField value={decoyPassphrase} show={showDecoyPass} onToggle={() => setShowDecoyPass(v => !v)} onChange={(v) => setOptions({ decoyPassphrase: v })} />
            </div>
          </div>
        )}
      </div>

      {/* Passphrase */}
      <div style={{ marginBottom: '1rem' }}>
        <label style={{ fontSize: 12, color: 'var(--ui-text2)', display: 'block', marginBottom: 6, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.07em' }}>Passphrase</label>
        <PassField value={passphrase} show={showPass} onToggle={() => setShowPass(v => !v)} onChange={(v) => setOptions({ passphrase: v })} />
        <div style={{ marginTop: 8 }}><EntropyBar value={passphrase} /></div>
        {passphrase.length > 0 && passphrase.length < settings.passphraseMinLen && (
          <p style={{ fontSize: 11, color: 'var(--ui-warn)', marginTop: 4 }}>
            Consider using at least {settings.passphraseMinLen} characters.
          </p>
        )}
      </div>

      {/* Export key */}
      <Toggle
        checked={exportKey}
        onChange={(v) => setOptions({ exportKey: v })}
        label="Export key file"
        description="Save an optional .json key file alongside the output."
      />
    </StepShell>
  )
}

function PassField({ value, show, onToggle, onChange }: { value: string; show: boolean; onToggle: () => void; onChange: (v: string) => void }) {
  return (
    <div style={{ position: 'relative' }}>
      <div style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--ui-text2)', pointerEvents: 'none' }}>
        <KeyRound size={15} />
      </div>
      <input
        type={show ? 'text' : 'password'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Enter passphrase…"
        style={{
          width: '100%',
          background: 'var(--ui-surface)',
          border: '1px solid var(--ui-border)',
          borderRadius: 'var(--sc-radius-input)',
          color: 'var(--ui-text)',
          fontSize: 14,
          padding: '9px 40px',
          outline: 'none',
        }}
        onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--ui-accent)' }}
        onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--ui-border)' }}
      />
      <button
        onClick={onToggle}
        aria-label={show ? 'Hide passphrase' : 'Show passphrase'}
        style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--ui-text2)', display: 'flex', alignItems: 'center' }}
      >
        {show ? <EyeOff size={15} /> : <Eye size={15} />}
      </button>
    </div>
  )
}

// ── Step 4: Embed ─────────────────────────────────────────────────────────

function Step4() {
  const { payloadFile, coverFile, coverPreviewUrl, cipher, mode, deniable, decoyFile, passphrase, decoyPassphrase, exportKey, result, error, embedding, setResult, setError, setEmbedding, setStep } = useEmbedStore()
  const navigate = useNavigate()
  const [copied, setCopied] = useState(false)

  useFooter({
    backLabel: 'Options',
    backAction: embedding ? null : () => setStep(3),
    continueLabel: result ? 'Done' : undefined,
    continueAction: result ? () => navigate('/') : null,
    steps: EMBED_STEPS,
    currentStep: 4,
  })

  const handleEmbed = useCallback(async () => {
    if (!payloadFile || !coverFile) return
    setEmbedding(true)
    setError(null)
    try {
      const res = await ipcEmbed({
        cover: coverPreviewUrl ?? coverFile.name,
        payload: payloadFile.name,
        passphrase,
        cipher,
        mode,
        deniable,
        decoyPayload: deniable ? (decoyFile?.name ?? undefined) : undefined,
        decoyPassphrase: deniable ? decoyPassphrase : undefined,
        exportKey,
        output: '',
      })
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong. Please try again.')
    }
  }, [payloadFile, coverFile, coverPreviewUrl, passphrase, cipher, mode, deniable, decoyFile, decoyPassphrase, exportKey, setEmbedding, setError, setResult])

  const handleCopy = useCallback(() => {
    if (!result?.outputPath) return
    navigator.clipboard.writeText(result.outputPath)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [result])

  return (
    <StepShell title="Review & Embed" subtitle="Check your selections and embed when ready." step={4} totalSteps={4}>

      {/* Summary */}
      {!result && (
        <div style={{ background: 'var(--ui-surface)', border: '1px solid var(--ui-border)', borderRadius: 10, padding: '1rem', marginBottom: '1.5rem' }}>
          <Row label="Message" value={payloadFile?.name ?? '—'} />
          <Row label="Cover"   value={coverFile?.name ?? '—'} />
          <Row label="Cipher"  value={CIPHER_INFO[cipher].label} />
          <Row label="Mode"    value={mode === 'adaptive' ? 'Adaptive (Secure)' : 'Standard (High Capacity)'} />
          <Row label="Deniable" value={deniable ? 'Yes' : 'No'} />
          <Row label="Export key file" value={exportKey ? 'Yes' : 'No'} />
        </div>
      )}

      {/* Embed button */}
      {!result && !error && (
        <button
          onClick={handleEmbed}
          disabled={embedding}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
            width: '100%',
            padding: '12px',
            background: 'var(--ui-accent)',
            border: 'none',
            borderRadius: 'var(--sc-radius-btn)',
            color: '#ffffff',
            fontSize: 15,
            fontWeight: 600,
            cursor: embedding ? 'wait' : 'pointer',
            opacity: embedding ? 0.75 : 1,
            transition: 'opacity var(--sc-t-fast)',
          }}
        >
          {embedding ? (
            <>
              <SpinnerIcon />
              Embedding…
            </>
          ) : (
            <>
              <Lock size={16} />
              Embed
            </>
          )}
        </button>
      )}

      {/* Progress bar (indeterminate while embedding) */}
      {embedding && (
        <div style={{ marginTop: 12, height: 4, borderRadius: 2, background: 'var(--ui-border)', overflow: 'hidden' }}>
          <div style={{
            height: '100%',
            width: '40%',
            borderRadius: 2,
            background: 'var(--ui-accent)',
            animation: 'slide-indeterminate 1.2s linear infinite',
          }} />
        </div>
      )}

      {/* Error state */}
      {error && (
        <div style={{ padding: '1rem', borderRadius: 10, background: 'color-mix(in srgb, var(--ui-danger) 10%, var(--ui-surface))', border: '1px solid color-mix(in srgb, var(--ui-danger) 30%, transparent)' }}>
          <p style={{ fontSize: 14, color: 'var(--ui-danger)', fontWeight: 500 }}>Embedding failed</p>
          <p style={{ fontSize: 13, color: 'var(--ui-text2)', marginTop: 4 }}>{error}</p>
          <button onClick={() => { setError(null) }} style={{ marginTop: 10, fontSize: 13, color: 'var(--ui-accent)', background: 'transparent', border: 'none', cursor: 'pointer', padding: 0 }}>
            Try Again
          </button>
        </div>
      )}

      {/* Success state */}
      {result && (
        <div style={{ padding: '1.25rem', borderRadius: 10, background: 'color-mix(in srgb, var(--ui-success) 10%, var(--ui-surface))', border: '1px solid color-mix(in srgb, var(--ui-success) 30%, transparent)' }}>
          <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--ui-success)', marginBottom: 8 }}>Hidden successfully</p>
          <p style={{ fontSize: 12, color: 'var(--ui-text2)', fontFamily: "'Space Mono', monospace", wordBreak: 'break-all', marginBottom: 12 }}>
            {result.outputPath}
          </p>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => { /* Tauri: open folder */ }}
              style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--ui-text)', background: 'var(--ui-surface)', border: '1px solid var(--ui-border)', borderRadius: 6, padding: '6px 12px', cursor: 'pointer' }}
            >
              <FolderOpen size={14} /> Open folder
            </button>
            <button
              onClick={handleCopy}
              style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: copied ? 'var(--ui-success)' : 'var(--ui-text)', background: 'var(--ui-surface)', border: '1px solid var(--ui-border)', borderRadius: 6, padding: '6px 12px', cursor: 'pointer' }}
            >
              <Copy size={14} /> {copied ? 'Copied!' : 'Copy path'}
            </button>
          </div>
        </div>
      )}

      <style>{`
        @keyframes slide-indeterminate {
          0%   { transform: translateX(-150%); }
          100% { transform: translateX(350%); }
        }
      `}</style>
    </StepShell>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid var(--ui-border)' }}>
      <span style={{ fontSize: 12, color: 'var(--ui-text2)' }}>{label}</span>
      <span style={{ fontSize: 12, color: 'var(--ui-text)', fontWeight: 500 }}>{value}</span>
    </div>
  )
}

function SpinnerIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ animation: 'spin 0.8s linear infinite' }}>
      <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="2" strokeOpacity="0.3" />
      <path d="M8 2A6 6 0 0 1 14 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </svg>
  )
}

// ── Embed route ───────────────────────────────────────────────────────────

export default function Embed() {
  const { step } = useEmbedStore()

  return (
    <div style={{ minHeight: '100%' }}>
      <div key={step} className="sc-enter">
        {step === 1 && <Step1 />}
        {step === 2 && <Step2 />}
        {step === 3 && <Step3 />}
        {step === 4 && <Step4 />}
      </div>
    </div>
  )
}
