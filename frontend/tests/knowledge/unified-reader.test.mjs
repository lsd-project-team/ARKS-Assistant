import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { JSDOM } from 'jsdom';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createElement, useEffect, act } from 'react';
import { archifyData } from '../../src/features/knowledge/data/archifyData.ts';
import { coordinateArtifacts } from '../../src/features/knowledge/data/coordinateDiagrams.ts';
import { functionalArtifacts } from '../../src/features/knowledge/data/functionalTopics.ts';
import { sourceGuides } from '../../src/features/knowledge/sourceGuides.ts';
import { diagramDocument } from '../../src/features/knowledge/reader/diagramDocument.ts';
import { flowDocument } from '../../src/features/knowledge/reader/flowDocument.ts';

const dom = new JSDOM('<html><body></body></html>', { pretendToBeVisual: true });
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.DOMParser = dom.window.DOMParser;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const { createRoot } = await import('react-dom/client');
const bundle = await build({
  stdin: {
    contents: "export * from './src/features/knowledge/reader/ReaderFrame.tsx';",
    resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
    loader: 'tsx',
  },
  bundle: true,
  write: false,
  platform: 'node',
  format: 'cjs',
  packages: 'external',
  jsx: 'automatic',
  loader: { '.css': 'empty' },
});
const module = { exports: {} };
new Function('require', 'module', 'exports', bundle.outputFiles[0].text)(
  createRequire(import.meta.url),
  module,
  module.exports,
);
const { ReaderFrame, useReaderCanvas } = module.exports;

test('统一适配器覆盖全部独立交付及坐标、标定图，保留原节点、连线与尺寸', async () => {
  const paths = new Set([
    ...archifyData.flowchartCatalog.entries
      .filter((entry) => entry.type !== 'supplemental' && !entry.inlineTopic)
      .map((entry) => entry.html.replace(/^docs[\\/]archify[\\/]/, '')),
    ...coordinateArtifacts.map((entry) => entry.path),
    ...Object.values(functionalArtifacts).map((entry) => entry.path),
  ]);
  assert.ok(paths.size > 100);
  for (const path of paths) {
    const source = await readFile(
      new URL(`../../../resources/knowledge/flows/${path}`, import.meta.url),
      'utf8',
    );
    const adapted = diagramDocument(source, 'light', '');
    const parsed = new DOMParser().parseFromString(adapted.html, 'text/html');
    const svg = parsed.querySelector('body > svg');
    assert.ok(svg, path);
    assert.equal(svg.getAttribute('role'), 'group', path);
    const preset =
      source.match(/<html[^>]*data-preset="([^"]+)"/)?.[1] ?? svg.dataset.preset ?? 'classic';
    assert.equal(parsed.documentElement.dataset.preset, preset, path);
    assert.equal(parsed.querySelectorAll('script,iframe,foreignObject').length, 0, path);
    const raw = source.slice(
      source.indexOf('<svg '),
      source.indexOf('</svg>', source.indexOf('<svg ')) + 6,
    );
    assert.equal(
      svg.querySelectorAll('[data-node-id]').length,
      (raw.match(/data-node-id="/g) ?? []).length,
      path,
    );
    assert.equal(
      svg.querySelectorAll('[data-edge-from]').length,
      (raw.match(/data-edge-from="/g) ?? []).length,
      path,
    );
    assert.deepEqual(
      adapted.bounds,
      svg
        .getAttribute('viewBox')
        .trim()
        .split(/[\s,]+/)
        .map(Number),
      path,
    );
    assert.equal(new Set(adapted.nodes.map((item) => item.id)).size, adapted.nodes.length, path);
  }
});

test('异常交付独立失败，图内事件、脚本和外链不会进入阅读文档', () => {
  for (const source of ['<html/>', '<svg viewBox="0 0 NaN 10"/>', '<svg viewBox="0 0 -1 10"/>'])
    assert.throws(() => diagramDocument(source, 'light', ''), /SVG|尺寸/);
  const adapted = diagramDocument(
    `<svg viewBox="0 0 400 200" onload="bad()"><script>bad()</script>
    <foreignObject><div>bad</div></foreignObject><image href="https://external.test/pixel"/>
    <g data-node-id="a" data-node-label="入口" data-node-sublabel="读取参数"><rect width="40" height="20" onclick="bad()"/></g>
    <g data-node-id="b" data-node-label="结果"/>
    <g data-edge-from="a" data-edge-to="b" data-edge-label="成功" data-edge-id="ab"/>
    <g data-edge-from="a" data-edge-to="b" data-edge-label="成功" data-edge-id="ab-hit"/></svg>`,
    'dark',
    '',
  );
  assert.doesNotMatch(adapted.html, /<script|foreignObject|onload|onclick|external\.test/);
  assert.equal(adapted.nodes[0].description, '读取参数');
  assert.deepEqual(adapted.nodes[0].branches, [{ id: 'ab', target: 'b', label: '成功 → 结果' }]);
  assert.match(adapted.html, /data-theme="dark"/);
});

test('全部210条说明保持节点标题，只有已定义顺序的流程才绘制执行箭头', () => {
  for (const guide of sourceGuides)
    for (const flow of guide.flows) {
      const adapted = diagramDocument(flowDocument(flow), 'light', '');
      assert.deepEqual(
        adapted.nodes.map((item) => item.id),
        flow.steps.map((item) => item.id),
      );
      assert.deepEqual(
        adapted.nodes.map((item) => item.label),
        flow.steps.map((item) => item.title),
      );
      assert.equal(
        adapted.nodes.reduce((sum, item) => sum + item.branches.length, 0),
        flow.sequential === false ? 0 : flow.steps.length - 1,
        flow.id,
      );
    }
});

test('工具栏操作实际画布接口，搜索后选择节点并能关闭说明区', async () => {
  const target = document.createElement('div');
  document.body.append(target);
  const root = createRoot(target);
  const calls = [];
  function Canvas() {
    const bridge = useReaderCanvas();
    useEffect(
      () =>
        bridge.register(
          [
            { id: 'a', label: '读取配方', branches: [] },
            { id: 'b', label: '任务调度', description: 'BondTask', branches: [] },
          ],
          {
            fit: () => calls.push('fit'),
            zoom: (factor) => calls.push(factor),
            export: () => calls.push('export'),
          },
        ),
      [bridge.register],
    );
    return createElement('span', { 'data-selected': bridge.selected }, '画布');
  }
  await act(async () =>
    root.render(createElement(ReaderFrame, { title: '验收' }, createElement(Canvas))),
  );
  assert.equal(target.querySelector('.reader-detail').hidden, true);
  const click = async (selector) => act(async () => target.querySelector(selector).click());
  await click('.reader-tools > button');
  await click('[aria-label="放大图谱"]');
  await click('.reader-tools > button:last-child');
  assert.deepEqual(calls, ['fit', 1.25, 'export']);
  const search = target.querySelector('input');
  await act(async () => {
    Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(
      search,
      'BondTask',
    );
    search.dispatchEvent(new window.Event('input', { bubbles: true }));
  });
  assert.match(target.querySelector('.reader-search-results').textContent, /找到 1 个节点/);
  await click('.reader-search-results button');
  assert.equal(target.querySelector('[data-selected]').dataset.selected, 'b');
  assert.equal(target.querySelector('.reader-detail h2').textContent, '任务调度');
  assert.equal(target.querySelector('.reader-detail').hidden, false);
  await click('[aria-controls][aria-pressed]');
  assert.equal(target.querySelector('.reader-detail').hidden, true);
  await act(async () => root.unmount());
  target.remove();
});

test.after(() => dom.window.close());
