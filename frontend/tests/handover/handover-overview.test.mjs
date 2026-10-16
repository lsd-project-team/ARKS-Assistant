import test from 'node:test';
import assert from 'node:assert/strict';
import {
  eventsInRange,
  overviewSummary,
  packageRecordCount,
  selectEvents,
  selectMaterials,
  selectTasks,
} from '../../src/features/handover/overview/overviewData.ts';

function record(id, kind, state = 'draft', payload = {}) {
  return {
    id,
    kind,
    state,
    payload,
    title: id,
    version: 1,
    scope_id: 'global',
    created_at: '2026-10-13T08:00:00Z',
    updated_at: '2026-10-13T08:00:00Z',
  };
}
const overview = (records, blocks = {}) => ({ scope_id: 'global', records, blocks });

test('资料确认统计只包含有效资料与访谈，草稿和待复核均计入待处理', () => {
  const rows = [
    record('source', 'source', 'confirmed'),
    record('interview', 'interview', 'confirmed'),
    record('draft', 'source'),
    record('review', 'interview', 'needs_review'),
    record('archive', 'source', 'archived'),
    record('candidate', 'candidate', 'needs_review'),
    record('job', 'job', 'needs_review'),
  ];
  const result = overviewSummary(overview(rows));
  assert.equal(result.materials.length, 4);
  assert.equal(result.materialConfirmed, 2);
  assert.equal(result.sources.length, 2);
  assert.equal(result.interviews.length, 2);
  assert.equal(result.reviewCount, 1);
});

test('工作进度只按登记状态统计，旧验收记录计入已完成，关联条件不自动改变阻塞数', () => {
  const rows = [
    record('accepted', 'task', 'confirmed', { work_status: 'accepted' }),
    record('expired', 'task', 'needs_review', { work_status: 'accepted' }),
    record('manual-block', 'task', 'draft', { work_status: 'blocked' }),
    record('dependency-block', 'task', 'confirmed', { work_status: 'doing' }),
    record('archived', 'task', 'archived', { work_status: 'blocked' }),
  ];
  const result = overviewSummary(overview(rows, { 'dependency-block': ['依赖未验收'] }));
  assert.equal(result.tasks.length, 4);
  assert.equal(result.unfinished.length, 2);
  assert.equal(result.completed.length, 2);
  assert.equal(result.blocked.length, 1);
  assert.equal(result.workStages.find((stage) => stage.id === 'done').value, 2);
  assert.equal(result.reviewCount, 0);
  assert.equal(
    result.workStages.reduce((sum, stage) => sum + stage.value, 0),
    4,
  );
  assert.deepEqual(
    result.priorities.map((row) => row.id),
    ['manual-block', 'dependency-block'],
  );
});

test('交接包按固定版本去重，来源换版或归档不影响收录数量', () => {
  const pack = record('package', 'package', 'confirmed', {
    records: [
      { record_id: 'source', version: 1 },
      { record_id: 'source', version: 1 },
      { record_id: 'source', version: 2 },
      { record_id: 'archived', version: 3 },
      { record_id: 'invalid', version: 0 },
    ],
  });
  assert.equal(packageRecordCount(pack), 3);
  const source = { ...record('source', 'source', 'confirmed'), version: 9 };
  const result = overviewSummary(
    overview([pack, source, record('archived', 'source', 'archived')]),
  );
  assert.equal(result.packageBars[0].value, 3);
  assert.equal(result.packageConfirmed, 1);
});

test('操作图统计每次操作而非唯一记录，其他动作不丢失，同一时间按日志编号排序', () => {
  const actions = ['created', 'confirm', 'confirm', 'updated', 'invalidated', 'archive', 'restore'];
  const events = actions.map((action, index) => ({
    id: index + 1,
    record_id: 'same-record',
    action,
    actor: '整理人',
    detail: '',
    version: index + 1,
    created_at: '2026-10-13T08:00:00Z',
  }));
  const original = structuredClone(events);
  const result = overviewSummary(overview([]), events);
  assert.equal(result.eventBars.find((bar) => bar.id === 'confirm').value, 2);
  assert.equal(result.eventBars.find((bar) => bar.id === 'other').value, 2);
  assert.equal(
    result.eventBars.reduce((sum, bar) => sum + bar.value, 0),
    7,
  );
  assert.deepEqual(
    result.recentEvents.map((event) => event.id),
    [7, 6],
  );
  assert.deepEqual(events, original);
});

test('空交接范围保留零值，不产生假记录或图表数据', () => {
  const result = overviewSummary(overview([]), []);
  assert.equal(result.materialConfirmed, 0);
  assert.equal(result.materials.length, 0);
  assert.equal(result.unfinished.length, 0);
  assert.deepEqual(result.packageBars, []);
  assert.deepEqual(result.recentEvents, []);
  assert.equal(
    result.eventBars.reduce((sum, bar) => sum + bar.value, 0),
    0,
  );
});

test('资料类型与确认状态组合筛选，不改变全局记录及其顺序', () => {
  const rows = [
    record('source', 'source', 'confirmed'),
    record('draft', 'interview'),
    record('review', 'interview', 'needs_review'),
  ];
  const original = structuredClone(rows);
  assert.deepEqual(
    selectMaterials(rows, 'interview', 'needs_review').map((row) => row.id),
    ['review'],
  );
  assert.equal(selectMaterials(rows, 'all', 'all').length, 3);
  assert.equal(selectMaterials(rows, 'source', 'draft').length, 0);
  assert.deepEqual(rows, original);
});

test('图表选择已完成时包含旧验收状态，全部工作仍优先展示登记的阻塞项', () => {
  const rows = [
    record('doing', 'task', 'draft', { work_status: 'doing' }),
    record('accepted', 'task', 'confirmed', { work_status: 'accepted' }),
    record('blocked', 'task', 'draft', { work_status: 'blocked' }),
  ];
  const original = structuredClone(rows);
  assert.deepEqual(
    selectTasks(rows, 'done').map((row) => row.id),
    ['accepted'],
  );
  assert.equal(selectTasks(rows, 'all')[0].id, 'blocked');
  assert.equal(selectTasks(rows, 'todo').length, 0);
  assert.deepEqual(rows, original);
});

test('日志时间范围处理边界、未来时间与无效日期，操作筛选保留其他动作和固定版本', () => {
  const now = Date.parse('2026-10-14T08:00:00Z');
  const events = [
    { id: 1, action: 'created', version: 1, created_at: '2026-10-07T08:00:00Z' },
    { id: 2, action: 'confirm', version: 2, created_at: '2026-10-07T07:59:59Z' },
    { id: 3, action: 'archive', version: 3, created_at: '2026-10-13T08:00:00Z' },
    { id: 4, action: 'future-action', version: 4, created_at: '2026-10-14T09:00:00Z' },
    { id: 5, action: 'restore', version: 5, created_at: 'invalid' },
  ];
  const original = structuredClone(events);
  assert.deepEqual(
    eventsInRange(events, 7, now).map((event) => event.id),
    [1, 3],
  );
  assert.deepEqual(
    selectEvents(eventsInRange(events, 7, now), 'other').map((event) => [event.id, event.version]),
    [[3, 3]],
  );
  assert.deepEqual(
    selectEvents(eventsInRange(events, 0, now), 'other').map((event) => event.id),
    [5, 4, 3],
  );
  assert.deepEqual(events, original);
});
