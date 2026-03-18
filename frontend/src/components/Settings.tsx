import { useEffect } from 'react'
import { X } from 'lucide-react'
import { Toggle } from './Toggle'
import { useSettingsStore } from '../lib/stores/settingsStore'
import type { Cipher, EmbedMode } from '../lib/ipc'

interface SettingsProps {
  isOpen: boolean
  onClose: () => void
}

const CIPHER_LABELS: Record<Cipher, string> = {
  'ascon-128':          'Ascon-128',
  'chacha20-poly1305':  'ChaCha20-Poly1305',
  'aes-256-gcm':        'AES-256-GCM',
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: '1.75rem' }}>
      <p style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--ui-text2)', marginBottom: '0.75rem' }}>
        {title}
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {children}
      </div>
    </div>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
      <span style={{ fontSize: 13, color: 'var(--ui-text)', flexShrink: 0 }}>{label}</span>
      {children}
    </div>
  )
}

function Select<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T
  onChange: (v: T) => void
  options: Array<{ value: T; label: string }>
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as T)}
      style={{
        background: 'var(--ui-surface)',
        border: '1px solid var(--ui-border)',
        borderRadius: 'var(--sc-radius-input)',
        color: 'var(--ui-text)',
        fontSize: 13,
        padding: '4px 8px',
        cursor: 'pointer',
      }}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  )
}

function NumberInput({ value, onChange, min, max }: { value: number; onChange: (v: number) => void; min?: number; max?: number }) {
  return (
    <input
      type="number"
      value={value}
      min={min}
      max={max}
      onChange={(e) => onChange(Number(e.target.value))}
      style={{
        background: 'var(--ui-surface)',
        border: '1px solid var(--ui-border)',
        borderRadius: 'var(--sc-radius-input)',
        color: 'var(--ui-text)',
        fontSize: 13,
        padding: '4px 8px',
        width: 64,
        textAlign: 'right',
      }}
    />
  )
}

export function Settings({ isOpen, onClose }: SettingsProps) {
  const { settings, update } = useSettingsStore()

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isOpen, onClose])

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.4)',
            zIndex: 99,
          }}
        />
      )}

      {/* Panel */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          height: '100%',
          width: 380,
          background: 'var(--ui-surface)',
          borderLeft: '1px solid var(--ui-border)',
          zIndex: 100,
          transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform var(--sc-t-slow)',
          display: 'flex',
          flexDirection: 'column',
          overflowY: 'auto',
        }}
        role="dialog"
        aria-modal="true"
        aria-label="Settings"
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem 1.25rem', borderBottom: '1px solid var(--ui-border)', flexShrink: 0 }}>
          <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--ui-text)' }}>Settings</span>
          <button
            onClick={onClose}
            aria-label="Close settings"
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--ui-text2)', display: 'flex', alignItems: 'center', padding: 4, borderRadius: 6 }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: '1.25rem', flex: 1 }}>

          <Section title="Appearance">
            <Row label="Theme">
              <Select
                value={settings.theme}
                onChange={(v) => update({ theme: v })}
                options={[
                  { value: 'system', label: 'System' },
                  { value: 'dark',   label: 'Dark' },
                  { value: 'light',  label: 'Light' },
                ]}
              />
            </Row>
            <Toggle
              checked={settings.reduceMotion}
              onChange={(v) => update({ reduceMotion: v })}
              label="Reduce motion"
              description="Disables all transitions and animations."
            />
          </Section>

          <Section title="Embedding Defaults">
            <Row label="Default cipher">
              <Select<Cipher>
                value={settings.defaultCipher}
                onChange={(v) => update({ defaultCipher: v })}
                options={(Object.entries(CIPHER_LABELS) as [Cipher, string][]).map(([value, label]) => ({ value, label }))}
              />
            </Row>
            <Row label="Default mode">
              <Select<EmbedMode>
                value={settings.defaultMode}
                onChange={(v) => update({ defaultMode: v })}
                options={[
                  { value: 'adaptive',   label: 'Adaptive (Secure)' },
                  { value: 'sequential', label: 'Standard (High Capacity)' },
                ]}
              />
            </Row>
            <Toggle
              checked={settings.autoExportKey}
              onChange={(v) => update({ autoExportKey: v })}
              label="Auto-export key file"
              description="Always export a key file alongside the stego file."
            />
            <Toggle
              checked={settings.autoScoreOnDrop}
              onChange={(v) => update({ autoScoreOnDrop: v })}
              label="Auto-score cover on drop"
              description="Score the cover file immediately when dropped."
            />
          </Section>

          <Section title="Security">
            <Row label="Min passphrase length">
              <NumberInput value={settings.passphraseMinLen} onChange={(v) => update({ passphraseMinLen: v })} min={1} max={64} />
            </Row>
            <Row label="Clear clipboard (seconds)">
              <NumberInput value={settings.clearClipboardSecs} onChange={(v) => update({ clearClipboardSecs: v })} min={0} max={300} />
            </Row>
            <Row label="Session timeout (minutes)">
              <NumberInput value={settings.sessionTimeoutMins} onChange={(v) => update({ sessionTimeoutMins: v })} min={0} max={480} />
            </Row>
            <Toggle
              checked={settings.showTechnicalErrors}
              onChange={(v) => update({ showTechnicalErrors: v })}
              label="Show technical error details"
              description="When off, only plain-language error messages are shown."
            />
          </Section>

          <Section title="Analysis Defaults">
            <Row label="Report format">
              <Select
                value={settings.defaultReportFormat}
                onChange={(v) => update({ defaultReportFormat: v })}
                options={[
                  { value: 'html', label: 'HTML' },
                  { value: 'json', label: 'JSON' },
                  { value: 'csv',  label: 'CSV' },
                ]}
              />
            </Row>
          </Section>

          <Section title="About">
            <div style={{ fontSize: 13, color: 'var(--ui-text2)', lineHeight: 1.7 }}>
              <p><strong style={{ color: 'var(--ui-text)' }}>Stegcore</strong> v3.0.0-dev</p>
              <p>Licence: AGPL-3.0</p>
              <p style={{ marginTop: 8, fontSize: 12 }}>
                No telemetry. No network connections. Fully offline.
              </p>
            </div>
          </Section>

        </div>
      </div>
    </>
  )
}
