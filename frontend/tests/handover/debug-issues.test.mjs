import test from 'node:test';
import assert from 'node:assert/strict';
import {
  filterDebugIssues,
  debugEditablePayload,
  debugStatus,
  debugVisiblePayload,
  debugKnowledgePayload,
} from '../../src/features/handover/debug_issues/debugIssues.ts';

test('六项投影保留旧字段事实，已合入方法和注意事项的内容不重复，也不补造结果', () => {
  const payload = {
    problem: '取片不稳定',
    conditions: '现场加热',
    device: 'ZX2200 HS',
    module: 'S1',
    investigation: '检查真空管路',
    solution: '检查真空管路，再更换密封圈',
    cause: '原记录认为密封圈破损',
    notes: '原因判断：原记录认为密封圈破损',
    original_text: '完整原文',
    images: [{ id: '原图' }],
  };
  const original = structuredClone(payload);
  const projected = debugKnowledgePayload(payload);
  assert.equal(projected.question, payload.problem);
  assert.ok(projected.answer.includes('现场加热'));
  assert.ok(projected.answer.includes('更换密封圈'));
  assert.equal(projected.original_text, payload.original_text);
  assert.deepEqual(projected.images, payload.images);
  assert.equal(projected.verification, undefined);
  assert.deepEqual(payload, original);
});
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

test('导入来源编号和文件不进入展示及编辑，正文、状态与原始对象保留', () => {
  const original = {
    id: 'EXP-099',
    source: '原始交接.xlsx',
    title: '保留标题',
    question: '保留问题',
    answer: '保留处理',
    caution: '保留条件',
    status: '待验证',
  };
  const payload = {
    origin: 'import',
    original_text: JSON.stringify(original),
    problem: '完整正文',
    notes:
      '来源编号：EXP-099\n原始来源：原始交接.xlsx\n本次提供文件：本次.xlsx\n本包提供文件：本包.xlsx\n导入标识：包哈希\n关联记录：EXP-001《其他问题》\n处理后仍需验证。',
    keywords: ['EXP-099', 'ZX2200', '力控'],
    resolution_status: 'open',
  };
  const before = structuredClone(payload);
  const visible = debugVisiblePayload(payload);
  assert.deepEqual(JSON.parse(visible.original_text), {
    title: original.title,
    question: original.question,
    answer: original.answer,
    caution: original.caution,
    status: original.status,
  });
  assert.equal(visible.notes, '关联记录：《其他问题》\n处理后仍需验证。');
  assert.deepEqual(visible.keywords, ['ZX2200', '力控']);
  assert.equal(visible.problem, '完整正文');
  assert.equal(visible.resolution_status, 'open');
  const editable = debugEditablePayload(payload);
  assert.ok(editable.answer.includes('处理后仍需验证'));
  assert.deepEqual(editable.keywords, visible.keywords);
  assert.deepEqual(payload, before);
});

test('非导入原文、损坏 JSON 和正常说明不误删，来源词出现在正文中仍保留', () => {
  const original_text = '{"id":"业务对象","source":"信号来源"}';
  const notes = '检查信号来源：编码器\r\n第二行。';
  for (const payload of [
    { origin: 'human', original_text, notes },
    { origin: 'import', original_text: '{未完成JSON', notes },
    { origin: 'import', original_text: '[1,2]', notes },
  ]) {
    assert.equal(debugVisiblePayload(payload).original_text, payload.original_text);
    assert.equal(debugVisiblePayload(payload).notes, notes);
  }
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
  assert.equal(payload.metadata.resolution_status, 'recorded');
  assert.equal(debugStatus(payload), '已记录');
  assert.equal(payload.metadata.occurred_on, '8月28日');
  assert.equal(payload.metadata.recorded_at, '9月1日 15:49');
  assert.equal(payload.metadata.recorded_by, '贺强');
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
  assert.equal(debugEditablePayload({ problem: '旧问题' }).metadata.record_type, 'problem');
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
  assert.equal(value.question, '报警');
  assert.equal(value.metadata.resolution_status, 'resolved');
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
