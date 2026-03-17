export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: string
  type: ToastType
  message: string
  /** Technical detail shown when "Show technical error details" is on */
  detail?: string
  /** If true, stays until the user dismisses it */
  persistent: boolean
  duration: number // ms
}

type Listener = (toasts: Toast[]) => void

const MAX_VISIBLE = 3
let toasts: Toast[] = []
const listeners = new Set<Listener>()

function notify() {
  const copy = [...toasts]
  listeners.forEach((l) => l(copy))
}

function add(t: Omit<Toast, 'id'>): string {
  const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`
  const entry: Toast = { ...t, id }

  // If at max capacity, remove the oldest non-persistent toast
  if (toasts.length >= MAX_VISIBLE) {
    const oldest = toasts.find((x) => !x.persistent)
    if (oldest) toasts = toasts.filter((x) => x.id !== oldest.id)
  }

  toasts = [...toasts, entry]
  notify()

  if (!t.persistent) {
    setTimeout(() => toast.remove(id), t.duration)
  }

  return id
}

export const toast = {
  success(message: string, duration = 4000): string {
    return add({ type: 'success', message, persistent: false, duration })
  },

  error(message: string, detail?: string): string {
    return add({ type: 'error', message, detail, persistent: true, duration: 0 })
  },

  warning(message: string, duration = 5000): string {
    return add({ type: 'warning', message, persistent: false, duration })
  },

  info(message: string, duration = 4000): string {
    return add({ type: 'info', message, persistent: false, duration })
  },

  remove(id: string): void {
    toasts = toasts.filter((t) => t.id !== id)
    notify()
  },

  subscribe(listener: Listener): () => void {
    listeners.add(listener)
    listener([...toasts])
    return () => listeners.delete(listener)
  },
}
