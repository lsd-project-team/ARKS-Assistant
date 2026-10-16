import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

// 被编译组件使用 CJS 入口；Provider 也使用同一入口，避免测试创建两份 React Context。
const require = createRequire(import.meta.url);
const { QueryClient, QueryClientProvider } = require('@tanstack/react-query');

// 执行真实组件与查询缓存，仅隔离资料查看器和 HTTP，不替换筛选逻辑。
const result = await build({
  stdin: {
    contents: "export * from './src/features/chat/components/RunKnowledgeSummary.tsx';",
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
  plugins: [
    {
      name: 'external-boundaries',
      setup(builder) {
        builder.onResolve({ filter: /app\/(components\/Markdown|api\/client)$/ }, (args) => ({
          path: args.path.endsWith('/Markdown') ? 'markdown' : 'http',
          namespace: 'boundary',
        }));
        builder.onLoad({ filter: /.*/, namespace: 'boundary' }, (args) => ({
          contents:
            args.path === 'markdown'
              ? 'export function Markdown({content}) { return content; }'
              : 'export function api() { throw new Error("测试禁止真实 HTTP 请求"); }',
          loader: 'js',
        }));
      },
    },
  ],
});
const bundledModule = { exports: {} };
new Function('require', 'module', 'exports', result.outputFiles[0].text)(
  require,
  bundledModule,
  bundledModule.exports,
);
const { KnowledgeFeedback, RunKnowledgeSummary } = bundledModule.exports;
const references = [
  {
    kind: 'handover_material',
    id: 'daf',
    title: 'M8 DAF信息收集.docx',
    version: 1,
    citation: 'handover-source:daf/1#L1-L20',
  },
  {
    kind: 'debug_issue',
    id: 'pickup',
    title: '中转台取片异常',
    version: 2,
    citation: 'debug-issue:pickup/2',
    resolution_status: 'open',
  },
];
const searches = [{ kind: 'material', matched: 0 }];
const render = (props) => renderToStaticMarkup(createElement(KnowledgeFeedback, props));

test('流式问候有候选和检索未命中时，也不显示本轮参考或检索提示', () => {
  assert.equal(render({ answer: '你好！', references, searches }), '');
});

test('流式回答只显示实际引用的一项及其未解决提示', () => {
  const html = render({ answer: '[记录](debug-issue:pickup/2)', references, searches });
  assert.match(html, /本轮参考 · 1 条资料/);
  assert.match(html, /中转台取片异常/);
  assert.match(html, /未解决，不能作为已验证方案/);
  assert.doesNotMatch(html, /M8 DAF|未找到相关可用内容/);
});

test('上下文保留完整候选与检索提示，并明确区分于回答引用', () => {
  const html = render({ mode: 'context', references, searches });
  assert.match(html, /资料检索记录 · 2 条资料/);
  assert.match(html, /M8 DAF信息收集.docx/);
  assert.match(html, /中转台取片异常/);
  assert.match(html, /未找到相关可用内容/);
  assert.match(html, /不表示回答已经引用/);
  assert.doesNotMatch(html, /本轮参考/);
});

test('记忆保存反馈不依赖引用资料，空检索记录不产生占位块', () => {
  const html = render({
    answer: '已记住',
    references,
    saves: [{ text: '已保存', scope: 'user', name: '答复语言', status: 'saved' }],
  });
  assert.match(html, /已保存 · 个人偏好 · 答复语言/);
  assert.doesNotMatch(html, /本轮参考|<details/);
  assert.equal(render({ mode: 'context' }), '');
});

function renderHistory(answer, context) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  try {
    if (context) client.setQueryData(['run-knowledge', 'project-a', 'run-a'], context);
    return renderToStaticMarkup(
      createElement(
        QueryClientProvider,
        { client },
        createElement(RunKnowledgeSummary, { runId: 'run-a', projectId: 'project-a', answer }),
      ),
    );
  } finally {
    client.clear();
  }
}

test('历史无引用回答不显示原来的“参考资料与记忆”占位入口', () => {
  assert.equal(renderHistory('你好'), '');
  const html = renderHistory('你好', { references, searches });
  assert.doesNotMatch(html, /本轮参考|参考资料与记忆|M8 DAF|中转台取片异常/);
});

test('历史引用回答使用本条回复的内容筛选缓存记录，切换版本不会串用引用', () => {
  const context = { references, searches };
  const first = renderHistory('[原文](handover-source:daf/1#L5)', context);
  assert.match(first, /本轮参考 · 1 条资料/);
  assert.match(first, /M8 DAF信息收集.docx/);
  assert.match(first, /handover-source:daf\/1#L5/);
  assert.doesNotMatch(first, /中转台取片异常/);
  const second = renderHistory('[记录](debug-issue:pickup/2)', context);
  assert.match(second, /本轮参考 · 1 条资料/);
  assert.match(second, /中转台取片异常/);
  assert.doesNotMatch(second, /M8 DAF/);
});

test('历史候选匹配失败或引用上下文尚未加载时不假造参考列表', () => {
  const missing = renderHistory('[记录](debug-issue:unknown/2)', { references });
  assert.doesNotMatch(missing, /本轮参考|M8 DAF|中转台取片异常/);
  assert.equal(renderHistory('[记录](debug-issue:pickup/2)'), '');
});
