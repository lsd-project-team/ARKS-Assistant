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
        };
        builder.onResolve({ filter: /.*/ }, ({ path }) => {
          const name =
            path === 'react'
              ? 'react'
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
}
function render(props) {
  environment.cursor = 0;
  const tree = SourceImport({
    scopeId: 'global',
    actor: '整理人',
    onActor() {},
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

test('新增只上传文件，旧文本草稿可下载且不能切回文字提交，保存后仍保留', async (context) => {
  reset();
  const old = JSON.stringify({
    title: '旧纪要',
    payload: { mode: 'text', content: '旧原文\r\n  保留空白 ', notes: '旧来源' },
  });
  storage.set('arks-handover-draft:global:import', old);
  const activeKey = 'arks-handover-draft:global:source-file-import';
  storage.set(
    activeKey,
    JSON.stringify({ title: '', payload: { notes: '新附件来源', provider: '隐藏的旧字段' } }),
  );
  const uploads = [];
  const saved = [];
  const props = {
    client: {
      send() {
        assert.fail('新增资料不能调用直接文本接口');
      },
      upload: async (...args) => {
        uploads.push(args);
        return { id: 'new-file' };
      },
    },
    onSaved: (row) => saved.push(row),
  };
  let tree = render(props);
  const html = renderToStaticMarkup(tree);
  assert.ok(!html.includes('输入文本'));
  assert.ok(!html.includes('AI 提取'));
  assert.ok(!input(tree, '文本内容'));
  assert.ok(html.includes('下载文本草稿'));
  let originalBlob;
  let download;
  context.mock.method(URL, 'createObjectURL', (blob) => {
    originalBlob = blob;
    return 'blob:legacy-draft';
  });
  context.mock.method(URL, 'revokeObjectURL', () => {});
  const oldDocument = globalThis.document;
  globalThis.document = {
    createElement: () => ({
      click() {
        download = { href: this.href, filename: this.download };
      },
    }),
  };
  context.after(() => {
    globalThis.document = oldDocument;
  });
  nodes(tree)
    .find((node) => node.type === 'button' && node.props.children === '下载文本草稿')
    .props.onClick();
  assert.equal(await originalBlob.text(), '旧原文\r\n  保留空白 ');
  assert.deepEqual(download, { href: 'blob:legacy-draft', filename: '旧纪要.txt' });
  await submit(tree);
  assert.equal(uploads.length, 0);
  const file = new File(['新附件原文'], '说明.txt', { type: 'text/plain' });
  input(tree, '文件').props.onChange({ target: { files: [file] } });
  tree = render(props);
  await submit(tree);
  assert.deepEqual(uploads, [[file, { actor: '整理人', notes: '新附件来源' }]]);
  assert.deepEqual(saved, [{ id: 'new-file' }]);
  assert.equal(storage.has(activeKey), false);
  assert.equal(storage.get('arks-handover-draft:global:import'), old);
  environment.states = [];
  const emptyText = JSON.stringify({
    title: '尚未填写正文的旧草稿',
    payload: { mode: 'text', content: '', notes: '仅属于旧文本的来源' },
  });
  storage.set('arks-handover-draft:global:import', emptyText);
  tree = render(props);
  assert.equal(input(tree, '来源说明（选填）').props.value, '');
  input(tree, '文件').props.onChange({ target: { files: [file] } });
  await submit(render(props));
  assert.equal(uploads[1][1].notes, '');
  assert.equal(storage.get('arks-handover-draft:global:import'), emptyText);
});

test('历史文本仍可修改，正文不裁剪，换版保留来源元信息和原记录关系', async () => {
  reset();
  const sent = [];
  const replacing = {
    id: 'old-text',
    title: '已有文本',
    payload: {
      format: 'text',
      content: '原版',
      notes: '原来源',
      provider: '原作者',
      source_version: '原版本',
      device: '设备 A',
    },
  };
  const props = {
    replacing,
    client: {
      upload() {
        assert.fail('历史文本更新应使用文本接口');
      },
      send: async (...args) => {
        sent.push(args);
        return { id: 'new-text' };
      },
    },
  };
  let tree = render(props);
  assert.ok(!renderToStaticMarkup(tree).includes('输入文本'));
  assert.ok(!input(tree, '文件'));
  const content = '  新原文\r\n尾部空白  \n';
  input(tree, '文本内容').props.onChange({ target: { value: content } });
  tree = render(props);
  await submit(tree);
  assert.deepEqual(sent, [
    [
      '/sources/text',
      {
        title: '已有文本',
        content,
        actor: '整理人',
        notes: '原来源',
        provider: '原作者',
        source_version: '原版本',
        device: '设备 A',
        supersedes: 'old-text',
      },
    ],
  ]);
  assert.equal(replacing.payload.content, '原版');
});

test('旧文件草稿说明在上传成功后迁移完成，不在下一次添加时重复带入', async () => {
  reset();
  const key = 'arks-handover-draft:global:import';
  storage.set(key, JSON.stringify({ title: '', payload: { mode: 'file', notes: '上次文件来源' } }));
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
  assert.equal(input(tree, '来源说明（选填）').props.value, '上次文件来源');
  input(tree, '文件').props.onChange({ target: { files: [new File(['原文'], '资料.txt')] } });
  await submit(render(props));
  assert.equal(uploads[0][1].notes, '上次文件来源');
  assert.equal(storage.has(key), false);
  environment.states = [];
  tree = render(props);
  assert.equal(input(tree, '来源说明（选填）').props.value, '');
});

test('文件换版失败保留当前草稿与旧文本草稿，重试仍提交文件和原关系', async () => {
  reset();
  const legacyKey = 'arks-handover-draft:global:source-update:document';
  const legacy = JSON.stringify({
    title: '未保存内容',
    payload: { mode: 'text', content: '旧换版草稿', notes: '旧文字来源' },
  });
  storage.set(legacyKey, legacy);
  const activeKey = 'arks-handover-draft:global:source-file-update:document';
  const current = JSON.stringify({ title: '原文档', payload: { notes: '当前文件来源' } });
  storage.set(activeKey, current);
  const uploads = [];
  let failing = true;
  const props = {
    replacing: {
      id: 'document',
      title: '原文档',
      payload: {
        format: 'pdf',
        notes: '原来源',
        provider: '原作者',
        source_version: '1',
        device: '设备 A',
      },
    },
    client: {
      upload: async (...args) => {
        uploads.push(args);
        if (failing) throw new Error('上传失败');
        return { id: 'replacement' };
      },
    },
  };
  let tree = render(props);
  const file = new File(['PDF fixture'], '新版.pdf');
  input(tree, '文件').props.onChange({ target: { files: [file] } });
  tree = render(props);
  await submit(tree);
  assert.deepEqual(uploads, [
    [
      file,
      {
        actor: '整理人',
        notes: '当前文件来源',
        supersedes: 'document',
        provider: '原作者',
        source_version: '1',
        device: '设备 A',
      },
    ],
  ]);
  assert.equal(storage.get(activeKey), current);
  assert.equal(storage.get(legacyKey), legacy);
  assert.ok(renderToStaticMarkup(render(props)).includes('上传失败'));
  failing = false;
  await submit(render(props));
  assert.equal(uploads.length, 2);
  assert.deepEqual(uploads[1], uploads[0]);
  assert.equal(storage.has(activeKey), false);
  assert.equal(storage.get(legacyKey), legacy);
});

test('历史文本按 Unicode 字符校验上限，超限阻止提交且正文不被截断', async () => {
  reset();
  const requests = [];
  const props = {
    replacing: {
      id: 'text',
      title: '历史原文',
      payload: { format: 'text', content: '字'.repeat(99999) + '😀' },
    },
    client: {
      send: async (...args) => {
        requests.push(args);
        return { id: 'updated' };
      },
    },
  };
  let tree = render(props);
  await submit(tree);
  assert.equal(requests.length, 1);
  const overLimit = '字'.repeat(100000) + '😀';
  input(tree, '文本内容').props.onChange({ target: { value: overLimit } });
  tree = render(props);
  await submit(tree);
  assert.equal(requests.length, 1);
  assert.equal(input(tree, '文本内容').props.value, overLimit);
  assert.ok(renderToStaticMarkup(tree).includes('文本超过 100,000 字符'));
});
