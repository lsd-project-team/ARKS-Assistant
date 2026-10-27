import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { presentationTopics } from '../../src/features/knowledge/data/presentation.ts';
import { archifyData } from '../../src/features/knowledge/data/archifyData.ts';

const result = await build({
  stdin: {
    contents:
      "export * from './src/features/knowledge/KnowledgePages.tsx'; export { coordinateVisual } from './src/features/knowledge/coordinates/CoordinateReader.tsx';",
    resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
    loader: 'tsx',
  },
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  jsx: 'automatic',
  metafile: true,
  loader: { '.css': 'empty' },
  plugins: [
    {
      name: 'inline-css',
      setup(build) {
        build.onResolve({ filter: /\.css\?inline$/ }, ({ path }) => ({
          path,
          namespace: 'css-text',
        }));
        build.onLoad({ filter: /.*/, namespace: 'css-text' }, () => ({
          contents: 'export default "";',
          loader: 'js',
        }));
      },
    },
  ],
});
const module = { exports: {} };
new Function('require', 'module', 'exports', result.outputFiles[0].text)(
  createRequire(import.meta.url),
  module,
  module.exports,
);
const { TopicDetail, DiagramDetail, GraphAtlas, coordinateVisual } = module.exports;
const render = (component, props) =>
  renderToStaticMarkup(createElement(component, { navigate() {}, ...props }));

test('全部专题保留流程内容，不再显示源码模块、依据、路径和快照选区', () => {
  for (const topic of presentationTopics) {
    const html = render(TopicDetail, { id: topic.id });
    assert.ok(html.includes(topic.title));
    assert.match(html, /建议阅读顺序/);
    assert.doesNotMatch(
      html,
      /源码模块结构|关联源码模块|源码依据|查看依据|查看协作依据|source-evidence|source-module|<pre/,
    );
  }
  assert.ok(
    Object.keys(result.metafile.inputs).every(
      (path) => !/source-evidence\.json|EngineeringViews|engineeringData/.test(path),
    ),
  );
});

test('生产流程保留原图、节点说明和协作条件，移除节点依据', () => {
  for (const graph of archifyData.graphs) {
    const html = render(DiagramDetail, { id: graph.slug, theme: 'light' });
    assert.match(html, /<iframe/);
    assert.match(html, /深入阅读节点与模块协作/);
    assert.ok(html.includes(graph.nodes[0].label));
    assert.doesNotMatch(
      html,
      /源码依据|查看依据|查看协作依据|evidence-item|source-file|source-method|<pre/,
    );
  }
});

test('G0 从专题和图谱目录进入同一阅读页，使用 Archify 交付图', () => {
  const topic = render(TopicDetail, { id: 'g0' });
  const catalog = render(DiagramDetail, { id: 'g0-coordinate-system', theme: 'light' });
  assert.equal(catalog, topic);
  assert.match(topic, /data-archify-source="g0-archify\/device-tree\.html"/);
  assert.doesNotMatch(topic, /<svg[^>]+role="img"|g0-map-wide|g0-map-compact/);
  for (const label of [
    '坐标关系',
    '普通转换',
    '相机转换',
    '加载与保存',
    '标定与修正',
    '生产应用',
    '使用边界',
  ])
    assert.ok(topic.includes(label), label);
  assert.doesNotMatch(topic, /原图尚未生成|业务介绍|展开专题概览与协作条件/);
  assert.equal((topic.match(/<h1>/g) ?? []).length, 1);
});

test('G0 三张关系图都引用实际 Archify HTML，公式与数值例子继续留在节点内', () => {
  for (const [flow, step, source] of [
    ['g0-relations', 'reference', 'device-tree'],
    ['g0-relations', 'product', 'product-tree'],
    ['g0-camera', 'inputs', 'camera-reading'],
  ]) {
    const html = renderToStaticMarkup(coordinateVisual(flow, step));
    assert.ok(html.includes(`data-archify-source="g0-archify/${source}.html"`));
    assert.equal((html.match(/<figure/g) ?? []).length, 1);
    assert.match(html, /完整图谱/);
    assert.doesNotMatch(html, /图内可放大、拖动查看/);
  }
  assert.match(renderToStaticMarkup(coordinateVisual('g0-general', 'forward')), /cos θ/);
  assert.match(renderToStaticMarkup(coordinateVisual('g0-general', 'example')), /<table>/);
});

test('全部图谱包含可进入的 G0 内嵌阅读入口，既有独立图谱仍可展示', () => {
  const html = render(GraphAtlas, {});
  assert.match(html, /设备、产品和相机中的位置怎样转换为同一个 G0 目标/);
  const entry = archifyData.flowchartCatalog.entries.find(
    (item) => item.id === 'g0-coordinate-system',
  );
  assert.equal(entry.inlineTopic, 'g0');
  assert.equal(
    archifyData.flowchartCatalog.counts.total,
    archifyData.flowchartCatalog.entries.length,
  );
  const startup = render(DiagramDetail, { id: 'startup-workflow', theme: 'light' });
  assert.match(startup, /<iframe/);
  assert.doesNotMatch(startup, /g0-reader/);
});
