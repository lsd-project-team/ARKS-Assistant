import type { CodeSourceGroup } from '../rich/codeSources';
import { codeRange } from '../rich/codeSources';
import { SourceReference } from '../rich/SourceReference';

export function CodeSources({
  groups,
  runId,
  sourceId,
}: {
  groups: CodeSourceGroup[];
  runId?: string;
  sourceId?: string;
}) {
  return (
    <span className="answer-code-sources">
      {groups.map((group) => (
        <span className="answer-code-file" key={group.key} role="group" aria-label={group.name}>
          <span className="answer-code-filename">{group.name}:</span>
          {group.sources.map((source) => (
            <SourceReference
              key={codeRange(source)}
              source={source}
              runId={runId}
              sourceId={sourceId}
              compact
            />
          ))}
        </span>
      ))}
    </span>
  );
}
