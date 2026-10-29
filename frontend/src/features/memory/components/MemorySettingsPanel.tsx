import { useQuery } from '@tanstack/react-query';
import { RefreshCw } from 'lucide-react';
import { useProjectApi } from '../../projects/hooks/useProjectApi';
import { useWorkspace } from '../../../app/state/store';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { Markdown } from '../../../app/components/Markdown';
import type { Memory } from '../../../shared/types/api';

export function MemorySettingsPanel() {
  const api = useProjectApi();
  const projectId = useWorkspace((state) => state.projectId);
  const memories = useQuery({
    queryKey: ['memories', projectId],
    queryFn: () => api<Memory[]>('/memories'),
    refetchInterval: 15000,
  });
  return (
    <section className="settings-memory-panel" aria-label="后台长期记忆">
      <Button disabled={memories.isFetching} onClick={() => void memories.refetch()}>
        <RefreshCw size={14} />
        刷新记忆
      </Button>
      <ErrorText error={memories.error} />
      {memories.isPending && <p className="muted">正在读取记忆…</p>}
      {memories.data?.length === 0 && <p className="muted">暂无长期记忆。</p>}
      {memories.data?.map((memory) => (
        <article className="context-card" key={memory.name}>
          <p className="muted">
            更新于 {new Date(memory.updated_at * 1000).toLocaleString('zh-CN')}
          </p>
          <Markdown content={memory.content} />
          {memory.lifecycle === 'needs_review' && (
            <p className="muted">相关源码已有变化，使用这些历史认识时需要重新核对。</p>
          )}
        </article>
      ))}
    </section>
  );
}
