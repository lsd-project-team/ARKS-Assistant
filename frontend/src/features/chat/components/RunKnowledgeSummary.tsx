import { useQuery } from '@tanstack/react-query';
import type {
  RunContext,
  KnowledgeReference,
  KnowledgeSearch,
  MemorySaveFeedback,
} from '../../../shared/types/api';
import { api } from '../../../app/api/client';
import {
  distinctReferences,
  knowledgeKindLabels,
  searchNotices,
} from '../../knowledge/lib/knowledgeFeedback';
import { answerKnowledgeCitations, answerReferences } from '../../knowledge/lib/answerReferences';
import { Markdown } from '../../../app/components/Markdown';
import { ErrorText } from '../../../shared/ui/ui';
import '../../knowledge/styles/knowledge-feedback.css';
import { DebugIssueSources, originalDebugReferences } from './DebugIssueSources';

type KnowledgeFeedbackProps = {
  references?: KnowledgeReference[];
  searches?: KnowledgeSearch[];
  saves?: MemorySaveFeedback[];
} & ({ mode: 'context'; answer?: never } | { mode?: 'answer'; answer: string });

export function KnowledgeFeedback({
  mode = 'answer',
  answer = '',
  references = [],
  searches = [],
  saves = [],
}: KnowledgeFeedbackProps) {
  const sources =
    mode === 'context' ? distinctReferences(references) : answerReferences(answer, references);
  const notices = mode === 'context' ? searchNotices(searches, sources) : [];
  // 检索候选不等于回答依据；原图必须跟随回答实际引用的固定版本。
  const originals = mode === 'answer' ? originalDebugReferences(sources) : [];
  if (!sources.length && !notices.length && !saves.length && !originals.length) return null;
  return (
    <div className="knowledge-feedback">
      {originals.length > 0 && <DebugIssueSources references={originals} />}
      {saves.map((save, index) => (
        <p
          key={`${save.name}:${index}`}
          className={`memory-save-feedback ${save.status}`}
          role="status"
        >
          {save.text} · {save.scope === 'user' ? '个人偏好' : '项目记忆'} · {save.name}
        </p>
      ))}
      {mode === 'answer'
        ? sources.length > 0 && (
            <details>
              <summary>参考资料</summary>
              {sources.map((row) => (
                <div className="knowledge-reference" key={row.citation}>
                  <Markdown content={`[${row.title.replace(/[\[\]\n]/g, ' ')}](${row.citation})`} />
                </div>
              ))}
            </details>
          )
        : (sources.length > 0 || notices.length > 0) && (
            <details>
              <summary>
                资料检索记录
                {sources.length > 0 ? ` · ${sources.length} 条资料` : ' · 检索结果'}
              </summary>
              {sources.length > 0 && (
                <p className="muted">本轮自动带入或检索返回的资料，不表示回答已经引用。</p>
              )}
              {sources.map((row) => (
                <div className="knowledge-reference" key={row.citation}>
                  <small>
                    {knowledgeKindLabels[row.kind]}
                    {row.kind !== 'debug_issue' && ` · v${row.version}`}
                  </small>
                  <Markdown content={`[${row.title.replace(/[\[\]\n]/g, ' ')}](${row.citation})`} />
                  {row.resolution_status === 'open' && <small>未解决，不能作为已验证方案</small>}
                  {row.compatibility?.status === 'needs_confirmation' && (
                    <small>适用条件待核对</small>
                  )}
                  {row.compatibility?.status === 'mismatch' && (
                    <small>条件不符，仅供历史对照</small>
                  )}
                </div>
              ))}
              {notices.map((notice) => (
                <p className="muted" key={notice}>
                  {notice}
                </p>
              ))}
            </details>
          )}
    </div>
  );
}

export function RunKnowledgeSummary({
  runId,
  projectId,
  answer,
}: {
  runId: string;
  projectId: string;
  answer: string;
  recent?: boolean;
}) {
  const hasCitations = answerKnowledgeCitations(answer).length > 0;
  const context = useQuery({
    queryKey: ['run-knowledge', projectId, runId],
    queryFn: () => api<RunContext>(`/runs/${runId}/context`, undefined, projectId),
    // 历史回复恢复引用快照后，仍由当前回答的引用筛选原图。
    enabled: true,
    staleTime: 300000,
  });
  if (!context.data) return hasCitations ? <ErrorText error={context.error} /> : null;
  return (
    <div className="run-knowledge-summary">
      <KnowledgeFeedback
        answer={answer}
        references={context.data.references}
        saves={context.data.memory_saves}
      />
      <ErrorText error={context.error} />
    </div>
  );
}
