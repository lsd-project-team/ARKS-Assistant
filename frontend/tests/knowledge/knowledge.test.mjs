import test from 'node:test';
import assert from 'node:assert/strict';
import { routeFromHash, routeHash } from '../../src/features/knowledge/routes.ts';

test('功能专题和流程图路由刷新后可恢复', () => {
  for (const route of [
    { kind: 'graphs' },
    { kind: 'modules' },
    { kind: 'topic', id: 'architecture' },
    { kind: 'catalog', id: 'zx2200-architecture' },
    { kind: 'graph', slug: 'startup-workflow', signal: '运行条件' },
  ])
    assert.deepEqual(routeFromHash('#' + routeHash(route)), route);
  assert.deepEqual(routeFromHash('#unknown'), { kind: 'chat' });
});

test('历史源码链接统一回到功能目录，不恢复已删除的快照页面', () => {
  for (const hash of [
    '#source-file/id?start=12&end=30',
    '#source-file/id?start=-3&end=nan',
    '#source-method/abc123',
    '#source-module/module1',
    '#source-import',
  ])
    assert.deepEqual(routeFromHash(hash), { kind: 'modules' });
});
