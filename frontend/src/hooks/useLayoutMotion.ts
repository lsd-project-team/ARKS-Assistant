import { useLayoutEffect, useRef, useState } from 'react';
import {
  animateLayout,
  measureLayout,
  stopLayoutMotion,
  takeLayoutSnapshot,
} from '../lib/layoutMotion';

type Visibility = { collapsed: boolean; codeOpen: boolean; explorerOpen: boolean };

export function useLayoutMotion(state: Visibility, layoutKey: string) {
  const root = useRef<HTMLDivElement>(null);
  const [retained, setRetained] = useState(state);
  const sizes = useRef<ReturnType<typeof measureLayout> | null>(null);
  const lastKey = useRef(layoutKey);
  const generation = useRef(0);

  useLayoutEffect(() => {
    const element = root.current!;
    const observe = () => {
      if (!element.dataset.resizing && !element.dataset.layoutMoving) {
        sizes.current = measureLayout(element);
      }
    };
    observe();
    const observer = new ResizeObserver(observe);
    observer.observe(element);
    element
      .querySelectorAll('.app-navigation, .chat-pane, .file-explorer')
      .forEach((pane) => observer.observe(pane));
    return () => {
      observer.disconnect();
      stopLayoutMotion(element);
    };
  }, []);

  useLayoutEffect(() => {
    if (lastKey.current === layoutKey) return;
    lastKey.current = layoutKey;
    const element = root.current!;
    const from =
      takeLayoutSnapshot(element) ||
      (element.dataset.layoutMoving ? measureLayout(element) : sizes.current);
    stopLayoutMotion(element);
    const to = measureLayout(element);
    const current = ++generation.current;
    // 退出过渡结束前保留面板内容，避免宽度还在变化时编辑器就被卸载。
    const complete = () => {
      if (current !== generation.current) return;
      sizes.current = to;
      setRetained(state);
    };
    if (!from || (window.innerWidth <= 800 && state.collapsed === retained.collapsed)) complete();
    else animateLayout(element, from, to, complete);
  }, [layoutKey, state.collapsed, state.codeOpen, state.explorerOpen]);

  return {
    root,
    codeMounted: state.codeOpen || retained.codeOpen,
    filesMounted: state.explorerOpen || retained.explorerOpen,
    navigationExpanded: !state.collapsed || !retained.collapsed,
  };
}
