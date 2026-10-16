import { workspaceVisibility } from './paneLayout.ts';
import { fileJump } from '../../features/source_reader/lib/fileNavigation.ts';
import type { WorkspaceSet, WorkspaceState } from '../state/types.ts';
// 账号持久化由应用层统一装配，本模块维护自己的状态和操作。
export function layoutState(
  set: WorkspaceSet,
): Pick<
  WorkspaceState,
  | 'chatRatio'
  | 'explorerWidth'
  | 'navigationWidth'
  | 'codeOpen'
  | 'explorerOpen'
  | 'collapsed'
  | 'readingFocused'
  | 'workspaceRestore'
  | 'focusChatRatio'
  | 'mobile'
  | 'navigationVersion'
  | 'resetLayout'
  | 'toggleReadingFocus'
  | 'setMobile'
  | 'setWorkspaceOpen'
  | 'collapsePane'
  | 'setLayout'
> {
  return {
    chatRatio: 0.36,

    explorerWidth: 0,

    navigationWidth: 0,

    codeOpen: true,

    explorerOpen: true,

    collapsed: false,

    readingFocused: false,

    workspaceRestore: null,

    focusChatRatio: 0.24,

    mobile: 'chat',

    navigationVersion: 0,

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

    toggleReadingFocus: () =>
      set((state) => ({ readingFocused: !state.readingFocused, mobile: 'code' })),

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
  };
}
