import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';

const saved = new Map();
globalThis.localStorage = {
  getItem: (key) => saved.get(key) ?? null,
  setItem: (key, value) => saved.set(key, value),
  removeItem: (key) => saved.delete(key),
};
globalThis.window = { localStorage: globalThis.localStorage };
const { useWorkspace, draftFor } = await import('../../src/app/state/store.ts');
const projects = {
  default_project_id: 'A',
  projects: [
    { id: 'A', state: 'active' },
    { id: 'B', state: 'active' },
    { id: 'archived', state: 'archived' },
  ],
};
const environment = {
  store: useWorkspace,
  draftFor,
  effects: [],
  requests: [],
  notices: [],
  list: { data: projects },
  project: { source_root: null, source_folders: [] },
  error: undefined,
};

// 执行真实新建 Hook、初始化 effect 和工作区状态，只隔离 React 调度、HTTP 与子页面。
const result = await build({
  stdin: {
    contents:
      "export { useNewConversation } from './src/features/chat/hooks/useNewConversation';" +
      "export { ProjectShell } from './src/features/projects/components/ProjectShell';",
    resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
    loader: 'tsx',
  },
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  jsx: 'automatic',
  plugins: [
    {
      name: 'external-boundaries',
      setup(builder) {
        const stubs = new Map([
          ['react', 'export function useEffect(effect) { environment.effects.push(effect); }'],
          [
            '@tanstack/react-query',
            'export const useQuery = () => environment.list;' +
              'export const QueryClientProvider = ({children}) => children;',
          ],
          [
            'store',
            'export const useWorkspace = (selector) => selector(environment.store.getState());' +
              'useWorkspace.getState = () => environment.store.getState();' +
              'useWorkspace.setState = (...args) => environment.store.setState(...args);' +
              'export const draftFor = (state) => environment.draftFor(state);',
          ],
          ['projects', 'export const useProjects = () => environment.list;'],
          ['cache', 'export const projectCache = (id) => id;'],
          ['toast', 'export const toast = (message) => environment.notices.push(message);'],
          [
            'http',
            'export function api(path) {' +
              'environment.requests.push(path);' +
              'return environment.error ? Promise.reject(environment.error) : Promise.resolve(environment.project); }',
          ],
          ['ui', 'export const Button = () => null; export const ErrorText = () => null;'],
          ['app', 'export default function App() { return null; }'],
        ]);
        const suffixes = [
          ['/state/store', 'store'],
          ['/useProjects', 'projects'],
          ['/projectCache', 'cache'],
          ['/utils/toasts', 'toast'],
          ['/api/client', 'http'],
          ['/ui/ui', 'ui'],
          ['/app/App', 'app'],
        ];
        builder.onResolve({ filter: /.*/ }, ({ path }) => {
          const name = stubs.has(path)
            ? path
            : suffixes.find(([suffix]) => path.endsWith(suffix))?.[1];
          if (name) return { path: name, namespace: 'boundary' };
        });
        builder.onLoad({ filter: /.*/, namespace: 'boundary' }, ({ path }) => ({
          contents: stubs.get(path),
          loader: 'js',
        }));
      },
    },
  ],
});
const bundledModule = { exports: {} };
new Function('require', 'module', 'exports', 'environment', result.outputFiles[0].text)(
  createRequire(import.meta.url),
  bundledModule,
  bundledModule.exports,
  environment,
);
const { useNewConversation, ProjectShell } = bundledModule.exports;

function reset() {
  saved.clear();
  useWorkspace.setState(useWorkspace.getInitialState(), true);
  environment.effects = [];
  environment.requests = [];
  environment.notices = [];
  environment.list = { data: projects };
  environment.error = undefined;
}

async function synchronizeProjectShell() {
  ProjectShell();
  for (const effect of environment.effects.splice(0)) effect();
  await Promise.resolve();
  await Promise.resolve();
}

test('最近对话的无项目新建入口离开当前项目，初始化和列表刷新不再把它拉回项目', async () => {
  reset();
  useWorkspace.getState().initializeProject('B');
  useWorkspace.getState().selectThread('chat-b');
  useWorkspace.getState().setDraft('原项目草稿');
  assert.equal(useNewConversation()(), true);
  assert.equal(useWorkspace.getState().projectId, 'independent');
  assert.equal(useWorkspace.getState().threadId, '');
  assert.equal(draftFor(useWorkspace.getState()).content, '');
  await synchronizeProjectShell();
  await synchronizeProjectShell();
  assert.equal(useWorkspace.getState().projectId, 'independent');
  assert.equal(useWorkspace.getState().drafts['chat-b'].content, '原项目草稿');
  assert.deepEqual(environment.requests, []);
});

test('项目列表尚未返回时，公共入口也能创建独立对话', () => {
  reset();
  useWorkspace.getState().initializeProject('B');
  environment.list = { isPending: true };
  assert.equal(useNewConversation()(), true);
  assert.equal(useWorkspace.getState().projectId, 'independent');
  assert.deepEqual(environment.notices, []);
});

test('项目内新建仍固定指定项目，归档或已删除项目不能回退到其他项目', () => {
  reset();
  useWorkspace.getState().initializeProject('B');
  const start = useNewConversation();
  assert.equal(start('A'), true);
  assert.equal(useWorkspace.getState().projectId, 'A');
  assert.equal(start('archived'), false);
  assert.equal(start('removed'), false);
  assert.equal(useWorkspace.getState().projectId, 'A');
  assert.equal(environment.notices.length, 2);
});

test('新账号初次初始化默认进入独立对话；已有项目会话保持当前归属', async () => {
  reset();
  await synchronizeProjectShell();
  assert.equal(useWorkspace.getState().projectId, 'independent');
  assert.deepEqual(environment.requests, []);
  useWorkspace.getState().switchProject('B');
  useWorkspace.getState().selectThread('chat-b');
  await synchronizeProjectShell();
  assert.equal(useWorkspace.getState().projectId, 'B');
  assert.equal(useWorkspace.getState().threadId, 'chat-b');
  assert.deepEqual(environment.requests, ['/projects/B']);
});

test('已失效的项目恢复为独立对话，不自动归属默认项目', async () => {
  reset();
  useWorkspace.getState().initializeProject('removed');
  environment.error = { status: 404 };
  await synchronizeProjectShell();
  assert.equal(useWorkspace.getState().projectId, 'independent');
  assert.deepEqual(environment.requests, ['/projects/removed']);
});
