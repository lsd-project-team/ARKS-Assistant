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
  start: (kind: DragKind, id: string, group: DragGroup) => void;
  hoverProject: (projectId: string, beforeId: string | null) => void;
  hoverRecent: () => void;
  hoverNone: () => void;
  drop: () => Promise<void>;
  end: () => void;
}

const DragContext = createContext<DragContextValue | null>(null);

export function useSidebarDrag() {
  return useContext(DragContext);
}

// 与 DeepSeek Harness 一致：使用浏览器原生拖拽，拖到行的上半/下半显示插入线。
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
        if (!active) return;
        if (
          active.kind === 'project' &&
          active.beforeId === beforeId &&
          active.overProjectId === projectId
        )
          return;
        set({ ...active, overProjectId: projectId, overRecent: false, beforeId });
      },
      hoverRecent: () => {
        const active = current.current;
        if (!active || active.kind !== 'thread' || active.overRecent) return;
        set({ ...active, overProjectId: undefined, overRecent: true, beforeId: undefined });
      },
      hoverNone: () => {
        const active = current.current;
        if (!active || (!active.overProjectId && !active.overRecent)) return;
        set({ ...active, overProjectId: undefined, overRecent: false, beforeId: undefined });
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
          if (active.overProjectId) {
            await api('/projects/move-threads', {
              method: 'POST',
              body: jsonBody({ ids: [active.id], project_id: active.overProjectId }),
            });
            if (useWorkspace.getState().threadId === active.id)
              useWorkspace.getState().selectThread('');
            await cache.invalidateQueries({ queryKey: ['threads'] });
            await cache.invalidateQueries({ queryKey: ['project-threads'] });
            await cache.invalidateQueries({ queryKey: ['projects'] });
            toast('对话已移动');
          } else if (active.overRecent) {
            await api('/projects/move-threads', {
              method: 'POST',
              body: jsonBody({ ids: [active.id], project_id: null }),
            });
            if (useWorkspace.getState().threadId === active.id)
              useWorkspace.getState().selectThread('');
            await cache.invalidateQueries({ queryKey: ['threads'] });
            await cache.invalidateQueries({ queryKey: ['project-threads'] });
            await cache.invalidateQueries({ queryKey: ['projects'] });
            toast('对话已移到最近对话');
          }
        } catch (error) {
          toast(error instanceof Error ? error.message : '拖拽操作失败', undefined, 'error');
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
