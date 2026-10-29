import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { build } from 'esbuild';

const storage = new Map();
globalThis.localStorage = {
  getItem: (key) => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, value),
  removeItem: (key) => storage.delete(key),
};
globalThis.window = { addEventListener() {}, removeEventListener() {} };
const environment = {
  createElement,
  states: [],
  cursor: 0,
  effects: [],
  cleanups: [],
  user: undefined,
  useState(initial) {
    const index = this.cursor++;
    if (!(index in this.states))
      this.states[index] = typeof initial === 'function' ? initial() : initial;
    return [
      this.states[index],
      (value) => {
        this.states[index] = typeof value === 'function' ? value(this.states[index]) : value;
      },
    ];
  },
  useEffect(effect) {
    const index = this.cursor++;
    if (!(index in this.states)) {
      this.states[index] = true;
      this.effects.push(effect);
    }
  },
};
// 仅隔离 React 调度、弹窗容器和 HTTP；执行真实表单、上传队列和重试逻辑。
const bundled = await build({
  entryPoints: [
    fileURLToPath(
      new URL('../../src/features/handover/materials/SourceImport.tsx', import.meta.url),
    ),
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
      name: 'source-import-boundaries',
      setup(builder) {
        const stubs = {
          react:
            'export const useState = (initial) => environment.useState(initial); export const useRef = (initial) => environment.useState(() => ({current:initial}))[0]; export const useEffect = (effect) => environment.useEffect(effect);',
          modal:
            'export const HandoverModal = ({children, footer}) => environment.createElement("form", null, children, footer);',
          ui: 'export const Button = "button"; export const ErrorText = ({error}) => error ? environment.createElement("p", {role:"alert"}, String(error)) : null;',
          auth: 'export const useAuth = () => ({session: environment.user ? {user: environment.user} : null});',
        };
        builder.onResolve({ filter: /.*/ }, ({ path }) => {
          const name =
            path === 'react'
              ? 'react'
              : path.endsWith('/auth/AuthContext')
                ? 'auth'
                : path.endsWith('/HandoverModal')
                  ? 'modal'
                  : path.endsWith('/ui/ui')
                    ? 'ui'
                    : '';
          if (name) return { path: name, namespace: 'source-boundary' };
        });
        builder.onLoad({ filter: /.*/, namespace: 'source-boundary' }, ({ path }) => ({
          contents: stubs[path],
        }));
      },
    },
  ],
});
const bundledModule = { exports: {} };
new Function('require', 'module', 'exports', 'environment', bundled.outputFiles[0].text)(
  createRequire(import.meta.url),
  bundledModule,
  bundledModule.exports,
  environment,
);
const { SourceImport } = bundledModule.exports;
function reset() {
  storage.clear();
  environment.states = [];
  environment.cursor = 0;
  environment.effects = [];
  environment.cleanups = [];
  environment.user = { display_name: '当前登录人', username: 'current' };
}
function render(props) {
  environment.cursor = 0;
  const tree = SourceImport({
    onSaved() {},
    onClose() {},
    ...props,
  });
  for (const effect of environment.effects.splice(0)) environment.cleanups.push(effect());
  return tree;
}
function nodes(tree) {
  if (!tree || typeof tree !== 'object') return [];
  if (Array.isArray(tree)) return tree.flatMap(nodes);
  return [tree, ...nodes(tree.props?.children), ...nodes(tree.props?.footer)];
}
function input(tree, label) {
  const field = nodes(tree).find(
    (node) => node.type === 'label' && node.props.children[0]?.props.children === label,
  );
  return nodes(field).find((node) => ['input', 'textarea'].includes(node.type));
}
async function submit(tree) {
  tree.props.onSubmit({ preventDefault() {} });
  await new Promise(setImmediate);
}

test('上传表单仅选择原文件，不恢复旧文本或提交隐藏元信息', async () => {
  reset();
  const oldDraft = JSON.stringify({
    title: '旧纪要',
    payload: { mode: 'text', content: '旧草稿原文' },
  });
  storage.set('arks-handover-draft:global:import', oldDraft);
  const uploads = [],
    saved = [];
  const props = {
    client: {
      upload: async (...args) => {
        uploads.push(args);
        return { id: 'file' };
      },
    },
    onSaved: () => saved.push('changed'),
  };
  let tree = render(props);
  assert.equal(input(tree, '文件').props.multiple, true);
  const html = renderToStaticMarkup(tree);
  for (const obsolete of [
    '整理人',
    '来源说明',
    '文本内容',
    '输入文本',
    '下载文本草稿',
    'AI 提取',
    '版本',
  ])
    assert.ok(!html.includes(obsolete), obsolete);
  await submit(tree);
  assert.equal(uploads.length, 0);
  const file = new File(['不解析的原文件'], '资料.docx');
  input(tree, '文件').props.onChange({ target: { files: [file] } });
  tree = render(props);
  await submit(tree);
  assert.deepEqual(uploads, [[file, {}]]);
  assert.deepEqual(saved, ['changed']);
  assert.equal(storage.get('arks-handover-draft:global:import'), oldDraft);
});

test('失败后保留所选文件，可重试；上传过程中阻止重复提交', async () => {
  reset();
  let resolveUpload, rejectUpload;
  const uploads = [],
    saved = [];
  const props = {
    client: {
      upload: (...args) => {
        uploads.push(args);
        return new Promise((resolve, reject) => {
          resolveUpload = resolve;
          rejectUpload = reject;
        });
      },
    },
    onSaved: () => saved.push('changed'),
  };
  let tree = render(props);
  const file = new File(['原文件'], '文件.zip');
  input(tree, '文件').props.onChange({ target: { files: [file] } });
  tree = render(props);
  await submit(tree);
  tree = render(props);
  assert.ok(input(tree, '文件').props.disabled);
  await submit(tree);
  assert.equal(uploads.length, 1);
  rejectUpload(new Error('上传失败，请重试'));
  await new Promise(setImmediate);
  assert.ok(renderToStaticMarkup(render(props)).includes('上传失败，请重试'));
  await submit(render(props));
  assert.equal(uploads.length, 2);
  assert.equal(uploads[1][0], file);
  resolveUpload({ id: 'retry' });
  await new Promise(setImmediate);
  assert.deepEqual(saved, ['changed']);
});

test('多文件逐个保存，全部完成后只刷新一次并保留窗口；不合并文件或提交额外元信息', async () => {
  reset();
  const files = [new File(['PDF'], '手册.pdf'), new File(['DOCX'], '说明.docx')];
  const uploads = [];
  let changed = 0,
    closed = 0;
  const props = {
    client: { upload: async (...args) => uploads.push(args) },
    onSaved: () => changed++,
    onClose: () => closed++,
  };
  input(render(props), '文件').props.onChange({ target: { files } });
  const html = renderToStaticMarkup(render(props));
  assert.ok(html.includes('手册.pdf') && html.includes('说明.docx'));
  await submit(render(props));
  assert.deepEqual(
    uploads,
    files.map((file) => [file, {}]),
  );
  assert.equal(changed, 1);
  assert.equal(closed, 0);
  assert.ok(renderToStaticMarkup(render(props)).includes('文件已保存，可以继续选择文件上传'));
});

test('部分失败后继续其他文件，窗口保留；重试只上传失败项，不重复保存成功文件', async () => {
  reset();
  const files = ['a.pdf', 'b.docx', 'c.txt'].map((name) => new File([name], name));
  const uploads = [];
  let failed = false,
    changed = 0,
    closed = 0;
  const props = {
    client: {
      upload: async (file) => {
        uploads.push(file);
        if (file === files[1] && !failed) {
          failed = true;
          throw new Error('网络失败');
        }
      },
    },
    onSaved: () => changed++,
    onClose: () => closed++,
  };
  input(render(props), '文件').props.onChange({ target: { files } });
  await submit(render(props));
  assert.deepEqual(uploads, files);
  assert.equal(changed, 1);
  assert.equal(closed, 0);
  const html = renderToStaticMarkup(render(props));
  assert.ok(html.includes('已上传 2 个'));
  assert.ok(html.includes('重试失败文件（1）'));
  assert.ok(html.includes('网络失败'));
  await submit(render(props));
  assert.deepEqual(uploads, [...files, files[1]]);
  assert.equal(changed, 2);
  assert.equal(closed, 0);
});

test('非法文件分别报错，不阻塞其他有效文件；移除非法项后可完成', async () => {
  reset();
  const empty = new File([], '空.txt');
  const oversized = { name: '超限.zip', size: 32 * 1024 * 1024 + 1 };
  const valid = new File(['原文'], '原文.txt');
  const uploads = [];
  let closed = 0;
  const props = {
    client: { upload: async (file) => uploads.push(file) },
    onClose: () => closed++,
  };
  input(render(props), '文件').props.onChange({ target: { files: [empty, valid, oversized] } });
  let html = renderToStaticMarkup(render(props));
  assert.ok(html.includes('文件不能为空') && html.includes('文件不能超过 32 MB'));
  await submit(render(props));
  assert.deepEqual(uploads, [valid]);
  assert.equal(closed, 0);
  for (const file of [empty, oversized]) {
    nodes(render(props))
      .find((node) => node.props?.['aria-label'] === `移除 ${file.name}`)
      .props.onClick();
  }
  const tree = render(props);
  const complete = nodes(tree).find((node) => node.props?.children === '继续选择文件');
  assert.equal(complete.props.type, 'button');
  let chosen = 0;
  input(tree, '文件').props.ref.current = { click: () => chosen++ };
  complete.props.onClick();
  assert.equal(chosen, 1);
  assert.equal(closed, 0);
});

test('同一渲染内连点也只启动一个队列，期间禁止关闭和更改；文件顺序执行', async () => {
  reset();
  const files = ['1.txt', '2.txt'].map((name) => new File([name], name));
  const uploads = [],
    releases = [];
  let closed = 0;
  const props = {
    client: {
      upload: (file) => {
        uploads.push(file);
        return new Promise((resolve) => releases.push(resolve));
      },
    },
    onClose: () => closed++,
  };
  input(render(props), '文件').props.onChange({ target: { files } });
  const tree = render(props);
  await submit(tree);
  await submit(tree);
  tree.props.onClose();
  input(tree, '文件').props.onChange({ target: { files: [new File(['x'], '替换.txt')] } });
  assert.deepEqual(uploads, [files[0]]);
  assert.equal(closed, 0);
  releases[0]();
  await new Promise(setImmediate);
  assert.deepEqual(uploads, files);
  assert.ok(renderToStaticMarkup(render(props)).includes('已上传 1 个'));
  releases[1]();
  await new Promise(setImmediate);
  assert.equal(closed, 0);
});

test('连续选择保存三轮，窗口保留已成功文件；只上传新选择的文件，最后主动关闭', async () => {
  reset();
  const files = ['第一份.pdf', '第二份.docx', '第三份.txt'].map((name) => new File([name], name));
  const uploads = [];
  let changed = 0,
    closed = 0;
  const props = {
    client: { upload: async (file) => uploads.push(file) },
    onSaved: () => changed++,
    onClose: () => closed++,
  };
  for (const [index, file] of files.entries()) {
    input(render(props), '文件').props.onChange({ target: { files: [file] } });
    await submit(render(props));
    assert.deepEqual(uploads, files.slice(0, index + 1));
    assert.equal(changed, index + 1);
    assert.equal(closed, 0);
    const html = renderToStaticMarkup(render(props));
    assert.ok(html.includes(`已上传 ${index + 1} 个`));
    for (const previous of files.slice(0, index + 1)) assert.ok(html.includes(previous.name));
    await submit(render(props));
    assert.equal(uploads.length, index + 1);
  }
  nodes(render(props))
    .find((node) => node.props?.children === '关闭')
    .props.onClick();
  assert.equal(closed, 1);
});

test('继续选择不会清除失败文件；再次保存时保留成功项，只上传失败项和新文件', async () => {
  reset();
  const [saved, failed, added] = ['已存.txt', '失败.txt', '新增.txt'].map(
    (name) => new File([name], name),
  );
  const uploads = [];
  let rejectOnce = true;
  const props = {
    client: {
      upload: async (file) => {
        uploads.push(file);
        if (file === failed && rejectOnce) {
          rejectOnce = false;
          throw new Error('临时失败');
        }
      },
    },
  };
  input(render(props), '文件').props.onChange({ target: { files: [saved, failed] } });
  await submit(render(props));
  input(render(props), '文件').props.onChange({ target: { files: [added] } });
  assert.ok(renderToStaticMarkup(render(props)).includes('临时失败'));
  await submit(render(props));
  assert.deepEqual(uploads, [saved, failed, failed, added]);
  assert.ok(renderToStaticMarkup(render(props)).includes('已上传 3 个'));
});

test('离开上传界面后停止发送剩余文件，已成功保存的文件仍通知刷新', async () => {
  reset();
  const files = ['1.txt', '2.txt'].map((name) => new File([name], name));
  const uploads = [];
  let release,
    changed = 0,
    closed = 0;
  const props = {
    client: {
      upload: (file) => {
        uploads.push(file);
        return new Promise((resolve) => {
          release = resolve;
        });
      },
    },
    onSaved: () => changed++,
    onClose: () => closed++,
  };
  input(render(props), '文件').props.onChange({ target: { files } });
  await submit(render(props));
  for (const cleanup of environment.cleanups) cleanup?.();
  release();
  await new Promise(setImmediate);
  assert.deepEqual(uploads, [files[0]]);
  assert.equal(changed, 1);
  assert.equal(closed, 0);
});

test('空文件及超限文件不能上传，32 MB 边界允许，未登录时阻止提交', async () => {
  reset();
  const uploads = [];
  const props = {
    client: {
      upload: async (...args) => {
        uploads.push(args);
        return { id: 'file' };
      },
    },
  };
  let tree = render(props);
  input(tree, '文件').props.onChange({ target: { files: [new File([], '空文件.txt')] } });
  tree = render(props);
  assert.ok(renderToStaticMarkup(tree).includes('文件不能为空'));
  await submit(tree);
  const boundary = new File([new Uint8Array(32 * 1024 * 1024)], '大文件.pdf');
  const tooLarge = new File([boundary, 'x'], '超限.pdf');
  input(tree, '文件').props.onChange({ target: { files: [tooLarge] } });
  tree = render(props);
  assert.ok(renderToStaticMarkup(tree).includes('文件不能超过 32 MB'));
  await submit(tree);
  assert.equal(uploads.length, 0);
  input(tree, '文件').props.onChange({ target: { files: [boundary] } });
  await submit(render(props));
  assert.equal(uploads.length, 1);
  environment.user = undefined;
  await submit(render(props));
  assert.equal(uploads.length, 1);
});
