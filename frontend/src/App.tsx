import { useState, useCallback } from 'react'
import { BrowserRouter, Routes, Route, Outlet } from 'react-router-dom'
import SplashDark from './components/SplashDark'
import SplashLight from './components/SplashLight'
import { effectiveTheme } from './lib/theme'
import Home from './routes/Home'

// theme.ts / initTheme() in main.tsx owns data-theme on <html> and the
// OS-change listener — App.tsx just reads the resolved theme once for
// deciding which splash variant to render.
const initialTheme = effectiveTheme()

function Layout() {
  return <Outlet />
}

function App() {
  const [splashDone, setSplashDone] = useState(false)
  const [splashVisible, setSplashVisible] = useState(true)

  const handleSplashComplete = useCallback(() => {
    // Trigger the 200ms fade-out, then fully unmount
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
          <Route element={<Layout />}>
            <Route index element={<Home />} />
            {/* Sessions 7–9 will add Embed, Extract, Analyze routes here */}
          </Route>
        </Routes>
      </BrowserRouter>
    </>
  )
}

export default App
