import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { MoreHorizontal } from 'lucide-react';
import { usePopupPosition } from '../../../shared/hooks/usePopupPosition';
import { api, jsonBody } from '../../../app/api/client';
import { toast } from '../../../shared/utils/toasts';
import type { Project } from '../../../shared/types/api';

export function ProjectMenu({ project, onEdit }: { project: Project; onEdit: () => void }) {
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const popup = useRef<HTMLDivElement>(null);
  const position = usePopupPosition(open, popup, trigger);
  const close = () => {
    setOpen(false);
    trigger.current?.focus();
  };
  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => {
      if (
        !popup.current?.contains(event.target as Node) &&
        !trigger.current?.contains(event.target as Node)
      )
        setOpen(false);
    };
    document.addEventListener('pointerdown', outside);
    return () => document.removeEventListener('pointerdown', outside);
  }, [open]);
  useEffect(() => {
    if (open && position.visibility === 'visible')
      popup.current?.querySelector<HTMLButtonElement>('button')?.focus();
  }, [open, position.visibility]);
  async function change(path: string, body: unknown, method = 'PATCH') {
    close();
    setPending(true);
    try {
      await api(`/projects/${project.id}${path}`, { method, body: jsonBody(body) });
      toast('项目已更新');
    } catch (error) {
      toast(error instanceof Error ? error.message : '操作失败', undefined, 'error');
    } finally {
      setPending(false);
    }
  }
  return (
    <>
      <button
        ref={trigger}
        className="project-hover-action"
        aria-label={`项目操作：${project.name}`}
        title="项目操作"
        aria-haspopup="menu"
        aria-expanded={open}
        disabled={pending}
        onClick={() => setOpen(!open)}
      >
        <MoreHorizontal size={15} />
      </button>
      {open &&
        createPortal(
          <div
            ref={popup}
            className="thread-menu"
            style={position}
            role="menu"
            aria-label={`项目操作：${project.name}`}
            onKeyDown={(event) => {
              if (['Escape', 'Tab'].includes(event.key)) {
                close();
                return;
              }
              if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
              event.preventDefault();
              const items = Array.from(
                event.currentTarget.querySelectorAll<HTMLButtonElement>('button'),
              );
              const index = items.indexOf(document.activeElement as HTMLButtonElement);
              const next =
                event.key === 'Home'
                  ? 0
                  : event.key === 'End'
                    ? items.length - 1
                    : (index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
              items[next]?.focus();
            }}
          >
            <button
              role="menuitem"
              onClick={() => {
                close();
                onEdit();
              }}
            >
              项目设置与重命名
            </button>
            <button
              role="menuitem"
              onClick={() => void change('', { pinned: project.pinned_order === null })}
            >
              {project.pinned_order === null ? '置顶项目' : '取消置顶项目'}
            </button>
            <button
              role="menuitem"
              onClick={() => void change('/position', { direction: -1 }, 'POST')}
            >
              向上移动
            </button>
            <button
              role="menuitem"
              onClick={() => void change('/position', { direction: 1 }, 'POST')}
            >
              向下移动
            </button>
            <button
              role="menuitem"
              onClick={() =>
                void change('', { state: project.state === 'archived' ? 'active' : 'archived' })
              }
            >
              {project.state === 'archived' ? '恢复项目' : '归档项目'}
            </button>
          </div>,
          document.body,
        )}
    </>
  );
}
