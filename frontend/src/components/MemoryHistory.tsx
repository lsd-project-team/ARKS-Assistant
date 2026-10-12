import { useProjectApi } from '../hooks/useProjectApi';
import { useQuery } from '@tanstack/react-query';
import { History } from 'lucide-react';
import type { MemoryRevision } from '../types';
import { query } from '../lib/api';
import { Button, ErrorText } from './ui';

const actions: Record<string, string> = {
  created: '首次保存',
  updated: '修改',
  imported: '原有版本',
  deleted: '删除前保留',
  restored: '恢复版本',
};

export function MemoryHistory({
  name,
  scope,
  busy,
  onRestore,
}: {
  name: string;
  scope: string;
  busy: boolean;
  onRestore: (revision: MemoryRevision) => void;
}) {
  const api = useProjectApi();
  const history = useQuery({
    queryKey: ['memory-history', scope, name],
    queryFn: () => api<MemoryRevision[]>(`/memories/${scope}/${query(name)}/history`),
  });
  return (
    <details className="memory-history">
      <summary>
        <History size={14} />
        历史版本 {history.data ? `· ${history.data.length}` : ''}
      </summary>
      <ErrorText error={history.error} />
      {history.isPending && <p className="muted">正在读取历史…</p>}
      {history.data?.length === 0 && (
        <p className="muted">尚无历史修改，后续保存和删除将保留版本。</p>
      )}
      {history.data?.map((revision) => (
        <details key={revision.id}>
          <summary>
            {actions[revision.action] || revision.action} ·{' '}
            {new Date(revision.created_at).toLocaleString('zh-CN')}
          </summary>
          <pre>{revision.content}</pre>
          <small>版本 {revision.version.slice(0, 10)} · 恢复将保留该版本的源码来源</small>
          <Button disabled={busy} onClick={() => onRestore(revision)}>
            恢复此版本
          </Button>
        </details>
      ))}
    </details>
  );
}
