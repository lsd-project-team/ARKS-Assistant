import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { mergedStorage } from './mergedStorage.ts';
import { workspaceVisibility, type PaneWidths, type WorkspaceVisibility } from './paneLayout.ts';
import type { Selection, SourceOptions, SourceFile } from '../types';
import { restoredMessageJump, type ChatPosition, type MessageJump } from './chatNavigation.ts';
import { emptyProjectSession, projectSession, type ProjectSession } from './projectSessions.ts';
import type { SidebarView, ThreadEntry } from './sidebarNavigation';
import {
  fileJump,
  navigateFiles,
  parentDirectories,
  visitFile,
  closeTabs,
  type FileLocation,
  type FileNavigation,
  type FileOpenMode,
} from './fileNavigation.ts';

interface WorkspaceState extends FileNavigation {
  historicalSource: { source: SourceFile; start: number; end: number } | null;
  projectId: string;
  projectPage: boolean;
  projectSessions: Record<string, ProjectSession>;
  sourceBindings: Record<string, string>;
  sidebarView: SidebarView;
  expandedProjects: Record<string, boolean>;
  threadEntries: Record<string, ThreadEntry>;
  setThreadEntry: (id: string, entry: ThreadEntry) => void;
  setSidebarView: (view: SidebarView) => void;
  setProjectExpanded: (id: string, expanded: boolean) => void;
  switchProject: (id: string, page?: boolean) => void;
  startConversation: (projectId: string) => void;
  initializeProject: (id: string) => void;
  setProjectPage: (page: boolean) => void;
  resetProjectSource: (id: string) => void;
  threadId: string;
  messageJump: MessageJump;
  chatPositions: Record<string, ChatPosition>;
  closedFiles: FileLocation[];
  sourceFontSize: number;
  sourceLineHeight: number;
  drafts: Record<string, ConversationDraft>;
  chatRatio: number;
  explorerWidth: number;
  navigationWidth: number;
  codeOpen: boolean;
  explorerOpen: boolean;
  collapsed: boolean;
  readingFocused: boolean;
  workspaceRestore: WorkspaceVisibility | null;
  focusChatRatio: number;
  expandedDirectories: string[];
  rootExpanded: boolean;
  explorerScroll: number;
  revealTime: number;
  wordWrap: boolean;
  sourceModes: Record<string, boolean>;
  jump: { line: number; time: number; align: 'start' | 'center'; endLine?: number };
  mobile: 'code' | 'chat';
  openFile: (path: string, line?: number, mode?: FileOpenMode, endLine?: number) => void;
  closeFile: (path: string) => void;
  keepFile: (path: string) => void;
  closeOtherFiles: (path: string) => void;
  closeAllFiles: () => void;
  closeRightFiles: (path: string) => void;
  reopenFile: () => void;
  setReader: (fontSize: number, lineHeight: number) => void;
  resetLayout: () => void;
  navigateHistory: (direction: number) => void;
  toggleReadingFocus: () => void;
  setDirectoryExpanded: (path: string, expanded: boolean) => void;
  collapseDirectories: () => void;
  revealFile: () => void;
  completeReveal: () => void;
  saveExplorerScroll: (top: number) => void;
  setRootExpanded: (expanded: boolean) => void;
  setWordWrap: (wrap: boolean) => void;
  setSourceMode: (path: string, source: boolean) => void;
  selectThread: (id: string) => void;
  jumpToMessage: (threadId: string, messageId: string) => void;
  clearMessageJump: () => void;
  saveChatPosition: (id: string, position: ChatPosition) => void;
  forgetThread: (id: string) => void;
  restoreDraft: (id: string, draft: ConversationDraft) => void;
  attachNewDraft: (id: string) => void;
  addSelection: (selection: Selection) => void;
  removeSelection: (index: number) => void;
  clearSelections: () => void;
  setMobile: (tab: 'code' | 'chat') => void;
  navigationVersion: number;
  setWorkspaceOpen: (open: boolean) => void;
  collapsePane: (kind: 'chat' | 'files', restore?: PaneWidths) => void;
  setDraft: (content: string) => void;
  setSourceOptions: (options: SourceOptions) => void;
  consumeDraft: (key: string, draft: ConversationDraft) => void;
  consumeCommand: (key: string, draft: ConversationDraft) => void;
  savePosition: (path: string, line: number) => void;
  restoreReadingPosition: () => void;
  setLayout: (
    layout: Partial<
      Pick<
        WorkspaceState,
        | 'chatRatio'
        | 'focusChatRatio'
        | 'explorerWidth'
        | 'navigationWidth'
        | 'codeOpen'
        | 'explorerOpen'
        | 'collapsed'
      >
    >,
  ) => void;
}
export interface ConversationDraft {
  content: string;
  selections: Selection[];
  source_options?: Partial<SourceOptions>;
}
const EMPTY_DRAFT: ConversationDraft = { content: '', selections: [] };
export const draftKey = (threadId: string, projectId?: string) =>
  threadId || (projectId ? `new:${projectId}` : 'new');
export const draftFor = (
  state: Pick<WorkspaceState, 'drafts' | 'threadId'> & { projectId?: string },
) => state.drafts[draftKey(state.threadId, state.projectId)] || EMPTY_DRAFT;
function patchDraft(state: WorkspaceState, changes: Partial<ConversationDraft>) {
  return {
    drafts: {
      ...state.drafts,
      [draftKey(state.threadId, state.projectId)]: { ...draftFor(state), ...changes },
    },
  };
}
export const useWorkspace = create<WorkspaceState>()(
  persist(
    (set, get) => ({
      historicalSource: null,
      projectId: '',
      projectPage: false,
      projectSessions: {},
      sourceBindings: {},
      sidebarView: 'active',
      expandedProjects: {},
      threadEntries: {},
      setThreadEntry: (id, entry) =>
        set((state) => ({ threadEntries: { ...state.threadEntries, [id]: entry } })),
      setSidebarView: (sidebarView) => set({ sidebarView }),
      setProjectExpanded: (id, expanded) =>
        set((state) => ({ expandedProjects: { ...state.expandedProjects, [id]: expanded } })),
      initializeProject: (projectId) =>
        set((state) => {
          if (state.projectId) return {};
          const drafts = { ...state.drafts };
          if (drafts.new) {
            drafts[draftKey('', projectId)] = drafts.new;
            delete drafts.new;
          }
          return { projectId, drafts };
        }),
      switchProject: (projectId, projectPage = false) =>
        set((state) => {
          if (state.projectId === projectId) return { projectPage };
          const sessions = { ...state.projectSessions, [state.projectId]: projectSession(state) };
          const next = sessions[projectId] || emptyProjectSession();
          return {
            ...next,
            projectId,
            projectPage,
            projectSessions: sessions,
            historicalSource: null,
            readingFocused: false,
            workspaceRestore: null,
            mobile: 'chat',
            revealTime: 0,
            navigationVersion: state.navigationVersion + 1,
            messageJump: restoredMessageJump(state.chatPositions[next.threadId]),
            jump: { line: next.positions[next.activePath] || 1, time: Date.now(), align: 'start' },
          };
        }),
      setProjectPage: (projectPage) => set({ projectPage }),
      startConversation: (projectId) => {
        // 先固定项目，再进入新草稿，源码、仓库、资料开关沿用该项目的配置。
        get().switchProject(projectId);
        get().setSidebarView('active');
        get().selectThread('');
      },
      resetProjectSource: (id) =>
        set((state) => {
          const projectSessions = { ...state.projectSessions };
          const current = state.projectId === id;
          const saved = current ? projectSession(state) : projectSessions[id];
          const fresh = { ...emptyProjectSession(), threadId: saved?.threadId || '' };
          projectSessions[id] = fresh;
          return {
            projectSessions,
            ...(current
              ? {
                  ...fresh,
                  historicalSource: null,
                  readingFocused: false,
                  workspaceRestore: null,
                  revealTime: 0,
                  navigationVersion: state.navigationVersion + 1,
                }
              : {}),
          };
        }),
      paths: [],
      activePath: '',
      previewPath: '',
      history: [],
      historyIndex: -1,
      threadId: '',
      messageJump: { id: '', time: 0 },
      chatPositions: {},
      closedFiles: [],
      sourceFontSize: 12,
      sourceLineHeight: 1.8,
      drafts: {},
      positions: {},
      chatRatio: 0.36,
      explorerWidth: 0,
      navigationWidth: 0,
      codeOpen: true,
      explorerOpen: true,
      collapsed: false,
      readingFocused: false,
      workspaceRestore: null,
      focusChatRatio: 0.24,
      expandedDirectories: [],
      rootExpanded: true,
      explorerScroll: 0,
      revealTime: 0,
      wordWrap: true,
      sourceModes: {},
      mobile: 'chat',
      navigationVersion: 0,
      jump: { line: 1, time: 0, align: 'start' },
      openFile: (path, line, mode, endLine) =>
        set((state) => ({
          ...visitFile(state, path, line, mode),
          ...(endLine ? { jump: { ...fileJump(state, path, line), endLine } } : {}),
          expandedDirectories: [
            ...new Set([...state.expandedDirectories, ...parentDirectories(path)]),
          ],
          ...(line !== undefined ? { sourceModes: { ...state.sourceModes, [path]: true } } : {}),
          codeOpen: true,
          navigationVersion: state.navigationVersion + 1,
          mobile: 'code',
        })),
      closeFile: (path) =>
        set((state) => (state.paths.includes(path) ? closeTabs(state, [path]) : {})),
      keepFile: (path) => set((state) => (state.previewPath === path ? { previewPath: '' } : {})),
      closeOtherFiles: (path) =>
        set((state) => ({
          ...closeTabs(
            state,
            state.paths.filter((item) => item !== path),
          ),
          activePath: path,
          previewPath: '',
          jump: fileJump(state, path),
        })),
      closeAllFiles: () => set((state) => closeTabs(state, state.paths)),
      closeRightFiles: (path) =>
        set((state) => closeTabs(state, state.paths.slice(state.paths.indexOf(path) + 1))),
      reopenFile: () =>
        set((state) => {
          const available = state.closedFiles.filter((item) => !state.paths.includes(item.path));
          const latest = available.at(-1);
          return latest
            ? {
                ...visitFile(state, latest.path, latest.line),
                closedFiles: available.slice(0, -1),
                codeOpen: true,
                mobile: 'code',
                navigationVersion: state.navigationVersion + 1,
              }
            : {};
        }),
      setReader: (fontSize, lineHeight) =>
        set((state) => ({
          sourceFontSize: Math.min(22, Math.max(10, fontSize)),
          sourceLineHeight: Math.min(2.4, Math.max(1.3, lineHeight)),
          jump: fileJump(state, state.activePath),
        })),
      resetLayout: () =>
        set({
          chatRatio: 0.36,
          explorerWidth: 0,
          navigationWidth: 0,
          collapsed: false,
          readingFocused: false,
          workspaceRestore: null,
          focusChatRatio: 0.24,
          codeOpen: true,
          explorerOpen: true,
          mobile: 'chat',
        }),
      navigateHistory: (direction) =>
        set((state) => {
          const changes = navigateFiles(state, direction);
          return changes.activePath
            ? {
                ...changes,
                codeOpen: true,
                navigationVersion: state.navigationVersion + 1,
                mobile: 'code',
                expandedDirectories: [
                  ...new Set([
                    ...state.expandedDirectories,
                    ...parentDirectories(changes.activePath),
                  ]),
                ],
              }
            : {};
        }),
      toggleReadingFocus: () =>
        set((state) => ({ readingFocused: !state.readingFocused, mobile: 'code' })),
      setDirectoryExpanded: (path, expanded) =>
        set((state) => ({
          expandedDirectories: expanded
            ? [...new Set([...state.expandedDirectories, path])]
            : state.expandedDirectories.filter((item) => item !== path),
        })),
      collapseDirectories: () => set({ expandedDirectories: [], rootExpanded: true }),
      revealFile: () =>
        set((state) => ({
          explorerOpen: true,
          rootExpanded: true,
          revealTime: Date.now(),
          expandedDirectories: [
            ...new Set([...state.expandedDirectories, ...parentDirectories(state.activePath)]),
          ],
        })),
      saveExplorerScroll: (explorerScroll) => set({ explorerScroll }),
      completeReveal: () => set({ revealTime: 0 }),
      setRootExpanded: (rootExpanded) => set({ rootExpanded }),
      setWordWrap: (wordWrap) => set({ wordWrap }),
      setSourceMode: (path, source) =>
        set((state) => ({ sourceModes: { ...state.sourceModes, [path]: source } })),
      selectThread: (threadId) =>
        set((state) => ({
          threadId,
          projectPage: false,
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
      setMobile: (mobile) => set({ mobile }),
      setWorkspaceOpen: (open) =>
        set((state) => ({
          ...workspaceVisibility(state, open),
          ...(open && !state.codeOpen ? { jump: fileJump(state, state.activePath) } : {}),
        })),
      collapsePane: (kind, restore) =>
        set((state) => ({
          // 宽度和可见性一起更新，拖动收起不会留下最后几帧的极窄宽度。
          ...(kind === 'chat'
            ? restore
            : { explorerWidth: restore?.explorerWidth ?? state.explorerWidth }),
          ...(kind === 'chat' || !state.codeOpen
            ? workspaceVisibility(state, false)
            : { explorerOpen: false }),
        })),
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
      savePosition: (path, line) =>
        set((state) =>
          state.positions[path] === line
            ? state
            : { positions: { ...state.positions, [path]: line } },
        ),
      restoreReadingPosition: () => set((state) => ({ jump: fileJump(state, state.activePath) })),
      setLayout: (layout) =>
        set((state) => {
          const codeOpen = layout.codeOpen ?? state.codeOpen;
          const explorerOpen = layout.explorerOpen ?? state.explorerOpen;
          return {
            ...layout,
            // 重新挂载阅读器时恢复最后阅读行，不沿用上次引用跳转的位置。
            ...(codeOpen && !state.codeOpen ? { jump: fileJump(state, state.activePath) } : {}),
            ...(!codeOpen ? { readingFocused: false } : {}),
            ...(!codeOpen && !explorerOpen ? { mobile: 'chat' as const } : {}),
          };
        }),
    }),
    {
      name: 'trunk-workspace',
      storage: createJSONStorage(() => mergedStorage(localStorage)),
      merge: (persisted, current) => {
        const state = { ...current, ...(persisted as Partial<WorkspaceState>) };
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
        projectPage: state.projectPage,
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
