import { restoredMessageJump } from './lib/chatNavigation.ts';
import { draftKey, draftFor, patchDraft } from './state/drafts.ts';
import type { WorkspaceSet, WorkspaceState } from '../../app/state/types.ts';
// 账号持久化由应用层统一装配，本模块维护自己的状态和操作。
export function chatState(
  set: WorkspaceSet,
): Pick<
  WorkspaceState,
  | 'sidebarView'
  | 'threadEntries'
  | 'setThreadEntry'
  | 'setSidebarView'
  | 'threadId'
  | 'messageJump'
  | 'chatPositions'
  | 'drafts'
  | 'selectThread'
  | 'jumpToMessage'
  | 'clearMessageJump'
  | 'saveChatPosition'
  | 'forgetThread'
  | 'restoreDraft'
  | 'attachNewDraft'
  | 'addSelection'
  | 'removeSelection'
  | 'clearSelections'
  | 'setDraft'
  | 'setSourceOptions'
  | 'consumeDraft'
  | 'consumeCommand'
> {
  return {
    sidebarView: 'active',

    threadEntries: {},

    setThreadEntry: (id, entry) =>
      set((state) => ({ threadEntries: { ...state.threadEntries, [id]: entry } })),

    setSidebarView: (sidebarView) => set({ sidebarView }),

    threadId: '',

    messageJump: { id: '', time: 0 },

    chatPositions: {},

    drafts: {},

    selectThread: (threadId) =>
      set((state) => ({
        threadId,
        mobile: 'chat',
        messageJump: restoredMessageJump(state.chatPositions[threadId]),
      })),

    jumpToMessage: (threadId, id) =>
      set({ threadId, mobile: 'chat', messageJump: { id, time: Date.now() } }),

    clearMessageJump: () => set({ messageJump: { id: '', time: Date.now() } }),

    saveChatPosition: (id, position) =>
      set((state) => ({ chatPositions: { ...state.chatPositions, [id]: position } })),

    forgetThread: (id) =>
      set((state) => {
        const drafts = { ...state.drafts };
        const chatPositions = { ...state.chatPositions };
        const threadEntries = { ...state.threadEntries };
        delete drafts[id];
        delete chatPositions[id];
        delete threadEntries[id];
        const projectSessions = Object.fromEntries(
          Object.entries(state.projectSessions).map(([projectId, session]) => [
            projectId,
            session.threadId === id ? { ...session, threadId: '' } : session,
          ]),
        );
        return {
          drafts,
          chatPositions,
          threadEntries,
          projectSessions,
          ...(state.threadId === id ? { threadId: '', messageJump: { id: '', time: 0 } } : {}),
        };
      }),

    restoreDraft: (id, draft) => set((state) => ({ drafts: { [id]: draft, ...state.drafts } })),

    attachNewDraft: (threadId) =>
      set((state) => {
        if (state.threadId) return state;
        // 新会话的首次运行成功后才迁移草稿；失败时仍可在原输入框重试。
        const drafts = { ...state.drafts };
        const key = draftKey('', state.projectId);
        if (drafts[key]) drafts[threadId] = drafts[key];
        delete drafts[key];
        return { threadId, drafts, mobile: 'chat' };
      }),

    addSelection: (selection) =>
      set((state) => ({
        ...patchDraft(state, {
          selections: [
            ...draftFor(state).selections.filter(
              (item) =>
                !(
                  item.path === selection.path &&
                  item.start_line === selection.start_line &&
                  item.end_line === selection.end_line
                ),
            ),
            selection,
          ].slice(-8),
        }),
        mobile: 'chat',
      })),

    removeSelection: (index) =>
      set((state) =>
        patchDraft(state, {
          selections: draftFor(state).selections.filter((_, position) => position !== index),
        }),
      ),

    clearSelections: () => set((state) => patchDraft(state, { selections: [] })),

    setDraft: (content) => set((state) => patchDraft(state, { content })),

    setSourceOptions: (source_options) => set((state) => patchDraft(state, { source_options })),

    consumeDraft: (key, submitted) =>
      set((state) => {
        // 请求返回时用户可能已切换会话或继续输入，只清理实际提交的草稿。
        if (state.drafts[key] !== submitted) return state;
        const drafts = { ...state.drafts };
        delete drafts[key];
        return { drafts };
      }),

    consumeCommand: (key, submitted) =>
      set((state) => {
        // 命令仅清理提交时的文本，保留选区，也不覆盖异步请求期间的新草稿。
        if (state.drafts[key] !== submitted) return state;
        return {
          drafts: {
            ...state.drafts,
            [key]: { ...submitted, content: '', selections: submitted.selections },
          },
        };
      }),
  };
}
