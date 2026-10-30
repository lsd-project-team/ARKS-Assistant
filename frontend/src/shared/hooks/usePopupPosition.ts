import { useLayoutEffect, useState, type CSSProperties, type RefObject } from 'react';

export function usePopupPosition(
  open: boolean,
  popup: RefObject<HTMLElement | null>,
  trigger: RefObject<HTMLElement | null>,
  point?: { left: number; top: number },
): CSSProperties {
  const [position, setPosition] = useState<CSSProperties>({ visibility: 'hidden' });
  useLayoutEffect(() => {
    if (!open) return;
    const place = () => {
      const element = popup.current;
      const anchor = trigger.current?.getBoundingClientRect();
      if (!element || !anchor) return;
      const bounds = element.getBoundingClientRect();
      const margin = 8;
      let top = point?.top ?? anchor.bottom + 6;
      // 按菜单实际高度避让视口；右键入口保留鼠标位置，按钮入口可向上展开。
      if (!point && top + bounds.height > window.innerHeight - margin)
        top = anchor.top - bounds.height - 6;
      setPosition({
        left: Math.max(
          margin,
          Math.min(
            point?.left ?? anchor.right - bounds.width,
            window.innerWidth - bounds.width - margin,
          ),
        ),
        top: Math.max(margin, Math.min(top, window.innerHeight - bounds.height - margin)),
        visibility: 'visible',
      });
    };
    place();
    const observer = new ResizeObserver(place);
    if (popup.current) observer.observe(popup.current);
    window.addEventListener('resize', place);
    return () => {
      observer.disconnect();
      window.removeEventListener('resize', place);
    };
  }, [open, popup, trigger, point]);
  return position;
}
