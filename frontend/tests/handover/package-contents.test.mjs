import test from 'node:test';
import assert from 'node:assert/strict';
import {
  packageGroups,
  packageNotes,
} from '../../src/features/handover/packages/packageContents.ts';

test('历史访谈归入资料，包内分类保留打包时版本，更新和归档不替换固定引用', () => {
  const payload = {
    records: [
      { record_id: 'task', version: 2 },
      { record_id: 'source', version: 1 },
      { record_id: 'interview', version: 3 },
      { record_id: 'decision', version: 2 },
    ],
  };
  const records = [
    { id: 'source', kind: 'source', title: '资料', version: 9, state: 'archived' },
    { id: 'task', kind: 'task', title: '工作', version: 6 },
    { id: 'interview', kind: 'interview', title: '访谈', version: 5 },
    { id: 'decision', kind: 'decision', title: '决策', version: 3 },
  ];
  const original = structuredClone({ payload, records });
  const groups = packageGroups(payload, records);
  assert.deepEqual(
    groups.map((group) => group.id),
    ['source', 'task', 'other'],
  );
  assert.deepEqual(
    groups.flatMap((group) => group.items.map((item) => [item.record_id, item.version])),
    [
      ['source', 1],
      ['interview', 3],
      ['task', 2],
      ['decision', 2],
    ],
  );
  assert.deepEqual({ payload, records }, original);
});

test('去重仅合并相同固定引用，不合并同一记录的不同版本，缺失目录条目仍可查看引用', () => {
  const payload = {
    records: [
      { record_id: 'same', version: 1 },
      { record_id: 'same', version: 1 },
      { record_id: 'same', version: 2 },
      { record_id: 'unknown', version: 4, locator: '说明', quote: '原文' },
    ],
  };
  const groups = packageGroups(payload, [{ id: 'same', kind: 'source', title: '来源' }]);
  assert.equal(groups[0].items.length, 2);
  assert.deepEqual(groups[1].items, [
    { record_id: 'unknown', version: 4, locator: '说明', quote: '原文', title: 'unknown' },
  ]);
  assert.deepEqual(packageGroups({}, []), []);
});

test('空交接说明隐藏，有内容的待补充事项和备注保留原始文本', () => {
  const payload = { scope: ' \n ', gaps: '待补充现场记录\n第二条', notes: '  原始备注  ' };
  const original = structuredClone(payload);
  assert.deepEqual(packageNotes(payload), [
    { id: 'gaps', label: '待补充事项', content: payload.gaps },
    { id: 'notes', label: '补充说明', content: payload.notes },
  ]);
  assert.deepEqual(packageNotes({}), []);
  assert.deepEqual(payload, original);
});
