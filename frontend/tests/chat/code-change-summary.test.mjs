import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';

const require = createRequire(import.meta.url);
const { QueryClient, QueryClientProvider } = require('@tanstack/react-query');
const dom = new JSDOM('<!doctype html><div id="root"></div>');
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const boundary = { calls: [], summary: null, opened: [] };
const compiled = await build({
  entryPoints: [
    fileURLToPath(
      new URL('../../src/features/chat/code_work/CodeChangeSummary.tsx', import.meta.url),
    ),
  ],
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  jsx: 'automatic',
  loader: { '.css': 'empty' },
  plugins: [
    {
      name: 'summary-network',
      setup(builder) {
        builder.onResolve({ filter: /app\/api\/client$/ }, ({ path }) => ({
          path,
          namespace: 'summary-api',
        }));
        builder.onLoad({ filter: /.*/, namespace: 'summary-api' }, () => ({
          loader: 'js',
          contents: 'export const api = (...args) => boundary.api(...args);',
        }));
      },
    },
  ],
});
const module = { exports: {} };
new Function('require', 'module', 'exports', 'boundary', compiled.outputFiles[0].text)(
  require,
  module,
  module.exports,
  boundary,
);
const { CodeChangeSummary } = module.exports;
const files = Array.from({ length: 5 }, (_, index) => ({
  path: `AKRS.ZX2200/Main/File${index}.cs`,
  kind: 'modified',
  version: `v${index}`,
  additions: index + 1,
  deletions: index,
}));
async function until(condition) {
  const deadline = Date.now() + 3000;
  while (!condition()) {
    assert.ok(Date.now() < deadline, '修改摘要未在时限内更新');
    await act(async () => new Promise((resolve) => setTimeout(resolve, 10)));
  }
}
async function mounted(check) {
  boundary.calls = [];
  boundary.opened = [];
  boundary.summary = { exists: true, revision: 3, files, additions: 15, deletions: 10 };
  boundary.api = async (url, options, project) => {
    boundary.calls.push({ url, project });
    return structuredClone(boundary.summary);
  };
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const root = createRoot(document.getElementById('root'));
  async function render(extra = {}) {
    await act(async () =>
      root.render(
        createElement(
          QueryClientProvider,
          { client: cache },
          createElement(CodeChangeSummary, {
            threadId: 'thread-a',
            projectId: 'project-a',
            busy: false,
            refreshKey: 'run-a',
            onOpen: (path) => boundary.opened.push(path),
            ...extra,
          }),
        ),
      ),
    );
  }
  try {
    await render();
    await until(() => document.querySelector('[aria-label="代码修改摘要"]'));
    await check({ cache, render });
  } finally {
    await act(async () => root.unmount());
    cache.clear();
  }
}
async function click(button) {
  await act(async () => button.click());
}

test('默认三项、展开全部、总计和文件点击来自真实摘要数据', async () => {
  await mounted(async () => {
    assert.match(document.querySelector('.code-change-title').textContent, /已修改 5 个文件/);
    assert.equal(
      document.querySelector('.code-change-title .code-change-counts').getAttribute('aria-label'),
      '新增 15 行，删除 10 行',
    );
    assert.equal(document.querySelectorAll('.code-change-files li').length, 3);
    assert.doesNotMatch(document.body.textContent, /File4/);
    const expand = document.querySelector('.code-change-expand');
    assert.match(expand.textContent, /再显示 2 个文件/);
    await click(expand);
    assert.equal(expand.getAttribute('aria-expanded'), 'true');
    assert.equal(document.querySelectorAll('.code-change-files li').length, 5);
    await click(document.querySelectorAll('.code-change-files button')[4]);
    assert.deepEqual(boundary.opened, [files[4].path]);
    await click(document.querySelector('.code-change-heading > button'));
    assert.equal(boundary.opened[1], undefined);
    assert.deepEqual(boundary.calls, [
      { url: '/threads/thread-a/code-work/summary', project: 'project-a' },
    ]);
    await click(expand);
    assert.equal(document.querySelectorAll('.code-change-files li').length, 3);
  });
});

test('撤销后刷新隐藏零修改卡片，避免保留过期统计', async () => {
  await mounted(async ({ cache }) => {
    boundary.summary = { exists: true, revision: 4, files: [], additions: 0, deletions: 0 };
    await act(async () => {
      await cache.invalidateQueries({ queryKey: ['code-work', 'project-a', 'thread-a'] });
    });
    await until(() => !document.querySelector('[aria-label="代码修改摘要"]'));
    assert.doesNotMatch(document.body.textContent, /已修改|File0/);
  });
});

test('切换项目与对话不会显示上一份副本，完成新一轮后重新请求摘要', async () => {
  await mounted(async ({ render }) => {
    let resolve;
    boundary.api = (url, options, project) => {
      boundary.calls.push({ url, project });
      return new Promise((done) => {
        resolve = done;
      });
    };
    await render({ threadId: 'thread-b', projectId: 'project-b', refreshKey: 'run-b' });
    assert.equal(document.querySelector('[aria-label="代码修改摘要"]'), null);
    await act(async () =>
      resolve({
        exists: true,
        revision: 1,
        files: [{ ...files[0], path: 'AKRS.ZX2200/Other.cs' }],
        additions: 1,
        deletions: 0,
      }),
    );
    await until(() => document.querySelector('.code-change-files button'));
    assert.match(document.body.textContent, /Other.cs/);
    assert.doesNotMatch(document.body.textContent, /File0/);
    assert.deepEqual(boundary.calls.at(-1), {
      url: '/threads/thread-b/code-work/summary',
      project: 'project-b',
    });
    await render({ threadId: 'thread-b', projectId: 'project-b', refreshKey: 'run-b:completed' });
    assert.equal(boundary.calls.length, 3);
    await act(async () =>
      resolve({ exists: true, revision: 2, files: [], additions: 0, deletions: 0 }),
    );
  });
});
