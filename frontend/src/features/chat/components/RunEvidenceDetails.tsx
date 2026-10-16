import type { RunContext } from '../../../shared/types/api';
import { Markdown } from '../../../app/components/Markdown';
import { AnalysisRunDetails } from './AnalysisRunDetails';

export function RunEvidenceDetails({
  context,
  onOpen,
}: {
  context: RunContext;
  onOpen: (path: string, line: number, endLine: number, version: string) => void;
}) {
  const reads = context.source_evidence || [];
  const requests = context.provider_usage || [];
  const reported = requests.filter((item) => item.reported);
  const sum = (field: 'input_tokens' | 'output_tokens') =>
    reported.reduce((total, item) => total + (item[field] ?? 0), 0).toLocaleString();
  return (
    <>
      <AnalysisRunDetails completion={context.completion} progress={context.analysis_progress} />
      {context.analysis_plan && (
        <p className="muted">
          {context.analysis_plan.mode === 'deep' ? '深度分析' : '普通分析'} · 工具预算{' '}
          {context.analysis_plan.limit}（含关键复核 {context.analysis_plan.reserve}）· 回复上限{' '}
          {context.analysis_plan.output_tokens} tokens
        </p>
      )}
      {context.source_options && (
        <p className="muted">
          本轮允许检索：本地源码
          {context.source_options.use_deepwiki && '、DeepWiki'}
          {context.source_options.use_knowledge && '、本地知识资料'}
          {context.source_options.use_memory && '、长期记忆'}
        </p>
      )}
      {!!context.wiki_provenance?.length && (
        <details>
          <summary>实际使用的 DeepWiki · {context.wiki_provenance.length} 次</summary>
          {context.wiki_provenance.map((item, index) => (
            <p key={index}>
              {item.repo} · {item.note}
              <br />
              本地提交：{item.local.commit || '未知'}
              {item.local.dirty && '（含本地修改）'}
              <br />
              Wiki 索引提交：{item.remote_indexed_commit || '未提供'}
            </p>
          ))}
        </details>
      )}
      {!!context.knowledge_retrieval?.length && (
        <details>
          <summary>实际带入的流程资料</summary>
          {context.knowledge_retrieval
            .flatMap((item) => item.titles)
            .map((title) => (
              <p key={title}>{title}</p>
            ))}
        </details>
      )}
      {!context.references?.length && !!context.materials?.length && (
        <details>
          <summary>实际带入的项目资料</summary>
          {context.materials.map((material) => (
            <Markdown
              key={material.id}
              content={`[${material.title.replace(/[\[\]\n]/g, ' ')} · 版本 ${material.version}](${material.citation})`}
            />
          ))}
        </details>
      )}
      {requests.length > 0 && (
        <details>
          <summary>供应商实际用量 · {requests.length} 次请求</summary>
          {reported.length > 0 && (
            <p>
              已报告请求合计：输入 {sum('input_tokens')} · 输出 {sum('output_tokens')} tokens
            </p>
          )}
          {reported.length < requests.length && (
            <p className="muted">
              {requests.length - reported.length} 次请求未返回用量，合计不含这些请求。
            </p>
          )}
          <p className="muted">
            实际用量与上下文估算分开记录，包含回答、工具轮次、来源纠正及压缩请求。
          </p>
          {requests.map((item, index) => (
            <p key={index} className="muted">
              请求 {index + 1} · {item.purpose} · 结束原因：
              {item.stop_reason || item.finish_reason || '供应商未提供'}
            </p>
          ))}
        </details>
      )}
      {reads.length > 0 && (
        <details>
          <summary>本轮核对的源码 · {reads.length} 段</summary>
          {reads.map((source, index) => (
            <button
              type="button"
              className="context-source"
              key={index}
              disabled={source.current_status === 'unavailable'}
              onClick={() =>
                onOpen(source.path, source.start_line, source.end_line, source.version)
              }
            >
              {source.path} ·{' '}
              {source.start_line === 0 ? '空文件' : `L${source.start_line}–${source.end_line}`}
              {source.current_status === 'changed' && ' · 文件已变化，将打开当前版本'}
              {source.current_status === 'unavailable' && ' · 当前不可读取'}
            </button>
          ))}
        </details>
      )}
      {context.answer_validation && (
        <details>
          <summary>
            引用核对 ·{' '}
            {context.answer_validation.passed
              ? context.answer_validation.citations.length
                ? '通过'
                : '本轮无源码引用'
              : '仍需核对'}
          </summary>
          <p className="muted">{context.answer_validation.scope}</p>
          {context.answer_validation.reasons.map((reason) => (
            <p key={reason}>{reason}</p>
          ))}
        </details>
      )}
      {context.source_review && (
        <details>
          <summary>
            结论复核 ·{' '}
            {context.source_review.verdict === 'passed'
              ? 'AI 未发现条件或顺序矛盾'
              : context.source_review.verdict === 'needs_correction'
                ? '发现问题，已触发修正'
                : '仍需核对'}
          </summary>
          <p className="muted">
            {context.source_review.scope || 'AI 源码复核，不能替代人工验收。'}{' '}
            {context.source_review.reason}
          </p>
          {context.source_review.issues.map((issue, index) => (
            <p key={index}>
              {issue.claim}
              <br />
              {issue.reason}
            </p>
          ))}
        </details>
      )}
    </>
  );
}
