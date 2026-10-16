import type { RunContext, Selection } from '../../../shared/types/api';
import { distinctReferences } from '../../knowledge/lib/knowledgeFeedback';
import { toolLabel } from '../lib/toolLabels';
import { ContextBudgetDetails } from './ContextBudgetDetails';
import { KnowledgeFeedback } from './RunKnowledgeSummary';
import { RunEvidenceDetails } from './RunEvidenceDetails';

export function RunContextPanel({
  context,
  onOpen,
  onSelection,
  onDebug,
}: {
  context: RunContext;
  onOpen: (path: string, line: number, endLine: number, version: string) => void;
  onSelection: (selection: Selection) => void;
  onDebug: (id: string, version: number) => void;
}) {
  const references = distinctReferences(context.references || []);
  const referenceCount =
    references.length || (context.materials?.length || 0) + (context.debug_issues?.length || 0);
  return (
    <div className="context-panel-content">
      <div className="context-overview" aria-label="本轮资料概况">
        {[
          ['资料记录', referenceCount],
          ['长期记忆', context.memories.length],
          ['代码选区', context.selections.length],
        ].map(([label, count]) => (
          <div key={label}>
            <strong>{count}</strong>
            <span>{label}</span>
          </div>
        ))}
      </div>
      <KnowledgeFeedback
        mode="context"
        references={context.references}
        searches={context.searches}
        saves={context.memory_saves}
      />
      {!references.length &&
        context.debug_issues?.map((issue) => (
          <button
            key={issue.id}
            className="context-source"
            onClick={() => onDebug(issue.id, issue.version)}
          >
            调试记录 · {issue.title} · v{issue.version}
          </button>
        ))}
      <section className="context-card">
        <h3>
          长期记忆 <span className="context-count">{context.memories.length}</span>
        </h3>
        {!context.recorded && <p className="muted">本轮未记录记忆快照，无法追溯实际带入的内容。</p>}
        {context.memories.map((memory) => (
          <details className="context-memory" key={`${memory.scope}/${memory.name}`}>
            <summary>
              {memory.name}
              <span>
                {memory.scope === 'user' ? '用户偏好' : '项目记忆'}
                {memory.partial && ' · 部分带入'}
              </span>
            </summary>
            <pre>{memory.injected_text || memory.content}</pre>
            <small>带入版本：{memory.version?.slice(0, 10)}</small>
            {memory.inclusion_reason && <small>{memory.inclusion_reason}</small>}
            {!!memory.conflicts?.length && (
              <small>同字段值不同，需核对：{memory.conflicts.join('、')}</small>
            )}
          </details>
        ))}
        {context.recorded && !context.memories.length && (
          <p className="context-empty-note">本轮未带入长期记忆</p>
        )}
      </section>
      {!!context.selections.length && (
        <section className="context-card">
          <h3>
            代码选区 <span className="context-count">{context.selections.length}</span>
          </h3>
          {context.selections.map((selection, index) => (
            <button key={index} className="context-source" onClick={() => onSelection(selection)}>
              {selection.path} · L{selection.start_line}–{selection.end_line}
              {selection.stale && ' · 旧版本'}
            </button>
          ))}
        </section>
      )}
      <details className="context-advanced">
        <summary>
          <span>运行与核对详情</span>
          <small>模型、预算、来源与用量</small>
        </summary>
        <div className="context-advanced-body">
          {context.model?.profile_id && (
            <div className="run-model-record">
              <strong>
                {context.model.profile_name} · {context.model.model || '未填写模型名称'}
              </strong>
              <small>
                {context.model.protocol === 'anthropic'
                  ? 'Anthropic Messages'
                  : 'OpenAI Chat Completions'}{' '}
                · {context.model.base_url}
              </small>
              <small>
                压缩模型：{context.model.summary_model || context.model.model || '未配置'}
              </small>
            </div>
          )}
          {context.budget && (
            <details>
              <summary>本轮请求预算 · 估算 {context.budget.tokens.toLocaleString()} tokens</summary>
              <ContextBudgetDetails usage={context.budget} snapshot />
            </details>
          )}
          <RunEvidenceDetails context={context} onOpen={onOpen} />
          {!!context.tools.length && (
            <p className="muted">
              资料获取：{[...new Set(context.tools.map((tool) => toolLabel(tool.name)))].join('、')}
            </p>
          )}
        </div>
      </details>
    </div>
  );
}
