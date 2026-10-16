import test from 'node:test';
import assert from 'node:assert/strict';
import { activeRun } from '../../src/features/chat/lib/activeRun.ts';
import { elapsedRun, persistedFeedback } from '../../src/features/chat/lib/runFeedback.ts';

test('第一轮临时运行不能覆盖随后自动出队的运行', () => {
  const started = { id: 'first', thread_id: 'thread', status: 'queued' };
  assert.equal(activeRun(started, undefined, 'thread'), started);
  const completed = { ...started, status: 'completed' };
  assert.equal(activeRun(started, { runs: [completed] }, 'thread'), undefined);
  const next = { id: 'next', thread_id: 'thread', status: 'running' };
  assert.equal(activeRun(started, { runs: [completed, next] }, 'thread'), next);
  assert.equal(activeRun(started, { runs: [] }, 'other-thread'), undefined);
});

test('刷新后使用已保存结束时间，耗时不继续增长', () => {
  const run = {
    created_at: '2026-10-10T00:00:00Z',
    started_at: '2026-10-10T00:00:03Z',
    finished_at: '2026-10-10T00:01:15Z',
  };
  assert.equal(elapsedRun(run, Date.parse('2026-10-11T00:00:00Z')), '1 分 15 秒');
  assert.equal(
    elapsedRun({ ...run, finished_at: null }, Date.parse('2026-10-10T00:00:15Z')),
    '15 秒',
  );
});

test('刷新后的认证和 MCP 错误仍有正确处理入口', () => {
  assert.equal(
    persistedFeedback({ error: '凭据无效', error_code: 'authentication' }).action,
    'settings',
  );
  assert.equal(
    persistedFeedback({ error: '服务无法连接', error_code: 'mcp_connection' }).action,
    'mcp_settings',
  );
  assert.equal(
    persistedFeedback({ error: '输入太长', error_code: 'context_limit' }).action,
    'context',
  );
});
