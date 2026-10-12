import { useLayoutEffect, useRef, useState } from 'react';
import { useWorkspace } from '../lib/store';
import type { ChatPosition } from '../lib/chatNavigation';

function readingPosition(area: HTMLDivElement, following: boolean): ChatPosition {
  const top = area.getBoundingClientRect().top;
  const anchor = [...area.querySelectorAll<HTMLElement>('[data-message-id]')].find(
    (node) => node.getBoundingClientRect().bottom > top,
  );
  return {
    anchor: anchor?.dataset.messageId || '',
    offset: anchor ? top - anchor.getBoundingClientRect().top : 0,
    following,
  };
}

export function useChatScroll(threadId: string, revision: string, visible: boolean, loaded = true) {
  const scrollArea = useRef<HTMLDivElement>(null);
  const following = useRef(true);
  const initialized = useRef('');
  const lastPosition = useRef<ChatPosition | undefined>(undefined);
  const prepended = useRef<{ height: number; top: number } | undefined>(undefined);
  const [showLatest, setShowLatest] = useState(false);
  const jump = useWorkspace((state) => state.messageJump);
  const scope = `${threadId}:${jump.time}`;
  function toLatest() {
    following.current = true;
    setShowLatest(false);
    useWorkspace.getState().clearMessageJump();
    const area = scrollArea.current;
    if (area) area.scrollTop = area.scrollHeight;
  }
  function preserveOnPrepend() {
    const area = scrollArea.current;
    if (area) prepended.current = { height: area.scrollHeight, top: area.scrollTop };
  }
  useLayoutEffect(
    () => () => {
      if (lastPosition.current && threadId)
        useWorkspace.getState().saveChatPosition(threadId, lastPosition.current);
      lastPosition.current = undefined;
      prepended.current = undefined;
    },
    [threadId],
  );
  useLayoutEffect(() => {
    const area = scrollArea.current;
    if (!area || !visible || !loaded) return;
    if (initialized.current !== scope) {
      const saved = useWorkspace.getState().chatPositions[threadId];
      const node = [...area.querySelectorAll<HTMLElement>('[data-message-id]')].find(
        (item) => item.dataset.messageId === jump.id,
      );
      if (jump.id && !node) return;
      following.current = !jump.id;
      if (node) {
        const offset = jump.restore ? saved?.offset || 0 : -area.clientHeight / 3;
        area.scrollTop +=
          node.getBoundingClientRect().top - area.getBoundingClientRect().top + offset;
      } else area.scrollTop = area.scrollHeight;
      initialized.current = scope;
    } else if (prepended.current) {
      // 加载旧消息后按新增内容的高度补偿，屏幕内正在阅读的段落保持原位。
      area.scrollTop = prepended.current.top + area.scrollHeight - prepended.current.height;
      prepended.current = undefined;
    } else if (following.current) area.scrollTop = area.scrollHeight;
    setShowLatest(!following.current);
    lastPosition.current = readingPosition(area, following.current);
  }, [scope, threadId, jump.id, jump.restore, revision, visible, loaded]);
  useLayoutEffect(() => {
    const area = scrollArea.current;
    const root = area?.closest('.app-shell');
    if (!area || !root) return;
    const settled = () => {
      if (following.current) area.scrollTop = area.scrollHeight;
      onScroll();
    };
    root.addEventListener('workspace-layout-settled', settled);
    return () => root.removeEventListener('workspace-layout-settled', settled);
  }, [threadId, scope]);
  function onScroll() {
    const area = scrollArea.current;
    if (!area || initialized.current !== scope) return;
    // 分栏重排产生的滚动事件不逐帧写入持久化状态，结束后统一保存阅读位置。
    const root = area.closest<HTMLElement>('.app-shell');
    if (root?.dataset.resizing || root?.dataset.layoutMoving) return;
    // 搜索页的底部并非整段对话的末尾，不自动回到最新一页。
    following.current = !jump.id && area.scrollHeight - area.scrollTop - area.clientHeight < 64;
    setShowLatest(!following.current);
    lastPosition.current = readingPosition(area, following.current);
    if (threadId) useWorkspace.getState().saveChatPosition(threadId, lastPosition.current);
  }
  return { scrollArea, onScroll, showLatest, toLatest, preserveOnPrepend };
}
