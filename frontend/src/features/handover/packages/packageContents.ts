import type { Evidence, HandoverRecord } from '../shared/types';
import { refs, text } from '../shared/types.ts';

const categories = [
  { id: 'source', label: '资料' },
  { id: 'task', label: '工作项' },
  { id: 'other', label: '其他记录' },
] as const;
export interface PackageItem extends Evidence {
  title: string;
}

export function packageGroups(payload: HandoverRecord['payload'], records: HandoverRecord[]) {
  const byId = new Map(records.map((row) => [row.id, row]));
  const seen = new Set<string>();
  const items: PackageItem[] = [];
  for (const reference of refs(payload.records)) {
    const key = `${reference.record_id}:${reference.version}`;
    if (seen.has(key)) continue;
    seen.add(key);
    // 使用包内保存的版本；目录中记录后来换版、归档都不能改变打开的内容。
    items.push({
      ...reference,
      title: byId.get(reference.record_id)?.title || reference.record_id,
    });
  }
  return categories
    .map((category) => ({
      ...category,
      items: items.filter((item) => {
        const kind = byId.get(item.record_id)?.kind;
        if (category.id === 'source') return kind === 'source' || kind === 'interview';
        return category.id === 'other'
          ? !['source', 'interview', 'task'].includes(kind || '')
          : kind === category.id;
      }),
    }))
    .filter((group) => group.items.length);
}

export function packageNotes(payload: HandoverRecord['payload']) {
  return [
    { id: 'scope', label: '交接说明', content: text(payload.scope) },
    { id: 'gaps', label: '待补充事项', content: text(payload.gaps) },
    { id: 'notes', label: '补充说明', content: text(payload.notes) },
  ].filter((item) => item.content.trim());
}
