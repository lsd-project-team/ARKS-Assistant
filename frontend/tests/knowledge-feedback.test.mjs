import test from 'node:test';
import assert from 'node:assert/strict';
import { distinctReferences, searchNotices } from '../src/lib/knowledgeFeedback.ts';

const reference = {
  kind: 'debug_issue',
  id: 'a',
  title: '取片异常',
  version: 1,
  citation: 'debug-issue:a/1',
};

test('多轮返回相同引用只显示一次，不合并不同引用版本', () => {
  const rows = distinctReferences([
    reference,
    reference,
    { ...reference, version: 2, citation: 'debug-issue:a/2' },
  ]);
  assert.equal(rows.length, 2);
});

test('首次未命中而后续补查成功，不继续显示没有资料', () => {
  const rows = searchNotices(
    [
      { kind: 'debug_issue', matched: 0 },
      { kind: 'debug_issue', matched: 1 },
    ],
    [reference],
  );
  assert.deepEqual(rows, []);
});

test('区分未命中、条件排除、附件不可读与语义降级', () => {
  const rows = searchNotices(
    [
      {
        kind: 'handover_material',
        matched: 0,
        excluded_conditions: 1,
        unreadable: 1,
        degraded: true,
      },
    ],
    [],
  );
  assert.equal(rows.length, 4);
  assert.ok(rows.some((text) => text.includes('条件不符')));
  assert.ok(rows.some((text) => text.includes('关键词和同义词')));
});

test('后续语义检索恢复后，不继续提示降级', () => {
  assert.deepEqual(
    searchNotices(
      [
        { kind: 'material', matched: 1, degraded: true },
        { kind: 'material', matched: 1, degraded: false },
      ],
      [],
    ),
    [],
  );
});
