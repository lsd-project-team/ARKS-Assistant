import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const require = createRequire(import.meta.url);
const compiled = await build({
  stdin: {
    contents: `export { DiffLines } from './src/features/chat/workspace_work/DiffLines';`,
    resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
    loader: 'tsx',
  },
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  jsx: 'automatic',
  loader: { '.css': 'empty' },
});
const module = { exports: {} };
new Function('module', 'exports', 'require', compiled.outputFiles[0].text)(
  module,
  module.exports,
  require,
);
const { DiffLines } = module.exports;

test('工作区差异按行分类渲染并保留内容', () => {
  const diff = ['--- a/src/a.cs', '+++ b/src/a.cs', '@@ -1 +1 @@', '-class A { }', '+class B { }', ' tail'].join(
    '\n',
  );
  const html = renderToStaticMarkup(createElement(DiffLines, { diff }));
  assert.match(html, /work-diff-line meta/);
  assert.match(html, /work-diff-line hunk/);
  assert.match(html, /work-diff-line del[^>]*>-class A \{ \}/);
  assert.match(html, /work-diff-line add[^>]*>\+class B \{ \}/);
  assert.match(html, /work-diff-line context[^>]*> tail/);
});

test('空差异显示明确占位', () => {
  const html = renderToStaticMarkup(createElement(DiffLines, { diff: '' }));
  assert.match(html, /没有差异/);
});
