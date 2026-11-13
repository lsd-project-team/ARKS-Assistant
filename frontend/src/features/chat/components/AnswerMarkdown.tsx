import { useMemo, type ComponentProps, type ReactNode } from 'react';
import { RichContentRenderer, RichContentSegments } from '../rich/RichContentRenderer';
import { createContentParser } from '../rich/parseContent';
import { separateAnswerSources } from '../rich/answerSources';
import { AnswerSources } from './AnswerSources';
import { CodingChanges } from './CodingChanges';
import '../styles/answer-sources.css';

export function AnswerMarkdown({
  content,
  runId,
  sourceId,
  streaming = false,
  afterContent,
}: ComponentProps<typeof RichContentRenderer> & { afterContent?: ReactNode }) {
  const parse = useMemo(createContentParser, []);
  const presentation = useMemo(
    () => separateAnswerSources(parse(content, streaming)),
    [content, streaming, parse],
  );
  return (
    <div className="answer-reading">
      <RichContentSegments
        segments={presentation.body}
        runId={runId}
        sourceId={sourceId}
        streaming={streaming}
      />
      {afterContent}
      <AnswerSources sources={presentation.sources} runId={runId} sourceId={sourceId} />
      <CodingChanges runId={runId} streaming={streaming} />
    </div>
  );
}
