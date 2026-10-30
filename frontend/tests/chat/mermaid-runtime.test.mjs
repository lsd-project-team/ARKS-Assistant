import test from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<!doctype html><html><body></body></html>', { pretendToBeVisual: true });
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.SVGElement = dom.window.SVGElement;
globalThis.CSSStyleSheet = dom.window.CSSStyleSheet;
// jsdom 没有排版引擎；只替代尺寸测量，解析、布局算法、SVG 生成及清理运行真实依赖。
dom.window.SVGElement.prototype.getBBox = function () {
  return { x: 0, y: 0, width: (this.textContent?.length || 1) * 8, height: 20 };
};
dom.window.SVGElement.prototype.getComputedTextLength = function () {
  return (this.textContent?.length || 1) * 8;
};
const { renderMermaid, sanitizeDiagram } =
  await import('../../src/features/chat/rich/mermaidRender.ts');

test('真实 Mermaid 渲染流程图、处理语法错误且错误不阻塞后续队列', async () => {
  const [light, dark] = await Promise.all([
    renderMermaid('flowchart LR\nA[读取] --> B[完成]', false),
    renderMermaid('flowchart TD\nA[执行] --> B{成功?}\nB --> C[结束]', true),
  ]);
  for (const svg of [light, dark]) {
    assert.match(svg, /<svg/);
    assert.doesNotMatch(svg, /<script|<foreignObject|onclick=/);
  }
  assert.match(light, /读取/);
  assert.match(dark, /成功/);
  await assert.rejects(renderMermaid('flowchart LR\nA[', false));
  assert.match(await renderMermaid('flowchart LR\nX --> Y', false), /<svg/);
});

test('SVG 清理移除事件、脚本、外链及 HTML，配置覆盖在渲染前被拒绝', async () => {
  const clean = sanitizeDiagram(
    '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"><script>bad()</script><foreignObject><div>bad</div></foreignObject><image href="https://evil.test/track"/><a href="javascript:bad()"><text>text</text></a><text>safe</text></svg>',
  );
  assert.doesNotMatch(clean, /script|foreignObject|onload|href|evil\.test/);
  assert.match(clean, /safe/);
  await assert.rejects(
    renderMermaid('%%{init: {"securityLevel":"loose"}}%%\nflowchart LR\nA-->B', false),
  );
});

test('SVG 图片使用 viewBox 的固有尺寸，窄竖图不会按正文宽度放大', () => {
  const svg = sanitizeDiagram(
    '<svg xmlns="http://www.w3.org/2000/svg" width="100%" style="max-width:168px" viewBox="4 4 168 240"><text>步骤</text></svg>',
  );
  const root = svg.match(/^<svg[^>]*>/)[0];
  assert.match(root, /width="168"/);
  assert.match(root, /height="240"/);
  assert.doesNotMatch(root, /100%|max-width/);
  assert.match(svg, /步骤/);
});

test.after(() => dom.window.close());
