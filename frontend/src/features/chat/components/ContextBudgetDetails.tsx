import type { ContextUsage } from '../../../shared/types/api';

const categories = [
  ['system', '系统提示'],
  ['tools', '工具定义'],
  ['memory', '长期记忆'],
  ['messages', '对话与摘要'],
  ['selections', '代码选区'],
] as const;

export function ContextBudgetDetails({
  usage,
  snapshot = false,
}: {
  usage: ContextUsage;
  snapshot?: boolean;
}) {
  return (
    <div className="context-budget">
      <dl>
        {categories.map(([key, label]) => (
          <div key={key}>
            <dt>{label}</dt>
            <dd>{usage.breakdown?.[key]?.toLocaleString() ?? '未记录'}</dd>
          </div>
        ))}
        <div>
          <dt>预留回复</dt>
          <dd>{usage.output_reserved?.toLocaleString() ?? '未记录'}</dd>
        </div>
        <div>
          <dt>估算余量</dt>
          <dd>{usage.headroom?.toLocaleString() ?? '未记录'}</dd>
        </div>
      </dl>
      <p className="muted">
        {usage.complete
          ? snapshot
            ? usage.phase === 'before_compaction'
              ? '发送前预算检查的快照，此请求可能因超量而未发送。'
              : '最近一次模型请求的估算快照，包含框架追加的提示和工具。'
            : '对话按当前状态计数，系统、工具和记忆沿用最近一轮的配置。下轮发送时重新计算。'
          : '旧记录仅能估算历史消息，缺少实际请求的系统、工具和记忆记录。新一轮回复后会显示完整预算。'}{' '}
        供应商分词器可能不同，配置容量和估算值均不代表实测上限。
      </p>
      {usage.complete && usage.tokens > (usage.input_limit || usage.limit) && (
        <p role="status">当前估算超过输入预算，下一轮会先尝试压缩；仍超量时保留原文并提示调整。</p>
      )}
    </div>
  );
}
