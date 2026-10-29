import { text, type Payload } from '../shared/types.ts';

export const debugKnowledgeFields = [
  { key: 'conditions', label: '适用条件', placeholder: '适用的设备、模块、版本或工况，可留空' },
  {
    key: 'problem',
    label: '内容说明',
    required: true,
    placeholder: '说明问题现象、原理或事项背景',
  },
  { key: 'solution', label: '处理方法', placeholder: '实际采取的操作或使用方法；建议请写明是建议' },
  {
    key: 'verification',
    label: '结果记录',
    placeholder: '实际观察结果、试验数据或完成情况，可留空',
  },
  { key: 'notes', label: '注意事项', placeholder: '适用限制、风险和尚未验证的判断，可留空' },
] as const;

const normalize = (value: string) => value.replace(/[\s，。；：、,. ;:]/g, '').toLowerCase();
function joinFacts(values: string[]) {
  const parts: string[] = [];
  for (const value of values.filter((item) => item.trim())) {
    if (!parts.some((part) => normalize(part).includes(normalize(value)))) parts.push(value);
  }
  return parts.join('\n\n');
}

// 旧修订沿用原字段保存；展示时合入六项，不能因换结构而漏掉旧排查与原因。
export function debugKnowledgePayload(payload: Payload): Payload {
  const conditions = text(payload.conditions);
  const core = debugKnowledgeFields.map(({ key }) => text(payload[key]));
  const uncovered = (value: string) =>
    value && !core.some((part) => normalize(part).includes(normalize(value)));
  return {
    ...payload,
    conditions: joinFacts([
      conditions,
      ...(['device', 'environment', 'software_version', 'module'] as const)
        .filter(
          (key) =>
            text(payload[key]) && !normalize(conditions).includes(normalize(text(payload[key]))),
        )
        .map(
          (key) =>
            `${{ device: '设备', environment: '环境', software_version: '软件版本', module: '模块' }[key]}：${text(payload[key])}`,
        ),
    ]),
    problem: joinFacts([
      text(payload.problem),
      uncovered(text(payload.investigation)) ? text(payload.investigation) : '',
      uncovered(text(payload.cause)) ? `原因判断：${text(payload.cause)}` : '',
    ]),
  };
}
