import { useLayoutEffect, useRef, useState } from 'react';

export function useFileTabScroll(activePath: string, paths: string[]) {
  const tabs = useRef<HTMLDivElement>(null);
  const [edges, setEdges] = useState({ overflow: false, backward: false, forward: false });

  useLayoutEffect(() => {
    const list = tabs.current;
    if (!list) return;
    const update = () => {
      const maximum = list.scrollWidth - list.clientWidth;
      const next = {
        overflow: maximum > 1,
        backward: list.scrollLeft > 1,
        forward: list.scrollLeft < maximum - 1,
      };
      setEdges((current) =>
        current.overflow === next.overflow &&
        current.backward === next.backward &&
        current.forward === next.forward
          ? current
          : next,
      );
    };
    const revealActive = () => {
      const active = list.querySelector<HTMLElement>('.code-tab.active');
      if (active) {
        const viewport = list.getBoundingClientRect();
        const bounds = active.getBoundingClientRect();
        // 只移动标签栏，避免 scrollIntoView 连带移动聊天区或整个工作区。
        if (bounds.left < viewport.left + 8) list.scrollLeft += bounds.left - viewport.left - 8;
        else if (bounds.right > viewport.right - 8)
          list.scrollLeft += bounds.right - viewport.right + 8;
      }
      update();
    };
    const wheel = (event: WheelEvent) => {
      if (event.ctrlKey || event.deltaX || !event.deltaY) return;
      const before = list.scrollLeft;
      const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? list.clientWidth : 1;
      list.scrollLeft += event.deltaY * unit;
      if (list.scrollLeft !== before) event.preventDefault();
    };
    const observer = new ResizeObserver(revealActive);
    observer.observe(list);
    list.addEventListener('scroll', update);
    list.addEventListener('wheel', wheel, { passive: false });
    revealActive();
    return () => {
      observer.disconnect();
      list.removeEventListener('scroll', update);
      list.removeEventListener('wheel', wheel);
    };
  }, [activePath, paths]);

  function scrollTabs(direction: number) {
    const list = tabs.current;
    if (!list) return;
    list.scrollBy({
      left: direction * Math.max(120, list.clientWidth * 0.75),
      behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
    });
  }

  return { tabs, ...edges, scrollTabs };
}
