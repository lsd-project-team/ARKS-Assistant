import test from 'node:test';
import assert from 'node:assert/strict';
import {
  filterDebugIssues,
  debugEditablePayload,
  debugStatus,
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

test('工作进展和经验按已记录展示，记录人和两个日期可独立编辑及检索', () => {
  const payload = debugEditablePayload({
    record_type: 'progress',
    problem: '发货延期，已与销售沟通',
    occurred_on: '8月28日',
    recorded_by: '贺强',
    recorded_at: '9月1日 15:49',
    resolution_status: 'open',
    reported_by: '李少达',
  });
  assert.equal(payload.resolution_status, 'recorded');
  assert.equal(debugStatus(payload), '已记录');
  assert.equal(payload.occurred_on, '8月28日');
  assert.equal(payload.recorded_at, '9月1日 15:49');
  assert.equal(payload.recorded_by, '贺强');
  assert.equal('reported_by' in payload, false);
  const rows = [
    { id: 'progress', kind: 'debug_issue', title: '发货延期', updated_at: '2026-10-16', payload },
  ];
  assert.deepEqual(
    filterDebugIssues(rows, '贺强 8月28日', 'recorded', 'progress').map((row) => row.id),
    ['progress'],
  );
  assert.deepEqual(filterDebugIssues(rows, '', 'open'), []);
  assert.deepEqual(filterDebugIssues(rows, '', '', 'problem'), []);
  assert.equal(debugEditablePayload({ problem: '旧问题' }).record_type, 'problem');
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
