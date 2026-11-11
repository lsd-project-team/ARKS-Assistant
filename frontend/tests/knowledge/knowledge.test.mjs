import test from 'node:test';
import assert from 'node:assert/strict';
import { routeFromHash, routeHash } from '../../src/features/knowledge/routes.ts';
import { presentationTopics } from '../../src/features/knowledge/data/presentation.ts';
import { archifyData } from '../../src/features/knowledge/data/archifyData.ts';
import { readingGraphPaths } from '../../src/features/knowledge/data/readingDestinations.ts';

test('旧目录回到全部图谱，23个旧专题链接直接恢复到公开图谱', () => {
  for (const hash of [
    '#modules',
    '#overview',
    '#topic/missing',
    '#topic/__proto__',
    '#topic/toString',
  ])
    assert.deepEqual(routeFromHash(hash), { kind: 'graphs' });
  assert.equal(presentationTopics.length, 23);
  assert.equal(Object.keys(readingGraphPaths).length, 23);
  for (const reading of presentationTopics) {
    const route = routeFromHash('#topic/' + reading.id);
    const id = route.slug ?? route.id;
    assert.equal(id, reading.diagrams[0], reading.id);
    assert.ok(
      archifyData.flowchartCatalog.entries.some(
        (entry) => entry.id === id && entry.type !== 'supplemental',
      ),
    );
    assert.deepEqual(routeFromHash('#' + routeHash(route)), route);
  }
});

test('图谱路由刷新后可恢复', () => {
  for (const route of [
    { kind: 'graphs' },
    { kind: 'catalog', id: 'zx2200-architecture' },
    { kind: 'graph', slug: 'startup-workflow', signal: '运行条件' },
  ])
    assert.deepEqual(routeFromHash('#' + routeHash(route)), route);
  assert.deepEqual(routeFromHash('#unknown'), { kind: 'chat' });
});

test('历史源码链接统一回到图谱目录，不恢复已删除的快照页面', () => {
  for (const hash of [
    '#source-file/id?start=12&end=30',
    '#source-file/id?start=-3&end=nan',
    '#source-method/abc123',
    '#source-module/module1',
    '#source-import',
  ])
    assert.deepEqual(routeFromHash(hash), { kind: 'graphs' });
});
