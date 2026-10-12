import { useEffect, useRef, type PointerEvent } from 'react';
import {
  animateLayout,
  measureLayout,
  rememberLayout,
  stopLayoutMotion,
  takeLayoutSnapshot,
} from '../lib/layoutMotion';

type Drag = {
  root: HTMLElement;
  offset: number;
  requested: number;
  cursor: string;
  userSelect: string;
  frame: number;
  preview: (width: number) => void;
  settle: (width: number) => void;
};

export function useDividerDrag() {
  const drag = useRef<Drag | null>(null);
  const clear = () => {
    const current = drag.current;
    if (!current) return;
    cancelAnimationFrame(current.frame);
    document.body.style.cursor = current.cursor;
    document.body.style.userSelect = current.userSelect;
    delete current.root.dataset.resizing;
    ['--drag-navigation-width', '--drag-chat-width', '--drag-file-width'].forEach((property) =>
      current.root.style.removeProperty(property),
    );
    drag.current = null;
  };
  useEffect(() => clear, []);

  return {
    begin(
      event: PointerEvent<HTMLElement>,
      width: number,
      requested: number,
      kind: string,
      preview: Drag['preview'],
      settle: Drag['settle'],
    ) {
      if (event.button !== 0 || !event.isPrimary) return;
      event.preventDefault();
      event.currentTarget.focus();
      const root = event.currentTarget.closest<HTMLElement>('.app-shell')!;
      stopLayoutMotion(root);
      drag.current = {
        root,
        offset: requested - width,
        requested: width,
        cursor: document.body.style.cursor,
        userSelect: document.body.style.userSelect,
        frame: 0,
        preview,
        settle,
      };
      root.dataset.resizing = kind;
      preview(width);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    move(event: PointerEvent<HTMLElement>, requested: number) {
      const current = drag.current;
      if (!current || !event.currentTarget.hasPointerCapture(event.pointerId)) return;
      current.requested = requested - current.offset;
      if (current.frame) return;
      // 高频指针事件合并到每帧；拖动不写持久化状态，也不重绘整个 React 工作区。
      current.frame = requestAnimationFrame(() => {
        current.frame = 0;
        current.preview(current.requested);
      });
    },
    end(event: PointerEvent<HTMLElement>, cancelled = false) {
      const current = drag.current;
      if (!current) return;
      current.preview(current.requested);
      const from = measureLayout(current.root);
      rememberLayout(current.root);
      clear();
      if (event.currentTarget.hasPointerCapture(event.pointerId))
        event.currentTarget.releasePointerCapture(event.pointerId);
      if (!cancelled) current.settle(current.requested);
      // 取消或松手回弹至原宽度时，状态可能未改变，仍完成视觉过渡。
      requestAnimationFrame(() => {
        const pending = takeLayoutSnapshot(current.root);
        if (pending && !current.root.dataset.layoutMoving && current.root.isConnected) {
          animateLayout(current.root, from, measureLayout(current.root));
        }
      });
    },
  };
}
