import { create } from 'zustand'

export type ExtractStep = 1 | 2 | 3

interface ExtractStore {
  step: ExtractStep
  stegoFile: File | null
  stegoPreviewUrl: string | null
  keyFile: File | null
  keyFileMetadata: Record<string, unknown> | null
  passphrase: string
  result: Uint8Array | null
  resultText: string | null
  error: string | null
  extracting: boolean

  setStep: (s: ExtractStep) => void
  setStegoFile: (f: File | null, previewUrl: string | null) => void
  setKeyFile: (f: File | null, metadata: Record<string, unknown> | null) => void
  setPassphrase: (p: string) => void
  setResult: (bytes: Uint8Array) => void
  setError: (e: string | null) => void
  setExtracting: (v: boolean) => void
  reset: () => void
}

const INITIAL: Omit<ExtractStore, keyof { setStep: unknown; setStegoFile: unknown; setKeyFile: unknown; setPassphrase: unknown; setResult: unknown; setError: unknown; setExtracting: unknown; reset: unknown }> = {
  step: 1,
  stegoFile: null,
  stegoPreviewUrl: null,
  keyFile: null,
  keyFileMetadata: null,
  passphrase: '',
  result: null,
  resultText: null,
  error: null,
  extracting: false,
}

export const useExtractStore = create<ExtractStore>((set) => ({
  ...INITIAL,

  setStep: (step) => set({ step }),
  setStegoFile: (stegoFile, stegoPreviewUrl) => set({ stegoFile, stegoPreviewUrl }),
  setKeyFile: (keyFile, keyFileMetadata) => set({ keyFile, keyFileMetadata }),
  setPassphrase: (passphrase) => set({ passphrase }),

  setResult: (result) => {
    // Attempt UTF-8 decode for preview
    let resultText: string | null = null
    try {
      resultText = new TextDecoder('utf-8', { fatal: true }).decode(result)
    } catch {
      resultText = null
    }
    set({ result, resultText, error: null, extracting: false })
  },

  setError: (error) => set({ error, extracting: false }),
  setExtracting: (extracting) => set({ extracting }),

  reset: () => set({ ...INITIAL }),
}))
