import test from 'node:test';
import assert from 'node:assert/strict';
import {
  motionFixedNote,
  componentTime,
} from '../../src/features/action_timing/source-detail-presentation.ts';
import {
  actionPresentation,
  actionTableCsv,
} from '../../src/features/action_timing/presentation.ts';

test('包内20 ms等待明确展示与运动重叠，不伪造完整运动时长', () => {
  assert.match(motionFixedNote({ source_fixed_wait_ms: 20 }), /20 ms.*重叠.*不另加/);
  assert.match(motionFixedNote({ source_fixed_wait_ms: 20 }), /初始化等门禁通过时/);
  assert.equal(motionFixedNote({ source_fixed_wait_ms: 0 }), '');
  assert.equal(motionFixedNote(undefined), '');
});

const component = {
  milliseconds: 90,
  factors: ['点数', '每点次数'],
  conditions: [],
  sources: [],
  scope: 'conditional',
  note: '',
};
const row = {
  id: 'loop',
  name: '标定步骤',
  kind: 'workflow',
  class_name: 'Teach',
  group: '公共动作',
  known_delay_min_ms: 0,
  known_delay_max_ms: null,
  total_ms: null,
  source_components: [component],
  missing_categories: ['input'],
};

test('未知次数保留90 ms每轮组成，表格导出保留条件及未定含义', () => {
  assert.equal(componentTime(component), '90 ms × 点数 × 每点次数');
  const view = actionPresentation(row);
  assert.equal(view.duration, '条件组成 90 ms × 待定次数');
  assert.match(view.remainder, /完整耗时未定/);
  assert.match(view.note, /当前配方、输入值或循环次数/);
  assert.match(actionTableCsv([row]), /条件组成 90 ms × 待定次数.*完整耗时未定/);
});

test('后台1秒不作为按钮同步总耗时，已有前台等待继续优先', () => {
  const action = {
    ...row,
    source_components: [],
    known_components: [{ ...component, milliseconds: 1000, factors: [], scope: 'background' }],
  };
  assert.equal(actionPresentation(action).duration, '后台停留 1,000 ms');
  assert.match(actionPresentation(action).remainder, /完整耗时未定/);
  assert.equal(
    actionPresentation({ ...action, known_delay_min_ms: 20, known_delay_max_ms: 20 }).duration,
    '20 ms',
  );
  assert.equal(
    actionPresentation({ ...action, execution_status: 'skipped' }).duration,
    '空跑不动作',
  );
});

test('展开保护明确归为未完成的分析，表格与导出不宣称源码无法计算', () => {
  const action = {
    ...row,
    source_components: [{ ...component, milliseconds: 15, factors: [] }],
    truncated: true,
    missing_categories: ['analysis'],
    motion_count: 1,
  };
  const view = actionPresentation(action);
  assert.equal(view.duration, '条件组成 15 ms');
  assert.match(view.note, /源码分析尚未完成/);
  assert.doesNotMatch(view.note, /无法由.*源码|缺少.*硬件/);
  assert.match(actionTableCsv([action]), /源码分析尚未完成/);
});

test('同步发起为零仍显示后台等待，表格和导出不把1秒误报成同步耗时', () => {
  const action = {
    ...row,
    total_ms: 0,
    execution_status: 'complete',
    source_components: [],
    known_components: [{ ...component, milliseconds: 1000, factors: [], scope: 'background' }],
  };
  const view = actionPresentation(action);
  assert.equal(view.duration, '后台停留 1,000 ms');
  assert.equal(view.remainder, '当前同步路径无固定停留');
  assert.match(view.note, /与当前同步停留分开.*完成关系/);
  assert.equal(view.hasDuration, true);
  assert.match(actionTableCsv([action]), /后台停留 1,000 ms 当前同步路径无固定停留/);
});

test('同步路径无等待时仍可展示条件组成，不能暗示该条件当前已经执行', () => {
  const action = {
    ...row,
    total_ms: 0,
    execution_status: 'complete',
    source_components: [{ ...component, milliseconds: 100, factors: [] }],
  };
  const view = actionPresentation(action);
  assert.equal(view.duration, '条件组成 100 ms');
  assert.equal(view.remainder, '当前同步路径无固定停留');
  assert.match(view.note, /触发条件.*完成关系/);
  assert.equal(actionPresentation({ ...action, execution_status: 'skipped' }).hasDuration, false);
});

test('已有同步耗时继续显示同步结果，不与后台组成相加', () => {
  const action = {
    ...row,
    known_delay_min_ms: 20,
    known_delay_max_ms: 20,
    total_ms: 20,
    known_components: [{ ...component, milliseconds: 1000, factors: [], scope: 'background' }],
  };
  assert.equal(actionPresentation(action).duration, '20 ms');
  assert.doesNotMatch(actionTableCsv([action]), /1,020|1,000/);
});
