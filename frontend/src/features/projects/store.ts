import { emptyProjectSession, projectSession } from './lib/projectSessions.ts';
import { draftKey } from '../chat/state/drafts.ts';
import { restoredMessageJump } from '../chat/lib/chatNavigation.ts';
import type { WorkspaceSet, WorkspaceState } from '../../app/state/types.ts';
// 账号持久化由应用层统一装配，本模块维护自己的状态和操作。
export function projectsState(
  set: WorkspaceSet,
  get: () => WorkspaceState,
): Pick<
  WorkspaceState,
  | 'projectId'
  | 'projectSessions'
  | 'sourceBindings'
  | 'expandedProjects'
  | 'setProjectExpanded'
  | 'initializeProject'
  | 'switchProject'
  | 'startConversation'
  | 'resetProjectSource'
  | 'removeProject'
> {
  return {
    projectId: '',

    projectSessions: {},

    sourceBindings: {},

    expandedProjects: {},

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

    switchProject: (projectId) =>
      set((state) => {
        if (state.projectId === projectId) return {};
        const sessions = { ...state.projectSessions, [state.projectId]: projectSession(state) };
        const next = sessions[projectId] || emptyProjectSession();
        return {
          ...next,
          projectId,
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

    removeProject: (id, disposition) => {
      const current = get();
      const threadId = current.projectId === id ? current.threadId : '';
      if (current.projectId === id) {
        current.switchProject('independent');
        get().selectThread(disposition === 'independent' ? threadId : '');
        get().setSidebarView(disposition === 'trash' ? 'deleted' : 'active');
        if (threadId && disposition === 'independent') get().setThreadEntry(threadId, 'recent');
      }
      set((state) => {
        const projectSessions = { ...state.projectSessions };
        const sourceBindings = { ...state.sourceBindings };
        const expandedProjects = { ...state.expandedProjects };
        const drafts = { ...state.drafts };
        const source = drafts[draftKey('', id)];
        const targetKey = draftKey('', 'independent');
        const target = drafts[targetKey];
        if (source) {
          // 两边都有草稿时保留两份正文和全部选区，不覆盖原独立草稿或截断选区。
          drafts[targetKey] = target
            ? {
                ...target,
                content: [target.content, source.content].filter(Boolean).join('\n\n'),
                selections: [...target.selections, ...source.selections],
              }
            : source;
        }
        delete drafts[draftKey('', id)];
        delete projectSessions[id];
        delete sourceBindings[id];
        delete expandedProjects[id];
        return { projectSessions, sourceBindings, expandedProjects, drafts };
      });
    },
  };
}
