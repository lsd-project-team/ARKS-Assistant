import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, jsonBody } from '../../../app/api/client';
import { toast } from '../../../shared/utils/toasts';

type DragKind = 'project' | 'thread';

interface DragState {
  kind: DragKind;
  id: string;
  group?: 'pinned' | 'normal';
  overProjectId?: string;
  overThreadId?: string;
  beforeId?: string | null;
}

interface DragContextValue {
  state?: DragState;
  start: (kind: DragKind, id: string, group?: 'pinned' | 'normal') => void;
  hoverProject: (projectId: string, beforeId: string | null) => void;
  hoverThread: (beforeId: string | null) => void;
  hoverNone: () => void;
  drop: () => Promise<void>;
  end: () => void;
}

const DragContext = createContext<DragContextValue | null>(null);

export function useSidebarDrag() {
  return useContext(DragContext);
}

export function SidebarDragProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<DragState | undefined>(undefined);
  const current = useRef<DragState | undefined>(undefined);
  const committed = useRef(false);
  const cache = useQueryClient();

  const set = useCallback((next: DragState | undefined) => {
    current.current = next;
    setState(next);
  }, []);

  const value = useMemo<DragContextValue>(
    () => ({
      state,
      start: (kind, id, group) => {
        committed.current = false;
        set({ kind, id, group });
      },
      hoverProject: (projectId, beforeId) => {
        const active = current.current;
        if (!active || active.kind !== 'project') return;
        if (active.overProjectId === projectId && active.beforeId === beforeId) return;
        set({ ...active, overProjectId: projectId, beforeId });
      },
      hoverThread: (beforeId) => {
        const active = current.current;
        if (!active || active.kind !== 'thread') return;
        if (active.overThreadId === active.id && active.beforeId === beforeId) return;
        set({ ...active, overThreadId: active.id, beforeId });
      },
      hoverNone: () => {
        const active = current.current;
        if (!active || (!active.overProjectId && active.overThreadId === undefined)) return;
        set({ ...active, overProjectId: undefined, overThreadId: undefined, beforeId: undefined });
      },
      drop: async () => {
        const active = current.current;
        if (!active || committed.current) return;
        committed.current = true;
        set(undefined);
        try {
          if (active.kind === 'project') {
            if (!active.overProjectId || active.beforeId === active.id) return;
            await api(`/projects/${active.id}/order`, {
              method: 'POST',
              body: jsonBody({ before_id: active.beforeId ?? null }),
            });
            await cache.invalidateQueries({ queryKey: ['projects'] });
            toast('项目顺序已调整');
            return;
          }
          if (active.overThreadId === undefined) return;
          await api(`/threads/${active.id}/order`, {
            method: 'POST',
            body: jsonBody({ before_id: active.beforeId ?? null }),
          });
          await cache.invalidateQueries({ queryKey: ['threads'] });
          await cache.invalidateQueries({ queryKey: ['project-threads'] });
          toast('对话顺序已调整');
        } catch (error) {
          toast(error instanceof Error ? error.message : '拖动操作失败', undefined, 'error');
        }
      },
      end: () => {
        committed.current = false;
        set(undefined);
      },
    }),
    [state, set, cache],
  );

  return <DragContext.Provider value={value}>{children}</DragContext.Provider>;
}
