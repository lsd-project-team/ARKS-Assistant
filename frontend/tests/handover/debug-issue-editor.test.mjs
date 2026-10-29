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
const environment = {};
const bundle = await build({
  entryPoints: [
    fileURLToPath(
      new URL('../../src/features/handover/debug_issues/DebugIssueEditor.tsx', import.meta.url),
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
      name: 'editor-modal-boundary',
      setup(builder) {
        builder.onResolve({ filter: /\/HandoverModal$/ }, () => ({
          path: 'modal',
          namespace: 'boundary',
        }));
        builder.onLoad({ filter: /.*/, namespace: 'boundary' }, () => ({
          resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
          contents:
            'import {createElement} from "react"; export function HandoverModal(props) { environment.modal = props; return createElement("form", null, props.children, props.footer); }',
        }));
      },
    },
  ],
});
const module = { exports: {} };
new Function('require', 'module', 'exports', 'environment', bundle.outputFiles[0].text)(
  createRequire(import.meta.url),
  module,
  module.exports,
  environment,
);
const { DebugIssueEditor } = module.exports;
const payload = {
  record_type: 'problem',
  resolution_status: 'resolved',
  problem: 'E901 真空报警',
  solution: '更换密封圈',
  occurred_on: '8月24日',
  recorded_by: '原作者',
  recorded_at: '8月25日 10:14',
  conditions: 'S1 加热时取片',
  environment: '离线环境\n配方 A',
  device: 'ZX2200 HS',
  software_version: '2.1.0',
  module: 'S1 取片',
  investigation: '检查真空管路',
  cause: '密封圈破损',
  verification: '连续取片20次正常',
  notes: '保留原有说明',
  keywords: ['E901', '真空', '取片'],
};
const row = {
  id: 'legacy',
  title: '旧记录',
  kind: 'debug_issue',
  version: 7,
  payload: {
    ...payload,
    reported_by: '实际录入人',
    original_text: '原始描述',
    images: [{ id: 'original-image' }],
  },
};
function render(client = {}, record) {
  return renderToStaticMarkup(
    createElement(DebugIssueEditor, { client, row: record, onSaved() {}, onClose() {} }),
  );
}
async function submit() {
  environment.modal.onSubmit({ preventDefault() {} });
  await new Promise(setImmediate);
}

test('主表仅有五项，补充信息默认收起；已解决时处理办法必填，其他类型不显示处理状态', () => {
  storage.clear();
  const html = render({}, row);
  const primary = html.split('<details')[0];
  assert.equal((primary.match(/<label\b/g) || []).length, 5);
  for (const label of ['记录标题', '记录类型', '处理状态', '记录内容', '处理办法'])
    assert.ok(primary.includes(label), label);
  assert.match(primary, /<textarea required=""[^>]*>更换密封圈<\/textarea>/);
  assert.match(
    html,
    /<details class="debug-issue-additional"><summary>补充信息（选填）<\/summary>/,
  );
  for (const label of [
    '发生条件',
    '设备与环境',
    '事项日期',
    '原记录人',
    '原记录时间',
    '处理经过',
    '问题原因',
    '关键词',
  ]) {
    assert.ok(!primary.includes(label + '</span>'), label);
    assert.ok(html.includes(label), label);
  }
  const experience = render(
    {},
    { ...row, payload: { ...payload, record_type: 'experience', resolution_status: 'recorded' } },
  ).split('<details')[0];
  assert.ok(!experience.includes('处理状态'));
  assert.match(experience, /<textarea(?! required)[^>]*>更换密封圈<\/textarea>/);
});

test('补充区未展开也完整提交旧字段，不改写记录人、日期、条件与关键词，内部来源由服务端保留', async () => {
  storage.clear();
  const original = structuredClone(row);
  let sent;
  render(
    {
      send: async (...args) => {
        sent = args;
        return row;
      },
    },
    row,
  );
  await submit();
  assert.deepEqual(sent, [
    '/debug-issues/legacy',
    { title: '旧记录', version: 7, payload },
    'PATCH',
  ]);
  assert.deepEqual(row, original);
});

test('旧草稿恢复后隐藏字段继续提交，提交失败不清空草稿', async () => {
  storage.clear();
  const key = 'arks-handover-draft:global:new:debug_issue';
  const draft = {
    title: '未保存的记录',
    payload: { ...payload, keywords_text: 'E901，真空，取片' },
  };
  const saved = JSON.stringify(draft);
  storage.set(key, saved);
  let sent;
  const html = render({
    send: async (...args) => {
      sent = args;
      throw new Error('暂时无法保存');
    },
  });
  assert.ok(html.includes('已恢复未保存的记录'));
  await submit();
  assert.deepEqual(sent[1], { title: draft.title, version: undefined, payload });
  assert.equal(storage.get(key), saved);
});
