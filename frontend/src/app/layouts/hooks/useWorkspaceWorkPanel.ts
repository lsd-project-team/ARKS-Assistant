import { useCallback, useEffect, useRef, useState } from 'react';
import { useWorkspace } from '../../state/store';

type Origin = {
  projectId: string;
  threadId: string;
  navigationVersion: number;
  layout: {
    codeOpen: boolean;
    explorerOpen: boolean;
    readingFocused: boolean;
    mobile: 'chat' | 'code';
  };
  trigger: HTMLElement | null;
};

/** 代码工作区复用右侧区域；关闭恢复原布局，切换会话或打开源码时退出。 */
export function useWorkspaceWorkPanel() {
  const { projectId, threadId, navigationVersion, codeOpen } = useWorkspace();
  const [open, setOpen] = useState(false);
  const origin = useRef<Origin | null>(null);
  const show = useCallback(() => {
    const state = useWorkspace.getState();
    origin.current ??= {
      projectId: state.projectId,
      threadId: state.threadId,
      navigationVersion: state.navigationVersion,
      layout: {
        codeOpen: state.codeOpen,
        explorerOpen: state.explorerOpen,
        readingFocused: state.readingFocused,
        mobile: state.mobile,
      },
      trigger: document.activeElement instanceof HTMLElement ? document.activeElement : null,
    };
    setOpen(true);
    useWorkspace.setState({
      codeOpen: true,
      explorerOpen: false,
      readingFocused: false,
      mobile: 'code',
    });
  }, []);
  const close = useCallback((restore = true) => {
    const previous = origin.current;
    origin.current = null;
    setOpen(false);
    const state = useWorkspace.getState();
    if (
      restore &&
      previous?.projectId === state.projectId &&
      previous.navigationVersion === state.navigationVersion
    ) {
      useWorkspace.setState(previous.layout);
      if (previous.layout.codeOpen) state.restoreReadingPosition();
      if (previous.trigger?.isConnected) previous.trigger.focus({ preventScroll: true });
    }
  }, []);
  useEffect(() => {
    const previous = origin.current;
    if (!open || !previous) return;
    if (!codeOpen) close(false);
    else if (
      previous.projectId !== projectId ||
      previous.threadId !== threadId ||
      previous.navigationVersion !== navigationVersion
    ) {
      close();
    }
  }, [open, projectId, threadId, navigationVersion, codeOpen, close]);
  return { open, show, close };
}
