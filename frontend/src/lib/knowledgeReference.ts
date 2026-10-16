import type { HandoverRecord } from '../handover/types.ts';
import { text } from '../handover/types.ts';

export function isKnowledgeReference(href: string) {
  return /^(source|material|debug-issue|handover-source):/.test(href);
}

export function handoverReference(href: string) {
  const match =
    /^(debug-issue|handover-source):([\w-]+)\/([1-9]\d*)(?:#L([1-9]\d*)(?:-L?([1-9]\d*))?)?$/.exec(
      href,
    );
  if (!match || (match[1] === 'handover-source' && !match[4])) return;
  const start = Number(match[4] || 1);
  const end = Number(match[5] || start);
  const version = Number(match[3]);
  if (![start, end, version].every(Number.isSafeInteger) || end < start) return;
  return { kind: match[1], id: match[2], version, start, end };
}

export function handoverDocumentText(row: HandoverRecord) {
  if (row.kind !== 'interview') return text(row.payload.content);
  return (
    [
      ['topic', '主题'],
      ['questions', '问题'],
      ['transcript', '访谈原文'],
      ['correction', '补充更正'],
    ] as const
  )
    .filter(([key]) => text(row.payload[key]))
    .map(([key, label]) => `${label}：${text(row.payload[key])}`)
    .join('\n');
}
