import type { Selection, SourceFile } from '../../../shared/types/api';

export interface SourcePoint {
  line: number;
  column: number;
}

export function indexSource(content: string) {
  const starts = [0];
  for (const match of content.matchAll(/\r\n|\r|\n/g)) {
    starts.push(match.index + match[0].length);
  }
  return { starts, lines: content.split(/\r\n|\r|\n/) };
}

export type SourceIndex = ReturnType<typeof indexSource>;

export function sourcePointAtOffset(index: SourceIndex, offset: number): SourcePoint {
  let low = 0;
  let high = index.starts.length - 1;
  while (low < high) {
    const middle = Math.ceil((low + high) / 2);
    if (index.starts[middle] <= offset) low = middle;
    else high = middle - 1;
  }
  return { line: low + 1, column: offset - index.starts[low] + 1 };
}

export function findSourceMatches(content: string, query: string) {
  if (!query) return [];
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const matches: { start: number; end: number }[] = [];
  for (const match of content.matchAll(new RegExp(escaped, 'gi'))) {
    matches.push({ start: match.index, end: match.index + match[0].length });
    if (matches.length === 20_000) break;
  }
  return matches;
}

export function sourceSelection(
  source: SourceFile,
  index: SourceIndex,
  first: SourcePoint,
  last: SourcePoint,
): Selection | null {
  const offset = (point: SourcePoint) => {
    const line = index.lines[point.line - 1];
    if (line === undefined || point.column < 1 || point.column > line.length + 1) return null;
    return index.starts[point.line - 1] + point.column - 1;
  };
  const firstOffset = offset(first);
  const lastOffset = offset(last);
  if (firstOffset === null || lastOffset === null || firstOffset === lastOffset) return null;
  const [start, end] = firstOffset < lastOffset ? [first, last] : [last, first];
  return {
    ...(source.source_workspace_id ? { source_workspace_id: source.source_workspace_id } : {}),
    path: source.path,
    version: source.version,
    start_line: start.line,
    start_column: start.column,
    end_line: end.line,
    end_column: end.column,
    // 直接截取原文，保留 CRLF、Tab 和 UTF-16 列坐标，不能用 DOM 文本重建源码。
    content: source.content.slice(
      Math.min(firstOffset, lastOffset),
      Math.max(firstOffset, lastOffset),
    ),
  };
}

function pointAtNode(root: ShadowRoot, node: Node, offset: number, index: SourceIndex) {
  const element = node.nodeType === Node.ELEMENT_NODE ? (node as Element) : node.parentElement;
  const line = element?.closest<HTMLElement>('[data-line][data-line-index]');
  if (!line || !root.contains(line)) return null;
  const lineNumber = Number(line.dataset.line);
  const text = index.lines[lineNumber - 1];
  if (text === undefined) return null;
  const prefix = document.createRange();
  prefix.setStart(line, 0);
  prefix.setEnd(node, offset);
  return { line: lineNumber, column: Math.min(prefix.toString().length, text.length) + 1 };
}

export function readSourceSelection(root: ShadowRoot, source: SourceFile, index: SourceIndex) {
  const shadowSelection = root as ShadowRoot & { getSelection?: () => globalThis.Selection | null };
  const selected = shadowSelection.getSelection?.() ?? document.getSelection();
  if (!selected || !selected.rangeCount) return null;
  // Chromium 提供根内选区；其他浏览器用组合范围，避免边界重定位后丢失列号。
  const nativeRange = selected.getRangeAt(0);
  const range =
    nativeRange.startContainer.getRootNode() === root
      ? nativeRange
      : selected.getComposedRanges?.({ shadowRoots: [root] })[0];
  if (!range) return null;
  const first = pointAtNode(root, range.startContainer, range.startOffset, index);
  const last = pointAtNode(root, range.endContainer, range.endOffset, index);
  return first && last ? sourceSelection(source, index, first, last) : null;
}
