import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';

const dom = new JSDOM('<div id="root"></div>');
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let copied;
Object.defineProperty(globalThis, 'navigator', {
  configurable: true,
  value: {
    clipboard: {
      writeText: async (text) => {
        copied = text;
      },
    },
  },
});
const compiled = await build({
  entryPoints: [
    fileURLToPath(new URL('../../src/shared/ui/markdown/CodeBlock.tsx', import.meta.url)),
  ],
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  jsx: 'automatic',
  plugins: [
    {
      name: 'toast',
      setup(builder) {
        builder.onResolve({ filter: /utils\/toasts$/ }, () => ({
          path: 'toast',
          namespace: 'mock',
        }));
        builder.onLoad({ filter: /.*/, namespace: 'mock' }, () => ({
          contents: 'export const toast = () => {};',
          loader: 'js',
        }));
      },
    },
  ],
});
const module = { exports: {} };
new Function('require', 'module', 'exports', compiled.outputFiles[0].text)(
  createRequire(import.meta.url),
  module,
  module.exports,
);
const { CodeBlock } = module.exports;

test('超长代码复制保留缩进、CRLF 和末尾空行；流式追加保持展开及换行状态', async () => {
  const root = createRoot(document.getElementById('root'));
  const raw = '  value = "中文";\r\n'.repeat(1000) + '\r\n';
  const render = (content) =>
    createElement(CodeBlock, {
      rawContent: content,
      streaming: true,
      children: createElement('code', { className: 'language-typescript' }, content),
    });
  try {
    await act(async () => root.render(render(raw)));
    await act(async () => document.querySelector('[aria-label="复制代码"]').click());
    assert.equal(copied, raw);
    await act(async () => document.querySelector('.code-expand').click());
    await act(async () => document.querySelector('[aria-label="代码自动换行"]').click());
    await act(async () => root.render(render(raw + 'tail')));
    assert.equal(document.querySelector('.code-expand').getAttribute('aria-expanded'), 'true');
    assert.equal(
      document.querySelector('[aria-label="代码自动换行"]').getAttribute('aria-pressed'),
      'true',
    );
    assert.match(document.querySelector('pre').textContent, /tail$/);
  } finally {
    await act(async () => root.unmount());
    dom.window.close();
  }
});
