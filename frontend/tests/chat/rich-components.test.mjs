import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const require = createRequire(import.meta.url);
const result = await build({
  stdin: {
    contents:
      "export * from './src/features/chat/rich/ContentBlocks.tsx'; export * from './src/features/chat/rich/FlowDiagram.tsx'; export * from './src/shared/ui/markdown/CodeBlock.tsx';",
    resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
    loader: 'tsx',
  },
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  jsx: 'automatic',
});
const module = { exports: {} };
new Function('require', 'module', 'exports', result.outputFiles[0].text)(
  require,
  module,
  module.exports,
);
const { OverviewGrid, StepFlow, DataTable, FlowDiagram, CollapsibleSection, CodeBlock } =
  module.exports;
const render = (Component, props) => renderToStaticMarkup(createElement(Component, props));
const renderText = (content) => createElement('p', null, content);
const renderSource = (source, key) =>
  createElement('span', { key }, `${source.path}:${source.start_line}`);

test('功能概览按真实数据展示，不将无操作项目变成按钮', () => {
  const block = {
    type: 'overview_grid',
    id: 'o',
    items: [{ id: 'one', title: '参数管理', description: '任意业务描述', icon: 'settings' }],
  };
  const html = render(OverviewGrid, { block, renderText, renderSource });
  assert.match(html, /参数管理/);
  assert.match(html, /任意业务描述/);
  assert.doesNotMatch(html, /<button|FrmGlobal|标定/);
  assert.equal(
    render(OverviewGrid, { block: { ...block, items: [] }, renderText, renderSource }),
    '',
  );
});

test('步骤支持超过五项、源码和默认收起的次要细节', () => {
  const steps = Array.from({ length: 19 }, (_, i) => ({
    id: `s${i}`,
    title: `第${i + 1}项`,
    description: '动作',
    details: i === 0 ? '补充说明' : undefined,
    sources: [{ path: 'Engine.cs', start_line: i + 1 }],
  }));
  const html = render(StepFlow, {
    block: { id: 's', type: 'step_flow', title: '真实流程', steps },
    renderText,
    renderSource,
  });
  assert.equal((html.match(/class="rich-step-number"/g) || []).length, 19);
  assert.match(html, /Engine.cs:19/);
  assert.match(html, /<details class="rich-collapsible"><summary>详细说明/);
  assert.match(html, /<ol/);
});

test('表格保留零值、数字对齐、表头语义及恶意字符串的文本性质', () => {
  const html = render(DataTable, {
    block: {
      id: 't',
      type: 'table',
      title: '参数',
      columns: [{ id: 'a', label: '数值', align: 'right' }],
      rows: [
        { id: 'zero', cells: [0] },
        { id: 'html', cells: ['<script>alert(1)</script>'] },
      ],
    },
  });
  assert.match(html, /scope="col"/);
  assert.match(html, /text-align:right/);
  assert.match(html, />0<\/td>/);
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /&lt;script&gt;/);
});

test('图形只展示显式节点和边，有缩放、适配、全屏与文字替代', () => {
  const html = render(FlowDiagram, {
    block: {
      id: 'g',
      type: 'diagram',
      title: '异常处理',
      nodes: [
        { id: 'a', label: '执行' },
        { id: 'b', label: '重试' },
      ],
      edges: [
        { from: 'a', to: 'b', label: '失败' },
        { from: 'b', to: 'a' },
      ],
    },
  });
  for (const label of ['缩小图形', '放大图形', '适配图形宽度', '全屏查看图形', '节点与连接说明'])
    assert.ok(html.includes(label));
  assert.match(html, /执行 → 重试：失败/);
  assert.match(html, /重试 → 执行/);
});

test('折叠使用原生语义，代码保留完整文本与可访问操作', () => {
  assert.match(
    render(CollapsibleSection, { title: '详情', defaultOpen: true, children: '内容' }),
    /<details[^>]* open=""/,
  );
  const html = render(CodeBlock, {
    filename: 'worker.py',
    startLine: 8,
    streaming: true,
    children: createElement(
      'code',
      { className: 'language-python' },
      'print("hello")\n'.repeat(25),
    ),
  });
  assert.match(html, /worker.py/);
  assert.match(html, /复制代码/);
  assert.match(html, /aria-expanded="false"/);
  assert.equal((html.match(/print\(/g) || []).length, 25);
});
