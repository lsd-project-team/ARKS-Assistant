import { Markdown } from '../../../app/components/Markdown';
import { SourceReference } from '../rich/SourceReference';
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
  if (!sources.length) return null;
  return (
    <section className="answer-sources" aria-label="来源">
      <span className="answer-sources-label">来源：</span>
      <div className="answer-sources-list">
        {sources.map((source, index) =>
          source.type === 'source' ? (
            <SourceReference key={index} source={source.source} runId={runId} sourceId={sourceId} />
          ) : (
            <Markdown key={index} content={source.markdown} runId={runId} sourceId={sourceId} />
          ),
        )}
      </div>
    </section>
  );
}
