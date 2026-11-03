import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';

const dom = new JSDOM('<!doctype html><div id="root"></div>');
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const compiled = await build({
  entryPoints: [
    fileURLToPath(new URL('../../src/features/chat/rich/MermaidViewport.tsx', import.meta.url)),
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
const { MermaidViewport } = module.exports;
const svg =
  '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="800"><text>测试流程</text></svg>';

async function mounted(verify, count = 1) {
  const root = createRoot(document.getElementById('root'));
  try {
    await act(async () =>
      root.render(
        Array.from({ length: count }, (_, index) =>
          createElement(MermaidViewport, { key: index, svg, title: `测试流程 ${index}` }),
        ),
      ),
    );
    const diagrams = Array.from(document.querySelectorAll('.rich-mermaid-viewport')).map(
      (viewport) => {
        const image = viewport.querySelector('img');
        const tools = viewport.previousElementSibling;
        // jsdom 不加载图片或排版；事件、React 状态、监听清理及滚动计算仍真实执行。
        Object.defineProperties(image, {
          naturalWidth: { value: 1000 },
          naturalHeight: { value: 800 },
        });
        Object.defineProperties(viewport, {
          clientWidth: { value: 800 },
          clientHeight: { value: 400 },
        });
        viewport.getBoundingClientRect = () => ({ left: 10, top: 20, width: 800, height: 400 });
        image.getBoundingClientRect = () => ({
          left: 10 - viewport.scrollLeft,
          top: 20 - viewport.scrollTop,
          width: parseFloat(image.style.width) || 1000,
          height: parseFloat(image.style.height) || 800,
        });
        return { viewport, image, tools, percent: () => tools.querySelector('output').textContent };
      },
    );
    await act(async () =>
      diagrams.forEach(({ image }) => image.dispatchEvent(new dom.window.Event('load'))),
    );
    await verify(diagrams, root);
  } finally {
    await act(async () => root.unmount());
  }
}

function wheel(viewport, options = {}) {
  const event = new dom.window.WheelEvent('wheel', {
    bubbles: true,
    cancelable: true,
    ctrlKey: true,
    deltaY: -120,
    clientX: 210,
    clientY: 170,
    ...options,
  });
  viewport.dispatchEvent(event);
  return event;
}
const pointUnderCursor = (image) => {
  const rect = image.getBoundingClientRect();
  return [(210 - rect.left) / rect.width, (170 - rect.top) / rect.height];
};

test('Ctrl 加滚轮只缩放图片并保持鼠标指向的图内位置，普通滚轮不拦截', async () => {
  await mounted(async ([diagram]) => {
    const { viewport, image, percent } = diagram;
    let ordinary;
    await act(async () => {
      ordinary = wheel(viewport, { ctrlKey: false });
    });
    assert.equal(ordinary.defaultPrevented, false);
    assert.equal(percent(), '100%');
    viewport.scrollLeft = 200;
    viewport.scrollTop = 100;
    const before = pointUnderCursor(image);
    let zoomed;
    await act(async () => {
      zoomed = wheel(viewport);
    });
    assert.equal(zoomed.defaultPrevented, true);
    assert.equal(percent(), '127%');
    assert.ok(parseFloat(image.style.width) > 1000);
    pointUnderCursor(image).forEach((value, index) =>
      assert.ok(Math.abs(value - before[index]) < 1e-8),
    );
    assert.equal(viewport.querySelector('svg'), null);
    assert.match(image.src, /^data:image\/svg\+xml/);
    const outside = wheel(document.body);
    assert.equal(outside.defaultPrevented, false);
  });
});

test('像素、行和页单位的滚轮输入得到一致缩放，零位移不拦截', async () => {
  for (const options of [
    { deltaMode: 0, deltaY: -120 },
    { deltaMode: 1, deltaY: -7.5 },
    { deltaMode: 2, deltaY: -0.3 },
  ]) {
    await mounted(async ([{ viewport, percent }]) => {
      await act(async () => wheel(viewport, options));
      assert.equal(percent(), '127%');
      const ignored = wheel(viewport, { deltaY: 0 });
      assert.equal(ignored.defaultPrevented, false);
      assert.equal(percent(), '127%');
    });
  }
});

test('缩放限制在 25% 至 400%，按钮可缩放和重置且恢复滚动起点', async () => {
  await mounted(async ([{ viewport, image, tools, percent }]) => {
    await act(async () => wheel(viewport, { deltaY: -100000 }));
    assert.equal(percent(), '400%');
    assert.equal(image.style.width, '4000px');
    assert.equal(tools.querySelector('[aria-label="放大流程图"]').disabled, true);
    const capped = wheel(viewport);
    assert.equal(capped.defaultPrevented, true);
    await act(async () => wheel(viewport, { deltaY: 100000 }));
    assert.equal(percent(), '25%');
    assert.equal(tools.querySelector('[aria-label="缩小流程图"]').disabled, true);
    viewport.scrollLeft = 20;
    viewport.scrollTop = 30;
    await act(async () => tools.querySelector('[aria-label="重置流程图缩放"]').click());
    assert.equal(percent(), '100%');
    assert.equal(image.style.width, '1000px');
    assert.equal(viewport.scrollLeft, 0);
    assert.equal(viewport.scrollTop, 0);
    await act(async () => tools.querySelector('[aria-label="放大流程图"]').click());
    assert.equal(percent(), '120%');
    await act(async () => tools.querySelector('[aria-label="缩小流程图"]').click());
    assert.equal(percent(), '100%');
  });
});

test('同一帧连续滚轮可累积缩放，卸载后不再拦截滚轮', async () => {
  let oldViewport;
  await mounted(async ([{ viewport, image, percent }]) => {
    oldViewport = viewport;
    const before = pointUnderCursor(image);
    await act(async () => {
      wheel(viewport);
      wheel(viewport);
    });
    assert.equal(percent(), '162%');
    pointUnderCursor(image).forEach((value, index) =>
      assert.ok(Math.abs(value - before[index]) < 1e-8),
    );
  });
  assert.equal(wheel(oldViewport).defaultPrevented, false);
});

test('同一回答中的多张流程图分别保持自己的缩放比例', async () => {
  await mounted(async ([first, second]) => {
    await act(async () => wheel(first.viewport));
    assert.equal(first.percent(), '127%');
    assert.equal(second.percent(), '100%');
    await act(async () => wheel(second.viewport, { deltaY: 120 }));
    assert.equal(first.percent(), '127%');
    assert.equal(second.percent(), '79%');
  }, 2);
});

test.after(() => dom.window.close());
