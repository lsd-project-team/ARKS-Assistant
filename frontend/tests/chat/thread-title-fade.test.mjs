import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';
import { act, createElement } from 'react';

const dom = new JSDOM('<!doctype html><body></body>', { url: 'http://localhost/' });
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const { createRoot } = await import('react-dom/client');
const compiled = await build({
  entryPoints: [
    fileURLToPath(new URL('../../src/features/chat/components/ThreadItem.tsx', import.meta.url)),
  ],
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  packages: 'external',
  jsx: 'automatic',
});
const module = { exports: {} };
new Function('require', 'module', 'exports', compiled.outputFiles[0].text)(
  createRequire(import.meta.url),
  module,
  module.exports,
);
const { ThreadItem } = module.exports;
const fullTitle = '晶圆取片高度和顶针速度的默认值是多少？';

async function mounted(dimensions, verify) {
  const holder = document.createElement('div');
  document.body.append(holder);
  const root = createRoot(holder);
  const observers = [];
  const listeners = new Set();
  const fonts = new dom.window.EventTarget();
  let finishFonts;
  fonts.ready = new Promise((resolve) => {
    finishFonts = resolve;
  });
  const add = fonts.addEventListener.bind(fonts),
    remove = fonts.removeEventListener.bind(fonts);
  fonts.addEventListener = (type, callback) => {
    if (type === 'loadingdone') listeners.add(callback);
    add(type, callback);
  };
  fonts.removeEventListener = (type, callback) => {
    if (type === 'loadingdone') listeners.delete(callback);
    remove(type, callback);
  };
  const previousFonts = Object.getOwnPropertyDescriptor(document, 'fonts');
  Object.defineProperty(document, 'fonts', { configurable: true, value: fonts });
  const previousObserver = globalThis.ResizeObserver;
  globalThis.ResizeObserver = class {
    targets = new Set();
    disconnected = false;
    constructor(callback) {
      this.callback = callback;
      observers.push(this);
    }
    observe(element) {
      this.targets.add(element);
    }
    disconnect() {
      this.disconnected = true;
      this.targets.clear();
    }
  };
  const prototype = dom.window.HTMLElement.prototype;
  const descriptors = Object.fromEntries(
    ['clientWidth', 'scrollWidth'].map((key) => [
      key,
      Object.getOwnPropertyDescriptor(prototype, key),
    ]),
  );
  let reads = 0;
  for (const [property, key] of [
    ['clientWidth', 'visible'],
    ['scrollWidth', 'content'],
  ])
    Object.defineProperty(prototype, property, {
      configurable: true,
      get() {
        if (!this.classList.contains('thread-title')) return 0;
        reads++;
        return dimensions[key];
      },
    });
  let props = {
    row: { id: 'thread-a', title: fullTitle, state: 'active', updated_at: '2026-11-09' },
    selected: false,
    filter: '',
    busy: false,
    onSelect() {},
    onAction() {},
    onRename: async () => {},
  };
  let unmounted = false;
  const render = async (updates = {}) => {
    props = { ...props, ...updates };
    await act(async () => root.render(createElement(ThreadItem, props)));
  };
  const unmount = async () => {
    if (unmounted) return;
    await act(async () => root.unmount());
    unmounted = true;
  };
  try {
    await render();
    await verify({
      holder,
      render,
      fonts,
      listeners,
      observers,
      finishFonts,
      unmount,
      reads: () => reads,
      label: () => holder.querySelector('.thread-title'),
      resize: async () =>
        act(async () => {
          for (const observer of observers)
            if ([...observer.targets].some((element) => element.classList.contains('thread-title')))
              observer.callback([]);
        }),
    });
  } finally {
    await unmount();
    holder.remove();
    for (const [key, descriptor] of Object.entries(descriptors)) {
      if (descriptor) Object.defineProperty(prototype, key, descriptor);
      else delete prototype[key];
    }
    if (previousFonts) Object.defineProperty(document, 'fonts', previousFonts);
    else delete document.fonts;
    globalThis.ResizeObserver = previousObserver;
  }
}

test('短标题和刚好容纳的标题不渐隐，溢出一像素才标记；完整标题与选择交互保留', async () => {
  for (const content of [120, 200, 201]) {
    await mounted({ visible: 200, content }, async ({ holder, label, render }) => {
      assert.equal(label().getAttribute('data-overflow'), content > 200 ? 'true' : null);
      assert.equal(label().textContent, fullTitle);
      assert.equal(holder.querySelector('.thread-select').title, fullTitle);
      let selections = 0;
      await render({ onSelect: () => selections++ });
      await act(async () => holder.querySelector('.thread-select').click());
      assert.equal(selections, 1);
    });
  }
});

test('侧栏扩宽取消渐隐，缩窄后重新启用，不改标题或行内容', async () => {
  const dimensions = { visible: 160, content: 200 };
  await mounted(dimensions, async ({ label, resize }) => {
    assert.equal(label().dataset.overflow, 'true');
    dimensions.visible = 200;
    await resize();
    assert.equal(label().hasAttribute('data-overflow'), false);
    dimensions.visible = 140;
    await resize();
    assert.equal(label().dataset.overflow, 'true');
    assert.equal(label().textContent, fullTitle);
  });
});

test('字体加载完成后重测，卸载清理监听和观察器，迟到的字体回调不再读取旧元素', async () => {
  const dimensions = { visible: 200, content: 180 };
  await mounted(
    dimensions,
    async ({ label, fonts, listeners, observers, finishFonts, unmount, reads }) => {
      assert.equal(label().hasAttribute('data-overflow'), false);
      dimensions.content = 210;
      await act(async () => fonts.dispatchEvent(new dom.window.Event('loadingdone')));
      assert.equal(label().dataset.overflow, 'true');
      assert.equal(listeners.size, 1);
      await unmount();
      assert.equal(listeners.size, 0);
      assert.ok(observers.every((observer) => observer.disconnected));
      const before = reads();
      await act(async () => finishFonts());
      assert.equal(reads(), before);
    },
  );
});

test('重命名取消后恢复观察，新标题及搜索高亮更新时重测，原菜单继续可用', async () => {
  const dimensions = { visible: 160, content: 200 };
  await mounted(dimensions, async ({ holder, label, render, listeners }) => {
    await act(async () => holder.querySelector('.thread-more').click());
    const rename = [...document.querySelectorAll('[role=menuitem]')].find(
      (element) => element.textContent === '重命名',
    );
    assert.ok(rename);
    await act(async () => rename.click());
    assert.equal(label(), null);
    assert.equal(listeners.size, 0);
    const input = holder.querySelector('input[aria-label=对话名称]');
    dimensions.content = 80;
    await act(async () =>
      input.dispatchEvent(
        new dom.window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }),
      ),
    );
    assert.equal(label().hasAttribute('data-overflow'), false);
    assert.equal(listeners.size, 1);
    dimensions.content = 210;
    const title = '更新后的取片高度参数说明';
    await render({
      row: { id: 'thread-a', title, state: 'active' },
      filter: '高度',
      selected: true,
    });
    assert.equal(label().dataset.overflow, 'true');
    assert.equal(label().textContent, title);
    assert.equal(holder.querySelector('.thread-select').title, title);
    assert.equal(label().querySelector('mark').textContent, '高度');
  });
});
