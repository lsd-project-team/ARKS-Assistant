import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const bundled = await build({
  stdin: {
    contents: `export { MaterialsPanel } from './src/features/handover/overview/DashboardPanels'; export { overviewSummary } from './src/features/handover/overview/overviewData';`,
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
new Function('require', 'module', 'exports', bundled.outputFiles[0].text)(
  createRequire(import.meta.url),
  module,
  module.exports,
);
const { MaterialsPanel, overviewSummary } = module.exports;

function row(id, filename, created_at) {
  return {
    id,
    title: '内部记录名',
    kind: 'source',
    state: 'draft',
    payload: { content: '不展示的正文' },
    version: 2,
    created_by: '上传人',
    original_file: { name: filename },
    created_at,
    updated_at: created_at,
  };
}
function render(records) {
  return renderToStaticMarkup(
    createElement(MaterialsPanel, {
      data: overviewSummary({ records, blocks: {} }),
      definitions: {},
      onOpen() {},
      onNavigate() {},
    }),
  );
}

test('资料卡片复用环形统计、类型筛选和资料分页入口，文件使用实际文件名', () => {
  const html = render([
    row('first', '旧手册.pdf', '2026-10-26T08:00:00Z'),
    row('second', '用户手册.pdf', '2026-10-27T08:00:00Z'),
    row('third', '最新资料.docx', '2026-10-28T08:00:00Z'),
  ]);
  for (const value of [
    '资料文件类型分布',
    'PDF 2 份，点击筛选',
    'Word 1 份，点击筛选',
    '查看全部资料总数',
    '最近资料',
    '下一页资料',
    '查看全部',
  ])
    assert.ok(html.includes(value), value);
  assert.equal((html.match(/aria-label="查看原文件：/g) || []).length, 2);
  assert.ok(html.includes('查看原文件：最新资料.docx'));
  assert.ok(html.includes('查看原文件：用户手册.pdf'));
  assert.doesNotMatch(html, /查看原文件：旧手册|内部记录名|不展示的正文|待确认|v2|资料审核/);
});

test('无资料时显示零值图表和空列表，不生成假文件、假占比或分页', () => {
  const html = render([]);
  assert.match(html, /资料文件类型分布/);
  assert.match(html, /此类型暂无资料/);
  assert.doesNotMatch(html, /NaN|Infinity|查看原文件：|下一页资料|dashboard-ring-segment/);
});
