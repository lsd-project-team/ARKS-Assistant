import test from 'node:test';
import assert from 'node:assert/strict';
import { boundProjectApi } from '../src/lib/projectRequest.ts';

test('切换项目后，等待中的记忆保存和源码查询保持原项目身份', async () => {
  let foreground = 'A';
  const calls = [];
  const request = async (path, options, projectId = foreground) => {
    calls.push({ path, projectId, method: options?.method });
    return { ok: true };
  };
  const original = boundProjectApi(foreground, request);
  await original('/memories/review', { method: 'POST' });
  foreground = 'B';
  const save = original('/memories', { method: 'PUT' });
  const oldQuery = original('/file?path=Program.cs');
  const current = boundProjectApi(foreground, request);
  await Promise.all([save, oldQuery, current('/file?path=Program.cs')]);
  assert.deepEqual(
    calls.map(({ projectId }) => projectId),
    ['A', 'A', 'A', 'B'],
  );
});

test('其他项目的预览查询可显式指定项目，默认绑定仍不变', async () => {
  const calls = [];
  const api = boundProjectApi('A', async (path, options, projectId) => {
    calls.push(projectId);
    return [];
  });
  await api('/threads', undefined, 'B');
  await api('/threads');
  assert.deepEqual(calls, ['B', 'A']);
});
