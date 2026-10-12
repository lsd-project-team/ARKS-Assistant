import { useProjectApi } from './useProjectApi';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { jsonBody } from '../lib/api';
import type { ConversationDraft } from '../lib/store';
import type { QuestionQueue, QueuedQuestion, Run } from '../types';

export function useQuestionQueue(threadId: string, onStarted: (run: Run) => void) {
  const api = useProjectApi();
  const cache = useQueryClient();
  const query = useQuery({
    queryKey: ['queue', threadId],
    queryFn: () => api<QuestionQueue>(`/threads/${threadId}/queue`),
    enabled: !!threadId,
    refetchInterval: 3000,
  });
  async function refresh(id: string) {
    await Promise.all([
      cache.invalidateQueries({ queryKey: ['queue', id] }),
      cache.invalidateQueries({ queryKey: ['thread', id] }),
      cache.invalidateQueries({ queryKey: ['threads'] }),
    ]);
  }
  const control = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'pause' | 'continue' }) =>
      api<QuestionQueue & { started_run: Run | null }>(`/threads/${id}/queue/${action}`, {
        method: 'POST',
      }),
    onSuccess: (result, { id }) => {
      if (result.started_run) onStarted(result.started_run);
      void refresh(id);
    },
  });
  const remove = useMutation({
    mutationFn: (item: QueuedQuestion) => api(`/queue/${item.id}`, { method: 'DELETE' }),
    onSettled: (_result, _error, item) => {
      void refresh(item.thread_id);
    },
  });
  const edit = useMutation({
    mutationFn: ({ item, draft }: { item: QueuedQuestion; draft: ConversationDraft }) =>
      api<QueuedQuestion>(`/queue/${item.id}`, {
        method: 'PATCH',
        body: jsonBody({ ...draft, version: item.updated_at }),
      }),
    onSettled: (_result, _error, { item }) => {
      void refresh(item.thread_id);
    },
  });
  return { query, control, remove, edit, refresh };
}
