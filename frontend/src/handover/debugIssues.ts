import { ids, text, type HandoverRecord, type Payload } from './types.ts';

export const debugIssueFields = [
  {
    key: 'problem',
    label: '问题现象',
    required: true,
    placeholder: '出现了什么问题、报错或异常表现？',
  },
  { key: 'conditions', label: '发生条件', placeholder: '在哪一步、什么情况下出现？' },
  { key: 'environment', label: '设备与环境', placeholder: '设备型号、配方、系统环境等' },
  { key: 'device', label: '设备型号', short: true, placeholder: '例如 ZX2200 HS，可留空' },
  { key: 'software_version', label: '软件版本', short: true },
  { key: 'module', label: '涉及模块', short: true },
  { key: 'investigation', label: '排查过程', placeholder: '做过哪些检查？各自发现了什么？' },
  { key: 'cause', label: '问题原因', placeholder: '尚未明确时可以留空' },
  { key: 'solution', label: '解决办法', placeholder: '具体如何处理？尚未解决时可以留空' },
  { key: 'verification', label: '验证结果', placeholder: '处理后如何验证、实际结果如何？' },
  { key: 'notes', label: '补充说明' },
] as const;

export function debugStatus(payload: Payload) {
  return payload.resolution_status === 'resolved' ? '已解决' : '未解决';
}

export function debugEditablePayload(payload: Payload): Payload {
  return {
    ...Object.fromEntries(debugIssueFields.map(({ key }) => [key, text(payload[key])])),
    resolution_status: payload.resolution_status === 'resolved' ? 'resolved' : 'open',
    keywords: ids(payload.keywords),
  };
}

export function filterDebugIssues(rows: HandoverRecord[], query: string, status: string) {
  const words = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  return rows
    .filter((row) => {
      if (row.kind !== 'debug_issue') return false;
      if (status && row.payload.resolution_status !== status) return false;
      const haystack = [row.title, ...Object.values(row.payload)].join(' ').toLocaleLowerCase();
      return words.every((word) => haystack.includes(word));
    })
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at));
}
