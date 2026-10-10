import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Selection } from '../types';

interface WorkspaceState {
  paths: string[];
  activePath: string;
  threadId: string;
  selections: Selection[];
  jump: { line: number; time: number };
  sidebar: 'files' | 'threads';
  mobile: 'code' | 'chat';
  openFile: (path: string, line?: number) => void;
  closeFile: (path: string) => void;
  selectThread: (id: string) => void;
  addSelection: (selection: Selection) => void;
  removeSelection: (index: number) => void;
  clearSelections: () => void;
  setSidebar: (tab: 'files' | 'threads') => void;
  setMobile: (tab: 'code' | 'chat') => void;
}
export const useWorkspace = create<WorkspaceState>()(
  persist(
    (set) => ({
      paths: [],
      activePath: '',
      threadId: '',
      selections: [],
      sidebar: 'files',
      mobile: 'code',
      jump: { line: 1, time: 0 },
      openFile: (path, line = 1) =>
        set((state) => ({
          paths: state.paths.includes(path) ? state.paths : [...state.paths, path],
          activePath: path,
          mobile: 'code',
          jump: { line, time: Date.now() },
        })),
      closeFile: (path) =>
        set((state) => {
          const paths = state.paths.filter((item) => item !== path);
          return {
            paths,
            activePath: state.activePath === path ? paths.at(-1) || '' : state.activePath,
          };
        }),
      selectThread: (threadId) => set({ threadId, selections: [], mobile: 'chat' }),
      addSelection: (selection) =>
        set((state) => ({
          selections: [
            ...state.selections.filter(
              (item) =>
                !(
                  item.path === selection.path &&
                  item.start_line === selection.start_line &&
                  item.end_line === selection.end_line
                ),
            ),
            selection,
          ].slice(-8),
          mobile: 'chat',
        })),
      removeSelection: (index) =>
        set((state) => ({
          selections: state.selections.filter((_, position) => position !== index),
        })),
      clearSelections: () => set({ selections: [] }),
      setSidebar: (sidebar) => set({ sidebar }),
      setMobile: (mobile) => set({ mobile }),
    }),
    {
      name: 'trunk-workspace',
      partialize: (state) => ({
        paths: state.paths,
        activePath: state.activePath,
        threadId: state.threadId,
      }),
    },
  ),
);
