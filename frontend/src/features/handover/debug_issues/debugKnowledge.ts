import { ids, text, type Payload } from '../shared/types.ts';

export const debugKnowledgeFields = [
  { key: 'question', label: '问题', required: true, placeholder: '用自然的问句描述要解决的问题' },
  {
    key: 'answer',
    label: '答案',
    required: true,
    placeholder: '用完整句子写清处理办法、适用条件和必要说明',
  },
] as const;

export function debugMetadata(payload: Payload): Payload {
  return payload.metadata &&
    typeof payload.metadata === 'object' &&
    !Array.isArray(payload.metadata)
    ? (payload.metadata as Payload)
    : payload;
}

// 旧引用不改写存储；在阅读时完整投影，保留旧排查、原因、结果和原图。
export function debugKnowledgePayload(payload: Payload): Payload {
  const metadata = debugMetadata(payload);
  if ('question' in payload || 'answer' in payload) return { ...metadata, ...payload };
  const parts: string[] = [];
  const normalize = (value: string) => value.replace(/[\s，。；：、,. ;:]/g, '').toLowerCase();
  for (const key of [
    'conditions',
    'problem',
    'investigation',
    'cause',
    'solution',
    'verification',
    'notes',
  ]) {
    const value = text(payload[key])
      .replace(
        /^[ \t]*(?:来源编号|原始来源|本(?:次|包)提供文件|导入标识)[ \t]*[：:][^\r\n]*(?:\r?\n|$)/gm,
        '',
      )
      .replace(/\bEXP-\d{3}\b[ \t]*/g, '')
      .trim();
    if (value && !parts.some((part) => normalize(part).includes(normalize(value))))
      parts.push(value.replace(/[。；;\s]+$/, '') + '。');
  }
  return {
    ...payload,
    question: text(payload.problem),
    answer: parts.join('\n\n'),
    keywords: ids(payload.keywords),
  };
}
