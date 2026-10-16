import test from 'node:test';
import assert from 'node:assert/strict';
const saved = new Map();
globalThis.localStorage = {
  getItem: (key) => saved.get(key) ?? null,
  setItem: (key, value) => saved.set(key, value),
  removeItem: (key) => saved.delete(key),
};
globalThis.window = { localStorage: globalThis.localStorage };
const { useWorkspace, activateWorkspaceAccount, draftFor } = await import('../src/lib/store.ts');
const { ownedLegacyWorkspace, prepareLegacyWorkspace, workspaceStorageKey } =
  await import('../src/lib/accountWorkspace.ts');
const { sessionFetch, setSessionToken, setSessionAccount } = await import('../src/auth/session.ts');

test('切换账号隔离当前项目、最近对话、草稿和源码位置，切回恢复自己的内容', () => {
  activateWorkspaceAccount('first');
  useWorkspace.getState().initializeProject('project-a');
  useWorkspace.getState().selectThread('chat-a');
  useWorkspace.getState().setDraft('甲的未发送草稿');
  useWorkspace.getState().openFile('Private.cs', 55);
  useWorkspace.getState().savePosition('Private.cs', 55);
  useWorkspace.getState().setThreadEntry('chat-a', { kind: 'recent' });
  activateWorkspaceAccount('second');
  assert.equal(useWorkspace.getState().projectId, '');
  assert.equal(useWorkspace.getState().threadId, '');
  assert.deepEqual(useWorkspace.getState().paths, []);
  assert.deepEqual(useWorkspace.getState().drafts, {});
  assert.deepEqual(useWorkspace.getState().threadEntries, {});
  useWorkspace.getState().initializeProject('project-b');
  useWorkspace.getState().setDraft('乙的草稿');
  const second = saved.get(workspaceStorageKey('second'));
  assert.ok(
    !second.includes('甲的') && !second.includes('Private.cs') && !second.includes('chat-a'),
  );
  activateWorkspaceAccount('first');
  assert.equal(useWorkspace.getState().projectId, 'project-a');
  assert.equal(useWorkspace.getState().threadId, 'chat-a');
  assert.equal(draftFor(useWorkspace.getState()).content, '甲的未发送草稿');
  assert.equal(useWorkspace.getState().positions['Private.cs'], 55);
  activateWorkspaceAccount('');
  assert.deepEqual(useWorkspace.getState().drafts, {});
  activateWorkspaceAccount('second');
  assert.equal(draftFor(useWorkspace.getState()).content, '乙的草稿');
});

test('旧公共浏览器状态只迁移服务端确认的本人项目和对话，原件始终保留', async () => {
  const legacy = {
    state: {
      projectId: 'project-a',
      threadId: 'chat-unknown',
      paths: ['Private.cs'],
      projectSessions: {
        'project-a': { threadId: 'chat-unknown' },
        'project-b': { threadId: 'chat-b' },
      },
      drafts: {
        'chat-a': { content: '甲的' },
        'chat-b': { content: '乙的' },
        'new:project-a': { content: '/' },
        new: { content: '不明' },
      },
      chatPositions: { 'chat-a': { top: 1 }, 'chat-b': { top: 2 } },
      threadEntries: { 'chat-a': 'recent', 'chat-b': 'recent' },
    },
    version: 0,
  };
  const original = JSON.stringify(legacy);
  saved.set('trunk-workspace', original);
  const result = ownedLegacyWorkspace(
    JSON.parse(original),
    new Set(['project-a']),
    new Set(['chat-a']),
  );
  assert.equal(result.state.threadId, '');
  assert.deepEqual(Object.keys(result.state.projectSessions), ['project-a']);
  assert.equal(result.state.projectSessions['project-a'].threadId, '');
  assert.deepEqual(Object.keys(result.state.drafts), ['chat-a', 'new:project-a']);
  const other = ownedLegacyWorkspace(
    JSON.parse(original),
    new Set(['project-b']),
    new Set(['chat-b']),
  );
  assert.equal(other.state.paths, undefined);
  assert.deepEqual(Object.keys(other.state.drafts), ['chat-b']);
  await prepareLegacyWorkspace('migrate-first', async (path) =>
    path === '/api/projects' || path === '/api/projects?state=archived'
      ? {
          projects: [
            { id: 'project-a', owner_id: 'migrate-first' },
            { id: 'project-b', owner_id: 'someone' },
          ],
        }
      : path.includes('state=active')
        ? [
            { id: 'chat-a', owner_id: 'migrate-first' },
            { id: 'chat-b', owner_id: 'someone' },
          ]
        : [],
  );
  assert.equal(saved.get('trunk-workspace'), original);
  assert.ok(!saved.get(workspaceStorageKey('migrate-first')).includes('乙的'));
  assert.ok(saved.get(workspaceStorageKey('migrate-first')).includes('"/"'));
});

test('账号切换后忽略此前请求的晚到响应，每个请求携带预期账号供服务端核对', async (t) => {
  let complete;
  let headers;
  t.mock.method(globalThis, 'fetch', (_url, options) => {
    headers = options.headers;
    return new Promise((resolve) => {
      complete = resolve;
    });
  });
  setSessionToken('first-token');
  setSessionAccount('first');
  const pending = sessionFetch('/api/projects');
  assert.equal(headers.get('X-Arks-Account'), 'first');
  setSessionToken('second-token');
  setSessionAccount('second');
  complete(new Response('PRIVATE-FIRST-ACCOUNT'));
  await assert.rejects(pending, (error) => error.name === 'AbortError');
  setSessionToken('');
  setSessionAccount('');
});
