import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';

const dom = new JSDOM('<div id="root"></div>', { url: 'http://localhost/' });
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.localStorage = dom.window.localStorage;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
globalThis.ResizeObserver = class {
  observe() {}
  disconnect() {}
};
const { useWorkspace } = await import('../../src/app/state/store.ts');
const environment = {
  store: useWorkspace,
  requests: [],
  closes: 0,
  notices: [],
  cleared: [],
  refreshed: [],
};
const compiled = await build({
  stdin: {
    contents:
      "export { ProjectMenu } from './src/features/projects/components/ProjectMenu'; export { ProjectDeleteDialog } from './src/features/projects/components/ProjectDeleteDialog';",
    resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
    loader: 'tsx',
  },
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  external: ['react'],
  jsx: 'automatic',
  plugins: [
    {
      name: 'boundaries',
      setup(builder) {
        builder.onResolve(
          { filter: /(state\/store|api\/client|utils\/toasts|lib\/projectCache|ui\/ui)$/ },
          ({ path }) => ({ path, namespace: 'boundary' }),
        );
        builder.onLoad({ filter: /.*/, namespace: 'boundary' }, ({ path }) => ({
          loader: 'js',
          contents: path.endsWith('store')
            ? 'export const useWorkspace = environment.store;'
            : path.endsWith('client')
              ? 'export const jsonBody = JSON.stringify; export const api = (path, options) => { environment.requests.push({path, options}); return environment.response ? environment.response() : Promise.resolve({ok:true}); };'
              : path.endsWith('toasts')
                ? 'export const toast = message => environment.notices.push(message);'
                : path.endsWith('projectCache')
                  ? 'export const projectCache = id => ({ clear: () => environment.cleared.push(id) }); export const invalidateProjectCaches = groups => { environment.refreshed.push(groups); return Promise.resolve(); };'
                  : 'import {createElement as h} from "react"; export const Button = props => h("button", props); export const ErrorText = ({error}) => error ? h("div", {role:"alert"}, error.message) : null; export const Modal = ({title,children,onClose}) => h("div", {role:"dialog", onKeyDown: e => e.key === "Escape" && onClose()}, h("h2",null,title), h("button", {"aria-label":"关闭",onClick:onClose}, "关闭"),children);',
        }));
      },
    },
  ],
});
const module = { exports: {} };
new Function('require', 'module', 'exports', 'environment', compiled.outputFiles[0].text)(
  createRequire(import.meta.url),
  module,
  module.exports,
  environment,
);
const { ProjectMenu, ProjectDeleteDialog } = module.exports;
const project = { id: 'A', name: '项目 A', state: 'active', pinned_order: null };
const button = (name) =>
  [...document.querySelectorAll('button')].find((el) => el.textContent === name);
async function mounted(verify, Component = ProjectDeleteDialog) {
  localStorage.clear();
  useWorkspace.setState(useWorkspace.getInitialState(), true);
  useWorkspace.getState().initializeProject('A');
  useWorkspace.getState().setDraft('保留草稿');
  Object.assign(environment, {
    requests: [],
    closes: 0,
    notices: [],
    cleared: [],
    refreshed: [],
    response: undefined,
  });
  const root = createRoot(document.getElementById('root'));
  try {
    await act(async () =>
      root.render(
        createElement(Component, {
          project,
          onClose: () => environment.closes++,
          onEdit: () => {},
        }),
      ),
    );
    await verify();
  } finally {
    await act(async () => root.unmount());
  }
}

test('项目菜单能打开删除弹窗，取消不发请求且保留草稿', async () => {
  await mounted(async () => {
    await act(async () => document.querySelector('[aria-label="项目操作：项目 A"]').click());
    await act(async () => button('删除项目').click());
    assert.ok(document.querySelector('[role="dialog"]'));
    assert.equal(document.querySelector('input[type="radio"]').checked, true);
    await act(async () => button('取消').click());
    assert.equal(document.querySelector('[role="dialog"]'), null);
    assert.deepEqual(environment.requests, []);
    assert.equal(useWorkspace.getState().drafts['new:A'].content, '保留草稿');
  }, ProjectMenu);
});

for (const disposition of ['independent', 'trash']) {
  test(`确认删除按选择调用 DELETE，并完成状态和缓存更新：${disposition}`, async () => {
    await mounted(async () => {
      if (disposition === 'trash')
        await act(async () => document.querySelectorAll('input[type="radio"]')[1].click());
      await act(async () => button('删除项目').click());
      assert.deepEqual(environment.requests, [
        { path: `/projects/A?disposition=${disposition}`, options: { method: 'DELETE' } },
      ]);
      assert.equal(useWorkspace.getState().projectId, 'independent');
      assert.equal(useWorkspace.getState().drafts['new:independent'].content, '保留草稿');
      assert.deepEqual(environment.cleared, ['A']);
      assert.ok(environment.refreshed[0].includes('threads'));
      assert.equal(environment.closes, 1);
    });
  });
}

test('失败显示原错误且不改变项目或草稿，用户可以重试', async () => {
  await mounted(async () => {
    environment.response = () => Promise.reject(new Error('项目中有等待发送的问题，请先处理队列'));
    await act(async () => button('删除项目').click());
    assert.match(document.querySelector('[role="alert"]').textContent, /先处理队列/);
    assert.equal(useWorkspace.getState().projectId, 'A');
    assert.equal(useWorkspace.getState().drafts['new:A'].content, '保留草稿');
    assert.deepEqual(environment.cleared, []);
    assert.equal(environment.closes, 0);
    environment.response = undefined;
    await act(async () => button('删除项目').click());
    assert.equal(environment.requests.length, 2);
    assert.equal(environment.closes, 1);
  });
});

test('请求中重复点击只提交一次，关闭操作不能提前结束删除流程', async () => {
  await mounted(async () => {
    let complete;
    environment.response = () =>
      new Promise((resolve) => {
        complete = resolve;
      });
    const confirm = button('删除项目');
    await act(async () => {
      confirm.click();
      confirm.click();
    });
    assert.equal(environment.requests.length, 1);
    assert.equal(button('正在删除…').disabled, true);
    await act(async () => document.querySelector('[aria-label="关闭"]').click());
    assert.equal(environment.closes, 0);
    assert.equal(useWorkspace.getState().projectId, 'A');
    await act(async () => complete({ ok: true }));
    assert.equal(environment.closes, 1);
  });
});
