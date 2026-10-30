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
  loader: { '.css': 'empty' },
  plugins: [
    {
      name: 'boundaries',
      setup(builder) {
        builder.onResolve(
          {
            filter:
              /(state\/store|api\/client|hooks\/useSourceCitation|components\/(HandoverMaterialViewer|SelectionPreview))$/,
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
                : 'export const HandoverMaterialViewer = () => null; export const SelectionPreview = () => null;',
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
const render = (content, evidence = [], streaming = false) => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(['source-evidence', 'p', 'r'], { source_evidence: evidence });
  try {
    return renderToStaticMarkup(
      createElement(
        QueryClientProvider,
        { client },
        createElement(module.exports.AnswerMarkdown, { content, runId: 'r', streaming }),
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

test('AI 自主选择的长段落、强调、来源段落和展示文字均保留', () => {
  const paragraph = 'Main方法体为空，没有后续动作。'.repeat(30);
  const html = render(
    `**${paragraph}**\n\n来源：[**试验记录** · v4](debug-issue:trial/4)\n\n本次试验的原图如下：\n\n（3张原图随上述引用直接展示）`,
  );
  assert.ok(html.includes(`<strong>${paragraph}</strong>`));
  assert.match(html, /来源：<button[^>]*><strong>试验记录<\/strong> · v4<\/button>/);
  assert.match(html, /<p>本次试验的原图如下：<\/p>/);
  assert.match(html, /<p>（3张原图随上述引用直接展示）<\/p>/);
  assert.equal((html.match(/<p>/g) || []).length, 4);
});

test('结构化正文沿用 AI 的段落与来源位置，不额外整理', () => {
  const content = '结果为−4～2μm。\n\n来源：[记录 · v2](debug-issue:trial/2)';
  const html = render(
    '```rich-content\n' +
      JSON.stringify({ version: 1, blocks: [{ id: 'body', type: 'text', content }] }) +
      '\n```',
  );
  assert.match(html, /<p>结果为−4～2μm。<\/p>\s*<p>来源：<button/);
  assert.match(html, /记录 · v2<\/button>/);
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

test('经验引用保留 AI 选择的标签和修订文字，使用当前页弹窗按钮', () => {
  const html = render('处理结果。 [取片经验 · v2](debug-issue:pickup/2)');
  assert.match(html, /<button[^>]*aria-haspopup="dialog"[^>]*>取片经验 · v2<\/button>/);
  assert.doesNotMatch(html, /handover\/issues|href="debug-issue:|参考资料/);
});

test('无效经验版本不能触发记录查看或变成外部跳转', () => {
  for (const href of ['debug-issue:pickup/0', 'debug-issue:pickup/9007199254740992']) {
    const html = render(`[经验](${href})`);
    assert.match(html, /引用格式无效/);
    assert.doesNotMatch(html, /aria-haspopup="dialog"|href="debug-issue:/);
  }
});

test('已删除的项目资料引用只保留文字，不显示读取按钮或可点击链接', () => {
  const html = render('历史[旧资料](material:project-a/manual/1#L1)正文。');
  assert.match(html, /历史<span>旧资料<\/span>正文/);
  assert.doesNotMatch(html, /<button|<a|material:/);
});

test('KaTeX 同时解析行内和独立公式，坏公式保留可读原文', () => {
  const html = render('行内 $E=mc^2$。\n\n$$\n\\frac{1}{2} + x\n$$');
  assert.match(html, /class="katex"/);
  assert.match(html, /katex-display/);
  assert.match(html, /<math/);
  const invalid = render('$\\frac{broken$');
  assert.match(invalid, /katex-error/);
  assert.match(invalid, /frac/);
  const unsafe = render('$\\href{javascript:alert(1)}{危险}$');
  assert.doesNotMatch(unsafe, /href="javascript:|<script/);
});

test('未闭合的流式代码块保留长行、空白和文本，结束后不修改内容', () => {
  const code = '  const value = "中英文";\n' + 'x'.repeat(8000) + '\n\n';
  const partial = render('```typescript\n' + code, [], true);
  assert.ok(partial.includes('x'.repeat(8000)));
  assert.match(partial, /typescript/);
  assert.match(partial, /复制代码/);
  const completed = render('```typescript\n' + code + '```');
  assert.ok(completed.includes('x'.repeat(8000)));
});

test('Markdown 表格使用独立滚动容器且保留转义竖线及单元格对齐', () => {
  const html = render('| 中文 | Value |\n|---|---:|\n| A\\|B | 0 |');
  assert.match(html, /class="markdown-table-scroll"/);
  assert.match(html, /<thead>/);
  assert.match(html, /A\|B/);
  assert.match(html, /text-align:right/);
});

test('markdown 和 tool_call 块真实分发，工具参数始终为文字且失败不影响相邻内容', () => {
  const html = render(
    '```rich-content\n' +
      JSON.stringify({
        version: 1,
        blocks: [
          { id: 'm', type: 'markdown', content: '**正常正文**' },
          {
            id: 't',
            type: 'tool_call',
            tool: {
              id: 'call',
              name: 'read_source',
              arguments: { path: '**不能作为强调**<script>bad()</script>' },
              status: 'error',
              result: '文件不存在',
            },
          },
          { id: 'bad', type: 'unknown' },
          { id: 'end', type: 'text', content: '结尾正文' },
        ],
      }) +
      '\n```',
  );
  assert.match(html, /<strong>正常正文<\/strong>/);
  assert.match(html, /执行失败/);
  assert.match(html, /文件不存在/);
  assert.match(html, /\*\*不能作为强调\*\*/);
  assert.doesNotMatch(html, /<script>|<strong>不能作为强调/);
  assert.match(html, /结尾正文/);
});
