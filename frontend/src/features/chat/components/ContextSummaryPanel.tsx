import { MessageSquare } from 'lucide-react';
import type { ConversationContext } from '../../../shared/types/api';
import { Button } from '../../../shared/ui/ui';
import { ContextBudgetDetails } from './ContextBudgetDetails';

export function ContextSummaryPanel({
  context,
  edit,
  saving,
  onStart,
  onChange,
  onSave,
  onCancel,
}: {
  context: ConversationContext;
  edit?: { summary: string };
  saving: boolean;
  onStart: () => void;
  onChange: (value: string) => void;
  onSave: () => void;
  onCancel: () => void;
}) {
  const limit = context.input_limit || context.limit;
  const percent = limit > 0 ? Math.max(0, Math.round((context.tokens / limit) * 100)) : 0;
  return (
    <div className="context-panel-content">
      <div className="context-usage-card">
        <div>
          <span>
            {context.complete ? '上下文占用' : '历史消息占用'} <small>估算</small>
          </span>
          <strong>{percent}%</strong>
        </div>
        <progress
          aria-label="估算上下文占用"
          value={Math.min(context.tokens, limit)}
          max={Math.max(1, limit)}
        />
        <p>
          {context.tokens.toLocaleString()} <span>/ {limit.toLocaleString()} 输入 tokens</span>
        </p>
        {context.tokens > limit && <p role="status">已超过输入预算，下一轮会先尝试压缩。</p>}
      </div>
      {context.summary ? (
        <section className="context-card context-summary-card">
          <div className="context-section-heading">
            <h3>
              当前摘要{' '}
              <span className="context-count">已归纳 {context.summarized_count} 条消息</span>
            </h3>
            {!edit && <Button onClick={onStart}>纠正摘要</Button>}
          </div>
          {edit ? (
            <>
              <textarea
                aria-label="纠正压缩摘要"
                rows={10}
                disabled={saving}
                value={edit.summary}
                onChange={(event) => onChange(event.target.value)}
              />
              <div className="context-edit-actions">
                <Button disabled={saving} onClick={onCancel}>
                  取消编辑
                </Button>
                <Button
                  className="primary"
                  disabled={saving || !edit.summary.trim()}
                  onClick={onSave}
                >
                  {saving ? '正在保存…' : '保存纠正'}
                </Button>
              </div>
            </>
          ) : (
            <pre className="summary-content">{context.summary}</pre>
          )}
          <p className="muted">
            纠正后用于后续回答，原始消息继续保留。运行中不可修改；版本变化时请先刷新。
          </p>
        </section>
      ) : (
        <div className="context-summary-empty">
          <MessageSquare size={25} aria-hidden="true" />
          <strong>尚未生成压缩摘要</strong>
          <p>当前保留原始对话，达到阈值后会自动压缩。</p>
          <small>
            也可在输入框使用 <code>/compact</code> 手动请求压缩。
          </small>
        </div>
      )}
      <details className="context-advanced">
        <summary>
          <span>用量明细</span>
          <small>系统提示、工具、记忆与消息</small>
        </summary>
        <div className="context-advanced-body">
          <ContextBudgetDetails usage={context} />
        </div>
      </details>
    </div>
  );
}
