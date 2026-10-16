import test from 'node:test';
import assert from 'node:assert/strict';
import {
  pendingReviewRows,
  reviewCounts,
  reviewReason,
  selectReviewRows,
} from '../../src/features/handover/reviews/reviewRecords.ts';

const row = (id, kind = 'interview', state = 'needs_review', version = 3) => ({
  id,
  kind,
  state,
  version,
  title: id,
  payload: {},
  scope_id: 'global',
  created_at: '2026-10-14T07:00:00Z',
  updated_at: '2026-10-14T08:00:00Z',
});
const event = (id, record_id, version, action = 'updated', detail = '') => ({
  id,
  record_id,
  version,
  action,
  detail,
  actor: '整理人',
  created_at: '2026-10-14T08:00:00Z',
});

test('统一待审核队列包含首次确认与重新复核，任务及 AI 运行、候选不进入队列', () => {
  const rows = [
    row('source', 'source'),
    row('interview'),
    row('package', 'package'),
    row('issue', 'issue'),
    row('plan', 'plan'),
    row('decision', 'decision'),
    row('task', 'task'),
    row('candidate', 'candidate'),
    row('job', 'job'),
    row('draft', 'source', 'draft'),
    row('confirmed', 'source', 'confirmed'),
    row('archived', 'interview', 'archived'),
    row('rejected', 'interview', 'rejected'),
  ];
  const original = structuredClone(rows);
  assert.deepEqual(reviewCounts(rows), { all: 7, source: 2, interview: 1, package: 1, other: 3 });
  assert.equal(pendingReviewRows(rows).length, 7);
  assert.deepEqual(
    selectReviewRows(rows, 'other').map((item) => item.id),
    ['issue', 'plan', 'decision'],
  );
  assert.deepEqual(
    selectReviewRows(rows, 'source').map((item) => item.id),
    ['source', 'draft'],
  );
  assert.equal(selectReviewRows(rows, 'all').length, 7);
  assert.deepEqual(rows, original);
});

test('空分类只清空当前结果，分类计数仍基于全部待复核记录', () => {
  const rows = [row('interview'), row('package', 'package')];
  assert.deepEqual(selectReviewRows(rows, 'source'), []);
  assert.deepEqual(reviewCounts(rows), { all: 2, source: 0, interview: 1, package: 1, other: 0 });
  assert.deepEqual(reviewCounts([]), { all: 0, source: 0, interview: 0, package: 0, other: 0 });
});

test('复核原因匹配当前记录、当前版本的最新操作，不依赖日志排列顺序', () => {
  const record = row('interview');
  const events = [
    event(9, 'interview', 2, 'invalidated', '过期原因'),
    event(11, 'another', 3, 'updated', '其他记录原因'),
    event(5, 'interview', 3, 'updated', '最新内容更正'),
    event(4, 'interview', 3, 'updated', '较早原因'),
  ];
  const original = structuredClone(events);
  assert.equal(reviewReason(record, events, [record]), '本记录内容已修改：最新内容更正');
  assert.equal(
    reviewReason(record, [...events].reverse(), [record]),
    '本记录内容已修改：最新内容更正',
  );
  assert.deepEqual(events, original);
});

test('关联失效展示已知来源名称，未知来源保留原日志，恢复说明不混入修改原因', () => {
  const record = row('package', 'package');
  const source = { ...row('source-id', 'source'), title: '载具访谈' };
  assert.equal(
    reviewReason(
      record,
      [event(6, record.id, 3, 'invalidated', '更正原文；影响来源 source-id')],
      [source],
    ),
    '更正原文；影响来源「载具访谈」',
  );
  assert.equal(
    reviewReason(
      record,
      [event(6, record.id, 3, 'invalidated', '更正原文；影响来源 unknown-id')],
      [source],
    ),
    '更正原文；影响来源 unknown-id',
  );
  assert.equal(
    reviewReason(record, [event(7, record.id, 3, 'restore')], []),
    '归档记录已恢复，需要重新复核。',
  );
  assert.equal(
    reviewReason(record, [event(7, record.id, 3, 'restore', '补充后继续查阅')], []),
    '归档记录已恢复：补充后继续查阅',
  );
});

test('日志缺失或仅有历史原因时明确提示，不推断未记录的变更', () => {
  const record = row('interview');
  const fallback = '未读取到当前版本的复核原因，请查看修改记录。';
  assert.equal(reviewReason(record, [], []), fallback);
  assert.equal(
    reviewReason(record, [event(2, record.id, 2, 'invalidated', '历史原因')], []),
    fallback,
  );
  assert.equal(reviewReason(record, [event(2, record.id, 3, 'confirm', '确认意见')], []), fallback);
  assert.equal(reviewReason({ ...record, state: 'confirmed' }, [event(2, record.id, 3)], []), '');
  assert.equal(
    reviewReason(record, [event(2, record.id, 3, 'updated', '  ')], []),
    '本记录内容已修改，需要重新复核。',
  );
});
