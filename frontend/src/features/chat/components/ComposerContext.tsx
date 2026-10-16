import { useProjectApi } from '../../projects/hooks/useProjectApi';
import type { CSSProperties } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { ContextUsage, ConversationContext } from '../../../shared/types/api';
import { ErrorText } from '../../../shared/ui/ui';

export function ComposerContext({
  threadId,
  liveContext,
  compactStatus,
  compactError,
  onView,
}: {
  threadId: string;
  liveContext?: ContextUsage;
  compactStatus: string;
  compactError: unknown;
  onView: () => void;
}) {
  const api = useProjectApi();
  const context = useQuery({
    queryKey: ['context', threadId],
    queryFn: () => api<ConversationContext>(`/threads/${threadId}/context`),
    enabled: !!threadId,
    staleTime: 10_000,
  });
  const usage = liveContext || context.data;
  const percent = usage
    ? Math.min(
        100,
        Math.max(0, Math.round((usage.tokens / (usage.input_limit || usage.limit)) * 100)),
      )
    : 0;
  const label = !threadId
    ? '新对话'
    : usage
      ? `${usage.complete ? '上下文' : '历史消息'} ${percent}%`
      : context.isError
        ? '上下文暂不可用'
        : '读取上下文…';
  const details = usage
    ? `估算 ${usage.tokens.toLocaleString()} / ${(usage.input_limit || usage.limit).toLocaleString()} 输入 tokens${usage.complete ? ` · 已预留 ${usage.output_reserved?.toLocaleString()} 回复 tokens` : ' · 旧记录缺少系统和工具预算'} · 点击查看详情`
    : '查看带入资料和压缩摘要';
  return (
    <div className="composer-context">
      <div className="composer-context-actions">
        <button
          type="button"
          className="context-usage"
          aria-label="查看对话上下文"
          title={details}
          disabled={!threadId}
          onClick={onView}
        >
          <span
            className="context-ring"
            aria-hidden="true"
            style={{ '--context-percent': `${percent}%` } as CSSProperties}
          />
          <span>{label}</span>
        </button>
      </div>
      {compactStatus && (
        <div className="composer-context-status" role="status">
          {compactStatus}
        </div>
      )}
      <ErrorText error={compactError} />
    </div>
  );
}
