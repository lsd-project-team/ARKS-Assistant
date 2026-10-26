import test from 'node:test';
import assert from 'node:assert/strict';
import {
  durationText,
  actionValues,
  importSummary,
} from '../../src/features/action_timing/ledger-format.ts';

test('空耗时显示待填写，实际零值和极小数值完整保留', () => {
  assert.equal(durationText(null), '待填写');
  assert.equal(durationText(undefined), '待填写');
  assert.equal(durationText(0), '0');
  assert.equal(durationText(1.25), '1.25');
  assert.equal(durationText(0.00000001), '0.00000001');
});

test('添加与编辑使用同一表单契约，空值不变成零', () => {
  assert.deepEqual(actionValues('  取料  ', '', ' ', '  后续补充  '), {
    name: '取料',
    category_id: null,
    duration_seconds: null,
    notes: '后续补充',
  });
  assert.deepEqual(actionValues('取料', 'category-id', '0', ''), {
    name: '取料',
    category_id: 'category-id',
    duration_seconds: 0,
    notes: '',
  });
});

for (const duration of ['-1', 'NaN', 'Infinity', '不是数值']) {
  test(`拒绝无效耗时 ${duration}`, () => {
    assert.throws(() => actionValues('动作', '', duration, ''), /非负数/);
  });
}

test('空名称阻止提交，导入结果区分新增、更新与跳过', () => {
  assert.throws(() => actionValues('  ', '', '', ''), /动作名称/);
  assert.equal(importSummary({ add: 2, update: 1, skip: 3 }), '新增 2，更新 1，跳过 3');
});
