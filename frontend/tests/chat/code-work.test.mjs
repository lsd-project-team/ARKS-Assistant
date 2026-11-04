import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';
const { QueryClient, QueryClientProvider } = createRequire(import.meta.url)(
  '@tanstack/react-query',
);

const dom = new JSDOM('<!doctype html><div id="root"></div>');
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const boundary = { calls: [], status: {}, diff: {}, role: 'user' };
const compiled = await build({
  entryPoints: [
    fileURLToPath(new URL('../../src/features/chat/code_work/CodeWorkDialog.tsx', import.meta.url)),
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
      name: 'code-work-network-boundaries',
      setup(builder) {
        builder.onResolve(
          { filter: /(app\/api\/client|auth\/AuthContext|shared\/ui\/ui)$/ },
          ({ path }) => ({ path, namespace: 'test-boundary' }),
        );
        builder.onLoad({ filter: /.*/, namespace: 'test-boundary' }, ({ path }) => ({
          loader: 'jsx',
          resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
          contents: path.endsWith('AuthContext')
            ? 'export const useAuth = () => ({ session: { user: { role: boundary.role } } });'
            : path.endsWith('/ui')
              ? "export const Modal = ({open,children}) => open ? <section>{children}</section> : null; export const Button = props => <button {...props}/>; export const ErrorText = ({error}) => error ? <div role='alert'>{error.message}</div> : null;"
              : 'export const api = (...args) => boundary.api(...args); export const apiUrl = x => x; export const jsonBody = JSON.stringify;',
        }));
      },
    },
  ],
});
const module = { exports: {} };
new Function('require', 'module', 'exports', 'boundary', compiled.outputFiles[0].text)(
  createRequire(import.meta.url),
  module,
  module.exports,
  boundary,
);
const { CodeWorkDialog } = module.exports;
const path = 'AKRS.ZX2200/Main/Example.cs';
async function until(condition) {
  const deadline = Date.now() + 3000;
  while (!condition()) {
    assert.ok(Date.now() < deadline, '界面没有在时限内更新');
    await act(async () => new Promise((resolve) => setTimeout(resolve, 10)));
  }
}

async function mounted(props, verify) {
  boundary.calls = [];
  boundary.role = 'user';
  boundary.status = {
    exists: true,
    configured: true,
    prepared: true,
    revision: 1,
    source_version: 'abc123',
    files: [{ path, kind: 'modified', version: 'v1' }],
    scope: '本机仿真范围',
  };
  boundary.diff = { path, version: 'v1', before: 'old', after: 'new', diff: '-old\n+new' };
  boundary.api = async (url, options, project) => {
    boundary.calls.push({ url, options, project });
    if (url.includes('/diff?')) return structuredClone(boundary.diff);
    if (url.endsWith('/revert')) {
      const body = JSON.parse(options.body);
      if (body.version !== boundary.diff.version) throw new Error('文件版本已变化，请刷新');
      boundary.status = { ...boundary.status, revision: 2, files: [] };
    }
    return structuredClone(boundary.status);
  };
  const cache = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const root = createRoot(document.getElementById('root'));
  try {
    await act(async () => {
      root.render(
        createElement(
          QueryClientProvider,
          { client: cache },
          createElement(CodeWorkDialog, {
            open: true,
            threadId: 'thread-1',
            projectId: 'project-1',
            busy: false,
            onClose() {},
            onRequest() {},
            ...props,
          }),
        ),
      );
      await new Promise((resolve) => setTimeout(resolve, 30));
    });
    if (props.threadId !== '') {
      await until(
        () => document.querySelector('[aria-label="代码差异"]')?.textContent === '-old\n+new\n',
      );
    }
    await verify(cache);
  } finally {
    await act(async () => root.unmount());
    cache.clear();
  }
}
const button = (text) =>
  Array.from(document.querySelectorAll('button')).find((node) => node.textContent === text);
const click = async (text) => {
  assert.ok(button(text), `button: ${text}`);
  await act(async () => {
    button(text).click();
    await new Promise((resolve) => setTimeout(resolve, 20));
  });
};
const setStatus = async (cache, status) => {
  await act(async () => {
    cache.setQueryData(['code-work', 'project-1', 'thread-1'], status);
    await new Promise((resolve) => setTimeout(resolve, 20));
  });
};

test('差异按当前项目与对话读取，撤销只提交已确认的文件版本', async () => {
  await mounted({}, async (cache) => {
    assert.equal(document.querySelector('[aria-label="代码差异"]').textContent, '-old\n+new\n');
    assert.ok(boundary.calls.every((call) => call.project === 'project-1'));
    assert.equal(document.querySelector('.code-environment'), null);
    await click('撤销此文件');
    boundary.diff.version = 'v2';
    boundary.status.files[0].version = 'v2';
    await act(async () => {
      cache.setQueryData(['code-work', 'project-1', 'thread-1'], structuredClone(boundary.status));
      await new Promise((resolve) => setTimeout(resolve, 30));
    });
    await click('确认撤销');
    await until(() => document.body.textContent.includes('文件版本已变化'));
    const request = boundary.calls.find((call) => call.url.endsWith('/revert'));
    assert.equal(JSON.parse(request.options.body).version, 'v1');
    assert.match(document.body.textContent, /版本已变化/);
    assert.equal(boundary.status.files.length, 1);
  });
});

test('旧版本的成功不展示为当前代码通过，验证期间禁用编辑和重复执行', async () => {
  await mounted({}, async (cache) => {
    const update = async (verification) =>
      setStatus(cache, {
        ...boundary.status,
        verification_current: false,
        verification,
      });
    await update({ id: 'job-1', revision: 0, status: 'passed', steps: [], error: '' });
    assert.match(document.querySelector('[role="status"]').textContent, /代码已修改，需重新验证/);
    await update({ id: 'job-2', revision: 1, status: 'testing', steps: [], error: '' });
    assert.equal(button('编译与仿真验证').disabled, true);
    assert.equal(button('让 AI 修改').disabled, true);
    assert.equal(button('撤销此文件').disabled, true);
    assert.ok(button('停止验证'));
  });
});

test('未创建对话的入口只准备修改请求，不请求不存在的副本', async () => {
  let requested = 0;
  await mounted({ threadId: '', onRequest: () => requested++ }, async () => {
    await click('开始描述修改要求');
    assert.equal(requested, 1);
    assert.deepEqual(boundary.calls, []);
  });
});

test('成功撤销后刷新文件清单，失败日志可以展开查看', async () => {
  await mounted({}, async (cache) => {
    await setStatus(cache, {
      ...boundary.status,
      verification_current: true,
      verification: {
        id: 'failed-job',
        revision: 1,
        status: 'failed',
        error: '编译未通过',
        steps: [
          { name: '编译', status: 'failed', log: 'Example.cs(3): error CS1002', exit_code: 1 },
        ],
      },
    });
    assert.match(document.querySelector('.code-verification pre').textContent, /CS1002/);
    assert.match(document.querySelector('[role="status"]').textContent, /验证失败/);
    await click('撤销此文件');
    await click('确认撤销');
    await until(() => document.body.textContent.includes('尚无代码修改'));
    assert.match(document.body.textContent, /尚无代码修改/);
  });
});
