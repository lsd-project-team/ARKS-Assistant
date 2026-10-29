import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, jsonBody } from '../../../app/api/client';
import { useAuth } from '../../auth/AuthContext';
import { useUnsavedGuard } from '../../../shared/hooks/useUnsavedGuard';
import { toast } from '../../../shared/utils/toasts';
import { validateAgentInstructions, type AgentInstructions } from '../lib/agentInstructionsDraft';

export function useAgentInstructions(open: boolean) {
  const accountId = useAuth().session?.user.id;
  const currentAccount = useRef(accountId);
  currentAccount.current = accountId;
  const cache = useQueryClient();
  const key = ['agent-instructions', accountId];
  const saved = useQuery({
    queryKey: key,
    queryFn: () => api<AgentInstructions>('/agent-instructions'),
    enabled: open && !!accountId,
  });
  const [editing, setEditing] = useState<AgentInstructions>();
  const [baseline, setBaseline] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [feedback, setFeedback] = useState('');
  const submitting = useRef(false);
  const draft = editing?.owner_id === accountId ? editing : undefined;
  const dirty = !!draft && draft.content !== baseline;
  const guard = useUnsavedGuard(dirty, busy);
  function reset(value?: AgentInstructions) {
    setEditing(value);
    setBaseline(value?.content || '');
    setError(undefined);
    setFeedback('');
  }
  useEffect(() => {
    if (
      open &&
      saved.data &&
      saved.data.owner_id === accountId &&
      !dirty &&
      saved.data.version !== draft?.version
    )
      reset(saved.data);
  }, [open, saved.data, accountId, dirty, draft?.version]);
  async function perform(action: () => Promise<void>) {
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError(undefined);
    try {
      await action();
    } catch (reason) {
      if (currentAccount.current === accountId) setError(reason);
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }
  function leave(action: () => void) {
    guard.request(() => {
      reset(saved.data);
      action();
    });
  }
  return {
    saved,
    draft,
    dirty,
    busy,
    error,
    feedback,
    guard,
    leave,
    validation: validateAgentInstructions(draft?.content || ''),
    setContent: (content: string) => {
      if (draft) setEditing({ ...draft, content });
      setFeedback('');
    },
    save: () =>
      perform(async () => {
        if (!draft || validateAgentInstructions(draft.content)) return;
        const response = await api<AgentInstructions>('/agent-instructions', {
          method: 'PUT',
          body: jsonBody({ content: draft.content, version: draft.version }),
        });
        cache.setQueryData(key, response);
        if (currentAccount.current !== accountId) return;
        reset(response);
        guard.cancel();
        setFeedback('全局 agent.md 已保存，后续启动的问答使用新内容');
        toast('全局指令已保存');
      }),
    reload: () =>
      leave(
        () =>
          void perform(async () => {
            const result = await saved.refetch();
            if (result.error) throw result.error;
            if (currentAccount.current === accountId) reset(result.data);
          }),
      ),
  };
}
