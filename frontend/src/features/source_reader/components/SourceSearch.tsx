import { useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronUp, X } from 'lucide-react';
import { findSourceMatches } from '../lib/sourceSelection';

export function SourceSearch({
  content,
  onMatch,
  onClose,
}: {
  content: string;
  onMatch: (start: number, end: number) => void;
  onClose: () => void;
}) {
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const matches = useMemo(() => findSourceMatches(content, query), [content, query]);
  const current = matches.length ? active % matches.length : 0;
  const match = matches[current];
  useEffect(() => {
    if (match) onMatch(match.start, match.end);
  }, [match, onMatch]);
  const move = (direction: number) => {
    if (matches.length) setActive((value) => (value + direction + matches.length) % matches.length);
  };
  return (
    <div
      className="source-search"
      role="search"
      aria-label="文件内查找"
      onPointerDown={(event) => event.stopPropagation()}
      onCopy={(event) => event.stopPropagation()}
      onKeyDown={(event) => {
        event.stopPropagation();
        if (event.key === 'Escape') {
          event.preventDefault();
          onClose();
        }
        if (event.key === 'Enter') {
          event.preventDefault();
          move(event.shiftKey ? -1 : 1);
        }
      }}
    >
      <input
        autoFocus
        aria-label="查找源码"
        placeholder="查找文件内容…"
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setActive(0);
        }}
      />
      <span aria-live="polite">
        {matches.length ? current + 1 : 0}/{matches.length}
        {matches.length === 20_000 ? '+' : ''}
      </span>
      <button
        aria-label="上一个匹配"
        title="上一个匹配 · Shift+Enter"
        disabled={!matches.length}
        onClick={() => move(-1)}
      >
        <ChevronUp size={14} />
      </button>
      <button
        aria-label="下一个匹配"
        title="下一个匹配 · Enter"
        disabled={!matches.length}
        onClick={() => move(1)}
      >
        <ChevronDown size={14} />
      </button>
      <button aria-label="关闭源码查找" title="关闭 · Esc" onClick={onClose}>
        <X size={13} />
      </button>
    </div>
  );
}
