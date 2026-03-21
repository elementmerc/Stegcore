import { useState, useEffect, useCallback } from 'react'
import { X, CheckCircle2, AlertTriangle, AlertCircle, Info } from 'lucide-react'
import { toast, type Toast, type ToastType } from '../lib/toast'

const ICON: Record<ToastType, typeof CheckCircle2> = {
  success: CheckCircle2,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
}

const ACCENT: Record<ToastType, string> = {
  success: 'var(--ui-success)',
  error: 'var(--ui-danger)',
  warning: 'var(--ui-warn)',
  info: 'var(--ui-accent)',
}

function ToastCard({ t }: { t: Toast }) {
  const Icon = ICON[t.type]
  const accent = ACCENT[t.type]

  const handleDismiss = useCallback(() => toast.remove(t.id), [t.id])

  return (
    <div
      role={t.type === 'error' ? 'alert' : undefined}
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 10,
        padding: '10px 14px',
        borderRadius: 8,
        background: 'var(--ui-surface)',
        border: '1px solid var(--ui-border)',
        borderLeft: `3px solid ${accent}`,
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        maxWidth: 340,
        animation: 'toast-in 0.25s ease-out',
      }}
    >
      <Icon size={16} style={{ color: accent, flexShrink: 0, marginTop: 1 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ fontSize: 13, color: 'var(--ui-text)', fontWeight: 500, lineHeight: 1.4 }}>
          {t.message}
        </p>
        {t.detail && (
          <p style={{ fontSize: 11, color: 'var(--ui-text2)', marginTop: 3, lineHeight: 1.4, wordBreak: 'break-word' }}>
            {t.detail}
          </p>
        )}
      </div>
      <button
        onClick={handleDismiss}
        aria-label="Dismiss"
        style={{
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          color: 'var(--ui-text2)',
          padding: 0,
          display: 'flex',
          flexShrink: 0,
        }}
      >
        <X size={14} />
      </button>
    </div>
  )
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([])

  useEffect(() => {
    return toast.subscribe(setToasts)
  }, [])

  if (!toasts.length) return null

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Notifications"
      style={{
        position: 'fixed',
        top: 68,
        right: 16,
        zIndex: 9000,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        pointerEvents: 'auto',
      }}
    >
      {toasts.map((t) => (
        <ToastCard key={t.id} t={t} />
      ))}
      <style>{`
        @keyframes toast-in {
          from { opacity: 0; transform: translateX(20px); }
          to   { opacity: 1; transform: translateX(0); }
        }
      `}</style>
    </div>
  )
}
