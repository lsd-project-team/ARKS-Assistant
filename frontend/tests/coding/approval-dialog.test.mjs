import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';

const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', {
  url: 'http://localhost/',
});
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
globalThis.MutationObserver = dom.window.MutationObserver;
globalThis.getComputedStyle = dom.window.getComputedStyle.bind(dom.window);
for (const key of [
  'Event',
  'CustomEvent',
  'KeyboardEvent',
  'MouseEvent',
  'FocusEvent',
  'PointerEvent',
  'HTMLElement',
  'HTMLInputElement',
  'Element',
  'Node',
  'DocumentFragment',
  'DOMRect',
]) {
  if (dom.window[key]) globalThis[key] = dom.window[key];
}
globalThis.requestAnimationFrame = (callback) => setTimeout(callback, 0);
globalThis.cancelAnimationFrame = (id) => clearTimeout(id);

const compiled = await build({
  entryPoints: [
    fileURLToPath(new URL('../../src/features/coding/ApprovalDialog.tsx', import.meta.url)),
  ],
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  jsx: 'automatic',
  plugins: [
    {
      name: 'approvals',
      setup(builder) {
        builder.onResolve({ filter: /useApprovals$/ }, () => ({
          path: 'approvals',
          namespace: 'mock',
        }));
        builder.onLoad({ filter: /.*/, namespace: 'mock' }, () => ({
          contents: `
            export function useApprovals() {
              return { data: { approvals: globalThis.__approvals || [] } };
            }
            export function useDecideApproval() {
              return {
                isPending: false,
                mutate: (vars, options) => {
                  globalThis.__decision = vars;
                  options && options.onSuccess && options.onSuccess();
                },
              };
            }
          `,
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
const { ApprovalDialogHost } = module.exports;

const approval = (overrides = {}) => ({
  id: 'a1',
  kind: 'command',
  command: 'node -e "console.log(1)"',
  cwd: '.',
  timeout: 120,
  status: 'pending',
  created_at: '2026-11-13T00:00:00',
  thread_id: 'thread-1',
  ...overrides,
});

async function mount(root) {
  await act(async () => root.render(createElement(ApprovalDialogHost)));
}

test('审批弹窗展示命令，Enter 允许一次，Esc 拒绝', async () => {
  globalThis.__approvals = [approval()];
  globalThis.__decision = undefined;
  const root = createRoot(document.getElementById('root'));
  try {
    await mount(root);
    assert.match(document.body.textContent, /允许运行这条命令吗/);
    assert.match(document.querySelector('.approval-dialog-command').textContent, /node -e/);

    await act(async () => {
      document
        .querySelector('.approval-dialog')
        .dispatchEvent(new dom.window.KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    });
    assert.deepEqual(globalThis.__decision, { id: 'a1', approved: true, scope: 'once' });

    globalThis.__decision = undefined;
    await act(async () => {
      document.dispatchEvent(new dom.window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    });
    assert.deepEqual(globalThis.__decision, { id: 'a1', approved: false, scope: 'once' });
  } finally {
    await act(async () => root.unmount());
  }
});

test('下拉里的本会话允许只在有对话线程时可选，并显示排队数量', async () => {
  globalThis.__approvals = [approval(), approval({ id: 'a2', cwd: 'src' })];
  globalThis.__decision = undefined;
  const root = createRoot(document.getElementById('root'));
  try {
    await mount(root);
    assert.match(document.body.textContent, /还有 1 条待确认/);

    await act(async () => document.querySelector('.approval-more').click());
    const items = [...document.querySelectorAll('.approval-menu button')];
    assert.equal(items.length, 2);
    assert.equal(items[1].disabled, false);
    await act(async () => items[1].click());
    assert.deepEqual(globalThis.__decision, { id: 'a1', approved: true, scope: 'session' });
  } finally {
    await act(async () => root.unmount());
  }
});

test('没有对话线程的审批只能允许一次', async () => {
  globalThis.__approvals = [approval({ thread_id: '' })];
  const root = createRoot(document.getElementById('root'));
  try {
    await mount(root);
    await act(async () => document.querySelector('.approval-more').click());
    const items = [...document.querySelectorAll('.approval-menu button')];
    assert.equal(items[1].disabled, true);
  } finally {
    await act(async () => root.unmount());
  }
});
