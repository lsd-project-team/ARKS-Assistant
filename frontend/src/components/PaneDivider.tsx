import { useEffect } from 'react';

function clearDragStyle() {
  document.body.style.cursor = '';
  document.body.style.userSelect = '';
}

function resizeChat(parent: HTMLElement, width: number) {
  // 从左侧计算问答宽度，同时为右侧源码保留可用空间。
  const maximum = Math.max(320, Math.min(720, parent.clientWidth - 350));
  parent.style.setProperty('--chat-width', `${Math.min(maximum, Math.max(320, width))}px`);
}

export function PaneDivider() {
  useEffect(() => clearDragStyle, []);
  return (
    <div
      className="pane-divider"
      role="separator"
      aria-label="调整问答和源码宽度"
      aria-orientation="vertical"
      tabIndex={0}
      onPointerDown={(event) => {
        event.currentTarget.setPointerCapture(event.pointerId);
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
      }}
      onPointerMove={(event) => {
        if (!event.currentTarget.hasPointerCapture(event.pointerId)) return;
        const parent = event.currentTarget.parentElement!;
        resizeChat(parent, event.clientX - parent.getBoundingClientRect().left);
      }}
      onPointerUp={(event) => {
        event.currentTarget.releasePointerCapture(event.pointerId);
        clearDragStyle();
      }}
      onLostPointerCapture={clearDragStyle}
      onKeyDown={(event) => {
        if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
        event.preventDefault();
        const parent = event.currentTarget.parentElement!;
        const width = parent.querySelector('.chat-pane')!.getBoundingClientRect().width;
        resizeChat(parent, width + (event.key === 'ArrowLeft' ? -24 : 24));
      }}
    />
  );
}
