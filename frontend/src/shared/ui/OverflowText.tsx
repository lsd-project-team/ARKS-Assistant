import { useLayoutEffect, useRef, useState, type ReactNode } from 'react';

export function OverflowText({ children, className }: { children: ReactNode; className: string }) {
  const element = useRef<HTMLSpanElement>(null);
  const [overflowing, setOverflowing] = useState(false);
  useLayoutEffect(() => {
    const node = element.current;
    if (!node) return;
    let active = true;
    const measure = () => {
      if (active) setOverflowing(node.scrollWidth > node.clientWidth);
    };
    measure();
    const observer =
      typeof ResizeObserver !== 'undefined' ? new ResizeObserver(measure) : undefined;
    observer?.observe(node);
    const fonts = document.fonts;
    fonts?.ready.then(measure);
    fonts?.addEventListener('loadingdone', measure);
    return () => {
      active = false;
      observer?.disconnect();
      fonts?.removeEventListener('loadingdone', measure);
    };
  }, [children, className]);
  return (
    <span ref={element} className={className} data-overflow={overflowing || undefined}>
      {children}
    </span>
  );
}
