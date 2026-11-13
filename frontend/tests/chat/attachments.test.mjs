import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';
import { JSDOM } from 'jsdom';
import { act, createElement, useRef } from 'react';
import {
  attachmentError,
  ACCEPTED_ATTACHMENTS,
  clipboardImages,
  isImageAttachment,
  MAX_FILE_SIZE,
} from '../../src/features/chat/attachments/files.ts';

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
  'Element',
  'Node',
  'Event',
  'MouseEvent',
]) {
  Object.defineProperty(globalThis, key, { value: dom.window[key], configurable: true });
}
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const { createRoot } = await import('react-dom/client');
const environment = {
  state: { drafts: {}, projectId: 'p1' },
  request: async () => ({}),
  calls: [],
  element: createElement,
};
const compiled = await build({
  stdin: {
    contents: `export { useAttachments } from './src/features/chat/attachments/useAttachments'; export { ChatComposer } from './src/features/chat/components/ChatComposer'; export { AttachmentList } from './src/features/chat/attachments/AttachmentList';`,
    resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
    loader: 'tsx',
  },
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  loader: { '.css': 'empty' },
  jsx: 'automatic',
  plugins: [
    {
      name: 'attachment-boundaries',
      setup(builder) {
        builder.onResolve(
          { filter: /\/(app\/api\/client|app\/state\/store|shared\/ui\/ui)$/ },
          ({ path }) => ({ path, namespace: 'attachment-test' }),
        );
        builder.onLoad({ filter: /.*/, namespace: 'attachment-test' }, ({ path }) => ({
          contents: path.endsWith('/client')
            ? 'export const api = (...args) => { environment.calls.push(args); return environment.request(...args); }; export const apiUrl = (path, project) => "/api/projects/" + project + path;'
            : path.endsWith('/store')
              ? `export const draftKey = (thread, project) => thread || (project ? 'new:' + project : 'new'); export const useWorkspace = Object.assign((selector) => selector(environment.state), { getState: () => environment.state, setState: (change) => { environment.state = { ...environment.state, ...change(environment.state) }; } });`
              : `export const Button = (props) => environment.element('button', props); export const Modal = (props) => environment.element('div', { 'data-modal': props.title }, props.children); export const ErrorText = () => null;`,
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
const { useAttachments, ChatComposer, AttachmentList } = bundled.exports;
let uploader;
function Harness({ project = 'p1', thread = 't1' }) {
  uploader = useAttachments(project, thread);
  return createElement('span', null, uploader.busy ? 'uploading' : 'ready');
}
const fakeFile = (name) => ({ name, size: 10 });
const metadata = (id) => ({
  id,
  filename: id + '.md',
  sha256: 'a'.repeat(64),
  size: 10,
  characters: 8,
  parse_status: 'readable',
  parse_notes: '按行读取',
});

async function mounted(verify) {
  environment.state = { drafts: {}, projectId: 'p1' };
  environment.calls = [];
  const root = createRoot(document.getElementById('root'));
  try {
    await act(async () => root.render(createElement(Harness)));
    await verify(root);
  } finally {
    await act(async () => root.unmount());
  }
}

test('所有约定格式及32MB边界通过，空文件和其他格式拒绝', () => {
  for (const extension of ACCEPTED_ATTACHMENTS.split(','))
    assert.equal(attachmentError({ name: '需求' + extension.toUpperCase(), size: 1 }), '');
  assert.equal(attachmentError({ name: 'limit.txt', size: MAX_FILE_SIZE }), '');
  assert.match(attachmentError({ name: 'large.txt', size: MAX_FILE_SIZE + 1 }), /32 MB/);
  assert.match(attachmentError({ name: 'empty.txt', size: 0 }), /不能为空/);
  assert.match(attachmentError({ name: 'old.doc', size: 1 }), /不支持/);
});

test('批量上传部分失败后继续，重试只提交失败项并保留原草稿', async () =>
  mounted(async () => {
    environment.state.drafts.t1 = { content: '依据文档修改', selections: [{ path: 'a.cs' }] };
    let failed = false;
    environment.request = async (path) => {
      if (path.includes('second') && !failed) {
        failed = true;
        throw new Error('临时失败');
      }
      return metadata(path.includes('first') ? 'one' : 'two');
    };
    await act(async () => uploader.upload([fakeFile('first.md'), fakeFile('second.xlsx')]));
    assert.equal(environment.state.drafts.t1.content, '依据文档修改');
    assert.equal(environment.state.drafts.t1.selections[0].path, 'a.cs');
    assert.deepEqual(
      environment.state.drafts.t1.attachments.map((item) => item.id),
      ['one'],
    );
    assert.equal(uploader.jobs.length, 1);
    assert.match(uploader.jobs[0].error, /临时失败/);
    await act(async () => uploader.upload([uploader.jobs[0].file], uploader.jobs[0].id));
    assert.equal(environment.calls.length, 3);
    assert.deepEqual(
      environment.state.drafts.t1.attachments.map((item) => item.id),
      ['one', 'two'],
    );
    assert.equal(uploader.jobs.length, 0);
    assert.equal(environment.calls[0][1].headers['Content-Type'], 'application/octet-stream');
  }));

test('异步上传切换会话后仍落在原草稿，保留期间新增输入', async () =>
  mounted(async (root) => {
    let finish;
    environment.request = () =>
      new Promise((resolve) => {
        finish = resolve;
      });
    let pending;
    await act(async () => {
      pending = uploader.upload([fakeFile('old.md')]);
    });
    await act(async () => root.render(createElement(Harness, { project: 'p2', thread: 't2' })));
    environment.state.drafts.t1 = { content: '上传期间继续输入', selections: [] };
    environment.state.drafts.t2 = { content: '另一会话', selections: [] };
    await act(async () => {
      finish(metadata('old'));
      await pending;
    });
    assert.equal(environment.state.drafts.t1.content, '上传期间继续输入');
    assert.equal(environment.state.drafts.t1.attachments[0].id, 'old');
    assert.equal(environment.state.drafts.t2.attachments, undefined);
  }));

test('同步重复触发不会上传两遍，移除附件保留正文', async () =>
  mounted(async () => {
    let finish;
    environment.request = () =>
      new Promise((resolve) => {
        finish = resolve;
      });
    environment.state.drafts.t1 = { content: '保留', selections: [] };
    let pending;
    await act(async () => {
      pending = uploader.upload([fakeFile('one.md')]);
      await uploader.upload([fakeFile('two.md')]);
    });
    assert.equal(environment.calls.length, 1);
    await act(async () => {
      finish(metadata('one'));
      await pending;
    });
    await act(async () => uploader.remove('one'));
    assert.equal(environment.state.drafts.t1.content, '保留');
    assert.deepEqual(environment.state.drafts.t1.attachments, []);
  }));

test('超过10个附件及无效格式不发送请求', async () =>
  mounted(async () => {
    environment.state.drafts.t1 = {
      content: '需求',
      selections: [],
      attachments: Array.from({ length: 10 }, (_, index) => metadata(String(index))),
    };
    await act(async () => uploader.upload([fakeFile('more.md'), fakeFile('old.doc')]));
    assert.equal(environment.calls.length, 0);
    assert.equal(uploader.jobs.length, 2);
    assert.match(uploader.jobs[0].error, /10/);
    assert.match(uploader.jobs[1].error, /不支持/);
  }));

test('上传解析期间允许输入，发送按钮被禁用以避免漏发附件', async () => {
  const root = createRoot(document.getElementById('root'));
  function Composer() {
    return createElement(ChatComposer, {
      inputRef: useRef(null),
      draft: '按文档修改',
      onChange() {},
      onSend() {},
      onCommand() {},
      onStop() {},
      onUploadFiles() {},
      sending: false,
      uploading: true,
      busy: false,
      stopping: false,
      canContext: false,
      canCompact: false,
      compactDisabledReason: '',
      model: 'test',
      context: null,
    });
  }
  try {
    await act(async () => root.render(createElement(Composer)));
    assert.equal(document.querySelector('textarea').disabled, false);
    assert.equal(document.querySelector('[aria-label="发送消息"]').disabled, true);
  } finally {
    await act(async () => root.unmount());
  }
});

test('图片格式可选，粘贴截图生成可辨认文件名', () => {
  assert.equal(attachmentError({ name: '报错.PNG', size: 1024 }), '');
  assert.equal(attachmentError({ name: '现场.JPG', size: 1024 }), '');
  assert.equal(attachmentError({ name: '动图.gif', size: 1024 }), '');
  assert.equal(isImageAttachment({ name: 'a.webp' }), true);
  assert.equal(isImageAttachment({ name: '说明.txt' }), false);
  assert.equal(isImageAttachment({ name: '没有扩展名', kind: 'image' }), true);
  const pasted = clipboardImages(
    [new File([new Uint8Array([1])], 'image.png', { type: 'image/png' })],
    new Date(2026, 10, 13, 9, 5, 7),
  );
  assert.equal(pasted[0].name, '截图-20261113-090507.png');
  const pair = clipboardImages(
    [
      new File([new Uint8Array([1])], 'image.png', { type: 'image/png' }),
      new File([new Uint8Array([1])], 'blob', { type: 'image/jpeg' }),
    ],
    new Date(2026, 10, 13, 9, 5, 7),
  );
  assert.deepEqual(
    pair.map((file) => file.name),
    ['截图-20261113-090507.png', '截图-20261113-090507-2.jpg'],
  );
  assert.equal(clipboardImages([new File(['text'], 'a.txt', { type: 'text/plain' })]).length, 0);
});

test('图片附件显示缩略图并打开原图预览', async () => {
  environment.state = { drafts: {}, projectId: 'p1' };
  const image = {
    ...metadata('img1'),
    filename: '报错截图.png',
    kind: 'image',
  };
  const root = createRoot(document.getElementById('root'));
  try {
    await act(async () => root.render(createElement(AttachmentList, { attachments: [image] })));
    const thumb = document.querySelector('img.attachment-thumb');
    assert.ok(thumb);
    assert.match(thumb.getAttribute('src'), /\/attachments\/img1\/image$/);
    assert.match(document.querySelector('.chat-attachment small').textContent, /图片/);
    await act(async () => document.querySelector('.attachment-name').click());
    const preview = document.querySelector('img.attachment-preview-image');
    assert.ok(preview);
    assert.match(preview.getAttribute('src'), /\/attachments\/img1\/image$/);
  } finally {
    await act(async () => root.unmount());
  }
});

test('粘贴图片交给上传，纯文字粘贴不受影响', async () => {
  const pasted = [];
  const root = createRoot(document.getElementById('root'));
  function Composer() {
    return createElement(ChatComposer, {
      inputRef: useRef(null),
      draft: '',
      onChange() {},
      onSend() {},
      onCommand() {},
      onStop() {},
      onUploadFiles() {},
      onPasteFiles: (files) => pasted.push(...files),
      sending: false,
      uploading: false,
      busy: false,
      stopping: false,
      canContext: false,
      canCompact: false,
      model: 'test',
      context: null,
    });
  }
  try {
    await act(async () => root.render(createElement(Composer)));
    const textarea = document.querySelector('textarea');
    const image = new File([new Uint8Array([1])], 'image.png', { type: 'image/png' });
    const paste = new dom.window.Event('paste', { bubbles: true });
    Object.defineProperty(paste, 'clipboardData', { value: { files: [image] } });
    await act(async () => textarea.dispatchEvent(paste));
    assert.equal(pasted.length, 1);
    const plain = new dom.window.Event('paste', { bubbles: true });
    Object.defineProperty(plain, 'clipboardData', { value: { files: [] } });
    await act(async () => textarea.dispatchEvent(plain));
    assert.equal(pasted.length, 1);
  } finally {
    await act(async () => root.unmount());
  }
});
