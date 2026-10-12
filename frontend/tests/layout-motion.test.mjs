import test from 'node:test';
import assert from 'node:assert/strict';
import { animateLayout, stopLayoutMotion, settledWidth } from '../src/lib/layoutMotion.ts';

test('松手按最终位置决定收起，阈值外回弹到可用宽度并保留最大限制', () => {
  assert.equal(settledWidth(180, 220, 360, 180), null);
  assert.equal(settledWidth(181, 220, 360, 180), 220);
  assert.equal(settledWidth(100, 140, 285, 100), null);
  assert.equal(settledWidth(101, 140, 285, 100), 140);
  assert.equal(settledWidth(500, 220, 360, 180), 360);
  // 穿过收起阈值后拉回，最终宽度仍能正常保留。
  assert.equal(settledWidth(260, 220, 360, 180), 260);
});

test('过渡逐帧连续、结束清理临时宽度，打断后不触发旧完成回调', () => {
  const frames = new Map();
  let frameId = 0;
  globalThis.matchMedia = () => ({ matches: false });
  globalThis.requestAnimationFrame = (callback) => {
    frames.set(++frameId, callback);
    return frameId;
  };
  globalThis.cancelAnimationFrame = (id) => frames.delete(id);
  const values = new Map();
  let settledEvents = 0;
  const root = {
    dataset: {},
    dispatchEvent: (event) => {
      assert.equal(event.type, 'workspace-layout-settled');
      assert.equal(values.size, 0);
      settledEvents++;
    },
    style: {
      setProperty: (key, value) => values.set(key, value),
      removeProperty: (key) => values.delete(key),
    },
  };
  const from = {
    navigation: 300,
    chat: 400,
    files: 240,
    content: 346,
    composer: 400,
    contentOffset: 12,
    composerOffset: 0,
    composerInset: 18,
  };
  const to = {
    navigation: 68,
    chat: 1020,
    files: 0,
    content: 720,
    composer: 720,
    contentOffset: 140,
    composerOffset: 150,
    composerInset: 0,
  };
  let completions = 0;
  const start = performance.now();
  animateLayout(root, from, to, () => completions++);
  assert.equal(values.get('--motion-file-width'), '240px');
  const tick = (now) => {
    const callbacks = [...frames.values()];
    frames.clear();
    callbacks.forEach((callback) => callback(now));
  };
  tick(start + 110);
  const midpoint = parseFloat(values.get('--motion-file-width'));
  assert.ok(midpoint > 0 && midpoint < 240);
  stopLayoutMotion(root);
  tick(start + 300);
  assert.equal(completions, 0);
  assert.equal(settledEvents, 0);
  assert.equal(frames.size, 0);
  assert.equal(values.size, 0);
  assert.equal(root.dataset.layoutMoving, undefined);
  animateLayout(root, from, to, () => completions++);
  tick(performance.now() + 300);
  assert.equal(completions, 1);
  assert.equal(settledEvents, 1);
  assert.equal(values.size, 0);
  assert.equal(root.dataset.layoutMoving, undefined);
});

test('减少动态效果偏好直接完成布局，不保留动画帧', () => {
  globalThis.matchMedia = () => ({ matches: true });
  globalThis.requestAnimationFrame = () => {
    throw new Error('不应创建动画帧');
  };
  const root = { dataset: {}, style: {}, dispatchEvent: () => {} };
  const from = {
    navigation: 300,
    chat: 400,
    files: 240,
    content: 346,
    composer: 400,
    contentOffset: 12,
    composerOffset: 0,
    composerInset: 18,
  };
  const to = {
    navigation: 68,
    chat: 1020,
    files: 0,
    content: 720,
    composer: 720,
    contentOffset: 140,
    composerOffset: 150,
    composerInset: 0,
  };
  let finished = false;
  animateLayout(root, from, to, () => {
    finished = true;
  });
  assert.equal(finished, true);
  assert.equal(root.dataset.layoutMoving, undefined);
});
