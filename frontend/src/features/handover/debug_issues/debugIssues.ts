import { ids, text, type HandoverRecord, type Payload } from '../shared/types.ts';
import { debugKnowledgeFields, debugKnowledgePayload, debugMetadata } from './debugKnowledge.ts';
export { debugKnowledgeFields, debugKnowledgePayload, debugMetadata };

export const debugRecordTypes = [
  { value: 'problem', label: '问题处理' },
  { value: 'experience', label: '优化与经验' },
  { value: 'progress', label: '工作进展' },
  { value: 'archive', label: '资料归档' },
] as const;
export const debugIssueFields = debugKnowledgeFields;
export const debugMetadataFields = [
  { key: 'occurred_on', label: '事项日期', short: true },
  { key: 'recorded_by', label: '原记录人', short: true },
  { key: 'recorded_at', label: '原记录时间', short: true },
  { key: 'device', label: '设备型号', short: true },
  { key: 'software_version', label: '软件版本', short: true },
  { key: 'module', label: '涉及模块', short: true },
  { key: 'conditions', label: '适用工况' },
  { key: 'environment', label: '设备与环境' },
] as const;

export function debugRecordType(payload: Payload) {
  return (
    debugRecordTypes.find(({ value }) => value === debugMetadata(payload).record_type) ||
    debugRecordTypes[0]
  );
}
export function debugStatus(payload: Payload) {
  if (debugRecordType(payload).value !== 'problem') return '已记录';
  return debugMetadata(payload).resolution_status === 'resolved' ? '已解决' : '未解决';
}
export function debugVisiblePayload(payload: Payload): Payload {
  const visible = debugKnowledgePayload(payload);
  visible.notes = text(visible.notes)
    .replace(
      /^[ \t]*(?:来源编号|原始来源|本(?:次|包)提供文件|导入标识)[ \t]*[：:][^\r\n]*(?:\r?\n|$)/gm,
      '',
    )
    .replace(/\bEXP-\d{3}\b[ \t]*/g, '');
  let original: Payload | undefined;
  if (visible.origin === 'import') {
    try {
      const value: unknown = JSON.parse(text(visible.original_text));
      if (value && typeof value === 'object' && !Array.isArray(value)) original = value as Payload;
    } catch {
      /* 非 JSON 原文逐字保留。 */
    }
  }
  if (!original) return visible;
  const { id: sourceId, source: _source, ...content } = original;
  return {
    ...visible,
    keywords: ids(visible.keywords).filter((word) => word !== sourceId),
    original_text: JSON.stringify(content, null, 2),
  };
}
export function debugEditablePayload(payload: Payload): Payload {
  const visible = debugVisiblePayload(payload);
  const metadata = debugMetadata(payload);
  const recordType = debugRecordType(payload).value;
  return {
    question: text(visible.question),
    answer: text(visible.answer),
    keywords: ids(visible.keywords),
    metadata: {
      ...Object.fromEntries(debugMetadataFields.map(({ key }) => [key, text(metadata[key])])),
      record_type: recordType,
      resolution_status:
        recordType === 'problem'
          ? metadata.resolution_status === 'resolved'
            ? 'resolved'
            : 'open'
          : 'recorded',
    },
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
      if (status && debugMetadata(row.payload).resolution_status !== status) return false;
      const content = debugVisiblePayload(row.payload);
      const metadata = debugMetadata(row.payload);
      const haystack = [
        row.title,
        content.question,
        content.answer,
        ...ids(content.keywords),
        ...debugMetadataFields.map(({ key }) => text(metadata[key])),
      ]
        .join(' ')
        .toLocaleLowerCase();
      return words.every((word) => haystack.includes(word));
    })
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at));
}
