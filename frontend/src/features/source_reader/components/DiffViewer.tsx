import { useMemo } from 'react';

interface Row {
  kind: 'context' | 'add' | 'remove' | 'hunk' | 'meta';
  oldLine: number | '';
  newLine: number | '';
  text: string;
}

const hunk = /^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/;

function parse(text: string): Row[] {
  const rows: Row[] = [];
  let oldLine = 0;
  let newLine = 0;
  for (const line of text.split('\n')) {
    if (!line || line.startsWith('diff --git') || line.startsWith('index ')) continue;
    if (line.startsWith('--- ') || line.startsWith('+++ ')) continue;
    const match = hunk.exec(line);
    if (match) {
      oldLine = Number(match[1]);
      newLine = Number(match[2]);
      rows.push({ kind: 'hunk', oldLine: '', newLine: '', text: line });
      continue;
    }
    if (line.startsWith('\\')) {
      rows.push({ kind: 'meta', oldLine: '', newLine: '', text: line });
      continue;
    }
    const marker = line[0];
    const body = line.slice(1);
    if (marker === '+') {
      rows.push({ kind: 'add', oldLine: '', newLine, text: body });
      newLine += 1;
    } else if (marker === '-') {
      rows.push({ kind: 'remove', oldLine, newLine: '', text: body });
      oldLine += 1;
    } else {
      rows.push({ kind: 'context', oldLine, newLine, text: body });
      oldLine += 1;
      newLine += 1;
    }
  }
  return rows;
}

export function DiffViewer({ text }: { text: string }) {
  const rows = useMemo(() => parse(text), [text]);
  return (
    <div className="diff-viewer" role="region" aria-label="代码对比">
      <div className="diff-rows">
        {rows.map((row, index) =>
          row.kind === 'hunk' ? (
            <div className="diff-row diff-hunk" key={index}>
              <span className="diff-line" />
              <span className="diff-line" />
              <span className="diff-code">{row.text}</span>
            </div>
          ) : (
            <div className={`diff-row diff-${row.kind}`} key={index}>
              <span className="diff-line">{row.oldLine}</span>
              <span className="diff-line">{row.newLine}</span>
              <span className="diff-code">{row.text || ' '}</span>
            </div>
          ),
        )}
      </div>
    </div>
  );
}
