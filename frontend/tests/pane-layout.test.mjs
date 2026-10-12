import test from 'node:test';
import assert from 'node:assert/strict';
import { paneWidthLimits, WORKSPACE_MIN_WIDTH } from '../src/lib/paneLayout.ts';
import { constrainWidth } from '../src/lib/layoutMotion.ts';
import { navigationLayout } from '../src/lib/navigationLayout.ts';

test('拖动问答边界始终为源码保留阅读宽度，专注模式保留较窄问答', () => {
  for (const parentWidth of [641, 842, 1018]) {
    const limits = paneWidthLimits({ kind: 'chat', parentWidth });
    assert.equal(constrainWidth(2000, limits.minimum, limits.maximum), parentWidth - 321);
    assert.equal(constrainWidth(0, limits.minimum, limits.maximum), 320);
    assert.equal(parentWidth - limits.maximum - 1, WORKSPACE_MIN_WIDTH);
  }
  assert.equal(paneWidthLimits({ kind: 'chat', parentWidth: 600, focused: true }).minimum, 260);
});

test('文件树在并排与浮层模式下均保持可读，并排时不侵占源码下限', () => {
  const withFiles = paneWidthLimits({ kind: 'chat', parentWidth: 842, filesOpen: true });
  assert.equal(withFiles.maximum, 360);
  // 右侧预算同时包含源码、文件栏以及它们之间的分界线。
  assert.equal(842 - withFiles.maximum - 1 - 160 - 1, WORKSPACE_MIN_WIDTH);
  const floatingFiles = paneWidthLimits({
    kind: 'chat',
    parentWidth: 842,
    filesOpen: true,
    filesOverlay: true,
  });
  assert.equal(floatingFiles.maximum, 521);
  const inline = paneWidthLimits({ kind: 'files', parentWidth: 600 });
  assert.equal(constrainWidth(800, inline.minimum, inline.maximum), 279);
  assert.equal(constrainWidth(0, inline.minimum, inline.maximum), 160);
  const overlay = paneWidthLimits({ kind: 'files', parentWidth: 320, filesOverlay: true });
  assert.equal(constrainWidth(800, overlay.minimum, overlay.maximum), 285);
  assert.equal(constrainWidth(0, overlay.minimum, overlay.maximum), 160);
});

test('仅显示文件树时按工作区宽度限制，极窄容器不会产生反向边界', () => {
  assert.deepEqual(paneWidthLimits({ kind: 'files', parentWidth: 800, codeOpen: false }), {
    minimum: 160,
    maximum: 360,
  });
  const narrow = paneWidthLimits({ kind: 'files', parentWidth: 100 });
  assert.equal(narrow.maximum, narrow.minimum);
});

test('导航最大宽度在桌面临界尺寸仍保留三栏预算，窄屏浮层不挤占正文', () => {
  for (const viewport of [1101, 1104, 1200, 1400]) {
    const layout = navigationLayout(500, viewport);
    assert.ok(viewport - layout.width >= 802);
    assert.ok(layout.width >= 220 && layout.width <= 360);
  }
  assert.equal(navigationLayout(500, 700).maximumWidth, 360);
});
