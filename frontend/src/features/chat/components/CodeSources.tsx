import type { RunContext } from '../../../shared/types/api';
import type { CodeSourceGroup } from '../rich/codeSources';
import { codeRange } from '../rich/codeSources';
import { SourceReference } from '../rich/SourceReference';
import { resolveSourceEvidence } from '../rich/sourceEvidence';

export function CodeSources({
  groups,
  runId,
  sourceId,
  context,
}: {
  groups: CodeSourceGroup[];
  runId?: string;
  sourceId?: string;
  context?: RunContext;
}) {
  return (
    <div className="answer-code-sources">
      {groups.map((group) => (
        <div className="answer-code-file" key={group.key}>
          <div className="answer-code-file-heading">
            <span className="answer-code-filename">{group.name}</span>
            <details className="answer-code-details">
              <summary aria-label={`文件引用详情 ${group.name}`}>详情</summary>
              <div className="answer-code-detail-content">
                <p className="answer-code-path">{group.path}</p>
                {group.version && <p>版本：{group.version}</p>}
                {group.sourceId && <p>源码目录：{group.sourceId}</p>}
                <ul>
                  {group.sources.map((source) => {
                    const resolved = resolveSourceEvidence(
                      source,
                      context?.source_evidence || [],
                      sourceId,
                    );
                    return (
                      <li key={codeRange(source)}>
                        {codeRange(source)} · {resolved.reason || '已匹配本轮源码证据'}
                      </li>
                    );
                  })}
                </ul>
              </div>
            </details>
          </div>
          <div className="answer-code-ranges" aria-label={`${group.name} 引用行号`}>
            {group.sources.map((source) => (
              <SourceReference
                key={codeRange(source)}
                source={source}
                runId={runId}
                sourceId={sourceId}
                compact
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
