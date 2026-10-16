import { text, type HandoverRecord, type Kind } from './types.ts';

export function filterCatalogRecords(
  rows: HandoverRecord[],
  kinds: Kind[],
  query: string,
  state: string,
) {
  const words = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  // 归档范围由工作台控制，列表筛选不混入其他页面的记录，也不改写原始顺序。
  return rows
    .filter((row) => {
      if (!kinds.includes(row.kind) || (state && row.state !== state)) return false;
      const content = [row.title, ...Object.values(row.payload).map(text)]
        .join(' ')
        .toLocaleLowerCase();
      return words.every((word) => content.includes(word));
    })
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at));
}
