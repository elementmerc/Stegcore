import React, { useState, useCallback, useEffect, useRef, createContext, useContext } from 'react'
import { BrowserRouter, Routes, Route, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Sun, Moon, Cog, ArrowLeft, ArrowRight } from 'lucide-react'
import SplashDark from './components/SplashDark'
import SplashLight from './components/SplashLight'
import { Settings as SettingsPanel } from './components/Settings'
import { StepTrack } from './components/StepTrack'
import { IconButton } from './components/IconButton'
import { effectiveTheme, toggleTheme } from './lib/theme'
import { useSettingsStore, FONT_SIZE_PX } from './lib/stores/settingsStore'
import Home from './routes/Home'
const Embed = React.lazy(() => import('./routes/Embed'))
const Extract = React.lazy(() => import('./routes/Extract'))
const Analyse = React.lazy(() => import('./routes/Analyse'))
const Learn = React.lazy(() => import('./routes/Learn'))
import { Installer } from './components/Installer'
import { ToastContainer } from './components/ToastContainer'
import { KeyboardShortcuts } from './components/KeyboardShortcuts'

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

// ── Error boundary — prevents blank screens on render crashes ─────────────

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  state: { error: Error | null } = { error: null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', height: '100%', gap: 12, padding: 32,
          color: 'var(--ui-text)', textAlign: 'center',
        }}>
          <p style={{ fontSize: 15, fontWeight: 600 }}>Something went wrong</p>
          <p style={{ fontSize: 12, color: 'var(--ui-text2)', maxWidth: 400 }}>
            {this.state.error.message}
          </p>
          <button
            onClick={() => { this.setState({ error: null }); window.history.back() }}
            style={{
              marginTop: 8, padding: '8px 20px', borderRadius: 7,
              background: 'var(--ui-accent)', color: '#fff', border: 'none',
              fontSize: 12, fontWeight: 500, cursor: 'pointer',
            }}
          >
            Go back
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

// ── Verse bar — rotating NLT Bible verse in footer ──────────────────────

function VerseBar() {
  const { settings } = useSettingsStore()
  const [verse, setVerse] = useState<{ text: string; reference: string } | null>(null)

  useEffect(() => {
    if (!settings.bibleVerses) { setVerse(null); return }
    let cancelled = false

    const fetchVerse = () => {
      import('./lib/ipc').then(({ getVerse }) => getVerse()).then(v => {
        if (!cancelled) setVerse(v)
      }).catch(() => {})
    }

    fetchVerse()
    const interval = setInterval(fetchVerse, 600_000) // 10 minutes
    return () => { cancelled = true; clearInterval(interval) }
  }, [settings.bibleVerses])

  if (!verse) return <div style={{ flex: 1 }} />

  return (
    <div style={{
      flex: 1,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 6,
      overflow: 'hidden',
      padding: '0 12px',
      minWidth: 0,
    }}>
      <span style={{
        fontSize: 'var(--font-size-xs)',
        fontStyle: 'italic',
        color: 'var(--ui-text2)',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {verse.text}
      </span>
      <span style={{
        fontSize: 'var(--font-size-xs)',
        color: 'var(--ui-text2)',
        whiteSpace: 'nowrap',
        flexShrink: 0,
        fontFamily: "'Space Mono', monospace",
        opacity: 0.7,
      }}>
        — {verse.reference}
      </span>
    </div>
  )
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
  const prevPathRef = useRef(location.pathname)
  const isBack = location.pathname === '/' || (prevPathRef.current !== '/' && location.pathname < prevPathRef.current)
  useEffect(() => { prevPathRef.current = location.pathname }, [location.pathname])

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
        <main style={{ flex: 1, overflow: 'hidden auto', background: 'var(--ui-bg)', position: 'relative' }}>
          <ErrorBoundary key={location.pathname}>
            <React.Suspense fallback={null}>
              <div className={isBack ? 'sc-enter-back' : 'sc-enter'} style={{ height: '100%' }}>
                <Outlet />
              </div>
            </React.Suspense>
          </ErrorBoundary>
        </main>

        {/* ── Footer nav — always present to prevent layout shift ── */}
        {/* Footer — always in DOM (prevents layout shift) */}
        {(() => {
          const showButtons = !isHome && (footerCfg?.backAction !== undefined || footerCfg?.continueAction !== undefined)
          return (
          <footer style={{
            flexShrink: 0,
            height: 52,
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
                  opacity: showButtons ? (footerCfg?.backAction ? 1 : 0.4) : 0,
                  transition: 'opacity var(--sc-t-fast)',
                  pointerEvents: showButtons ? 'auto' : 'none',
                  flexShrink: 0,
                }}
              >
                <ArrowLeft size={14} />
                {footerCfg?.backLabel ?? 'Back'}
              </button>

              {/* Verse — fills the middle between the buttons */}
              <VerseBar />

              <button
                className="sc-btn-primary"
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
                  opacity: showButtons ? (footerCfg?.continueAction && !footerCfg?.continueDisabled ? 1 : 0.4) : 0,
                  transition: 'opacity var(--sc-t-fast)',
                  pointerEvents: showButtons ? 'auto' : 'none',
                  flexShrink: 0,
                }}
              >
                {footerCfg?.continueLabel ?? 'Continue'}
                <ArrowRight size={14} />
              </button>
          </footer>
          )
        })()}
      </div>
    </FooterCtx.Provider>
  )
}

// ── App root ──────────────────────────────────────────────────────────────

function App() {
  const [firstRun, setFirstRun] = useState<boolean | null>(null) // null = checking
  const [splashDone, setSplashDone] = useState(false)
  const [splashVisible, setSplashVisible] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [shortcutsOpen, setShortcutsOpen] = useState(false)

  // Global `?` key opens keyboard shortcuts overlay
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA') return
      if (e.key === '?' && !settingsOpen) {
        e.preventDefault()
        setShortcutsOpen(v => !v)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [settingsOpen])

  const { load, settings } = useSettingsStore()

  useEffect(() => { load() }, [load])

  // Sync reduce-motion attribute with setting
  useEffect(() => {
    document.documentElement.setAttribute('data-reduce-motion', String(settings.reduceMotion))
  }, [settings.reduceMotion])

  // Sync interface size — zoom scales all inline px values proportionally
  useEffect(() => {
    const px = FONT_SIZE_PX[settings.fontSize] ?? 14
    const zoom = px / 14 // 14px is the base (zoom 1.0)
    document.documentElement.style.setProperty('--font-size-base', `${px}px`)
    document.documentElement.style.setProperty('--sc-ui-zoom', String(zoom))
  }, [settings.fontSize])

  // Check first-run status on mount
  useEffect(() => {
    import('@tauri-apps/api/core').then(({ invoke }) => {
      invoke<boolean>('is_first_run').then(setFirstRun)
    }).catch(() => {
      // Browser dev mode — skip installer
      setFirstRun(false)
    })
  }, [])

  const handleInstallerComplete = useCallback((prefs: { theme: string; defaultCipher: string }) => {
    // Apply preferences immediately
    const doc = document.documentElement
    if (prefs.theme === 'light') doc.setAttribute('data-theme', 'light')
    else if (prefs.theme === 'dark') doc.setAttribute('data-theme', 'dark')
    setFirstRun(false)
  }, [])

  const handleSplashComplete = useCallback(() => {
    setSplashDone(true)
    setTimeout(() => setSplashVisible(false), 200)
  }, [])

  // Still checking first-run status
  if (firstRun === null) return null

  // First-run: show installer instead of main app
  if (firstRun) return <Installer onComplete={handleInstallerComplete} />

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
            <Route path="analyse" element={<Analyse />} />
            <Route path="learn"   element={<Learn />} />
          </Route>
        </Routes>
      </BrowserRouter>

      <SettingsPanel isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <ToastContainer />
      <KeyboardShortcuts open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
    </>
  )
}

export default App
