import test from 'node:test';
import assert from 'node:assert/strict';
import { refreshSnapshot } from '../../src/features/knowledge/freshness.ts';
import { routeFromHash, routeHash, workspacePath } from '../../src/features/knowledge/routes.ts';
import { knowledgeSelection } from '../../src/features/knowledge/sourceContext.ts';

test('资料路由保留原图、专题、方法与行号，刷新后可恢复', () => {
  for (const route of [
    { kind: 'graphs' },
    { kind: 'modules' },
    { kind: 'topic', id: 'architecture' },
    { kind: 'graph', slug: 'startup-workflow', signal: '运行条件' },
    { kind: 'source-method', id: 'abc123' },
    { kind: 'source-module', id: 'module1' },
    { kind: 'source-file', id: 'file1', start: 12, end: 30 },
  ])
    assert.deepEqual(routeFromHash('#' + routeHash(route)), route);
  assert.deepEqual(routeFromHash('#source-file/id?start=-3&end=nan'), {
    kind: 'source-file',
    id: 'id',
    start: 1,
    end: 1,
  });
  assert.deepEqual(routeFromHash('#unknown'), { kind: 'chat' });
  assert.equal(workspacePath('trunk\\AKRS.ZX2200\\Program.cs'), 'AKRS.ZX2200/Program.cs');
});

test('变化、缺失、尚未核对的文件不能沿用旧资料的一致标记', () => {
  const source = {
    files: [
      { id: 'a', path: 'trunk/a.cs', current: true, exists: true },
      { id: 'b', path: 'trunk/b.cs', current: true, exists: true },
    ],
    reviewCurrent: true,
    relationships: [{ current: true, evidence: [{ fileId: 'a', current: true }] }],
  };
  const refreshed = refreshSnapshot(source, { a: { status: 'changed' }, b: { status: 'missing' } });
  assert.equal(refreshed.files[0].current, false);
  assert.equal(refreshed.files[1].exists, false);
  assert.equal(refreshed.staleFiles, 2);
  assert.equal(refreshed.reviewCurrent, false);
  assert.equal(refreshed.relationships[0].evidence[0].current, false);
  assert.equal(refreshed.relationships[0].current, false);
  assert.equal(refreshSnapshot(source, {}).files[0].current, false);
  assert.equal(source.files[0].current, true, '共享的静态资料不能被原地改写');
});

test('部分声明变化会使方法调用状态失效，匹配也不能覆盖旧版已失效记录', () => {
  const method = {
    current: true,
    declarations: [{ fileId: 'a' }, { fileId: 'b' }],
    outgoing: [{ fileId: 'a', current: true }],
  };
  const checks = { a: { status: 'match' }, b: { status: 'changed' } };
  assert.equal(refreshSnapshot(method, checks).current, false);
  assert.equal(refreshSnapshot(method, checks).outgoing[0].current, true);
  assert.equal(refreshSnapshot({ fileId: 'a', current: false }, checks).current, false);
});

test('图谱携带的源码选区保留 CRLF、中文和准确行列，并遵守上下文上限', () => {
  const source = {
    path: '中文.cs',
    version: 'v1',
    content: '第一行\r\n\t中文😀\r\n末行\r\n',
    line_count: 3,
  };
  const selection = knowledgeSelection(source, 1, 3);
  assert.equal(selection.content, '第一行\r\n\t中文😀\r\n末行');
  assert.equal(selection.end_column, 3);
  assert.equal(selection.version, 'v1');
  assert.equal(knowledgeSelection(source, 8, 9), null);
  const manyLines = {
    ...source,
    content: Array.from({ length: 100 }, (_, i) => `行${i}`).join('\r\n'),
    line_count: 100,
  };
  assert.equal(knowledgeSelection(manyLines, 1, 100).end_line, 60);
  const longLine = {
    ...source,
    content: 'a'.repeat(59999) + '😀' + 'b'.repeat(10000),
    line_count: 1,
  };
  assert.equal(knowledgeSelection(longLine, 1, 1).content.length, 59999);
});

test('跨模块依赖中的例子或关联模块变化后，整条关系需要重新确认', () => {
  const relation = {
    from: 'moduleA',
    to: 'moduleB',
    current: true,
    samples: [{ fileId: 'fileA', current: true }],
  };
  assert.equal(refreshSnapshot(relation, { fileA: { status: 'changed' } }).current, false);
  assert.equal(
    refreshSnapshot(relation, {
      fileA: { status: 'match' },
      moduleA: { status: 'match' },
      moduleB: { status: 'changed' },
    }).current,
    false,
  );
});
