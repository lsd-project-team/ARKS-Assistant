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
  'NodeFilter',
  'TreeWalker',
  'Document',
  'DocumentFragment',
  'DOMRect',
]) {
  if (dom.window[key]) globalThis[key] = dom.window[key];
}
dom.window.confirm = () => true;

const compiled = await build({
  entryPoints: [
    fileURLToPath(new URL('../../src/features/coding/PermissionMenu.tsx', import.meta.url)),
  ],
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  jsx: 'automatic',
  plugins: [
    {
      name: 'permission-mocks',
      setup(builder) {
        builder.onResolve({ filter: /@tanstack\/react-query$/ }, () => ({
          path: 'react-query',
          namespace: 'mock',
        }));
        builder.onResolve({ filter: /api\/client$/ }, () => ({ path: 'api', namespace: 'mock' }));
        builder.onResolve({ filter: /state\/store$/ }, () => ({ path: 'store', namespace: 'mock' }));
        builder.onResolve({ filter: /auth\/AuthContext$/ }, () => ({
          path: 'auth',
          namespace: 'mock',
        }));
        builder.onLoad({ filter: /.*/, namespace: 'mock' }, (args) => {
          if (args.path === 'react-query') {
            return {
              loader: 'js',
              contents: `
                export function useQuery() {
                  return { data: globalThis.__settings, error: null, isPending: false };
                }
                export function useMutation(options) {
                  return {
                    isPending: false,
                    mutate: (body) => {
                      globalThis.__saved = body;
                      options && options.onSuccess && options.onSuccess();
                    },
                  };
                }
                export function useQueryClient() {
                  return {
                    cancelQueries: async () => {},
                    getQueryData: () => globalThis.__settings,
                    setQueryData: () => {},
                    invalidateQueries: () => {},
                  };
                }
              `,
            };
          }
          if (args.path === 'api') {
            return {
              loader: 'js',
              contents: `
                export const api = async () => globalThis.__settings;
                export const jsonBody = (value) => JSON.stringify(value);
              `,
            };
          }
          if (args.path === 'store') {
            return {
              loader: 'js',
              contents: `
                export const useWorkspace = (selector) => selector({ projectId: 'p1' });
              `,
            };
          }
          return {
            loader: 'js',
            contents: `
              export const useAuth = () => ({
                session: { user: { role: globalThis.__admin ? 'admin' : 'user' } },
              });
            `,
          };
        });
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
const { PermissionMenu } = module.exports;

async function mount(root, inline = false) {
  await act(async () => root.render(createElement(PermissionMenu, { inline })));
}

test('切换完全权限先弹应用内确认，确认后才提交', async () => {
  globalThis.__admin = true;
  globalThis.__settings = { permission: 'workspace-write', writable: true, enabled: true };
  globalThis.__saved = undefined;
  const root = createRoot(document.getElementById('root'));
  try {
    await mount(root);
    const chip = document.querySelector('.permission-chip');
    assert.match(chip.textContent, /工作区内修改/);

    await act(async () => chip.click());
    const items = [...document.querySelectorAll('.permission-popover [role="menuitemradio"]')];
    assert.equal(items.length, 3);
    assert.equal(items[1].getAttribute('aria-checked'), 'true');

    await act(async () => items[2].click());
    assert.equal(globalThis.__saved, undefined);
    assert.match(document.querySelector('.permission-confirm').textContent, /切换到完全权限/);
    assert.match(document.querySelector('.permission-confirm').textContent, /危险命令仍会被拒绝/);

    await act(async () => document.querySelector('.permission-confirm .primary').click());
    assert.deepEqual(globalThis.__saved, { permission: 'full-access' });
  } finally {
    await act(async () => root.unmount());
  }
});

test('取消确认不会提交权限变更', async () => {
  globalThis.__settings = { permission: 'workspace-write', writable: true, enabled: true };
  globalThis.__saved = undefined;
  const root = createRoot(document.getElementById('root'));
  try {
    await mount(root);
    await act(async () => document.querySelector('.permission-chip').click());
    const items = [...document.querySelectorAll('.permission-popover [role="menuitemradio"]')];
    await act(async () => items[2].click());
    assert.ok(document.querySelector('.permission-confirm'));
    await act(async () => document.querySelector('.permission-confirm .button').click());
    assert.equal(globalThis.__saved, undefined);
    assert.equal(document.querySelector('.permission-confirm'), null);
  } finally {
    await act(async () => root.unmount());
  }
});

test('项目成员也能打开菜单并切换档位', async () => {
  globalThis.__admin = false;
  globalThis.__settings = { permission: 'read-only', writable: false, enabled: false };
  globalThis.__saved = undefined;
  const root = createRoot(document.getElementById('root'));
  try {
    await mount(root);
    const chip = document.querySelector('.permission-chip');
    assert.equal(chip.disabled, false);
    assert.match(chip.textContent, /仅可查看/);
    await act(async () => chip.click());
    const items = [...document.querySelectorAll('.permission-popover [role="menuitemradio"]')];
    assert.equal(items.length, 3);
    await act(async () => items[1].click());
    assert.deepEqual(globalThis.__saved, { permission: 'workspace-write' });
  } finally {
    await act(async () => root.unmount());
  }
});

test('内联三档可切换，只读目录切到工作区会同时启用编码', async () => {
  globalThis.__admin = true;
  globalThis.__settings = {
    permission: 'read-only',
    writable: false,
    readonly: true,
    enabled: false,
  };
  globalThis.__saved = undefined;
  const root = createRoot(document.getElementById('root'));
  try {
    await mount(root, true);
    const buttons = [...document.querySelectorAll('.permission-inline button')];
    assert.equal(buttons.length, 3);
    assert.equal(buttons[0].getAttribute('aria-checked'), 'true');

    await act(async () => buttons[1].click());
    assert.equal(globalThis.__saved, undefined);
    assert.match(document.querySelector('.permission-confirm').textContent, /启用编码/);
    await act(async () => document.querySelector('.permission-confirm .primary').click());
    assert.deepEqual(globalThis.__saved, { permission: 'workspace-write', enabled: true });
  } finally {
    await act(async () => root.unmount());
  }
});
