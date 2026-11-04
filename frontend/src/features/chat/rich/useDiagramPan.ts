import { useCallback, useEffect, useRef, useState, type RefObject } from 'react';

type Drag = { element: HTMLDivElement; pointerId: number; x: number; y: number };

export function useDiagramPan(viewport: RefObject<HTMLDivElement | null>, enabled: boolean) {
  const drag = useRef<Drag>(undefined);
  const [dragging, setDragging] = useState(false);
  const cancelPan = useCallback(() => {
    const current = drag.current;
    if (!current) return;
    drag.current = undefined;
    setDragging(false);
    if (current.element.hasPointerCapture(current.pointerId))
      current.element.releasePointerCapture(current.pointerId);
  }, []);

  useEffect(() => {
    const element = viewport.current;
    if (!element || !enabled) return;
    const down = (event: PointerEvent) => {
      if (event.pointerType !== 'mouse' || event.button !== 0 || !event.isPrimary || drag.current)
        return;
      const rect = element.getBoundingClientRect();
      const left = rect.left + element.clientLeft;
      const top = rect.top + element.clientTop;
      // 滚动条仍交给浏览器操作，只有图内按下左键才进入拖动。
      if (
        event.clientX < left ||
        event.clientX >= left + element.clientWidth ||
        event.clientY < top ||
        event.clientY >= top + element.clientHeight
      )
        return;
      event.preventDefault();
      element.focus({ preventScroll: true });
      element.setPointerCapture(event.pointerId);
      drag.current = { element, pointerId: event.pointerId, x: event.clientX, y: event.clientY };
      setDragging(true);
    };
    const move = (event: PointerEvent) => {
      const current = drag.current;
      if (!current || current.pointerId !== event.pointerId) return;
      if (!(event.buttons & 1)) {
        cancelPan();
        return;
      }
      event.preventDefault();
      element.scrollLeft -= event.clientX - current.x;
      element.scrollTop -= event.clientY - current.y;
      // 每次按实际位置推进，抵达滚动边界后反向拖动可以立即移动。
      current.x = event.clientX;
      current.y = event.clientY;
    };
    const stop = (event: PointerEvent) => {
      if (drag.current?.pointerId === event.pointerId) cancelPan();
    };
    const win = element.ownerDocument.defaultView;
    element.addEventListener('pointerdown', down);
    element.addEventListener('pointermove', move);
    element.addEventListener('pointerup', stop);
    element.addEventListener('pointercancel', stop);
    element.addEventListener('lostpointercapture', stop);
    win?.addEventListener('blur', cancelPan);
    return () => {
      cancelPan();
      element.removeEventListener('pointerdown', down);
      element.removeEventListener('pointermove', move);
      element.removeEventListener('pointerup', stop);
      element.removeEventListener('pointercancel', stop);
      element.removeEventListener('lostpointercapture', stop);
      win?.removeEventListener('blur', cancelPan);
    };
  }, [viewport, enabled, cancelPan]);

  return { dragging, cancelPan };
}
