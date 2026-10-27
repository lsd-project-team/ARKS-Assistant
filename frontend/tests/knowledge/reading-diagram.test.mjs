import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createReadingDiagram } from '../../src/features/knowledge/coordinates/archifyReadingPage.ts';

const resources = new URL('../../../resources/knowledge/flows/g0-archify/', import.meta.url);
const json = async (name) => JSON.parse(await readFile(new URL(`${name}.json`, resources), 'utf8'));

test('阅读副本保留 Archify 全部节点、连线与自然尺寸，移除脚本和无效交互', async () => {
  for (const name of [
    'device-tree',
    'product-tree',
    'camera-workflow',
    'device-reading',
    'camera-reading',
  ]) {
    const spec = await json(name);
    const source = await readFile(new URL(`${name}.html`, resources), 'utf8');
    const page = createReadingDiagram(source, 'classic');
    const sourceViewBox = source
      .match(/<svg[^>]*viewBox="([^"]+)"/)[1]
      .split(/\s+/)
      .map(Number);
    assert.deepEqual([page.width, page.height], sourceViewBox.slice(2));
    for (const node of spec.nodes ?? spec.components) {
      assert.ok(page.html.includes(`data-node-id="${node.id}"`), `${name}: ${node.id}`);
      assert.ok(page.html.includes(node.label), `${name}: ${node.label}`);
    }
    assert.equal(
      (page.html.match(/\bdata-edge-from=/g) ?? []).length,
      (source.match(/\bdata-edge-from=/g) ?? []).length,
    );
    const body = page.html.slice(page.html.indexOf('<body>'));
    assert.equal(/<script\b|tabindex=|role="button"/.test(body), false);
    assert.match(page.html, /height: auto !important/);
    assert.match(createReadingDiagram(source, 'dark').html, /data-theme="dark"/);
  }
});

test('纵向阅读图与原图拥有相同节点和方向关系，不省略相机或输入', async () => {
  for (const [original, reading] of [
    ['device-tree', 'device-reading'],
    ['camera-workflow', 'camera-reading'],
  ]) {
    const full = await json(original);
    const narrow = await json(reading);
    assert.deepEqual(
      narrow.components.map((node) => node.id).sort(),
      full.nodes.map((node) => node.id).sort(),
    );
    const edges =
      full.edges ??
      full.nodes.filter((node) => node.parent).map((node) => ({ from: node.parent, to: node.id }));
    const pairs = (items) => items.map((edge) => `${edge.from}>${edge.to}`).sort();
    assert.deepEqual(pairs(narrow.connections), pairs(edges));
  }
});

test('无法确定图形尺寸时不输出裁切或空白阅读图', () => {
  for (const html of [
    '',
    '<svg></svg>',
    '<svg viewBox="0 0 0 100"></svg>',
    '<svg viewBox="0 0 NaN 100"></svg>',
  ]) {
    assert.throws(() => createReadingDiagram(html, 'white'));
  }
});

test('产品定位图在阅读副本中保留限内写回与超限异常的方向', async () => {
  const source = await readFile(
    new URL(
      '../../../resources/knowledge/flows/functional-atlas/product-update.html',
      import.meta.url,
    ),
    'utf8',
  );
  const page = createReadingDiagram(source, 'classic');
  for (const [from, to, label] of [
    ['gate', 'write', '通过'],
    ['gate', 'error', '超限'],
  ]) {
    assert.ok(
      page.html.includes(
        `data-edge-from="${from}" data-edge-to="${to}" data-edge-label="${label}"`,
      ),
    );
  }
  assert.equal((page.html.match(/<g\b[^>]*data-node-id=/g) ?? []).length, 7);
  assert.doesNotMatch(page.html, /<script\b/);
  assert.match(page.html, /\[data-edge-id\] text \{ font-size: 14px/);
});

test('公共视觉图保留自动结果、人工回传与退出，不能把失败统一连到成功', async () => {
  const source = await readFile(
    new URL(
      '../../../resources/knowledge/flows/functional-atlas/vision-point.html',
      import.meta.url,
    ),
    'utf8',
  );
  const page = createReadingDiagram(source, 'classic');
  for (const [from, to, label] of [
    ['result', 'alarm', '空值'],
    ['alarm', 'convert', 'OK'],
    ['alarm', 'exit', '非 OK'],
  ])
    assert.ok(
      page.html.includes(
        `data-edge-from="${from}" data-edge-to="${to}" data-edge-label="${label}"`,
      ),
    );
  assert.equal((page.html.match(/<g\b[^>]*data-node-id=/g) ?? []).length, 7);
  assert.doesNotMatch(page.html, /data-edge-from="exit" data-edge-to="save"/);
});

test('标定图保留可跳过的同标记步骤及真实 S2 调度顺序', async () => {
  const source = await readFile(
    new URL(
      '../../../resources/knowledge/flows/functional-atlas/camera-calibration.html',
      import.meta.url,
    ),
    'utf8',
  );
  const page = createReadingDiagram(source, 'classic');
  const path = ['prepare', 'bond', 'offset', 'optional', 'position', 'wafer', 'results'];
  for (let index = 0; index < path.length - 1; index++)
    assert.ok(
      page.html.includes(`data-edge-from="${path[index]}" data-edge-to="${path[index + 1]}"`),
    );
  assert.equal((page.html.match(/<g\b[^>]*data-node-id=/g) ?? []).length, 7);
  assert.match(page.html, /确认执行，取消跳过/);
});

test('安全移动图先经限位和单步门控，再分成三种顺序而非顺序执行全部路径', async () => {
  const source = await readFile(
    new URL(
      '../../../resources/knowledge/flows/functional-atlas/safe-motion-branches.html',
      import.meta.url,
    ),
    'utf8',
  );
  const page = createReadingDiagram(source, 'classic');
  for (const [from, to] of [
    ['target', 'prepare'],
    ['prepare', 'single'],
    ['single', 'branch'],
    ['branch', 'xy-first'],
    ['branch', 'z-first'],
    ['branch', 'lift-first'],
  ])
    assert.ok(page.html.includes(`data-edge-from="${from}" data-edge-to="${to}"`));
  assert.equal((page.html.match(/<g\b[^>]*data-node-id=/g) ?? []).length, 7);
  assert.doesNotMatch(page.html, /data-edge-from="xy-first" data-edge-to="z-first"/);
  assert.match(page.html, /拒绝则直接返回/);
});

test('安全移动窄图保留原图的全部节点、含义和分支，仅缩紧排布', async () => {
  const folder = new URL('../../../resources/knowledge/flows/functional-atlas/', import.meta.url);
  const full = JSON.parse(await readFile(new URL('safe-motion-branches.json', folder), 'utf8'));
  const narrow = JSON.parse(await readFile(new URL('safe-motion-reading.json', folder), 'utf8'));
  const meaning = ({ pos, size, ...node }) => node;
  assert.deepEqual(narrow.components.map(meaning), full.components.map(meaning));
  assert.deepEqual(narrow.connections, full.connections);
  const source = await readFile(new URL('safe-motion-reading.html', folder), 'utf8');
  const page = createReadingDiagram(source, 'classic');
  assert.ok(page.width < 430);
  for (const node of full.components) assert.ok(page.html.includes(`data-node-id="${node.id}"`));
});
