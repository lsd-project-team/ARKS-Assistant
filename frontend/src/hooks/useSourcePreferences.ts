import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { jsonBody } from '../lib/api';
import type { SourceOptions, SourcePreferences } from '../types';
import { useProjectApi } from './useProjectApi';
import { useUnsavedGuard } from './useUnsavedGuard';
import { toast } from '../lib/toasts';

export function useSourcePreferences(open: boolean) {
  const api = useProjectApi();
  const cache = useQueryClient();
  const saved = useQuery({
    queryKey: ['source-preferences'],
    queryFn: () => api<SourcePreferences>('/source-options'),
    enabled: open,
    refetchInterval: open ? 10000 : false,
  });
  const [draft, setDraft] = useState<SourcePreferences>();
  const [baseline, setBaseline] = useState('');
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const [error, setError] = useState<unknown>();
  const [feedback, setFeedback] = useState('');
  const dirty = !!draft && JSON.stringify(draft) !== baseline;
  const guard = useUnsavedGuard(dirty, busy);
  function reset(value?: SourcePreferences) {
    setDraft(value);
    setBaseline(value ? JSON.stringify(value) : '');
    setError(undefined);
    setFeedback('');
  }
  useEffect(() => {
    if (!open) reset();
    else if (saved.data && !dirty && JSON.stringify(saved.data) !== baseline) reset(saved.data);
  }, [open, saved.data, dirty, baseline]);
  async function perform(action: () => Promise<void>) {
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError(undefined);
    setFeedback('');
    try {
      await action();
    } catch (reason) {
      setError(reason);
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }
  return {
    saved,
    draft,
    dirty,
    busy,
    error,
    feedback,
    guard,
    change: (source_options: SourceOptions) => {
      if (draft) setDraft({ ...draft, source_options });
      setFeedback('');
    },
    leave: (action: () => void) => guard.request(action),
    save: () =>
      perform(async () => {
        if (!draft) return;
        const response = await api<SourcePreferences>('/source-options', {
          method: 'PUT',
          body: jsonBody(draft),
        });
        cache.setQueryData(['source-preferences'], response);
        reset(response);
        guard.cancel();
        setFeedback('知识来源已保存，后续新问题自动使用');
        toast('知识来源已保存');
      }),
    reload: () =>
      guard.request(
        () =>
          void perform(async () => {
            const result = await saved.refetch();
            if (result.error) throw result.error;
            if (result.data) reset(result.data);
          }),
      ),
  };
}
