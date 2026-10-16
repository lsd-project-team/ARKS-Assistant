import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { RunContext, KnowledgeReference, KnowledgeSearch, MemorySaveFeedback } from '../types';
import { api } from '../lib/api';
import { distinctReferences, knowledgeKindLabels, searchNotices } from '../lib/knowledgeFeedback';
import { Markdown } from './Markdown';
import { ErrorText } from './ui';
import '../styles/knowledge-feedback.css';

export function KnowledgeFeedback({
  references = [],
  searches = [],
  saves = [],
}: {
  references?: KnowledgeReference[];
  searches?: KnowledgeSearch[];
  saves?: MemorySaveFeedback[];
}) {
  const sources = distinctReferences(references);
  const notices = searchNotices(searches, sources);
  if (!sources.length && !notices.length && !saves.length) return null;
  return (
    <div className="knowledge-feedback">
      {saves.map((save, index) => (
        <p
          key={`${save.name}:${index}`}
          className={`memory-save-feedback ${save.status}`}
          role="status"
        >
          {save.text} · {save.scope === 'user' ? '个人偏好' : '项目记忆'} · {save.name}
        </p>
      ))}
      {(sources.length > 0 || notices.length > 0) && (
        <details>
          <summary>
            本轮参考{sources.length > 0 ? ` · ${sources.length} 条资料` : ' · 检索结果'}
          </summary>
          {sources.length > 0 && (
            <p className="muted">本轮带入或检索返回的资料，点开可核对原文。</p>
          )}
          {sources.map((row) => (
            <div className="knowledge-reference" key={row.citation}>
              <small>
                {knowledgeKindLabels[row.kind]} · v{row.version}
              </small>
              <Markdown content={`[${row.title.replace(/[\[\]\n]/g, ' ')}](${row.citation})`} />
              {row.resolution_status === 'open' && <small>未解决，不能作为已验证方案</small>}
              {row.compatibility?.status === 'needs_confirmation' && <small>适用条件待核对</small>}
              {row.compatibility?.status === 'mismatch' && <small>条件不符，仅供历史对照</small>}
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
  recent = false,
}: {
  runId: string;
  projectId: string;
  recent?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const context = useQuery({
    queryKey: ['run-knowledge', projectId, runId],
    queryFn: () => api<RunContext>(`/runs/${runId}/context`, undefined, projectId),
    enabled: recent || open,
    staleTime: 300000,
  });
  return (
    <div className="run-knowledge-summary">
      {context.data ? (
        <KnowledgeFeedback
          references={context.data.references}
          searches={context.data.searches}
          saves={context.data.memory_saves}
        />
      ) : (
        <button className="text-button" aria-expanded={open} onClick={() => setOpen(true)}>
          {context.isFetching ? '正在读取参考资料…' : '参考资料与记忆'}
        </button>
      )}
      <ErrorText error={context.error} />
    </div>
  );
}
