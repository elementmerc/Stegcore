import { create } from 'zustand'
import type { Cipher, EmbedMode } from '../ipc'

export interface Settings {
  theme: 'dark' | 'light' | 'system'
  reduceMotion: boolean
  defaultCipher: Cipher
  defaultMode: EmbedMode
  defaultOutputFolder: string
  autoExportKey: boolean
  autoScoreOnDrop: boolean
  passphraseMinLen: number
  clearClipboardSecs: number
  sessionTimeoutMins: number
  showTechnicalErrors: boolean
  defaultReportFormat: 'html' | 'json' | 'csv'
  reportOutputFolder: string
}

const DEFAULTS: Settings = {
  theme: 'system',
  reduceMotion: false,
  defaultCipher: 'chacha20-poly1305',
  defaultMode: 'adaptive',
  defaultOutputFolder: '',
  autoExportKey: false,
  autoScoreOnDrop: true,
  passphraseMinLen: 12,
  clearClipboardSecs: 30,
  sessionTimeoutMins: 0,
  showTechnicalErrors: false,
  defaultReportFormat: 'html',
  reportOutputFolder: '',
}

interface SettingsStore {
  settings: Settings
  loaded: boolean
  load: () => Promise<void>
  update: (partial: Partial<Settings>) => void
}

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  settings: { ...DEFAULTS },
  loaded: false,

  load: async () => {
    try {
      const { getSettings } = await import('../ipc')
      const remote = await getSettings()
      set({ settings: { ...DEFAULTS, ...remote }, loaded: true })
    } catch {
      // backend unavailable in dev — use defaults
      set({ loaded: true })
    }
  },

  update: (partial) => {
    const next = { ...get().settings, ...partial }
    set({ settings: next })
    // Fire-and-forget — errors are swallowed; UI shouldn't block on this
    import('../ipc').then(({ setSettings }) => setSettings(partial)).catch(() => undefined)
  },
}))
