import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';

const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: 'http://localhost/' });
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const environment = { jumps: [], files: [], row: undefined };
const compiled = await build({
  stdin: {
    contents:
      "export { AnswerMarkdown } from './src/features/chat/components/AnswerMarkdown'; export { FileBlock } from './src/features/chat/rich/FileBlock'; export { ToolActivity } from './src/features/chat/components/ToolActivity';",
    resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
    loader: 'tsx',
  },
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  jsx: 'automatic',
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
  loader: { '.css': 'empty' },
  plugins: [
    {
      name: 'external-boundaries',
      setup(builder) {
        builder.onResolve(
          {
            filter:
              /(state\/store|api\/client|hooks\/useSourceCitation|handover\/shared\/client|materials\/OriginalMaterialViewer|components\/(HandoverMaterialViewer|SelectionPreview)|markdown\/CodeSyntax)$/,
          },
          ({ path }) => ({ path, namespace: 'boundary' }),
        );
        builder.onLoad({ filter: /.*/, namespace: 'boundary' }, ({ path }) => ({
          loader: 'js',
          contents: path.endsWith('store')
            ? 'export const useWorkspace = s => s({projectId:"p"}); useWorkspace.getState = () => ({projectId:"p"});'
            : path.endsWith('handover/shared/client')
              ? 'export const handoverClient = () => ({ get: async path => { environment.files.push(path); return environment.row; } });'
              : path.endsWith('api/client')
                ? 'export class ApiError extends Error {}; export const api = () => {throw Error("禁止网络");};'
                : path.endsWith('useSourceCitation')
                  ? 'export const useSourceCitation = () => async (...args) => { environment.jumps.push(args); return true; }; export const readCitationSource = () => {throw Error("禁止网络");};'
                  : path.endsWith('OriginalMaterialViewer')
                    ? 'import { createElement } from "react"; export const OriginalMaterialViewer = ({row}) => createElement("div", {"data-viewer": row.id}, row.title);'
                    : path.endsWith('CodeSyntax')
                      ? 'import { createElement } from "react"; export const CodeSyntax = ({content}) => createElement("code", null, content);'
                      : 'export const HandoverMaterialViewer = () => null; export const SelectionPreview = () => null;',
        }));
      },
    },
  ],
});
const module = { exports: {} };
const require = createRequire(import.meta.url);
const { QueryClient, QueryClientProvider } = require('@tanstack/react-query');
new Function('require', 'module', 'exports', 'environment', compiled.outputFiles[0].text)(
  require,
  module,
  module.exports,
  environment,
);
const { AnswerMarkdown, FileBlock, ToolActivity } = module.exports;
const fence = (blocks) => '```rich-content\n' + JSON.stringify({ version: 1, blocks }) + '\n```';
async function mounted(verify) {
  const root = createRoot(document.getElementById('root'));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const render = async (element) =>
    act(async () => root.render(createElement(QueryClientProvider, { client }, element)));
  try {
    await verify({ render, client });
  } finally {
    await act(async () => root.unmount());
    client.clear();
  }
}

test('点击紧凑源码链接传递原路径、行范围、版本和目录；流式追加不重建已确认块', async () => {
  environment.jumps = [];
  await mounted(async ({ render, client }) => {
    const source = {
      path: '@sources/library/Dir/源.cs',
      start_line: 12,
      end_line: 24,
      version: 'v1',
      source_workspace_id: 'library',
    };
    client.setQueryData(['source-evidence', 'p', 'r'], {
      source_evidence: [{ ...source, current_status: 'match', source_workspace_id: 'library' }],
    });
    const content = fence([
      { id: 'code', type: 'code', language: 'python', content: 'print(1)\n'.repeat(30) },
      { id: 'source', type: 'source_reference', sources: [source] },
      {
        id: 'tool',
        type: 'tool_call',
        tool: { id: 'call', name: 'read_source', result: '完成', status: 'success' },
      },
    ]);
    await render(createElement(AnswerMarkdown, { content, runId: 'r', streaming: true }));
    const button = document.querySelector('.answer-code-link');
    assert.equal(button.disabled, false);
    await act(async () => button.click());
    assert.deepEqual(environment.jumps, [[source.path, 12, 24, 'v1', 'library']]);
    await act(async () => document.querySelector('.code-expand').click());
    const tool = document.querySelector('.tool-call-card');
    tool.open = true;
    await render(
      createElement(AnswerMarkdown, {
        content: content + '\n\n新增段落',
        runId: 'r',
        streaming: true,
      }),
    );
    assert.equal(document.querySelector('.tool-call-card'), tool);
    assert.equal(tool.open, true);
    assert.equal(document.querySelector('.code-expand').getAttribute('aria-expanded'), 'true');
    assert.equal(document.querySelector('.answer-code-link'), button);
    await render(
      createElement(AnswerMarkdown, { content: JSON.parse(JSON.stringify(content)), runId: 'r' }),
    );
    assert.equal(button.getAttribute('aria-label'), '打开源码 源.cs:12–24');
  });
});

test('Markdown和结构化代码引用合为同一文件，使用相同定位逻辑且路径只在详情中', async () => {
  environment.jumps = [];
  await mounted(async ({ render, client }) => {
    const source = {
      path: 'Dir/Engine.cs',
      start_line: 12,
      end_line: 24,
      version: 'v1',
      source_workspace_id: 's',
    };
    client.setQueryData(['source-evidence', 'p', 'r'], {
      source_evidence: [{ ...source, start_line: 1, end_line: 100, current_status: 'match' }],
    });
    const content =
      fence([{ id: 'src', type: 'source_reference', sources: [source] }]) +
      '\n\n来源：[另一个范围](source:Dir/Engine.cs#L30-L32)';
    await render(createElement(AnswerMarkdown, { content, runId: 'r' }));
    assert.equal(document.querySelectorAll('.answer-code-file').length, 1);
    assert.equal(
      document.querySelectorAll('.rich-source-reference,.rich-source-link,.source-link').length,
      0,
    );
    const links = [...document.querySelectorAll('.answer-code-link')];
    assert.deepEqual(
      links.map((item) => item.textContent),
      ['12–24', '30–32'],
    );
    for (const link of links) await act(async () => link.click());
    assert.deepEqual(environment.jumps, [
      ['Dir/Engine.cs', 12, 24, 'v1', 's'],
      ['Dir/Engine.cs', 30, 32, 'v1', 's'],
    ]);
    const detail = document.querySelector('.answer-code-details');
    assert.equal(detail.open, false);
    assert.ok(detail.querySelector('.answer-code-path').textContent.includes('Dir/Engine.cs'));
    assert.doesNotMatch(
      document.querySelector('.answer-code-file-heading').querySelector('.answer-code-filename')
        .textContent,
      /Dir\//,
    );
  });
});

test('工具卡片区分运行、成功、失败和跳过，空结果及参数不丢失且展开状态稳定', async () => {
  await mounted(async ({ render }) => {
    const tools = [
      { id: 'run', name: 'read_source', arguments: { path: '**原文**' } },
      { id: 'done', name: 'search_source', status: 'success', result: '' },
      { id: 'failed', name: 'read_source', status: 'error', result: '找不到文件' },
      {
        id: 'skip',
        name: 'read_source',
        execution_status: 'skipped',
        skip_reason: 'verification_reserved',
      },
    ];
    await render(createElement(ToolActivity, { tools }));
    assert.deepEqual(
      [...document.querySelectorAll('.tool-call-card')].map((item) => item.dataset.state),
      ['pending', 'success', 'failed', 'skipped'],
    );
    assert.match(document.body.textContent, /（空结果）/);
    assert.match(document.body.textContent, /\*\*原文\*\*/);
    assert.equal(document.querySelector('strong'), null);
    const running = document.querySelector('.tool-call-card');
    running.open = true;
    await render(
      createElement(ToolActivity, {
        tools: [{ ...tools[0], status: 'success', result: '源码内容' }, ...tools.slice(1)],
      }),
    );
    assert.equal(document.querySelector('.tool-call-card'), running);
    assert.equal(running.open, true);
    assert.equal(running.dataset.state, 'success');
  });
});

test('文件通过已有资料接口打开；旧版本和非资料记录不会冒充原附件', async () => {
  for (const [kind, version, expected] of [
    ['source', 2, true],
    ['source', 3, false],
    ['task', 2, false],
  ]) {
    environment.files = [];
    environment.row = { id: 'file-record', kind, version, title: '真实资料标题' };
    await mounted(async ({ render }) => {
      await render(
        createElement(FileBlock, {
          block: {
            id: 'file',
            type: 'file',
            record_id: 'file-record',
            name: '资料.pdf',
            version: 2,
          },
        }),
      );
      await act(async () => document.querySelector('.rich-file > button').click());
      assert.deepEqual(environment.files, ['/records/file-record']);
      assert.equal(!!document.querySelector('[data-viewer="file-record"]'), expected);
      if (!expected) assert.ok(document.querySelector('[role="alert"]'));
    });
  }
});

test.after(() => dom.window.close());
