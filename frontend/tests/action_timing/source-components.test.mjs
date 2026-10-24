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
