import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { QueryClient } from '@tanstack/react-query';

const environment = { row: undefined, queries: [], QueryClient, createElement };
const bundled = await build({
  entryPoints: [
    fileURLToPath(new URL('../../src/features/handover/records/RecordView.tsx', import.meta.url)),
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
      name: 'query-boundary',
      setup(builder) {
        builder.onResolve({ filter: /\/PdfOriginal$/ }, () => ({
          path: 'pdf',
          namespace: 'pdf-boundary',
        }));
        builder.onLoad({ filter: /.*/, namespace: 'pdf-boundary' }, () => ({
          contents:
            'export const PdfOriginal = ({source}) => environment.createElement("div", {"data-pdf-original":source});',
        }));
        builder.onResolve({ filter: /\/HandoverModal$/ }, () => ({
          path: 'modal',
          namespace: 'modal-boundary',
        }));
        builder.onLoad({ filter: /.*/, namespace: 'modal-boundary' }, () => ({
          contents:
            'export const HandoverModal = ({title,description,children,footer}) => environment.createElement("section", null, title,description,children,footer);',
        }));
        builder.onResolve({ filter: /^@tanstack\/react-query$/ }, () => ({
          path: 'query',
          namespace: 'boundary',
        }));
        builder.onLoad({ filter: /.*/, namespace: 'boundary' }, () => ({
          contents:
            'export const QueryClient = environment.QueryClient; export const useQuery = options => { environment.queries.push(options); return {data: options.queryKey[0] === "handover-record" ? environment.row : [], refetch:async()=>({})}; };',
        }));
      },
    },
  ],
});
const module = { exports: {} };
new Function('require', 'module', 'exports', 'environment', bundled.outputFiles[0].text)(
  createRequire(import.meta.url),
  module,
  module.exports,
  environment,
);
const { RecordView } = module.exports;
const base = {
  id: 'original-id',
  kind: 'source',
  title: '原始手册.pdf',
  version: 8,
  state: 'needs_review',
  payload: { content: '旧的提取正文不可作为原文件展示', notes: '无关的来源说明' },
  created_by: '上传用户',
  created_at: '2026-10-28T08:00:00Z',
  updated_at: '2026-10-28T09:00:00Z',
  original_file: { name: '原始手册.pdf', previewable: true },
};
function render(row) {
  environment.row = row;
  environment.queries = [];
  return renderToStaticMarkup(
    createElement(RecordView, {
      scopeId: 'global',
      identifier: row.id,
      client: {},
      definitions: {},
      records: [row],
      canReview: true,
      reviewOnly: true,
      actor: '不应覆盖上传人',
      onActor() {},
      onClose() {},
      onOpen() {},
      onEdit() {},
      onChanged() {},
    }),
  );
}
test('管理员从审核入口打开资料也直接看原文件，不出现审核、换版、解析正文和版本控件', () => {
  const html = render(base);
  assert.ok(html.includes('data-pdf-original="/api/handover/sources/original-id/original"'));
  assert.ok(html.includes('上传用户'));
  assert.ok(html.includes('下载原文件'));
  for (const obsolete of [
    '旧的提取正文',
    '无关的来源说明',
    '待复核',
    '重新复核',
    '确认',
    '更新资料',
    '比对当前版本',
    'v8',
    '不应覆盖上传人',
  ])
    assert.ok(!html.includes(obsolete), obsolete);
  assert.equal(
    environment.queries.find((query) => query.queryKey[0] === 'handover-history').enabled,
    false,
  );
});
test('不支持预览的文件只提供原文件下载，不显示提取正文', () => {
  const html = render({
    ...base,
    title: 'Word.docx',
    original_file: { name: 'Word.docx', previewable: false },
  });
  assert.ok(!html.includes('<iframe'));
  assert.ok(!html.includes('旧的提取正文'));
  assert.ok(html.includes('此格式暂不支持在线预览'));
});
test('无原附件的旧文本仍可查阅，原文转义显示且不进入新的录入流程', () => {
  const html = render({
    ...base,
    original_file: null,
    payload: { content: '旧原文\n<script>原始字符</script>' },
  });
  assert.ok(html.includes('这条历史资料没有附件'));
  assert.ok(html.includes('&lt;script&gt;原始字符&lt;/script&gt;'));
  assert.ok(!html.includes('输入文本'));
});
