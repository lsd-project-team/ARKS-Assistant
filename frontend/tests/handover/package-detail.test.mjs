import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';
import { Children, createElement, isValidElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const require = createRequire(import.meta.url);
const { QueryClient, QueryClientProvider } = require('@tanstack/react-query');
const environment = {};
const bundle = await build({
  stdin: {
    contents: `export { PackageDetail } from './src/features/handover/packages/PackageDetail';
      export { RecordHistory } from './src/features/handover/reviews/RecordHistory';`,
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
      name: 'package-modal-boundary',
      setup(builder) {
        builder.onResolve({ filter: /\/HandoverModal$/ }, () => ({
          path: 'modal',
          namespace: 'boundary',
        }));
        builder.onLoad({ filter: /.*/, namespace: 'boundary' }, () => ({
          resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
          contents:
            'import {createElement} from "react"; export function HandoverModal(props) { environment.modal = props; return createElement("section", null, props.title, props.description, props.children, props.footer); }',
        }));
      },
    },
  ],
});
const module = { exports: {} };
new Function('require', 'module', 'exports', 'environment', bundle.outputFiles[0].text)(
  require,
  module,
  module.exports,
  environment,
);
const { PackageDetail, RecordHistory } = module.exports;
const definitions = { states: { draft: '待确认', confirmed: '已确认' } };
const source = { id: 'source', kind: 'source', title: '后来修改的标题', version: 9 };
const row = {
  id: 'package',
  kind: 'package',
  title: '设备软件交接包',
  state: 'draft',
  version: 3,
  created_at: '2026-10-28T03:00:00Z',
  payload: {
    records: [{ record_id: 'source', version: 2 }],
    scope: '保留交接说明',
    evidence: [{ record_id: 'source', version: 2, locator: '原定位', quote: '保留引文' }],
  },
};
function render(client, version) {
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  cache.setQueryData(['handover-record', 'global', 'source', 2], {
    ...source,
    version: 2,
    title: '打包时的标题',
  });
  return renderToStaticMarkup(
    createElement(
      QueryClientProvider,
      { client: cache },
      createElement(PackageDetail, {
        row,
        version,
        records: [source],
        definitions,
        client,
        history: null,
        onClose() {},
        onOpen() {},
      }),
    ),
  );
}

test('详情只保留绿色完整包下载，隐藏全部修订号和重复内容说明，仍读取打包时标题', () => {
  const before = structuredClone(row);
  const html = render({ download() {} }, 3);
  assert.match(html, /class="button primary"[^>]*>下载完整包<\/button>/);
  assert.doesNotMatch(
    html,
    /下载 Word|含附件|v[239]|<h3>包内内容<\/h3>|点击查看生成交接包时保存的内容/,
  );
  for (const text of [
    '打包时的标题',
    '保留交接说明',
    '保留引文',
    '原定位',
    '返回当前交接包',
    '生成时间',
  ]) {
    assert.ok(html.includes(text), text);
  }
  assert.deepEqual(row, before);
});

test('隐藏版本展示后完整包仍按选中的包修订下载', async () => {
  const calls = [];
  render({ download: async (...args) => calls.push(args) }, 3);
  const button = Children.toArray(environment.modal.footer.props.children)
    .filter(isValidElement)
    .find((element) => element.props.className === 'primary');
  button.props.onClick();
  await new Promise(setImmediate);
  assert.deepEqual(calls, [
    ['/packages/package/export?format=zip&version=3', '设备软件交接包.zip'],
  ]);
});

test('交接包历史隐藏修订号但仍打开对应内容，其他类型保留既有历史显示', () => {
  const props = {
    identifier: 'package',
    definitions,
    onOpen() {},
    onRetry() {},
    history: [{ version: 3, state: 'draft', created_at: row.created_at }],
  };
  const html = renderToStaticMarkup(createElement(RecordHistory, { ...props, showVersion: false }));
  assert.doesNotMatch(html, /v3/);
  assert.match(html, /待确认/);
  assert.match(renderToStaticMarkup(createElement(RecordHistory, props)), /v3/);
  const opened = [];
  const tree = RecordHistory({
    ...props,
    showVersion: false,
    onOpen: (...args) => opened.push(args),
  });
  function click(node) {
    if (!isValidElement(node)) return;
    if (node.props.onClick) node.props.onClick();
    Children.forEach(node.props.children, click);
  }
  click(tree);
  assert.deepEqual(opened, [['package', 3]]);
});
