import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { citationPath } from '../../src/features/source_reader/lib/citationPath.ts';
import { citationEndLine } from '../../src/features/source_reader/lib/citationRange.ts';

const saved = new Map();
globalThis.localStorage = {
  getItem: (key) => saved.get(key) ?? null,
  setItem: (key, value) => saved.set(key, value),
  removeItem: (key) => saved.delete(key),
};
globalThis.window = { localStorage: globalThis.localStorage };
const { useWorkspace } = await import('../../src/app/state/store.ts');
const require = createRequire(import.meta.url);
const { QueryClient, QueryClientProvider } = require('@tanstack/react-query');
const environment = { store: useWorkspace, requests: [], notices: [], respond: undefined };
const compiled = await build({
  stdin: {
    contents:
      "export { useSourceCitation } from './src/features/source_reader/hooks/useSourceCitation';",
    resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
    loader: 'tsx',
  },
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  plugins: [
    {
      name: 'boundaries',
      setup(builder) {
        builder.onResolve(
          { filter: /\/(state\/store|api\/client|utils\/toasts)$/ },
          ({ path }) => ({ path, namespace: 'boundary' }),
        );
        builder.onLoad({ filter: /.*/, namespace: 'boundary' }, ({ path }) => ({
          loader: 'js',
          contents: path.endsWith('/store')
            ? 'export const useWorkspace = (selector) => selector(environment.store.getState()); useWorkspace.getState = () => environment.store.getState(); useWorkspace.setState = (...args) => environment.store.setState(...args);'
            : path.endsWith('/toasts')
              ? 'export const toast = (message) => environment.notices.push(message);'
              : 'export const query = encodeURIComponent; export async function api(path,options,scope) { environment.requests.push({path,scope}); return environment.respond(path,scope); }',
        }));
      },
    },
  ],
});
const bundled = { exports: {} };
new Function('require', 'module', 'exports', 'environment', compiled.outputFiles[0].text)(
  require,
  bundled,
  bundled.exports,
  environment,
);
const context = {
  scope_id: 'independent',
  source_workspace_id: 'main',
  attached_source_ids: [],
  knowledge_available: true,
};
const file = {
  path: 'Dir/Test.cs',
  source_workspace_id: 'main',
  content: 'text',
  version: 'v1',
  line_count: 1000,
};

async function withCitation(
  scope,
  verify,
  respond = (path) => (path.endsWith('/source-context') ? { ...context, scope_id: scope } : file),
) {
  saved.clear();
  useWorkspace.setState(useWorkspace.getInitialState(), true);
  useWorkspace.getState().initializeProject(scope);
  useWorkspace.setState({ explorerOpen: false });
  environment.requests = [];
  environment.notices = [];
  environment.respond = respond;
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  let open;
  function Harness() {
    open = bundled.exports.useSourceCitation();
    return null;
  }
  renderToStaticMarkup(createElement(QueryClientProvider, { client }, createElement(Harness)));
  try {
    await verify(open);
  } finally {
    client.clear();
  }
}

for (const scope of ['independent', 'project-a'])
  test(`${scope} 使用真实源码身份，在右侧打开并展开对应目录与行范围`, async () => {
    await withCitation(scope, async (open) => {
      assert.equal(await open('Dir/Test.cs', 791, 802, 'v1', 'main'), true);
      const state = useWorkspace.getState();
      assert.equal(state.historicalSource, null);
      assert.equal(state.activePath, 'Dir/Test.cs');
      assert.equal(state.jump.line, 791);
      assert.equal(state.jump.endLine, 802);
      assert.equal(state.codeOpen, true);
      assert.equal(state.explorerOpen, true);
      assert.ok(state.expandedDirectories.includes('Dir'));
      assert.ok(state.revealTime > 0);
      assert.deepEqual(
        environment.requests.map((row) => row.path),
        [`/projects/${scope}/source-context`, '/file?path=Dir%2FTest.cs'],
      );
      assert.equal(environment.requests[1].scope, scope);
    });
  });

test('第一次点击等待源码身份返回，不因项目资料尚未加载而误弹窗', async () => {
  let resolve;
  const pending = new Promise((r) => {
    resolve = r;
  });
  await withCitation(
    'independent',
    async (open) => {
      const result = open('Dir/Test.cs', 2, 3, 'v1', 'main');
      await Promise.resolve();
      assert.equal(useWorkspace.getState().historicalSource, null);
      assert.equal(useWorkspace.getState().activePath, '');
      resolve(context);
      assert.equal(await result, true);
      assert.equal(useWorkspace.getState().activePath, 'Dir/Test.cs');
    },
    (path) => (path.endsWith('/source-context') ? pending : file),
  );
});

for (const boundary of ['context', 'file'])
  test(`${boundary} 读取期间切换项目，不污染新项目代码树`, async () => {
    await withCitation(
      'independent',
      async (open) => {
        assert.equal(await open('Dir/Test.cs', 2, 3, 'v1', 'main'), false);
        assert.equal(useWorkspace.getState().projectId, 'project-b');
        assert.equal(useWorkspace.getState().activePath, '');
        assert.equal(useWorkspace.getState().historicalSource, null);
      },
      (path) => {
        const metadata = path.endsWith('/source-context');
        if (metadata === (boundary === 'context'))
          useWorkspace.getState().switchProject('project-b');
        return metadata ? context : file;
      },
    );
  });

test('已关联附加目录的旧相对路径加上稳定前缀，不打开同名主目录文件', async () => {
  await withCitation(
    'project-a',
    async (open) => {
      assert.equal(await open('Dir/Test.cs', 2, 3, 'v1', 'library'), true);
      assert.equal(useWorkspace.getState().activePath, '@sources/library/Dir/Test.cs');
      assert.equal(useWorkspace.getState().historicalSource, null);
    },
    (path) =>
      path.endsWith('/source-context')
        ? { ...context, attached_source_ids: ['library'] }
        : { ...file, source_workspace_id: 'library' },
  );
  assert.equal(
    citationPath(
      { ...context, attached_source_ids: ['library'] },
      '@sources/library/Dir/Test.cs',
      'library',
    ),
    '@sources/library/Dir/Test.cs',
  );
  assert.throws(() => citationPath(context, '@sources/other/Dir/Test.cs', 'main'), /身份不一致/);
});

test('确属另一目录的历史引用保留原始来源，不能跳到当前目录同名文件', async () => {
  await withCitation(
    'independent',
    async (open) => {
      assert.equal(await open('Dir/Test.cs', 2, 3, 'v1', 'original'), true);
      assert.equal(useWorkspace.getState().activePath, '');
      assert.equal(useWorkspace.getState().historicalSource.source.source_workspace_id, 'original');
      assert.equal(environment.requests[1].path, '/sources/original/file?path=Dir%2FTest.cs');
    },
    (path) =>
      path.endsWith('/source-context') ? context : { ...file, source_workspace_id: 'original' },
  );
});

for (const [version, end, notice] of [
  ['old', 3, /文件已变化/],
  ['v1', 1001, /已失效/],
])
  test(`版本或范围失效仍打开右侧当前文件，但不错误高亮：${version}/${end}`, async () => {
    await withCitation('independent', async (open) => {
      assert.equal(await open('Dir/Test.cs', 2, end, version, 'main'), false);
      assert.equal(useWorkspace.getState().activePath, 'Dir/Test.cs');
      assert.equal(useWorkspace.getState().jump.endLine, undefined);
      assert.ok(environment.notices.some((message) => notice.test(message)));
    });
  });

test('读取源码身份失败时保留页面状态，不降级成错误目录或无权限原始引用', async () => {
  await withCitation(
    'independent',
    async (open) => {
      assert.equal(await open('Dir/Test.cs', 2, 3, 'v1', 'main'), false);
      assert.equal(useWorkspace.getState().activePath, '');
      assert.equal(useWorkspace.getState().historicalSource, null);
      assert.equal(environment.requests.length, 1);
    },
    () => {
      throw new Error('网络失败');
    },
  );
});

test('原始目录的版本变化显示当前文件供核对，但不返回成功定位', async () => {
  await withCitation(
    'independent',
    async (open) => {
      assert.equal(await open('Dir/Test.cs', 2, 3, 'old', 'original'), false);
      assert.equal(useWorkspace.getState().activePath, '');
      assert.equal(useWorkspace.getState().historicalSource.source.version, 'v1');
      assert.ok(environment.notices.some((message) => /文件已变化/.test(message)));
    },
    (path) =>
      path.endsWith('/source-context') ? context : { ...file, source_workspace_id: 'original' },
  );
});

test('旧引用仅有起始锚点时，只有读取证据覆盖标签范围才恢复多行定位', () => {
  const reads = [{ path: 'Dir/Test.cs', start_line: 760, end_line: 825 }];
  assert.equal(citationEndLine('Dir/Test.cs', 791, undefined, 'Test.cs:791-802', reads), 802);
  assert.equal(citationEndLine('Dir/Test.cs', 791, undefined, 'Test.cs:791-802', []), 791);
  for (const label of ['Other.cs:791-802', 'Test.cs:790-802', 'Test.cs:791-900', 'Test.cs:791-780'])
    assert.equal(citationEndLine('Dir/Test.cs', 791, undefined, label, reads), 791, label);
  assert.equal(citationEndLine('Dir/Test.cs', 791, '795', 'Test.cs:791-802', reads), 795);
});
