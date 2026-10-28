import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const bundled = await build({
  entryPoints: [
    fileURLToPath(
      new URL('../../src/features/chat/components/DebugIssueReference.tsx', import.meta.url),
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
      name: 'no-network',
      setup(builder) {
        builder.onResolve({ filter: /app\/api\/client$/ }, () => ({
          path: 'http',
          namespace: 'boundary',
        }));
        builder.onLoad({ filter: /.*/, namespace: 'boundary' }, () => ({
          contents: 'export const api = () => { throw new Error("测试禁止网络请求"); };',
        }));
      },
    },
  ],
});
const require = createRequire(import.meta.url);
const module = { exports: {} };
new Function('require', 'module', 'exports', bundled.outputFiles[0].text)(
  require,
  module,
  module.exports,
);
const { DebugIssueReference, DebugIssueReferenceContent } = module.exports;
const { QueryClient, QueryClientProvider } = require('@tanstack/react-query');

test('未点击出处时只渲染标题按钮，不读取记录或展示内部信息', () => {
  const client = new QueryClient();
  try {
    const html = renderToStaticMarkup(
      createElement(
        QueryClientProvider,
        { client },
        createElement(
          DebugIssueReference,
          { id: 'issue', version: 2, label: '取片经验' },
          '取片经验',
        ),
      ),
    );
    assert.match(html, /aria-haspopup="dialog"/);
    assert.match(html, />取片经验<\/button>/);
    assert.doesNotMatch(html, /issue|版本|v2|正在加载|记录内容|href=/);
  } finally {
    client.clear();
  }
});

test('引用内容显示完整事实和原图，隐藏导入编号并转义原文中的脚本', () => {
  const row = {
    id: 'issue',
    version: 2,
    kind: 'debug_issue',
    title: '取片经验',
    payload: {
      origin: 'import',
      problem: '完整正文'.repeat(300),
      recorded_by: '原作者',
      solution: '处理办法',
      verification: '结果记录',
      software_version: '设备软件 v4',
      keywords: ['EXP-099', '取片'],
      original_text: JSON.stringify({
        id: 'EXP-099',
        source: '内部导入文件.xlsx',
        content: '<script>原始文字</script>',
      }),
      images: [{ id: 'image', name: '内部原图名.png' }],
    },
  };
  const html = renderToStaticMarkup(createElement(DebugIssueReferenceContent, { row }));
  assert.ok(html.includes(row.payload.problem));
  for (const value of ['原作者', '处理办法', '结果记录', '设备软件 v4', '查看录入原文'])
    assert.ok(html.includes(value), value);
  assert.match(html, /\/api\/handover\/debug-issues\/issue\/images\/2\/0/);
  assert.match(html, /&lt;script&gt;原始文字&lt;\/script&gt;/);
  assert.doesNotMatch(html, /EXP-099|内部导入文件|内部原图名|<script>|引用版本|修订号/);
});
