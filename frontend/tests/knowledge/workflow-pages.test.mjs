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
    assert.match(html, /深入阅读节点与模块协作/);
    assert.ok(html.includes(graph.nodes[0].label));
    assert.doesNotMatch(
      html,
      /源码依据|查看依据|查看协作依据|evidence-item|source-file|source-method|<pre/,
    );
  }
});
