import { useEffect, useState } from 'react';
import type { Payload } from './types';

export interface Draft {
  title: string;
  payload: Payload;
  version?: number;
}
export function draftStorageKey(projectId: string, recordKey: string) {
  return `arks-handover-draft:${projectId}:${recordKey}`;
}
export function useHandoverDraft(projectId: string, recordKey: string, initial: Draft) {
  const key = draftStorageKey(projectId, recordKey);
  const [warning, setWarning] = useState('');
  const [restored] = useState(() => !!localStorage.getItem(key));
  const [draft, setDraft] = useState<Draft>(() => {
    try {
      return JSON.parse(localStorage.getItem(key) || 'null') || initial;
    } catch {
      return initial;
    }
  });
  const dirty = JSON.stringify(draft) !== JSON.stringify(initial);
  useEffect(() => {
    if (!dirty) return;
    try {
      localStorage.setItem(key, JSON.stringify(draft));
    } catch {
      setWarning('本机草稿存储空间不足，请保存后再离开页面。');
    }
  }, [key, draft, dirty]);
  useEffect(() => {
    if (!dirty) return;
    const guard = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', guard);
    return () => window.removeEventListener('beforeunload', guard);
  }, [dirty]);
  return { draft, setDraft, restored, warning, dirty, clear: () => localStorage.removeItem(key) };
}
