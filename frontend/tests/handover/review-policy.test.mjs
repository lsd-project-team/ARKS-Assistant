import test from 'node:test';
import assert from 'node:assert/strict';
import { canReviewRecord } from '../../src/features/handover/reviews/reviewPolicy.ts';

test('只允许审核当前待处理正式记录，历史版本、已有结果与工作/AI 记录只读', () => {
  for (const kind of ['package', 'issue']) {
    assert.equal(canReviewRecord({ kind, state: 'draft' }), true);
    assert.equal(canReviewRecord({ kind, state: 'needs_review' }), true);
    assert.equal(canReviewRecord({ kind, state: 'needs_review' }, true), false);
    for (const state of ['confirmed', 'rejected', 'archived']) {
      assert.equal(canReviewRecord({ kind, state }), false);
    }
  }
  for (const kind of ['source', 'interview', 'task', 'candidate', 'job']) {
    assert.equal(canReviewRecord({ kind, state: 'needs_review' }), false);
  }
});
