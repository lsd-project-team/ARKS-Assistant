import { useProjectApi } from '../../projects/hooks/useProjectApi';
import { useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { jsonBody, query } from '../../../app/api/client';
import { blankMemory, memorySignature, validateMemory, type DraftMemory } from '../lib/memoryDraft';
import type { Memory, MemoryReview, MemoryRevision } from '../../../shared/types/api';
import { toast } from '../../../shared/utils/toasts';
import { useUnsavedGuard } from '../../../shared/hooks/useUnsavedGuard';

export function useMemoryDraft(open: boolean, onClose: () => void) {
  const api = useProjectApi();
  const cache = useQueryClient();
  const memories = useQuery({
    queryKey: ['memories'],
    queryFn: () => api<Memory[]>('/memories?include_deleted=true'),
    enabled: open,
  });
  const [draft, setDraft] = useState<DraftMemory>(blankMemory);
  const [baseline, setBaseline] = useState(() => memorySignature(blankMemory()));
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [review, setReview] = useState<MemoryReview[]>([]);
  const [restoring, setRestoring] = useState<MemoryRevision>();
  const submitting = useRef(false);
  const dirty = memorySignature(draft) !== baseline;
  const guard = useUnsavedGuard(open && dirty, busy);
  function reset(memory: DraftMemory) {
    setDraft(memory);
    setBaseline(memorySignature(memory));
    setError(undefined);
    setDeleting(false);
    setReview([]);
    setRestoring(undefined);
    guard.cancel();
  }
  async function perform(action: () => Promise<void>) {
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError(undefined);
    try {
      await action();
      await cache.invalidateQueries({ queryKey: ['memories'] });
      await cache.invalidateQueries({ queryKey: ['memory-history'] });
    } catch (reason) {
      setError(reason);
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }
  function payload(memory: DraftMemory) {
    return { ...memory, source_paths: memory.sources?.map((row) => row.path) || [] };
  }
  function reviewedVersions() {
    return Object.fromEntries(review.map((row) => [row.name, row.version]));
  }
  async function save(confirmed = false) {
    const errors = validateMemory(draft);
    if (errors.length) throw new Error(errors.join('；'));
    if (!confirmed) {
      const matches = await api<MemoryReview[]>('/memories/review', {
        method: 'POST',
        body: jsonBody(payload(draft)),
      });
      setReview(matches);
      if (matches.length) return;
    }
    const memory = await api<Memory>('/memories', {
      method: 'PUT',
      body: jsonBody({
        ...payload(draft),
        confirm_conflicts: confirmed,
        reviewed_versions: confirmed ? reviewedVersions() : {},
      }),
    });
    reset(memory);
    toast('记忆已保存');
  }
  async function remove() {
    await api(`/memories/${draft.scope}/${query(draft.name)}?version=${draft.version}`, {
      method: 'DELETE',
    });
    reset(blankMemory());
    toast('记忆已删除，可从历史版本恢复');
  }
  async function restore() {
    if (!restoring) return;
    const memory = await api<Memory>(`/memories/${draft.scope}/${query(draft.name)}/restore`, {
      method: 'POST',
      body: jsonBody({
        revision_id: restoring.id,
        version: draft.version || null,
        record_version: draft.record_version,
        confirm_conflicts: true,
        reviewed_versions: reviewedVersions(),
      }),
    });
    reset(memory);
    toast('记忆版本已恢复，覆盖前的内容仍保留');
  }
  // 切页签、关闭设置和打开来源共用退出流程，避免未保存的记忆草稿被直接丢弃。
  function leave(action: () => void) {
    guard.request(() => {
      reset(blankMemory());
      action();
    });
  }
  return {
    memories,
    draft,
    setDraft: (memory: DraftMemory) => {
      setDraft(memory);
      setReview([]);
      setRestoring(undefined);
    },
    busy,
    error,
    dirty,
    deleting,
    setDeleting,
    guard,
    review,
    restoring,
    cancelReview: () => {
      setReview([]);
      setRestoring(undefined);
    },
    openRelated: (row: MemoryReview) => {
      const memory = memories.data?.find(
        (item) => item.name === row.name && item.scope === row.scope,
      );
      if (memory) guard.request(() => reset(memory));
    },
    prepareRestore: (revision: MemoryRevision) =>
      guard.request(() => {
        void perform(async () => {
          const matches = await api<MemoryReview[]>('/memories/review', {
            method: 'POST',
            body: jsonBody({ ...revision, source_paths: [] }),
          });
          setReview(matches);
          setRestoring(revision);
        });
      }),
    confirmReview: () => perform(() => (restoring ? restore() : save(true))),
    errors: validateMemory(draft),
    select: (memory: DraftMemory) => guard.request(() => reset(memory)),
    leave,
    close: () => leave(onClose),
    reload: () =>
      guard.request(() => {
        void perform(async () => {
          const result = await memories.refetch();
          if (result.error) throw result.error;
          const latest = result.data?.find(
            (row) => row.name === draft.name && row.scope === draft.scope,
          );
          if (latest) reset(latest);
          else throw new Error('记忆可能已被删除，请选择其他条目或新增记忆');
        });
      }),
    save: () => perform(() => save()),
    remove: () => perform(remove),
  };
}
