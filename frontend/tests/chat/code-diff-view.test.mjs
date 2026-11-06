import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';
import { act, createElement } from 'react';
import { parseDiffFromFile } from '@pierre/diffs';

const dom = new JSDOM('<div id="root"></div>');
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.getComputedStyle = dom.window.getComputedStyle.bind(dom.window);
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const { createRoot } = await import('react-dom/client');
const boundary = { parseDiffFromFile, height: 828, resize: null, disconnected: 0 };
Object.defineProperty(dom.window.HTMLElement.prototype, 'clientHeight', {
  get() {
    if (this.classList.contains('code-work-body')) return boundary.height;
    if (this.classList.contains('code-review-topbar')) return 46;
    if (this.classList.contains('code-review-file-header')) return 39;
    return 0;
  },
});
globalThis.ResizeObserver = class {
  constructor(callback) {
    boundary.resize = callback;
  }
  observe() {}
  disconnect() {
    boundary.disconnected++;
  }
};
const compiled = await build({
  entryPoints: [
    fileURLToPath(new URL('../../src/features/chat/code_work/CodeDiffView.tsx', import.meta.url)),
  ],
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  jsx: 'automatic',
  plugins: [
    {
      name: 'diff-view-boundaries',
      setup(builder) {
        builder.onResolve(
          { filter: /^@pierre\/diffs(?:\/react)?$|appearance$|editorTheme$/ },
          ({ path }) => ({ path, namespace: 'boundary' }),
        );
        builder.onLoad({ filter: /.*/, namespace: 'boundary' }, ({ path }) => ({
          loader: 'jsx',
          resolveDir: fileURLToPath(new URL('../../', import.meta.url)),
          contents: path.endsWith('/react')
            ? `export function FileDiff({fileDiff,options}) {
            const lines = fileDiff.hunks.reduce((sum,hunk)=>sum+hunk.unifiedLineCount,0);
            const changes = fileDiff.hunks.flatMap(hunk=>hunk.hunkContent).filter(row=>row.type==='change');
            return <diffs-container style={{lineHeight:'20px'}} data-lines={lines} data-added={changes.reduce((sum,row)=>sum+row.additions,0)} data-deleted={changes.reduce((sum,row)=>sum+row.deletions,0)} data-style={options.diffStyle}/>;
          }`
            : path === '@pierre/diffs'
              ? 'export const parseDiffFromFile = boundary.parseDiffFromFile;'
              : path.endsWith('appearance')
                ? 'export const useAppearance = () => false;'
                : 'export const SOURCE_THEME = {}; export const SOURCE_DARK_THEME = {};',
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
const CodeDiffView = module.exports.default;
const before = Array.from({ length: 1000 }, (_, index) => `line ${index + 1}\n`).join('');
const diff = {
  path: 'Example.cs',
  version: 'v1',
  before,
  after: before.replace('line 500\n', 'changed\n'),
};
const visible = () => Number(document.querySelector('diffs-container').dataset.lines);
const compactLines = (input) =>
  parseDiffFromFile(
    { name: input.path, contents: input.before },
    { name: input.path, contents: input.after },
    { context: 3 },
  ).hunks.reduce((sum, hunk) => sum + hunk.unifiedLineCount, 0);

async function mounted(embedded, verify) {
  const root = createRoot(document.getElementById('root'));
  boundary.height = 828;
  boundary.resize = null;
  boundary.disconnected = 0;
  const render = async (input = diff) =>
    act(async () =>
      root.render(
        createElement(
          'section',
          { className: embedded ? 'code-work-pane' : 'code-work-dialog' },
          createElement(
            'div',
            { className: 'code-work-body' },
            createElement('div', { className: 'code-review-topbar' }),
            createElement(
              'section',
              { className: 'code-review-file' },
              createElement('div', { className: 'code-review-file-header' }),
              createElement(CodeDiffView, { diff: input, split: false, onSelect() {} }),
            ),
          ),
        ),
      ),
    );
  try {
    await render();
    await verify(render);
  } finally {
    await act(async () => root.unmount());
  }
}

test('短差异用真实相邻行填充阅读空间，随高度调整且限制展开量', async () => {
  await mounted(true, async (render) => {
    const initial = visible();
    assert.ok(initial >= 37 && initial < 60);
    assert.equal(document.querySelector('diffs-container').dataset.added, '1');
    assert.equal(document.querySelector('diffs-container').dataset.deleted, '1');
    await act(async () => {
      boundary.height = 450;
      boundary.resize();
    });
    assert.ok(visible() >= 19 && visible() < initial);
    await act(async () => {
      boundary.height = 5000;
      boundary.resize();
    });
    assert.ok(visible() <= 100);
    const long = {
      ...diff,
      version: 'v2',
      after: before.replace(/line (?:49\d|50\d|51\d)\n/g, 'changed\n'),
    };
    boundary.height = 828;
    await render(long);
    assert.equal(visible(), compactLines(long));
  });
  assert.ok(boundary.disconnected > 0);
});

test('独立合并预览保留紧凑上下文，不使用右侧面板的高度策略', async () => {
  await mounted(false, async () => {
    assert.equal(visible(), compactLines(diff));
    assert.equal(boundary.resize, null);
  });
});
