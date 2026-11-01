import { Markdown } from '../../../app/components/Markdown';
import { useQuery } from '@tanstack/react-query';
import { useWorkspace } from '../../../app/state/store';
import { api } from '../../../app/api/client';
import type { RunContext } from '../../../shared/types/api';
import { groupCodeSources } from '../rich/codeSources';
import { CodeSources } from './CodeSources';
import type { AnswerSource } from '../rich/answerSources';

export function AnswerSources({
  sources,
  runId,
  sourceId,
}: {
  sources: AnswerSource[];
  runId?: string;
  sourceId?: string;
}) {
  const projectId = useWorkspace((state) => state.projectId);
  const hasCode = sources.some(
    (source) =>
      source.type === 'source' || (source.type === 'link' && source.url.startsWith('source:')),
  );
  const context = useQuery({
    queryKey: ['source-evidence', projectId, runId],
    queryFn: () => api<RunContext>(`/runs/${runId}/context`, undefined, projectId),
    enabled: !!runId && hasCode,
    staleTime: 15000,
    retry: false,
  });
  const { groups, others, invalid } = groupCodeSources(
    sources,
    context.data?.source_evidence || [],
    sourceId,
  );
  if (!sources.length) return null;
  return (
    <section className="answer-sources" aria-label="来源">
      <span className="answer-sources-label">来源：</span>
      <div className="answer-sources-list">
        {others.map(
          (source, index) =>
            source.type !== 'source' && (
              <Markdown key={index} content={source.markdown} runId={runId} sourceId={sourceId} />
            ),
        )}
        {groups.length > 0 && (
          <CodeSources groups={groups} runId={runId} sourceId={sourceId} context={context.data} />
        )}
        {invalid.map((source, index) => (
          <details className="answer-code-details" key={index}>
            <summary>{source.label || '代码引用'}（引用格式无效）</summary>
            <p className="answer-code-path">{source.url}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
