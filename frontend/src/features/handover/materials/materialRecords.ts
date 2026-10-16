import { text, type HandoverRecord } from '../shared/types.ts';

export const materialTypes = [
  { value: 'file', label: '文件资料' },
  { value: 'text', label: '文本记录' },
  { value: 'code', label: '源码资料' },
] as const;

export function materialType(row: HandoverRecord) {
  const format = text(row.payload.format).toLowerCase();
  if (row.kind === 'interview' || format === 'text') return materialTypes[1];
  if (['source', 'zip', 'cs', 'cpp', 'c', 'h'].includes(format)) return materialTypes[2];
  return materialTypes[0];
}

export function materialPreview(row: HandoverRecord) {
  return text(
    row.payload.content ||
      row.payload.transcript ||
      row.payload.topic ||
      row.payload.notes ||
      row.payload.parse_notes,
  ).slice(0, 600);
}
