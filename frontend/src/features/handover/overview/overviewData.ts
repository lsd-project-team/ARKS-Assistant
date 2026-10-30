import type { Event, HandoverRecord, Overview } from '../shared/types';
import { refs } from '../shared/types.ts';
import { taskStage } from '../tasks/taskProgress.ts';
import { debugRecordType, debugRecordTypes } from '../debug_issues/debugIssues.ts';
import {
  materialFiles,
  materialFileType,
  materialFileTypes,
} from '../materials/materialRecords.ts';

export type ChartTone = 'green' | 'blue' | 'red' | 'amber' | 'gray';
export interface ChartDatum {
  id: string;
  label: string;
  value: number;
  tone: ChartTone;
}

const workStages: Omit<ChartDatum, 'value'>[] = [
  { id: 'todo', label: '待开始', tone: 'gray' },
  { id: 'doing', label: '进行中', tone: 'blue' },
  { id: 'blocked', label: '阻塞', tone: 'amber' },
  { id: 'done', label: '已完成', tone: 'green' },
];
const issueTypeTones = {
  problem: 'amber',
  experience: 'green',
  progress: 'blue',
  archive: 'gray',
} as const;
const materialTypeTones = {
  pdf: 'red',
  word: 'blue',
  spreadsheet: 'green',
  image: 'amber',
  other: 'gray',
} as const;
const eventGroups: Omit<ChartDatum, 'value'>[] = [
  { id: 'created', label: '新增', tone: 'green' },
  { id: 'updated', label: '修改', tone: 'blue' },
  { id: 'confirm', label: '人工确认', tone: 'green' },
  { id: 'invalidated', label: '复核提醒', tone: 'amber' },
];
export const eventActionLabels: Record<string, string> = {
  created: '新增',
  updated: '修改',
  image_added: '添加原图',
  confirm: '人工确认',
  reject: '审核拒绝',
  invalidated: '需要重新复核',
  archive: '归档',
  restore: '恢复',
  merged: '审核合并',
  promoted: '候选已合并',
};

export function newestRecords(records: HandoverRecord[]) {
  return [...records].sort((a, b) => b.updated_at.localeCompare(a.updated_at));
}

export function selectTasks(records: HandoverRecord[], stage: string) {
  return records
    .filter((row) => stage === 'all' || taskStage(row.payload) === stage)
    .sort(
      (a, b) =>
        Number(taskStage(b.payload) === 'blocked') - Number(taskStage(a.payload) === 'blocked') ||
        b.updated_at.localeCompare(a.updated_at),
    );
}

export function selectIssues(records: HandoverRecord[], recordType: string) {
  return newestRecords(records).filter(
    (row) =>
      row.kind === 'debug_issue' &&
      row.state !== 'archived' &&
      (recordType === 'all' || debugRecordType(row.payload).value === recordType),
  );
}

export function selectMaterials(records: HandoverRecord[], fileType: string) {
  return materialFiles(records).filter(
    (row) => fileType === 'all' || materialFileType(row) === fileType,
  );
}

export function eventsInRange(events: Event[], days: number, now = Date.now()) {
  if (!days) return events;
  const start = now - days * 86400000;
  return events.filter((event) => {
    const time = Date.parse(event.created_at);
    return time >= start && time <= now;
  });
}

export function selectEvents(events: Event[], action: string) {
  // “其他”覆盖服务端新增动作，图表和下方日志采用同一分组，避免漏掉历史记录。
  return events
    .filter((event) =>
      action === 'all'
        ? true
        : action === 'other'
          ? !eventGroups.some((group) => group.id === event.action)
          : event.action === action,
    )
    .sort((a, b) => b.id - a.id);
}

export function packageRecordCount(record: HandoverRecord) {
  // 交接包引用固定版本；即使来源后来换版或归档，也不能改按当前记录重新计算。
  return new Set(
    refs(record.payload.records)
      .filter((ref) => ref.record_id && Number.isInteger(ref.version) && ref.version > 0)
      .map((ref) => ref.record_id + ':' + ref.version),
  ).size;
}

export function overviewSummary(overview: Overview, events?: Event[]) {
  const records = overview.records.filter(
    (row) => row.state !== 'archived' && row.kind !== 'job' && row.kind !== 'candidate',
  );
  const sources = records.filter((row) => row.kind === 'source');
  const interviews = records.filter((row) => row.kind === 'interview');
  const materials = selectMaterials([...sources, ...interviews], 'all');
  const materialTypes: ChartDatum[] = materialFileTypes.map(({ id, label }) => ({
    id,
    label,
    tone: materialTypeTones[id],
    value: materials.filter((row) => materialFileType(row) === id).length,
  }));
  const tasks = records.filter((row) => row.kind === 'task');
  const issues = selectIssues(records, 'all');
  const problems = issues.filter((row) => debugRecordType(row.payload).value === 'problem');
  const issueResolved = problems.filter(
    (row) => row.payload.resolution_status === 'resolved',
  ).length;
  const issueTypes: ChartDatum[] = debugRecordTypes.map(({ value, label }) => ({
    id: value,
    label,
    tone: issueTypeTones[value],
    value: issues.filter((row) => debugRecordType(row.payload).value === value).length,
  }));
  const unfinished = tasks.filter((row) => taskStage(row.payload) !== 'done');
  const completed = tasks.filter((row) => taskStage(row.payload) === 'done');
  const isBlocked = (row: HandoverRecord) => taskStage(row.payload) === 'blocked';
  const workStagesWithCounts = workStages.map((stage) => ({
    ...stage,
    value: tasks.filter((row) => taskStage(row.payload) === stage.id).length,
  }));
  const unknownWorkCount =
    tasks.length - workStagesWithCounts.reduce((sum, stage) => sum + stage.value, 0);
  if (unknownWorkCount) {
    workStagesWithCounts.push({
      id: 'unknown',
      label: '未指定',
      tone: 'gray',
      value: unknownWorkCount,
    });
  }
  const packages = newestRecords(records.filter((row) => row.kind === 'package'));
  const actionCounts = new Map<string, number>();
  for (const event of events || []) {
    actionCounts.set(event.action, (actionCounts.get(event.action) || 0) + 1);
  }
  const eventBars = eventGroups.map((group) => ({
    ...group,
    value: actionCounts.get(group.id) || 0,
  }));
  const otherEventCount =
    (events?.length || 0) - eventBars.reduce((sum, group) => sum + group.value, 0);
  if (otherEventCount) {
    eventBars.push({ id: 'other', label: '其他操作', tone: 'gray', value: otherEventCount });
  }
  return {
    sources,
    interviews,
    materials,
    materialTypes,
    latestSource: newestRecords(sources)[0],
    latestInterview: newestRecords(interviews)[0],
    tasks,
    issues,
    issueTypes,
    issueResolved,
    issueOpen: problems.length - issueResolved,
    issueRecorded: issues.length - problems.length,
    unfinished,
    completed,
    blocked: tasks.filter(isBlocked),
    workStages: workStagesWithCounts,
    priorities: [...unfinished]
      .sort(
        (a, b) =>
          Number(isBlocked(b)) - Number(isBlocked(a)) || b.updated_at.localeCompare(a.updated_at),
      )
      .slice(0, 2),
    packages,
    packageConfirmed: packages.filter((row) => row.state === 'confirmed').length,
    packageBars: packages.slice(0, 3).map((row, index) => ({
      id: row.id,
      label: row.title,
      value: packageRecordCount(row),
      tone: (index % 2 ? 'blue' : 'green') as ChartTone,
    })),
    eventBars,
    recentEvents: [...(events || [])].sort((a, b) => b.id - a.id).slice(0, 2),
    reviewCount: records.filter(
      (row) => !['task', 'source', 'interview'].includes(row.kind) && row.state === 'needs_review',
    ).length,
  };
}
