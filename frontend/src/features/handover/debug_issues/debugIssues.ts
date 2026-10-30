import { ids, text, type HandoverRecord, type Payload } from '../shared/types.ts';
export { debugKnowledgeFields, debugKnowledgePayload } from './debugKnowledge.ts';

export const debugRecordTypes = [
  { value: 'problem', label: '问题处理' },
  { value: 'experience', label: '优化与经验' },
  { value: 'progress', label: '工作进展' },
  { value: 'archive', label: '资料归档' },
] as const;

export function debugRecordType(payload: Payload) {
  return debugRecordTypes.find(({ value }) => value === payload.record_type) || debugRecordTypes[0];
}

export const debugIssueFields = [
  { key: 'occurred_on', label: '事项日期', short: true },
  { key: 'recorded_by', label: '原记录人', short: true },
  { key: 'recorded_at', label: '原记录时间', short: true },
  {
    key: 'problem',
    label: '内容说明',
    required: true,
    placeholder: '记录问题、优化经验、协调进展或归档事项，保留原有事实。',
  },
  { key: 'conditions', label: '适用条件', placeholder: '适用的设备、模块、版本或工况' },
  { key: 'environment', label: '设备与环境', placeholder: '设备型号、配方、系统环境等' },
  { key: 'device', label: '设备型号', short: true, placeholder: '例如 ZX2200 HS，可留空' },
  { key: 'software_version', label: '软件版本', short: true },
  { key: 'module', label: '涉及模块', short: true },
  { key: 'investigation', label: '处理经过', placeholder: '做过哪些检查、分析或协调？' },
  { key: 'cause', label: '问题原因', placeholder: '尚未明确时可以留空' },
  { key: 'solution', label: '处理方法', placeholder: '原文已有的办法或行动，可留空' },
  { key: 'verification', label: '结果记录', placeholder: '原文已有的结果或验证，可留空' },
  { key: 'notes', label: '注意事项' },
] as const;

export function debugStatus(payload: Payload) {
  if (debugRecordType(payload).value !== 'problem') return '已记录';
  return payload.resolution_status === 'resolved' ? '已解决' : '未解决';
}

export function debugVisiblePayload(payload: Payload): Payload {
  let original: Payload | undefined;
  if (payload.origin === 'import') {
    try {
      const parsed: unknown = JSON.parse(text(payload.original_text));
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        original = parsed as Payload;
      }
    } catch {
      // 非 JSON 原文仍逐字展示，不因来源信息隐藏而丢弃正文。
    }
  }
  // 仅移除导入时附加的来源行，业务条件、判断及处理结果继续保留。
  const notes = text(payload.notes).replace(
    /^[ \t]*(?:来源编号|原始来源|本(?:次|包)提供文件|导入标识)[ \t]*[：:][^\r\n]*(?:\r?\n|$)/gm,
    '',
  );
  if (!original) return { ...payload, notes };
  const { id: sourceId, source: _source, ...content } = original;
  return {
    ...payload,
    notes: notes.replace(/\bEXP-\d{3}\b[ \t]*/g, ''),
    keywords: ids(payload.keywords).filter((keyword) => keyword !== sourceId),
    original_text: JSON.stringify(content, null, 2),
  };
}

export function debugEditablePayload(payload: Payload): Payload {
  payload = debugVisiblePayload(payload);
  const recordType = debugRecordType(payload).value;
  return {
    ...Object.fromEntries(debugIssueFields.map(({ key }) => [key, text(payload[key])])),
    record_type: recordType,
    resolution_status:
      recordType === 'problem'
        ? payload.resolution_status === 'resolved'
          ? 'resolved'
          : 'open'
        : 'recorded',
    keywords: ids(payload.keywords),
  };
}

export function filterDebugIssues(
  rows: HandoverRecord[],
  query: string,
  status: string,
  recordType = '',
) {
  const words = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  return rows
    .filter((row) => {
      if (row.kind !== 'debug_issue') return false;
      if (recordType && debugRecordType(row.payload).value !== recordType) return false;
      if (status && row.payload.resolution_status !== status) return false;
      const haystack = [row.title, ...Object.values(row.payload)].join(' ').toLocaleLowerCase();
      return words.every((word) => haystack.includes(word));
    })
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at));
}
