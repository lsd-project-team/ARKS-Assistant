import type { HandoverRecord, Payload } from '../shared/types';
import { text } from '../shared/types.ts';

export const taskStages = [
  { value: 'todo', label: '待开始' },
  { value: 'doing', label: '进行中' },
  { value: 'blocked', label: '阻塞' },
  { value: 'done', label: '已完成' },
] as const;
export type TaskStage = (typeof taskStages)[number]['value'];

export function taskStage(payload: Payload): TaskStage {
  // 日常进度与旧的人工验收状态分开；历史 accepted 统一计入已完成，原值仍保留。
  const value = text(payload.work_status);
  if (value === 'accepted') return 'done';
  return taskStages.find((stage) => stage.value === value)?.value ?? 'todo';
}

export const taskStageLabel = (payload: Payload) =>
  taskStages.find((stage) => stage.value === taskStage(payload))!.label;

export function taskRows(records: HandoverRecord[]) {
  return records
    .filter((row) => row.kind === 'task')
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at));
}

export function taskCounts(rows: HandoverRecord[]) {
  const tasks = taskRows(rows);
  return {
    total: tasks.length,
    ...Object.fromEntries(
      taskStages.map((stage) => [
        stage.value,
        tasks.filter((row) => taskStage(row.payload) === stage.value).length,
      ]),
    ),
  } as Record<'total' | TaskStage, number>;
}

export function taskSearch(row: HandoverRecord, query: string) {
  return [row.title, text(row.payload.owner), text(row.payload.goal), text(row.payload.notes)]
    .join(' ')
    .toLowerCase()
    .includes(query.trim().toLowerCase());
}

export function taskEditablePayload(base: Payload, draft: Payload): Payload {
  // 简化表单只修改可见字段，版本冲突合并时以服务器的关联资料为准，避免清空旧数据。
  return {
    ...base,
    owner: text(draft.owner),
    work_status: text(draft.work_status) || 'todo',
    goal: text(draft.goal),
    notes: text(draft.notes),
  };
}

const simpleFields = new Set(['owner', 'work_status', 'goal', 'notes', 'origin']);
const legacyDefaults: Payload = {
  category: 'feature',
  priority: 'normal',
  evidence_status: 'unknown',
  required_layer: 'device',
};
export function taskLegacyPayload(payload: Payload): Payload {
  return Object.fromEntries(
    Object.entries(payload).filter(
      ([key, value]) =>
        !simpleFields.has(key) &&
        value !== legacyDefaults[key] &&
        (Array.isArray(value) ? value.length > 0 : value !== '' && value != null),
    ),
  );
}

export const taskActor = (actor: string) => actor.trim() || '本机用户（未填写姓名）';
