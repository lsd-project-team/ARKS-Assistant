import type { HandoverRecord } from '../shared/types';
import { text } from '../shared/types.ts';

export function effectiveWorkStatus(row: HandoverRecord) {
  const status = text(row.payload.work_status);
  return status === 'accepted' && row.state !== 'confirmed' ? 'done' : status;
}
export function workStatusLabel(row: HandoverRecord, values: Record<string, string>) {
  return row.payload.work_status === 'accepted' && row.state !== 'confirmed'
    ? '验收待复核'
    : values[text(row.payload.work_status)] || '未指定';
}
