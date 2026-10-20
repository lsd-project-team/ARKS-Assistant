import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { readFile } from 'node:fs/promises';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const require = createRequire(import.meta.url);
const result = await build({
  entryPoints: [
    fileURLToPath(
      new URL('../../src/features/chat/components/AnswerMarkdown.tsx', import.meta.url),
    ),
  ],
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  external: [
    'react',
    'react/*',
    'react-dom',
    'react-dom/*',
    '@tanstack/react-query',
    'lucide-react',
    '@radix-ui/*',
    '@pierre/diffs',
    'clsx',
    'tailwind-merge',
    'zustand',
  ],
  jsx: 'automatic',
  plugins: [
    {
      name: 'boundaries',
      setup(builder) {
        builder.onResolve(
          {
            filter:
              /(state\/store|api\/client|hooks\/useSourceCitation|components\/(MaterialViewer|HandoverMaterialViewer|SelectionPreview))$/,
          },
          (args) => ({ path: args.path, namespace: 'boundary' }),
        );
        builder.onLoad({ filter: /.*/, namespace: 'boundary' }, ({ path }) => ({
          loader: 'js',
          contents: path.endsWith('store')
            ? 'export const useWorkspace = selector => selector({projectId:"p"}); useWorkspace.getState = () => ({projectId:"p"});'
            : path.endsWith('client')
              ? 'export const api = () => {throw new Error("测试禁止网络")};'
              : path.endsWith('useSourceCitation')
                ? 'export const useSourceCitation = () => () => false; export const readCitationSource = () => { throw new Error("测试禁止网络"); };'
                : 'export const MaterialViewer = () => null; export const HandoverMaterialViewer = () => null; export const SelectionPreview = () => null;',
        }));
      },
    },
  ],
});
const module = { exports: {} };
new Function('require', 'module', 'exports', result.outputFiles[0].text)(
  require,
  module,
  module.exports,
);
const { QueryClient, QueryClientProvider } = require('@tanstack/react-query');
const render = (content, evidence = []) => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(['source-evidence', 'p', 'r'], { source_evidence: evidence });
  try {
    return renderToStaticMarkup(
      createElement(
        QueryClientProvider,
        { client },
        createElement(module.exports.AnswerMarkdown, { content, runId: 'r' }),
      ),
    );
  } finally {
    client.clear();
  }
};
const fixture = await readFile(new URL('./fixtures/rich-content.json', import.meta.url), 'utf8');

test('真实助手 Renderer 将所有白名单块和 Markdown 交错渲染', () => {
  const html = render('# 回答标题\n\n```rich-content\n' + fixture + '\n```\n\n结束说明。');
  for (const text of [
    '回答标题',
    '功能入口',
    'rich-overview-grid',
    'rich-step-number',
    '状态对照',
    '调用关系',
    '补充说明',
    '结束说明',
  ])
    assert.ok(html.includes(text), text);
  assert.match(html, /Program.cs:2/);
  assert.doesNotMatch(html, /"version"|"type":"step_flow"/);
});
test('旧 Markdown 的表格、嵌套列表、任务项、波浪参数和代码不回归', () => {
  const html = render(
    '## 标题\n\n20~30g，280~300\n\n- 第一层\n  - 第二层\n\n- [x] 完成\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n```js\nconst a = 1;\n```',
  );
  for (const text of ['<h2>', '第二层', 'type="checkbox"', '<table>', 'const a = 1', '20~30g'])
    assert.ok(html.includes(text), text);
  assert.doesNotMatch(html, /<del>/);
});
test('结构化 text 复用安全 Markdown，任意 HTML、脚本链接不能执行', () => {
  const html = render(
    '```rich-content\n' +
      JSON.stringify({
        version: 1,
        blocks: [
          {
            id: 'x',
            type: 'text',
            content: '<script>alert(1)</script>\n\n[危险](javascript:alert(1))',
          },
        ],
      }) +
      '\n```',
  );
  assert.doesNotMatch(html, /<script>|href="javascript:/);
  assert.ok(html.includes('危险'));
});
test('未知组件降级不丢正文，不允许任意组件加载', () => {
  const html = render(
    '前文\n\n```rich-content\n{"version":1,"blocks":[{"id":"x","type":"remote_component"}]}\n```\n\n后文',
  );
  assert.match(html, /未知内容块类型/);
  assert.match(html, /前文/);
  assert.match(html, /后文/);
  assert.match(html, /原始内容/);
});

test('格式损坏的业务引用不能降为任意外部协议链接', () => {
  const html = render('[坏引用](source:not-a-location)');
  assert.match(html, /引用格式无效/);
  assert.doesNotMatch(html, /href="source:/);
});
