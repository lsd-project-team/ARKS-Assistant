import type { Kind, Property } from './types';

export const relations: Record<string, Kind> = {
  task_id: 'task',
  task_ids: 'task',
  dependencies: 'task',
  constraints: 'constraint',
  baseline_id: 'baseline',
  source_id: 'source',
  package_id: 'package',
};
export const shortFields = new Set([
  'date',
  'owner',
  'due',
  'location',
  'authority',
  'software_version',
  'commit',
  'firmware',
  'sdk',
  'device',
  'recipe',
  'calibration',
  'tester',
  'audience',
  'receiver',
  'trainer',
  'provider',
  'source_version',
]);

// 表单与详情采用相同分组；只调整阅读顺序，保留未填写及未知的字段。
export function fieldSections(kind: Kind, keys: string[], properties: Record<string, Property>) {
  const groupFor = (key: string) => {
    const property = properties[key] || {};
    if (relations[key]) return 'relations';
    return shortFields.has(key) || property.enum || property.type === 'integer'
      ? 'basic'
      : 'content';
  };
  return [
    {
      id: 'basic',
      title: kind === 'baseline' ? '版本与设备' : kind === 'task' ? '工作信息' : '基本信息',
    },
    { id: 'content', title: '内容说明' },
    { id: 'relations', title: '关联记录' },
  ]
    .map((section) => ({
      ...section,
      keys: keys
        .filter((key) => groupFor(key) === section.id)
        .sort((a, b) => Number(a === 'notes') - Number(b === 'notes')),
    }))
    .filter((section) => section.keys.length);
}
