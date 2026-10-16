import test from 'node:test';
import assert from 'node:assert/strict';
import { adminRoute } from '../../src/features/admin/navigation.ts';

test('从管理页进入交接、复核和固定历史地址时，直接按当前地址判断有效性', () => {
  const materials = adminRoute('#handover/materials');
  assert.equal(materials.valid, true);
  assert.equal(materials.page, 'handover');
  assert.equal(materials.handover.tab, 'materials');
  const review = adminRoute('#handover/updates?record=record-1&version=3');
  assert.equal(review.page, 'reviews');
  assert.equal(review.handover.recordId, 'record-1');
  assert.equal(review.handover.version, 3);
});

test('管理员默认进入概览，问答详情支持独立刷新，聊天地址不挂载管理员聊天', () => {
  assert.equal(adminRoute('#admin/questions/thread-1').questionId, 'thread-1');
  assert.equal(adminRoute('#admin/questions/thread-1').page, 'questions');
  assert.equal(adminRoute('#handover/overview').page, 'overview');
  for (const hash of ['', '#chat', '#graphs']) {
    assert.equal(adminRoute(hash).valid, false);
    assert.equal(adminRoute(hash).page, 'overview');
  }
});
