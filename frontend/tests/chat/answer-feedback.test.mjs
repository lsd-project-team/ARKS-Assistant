import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';
import { act, createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', {
  url: 'http://localhost',
});
for (const key of [
  'window',
  'document',
  'navigator',
  'HTMLElement',
  'HTMLInputElement',
  'HTMLTextAreaElement',
  'HTMLFormElement',
  'HTMLSelectElement',
  'Element',
  'Node',
  'NodeFilter',
  'MutationObserver',
  'CustomEvent',
  'Event',
  'FocusEvent',
  'DocumentFragment',
  'Document',
  'SVGElement',
  'HTMLButtonElement',
  'KeyboardEvent',
  'PointerEvent',
  'MouseEvent',
  'getComputedStyle',
]) {
  Object.defineProperty(globalThis, key, { value: dom.window[key], configurable: true });
}
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
globalThis.requestAnimationFrame = (callback) => setTimeout(callback, 0);
globalThis.cancelAnimationFrame = clearTimeout;
dom.window.HTMLElement.prototype.scrollIntoView = () => {};
const { createRoot } = await import('react-dom/client');
const environment = { request: async () => ({}), toasts: [] };
const compiled = await build({
  stdin: {
    contents: `export { FeedbackDialog } from './src/features/chat/components/FeedbackDialog';
      export { AnswerFeedbackList } from './src/features/admin/AnswerFeedbackList';`,
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
      name: 'feedback-external-boundaries',
      setup(builder) {
        builder.onResolve({ filter: /\/(app\/api\/client|utils\/toasts)$/ }, ({ path }) => ({
          path: path.endsWith('/toasts') ? 'toasts' : 'api',
          namespace: 'feedback-boundary',
        }));
        builder.onLoad({ filter: /.*/, namespace: 'feedback-boundary' }, ({ path }) => ({
          contents:
            path === 'api'
              ? 'export const api = (...args) => environment.request(...args); export const jsonBody = JSON.stringify;'
              : 'export const toast = (value) => environment.toasts.push(value);',
        }));
      },
    },
  ],
});
const bundled = { exports: {} };
new Function('require', 'module', 'exports', 'environment', compiled.outputFiles[0].text)(
  createRequire(import.meta.url),
  bundled,
  bundled.exports,
  environment,
);
const { FeedbackDialog, AnswerFeedbackList } = bundled.exports;
const target = { messageId: 'old-answer', threadId: 'thread-a', projectId: 'project-a' };

async function mounted(verify) {
  const root = createRoot(document.getElementById('root'));
  let closed = 0;
  environment.toasts = [];
  try {
    await act(async () =>
      root.render(
        createElement(FeedbackDialog, {
          target,
          onClose: () => {
            closed++;
          },
        }),
      ),
    );
    const form = document.querySelector('form');
    const textarea = form.querySelector('textarea');
    const submit = form.querySelector('[type="submit"]');
    await verify({ form, textarea, submit, closed: () => closed });
  } finally {
    await act(async () => root.unmount());
  }
}

async function fill(textarea, value) {
  await act(async () => {
    Object.getOwnPropertyDescriptor(dom.window.HTMLTextAreaElement.prototype, 'value').set.call(
      textarea,
      value,
    );
    textarea.dispatchEvent(new dom.window.Event('input', { bubbles: true }));
  });
}
async function submitForm(form, times = 1) {
  await act(async () => {
    for (let i = 0; i < times; i++) {
      form.dispatchEvent(new dom.window.Event('submit', { bubbles: true, cancelable: true }));
    }
  });
}

test('空白说明不能提交，表单有可选分类和2000字限制', async () => {
  let requests = 0;
  environment.request = async () => {
    requests++;
  };
  await mounted(async ({ form, textarea, submit }) => {
    assert.equal(submit.disabled, true);
    assert.equal(textarea.maxLength, 2000);
    assert.equal(textarea.required, true);
    assert.equal(
      document.querySelector('[role="combobox"]').getAttribute('aria-label'),
      '问题类型（选填）',
    );
    await fill(textarea, ' \n ');
    await submitForm(form);
    assert.equal(requests, 0);
    assert.match(document.querySelector('[role="alert"]').textContent, /请填写/);
  });
});

test('提交固定回答和项目，等待时阻止重复提交和关闭，成功提示并关闭', async () => {
  const requests = [];
  let finish;
  environment.request = (...args) => {
    requests.push(args);
    return new Promise((resolve) => {
      finish = resolve;
    });
  };
  await mounted(async ({ form, textarea, submit, closed }) => {
    await fill(textarea, '原回答第一步有误');
    await submitForm(form, 2);
    assert.equal(requests.length, 1);
    assert.equal(requests[0][0], '/threads/thread-a/messages/old-answer/feedback');
    assert.equal(requests[0][2], 'project-a');
    const body = JSON.parse(requests[0][1].body);
    assert.equal(body.content, '原回答第一步有误');
    assert.equal(body.category, '');
    assert.match(body.submission_id, /^[0-9a-f-]{36}$/);
    assert.equal(submit.textContent, '正在提交…');
    assert.equal(submit.disabled, true);
    assert.equal(textarea.disabled, true);
    await act(async () => document.querySelector('[aria-label="关闭"]').click());
    assert.equal(closed(), 0);
    await act(async () => finish({ id: body.submission_id }));
    assert.deepEqual(environment.toasts, ['反馈已提交']);
    assert.equal(closed(), 1);
  });
});

test('网络失败保留输入，重试复用提交编号并正常完成', async () => {
  const requests = [];
  environment.request = async (...args) => {
    requests.push(JSON.parse(args[1].body));
    if (requests.length === 1) throw new Error('网络连接失败');
    return {};
  };
  await mounted(async ({ form, textarea, submit, closed }) => {
    await fill(textarea, '请补充异常流程');
    await submitForm(form);
    assert.equal(textarea.value, '请补充异常流程');
    assert.equal(submit.disabled, false);
    assert.equal(closed(), 0);
    assert.equal(document.querySelector('[role="alert"]').textContent, '网络连接失败');
    await submitForm(form);
    assert.equal(requests.length, 2);
    assert.equal(requests[0].submission_id, requests[1].submission_id);
    assert.equal(closed(), 1);
  });
});

test('失败后修改说明生成新提交编号，超长文本不会发请求', async () => {
  const requests = [];
  environment.request = async (...args) => {
    requests.push(JSON.parse(args[1].body));
    throw new Error('暂时不可用');
  };
  await mounted(async ({ form, textarea }) => {
    await fill(textarea, '第一次说明');
    await submitForm(form);
    await fill(textarea, '第二次说明');
    await submitForm(form);
    assert.notEqual(requests[0].submission_id, requests[1].submission_id);
    await fill(textarea, '字'.repeat(2001));
    await submitForm(form);
    assert.equal(requests.length, 2);
  });
});

test('取消直接关闭，不提交任何反馈', async () => {
  let requests = 0;
  environment.request = async () => {
    requests++;
  };
  await mounted(async ({ form, closed }) => {
    await act(async () => form.querySelector('.modal-footer [type="button"]').click());
    assert.equal(closed(), 1);
    assert.equal(requests, 0);
  });
});

test('管理员反馈展示保留换行并转义用户输入，空列表无占位', () => {
  assert.equal(renderToStaticMarkup(createElement(AnswerFeedbackList, { items: [] })), '');
  const markup = renderToStaticMarkup(
    createElement(AnswerFeedbackList, {
      items: [
        {
          id: 'feedback-a',
          actor: { display_name: '工程师甲' },
          created_at: '2026-11-04T03:00:00Z',
          category: 'source',
          content: '<script>alert(1)</script>\n请核对引用',
          message_id: 'old-answer',
        },
      ],
    }),
  );
  assert.match(markup, /工程师甲/);
  assert.match(markup, /来源有误/);
  assert.match(markup, /&lt;script&gt;alert\(1\)&lt;\/script&gt;\n请核对引用/);
  assert.doesNotMatch(markup, /<script>/);
});
