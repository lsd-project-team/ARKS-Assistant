import { text, type HandoverRecord } from '../shared/types.ts';

export function materialName(row: HandoverRecord) {
  return row.original_file?.name || text(row.payload.filename) || row.title;
}

export function materialFiles(rows: HandoverRecord[], search = '') {
  const words = search.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  return rows
    .filter((row) => {
      if (!['source', 'interview'].includes(row.kind) || row.state === 'archived') return false;
      const metadata = `${materialName(row)} ${row.created_by || ''}`.toLocaleLowerCase();
      return words.every((word) => metadata.includes(word));
    })
    .sort((a, b) => b.created_at.localeCompare(a.created_at));
}
