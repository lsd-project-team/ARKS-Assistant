import test from 'node:test';
import assert from 'node:assert/strict';
import { archifyData } from '../../src/features/knowledge/data/archifyData.ts';
import {
  graphCollections,
  graphOwner,
  graphMemberIds,
  primaryWorkflowIds,
} from '../../src/features/knowledge/data/graphCollections.ts';
import {
  graphDirectory,
  publicGraphs,
  graphMembers,
  searchGraphDirectory,
  relatedGraphs,
} from '../../src/features/knowledge/data/graphDirectory.ts';
import { displayDiagramTitle } from '../../src/features/knowledge/data/presentation.ts';
import { diagramRoute, routeFromHash, routeHash } from '../../src/features/knowledge/routes.ts';

test('20组合并成77个入口，原121张图恰好归属一次且保留8条主流程', () => {
  assert.equal(Object.keys(graphCollections).length, 20);
  assert.equal(graphDirectory.length, 77);
  assert.equal(publicGraphs.length, 121);
  const expanded = graphDirectory.flatMap((entry) =>
    graphMembers(entry.id).map((member) => member.id),
  );
  assert.equal(expanded.length, 121);
  assert.equal(new Set(expanded).size, 121);
  assert.deepEqual(new Set(expanded), new Set(publicGraphs.map((entry) => entry.id)));
  assert.deepEqual(
    new Set(graphDirectory.filter((entry) => entry.chapter).map((entry) => entry.id)),
    primaryWorkflowIds,
  );
  assert.deepEqual(new Set(archifyData.graphs.map((entry) => entry.slug)), primaryWorkflowIds);
  for (const id of [
    'g0-coordinate-system',
    'product-coordinate-lifecycle',
    'global-calibration-process',
    'camera-calibration-process',
    'tool-calibration-process',
    'pickup-workflow',
    'bond-action-workflow',
  ])
    assert.equal(graphOwner(id), id, '不同用途的图仍独立：' + id);
});

test('旧名称和编号可命中所属主入口并直接选中原细节图', () => {
  for (const id of Object.values(graphCollections).flat()) {
    const entry = publicGraphs.find((entry) => entry.id === id);
    for (const term of [id, displayDiagramTitle(id, entry.title)]) {
      const result = searchGraphDirectory(term).find(
        (result) => result.entry.id === graphOwner(id),
      );
      assert.ok(result, term);
      assert.equal(result.match.id, id, term);
    }
  }
  assert.equal(searchGraphDirectory('完全没有这张图-123').length, 0);
  assert.equal(searchGraphDirectory('   ').length, 77);
});

test('类型可找到主图内的时序图，条件必须在同一成员命中', () => {
  const results = searchGraphDirectory('轴到位等待与返回', 'sequence');
  assert.deepEqual(
    results.map(({ entry, match }) => [entry.id, match.id]),
    [['safe-motion-process', 'motion-arrival-sequence']],
  );
  assert.equal(searchGraphDirectory('轴到位等待与返回', 'architecture').length, 0);
  assert.equal(searchGraphDirectory('', 'all', 'main').length, 8);
  assert.equal(searchGraphDirectory('', 'all', 'detail').length, 69);
});

test('全部旧图链接和新子图链接都恢复原图，保留中文信号与章节', () => {
  for (const entry of publicGraphs) {
    const oldKind = primaryWorkflowIds.has(entry.id) ? 'graph' : 'catalog';
    const route = routeFromHash(`#${oldKind}/${entry.id}`);
    assert.equal(route.slug ?? route.id, graphOwner(entry.id));
    assert.equal(route.view ?? route.slug ?? route.id, entry.id);
    assert.deepEqual(routeFromHash('#' + routeHash(route)), route);
  }
  const route = routeFromHash('#catalog/manual-01?section=中文%26章节&signal=启动%26条件');
  assert.deepEqual(route, {
    kind: 'graph',
    slug: 'startup-workflow',
    view: 'manual-01',
    signal: '启动&条件',
    section: '中文&章节',
  });
  assert.deepEqual(routeFromHash('#' + routeHash(route)), route);
  assert.equal(
    routeHash(diagramRoute('safe-motion-process', { view: 'safe-motion' })),
    'catalog/safe-motion-process?view=safe-motion',
  );
});

test('越组与非法子图参数回到本组主图，相关阅读去重且不指回本组', () => {
  for (const view of ['manual-31', 'missing', '__proto__', 'constructor'])
    assert.deepEqual(routeFromHash('#graph/startup-workflow?view=' + view), {
      kind: 'graph',
      slug: 'startup-workflow',
    });
  for (const entry of graphDirectory) {
    const related = relatedGraphs(entry.id).map((item) => item.id);
    assert.equal(related.length, new Set(related).size);
    assert.ok(
      related.every((id) => graphOwner(id) === id && !graphMemberIds(entry.id).includes(id)),
    );
  }
});
