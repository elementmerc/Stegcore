import { create } from 'zustand'
import type { Cipher, EmbedMode, EmbedResult } from '../ipc'

export type EmbedStep = 1 | 2 | 3 | 4

interface EmbedStore {
  step: EmbedStep
  payloadFile: File | null
  coverFile: File | null
  coverPreviewUrl: string | null
  coverScore: number | null
  coverScoring: boolean
  cipher: Cipher
  mode: EmbedMode
  deniable: boolean
  decoyFile: File | null
  passphrase: string
  decoyPassphrase: string
  exportKey: boolean
  outputPath: string | null
  result: EmbedResult | null
  error: string | null
  embedding: boolean

  setStep: (s: EmbedStep) => void
  setPayloadFile: (f: File | null) => void
  setCoverFile: (f: File | null, previewUrl: string | null) => void
  setCoverScore: (score: number | null, scoring?: boolean) => void
  setOptions: (opts: Partial<Pick<EmbedStore, 'cipher' | 'mode' | 'deniable' | 'decoyFile' | 'passphrase' | 'decoyPassphrase' | 'exportKey'>>) => void
  setResult: (r: EmbedResult) => void
  setError: (e: string | null) => void
  setEmbedding: (v: boolean) => void
  reset: () => void
}

const INITIAL: Omit<EmbedStore, keyof { setStep: unknown; setPayloadFile: unknown; setCoverFile: unknown; setCoverScore: unknown; setOptions: unknown; setResult: unknown; setError: unknown; setEmbedding: unknown; reset: unknown }> = {
  step: 1,
  payloadFile: null,
  coverFile: null,
  coverPreviewUrl: null,
  coverScore: null,
  coverScoring: false,
  cipher: 'chacha20-poly1305',
  mode: 'adaptive',
  deniable: false,
  decoyFile: null,
  passphrase: '',
  decoyPassphrase: '',
  exportKey: false,
  outputPath: null,
  result: null,
  error: null,
  embedding: false,
}

export const useEmbedStore = create<EmbedStore>((set) => ({
  ...INITIAL,

  setStep: (step) => set({ step }),
  setPayloadFile: (payloadFile) => set({ payloadFile }),
  setCoverFile: (coverFile, coverPreviewUrl) => set({ coverFile, coverPreviewUrl, coverScore: null }),
  setCoverScore: (coverScore, coverScoring = false) => set({ coverScore, coverScoring }),
  setOptions: (opts) => set(opts),
  setResult: (result) => set({ result, error: null, embedding: false }),
  setError: (error) => set({ error, embedding: false }),
  setEmbedding: (embedding) => set({ embedding }),

  reset: () => set({ ...INITIAL }),
}))
