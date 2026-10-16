import type { SourceFile } from '../../shared/types/api';
import {
  indexSource,
  sourcePointAtOffset,
  sourceSelection,
} from '../source_reader/lib/sourceSelection.ts';

export function knowledgeSelection(source: SourceFile, start: number, requestedEnd: number) {
  const index = indexSource(source.content);
  const end = Math.min(requestedEnd, start + 59, source.line_count);
  if (
    !Number.isSafeInteger(start) ||
    start < 1 ||
    end < start ||
    index.lines[end - 1] === undefined
  )
    return null;
  const first = { line: start, column: 1 };
  let last = { line: end, column: index.lines[end - 1].length + 1 };
  const selected = sourceSelection(source, index, first, last);
  if (!selected?.content.trim()) return null;
  if (selected.content.length <= 60000) return selected;
  // 沿原文偏移限制长度，保留 CRLF 和列号，不从拆开的行重建选区。
  let stop = index.starts[start - 1] + 60000;
  const previous = source.content.charCodeAt(stop - 1);
  if (previous >= 0xd800 && previous <= 0xdbff) stop--;
  if (source.content[stop - 1] === '\r' && source.content[stop] === '\n') stop--;
  last = sourcePointAtOffset(index, stop);
  return sourceSelection(source, index, first, last);
}
