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
};
// 仅隔离 React 调度、弹窗容器和 HTTP；执行真实表单、草稿持久化及保存逻辑。
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
            'export const useState = (initial) => environment.useState(initial); export const useEffect = (effect) => environment.effects.push(effect);',
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
  environment.user = { display_name: '当前登录人', username: 'current' };
}
function render(props) {
  environment.cursor = 0;
  const tree = SourceImport({
    onSaved() {},
    onClose() {},
    ...props,
  });
  for (const effect of environment.effects.splice(0)) effect();
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
    onSaved: (row) => saved.push(row),
  };
  let tree = render(props);
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
  assert.deepEqual(saved, [{ id: 'file' }]);
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
    onSaved: (row) => saved.push(row),
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
  assert.deepEqual(saved, [{ id: 'retry' }]);
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
