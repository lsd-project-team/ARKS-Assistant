import test from 'node:test';
import assert from 'node:assert/strict';
import { toolCounts, toolState, toolSummary } from '../../src/features/chat/lib/runCompletion.ts';
import {
  defaultAnalysis,
  normalizeSettings,
  validateSettings,
  emptyModel,
} from '../../src/features/settings/lib/settingsDraft.ts';

test('tool counters distinguish actual failures and budget skips, including old records', () => {
  const tools = [
    { id: '1', name: 'read_source', status: 'success', result: 'source', cached: true },
    {
      id: '2',
      name: 'read_source',
      status: 'error',
      result: '本轮检索预算已用尽。请依据已有源码收尾',
    },
    { id: '3', name: 'read_source', status: 'error', execution_status: 'skipped' },
    { id: '4', name: 'read_source', status: 'error', result: 'file missing' },
    { id: '5', name: 'read_source' },
  ];
  assert.deepEqual(toolCounts(tools), {
    attempted: 5,
    success: 1,
    skipped: 2,
    failed: 1,
    pending: 1,
    cached: 1,
  });
  assert.equal(toolState(tools[1]), 'skipped');
  assert.match(toolSummary(tools), /成功 1.*未执行 2.*失败 1/);
});

test('analysis defaults use high safety limits and invalid reserve is rejected', () => {
  const model = emptyModel();
  const settings = normalizeSettings({
    model,
    model_profiles: [{ id: 'default', name: '默认', config: model }],
    active_profile_id: 'default',
    mcp_servers: [],
    auto_memory: true,
    version: '',
  });
  assert.deepEqual(settings.analysis, defaultAnalysis);
  assert.equal(settings.analysis.standard_calls, 128);
  assert.equal(settings.analysis.deep_calls, 192);
  assert.equal(settings.analysis.max_continuations, 8);
  assert.deepEqual(validateSettings(settings), []);
  assert.ok(
    validateSettings({
      ...settings,
      analysis: { ...defaultAnalysis, standard_calls: 8, verification_reserve: 8 },
    }).some((row) => row.includes('预留')),
  );
  assert.ok(
    validateSettings({ ...settings, analysis: { ...defaultAnalysis, max_continuations: 9 } })
      .length,
  );
});
