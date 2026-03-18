import { create } from 'zustand'

interface DragStore {
  isDraggingOver: boolean
  draggedFiles: File[]
  setDragging: (v: boolean) => void
  setDraggedFiles: (files: File[]) => void
  reset: () => void
}

export const useDragStore = create<DragStore>((set) => ({
  isDraggingOver: false,
  draggedFiles: [],

  setDragging: (isDraggingOver) => set({ isDraggingOver }),
  setDraggedFiles: (draggedFiles) => set({ draggedFiles }),
  reset: () => set({ isDraggingOver: false, draggedFiles: [] }),
}))
