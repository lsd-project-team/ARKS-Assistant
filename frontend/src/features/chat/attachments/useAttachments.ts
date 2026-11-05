import { useRef, useState } from 'react';
import { api } from '../../../app/api/client';
import { useWorkspace, draftKey } from '../../../app/state/store';
import type { ChatAttachment } from '../../../shared/types/api';
import { attachmentError, MAX_ATTACHMENTS } from './files';

interface UploadJob {
  id: string;
  file: File;
  status: 'waiting' | 'uploading' | 'failed';
  error?: string;
}

export function useAttachments(projectId: string, threadId: string) {
  const key = draftKey(threadId, projectId);
  const scope = `${projectId}:${key}`;
  const [jobsByScope, setJobs] = useState<Record<string, UploadJob[]>>({});
  const active = useRef(new Set<string>());
  const jobs = jobsByScope[scope] || [];
  const update = (target: string, change: (jobs: UploadJob[]) => UploadJob[]) =>
    setJobs((current) => ({ ...current, [target]: change(current[target] || []) }));

  async function upload(files: File[], retryId?: string) {
    if (active.current.has(scope)) return;
    active.current.add(scope);
    const batch = files.map((file) => ({
      id: retryId || crypto.randomUUID(),
      file,
      status: 'waiting' as const,
    }));
    update(scope, (current) => [...current.filter((job) => job.id !== retryId), ...batch]);
    try {
      for (const job of batch) {
        let error = attachmentError(job.file);
        const count = useWorkspace.getState().drafts[key]?.attachments?.length || 0;
        if (!error && count >= MAX_ATTACHMENTS) error = '每条消息最多附加 10 个文件';
        if (!error) {
          update(scope, (current) =>
            current.map((item) => (item.id === job.id ? { ...item, status: 'uploading' } : item)),
          );
          try {
            const result = await api<ChatAttachment>(
              `/attachments?filename=${encodeURIComponent(job.file.name)}`,
              {
                method: 'POST',
                headers: { 'Content-Type': 'application/octet-stream' },
                body: job.file,
              },
              projectId,
            );
            // 异步上传结束可能已经切换对话，附件仍写回最初选择文件的草稿。
            useWorkspace.setState((state) => {
              const draft = state.drafts[key] || { content: '', selections: [] };
              return {
                drafts: {
                  ...state.drafts,
                  [key]: { ...draft, attachments: [...(draft.attachments || []), result] },
                },
              };
            });
            update(scope, (current) => current.filter((item) => item.id !== job.id));
            continue;
          } catch (reason) {
            error = reason instanceof Error ? reason.message : '上传失败，请重试';
          }
        }
        update(scope, (current) =>
          current.map((item) => (item.id === job.id ? { ...item, status: 'failed', error } : item)),
        );
      }
    } finally {
      active.current.delete(scope);
    }
  }

  function remove(id: string) {
    useWorkspace.setState((state) => {
      const draft = state.drafts[key];
      if (!draft) return state;
      return {
        drafts: {
          ...state.drafts,
          [key]: { ...draft, attachments: draft.attachments?.filter((item) => item.id !== id) },
        },
      };
    });
  }

  return {
    jobs,
    upload,
    remove,
    busy: jobs.some((job) => job.status !== 'failed'),
    discard: (id: string) => update(scope, (current) => current.filter((job) => job.id !== id)),
  };
}
