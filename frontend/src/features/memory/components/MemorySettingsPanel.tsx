import { useQuery } from '@tanstack/react-query';
import { RefreshCw } from 'lucide-react';
import { useProjectApi } from '../../projects/hooks/useProjectApi';
import { useWorkspace } from '../../../app/state/store';
import { Button, ErrorText } from '../../../shared/ui/ui';
import { Markdown } from '../../../app/components/Markdown';
import type { Memory } from '../../../shared/types/api';

type MemoryStatus = {
  enabled: boolean;
  idle_hours: number;
  states: Record<string, number>;
  last_error: string;
};

export function MemorySettingsPanel() {
  const api = useProjectApi();
  const projectId = useWorkspace((state) => state.projectId);
  const memories = useQuery({
    queryKey: ['memories', projectId],
    queryFn: () => api<Memory[]>('/memories'),
    refetchInterval: 15000,
  });
  const status = useQuery({
    queryKey: ['memory-status', projectId],
    queryFn: () => api<MemoryStatus>('/memories/status'),
    refetchInterval: 15000,
  });
  return (
    <section className="settings-memory-panel" aria-label="后台长期记忆">
      <p>后台从已闲置的聊天中提取有用信息，再整理为后续对话可参考的记忆。</p>
      {status.data && (
        <p className="muted">
          {status.data.enabled ? '自动生成已开启' : '自动生成已关闭'} · 聊天闲置至少{' '}
          {status.data.idle_hours} 小时后进入筛选
          {' · 已处理 '}{status.data.states.completed || 0} 个聊天
          {!!status.data.states.running && ' · 正在处理'}
          {!!status.data.states.failed && ' · 部分处理失败，后台稍后重试'}
        </p>
      )}
      <Button
        disabled={memories.isFetching || status.isFetching}
        onClick={() => { void memories.refetch(); void status.refetch(); }}
      >
        <RefreshCw size={14} />刷新记忆
      </Button>
      <ErrorText error={memories.error || status.error} />
      {memories.isPending && <p className="muted">正在读取记忆…</p>}
      {memories.data?.length === 0 && (
        <p className="muted">暂无自动生成的记忆。符合条件的聊天会在后台处理。</p>
      )}
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
