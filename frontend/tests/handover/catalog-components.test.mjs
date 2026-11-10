import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const bundled = await build({
  stdin: {
    contents:
      "export { MaterialsPage } from './src/features/handover/materials/MaterialsPage'; export { PackageList } from './src/features/handover/packages/PackageList';",
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
const bundledModule = { exports: {} };
new Function('require', 'module', 'exports', bundled.outputFiles[0].text)(
  createRequire(import.meta.url),
  bundledModule,
  bundledModule.exports,
);
const { MaterialsPage, PackageList } = bundledModule.exports;
const definitions = {
  states: {
    draft: '待确认',
    confirmed: '已确认',
    needs_review: '待复核',
    rejected: '已拒绝',
    archived: '已归档',
  },
};
function row(id, kind, payload = {}, state = 'draft') {
  return {
    id,
    kind,
    title: id,
    payload,
    state,
    version: 2,
    created_at: '2026-10-15T08:00:00Z',
    updated_at: '2026-10-16T08:00:00Z',
  };
}
function render(Component, rows, archived = false) {
  return renderToStaticMarkup(
    createElement(Component, {
      rows,
      definitions,
      archived,
      actor: '测试用户',
      client: {},
      onActor() {},
      onOpen() {},
      onChanged() {},
    }),
  );
}

test('资料列表只显示原文件、真实上传人和上传时间，不显示正文、版本或审核状态', () => {
  const source = {
    ...row('用户手册', 'source', {
      format: 'pdf',
      content: '不展示的已提取正文',
      provider: '非上传人',
    }),
    created_by: '贺强',
    original_file: { name: '原始手册.pdf', previewable: true },
  };
  const legacy = {
    ...row('旧记录', 'source', { content: '不展示的资料正文' }),
    created_by: '李少达',
  };
  const html = render(MaterialsPage, [
    source,
    legacy,
    row('非资料', 'task'),
    row('已移出的文件', 'source', {}, 'archived'),
  ]);
  assert.equal((html.match(/aria-label="查看原文件：/g) || []).length, 2);
  for (const value of ['原始手册.pdf', '旧记录', '李少达', '贺强', '搜索资料'])
    assert.ok(html.includes(value), value);
  for (const obsolete of [
    '不展示的已提取正文',
    '不展示的资料正文',
    '非上传人',
    '非资料',
    '已移出的文件',
    'v2',
    '待确认',
    '资料类型',
    '全部类型',
    '全部状态',
    '记录状态',
    '文件资料',
    '文本记录',
    '源码资料',
  ])
    assert.ok(!html.includes(obsolete), obsolete);
});

test('交接包卡片保留打开与归档入口，收录数按固定版本去重，不伪造接收对象', () => {
  const record = row('交接包 A', 'package', {
    records: [
      { record_id: 'a', version: 1 },
      { record_id: 'a', version: 1 },
      { record_id: 'a', version: 2 },
    ],
  });
  const original = structuredClone(record);
  const html = render(PackageList, [record]);
  assert.ok(html.includes('aria-label="查看记录：交接包 A"'));
  assert.ok(html.includes('aria-label="归档交接包：交接包 A"'));
  assert.ok(html.includes('2 条记录'));
  assert.ok(!html.includes('v2'));
  assert.ok(!html.includes('接收：'));
  assert.deepEqual(record, original);
  const archived = render(PackageList, [{ ...record, state: 'archived' }], true);
  assert.ok(archived.includes('aria-label="恢复交接包：交接包 A"'));
  assert.ok(archived.includes('未确认'));
});

test('资料与交接包空列表只显示简洁状态，不带重复分组与引导说明', () => {
  for (const Component of [MaterialsPage, PackageList]) {
    const html = render(Component, []);
    assert.ok(html.includes(Component === MaterialsPage ? '暂无资料' : '暂无记录'));
    assert.ok(!html.includes('handover-group'));
    assert.ok(!html.includes('保留生成时的记录版本'));
  }
});
