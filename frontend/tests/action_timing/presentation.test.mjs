import test from 'node:test';
import assert from 'node:assert/strict';
import {
  actionPresentation,
  filterActions,
  actionTableCsv,
} from '../../src/features/action_timing/presentation.ts';

const action = {
  id: 'uplook',
  name: 'S2 上视纠偏',
  class_name: 'UpLookCorrectionActionNode',
  kind: 'node',
  group: 'S2 固晶',
  known_delay_min_ms: 20,
  known_delay_max_ms: 40,
  total_ms: null,
  motion_count: 10,
  wait_count: 7,
};

test('动作表区分停留部分和完整耗时，单点与双点使用当前源码数值', () => {
  assert.deepEqual(actionPresentation(action), {
    station: 'S2',
    name: '上视纠偏',
    duration: '20–40 ms',
    remainder: '+ 运动与等待时间',
    note: '单点停留 20 ms，双点停留 40 ms',
    hasDuration: true,
  });
  const changed = actionPresentation({ ...action, known_delay_min_ms: 30, known_delay_max_ms: 60 });
  assert.equal(changed.duration, '30–60 ms');
  assert.equal(changed.note, '单点停留 30 ms，双点停留 60 ms');
  const complete = actionPresentation({ ...action, total_ms: 75 });
  assert.equal(complete.duration, '75 ms');
  assert.equal(complete.remainder, '');
});

test('缺少耗时与无固定停留均不伪装成零毫秒，未定上界保留至少语义', () => {
  const unknown = {
    ...action,
    class_name: 'PickActionNode',
    known_delay_min_ms: 0,
    known_delay_max_ms: 0,
  };
  assert.equal(actionPresentation(unknown).duration, '待补参数');
  assert.equal(
    actionPresentation({ ...unknown, known_delay_min_ms: null, known_delay_max_ms: null }).duration,
    '待补参数',
  );
  assert.equal(actionPresentation({ ...unknown, total_ms: 0 }).duration, '无固定停留');
  assert.match(actionPresentation({ ...unknown, total_ms: 0 }).note, /不表示实际耗时为零/);
  assert.equal(actionPresentation({ ...action, known_delay_max_ms: null }).duration, '至少 20 ms');
});

test('源码不可执行或空跑跳过的动作明确标注，不要求用户补参数', () => {
  const unavailable = actionPresentation({ ...action, execution_status: 'unavailable' });
  assert.equal(unavailable.duration, '空跑不可执行');
  assert.equal(unavailable.remainder, '');
  assert.equal(unavailable.hasDuration, false);
  assert.equal(
    actionPresentation({ ...action, execution_status: 'skipped' }).duration,
    '空跑不动作',
  );
});

test('主要动作不混入控制器子动作，名称搜索与工位筛选一起生效', () => {
  const other = { ...action, id: 'dispense', name: 'S1 点胶', group: 'S1 点胶' };
  const controller = { ...action, id: 'controller', kind: 'controller' };
  const workflow = { ...action, id: 'workflow', kind: 'workflow' };
  const rows = [action, other, controller, workflow];
  assert.deepEqual(
    filterActions(rows, { auxiliary: false, group: 'S2 固晶', search: '  上视  ' }),
    [action],
  );
  assert.deepEqual(filterActions(rows, { auxiliary: true, group: '', search: '' }), [
    controller,
    workflow,
  ]);
  assert.deepEqual(filterActions(rows, { auxiliary: false, group: 'S1 点胶', search: '上视' }), []);
});

test('导出只含筛选后的动作，保留部分耗时说明及中文，并转义表格公式和引号', () => {
  const malicious = { ...action, class_name: 'Other', name: '=SUM(1,2)"测试', group: 'S1 点胶' };
  const selected = filterActions([action, malicious], {
    auxiliary: false,
    group: 'S2 固晶',
    search: '',
  });
  const csv = actionTableCsv(selected);
  assert.ok(csv.startsWith('\ufeff'));
  assert.equal(csv.trim().split('\r\n').length, 2);
  assert.ok(csv.includes('20–40 ms + 运动与等待时间'));
  assert.ok(!csv.includes('SUM'));
  assert.ok(actionTableCsv([malicious]).includes('"\'=SUM(1,2)""测试"'));
});
