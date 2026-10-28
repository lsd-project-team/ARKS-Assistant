import { text, type HandoverRecord } from '../shared/types.ts';

export function materialPreview(row: HandoverRecord) {
  return text(
    row.payload.content ||
      row.payload.transcript ||
      row.payload.topic ||
      row.payload.notes ||
      row.payload.parse_notes,
  ).slice(0, 600);
}
