import { Fragment } from 'react';

const tone = (line: string) => {
  if (line.startsWith('+++') || line.startsWith('---')) return 'meta';
  if (line.startsWith('@@')) return 'hunk';
  if (line.startsWith('+')) return 'add';
  if (line.startsWith('-')) return 'del';
  return 'context';
};

export function DiffLines({ diff, empty = '没有差异' }: { diff: string; empty?: string }) {
  const lines = diff.split('\n');
  if (!diff.trim()) return <p className="muted">{empty}</p>;
  return (
    <pre className="work-diff" aria-label="代码差异">
      {lines.map((line, index) => (
        <Fragment key={index}>
          <span className={`work-diff-line ${tone(line)}`}>{line || ' '}</span>
          {'\n'}
        </Fragment>
      ))}
    </pre>
  );
}
