import { create } from 'zustand';

export interface ToastItem {
  id: number;
  message: string;
  tone: 'success' | 'error';
  durationMs?: number;
  action?: { label: string; run: () => Promise<unknown> | void };
}
let sequence = 0;
export const useToasts = create<{
  items: ToastItem[];
  dismiss: (id: number) => void;
}>((set) => ({
  items: [],
  dismiss: (id) => set((state) => ({ items: state.items.filter((item) => item.id !== id) })),
}));

export function toast(
  message: string,
  action?: ToastItem['action'],
  tone: ToastItem['tone'] = 'success',
  durationMs?: number,
) {
  useToasts.setState((state) => ({
    items: [...state.items.slice(-2), { id: ++sequence, message, tone, action, durationMs }],
  }));
}
