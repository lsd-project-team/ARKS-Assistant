import test from 'node:test';
import assert from 'node:assert/strict';
import {
  fitCamera,
  boundCamera,
  zoomCamera,
  cameraViewBox,
  diagramHeight,
} from '../../src/features/knowledge/reader/diagramCamera.ts';

test('横图、竖图及有偏移的图在不同窗口中默认完整可见，并留出边距', () => {
  for (const bounds of [
    [0, 0, 1260, 434],
    [-100, 80, 500, 2400],
    [30, -400, 8000, 300],
  ])
    for (const size of [
      { width: 1100, height: 500 },
      { width: 320, height: 440 },
      { width: 1800, height: 900 },
    ]) {
      const camera = fitCamera(bounds, size),
        view = cameraViewBox(camera, size);
      assert.ok(view[0] <= bounds[0] && view[1] <= bounds[1]);
      assert.ok(
        view[0] + view[2] >= bounds[0] + bounds[2] && view[1] + view[3] >= bounds[1] + bounds[3],
      );
      assert.ok((bounds[0] - view[0]) * camera.scale >= 23.99);
      assert.ok((bounds[1] - view[1]) * camera.scale >= 23.99);
    }
});

test('全图时选择边缘节点或拖动画布，都不能把另一侧移出窗口', () => {
  const bounds = [0, 0, 1260, 434],
    size = { width: 1000, height: 500 },
    fit = fitCamera(bounds, size);
  for (const [x, y] of [
    [0, 0],
    [1260, 434],
    [-5000, 5000],
  ])
    assert.deepEqual(boundCamera({ ...fit, x, y }, bounds, size), fit);
});

test('放大后平移受边界限制，横纵两端始终可达', () => {
  const bounds = [0, 0, 1200, 800],
    size = { width: 600, height: 400 };
  assert.deepEqual(boundCamera({ x: -1000, y: -1000, scale: 2 }, bounds, size), {
    x: 150,
    y: 100,
    scale: 2,
  });
  assert.deepEqual(boundCamera({ x: 9000, y: 9000, scale: 2 }, bounds, size), {
    x: 1050,
    y: 700,
    scale: 2,
  });
});

test('按鼠标位置缩放保留鼠标下的图中位置，极宽图缩小不会反而放大', () => {
  const bounds = [0, 0, 10000, 5000],
    size = { width: 600, height: 400 };
  const camera = { x: 5000, y: 2500, scale: 1 },
    anchor = { x: 400, y: 180 };
  const next = zoomCamera(camera, bounds, size, 1.25, anchor);
  assert.equal(
    camera.x + (anchor.x - size.width / 2) / camera.scale,
    next.x + (anchor.x - size.width / 2) / next.scale,
  );
  assert.equal(
    camera.y + (anchor.y - size.height / 2) / camera.scale,
    next.y + (anchor.y - size.height / 2) / next.scale,
  );
  const fit = fitCamera(bounds, size);
  assert.ok(zoomCamera(fit, bounds, size, 0.8).scale < fit.scale);
});

test('窗口改变后重新适配，长竖图增加画布高度而非固定高度缩成小字', () => {
  const bounds = [0, 0, 500, 2400],
    width = 1000;
  const height = diagramHeight(bounds, width),
    fit = fitCamera(bounds, { width, height });
  assert.ok(height > 2400);
  assert.ok(fit.scale >= 1.4);
  assert.ok(diagramHeight([0, 0, 1260, 434], 1000) < 500);
});
