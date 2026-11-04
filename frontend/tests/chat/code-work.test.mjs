import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';
import { act, createElement } from 'react';
const { QueryClient, QueryClientProvider } = createRequire(import.meta.url)(
  '@tanstack/react-query',
);

const dom = new JSDOM('<!doctype html><div id="root"></div>');
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const { createRoot } = await import('react-dom/client');
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
          { filter: /(app\/api\/client|auth\/AuthContext|shared\/ui\/ui|CodeDiffView)$/ },
          ({ path }) => ({ path, namespace: 'test-boundary' }),
        );
        builder.onLoad({ filter: /.*/, namespace: 'test-boundary' }, ({ path }) => ({
          loader: 'jsx',
          resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
          contents: path.endsWith('CodeDiffView')
            ? 'export default function CodeDiffView({diff}) { return <pre aria-label="代码差异">{diff.diff}</pre>; }'
            : path.endsWith('AuthContext')
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

async function mounted(props, verify, setup = () => {}) {
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
    if (url.includes('/diff?')) {
      return {
        ...structuredClone(boundary.diff),
        path: new URL(url, 'http://test').searchParams.get('path'),
      };
    }
    if (url.endsWith('/revert')) {
      const body = JSON.parse(options.body);
      if (body.version !== boundary.diff.version) throw new Error('文件版本已变化，请刷新');
      boundary.status = { ...boundary.status, revision: 2, files: [] };
    }
    return structuredClone(boundary.status);
  };
  setup();
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
        () =>
          document.querySelector('[aria-label="代码差异"]')?.textContent.trim() === '-old\n+new',
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
    assert.equal(
      document.querySelector('[aria-label="代码差异"]').textContent.trim(),
      '-old\n+new',
    );
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
    assert.match(
      document.querySelector('[role="status"]').textContent,
      /代码或测试已修改，需重新验证/,
    );
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
    await until(() => document.body.textContent.includes('尚无待合入的代码修改'));
    assert.match(document.body.textContent, /尚无待合入的代码修改/);
  });
});

const change = async (element, value) => {
  await act(async () => {
    const prototype =
      element.tagName === 'TEXTAREA'
        ? window.HTMLTextAreaElement.prototype
        : window.HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(prototype, 'value').set.call(element, value);
    element.dispatchEvent(new window.Event('input', { bubbles: true }));
    element.dispatchEvent(new window.Event('change', { bubbles: true }));
  });
};

test('删除块反馈保留旧行范围、版本与草稿，撤销须确认精确修改块', async () => {
  const requests = [];
  await mounted(
    { onRequest: (text) => requests.push(text) },
    async () => {
      await click('反馈此处');
      assert.match(document.querySelector('.code-review-comment').textContent, /修改前 L2–2/);
      await change(document.querySelector('[aria-label="差异反馈说明"]'), '请保留这个分支');
      await click('带入聊天输入框');
      assert.equal(requests.length, 1);
      assert.match(requests[0], /文件：AKRS.ZX2200\/Main\/Example.cs/);
      assert.match(requests[0], /所查看版本：v1/);
      assert.match(requests[0], /修改前第 2–2 行/);
      assert.match(requests[0], /removed/);
      await click('撤销此块');
      assert.equal(
        boundary.calls.some((call) => call.url.endsWith('/revert-hunk')),
        false,
      );
      await click('确认撤销');
      const call = boundary.calls.find((call) => call.url.endsWith('/revert-hunk'));
      assert.deepEqual(JSON.parse(call.options.body), {
        path,
        version: 'v1',
        hunk_id: 'hunk-exact',
      });
    },
    () => {
      boundary.diff.before = 'kept\nremoved\n';
      boundary.diff.after = 'kept\n';
      boundary.diff.hunks = [
        {
          id: 'hunk-exact',
          old_start: 2,
          old_lines: 1,
          new_start: 1,
          new_lines: 0,
          before: 'removed\n',
          after: '',
        },
      ];
    },
  );
});

const mergeSetup = (admin = true, conflict = false) => {
  boundary.role = admin ? 'admin' : 'user';
  boundary.status.merge_plan_id = 'plan-id';
  boundary.status.merge_paths = [path];
  const previous = boundary.api;
  boundary.api = async (url, options, project) => {
    if (url.includes('/merge/') && !url.endsWith('/diff?')) {
      if (url.includes('/diff?'))
        return {
          ...boundary.diff,
          base: 'baseline',
          source: 'source',
          workspace: 'workspace',
          status: conflict ? 'conflict' : 'ready',
        };
      if (!options) {
        return {
          id: 'plan-id',
          target: 'C:\\test-original',
          revision: 1,
          status: 'preview',
          files: [{ path, status: conflict ? 'conflict' : 'ready', kind: 'modified' }],
          conflicts: conflict ? [path] : [],
          rebase_conflicts: [],
          can_apply: !conflict,
          verification: { id: 'job', revision: 1, status: 'passed', steps: [] },
        };
      }
      boundary.calls.push({ url, options, project });
      return structuredClone(boundary.status);
    }
    return previous(url, options, project);
  };
};

test('只有管理员明确确认已验证目标后可写回；改变冲突处理必须重新预览', async () => {
  await mounted(
    {},
    async () => {
      await click('合并');
      await until(() => button('确认应用到原工程'));
      assert.equal(button('确认应用到原工程').disabled, true);
      const confirm = document.querySelector('.code-work-checkbox input');
      await act(async () => confirm.click());
      assert.equal(button('确认应用到原工程').disabled, false);
      await click('确认应用到原工程');
      const request = boundary.calls.find((call) => call.url.endsWith('/apply'));
      assert.deepEqual(JSON.parse(request.options.body), { confirm_target: 'C:\\test-original' });
    },
    () => mergeSetup(),
  );
  await mounted(
    {},
    async () => {
      await click('合并');
      await until(() => document.querySelector('.code-conflict-resolution select'));
      assert.equal(button('验证合并结果').disabled, true);
      await act(async () => {
        const select = document.querySelector('.code-conflict-resolution select');
        select.value = 'workspace';
        select.dispatchEvent(new window.Event('change', { bubbles: true }));
      });
      assert.ok(button('按冲突处理重新预览'));
      assert.equal(button('验证合并结果').disabled, true);
      assert.equal(button('确认应用到原工程').disabled, true);
    },
    () => mergeSetup(true, true),
  );
});

test('普通用户可审查合并，不能出现写回入口；恢复冲突阻止编辑', async () => {
  await mounted(
    {},
    async (cache) => {
      await click('合并');
      await until(() => document.body.textContent.includes('写回原工程由管理员执行'));
      assert.equal(button('确认应用到原工程'), undefined);
      await setStatus(cache, {
        ...boundary.status,
        recovery: [
          {
            id: 'recover',
            target: 'C:\\test-original',
            files: [{ path, version: 'human-version', before: 'old', after: 'new' }],
          },
        ],
      });
      assert.match(document.body.textContent, /请管理员核对并确认结束恢复/);
      assert.equal(button('编译与仿真验证').disabled, true);
      assert.equal(button('让 AI 修改').disabled, true);
    },
    () => mergeSetup(false),
  );
});

test('需求测试更新带原版本，失败保留表单内容', async () => {
  await mounted(
    {},
    async () => {
      await click('验证');
      await click('查看/编辑');
      assert.equal(document.querySelector('form textarea').value, '必须只执行一次');
      await click('保存测试');
      await until(() => document.body.textContent.includes('用例已更新'));
      assert.equal(document.querySelector('form textarea').value, '必须只执行一次');
      const request = boundary.calls.find((call) => call.url.endsWith('/requirement'));
      assert.equal(JSON.parse(request.options.body).version, 'case-version');
    },
    () => {
      boundary.status.requirements = [
        {
          id: 'case-id',
          version: 'case-version',
          name: '重复操作',
          expectation: '必须只执行一次',
          code: 'Check(true,"call");',
          enabled: true,
        },
      ];
      const previous = boundary.api;
      boundary.api = async (url, options, project) => {
        if (url.endsWith('/requirement')) {
          boundary.calls.push({ url, options, project });
          throw new Error('用例已更新');
        }
        return previous(url, options, project);
      };
    },
  );
});

test('从摘要点击指定文件时直接展示并撤销该文件，不跳到首个文件', async () => {
  const other = 'AKRS.ZX2200/Main/Second.cs';
  await mounted(
    { initialPath: other },
    async () => {
      assert.equal(document.querySelector('.code-work-file-heading strong').textContent, other);
      const reads = boundary.calls.filter((call) => call.url.includes('/diff?'));
      assert.ok(reads.length > 0);
      assert.ok(
        reads.every((call) => new URL(call.url, 'http://test').searchParams.get('path') === other),
      );
      await click('撤销此文件');
      await click('确认撤销');
      const request = boundary.calls.find((call) => call.url.endsWith('/revert'));
      assert.equal(JSON.parse(request.options.body).path, other);
    },
    () => boundary.status.files.push({ path: other, kind: 'modified', version: 'v1' }),
  );
});
