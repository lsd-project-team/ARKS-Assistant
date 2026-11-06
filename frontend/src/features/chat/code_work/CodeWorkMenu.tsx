import { useEffect, useId, useRef, useState } from 'react';
import { MoreHorizontal } from 'lucide-react';

type MenuItem = { label: string; onSelect: () => void; disabled?: boolean };

/** 菜单留在当前容器内，弹窗和嵌入式面板共用同一套焦点与键盘行为。 */
export function CodeWorkMenu({
  items,
  label = '更多变更操作',
}: {
  items: MenuItem[];
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const close = () => {
    setOpen(false);
    trigger.current?.focus();
  };
  useEffect(() => {
    if (!open) return;
    menu.current?.querySelector<HTMLButtonElement>('button:not(:disabled)')?.focus();
    const outside = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('pointerdown', outside);
    return () => document.removeEventListener('pointerdown', outside);
  }, [open]);
  return (
    <div ref={root} className="code-work-options">
      <button
        ref={trigger}
        type="button"
        className="button icon-button"
        aria-label={label}
        title={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        onClick={() => setOpen(!open)}
        onKeyDown={(event) => {
          if (event.key === 'ArrowDown') {
            event.preventDefault();
            setOpen(true);
          }
        }}
      >
        <MoreHorizontal size={17} />
      </button>
      {open && (
        <div
          ref={menu}
          id={id}
          className="code-work-options-menu"
          role="menu"
          aria-label={label}
          onKeyDown={(event) => {
            if (event.key === 'Escape' || event.key === 'Tab') {
              event.stopPropagation();
              if (event.key === 'Escape') event.preventDefault();
              close();
              return;
            }
            if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
            event.preventDefault();
            const buttons = Array.from(
              event.currentTarget.querySelectorAll<HTMLButtonElement>('button:not(:disabled)'),
            );
            const current = buttons.indexOf(document.activeElement as HTMLButtonElement);
            const next =
              event.key === 'Home'
                ? 0
                : event.key === 'End'
                  ? buttons.length - 1
                  : (current + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) %
                    buttons.length;
            buttons[next]?.focus();
          }}
        >
          {items.map((item) => (
            <button
              type="button"
              role="menuitem"
              key={item.label}
              disabled={item.disabled}
              onClick={() => {
                close();
                item.onSelect();
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
