import test from 'node:test';
import assert from 'node:assert/strict';
import { activeSlice } from '../../src/features/auth/activity.ts';

test('有效时间仅累计前台有焦点的活动，后台和失焦立即停止', () => {
  assert.equal(activeSlice(1000, 2000, true, true), 1000);
  assert.equal(activeSlice(1000, 2000, false, true), 0);
  assert.equal(activeSlice(1000, 2000, true, false), 0);
});

test('60 秒空闲阈值精确截断，跨休眠间隔不补造活动时间', () => {
  assert.equal(activeSlice(1000, 60500, true, true), 500);
  assert.equal(activeSlice(1000, 61000, true, true), 0);
  assert.equal(activeSlice(60000, 60000, true, true), 0);
  assert.equal(activeSlice(-10, 1000, true, true), 0);
});
