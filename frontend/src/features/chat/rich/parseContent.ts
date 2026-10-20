import { parseDocument } from './schema.ts';
import type { RichDocument } from './types.ts';

export type ContentSegment =
  | { id: string; type: 'markdown'; content: string }
  | { id: string; type: 'rich'; document: RichDocument }
  | { id: string; type: 'fallback'; content: string; error: string }
  | { id: string; type: 'pending'; content: string };

// 仅识别显式协议围栏，跳过普通代码围栏中的同名示例，不推测业务语义。
export function parseContent(content: string, streaming = false): ContentSegment[] {
  const segments: ContentSegment[] = [];
  const fences = /^[ ]{0,3}(`{3,}|~{3,})([^\r\n]*)\r?$/gm;
  let opened: { marker: string; start: number; body: number; rich: boolean } | undefined;
  let consumed = 0;
  let documents = 0;
  for (const match of content.matchAll(fences)) {
    const marker = match[1],
      info = match[2].trim();
    if (!opened) {
      opened = {
        marker,
        start: match.index,
        body:
          match.index + match[0].length + (content[match.index + match[0].length] === '\n' ? 1 : 0),
        rich: info === 'rich-content' && documents < 32,
      };
      continue;
    }
    if (marker[0] !== opened.marker[0] || marker.length < opened.marker.length || info) continue;
    if (opened.rich) {
      if (opened.start > consumed)
        segments.push({
          id: `text:${consumed}`,
          type: 'markdown',
          content: content.slice(consumed, opened.start),
        });
      const end = match.index + match[0].length;
      const result = parseDocument(content.slice(opened.body, match.index));
      segments.push(
        result.document
          ? { id: `rich:${opened.start}`, type: 'rich', document: result.document }
          : {
              id: `rich:${opened.start}`,
              type: 'fallback',
              content: content.slice(opened.start, end),
              error: result.error,
            },
      );
      consumed = end;
      documents++;
    }
    opened = undefined;
  }
  if (opened?.rich) {
    if (opened.start > consumed)
      segments.push({
        id: `text:${consumed}`,
        type: 'markdown',
        content: content.slice(consumed, opened.start),
      });
    segments.push(
      streaming
        ? { id: `rich:${opened.start}`, type: 'pending', content: content.slice(opened.start) }
        : {
            id: `rich:${opened.start}`,
            type: 'fallback',
            content: content.slice(opened.start),
            error: '内容块未接收完整，已保留原文',
          },
    );
  } else if (consumed < content.length)
    segments.push({ id: `text:${consumed}`, type: 'markdown', content: content.slice(consumed) });
  return segments;
}
