import { useState, useCallback, useEffect, createContext, useContext } from 'react'
import { BrowserRouter, Routes, Route, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Sun, Moon, Cog, ArrowLeft, ArrowRight } from 'lucide-react'
import SplashDark from './components/SplashDark'
import SplashLight from './components/SplashLight'
import { Settings as SettingsPanel } from './components/Settings'
import { StepTrack } from './components/StepTrack'
import { IconButton } from './components/IconButton'
import { effectiveTheme, toggleTheme } from './lib/theme'
import { useSettingsStore } from './lib/stores/settingsStore'
import Home from './routes/Home'
import Embed from './routes/Embed'
import Extract from './routes/Extract'
import Analyze from './routes/Analyze'

// ── Theme observation ─────────────────────────────────────────────────────

const initialTheme = effectiveTheme()

// ── Footer context — wizard routes provide back/continue actions ──────────

export interface FooterConfig {
  backLabel?: string
  backAction?: (() => void) | null
  continueLabel?: string
  continueAction?: (() => void) | null
  continueDisabled?: boolean
  steps?: string[]
  currentStep?: number
}

const FooterCtx = createContext<(cfg: FooterConfig | null) => void>(() => undefined)
export function useFooter(cfg: FooterConfig | null) {
  const set = useContext(FooterCtx)
  useEffect(() => {
    set(cfg)
    return () => set(null)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(cfg)])
}

// ── Layout ────────────────────────────────────────────────────────────────

function Layout({
  settingsOpen,
  setSettingsOpen,
}: {
  settingsOpen: boolean
  setSettingsOpen: (v: boolean) => void
}) {
  const location = useLocation()
  const navigate = useNavigate()
  const [footerCfg, setFooterCfg] = useState<FooterConfig | null>(null)
  const [theme, setThemeState] = useState<'dark' | 'light'>(effectiveTheme())
  const isHome = location.pathname === '/'

  // Keep local theme state in sync with OS changes
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => setThemeState(effectiveTheme())
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  const handleThemeToggle = useCallback(() => {
    toggleTheme()
    setThemeState(effectiveTheme())
  }, [])

  return (
    <FooterCtx.Provider value={setFooterCfg}>
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

        {/* ── Header ── */}
        <header style={{
          flexShrink: 0,
          height: 56,
          display: 'flex',
          alignItems: 'center',
          padding: '0 1.25rem',
          borderBottom: '1px solid var(--ui-border)',
          background: 'var(--ui-surface)',
          gap: '0.75rem',
        }}>
          {/* Logo + wordmark */}
          <button
            onClick={() => navigate('/')}
            aria-label="Stegcore home"
            style={{ display: 'flex', alignItems: 'center', gap: 10, background: 'transparent', border: 'none', cursor: 'pointer', padding: 0 }}
          >
            {/* Layered Stack SVG */}
            <svg width="28" height="28" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="8"  y="10" width="48" height="12" rx="2.5" fill="#4da6ff" />
              <rect x="8"  y="28" width="21" height="12" rx="2.5" fill="#2a7fff" />
              <rect x="35" y="28" width="21" height="12" rx="2.5" fill="#2a7fff" />
              <rect x="8"  y="46" width="48" height="12" rx="2.5" fill="#1252cc" />
            </svg>
            <span style={{ fontWeight: 500, fontSize: 14, letterSpacing: '0.15em', color: 'var(--ui-text)', textTransform: 'uppercase' }}>
              STEGCORE
            </span>
          </button>

          {/* Step track — only on wizard routes */}
          {!isHome && footerCfg?.steps && footerCfg.currentStep !== undefined && (
            <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
              <StepTrack steps={footerCfg.steps} current={footerCfg.currentStep} />
            </div>
          )}

          {isHome && <div style={{ flex: 1 }} />}

          {/* Icon buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <IconButton
              icon={theme === 'dark' ? Sun : Moon}
              label="Toggle theme"
              onClick={handleThemeToggle}
            />
            <IconButton
              icon={Cog}
              label="Settings"
              onClick={() => setSettingsOpen(true)}
              active={settingsOpen}
            />
          </div>
        </header>

        {/* ── Content ── */}
        <main style={{ flex: 1, overflowY: 'auto', background: 'var(--ui-bg)', position: 'relative' }}>
          <div key={location.pathname} className="sc-enter" style={{ height: '100%' }}>
            <Outlet />
          </div>
        </main>

        {/* ── Footer nav — hidden on Home ── */}
        {!isHome && (footerCfg?.backAction !== undefined || footerCfg?.continueAction !== undefined) && (
          <footer style={{
            flexShrink: 0,
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 1.5rem',
            borderTop: '1px solid var(--ui-border)',
            background: 'var(--ui-surface)',
          }}>
            <button
              onClick={footerCfg?.backAction ?? undefined}
              disabled={!footerCfg?.backAction}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                background: 'transparent',
                border: '1px solid var(--ui-border)',
                borderRadius: 'var(--sc-radius-btn)',
                cursor: footerCfg?.backAction ? 'pointer' : 'default',
                color: footerCfg?.backAction ? 'var(--ui-text)' : 'var(--ui-text2)',
                fontSize: 13,
                fontWeight: 500,
                padding: '7px 16px',
                opacity: footerCfg?.backAction ? 1 : 0.4,
                transition: 'opacity var(--sc-t-fast)',
              }}
            >
              <ArrowLeft size={14} />
              {footerCfg?.backLabel ?? 'Back'}
            </button>

            <button
              onClick={footerCfg?.continueAction ?? undefined}
              disabled={!footerCfg?.continueAction || footerCfg?.continueDisabled}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                background: 'var(--ui-accent)',
                border: 'none',
                borderRadius: 'var(--sc-radius-btn)',
                cursor: footerCfg?.continueAction && !footerCfg?.continueDisabled ? 'pointer' : 'default',
                color: '#ffffff',
                fontSize: 14,
                fontWeight: 500,
                padding: '9px 22px',
                opacity: footerCfg?.continueAction && !footerCfg?.continueDisabled ? 1 : 0.4,
                transition: 'opacity var(--sc-t-fast)',
              }}
            >
              {footerCfg?.continueLabel ?? 'Continue'}
              <ArrowRight size={14} />
            </button>
          </footer>
        )}
      </div>
    </FooterCtx.Provider>
  )
}

// ── App root ──────────────────────────────────────────────────────────────

function App() {
  const [splashDone, setSplashDone] = useState(false)
  const [splashVisible, setSplashVisible] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)

  const { load } = useSettingsStore()

  useEffect(() => { load() }, [load])

  const handleSplashComplete = useCallback(() => {
    setSplashDone(true)
    setTimeout(() => setSplashVisible(false), 200)
  }, [])

  return (
    <>
      {splashVisible && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9999,
            opacity: splashDone ? 0 : 1,
            transition: splashDone ? 'opacity 200ms ease' : undefined,
            pointerEvents: splashDone ? 'none' : undefined,
          }}
        >
          {initialTheme === 'dark'
            ? <SplashDark onComplete={handleSplashComplete} />
            : <SplashLight onComplete={handleSplashComplete} />
          }
        </div>
      )}

      <BrowserRouter>
        <Routes>
          <Route element={<Layout settingsOpen={settingsOpen} setSettingsOpen={setSettingsOpen} />}>
            <Route index element={<Home />} />
            <Route path="embed"   element={<Embed />} />
            <Route path="extract" element={<Extract />} />
            <Route path="analyze" element={<Analyze />} />
          </Route>
        </Routes>
      </BrowserRouter>

      <SettingsPanel isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </>
  )
}

export default App
