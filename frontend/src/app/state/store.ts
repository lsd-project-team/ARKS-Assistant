import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { mergedStorage } from './mergedStorage.ts';
import { accountWorkspaceStorage, changeWorkspaceAccount } from './accountWorkspace.ts';
import { restoredMessageJump } from '../../features/chat/lib/chatNavigation.ts';
import { projectsState } from '../../features/projects/store.ts';
import { readerState } from '../../features/source_reader/store.ts';
import { chatState } from '../../features/chat/store.ts';
import { layoutState } from '../layouts/store.ts';
import type { WorkspaceState } from './types.ts';
export { draftKey, draftFor } from '../../features/chat/state/drafts.ts';
export type { ConversationDraft } from '../../features/chat/state/drafts.ts';
export const useWorkspace = create<WorkspaceState>()(
  persist(
    (set, get) => ({
      ...projectsState(set, get),
      ...readerState(set),
      ...chatState(set),
      ...layoutState(set),
    }),
    {
      name: 'trunk-workspace',
      storage: createJSONStorage(() => mergedStorage(accountWorkspaceStorage)),
      skipHydration: true,
      merge: (persisted, current) => {
        // 只恢复仍存在的字段，丢弃已移除页面留下的旧开关。
        const restored = Object.fromEntries(
          Object.entries((persisted || {}) as Partial<WorkspaceState>).filter(([key]) =>
            Object.hasOwn(current, key),
          ),
        ) as Partial<WorkspaceState>;
        const state = { ...current, ...restored };
        const history = state.history.length
          ? state.history
          : state.activePath
            ? [{ path: state.activePath, line: state.positions[state.activePath] ?? 1 }]
            : [];
        return {
          ...state,
          history,
          historyIndex: Math.max(
            -1,
            Math.min(
              history.length - 1,
              state.historyIndex < 0 ? history.length - 1 : state.historyIndex,
            ),
          ),
          jump: { line: state.positions[state.activePath] ?? 1, time: Date.now(), align: 'start' },
          messageJump: restoredMessageJump(state.chatPositions[state.threadId]),
        };
      },
      partialize: (state) => ({
        projectId: state.projectId,
        projectSessions: state.projectSessions,
        sourceBindings: state.sourceBindings,
        sidebarView: state.sidebarView,
        expandedProjects: state.expandedProjects,
        threadEntries: state.threadEntries,
        paths: state.paths,
        activePath: state.activePath,
        previewPath: state.previewPath,
        history: state.history,
        historyIndex: state.historyIndex,
        threadId: state.threadId,
        drafts: state.drafts,
        chatPositions: state.chatPositions,
        closedFiles: state.closedFiles,
        sourceFontSize: state.sourceFontSize,
        sourceLineHeight: state.sourceLineHeight,
        positions: state.positions,
        chatRatio: state.chatRatio,
        explorerWidth: state.explorerWidth,
        navigationWidth: state.navigationWidth,
        codeOpen: state.codeOpen,
        explorerOpen: state.explorerOpen,
        collapsed: state.collapsed,
        readingFocused: state.readingFocused,
        workspaceRestore: state.workspaceRestore,
        focusChatRatio: state.focusChatRatio,
        expandedDirectories: state.expandedDirectories,
        rootExpanded: state.rootExpanded,
        explorerScroll: state.explorerScroll,
        wordWrap: state.wordWrap,
        sourceModes: state.sourceModes,
      }),
    },
  ),
);

export function activateWorkspaceAccount(id: string) {
  changeWorkspaceAccount(id, () => {
    useWorkspace.setState(useWorkspace.getInitialState(), true);
    void useWorkspace.persist.rehydrate();
  });
}
