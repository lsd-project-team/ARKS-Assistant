import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, jsonBody } from '../../../app/api/client';
import { toast } from '../../../shared/utils/toasts';
import { useWorkspace } from '../../../app/state/store';

type DragKind = 'project' | 'thread';
type DragGroup = 'pinned' | 'normal';

interface DragState {
  kind: DragKind;
  id: string;
  group: DragGroup;
  overProjectId?: string;
  overRecent?: boolean;
  beforeId?: string | null;
}

interface DragContextValue {
  state?: DragState;
  begin: (kind: DragKind, id: string, group: DragGroup) => void;
}

const DragContext = createContext<DragContextValue | null>(null);

export function useSidebarDrag() {
  return useContext(DragContext);
}

// 长按 400 毫秒进入拖拽；移动超过 8 像素视为滚动，避免和列表滚动冲突。
export function useLongPressDrag(kind: DragKind, id: string, group: DragGroup) {
  const drag = useSidebarDrag();
  const timer = useRef<number | undefined>(undefined);
  const origin = useRef<{ x: number; y: number } | undefined>(undefined);
  const suppress = useRef(false);
  const cancel = () => {
    if (timer.current !== undefined) window.clearTimeout(timer.current);
    timer.current = undefined;
  };
  useEffect(() => cancel, []);
  return {
    onPointerDown: (event: ReactPointerEvent) => {
      if (!drag || event.button !== 0 || drag.state) return;
      origin.current = { x: event.clientX, y: event.clientY };
      timer.current = window.setTimeout(() => {
        timer.current = undefined;
        suppress.current = true;
        drag.begin(kind, id, group);
      }, 400);
    },
    onPointerMove: (event: ReactPointerEvent) => {
      if (!origin.current || timer.current === undefined) return;
      if (
        Math.abs(event.clientX - origin.current.x) > 8 ||
        Math.abs(event.clientY - origin.current.y) > 8
      )
        cancel();
    },
    onPointerUp: cancel,
    onPointerCancel: cancel,
    onClickCapture: (event: ReactMouseEvent) => {
      if (!suppress.current) return;
      suppress.current = false;
      event.preventDefault();
      event.stopPropagation();
    },
    onContextMenu: (event: ReactMouseEvent) => {
      if (!suppress.current) return;
      event.preventDefault();
    },
  };
}

function projectRows(group: DragGroup) {
  return Array.from(
    document.querySelectorAll<HTMLElement>(
      `[data-project-id][data-pinned="${group === 'pinned' ? 'true' : 'false'}"]`,
    ),
  );
}

export function SidebarDragProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<DragState | undefined>(undefined);
  const drag = useRef<DragState | undefined>(undefined);
  const cache = useQueryClient();

  const update = useCallback((next: DragState | undefined) => {
    drag.current = next;
    setState(next);
  }, []);

  const begin = useCallback(
    (kind: DragKind, id: string, group: DragGroup) => update({ kind, id, group }),
    [update],
  );

  const active = !!state;
  useEffect(() => {
    if (!active) return;
    document.body.classList.add('sidebar-dragging');
    const onMove = (event: PointerEvent) => {
      const current = drag.current;
      if (!current) return;
      const hit = document.elementFromPoint(event.clientX, event.clientY);
      if (!hit || !(hit instanceof Element)) return;
      if (current.kind === 'thread') {
        const recent = hit.closest('[data-recent-drop]');
        const project = hit.closest<HTMLElement>('[data-project-id]');
        const projectOk =
          project &&
          project.dataset.projectId !== current.id &&
          project.dataset.projectId !== undefined;
        update({
          ...current,
          overRecent: !project && !!recent,
          overProjectId: projectOk ? project.dataset.projectId : undefined,
          beforeId: undefined,
        });
        return;
      }
      const target = hit.closest<HTMLElement>('[data-project-id]');
      if (!target || target.dataset.projectId === current.id) {
        update({ ...current, overProjectId: undefined, beforeId: undefined });
        return;
      }
      if (target.dataset.pinned !== (current.group === 'pinned' ? 'true' : 'false')) {
        update({ ...current, overProjectId: undefined, beforeId: undefined });
        return;
      }
      const rows = projectRows(current.group);
      const index = rows.indexOf(target);
      const rect = target.getBoundingClientRect();
      const after = event.clientY > rect.top + rect.height / 2;
      const beforeId = after
        ? (rows[index + 1]?.dataset.projectId ?? null)
        : target.dataset.projectId;
      update({ ...current, overProjectId: target.dataset.projectId, beforeId: beforeId ?? null });
    };

    const finish = async () => {
      const current = drag.current;
      update(undefined);
      if (!current) return;
      try {
        if (current.kind === 'project') {
          if (!current.overProjectId) return;
          if (current.beforeId === current.id) return;
          await api(`/projects/${current.id}/order`, {
            method: 'POST',
            body: jsonBody({ before_id: current.beforeId ?? null }),
          });
          await cache.invalidateQueries({ queryKey: ['projects'] });
          toast('项目顺序已调整');
          return;
        }
        if (current.overProjectId) {
          await api('/projects/move-threads', {
            method: 'POST',
            body: jsonBody({ ids: [current.id], project_id: current.overProjectId }),
          });
          if (useWorkspace.getState().threadId === current.id)
            useWorkspace.getState().selectThread('');
          await cache.invalidateQueries({ queryKey: ['threads'] });
          await cache.invalidateQueries({ queryKey: ['project-threads'] });
          await cache.invalidateQueries({ queryKey: ['projects'] });
          toast('对话已移动');
        } else if (current.overRecent) {
          await api('/projects/move-threads', {
            method: 'POST',
            body: jsonBody({ ids: [current.id], project_id: null }),
          });
          if (useWorkspace.getState().threadId === current.id)
            useWorkspace.getState().selectThread('');
          await cache.invalidateQueries({ queryKey: ['threads'] });
          await cache.invalidateQueries({ queryKey: ['project-threads'] });
          await cache.invalidateQueries({ queryKey: ['projects'] });
          toast('对话已移到最近对话');
        }
      } catch (error) {
        toast(error instanceof Error ? error.message : '拖拽操作失败', undefined, 'error');
      }
    };

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', finish);
    window.addEventListener('pointercancel', finish);
    const preventScroll = (event: TouchEvent) => event.preventDefault();
    document.addEventListener('touchmove', preventScroll, { passive: false });
    return () => {
      document.body.classList.remove('sidebar-dragging');
      document.removeEventListener('touchmove', preventScroll);
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', finish);
      window.removeEventListener('pointercancel', finish);
    };
  }, [active, update, cache]);

  return <DragContext.Provider value={{ state, begin }}>{children}</DragContext.Provider>;
}
