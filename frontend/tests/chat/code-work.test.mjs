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
            ? 'export default function CodeDiffView({diff,split,wrap,onSelect}) { boundary.select = onSelect; return <pre aria-label="代码差异" data-split={split} data-wrap={wrap}>{diff.diff}</pre>; }'
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
  boundary.select = null;
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
    if (url.includes('/summary'))
      return {
        exists: true,
        revision: boundary.status.revision,
        additions: boundary.status.files.length * 2,
        deletions: boundary.status.files.length,
        files: boundary.status.files.map((file) => ({ ...file, additions: 2, deletions: 1 })),
      };
    if (url.includes('/diff?')) {
      const target = new URL(url, 'http://test').searchParams.get('path');
      return {
        ...structuredClone(boundary.diff),
        path: target,
        version:
          boundary.status.files.find((file) => file.path === target)?.version ??
          boundary.diff.version,
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
  Array.from(document.querySelectorAll('button')).find(
    (node) => node.textContent === text || node.getAttribute('aria-label') === text,
  );
const click = async (text) => {
  if (!button(text)) {
    await act(async () => {
      const trigger =
        text === '撤销此文件'
          ? document
              .querySelector('.code-review-file-content:not([hidden])')
              ?.closest('.code-review-file')
              .querySelector('[aria-haspopup="menu"]')
          : button('更多变更操作');
      trigger?.click();
    });
  }
  assert.ok(button(text), `button: ${text}`);
  await act(async () => {
    const details = button(text).closest('details');
    if (details && !details.open) details.querySelector('summary').click();
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

test('默认集中展示单个文件差异，次级信息按需打开且不会触发写入', async () => {
  await mounted({}, async () => {
    assert.equal(document.querySelector('nav[aria-label="修改文件"]'), null);
    assert.equal(document.querySelectorAll('.code-review-file').length, 1);
    assert.equal(document.querySelector('.code-work-options-menu'), null);
    assert.equal(document.querySelector('.code-verification'), null);
    assert.equal(document.querySelector('.code-review-comment'), null);
    assert.equal(document.querySelector('.code-work-locations'), null);
    assert.equal(document.querySelector('[aria-label="代码差异"]').dataset.split, 'true');
    assert.equal(document.querySelector('[aria-label="变更范围"]').value, '');
    assert.equal(document.querySelector('[role="status"]').textContent, '尚未验证');
    assert.equal(document.querySelectorAll('.code-review-top-actions button').length, 4);
    assert.equal(button('刷新变更'), undefined);
    assert.equal(button(`复制文件路径：${path}`), undefined);
    await click('更多变更操作');
    assert.equal(button('验证详情'), undefined);
    assert.equal(button('让 AI 修改'), undefined);
    assert.equal(button('收起全部文件'), undefined);
    assert.ok(button('切换为统一差异'));
    assert.ok(button('开启自动换行'));
    await click('工程信息');
    assert.match(document.body.textContent, /当前副本版本 1/);
    assert.ok(document.querySelector('.code-work-locations'));
    await click('返回变更');
    await click('历史');
    assert.match(document.querySelector('.code-review-page-title').textContent, /修改历史/);
    await click('返回变更');
    assert.equal(document.querySelectorAll('.code-review-file').length, 1);
    assert.ok(boundary.calls.every(({ options }) => !options?.method || options.method === 'GET'));
  });
});

test('更多菜单支持方向键、Escape 和外部关闭，Escape 不会连带关闭面板', async () => {
  let closed = 0;
  await mounted({ embedded: true, onClose: () => closed++ }, async () => {
    await click('更多变更操作');
    const menu = document.querySelector('[role="menu"]');
    const first = menu.querySelector('button');
    assert.equal(document.activeElement, first);
    const key = async (target, value) =>
      act(async () =>
        target.dispatchEvent(
          new window.KeyboardEvent('keydown', {
            key: value,
            bubbles: true,
            cancelable: true,
          }),
        ),
      );
    await key(first, 'ArrowDown');
    assert.equal(document.activeElement.textContent, '开启自动换行');
    await key(document.activeElement, 'End');
    assert.equal(document.activeElement.textContent, '工程信息');
    await key(document.activeElement, 'Escape');
    assert.equal(document.querySelector('[role="menu"]'), null);
    assert.equal(document.activeElement, button('更多变更操作'));
    assert.equal(closed, 0);
    await click('更多变更操作');
    await act(async () =>
      document.body.dispatchEvent(new window.Event('pointerdown', { bubbles: true })),
    );
    assert.equal(document.querySelector('[role="menu"]'), null);
  });
});

test('文件连续排列并延迟读取，统一控制左右对照、换行和展开收起', async () => {
  const second = 'AKRS.ZX2200/Controllers/Valve.cs';
  await mounted(
    { initialPath: second },
    async () => {
      const rows = document.querySelectorAll('.code-review-file');
      assert.equal(rows.length, 2);
      assert.equal(rows[0].querySelector('[aria-expanded]').getAttribute('aria-expanded'), 'false');
      assert.equal(rows[1].querySelector('[aria-expanded]').getAttribute('aria-expanded'), 'true');
      assert.ok(
        boundary.calls
          .filter(({ url }) => url.includes('/diff?'))
          .every(({ url }) => url.includes(encodeURIComponent(second))),
      );
      await until(() => document.querySelector('.code-review-scope-pill .code-review-counts'));
      assert.equal(
        document
          .querySelector('.code-review-scope-pill .code-review-counts')
          .getAttribute('aria-label'),
        '新增 4 行，删除 2 行',
      );
      assert.equal(
        rows[1].querySelector('.code-review-counts').getAttribute('aria-label'),
        '新增 2 行，删除 1 行',
      );
      await click(`查看修改文件：${path}`);
      await until(() => document.querySelectorAll('[aria-label="代码差异"]').length === 2);
      await click('切换为统一差异');
      assert.ok(
        [...document.querySelectorAll('[aria-label="代码差异"]')].every(
          (node) => node.dataset.split === 'false',
        ),
      );
      await click('开启自动换行');
      assert.ok(
        [...document.querySelectorAll('[aria-label="代码差异"]')].every(
          (node) => node.dataset.wrap === 'true',
        ),
      );
      await click('收起全部文件');
      assert.equal(document.querySelectorAll('.code-review-file-content:not([hidden])').length, 0);
      await click('展开全部文件');
      assert.equal(document.querySelectorAll('.code-review-file-content:not([hidden])').length, 2);
      await click('切换为左右对照');
      await click('关闭自动换行');
      assert.ok(
        [...document.querySelectorAll('[aria-label="代码差异"]')].every(
          (node) => node.dataset.split === 'true' && node.dataset.wrap === 'false',
        ),
      );
    },
    () => boundary.status.files.push({ path: second, version: 'second-v2', kind: 'modified' }),
  );
});

test('轮次选择使用独立快照及统计，切回累计后恢复可撤销的当前文件', async () => {
  await mounted(
    {},
    async () => {
      const scope = document.querySelector('select[aria-label="变更范围"]');
      assert.equal(
        [...scope.options].find((option) => option.textContent === '上一轮').value,
        'last-turn',
      );
      assert.equal([...scope.options].filter((option) => option.value === 'last-turn').length, 1);
      await act(async () => {
        scope.value = 'last-turn';
        scope.dispatchEvent(new window.Event('change', { bubbles: true }));
      });
      await until(
        () =>
          document.querySelector('[aria-label="代码差异"]')?.textContent ===
          '-snapshot-before\n+snapshot-after',
      );
      assert.equal(
        document
          .querySelector('.code-review-scope-pill .code-review-counts')
          .getAttribute('aria-label'),
        '新增 7 行，删除 3 行',
      );
      await click(`文件操作：${path}`);
      assert.ok(button('复制路径'));
      assert.equal(button('撤销此文件'), undefined);
      assert.equal(button('编译与仿真验证'), undefined);
      await act(async () => {
        scope.value = '';
        scope.dispatchEvent(new window.Event('change', { bubbles: true }));
      });
      await until(
        () => document.querySelector('[aria-label="代码差异"]')?.textContent === '-old\n+new',
      );
      await click('撤销此文件');
      await click('确认撤销');
      const request = boundary.calls.find((call) => call.url.endsWith('/revert'));
      assert.deepEqual(JSON.parse(request.options.body), { path, version: 'v1' });
    },
    () => {
      boundary.status.history = [
        { id: '3', run_id: 'last-turn', revision: 3, files: [path] },
        { id: 'old', run_id: 'old-turn', revision: 1, files: [path] },
        { id: '1', run_id: 'last-turn', revision: 1, files: [path] },
        { id: '2', run_id: 'last-turn', revision: 2, files: [path] },
      ];
      const previous = boundary.api;
      boundary.api = async (url, options, project) => {
        if (url.includes('run_id=last-turn')) {
          boundary.calls.push({ url, options, project });
          return url.includes('/summary')
            ? {
                exists: true,
                revision: 0,
                additions: 7,
                deletions: 3,
                files: [
                  { path, version: 'snapshot-v0', kind: 'modified', additions: 7, deletions: 3 },
                ],
              }
            : {
                ...boundary.diff,
                version: 'snapshot-v0',
                historical: true,
                run_id: 'last-turn',
                diff: '-snapshot-before\n+snapshot-after',
              };
        }
        return previous(url, options, project);
      };
    },
  );
});

test('不同文件版本的旧摘要不显示为当前增删统计', async () => {
  await mounted(
    {},
    async () => {
      assert.equal(document.querySelector('.code-review-scope-pill .code-review-counts'), null);
      assert.equal(document.querySelector('.code-review-file .code-review-counts'), null);
    },
    () => {
      const previous = boundary.api;
      boundary.api = async (url, options, project) => {
        const result = await previous(url, options, project);
        if (url.includes('/summary')) result.files[0].version = 'old-version';
        return result;
      };
    },
  );
});

test('一行验证状态保留停止与过期结果，基础回归不等同于需求验证通过', async () => {
  await mounted({}, async (cache) => {
    const job = { id: 'job', revision: 1, steps: [], error: '' };
    for (const [verification, current, expected] of [
      [{ ...job, status: 'cancelled' }, true, '验证已停止'],
      [{ ...job, status: 'failed' }, false, '需重新验证（上次失败）'],
      [{ ...job, status: 'passed' }, true, '基础回归通过'],
      [{ ...job, status: 'passed', requirements: [{ id: 'assertion' }] }, true, '验证通过'],
    ]) {
      await setStatus(cache, { ...boundary.status, verification, verification_current: current });
      assert.equal(document.querySelector('[role="status"]').textContent, expected);
      assert.equal(document.querySelector('.code-verification'), null);
    }
  });
});

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
    assert.match(document.querySelector('[role="status"]').textContent, /需重新验证/);
    assert.doesNotMatch(document.querySelector('[role="status"]').textContent, /验证通过/);
    await click('编译与仿真验证');
    assert.equal(boundary.calls.filter(({ url }) => url.endsWith('/verify')).length, 1);
    await update({ id: 'job-2', revision: 1, status: 'testing', steps: [], error: '' });
    assert.equal(button('编译与仿真验证'), undefined);
    assert.ok(button('停止验证'));
    await click(`文件操作：${path}`);
    assert.equal(button('撤销此文件').disabled, true);
    assert.ok(button('停止验证'));
    await click('停止验证');
    assert.equal(boundary.calls.filter(({ url }) => url.endsWith('/cancel')).length, 1);
    await update({ id: 'job-2', revision: 1, status: 'cancelled', steps: [], error: '' });
    assert.ok(button('编译与仿真验证'));
    assert.equal(button('停止验证'), undefined);
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

test('右侧变更区保留指定文件和历史轮次，不创建模态遮罩或允许历史撤销', async () => {
  const second = 'AKRS.ZX2200/Main/Second.cs';
  let closed = 0;
  await mounted(
    { embedded: true, initialPath: second, initialRunId: 'run-7', onClose: () => closed++ },
    async () => {
      assert.ok(document.querySelector('section[aria-label="代码变更"]'));
      assert.equal(document.querySelector('[role="dialog"], [aria-modal="true"]'), null);
      assert.equal(document.querySelector('.code-work-dialog'), null);
      assert.match(
        document
          .querySelector('.code-review-file-content:not([hidden])')
          .closest('.code-review-file').textContent,
        /Second.cs/,
      );
      assert.ok(
        boundary.calls.some(
          ({ url }) =>
            url.includes(`path=${encodeURIComponent(second)}`) && url.endsWith('run_id=run-7'),
        ),
      );
      await click(`文件操作：${second}`);
      assert.equal(button('撤销此文件'), undefined);
      await act(async () => document.querySelector('[aria-label="关闭代码变更"]').click());
      assert.equal(closed, 1);
    },
    () => boundary.status.files.push({ path: second, kind: 'modified', version: 'v2' }),
  );
});

test('右侧面板 Escape 可关闭，填写反馈时保留输入且运行中继续禁用编辑', async () => {
  let closed = 0;
  await mounted({ embedded: true, busy: true, onClose: () => closed++ }, async () => {
    await click(`文件操作：${path}`);
    assert.equal(button('撤销此文件').disabled, true);
    assert.equal(button('编译与仿真验证').disabled, true);
    const panel = document.querySelector('.code-work-pane');
    const input = document.createElement('textarea');
    input.value = '尚未提交的反馈';
    panel.append(input);
    await act(async () =>
      input.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true })),
    );
    assert.equal(closed, 0);
    assert.equal(input.value, '尚未提交的反馈');
    await act(async () =>
      panel.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true })),
    );
    assert.equal(closed, 1);
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
    assert.equal(document.querySelector('.code-verification'), null);
    assert.match(document.querySelector('[role="status"]').textContent, /验证失败/);
    await click('查看验证详情');
    assert.match(document.querySelector('.code-verification pre').textContent, /CS1002/);
    await click('返回变更');
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

test('移除修改块操作后仍可通过行号选区反馈，保留旧行范围与版本', async () => {
  const requests = [];
  await mounted(
    { onRequest: (text) => requests.push(text) },
    async () => {
      assert.equal(document.querySelector('[aria-label="修改块"]'), null);
      assert.equal(button('反馈此处'), undefined);
      assert.equal(button('撤销此块'), undefined);
      assert.equal(document.querySelector('.code-review-comment'), null);
      await act(async () => boundary.select({ start: 2, end: 2, side: 'deletions' }));
      assert.match(document.querySelector('.code-review-comment').textContent, /修改前 L2–2/);
      await change(document.querySelector('[aria-label="差异反馈说明"]'), '请保留这个分支');
      await click('带入聊天输入框');
      assert.equal(requests.length, 1);
      assert.match(requests[0], /^请先读取当前副本/);
      assert.match(requests[0], /文件：AKRS.ZX2200\/Main\/Example.cs/);
      assert.match(requests[0], /所查看版本：v1/);
      assert.match(requests[0], /修改前第 2–2 行/);
      assert.match(requests[0], /removed/);
      assert.ok(
        boundary.calls.every(({ options }) => !options?.method || options.method === 'GET'),
      );
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
    },
    () => mergeSetup(false),
  );
});

test('需求测试更新带原版本，失败保留表单内容', async () => {
  await mounted(
    {},
    async () => {
      await click('查看验证详情');
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
      const heading = document
        .querySelector('.code-review-file-content:not([hidden])')
        .closest('.code-review-file')
        .querySelector('strong');
      assert.equal(heading.textContent, 'Second.cs');
      assert.equal(heading.title, other);
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
