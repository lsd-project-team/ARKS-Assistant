import { useProjectApi } from './useProjectApi';
import { useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ApiError } from '../lib/api';
import { useWorkspace } from '../lib/store';
import type { Conversation } from '../types';
import { toast } from '../lib/toasts';

export function useConversation(threadId: string) {
  const api = useProjectApi();
  const projectId = useWorkspace((state) => state.projectId);
  const jump = useWorkspace((state) => state.messageJump);
  const scope = `${threadId}:${jump.time}`;
  const [older, setOlder] = useState<{ scope: string; pages: Conversation[] }>({
    scope: '',
    pages: [],
  });
  const query = useQuery({
    queryKey: ['thread', threadId, jump.id],
    queryFn: () =>
      api<Conversation>(
        `/threads/${threadId}${jump.id ? `?around=${encodeURIComponent(jump.id)}` : ''}`,
      ),
    enabled: !!threadId,
    refetchInterval: (result) =>
      result.state.data?.runs.some((run) => ['queued', 'running'].includes(run.status))
        ? 3000
        : 10000,
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 2,
  });
  useEffect(() => {
    if (
      !(query.error instanceof ApiError) ||
      query.error.status !== 404 ||
      query.isFetching ||
      useWorkspace.getState().threadId !== threadId ||
      useWorkspace.getState().projectId !== projectId
    )
      return;
    if (jump.id) {
      useWorkspace.getState().clearMessageJump();
      return;
    }
    // 其他窗口删除时保留此窗口尚未发送的草稿，恢复会话后仍能继续编辑。
    useWorkspace.getState().selectThread('');
    toast('此对话已在其他窗口删除，草稿已保留，可到回收站恢复');
  }, [query.error, query.isFetching, threadId, jump.id, projectId]);
  const pages = older.scope === scope ? older.pages : [];
  const first = pages[0] || query.data;
  const loadOlder = useMutation({
    mutationFn: async () => ({
      scope,
      page: await api<Conversation>(
        `/threads/${threadId}?before=${encodeURIComponent(first?.before_cursor || '')}`,
      ),
    }),
    onSuccess: ({ scope: loadedScope, page }) =>
      setOlder((current) => ({
        scope: loadedScope,
        pages: [page, ...(current.scope === loadedScope ? current.pages : [])],
      })),
  });
  const data = query.data;
  if (!data || !pages.length) return { ...query, loadOlder };
  const messages = new Map(
    [...pages, data].flatMap((page) => page.messages).map((message) => [message.id, message]),
  );
  const runs = new Map([...pages, data].flatMap((page) => page.runs).map((run) => [run.id, run]));
  return {
    ...query,
    data: {
      ...data,
      messages: [...messages.values()],
      runs: [...runs.values()].sort((a, b) =>
        (a.created_at || '').localeCompare(b.created_at || ''),
      ),
      has_older: first?.has_older,
      before_cursor: first?.before_cursor,
    },
    loadOlder,
  };
}
