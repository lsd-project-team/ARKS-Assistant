import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api as request, apiUrl, jsonBody } from '../../../app/api/client';
import { projectCache, invalidateProjectCaches } from '../../projects/lib/projectCache';
import { threadProject } from '../lib/sidebarNavigation';
import { useWorkspace } from '../../../app/state/store';
import type { Thread } from '../../../shared/types/api';
import type { ThreadAction } from '../components/ThreadItem';
import { toast } from '../../../shared/utils/toasts';

export function useSidebarActions() {
  const [pending, setPending] = useState('');
  const [purging, setPurging] = useState<Thread>();
  const [error, setError] = useState<unknown>();
  const [moving, setMoving] = useState<string[]>();
  // 全局最近列表可操作其他项目的对话；每次请求绑定行的归属，不能借用前台项目。
  const threadApi =
    (row: Thread) =>
    <T>(path: string, options?: RequestInit) =>
      request<T>(path, options, threadProject(row));
  const { selectThread, forgetThread, restoreDraft } = useWorkspace();
  const cache = useQueryClient();
  const refresh = () =>
    invalidateProjectCaches([
      'threads',
      'project-threads',
      'thread',
      'projects',
      'project',
      'memories',
    ]);
  async function rename(row: Thread, title: string) {
    const api = threadApi(row);
    setPending(row.id);
    try {
      await api(`/threads/${row.id}`, { method: 'PATCH', body: jsonBody({ title }) });
      await refresh();
      await cache.invalidateQueries({ queryKey: ['thread', row.id] });
      toast('对话已重命名');
    } finally {
      setPending('');
    }
  }
  async function restore(row: Thread) {
    const api = threadApi(row);
    await api(`/threads/${row.id}/restore`, { method: 'POST' });
    await refresh();
  }
  async function act(row: Thread, action: ThreadAction) {
    const api = threadApi(row);
    if (action === 'move') {
      setMoving([row.id]);
      return;
    }
    if (action === 'purge') {
      setPurging(row);
      return;
    }
    setPending(row.id);
    setError(undefined);
    try {
      if (action === 'delete') {
        const draft = useWorkspace.getState().drafts[row.id];
        const position = useWorkspace.getState().chatPositions[row.id];
        await api(`/threads/${row.id}`, { method: 'DELETE' });
        forgetThread(row.id);
        projectCache(threadProject(row)).removeQueries({ queryKey: ['thread', row.id] });
        toast('对话已移入回收站', {
          label: '撤销',
          run: async () => {
            await restore(row);
            useWorkspace.getState().switchProject(threadProject(row));
            if (draft) restoreDraft(row.id, draft);
            if (position) useWorkspace.getState().saveChatPosition(row.id, position);
            selectThread(row.id);
          },
        });
      } else if (action === 'restore') {
        await restore(row);
        toast('对话已恢复');
      } else if (action === 'archive') {
        await api(`/threads/${row.id}`, { method: 'PATCH', body: jsonBody({ state: 'archived' }) });
        if (useWorkspace.getState().threadId === row.id) selectThread('');
        toast('对话已归档', { label: '撤销', run: () => restore(row) });
      } else if (action === 'pin') {
        const pinned = row.pinned_order !== null && row.pinned_order !== undefined;
        await api(`/threads/${row.id}`, { method: 'PATCH', body: jsonBody({ pinned: !pinned }) });
        toast(pinned ? '已取消置顶' : '对话已置顶');
      } else if (action === 'up' || action === 'down') {
        await api(`/threads/${row.id}/pin-position`, {
          method: 'POST',
          body: jsonBody({ direction: action === 'up' ? -1 : 1 }),
        });
        toast('置顶顺序已调整');
      } else if (action === 'export') {
        const response = await fetch(apiUrl(`/threads/${row.id}/export`, threadProject(row)));
        if (!response.ok) throw new Error('导出失败，请重试');
        const url = URL.createObjectURL(await response.blob());
        const link = document.createElement('a');
        link.href = url;
        link.download = `${row.title.replace(/[\\/:*?"<>|]/g, '_')}.md`;
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        toast('对话已导出');
      }
      await refresh();
    } catch (reason) {
      setError(reason);
      toast(reason instanceof Error ? reason.message : '操作失败，请重试', undefined, 'error');
    } finally {
      setPending('');
    }
  }
  async function permanentlyDelete() {
    if (!purging) return;
    const api = threadApi(purging);
    setPending(purging.id);
    try {
      await api(`/threads/${purging.id}/permanent`, { method: 'DELETE' });
      forgetThread(purging.id);
      projectCache(threadProject(purging)).removeQueries({ queryKey: ['thread', purging.id] });
      setPurging(undefined);
      await refresh();
      toast('对话及关联记录已彻底删除');
    } catch (reason) {
      setError(reason);
    } finally {
      setPending('');
    }
  }
  return {
    pending,
    purging,
    setPurging,
    error,
    setError,
    moving,
    setMoving,
    rename,
    act,
    permanentlyDelete,
  };
}
