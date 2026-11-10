import test from 'node:test';
import assert from 'node:assert/strict';
import { parseHandoverHash } from '../../src/features/handover/navigation.ts';
import { draftStorageKey } from '../../src/features/handover/shared/drafts.ts';
import { localTime } from '../../src/features/handover/shared/format.ts';
import {
  effectiveWorkStatus,
  workStatusLabel,
} from '../../src/features/handover/tasks/workStatus.ts';
import { fieldSections } from '../../src/features/handover/shared/fieldLayout.ts';
import { handoverScope } from '../../src/features/handover/shared/types.ts';

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
  assert.equal(parseHandoverHash('#handover/updates').tab, 'updates');
  assert.deepEqual(parseHandoverHash('#handover/design?record=old-record&version=2'), {
    open: true,
    tab: 'overview',
    recordId: 'old-record',
    version: 2,
  });
});

test('本机交接草稿使用独立的全局范围，并按工作项区分', () => {
  assert.notEqual(draftStorageKey(handoverScope, 'task'), draftStorageKey(handoverScope, 'source'));
  assert.notEqual(
    draftStorageKey(handoverScope, 'record-a'),
    draftStorageKey(handoverScope, 'record-b'),
  );
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

test('交接字段分组保留所有字段且不改变调用方的顺序', () => {
  const keys = ['notes', 'owner', 'goal', 'dependencies', 'priority', 'custom'];
  const original = [...keys];
  const sections = fieldSections('task', keys, { priority: { enum: ['high', 'normal'] } });
  assert.deepEqual(
    sections.map(({ id, keys }) => [id, keys]),
    [
      ['basic', ['owner', 'priority']],
      ['content', ['goal', 'custom', 'notes']],
      ['relations', ['dependencies']],
    ],
  );
  assert.deepEqual(keys, original);
  assert.deepEqual(sections.flatMap((section) => section.keys).sort(), [...keys].sort());
});

test('基线版本与设备成组，空分组不产生多余标题', () => {
  const sections = fieldSections('baseline', ['software_version', 'sdk', 'source_id'], {});
  assert.equal(sections[0].title, '版本与设备');
  assert.deepEqual(
    sections.map((section) => section.id),
    ['basic', 'relations'],
  );
  assert.deepEqual(fieldSections('task', [], {}), []);
});
