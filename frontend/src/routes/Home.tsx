import { Lock, Sun, Moon } from 'lucide-react'
import { useState } from 'react'
import { toggleTheme, effectiveTheme } from '../lib/theme'

export default function Home() {
  const [theme, setTheme] = useState<'dark' | 'light'>(effectiveTheme())

  function handleToggle() {
    toggleTheme()
    setTheme(effectiveTheme())
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        background: 'var(--bg)',
      }}
    >
      {/* Header */}
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 1.5rem',
          height: '56px',
          borderBottom: '1px solid var(--border)',
          background: 'var(--surface)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600, color: 'var(--text)' }}>
          <Lock size={20} color="var(--accent)" />
          <span>Stegcore</span>
        </div>
        <button
          onClick={handleToggle}
          aria-label="Toggle theme"
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--text-muted)',
            padding: '0.4rem',
            borderRadius: 'var(--radius-btn)',
            display: 'flex',
            alignItems: 'center',
            transition: 'color var(--t-fast)',
          }}
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </header>

      {/* Placeholder content */}
      <main style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: 'var(--text-muted)', textAlign: 'center' }}>
          Session 1 scaffold — full UI coming in Session 7
        </p>
      </main>
    </div>
  )
}
