import test from 'node:test';
import assert from 'node:assert/strict';
import {
  filterDebugIssues,
  debugEditablePayload,
} from '../../src/features/handover/debug_issues/debugIssues.ts';
import { parseHandoverHash } from '../../src/features/handover/navigation.ts';

test('调试问题搜索可组合报警码、处理方法和状态，不混入工作项', () => {
  const rows = [
    {
      id: 'a',
      kind: 'debug_issue',
      title: 'E901 真空报警',
      updated_at: '2026-10-14',
      payload: { resolution_status: 'open', problem: '取片失败' },
    },
    {
      id: 'b',
      kind: 'debug_issue',
      title: 'E901 真空报警',
      updated_at: '2026-10-15',
      payload: { resolution_status: 'resolved', solution: '更换密封圈', keywords: ['S1'] },
    },
    { id: 'c', kind: 'task', title: 'E901 真空报警', updated_at: '2026-10-16', payload: {} },
  ];
  assert.deepEqual(
    filterDebugIssues(rows, 'E901 密封圈', '').map((row) => row.id),
    ['b'],
  );
  assert.deepEqual(
    filterDebugIssues(rows, 's1', 'resolved').map((row) => row.id),
    ['b'],
  );
  assert.deepEqual(
    filterDebugIssues(rows, '', 'open').map((row) => row.id),
    ['a'],
  );
  assert.deepEqual(
    rows.map((row) => row.id),
    ['a', 'b', 'c'],
  );
});

test('编辑请求仅发送可编辑事实字段，原文和对话身份由服务端保留', () => {
  const value = debugEditablePayload({
    problem: '报警',
    original_text: '完整描述',
    reported_by: '录入人',
    source_message_id: '消息',
    origin: 'ai',
    solution: '处理',
    resolution_status: 'resolved',
  });
  assert.equal(value.problem, '报警');
  assert.equal(value.resolution_status, 'resolved');
  for (const field of ['original_text', 'reported_by', 'source_message_id', 'origin'])
    assert.equal(field in value, false);
});

test('调试引用可恢复固定版本，去掉版本号后可查看和编辑最新记录', () => {
  assert.deepEqual(parseHandoverHash('#handover/issues?record=test-id&version=3'), {
    open: true,
    tab: 'issues',
    recordId: 'test-id',
    version: 3,
  });
  assert.deepEqual(parseHandoverHash('#handover/issues?record=test-id'), {
    open: true,
    tab: 'issues',
    recordId: 'test-id',
  });
});
