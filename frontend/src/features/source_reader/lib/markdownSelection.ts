import type { SourceFile } from '../../../shared/types/api';
import { indexSource, sourcePointAtOffset, sourceSelection } from './sourceSelection.ts';

export function markdownSourceRange(
  source: SourceFile,
  start: number,
  end: number,
  visibleText: string,
) {
  if (!visibleText.trim() || start < 0 || end > source.content.length || start >= end) return null;
  const raw = source.content.slice(start, end);
  const text = visibleText;
  const match = raw.indexOf(text);
  // 连续且唯一的文本能精确映射；重复文本、跨格式或跨段选区使用原始块范围。
  const unique = match >= 0 && raw.indexOf(text, match + 1) < 0;
  const first = unique ? start + match : start;
  const last = unique ? first + text.length : end;
  const index = indexSource(source.content);
  return sourceSelection(
    source,
    index,
    sourcePointAtOffset(index, first),
    sourcePointAtOffset(index, last),
  );
}

export function readMarkdownSelection(container: HTMLElement, source: SourceFile) {
  const selection = document.getSelection();
  if (!selection?.rangeCount || selection.isCollapsed) return null;
  const range = selection.getRangeAt(0);
  const blockAt = (node: Node) => {
    const element = node.nodeType === Node.ELEMENT_NODE ? (node as Element) : node.parentElement;
    return element?.closest<HTMLElement>('[data-source-start]');
  };
  const first = blockAt(range.startContainer);
  const last = blockAt(range.endContainer);
  if (!first || !last || !container.contains(first) || !container.contains(last)) return null;
  return markdownSourceRange(
    source,
    Number(first.dataset.sourceStart),
    Number(last.dataset.sourceEnd),
    selection.toString(),
  );
}

export function resolveMarkdownLink(currentPath: string, href: string) {
  if (!href || /^(?:[a-z][a-z\d+.-]*:|\/\/)/i.test(href)) return null;
  const [encodedPath, hash = ''] = href.split('#', 2);
  if (!encodedPath) return { path: currentPath, hash };
  let path: string;
  try {
    path = decodeURIComponent(encodedPath).replace(/\\/g, '/');
  } catch {
    return null;
  }
  if (path.startsWith('/')) return null;
  const parts = currentPath.split('/').slice(0, -1);
  for (const part of path.split('/')) {
    if (!part || part === '.') continue;
    if (part === '..') {
      if (!parts.length) return null;
      parts.pop();
    } else parts.push(part);
  }
  return { path: parts.join('/'), hash };
}
