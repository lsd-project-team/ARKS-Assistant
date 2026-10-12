import { useEffect, useRef, type RefObject } from 'react';
import { useWorkspace } from '../lib/store';

export function useExplorerScroll(ref: RefObject<HTMLDivElement | null>, filter: string) {
  const restoring = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const cancelRestoration = useRef<(() => void) | undefined>(undefined);
  const revealTime = useWorkspace((state) => state.revealTime);
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const state = useWorkspace.getState();
    const target = filter ? 0 : state.explorerScroll;
    restoring.current = true;
    // 目录按需加载，等节点长到目标位置后再结束恢复，避免加载期间覆盖旧位置。
    const restore = () => {
      element.scrollTop = target;
      if (element.scrollTop >= target && !element.querySelector('[data-tree-loading]')) {
        restoring.current = false;
        observer.disconnect();
      }
    };
    const observer = new MutationObserver(restore);
    observer.observe(element, { childList: true, subtree: true });
    restore();
    const cancelRestore = () => {
      restoring.current = false;
      observer.disconnect();
    };
    cancelRestoration.current = cancelRestore;
    const flush = () => {
      clearTimeout(timer.current);
      if (!filter && !restoring.current)
        useWorkspace.getState().saveExplorerScroll(element.scrollTop);
    };
    window.addEventListener('pagehide', flush);
    element.addEventListener('wheel', cancelRestore, { passive: true });
    element.addEventListener('pointerdown', cancelRestore);
    element.addEventListener('keydown', cancelRestore);
    return () => {
      observer.disconnect();
      window.removeEventListener('pagehide', flush);
      element.removeEventListener('wheel', cancelRestore);
      element.removeEventListener('pointerdown', cancelRestore);
      element.removeEventListener('keydown', cancelRestore);
      flush();
    };
  }, [filter, ref]);
  useEffect(() => {
    const element = ref.current;
    if (!element || !revealTime || filter) return;
    const reveal = () => {
      const row = element.querySelector<HTMLElement>(
        `[data-path="${CSS.escape(useWorkspace.getState().activePath)}"]`,
      );
      if (!row) return;
      cancelRestoration.current?.();
      row.scrollIntoView({ block: 'nearest' });
      observer.disconnect();
      useWorkspace.getState().saveExplorerScroll(element.scrollTop);
      useWorkspace.getState().completeReveal();
    };
    const observer = new MutationObserver(reveal);
    observer.observe(element, { childList: true, subtree: true });
    reveal();
    return () => observer.disconnect();
  }, [revealTime, filter, ref]);
  return () => {
    if (filter || restoring.current) return;
    clearTimeout(timer.current);
    const top = ref.current?.scrollTop ?? 0;
    timer.current = setTimeout(() => useWorkspace.getState().saveExplorerScroll(top), 120);
  };
}
