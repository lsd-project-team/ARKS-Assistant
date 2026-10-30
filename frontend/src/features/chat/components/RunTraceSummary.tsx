import type { RunContext, SelectionTrace } from '../../../shared/types/api';
import { toolLabel } from '../lib/toolLabels';
import { DebugIssueReference } from './DebugIssueReference';

const purposeLabels: Record<string, string> = {
  answer: '生成回答与选择工具',
  memory_selection: '筛选长期记忆',
  history_selection: '筛选较早对话',
  knowledge_selection: '筛选问题与经验',
  knowledge_verification: '核查经验事实',
  source_verification: '复核源码结论',
  summary: '压缩对话摘要',
  answer_draft: '整理回答',
};

export function durationLabel(value?: number | null): string {
  if (value == null || !Number.isFinite(value) || value < 0) return '耗时未记录';
  return value < 1000 ? `${Math.round(value)} 毫秒` : `${(value / 1000).toFixed(1)} 秒`;
}

function selectionLabel(row: SelectionTrace | undefined, fallback: string) {
  if (!row) return fallback;
  const counts =
    row.candidate_count == null
      ? ''
      : `候选 ${row.candidate_count} 项，选中 ${row.selected_count ?? 0} 项`;
  if (row.status === 'unavailable')
    return `筛选未完成${counts ? `（${counts}）` : ''}；${durationLabel(row.duration_ms)}`;
  return `${counts}；${durationLabel(row.duration_ms)}${row.cache_hits ? `，缓存复用 ${row.cache_hits} 次` : ''}`;
}

export function RunTraceSummary({
  context,
  onOpen,
}: {
  context: RunContext;
  onOpen?: (path: string, start: number, end: number, version: string) => unknown;
}) {
  const trace = context.trace;
  if (!trace) return null;
  const { memory, history, knowledge } = trace.filters;
  const active = ['queued', 'running', 'cancelling'].includes(trace.status);
  const knowledgeCheck = trace.checks.knowledge_answer_review;
  const verdictLabels: Record<string, string> = {
    passed: '通过',
    revised: '已修正',
    unknown: '未完成',
    skipped: '未执行',
    needs_correction: '仍需核对',
  };
  const paths = new Set((context.source_evidence || []).map((row) => row.path));
  return (
    <section className="context-card run-trace" aria-label="本轮依据与耗时">
      <h3>本轮依据与耗时</h3>
      <p>
        {active ? '已运行' : '执行耗时'}：{durationLabel(trace.elapsed_ms)} · 已记录模型请求{' '}
        {trace.model_calls} 次{trace.queue_ms != null && ` · 排队 ${durationLabel(trace.queue_ms)}`}
      </p>
      {!trace.recorded && <p className="muted">本轮未完整记录筛选过程，缺失数据不能按零计算。</p>}
      <dl className="run-trace-rows">
        <div>
          <dt>长期记忆</dt>
          <dd>
            {trace.memory_private
              ? '个人记忆筛选详情仅发起账号可见'
              : selectionLabel(
                  memory,
                  context.source_options?.use_memory === false ? '未启用' : '未记录筛选详情',
                )}
          </dd>
        </div>
        <div>
          <dt>较早对话</dt>
          <dd>
            {selectionLabel(history, trace.recorded ? '无需筛选较早历史' : '未记录筛选详情')}
            {history?.recent_messages != null && (
              <small>
                近期保留 {history.recent_messages}{' '}
                条消息；较早用户消息、答复工具链和摘要事实按项筛选。
              </small>
            )}
            {history?.before_tokens != null && history.after_tokens != null && (
              <small>
                历史消息估算：{history.before_tokens.toLocaleString()} →{' '}
                {history.after_tokens.toLocaleString()} tokens
              </small>
            )}
          </dd>
        </div>
        <div>
          <dt>问题与经验</dt>
          <dd>{selectionLabel(knowledge, trace.recorded ? '本轮未检索' : '未记录筛选详情')}</dd>
        </div>
        <div>
          <dt>源码依据</dt>
          <dd>
            已记录读取 {paths.size} 个文件、{context.source_evidence?.length || 0} 段；本轮附带{' '}
            {context.selections.length} 个代码选区
          </dd>
        </div>
        <div>
          <dt>DeepWiki</dt>
          <dd>
            {context.wiki_provenance?.length
              ? `实际查询 ${context.wiki_provenance.length} 次`
              : '本轮无已记录的查询结果'}
          </dd>
        </div>
        <div>
          <dt>经验事实核查</dt>
          <dd>
            {knowledgeCheck
              ? verdictLabels[knowledgeCheck.verdict || ''] || '结果未记录'
              : '本轮未记录核查结果'}
            {knowledgeCheck?.reason && <small>{knowledgeCheck.reason}</small>}
          </dd>
        </div>
        {context.answer_validation && (
          <div>
            <dt>源码引用检查</dt>
            <dd>{context.answer_validation.passed ? '通过' : '仍需核对'}</dd>
          </div>
        )}
        {context.source_review && (
          <div>
            <dt>源码结论复核</dt>
            <dd>{verdictLabels[context.source_review.verdict] || '未完成'}</dd>
          </div>
        )}
      </dl>
      {(context.memories.length > 0 || context.debug_issues?.length || paths.size > 0) && (
        <details>
          <summary>查看本轮选中的依据</summary>
          {context.memories.map((memory) => (
            <details key={`${memory.scope}/${memory.name}`}>
              <summary>记忆：{memory.name}</summary>
              <pre>{memory.injected_text || memory.content}</pre>
            </details>
          ))}
          {context.debug_issues?.map((issue) => (
            <DebugIssueReference
              key={`${issue.id}/${issue.version}`}
              id={issue.id}
              version={issue.version}
              label={issue.title}
              className="context-source"
            >
              {issue.title}
            </DebugIssueReference>
          ))}
          {context.source_evidence?.map((source, index) =>
            onOpen ? (
              <button
                key={index}
                className="context-source"
                onClick={() =>
                  onOpen(source.path, source.start_line, source.end_line, source.version)
                }
              >
                {source.path} · L{source.start_line}–{source.end_line}
                {source.current_status === 'changed' ? ' · 文件已变化' : ''}
              </button>
            ) : (
              <p key={index}>
                {source.path} · L{source.start_line}–{source.end_line}
              </p>
            ),
          )}
        </details>
      )}
      {!!trace.requests.length && (
        <details>
          <summary>各类模型请求耗时</summary>
          <dl className="run-trace-rows">
            {trace.requests.map((row) => (
              <div key={row.purpose}>
                <dt>{purposeLabels[row.purpose] || '其他模型请求'}</dt>
                <dd>
                  {row.calls} 次 · {row.timed_calls ? durationLabel(row.duration_ms) : '耗时未记录'}
                  {row.timed_calls < row.calls && `（${row.calls - row.timed_calls} 次未记录耗时）`}
                  {!!row.failed_calls && ` · ${row.failed_calls} 次失败`}
                </dd>
              </div>
            ))}
          </dl>
          <p className="muted">
            各类请求耗时为累计值；并行调用、筛选与工具耗时可能重叠，不能相加当作总耗时。
          </p>
        </details>
      )}
      {!!trace.tools.length && (
        <details>
          <summary>工具执行 · {trace.tools.length} 次</summary>
          <ol className="run-trace-tools">
            {trace.tools.map((tool) => (
              <li key={tool.id}>
                {toolLabel(tool.name)} ·{' '}
                {tool.status === 'error'
                  ? '失败'
                  : tool.status
                    ? '已返回'
                    : active
                      ? '执行中'
                      : '未记录返回'}{' '}
                · {durationLabel(tool.duration_ms)}
              </li>
            ))}
          </ol>
        </details>
      )}
      <small className="muted">
        展示已记录的操作、资料范围和检查结果；筛选或核查通过不代表设备验证完成。
      </small>
    </section>
  );
}
