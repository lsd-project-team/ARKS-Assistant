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

test('主表只有问题答案关键词，记录信息默认收起', () => {
  storage.clear();
  const html = render({}, row);
  const primary = html.split('<details')[0];
  assert.equal((primary.match(/<label\b/g) || []).length, 3);
  for (const label of ['问题', '答案', '关键词']) assert.ok(primary.includes(label), label);
  for (const label of [
    '标题',
    '适用条件',
    '内容说明',
    '处理方法',
    '结果记录',
    '注意事项',
    '原记录人',
  ])
    assert.ok(!primary.includes('<span>' + label), label);
  assert.equal((primary.match(/<textarea required/g) || []).length, 2);
  assert.match(html, /<summary>记录信息（选填）<\/summary>/);
  assert.ok(html.includes('原记录人') && html.includes('8月25日 10:14'));
});

test('保存三项正文并把可编辑管理字段放入metadata，保留旧事实而不发送来源身份', async () => {
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
  assert.equal(sent[0], '/debug-issues/legacy');
  assert.equal(sent[2], 'PATCH');
  assert.equal(sent[1].version, 7);
  const value = sent[1].payload;
  assert.deepEqual(Object.keys(value).sort(), ['answer', 'keywords', 'metadata', 'question']);
  assert.equal(value.question, payload.problem);
  for (const fact of ['更换密封圈', '检查真空管路', '密封圈破损', '连续取片20次正常'])
    assert.ok(value.answer.includes(fact));
  assert.equal(value.metadata.recorded_by, '原作者');
  assert.equal(value.metadata.recorded_at, '8月25日 10:14');
  assert.equal(value.metadata.resolution_status, 'resolved');
  for (const key of ['original_text', 'reported_by', 'images', 'source_message_id'])
    assert.equal(key in value.metadata, false);
  assert.deepEqual(value.keywords, payload.keywords);
  assert.deepEqual(row, original);
});

test('旧草稿可转为问答保存，提交失败继续保留草稿', async () => {
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
  assert.equal(sent[1].title, payload.problem);
  assert.equal(sent[1].payload.question, payload.problem);
  assert.equal(sent[1].payload.metadata.recorded_by, '原作者');
  assert.equal(storage.get(key), saved);
});
