export const FILES_MIN_WIDTH = 160;
export const FILES_COLLAPSE_WIDTH = 100;
export const WORKSPACE_MIN_WIDTH = 320;
export const WORKSPACE_COLLAPSE_WIDTH = 200;

export function paneWidthLimits({
  kind,
  parentWidth,
  dividerWidth = 1,
  focused = false,
  filesOverlay = false,
  filesOpen = false,
  codeOpen = true,
}: {
  kind: 'chat' | 'files';
  parentWidth: number;
  dividerWidth?: number;
  focused?: boolean;
  filesOverlay?: boolean;
  filesOpen?: boolean;
  codeOpen?: boolean;
}) {
  const minimum = kind === 'chat' ? (focused ? 260 : 320) : FILES_MIN_WIDTH;
  // 并排文件栏也占用空间，不能把源码的阅读预算再次分给文件栏。
  const workspaceMinimum =
    WORKSPACE_MIN_WIDTH + (filesOpen && !filesOverlay ? FILES_MIN_WIDTH + dividerWidth : 0);
  const maximum =
    kind === 'chat'
      ? parentWidth - workspaceMinimum - dividerWidth
      : filesOverlay
        ? Math.min(285, parentWidth)
        : codeOpen
          ? parentWidth - WORKSPACE_MIN_WIDTH - dividerWidth
          : Math.min(parentWidth * 0.45, parentWidth - 320);
  return { minimum, maximum: Math.max(minimum, maximum) };
}

export type PaneWidths = {
  chatRatio: number;
  focusChatRatio: number;
  explorerWidth: number;
};

export type WorkspaceVisibility = {
  codeOpen: boolean;
  explorerOpen: boolean;
  readingFocused: boolean;
};

export function workspaceVisibility(
  state: WorkspaceVisibility & { workspaceRestore: WorkspaceVisibility | null },
  open: boolean,
) {
  if (!open) {
    return {
      codeOpen: false,
      explorerOpen: false,
      readingFocused: false,
      mobile: 'chat' as const,
      // 重复关闭时保留之前的布局；文件树原本收起时，再打开也保持收起。
      workspaceRestore:
        state.codeOpen || state.explorerOpen
          ? {
              codeOpen: state.codeOpen,
              explorerOpen: state.explorerOpen,
              readingFocused: state.readingFocused,
            }
          : state.workspaceRestore,
    };
  }
  return {
    ...(state.workspaceRestore || {
      codeOpen: true,
      explorerOpen: true,
      readingFocused: state.readingFocused,
    }),
    workspaceRestore: null,
    mobile: 'code' as const,
  };
}
