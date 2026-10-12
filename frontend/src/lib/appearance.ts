import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Appearance = 'white' | 'classic' | 'dark';
export const appearanceModes: { id: Appearance; title: string; description: string }[] = [
  { id: 'white', title: '纯白', description: '白色画面、浅灰层次与深灰文字' },
  { id: 'classic', title: '柔和灰绿', description: '旧版的浅色配比，适合长时间阅读' },
  { id: 'dark', title: '深色', description: '旧版的深绿底色与柔和亮色文字' },
];
export const useAppearance = create<{ mode: Appearance; setMode: (mode: Appearance) => void }>()(
  persist((set) => ({ mode: 'white', setMode: (mode) => set({ mode }) }), {
    name: 'trunk-appearance',
    merge: (stored, current) => {
      const mode = (stored as { mode?: string } | undefined)?.mode;
      return {
        ...current,
        mode: appearanceModes.some((item) => item.id === mode) ? (mode as Appearance) : 'white',
      };
    },
  }),
);
