import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const storage = new Map();
globalThis.localStorage = {
  getItem: (key) => storage.get(key) ?? null,
  removeItem: (key) => storage.delete(key),
};
const environment = { user: { display_name: '当前登录人', username: 'current' }, modal: null };
const bundled = await build({
  entryPoints: [
    fileURLToPath(
      new URL('../../src/features/handover/packages/PackageBuilder.tsx', import.meta.url),
    ),
  ],
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  jsx: 'automatic',
  plugins: [
    {
      name: 'package-boundaries',
      setup(builder) {
        builder.onResolve({ filter: /\/(AuthContext|HandoverModal)$/ }, ({ path }) => ({
          path: path.endsWith('/AuthContext') ? 'auth' : 'modal',
          namespace: 'package-boundary',
        }));
        builder.onLoad({ filter: /.*/, namespace: 'package-boundary' }, ({ path }) => ({
          resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
          contents:
            path === 'auth'
              ? 'export const useAuth = () => ({session: {user: environment.user}});'
              : 'import {createElement} from "react"; export const HandoverModal = (props) => { environment.modal = props; return createElement("form", null, props.children, props.footer); };',
        }));
      },
    },
  ],
});
const bundledModule = { exports: {} };
new Function('require', 'module', 'exports', 'environment', bundled.outputFiles[0].text)(
  createRequire(import.meta.url),
  bundledModule,
  bundledModule.exports,
  environment,
);
const { PackageBuilder } = bundledModule.exports;
const draftKey = 'arks-handover-draft:global:package';
const records = [
  { id: 'issue', title: '调试经验', kind: 'debug_issue', state: 'draft', version: 2 },
  { id: 'source', title: '设备手册', kind: 'source', state: 'confirmed', version: 8 },
  { id: 'archived', title: '归档资料', kind: 'source', state: 'archived', version: 1 },
  { id: 'receipt', title: '旧接收记录', kind: 'receipt', state: 'draft', version: 1 },
];
function render(client, onSaved = () => {}) {
  return renderToStaticMarkup(
    createElement(PackageBuilder, {
      scopeId: 'global',
      client,
      records,
      definitions: {
        kinds: { debug_issue: '问题与经验', source: '资料' },
        states: { draft: '待确认', confirmed: '已确认' },
      },
      onSaved,
      onClose() {},
    }),
  );
}
async function submit() {
  environment.modal.onSubmit({ preventDefault() {} });
  await new Promise(setImmediate);
}

test('生成时使用当前登录人，恢复旧草稿仍保留范围和缺项，并排除无效选择', async () => {
  storage.clear();
  storage.set('arks-handover-actor:global', '以前手填的人');
  const payload = {
    recipient: '接收人',
    scope: '原交接范围',
    gaps: '现场尚未确认',
    record_ids: ['issue', 'archived', 'receipt', 'removed'],
  };
  storage.set(draftKey, JSON.stringify({ title: '原草稿', payload }));
  let sent;
  let saved;
  const html = render(
    {
      send: async (path, body) => {
        sent = { path, body };
        return { id: 'package' };
      },
    },
    (row) => {
      saved = row;
    },
  );
  assert.ok(html.includes('问题与经验'));
  assert.ok(!html.includes('问题与经验 · v2'));
  assert.ok(html.includes('设备手册'));
  assert.ok(!html.includes('v8'));
  assert.ok(!html.includes('整理人'));
  await submit();
  assert.deepEqual(sent, {
    path: '/packages',
    body: {
      title: '原草稿',
      recipient: '接收人',
      scope: '原交接范围\n\n待补充事项：\n现场尚未确认',
      gaps: '',
      record_ids: ['issue'],
      actor: '当前登录人',
    },
  });
  assert.deepEqual(saved, { id: 'package' });
  assert.equal(storage.has(draftKey), false);
});

test('补充信息可留空，提交失败保留草稿，显示名为空时使用登录名', async () => {
  storage.clear();
  environment.user = { display_name: '', username: 'current' };
  const draft = JSON.stringify({ title: '未保存的包', payload: { record_ids: ['issue'] } });
  storage.set(draftKey, draft);
  let body;
  let saved = false;
  render(
    {
      send: async (_path, input) => {
        body = input;
        throw new Error('服务暂不可用');
      },
    },
    () => {
      saved = true;
    },
  );
  await submit();
  assert.equal(body.actor, 'current');
  assert.equal(body.scope, '');
  assert.equal(saved, false);
  assert.equal(storage.get(draftKey), draft);
});
