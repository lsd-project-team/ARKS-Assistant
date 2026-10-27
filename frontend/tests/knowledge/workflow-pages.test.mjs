import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { presentationTopics } from '../../src/features/knowledge/data/presentation.ts';
import { archifyData } from '../../src/features/knowledge/data/archifyData.ts';
import { diagramReadings } from '../../src/features/knowledge/data/diagramReading.ts';
import { startupGuide } from '../../src/features/knowledge/reviews/startup.ts';
import { guidedDiagrams } from '../../src/features/knowledge/guidedDiagrams.ts';
import { readFile } from 'node:fs/promises';

const result = await build({
  stdin: {
    contents: "export * from './src/features/knowledge/KnowledgePages.tsx';",
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
const { TopicDetail, DiagramDetail } = module.exports;
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
    assert.match(
      html,
      graph.slug === 'startup-workflow' ? /完整关系图与其他控制入口/ : /深入阅读节点与模块协作/,
    );
    assert.ok(html.includes(graph.nodes[0].label));
    assert.doesNotMatch(
      html,
      /源码依据|查看依据|查看协作依据|evidence-item|source-file|source-method|<pre/,
    );
  }
});

test('启动专题从开机开始，生产放行局部页从启动检查开始，原有七个环节仍可进入', () => {
  const startup = render(TopicDetail, { id: 'startup' });
  assert.match(startup, /startup-reading\/boot\.html/);
  assert.match(startup, /aria-label="逐步阅读"/);
  for (const flow of startupGuide.flows) assert.ok(startup.includes(`id="source-tab-${flow.id}"`));
  const readiness = render(DiagramDetail, {
    id: 'machine-start-readiness-workflow',
    theme: 'light',
  });
  assert.match(readiness, /startup-reading\/production\.html/);
  assert.match(readiness, /完整启动检查关系图/);
  assert.match(readiness, /src="\/archify\/machine-start-readiness-workflow\.html\?/);
});

test('页面用途只说明一次，启动主路径使用逐步阅读，补充区保留后台与停止入口', () => {
  for (const graph of archifyData.graphs) {
    const html = render(DiagramDetail, { id: graph.slug, theme: 'light' });
    assert.equal(html.split(diagramReadings[graph.slug].summary).length - 1, 1);
    assert.doesNotMatch(html, /这张图回答什么/);
  }
  const startup = render(DiagramDetail, { id: 'startup-workflow', theme: 'light' });
  assert.doesNotMatch(startup, /aria-label="业务介绍"/);
  for (const name of ['后台监控与存储', 'Stop 软件停止', '再次点击启动'])
    assert.ok(startup.includes(name));
});

test('新版三张阅读图保留已复核节点与分支，阅读步骤和返回节点均有绑定', async () => {
  for (const [flowId, diagram] of Object.entries(guidedDiagrams)) {
    const file = diagram.path.replace('.html', '.archify.json');
    const spec = JSON.parse(
      await readFile(new URL(`../../../resources/knowledge/flows/${file}`, import.meta.url)),
    );
    const name = file.split('/')[1].replace('.archify.json', '');
    const original = JSON.parse(
      await readFile(
        new URL(
          `../../../resources/knowledge/flows/startup-v3-sample/${name}.workflow.json`,
          import.meta.url,
        ),
      ),
    );
    assert.deepEqual(
      spec.nodes.map(({ id, label, type }) => ({ id, label, type })),
      original.nodes.map(({ id, label, type }) => ({ id, label, type })),
    );
    assert.deepEqual(spec.edges, original.edges);
    const flow = startupGuide.flows.find((item) => item.id === flowId);
    assert.deepEqual(Object.keys(diagram.steps).sort(), flow.steps.map((item) => item.id).sort());
    assert.deepEqual(
      [...new Set(Object.values(diagram.steps).flat())].sort(),
      spec.nodes.map((node) => node.id).sort(),
    );
  }
});
