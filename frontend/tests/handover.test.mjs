import test from 'node:test';
import assert from 'node:assert/strict';
import { parseHandoverHash } from '../src/handover/navigation.ts';
import { draftStorageKey } from '../src/handover/drafts.ts';
import { localTime } from '../src/handover/format.ts';
import { effectiveWorkStatus, workStatusLabel } from '../src/handover/workStatus.ts';

test('交接地址可刷新和后退，其他模块的地址不打开交接页', () => {
  for (const hash of ['#chat', '#graphs', '#modules', '#graph/demo', '']) {
    assert.equal(parseHandoverHash(hash).open, false);
  }
  assert.deepEqual(parseHandoverHash('#handover/tasks?record=abc%2Fdef'), {
    open: true,
    tab: 'tasks',
    recordId: 'abc/def',
  });
  assert.equal(parseHandoverHash('#handover').tab, 'overview');
  assert.equal(parseHandoverHash('#handover/tasks?record=abc&version=3').version, 3);
  assert.equal(parseHandoverHash('#handover/tasks?record=abc&version=-1').version, undefined);
  assert.equal(parseHandoverHash('#handover/unknown').tab, 'overview');
});

test('本机交接草稿按项目和工作项区分', () => {
  assert.notEqual(draftStorageKey('project-a', 'task'), draftStorageKey('project-b', 'task'));
  assert.notEqual(draftStorageKey('project-a', 'task'), draftStorageKey('project-a', 'interview'));
});

test('确认时间保留真实时刻并以当前时区显示', () => {
  assert.equal(localTime(), '');
  assert.equal(localTime('未指定日期'), '未指定日期');
  assert.equal(
    localTime('2026-10-12T09:00:00+00:00'),
    new Date('2026-10-12T09:00:00Z').toLocaleString('zh-CN', { hour12: false }),
  );
});

test('验收意向和待复核的旧验收记录不会显示为已经验收', () => {
  const row = { state: 'draft', payload: { work_status: 'accepted' } };
  assert.equal(effectiveWorkStatus(row), 'done');
  assert.equal(workStatusLabel(row, { accepted: '已验收' }), '验收待复核');
  assert.equal(effectiveWorkStatus({ ...row, state: 'needs_review' }), 'done');
  assert.equal(effectiveWorkStatus({ ...row, state: 'confirmed' }), 'accepted');
});
