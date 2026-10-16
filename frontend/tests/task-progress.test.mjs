import test from 'node:test';
import assert from 'node:assert/strict';
import {
  taskCounts,
  taskRows,
  taskSearch,
  taskStage,
  taskEditablePayload,
  taskLegacyPayload,
  taskActor,
} from '../src/handover/taskProgress.ts';

const row = (id, payload = {}, kind = 'task') => ({
  id,
  kind,
  payload,
  title: id,
  updated_at: '2026-10-14T08:00:00Z',
});

test('四种进度完整计数，历史验收标记并入已完成，不依赖人工确认状态', () => {
  const rows = ['todo', 'doing', 'blocked', 'done', 'accepted'].map((work_status) =>
    row(work_status, { work_status }),
  );
  rows.push(row('source', {}, 'source'));
  assert.deepEqual(taskCounts(rows), { total: 5, todo: 1, doing: 1, blocked: 1, done: 2 });
  assert.equal(taskStage({}), 'todo');
  assert.equal(taskStage({ work_status: 'accepted' }), 'done');
});

test('状态筛选与关键字搜索组合使用，包含备注和负责人且不修改原顺序', () => {
  const rows = [
    row('old', { owner: '张工', notes: '等待配方记录' }),
    { ...row('new'), updated_at: '2026-10-14T09:00:00Z' },
  ];
  assert.equal(taskSearch(rows[0], ' 配方 '), true);
  assert.equal(taskSearch(rows[0], '张工'), true);
  assert.deepEqual(
    taskRows(rows).map((item) => item.id),
    ['new', 'old'],
  );
  assert.deepEqual(
    rows.map((item) => item.id),
    ['old', 'new'],
  );
});

test('冲突合并仅覆盖简化表单字段，保留服务器最新的来源、关系和其他说明', () => {
  const base = {
    owner: '原负责人',
    work_status: 'accepted',
    goal: '旧说明',
    notes: '旧备注',
    dependencies: ['new-dependency'],
    baseline_id: 'latest-baseline',
    evidence: [{ record_id: 'source', version: 3 }],
    current: '原有现状',
  };
  const original = structuredClone(base);
  const result = taskEditablePayload(base, {
    owner: '新负责人',
    work_status: 'done',
    goal: '新说明',
    notes: '完成核查',
    dependencies: ['stale'],
  });
  assert.deepEqual(result.dependencies, ['new-dependency']);
  assert.deepEqual(result.evidence, base.evidence);
  assert.equal(result.baseline_id, 'latest-baseline');
  assert.equal(result.current, '原有现状');
  assert.equal(result.notes, '完成核查');
  assert.deepEqual(base, original);
});

test('没有旧补充资料的新工作不展示空高级区域，已有资料继续可读', () => {
  assert.deepEqual(
    taskLegacyPayload({
      owner: '',
      work_status: 'todo',
      goal: '',
      notes: '',
      origin: 'human',
      category: 'feature',
      priority: 'normal',
      evidence_status: 'unknown',
      required_layer: 'device',
      dependencies: [],
      constraints: [],
      evidence: [],
      baseline_id: '',
    }),
    {},
  );
  assert.deepEqual(
    taskLegacyPayload({
      goal: '描述',
      current: '旧现状',
      baseline_id: 'base',
      dependencies: ['task'],
    }),
    { current: '旧现状', baseline_id: 'base', dependencies: ['task'] },
  );
  assert.equal(taskActor(''), '本机用户（未填写姓名）');
});
