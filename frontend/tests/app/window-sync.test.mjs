import test from 'node:test';
import assert from 'node:assert/strict';
import { mergedStorage } from '../../src/app/state/mergedStorage.ts';
import { queryGroups } from '../../src/shared/api/querySync.ts';

test('两个窗口的草稿和阅读位置不被另一个窗口的布局写入覆盖', () => {
  const values = new Map();
  const storage = {
    getItem: (name) => values.get(name) || null,
    setItem: (name, value) => values.set(name, value),
    removeItem: (name) => values.delete(name),
  };
  const one = mergedStorage(storage),
    two = mergedStorage(storage);
  const save = (target, state) =>
    target.setItem('workspace', JSON.stringify({ state, version: 0 }));
  save(one, { drafts: { a: { content: 'A 的问题', selections: [] } }, positions: { 'a.cs': 20 } });
  two.getItem('workspace');
  save(two, {
    drafts: {
      a: { content: 'A 的问题', selections: [] },
      b: { content: 'B 的问题', selections: [] },
    },
    positions: { 'a.cs': 20, 'b.cs': 40 },
  });
  save(one, {
    drafts: { a: { content: 'A 的问题', selections: [] } },
    positions: { 'a.cs': 21 },
    collapsed: true,
  });
  let result = JSON.parse(storage.getItem('workspace')).state;
  assert.equal(result.drafts.b.content, 'B 的问题');
  assert.equal(result.positions['b.cs'], 40);
  assert.equal(result.positions['a.cs'], 21);
  save(one, { drafts: {}, positions: { 'a.cs': 21 } });
  save(two, {
    drafts: {
      a: { content: 'A 的问题', selections: [] },
      b: { content: 'B 的续问', selections: [] },
    },
    positions: { 'a.cs': 20, 'b.cs': 40 },
    collapsed: false,
  });
  result = JSON.parse(storage.getItem('workspace')).state;
  assert.equal(result.drafts.a, undefined);
  assert.equal(result.drafts.b.content, 'B 的续问');
  assert.equal(result.positions['a.cs'], 21);
});

test('变更路径只触发对应数据重读，检测和备份上传不改变设置草稿', () => {
  assert.ok(queryGroups('/threads/id/restore').includes('threads'));
  assert.ok(queryGroups('/runs/id/cancel').includes('thread'));
  assert.deepEqual(queryGroups('/settings'), ['settings']);
  assert.deepEqual(queryGroups('/backup/validate'), []);
  assert.deepEqual(queryGroups('/settings/probe'), []);
});
