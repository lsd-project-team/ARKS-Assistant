import test from 'node:test';
import assert from 'node:assert/strict';
import {
  projectThreadOrder,
  threadProject,
  visibleThreads,
} from '../../src/features/chat/lib/sidebarNavigation.ts';

test('打开较早的对话后，预览保留当前选择且不增加默认行数', () => {
  const rows = [{ id: 'first' }, { id: 'second' }, { id: 'third' }, { id: 'fourth' }];
  const selected = { id: 'older' };
  assert.deepEqual(
    visibleThreads(rows, selected, 3).map((row) => row.id),
    ['first', 'second', 'older'],
  );
  assert.deepEqual(
    visibleThreads(rows, rows[1], 3).map((row) => row.id),
    ['first', 'second', 'third'],
  );
  assert.deepEqual(
    visibleThreads(rows, selected).map((row) => row.id),
    ['first', 'second', 'third', 'fourth', 'older'],
  );
});

test('归档项目合并分页时保留置顶顺序、按时间排序并消除重复行', () => {
  const rows = [
    { id: 'older', updated_at: '2026-10-10', pinned_order: null },
    { id: 'pin-two', updated_at: '2026-10-09', pinned_order: 2 },
    { id: 'newest', updated_at: '2026-10-12', pinned_order: null },
    { id: 'pin-one', updated_at: '2026-10-08', pinned_order: 1 },
    { id: 'older', updated_at: '2026-10-10', pinned_order: null },
  ];
  assert.deepEqual(
    projectThreadOrder(rows).map((row) => row.id),
    ['pin-one', 'pin-two', 'newest', 'older'],
  );
  assert.equal(rows.length, 5);
});

test('最近列表的项目归属来自对话行，独立对话使用独立命名空间', () => {
  assert.equal(threadProject({ project_id: 'project-b' }), 'project-b');
  assert.equal(threadProject({ project_id: null }), 'independent');
  assert.equal(threadProject({}), 'independent');
});
