import {
  fileJump,
  navigateFiles,
  parentDirectories,
  visitFile,
  closeTabs,
} from './lib/fileNavigation.ts';
import type { WorkspaceSet, WorkspaceState } from '../../app/state/types.ts';
// 账号持久化由应用层统一装配，本模块维护自己的状态和操作。
export function readerState(
  set: WorkspaceSet,
): Pick<
  WorkspaceState,
  | 'historicalSource'
  | 'paths'
  | 'activePath'
  | 'previewPath'
  | 'history'
  | 'historyIndex'
  | 'closedFiles'
  | 'sourceFontSize'
  | 'sourceLineHeight'
  | 'positions'
  | 'expandedDirectories'
  | 'rootExpanded'
  | 'explorerScroll'
  | 'revealTime'
  | 'wordWrap'
  | 'sourceModes'
  | 'jump'
  | 'openFile'
  | 'closeFile'
  | 'keepFile'
  | 'closeOtherFiles'
  | 'closeAllFiles'
  | 'closeRightFiles'
  | 'reopenFile'
  | 'setReader'
  | 'navigateHistory'
  | 'setDirectoryExpanded'
  | 'collapseDirectories'
  | 'revealFile'
  | 'saveExplorerScroll'
  | 'completeReveal'
  | 'setRootExpanded'
  | 'setWordWrap'
  | 'setSourceMode'
  | 'savePosition'
  | 'restoreReadingPosition'
> {
  return {
    historicalSource: null,

    paths: [],

    activePath: '',

    previewPath: '',

    history: [],

    historyIndex: -1,

    closedFiles: [],

    sourceFontSize: 12,

    sourceLineHeight: 1.8,

    positions: {},

    expandedDirectories: [],

    rootExpanded: true,

    explorerScroll: 0,

    revealTime: 0,

    wordWrap: true,

    sourceModes: {},

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

    savePosition: (path, line) =>
      set((state) =>
        state.positions[path] === line
          ? state
          : { positions: { ...state.positions, [path]: line } },
      ),

    restoreReadingPosition: () => set((state) => ({ jump: fileJump(state, state.activePath) })),
  };
}
