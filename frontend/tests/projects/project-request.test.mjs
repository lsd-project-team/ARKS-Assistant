import test from 'node:test';
import assert from 'node:assert/strict';
import { boundProjectApi } from '../../src/features/projects/lib/projectRequest.ts';
import { newConversationProject } from '../../src/features/chat/lib/conversationCreation.ts';
import { scopedApiUrl } from '../../src/shared/api/apiRoutes.ts';

test('公共入口的首次提问发送到独立工作区，项目内入口发送到指定项目', async () => {
  const projects = {
    projects: [{ id: 'project-a', state: 'active' }],
    default_project_id: 'project-a',
  };
  const calls = [];
  const request = async (path, options, projectId) => {
    calls.push({ url: scopedApiUrl(path, projectId), method: options.method });
    return { thread_id: 'new-thread' };
  };
  const independent = boundProjectApi(newConversationProject(projects), request);
  const withinProject = boundProjectApi(newConversationProject(projects, 'project-a'), request);
  await independent('/threads/start', { method: 'POST' });
  await withinProject('/threads/start', { method: 'POST' });
  assert.deepEqual(calls, [
    { url: '/api/p/independent/threads/start', method: 'POST' },
    { url: '/api/p/project-a/threads/start', method: 'POST' },
  ]);
});

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
