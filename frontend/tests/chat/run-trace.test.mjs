import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const bundled = await build({
  stdin: {
    contents: `export * from './src/features/chat/components/RunTraceSummary.tsx';`,
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
      name: 'no-network',
      setup(builder) {
        builder.onResolve({ filter: /app\/components\/Markdown$/ }, () => ({
          path: 'markdown',
          namespace: 'boundary',
        }));
        builder.onResolve({ filter: /app\/api\/client$/ }, () => ({
          path: 'http',
          namespace: 'boundary',
        }));
        builder.onLoad({ filter: /.*/, namespace: 'boundary' }, ({ path }) => ({
          contents:
            path === 'markdown'
              ? 'export const Markdown = ({content}) => content;'
              : 'export const api = () => { throw new Error("不应自动读取资料原文"); };',
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
const { RunTraceSummary, durationLabel } = module.exports;
const { QueryClient, QueryClientProvider } = require('@tanstack/react-query');

function render(trace, extra = {}) {
  const client = new QueryClient();
  try {
    return renderToStaticMarkup(
      createElement(
        QueryClientProvider,
        { client },
        createElement(RunTraceSummary, {
          context: { memories: [], selections: [], tools: [], recorded: true, trace, ...extra },
        }),
      ),
    );
  } finally {
    client.clear();
  }
}

const trace = {
  recorded: true,
  status: 'completed',
  elapsed_ms: 1320,
  queue_ms: 70,
  model_calls: 3,
  filters: {
    memory: {
      status: 'selected',
      candidate_count: 6,
      selected_count: 2,
      duration_ms: 400,
      passes: 1,
      cache_hits: 0,
    },
    history: {
      status: 'selected',
      candidate_count: 8,
      selected_count: 3,
      recent_messages: 12,
      before_tokens: 3000,
      after_tokens: 1000,
      duration_ms: 200,
      passes: 1,
      cache_hits: 2,
    },
    knowledge: {
      status: 'unavailable',
      candidate_count: 4,
      selected_count: 0,
      duration_ms: 100,
      passes: 1,
      cache_hits: 0,
    },
  },
  checks: { knowledge_answer_review: { verdict: 'unknown', reason: '核查暂未完成' } },
  requests: [
    { purpose: 'knowledge_selection', calls: 2, timed_calls: 2, duration_ms: 300, failed_calls: 1 },
  ],
  tools: [{ id: 'read', name: 'read_source', status: 'success', duration_ms: 300 }],
};

test('运行详情展示来源选择数量、缓存、核查状态和各类请求耗时', () => {
  const html = render(trace);
  for (const text of [
    '本轮依据与耗时',
    '1.3 秒',
    '排队 70 毫秒',
    '候选 6 项，选中 2 项',
    '缓存复用 2 次',
    '近期保留 12 条消息',
    '筛选未完成',
    '核查暂未完成',
    '筛选问题与经验',
    '1 次失败',
    '不能相加当作总耗时',
  ])
    assert.ok(html.includes(text), text);
  assert.ok(!html.includes('knowledge_selection'));
});

test('旧运行的缺失筛选或耗时显示未记录，不能伪装为零或通过', () => {
  const html = render({
    ...trace,
    recorded: false,
    elapsed_ms: null,
    queue_ms: null,
    filters: {},
    checks: {},
    requests: [{ purpose: 'answer', calls: 1, timed_calls: 0, duration_ms: 0, failed_calls: 0 }],
    tools: [],
  });
  assert.match(html, /缺失数据不能按零计算/);
  assert.match(html, /耗时未记录/);
  assert.doesNotMatch(html, /0 毫秒|无需筛选较早历史|<dd>通过<\/dd>/);
});

test('普通短对话说明无需旧历史筛选、经验未检索，关闭的记忆显示未启用', () => {
  const html = render(
    { ...trace, filters: {}, requests: [], tools: [] },
    { source_options: { use_memory: false } },
  );
  assert.match(html, /无需筛选较早历史/);
  assert.match(html, /本轮未检索/);
  assert.match(html, /未启用/);
});

test('其他账号的个人记忆统计只显示可见性说明', () => {
  const html = render({ ...trace, memory_private: true, filters: {}, requests: [], tools: [] });
  assert.match(html, /个人记忆筛选详情仅发起账号可见/);
  assert.doesNotMatch(html, /候选 6/);
});

test('来源标题可打开固定版本原文，加载概况不自动请求原文', () => {
  const html = render(trace, { debug_issues: [{ id: 'record', version: 2, title: '阀门试验' }] });
  assert.match(html, /查看本轮选中的依据/);
  assert.match(html, /阀门试验/);
  assert.match(html, /aria-haspopup="dialog"/);
  assert.doesNotMatch(html, /正在加载记录/);
});

test('耗时格式区分未知与实际零值，支持秒与毫秒', () => {
  assert.equal(durationLabel(null), '耗时未记录');
  assert.equal(durationLabel(-1), '耗时未记录');
  assert.equal(durationLabel(NaN), '耗时未记录');
  assert.equal(durationLabel(0), '0 毫秒');
  assert.equal(durationLabel(1200), '1.2 秒');
});
