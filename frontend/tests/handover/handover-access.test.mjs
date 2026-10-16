import test from 'node:test';
import assert from 'node:assert/strict';
import {
  allowedHandoverTab,
  canReview,
  handoverTabs,
} from '../../src/features/handover/shared/access.ts';
import { parseSession, sessionFetch, setSessionToken } from '../../src/features/auth/session.ts';
import { clearProjectCaches, projectCache } from '../../src/features/projects/lib/projectCache.ts';

test('普通用户和未知身份没有复核入口，管理员保留完整导航', () => {
  for (const role of ['user', undefined, 'unknown']) {
    assert.equal(canReview(role), false);
    assert.equal(allowedHandoverTab('updates', role), false);
    assert.deepEqual(
      handoverTabs(role).map((tab) => tab.id),
      ['overview', 'materials', 'tasks', 'issues', 'packages'],
    );
  }
  assert.equal(allowedHandoverTab('updates', 'admin'), true);
  assert.equal(handoverTabs('admin').length, 6);
  for (const tab of ['overview', 'materials', 'tasks', 'issues', 'packages'])
    assert.equal(allowedHandoverTab(tab, 'user'), true);
});

test('无效的服务端身份不能默认成为管理员', () => {
  const valid = {
    user: { id: 'account', username: 'user', display_name: '普通用户', role: 'user' },
    csrf_token: 'test-csrf',
  };
  assert.deepEqual(parseSession(valid), valid);
  for (const value of [
    null,
    {},
    { ...valid, csrf_token: '' },
    { ...valid, user: { ...valid.user, role: 'root' } },
  ])
    assert.throws(() => parseSession(value));
});

test('业务写入带会话 CSRF，身份切换清空令牌后不再发送旧令牌', async (t) => {
  const calls = [];
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    calls.push(options);
    return new Response('{}');
  });
  setSessionToken('admin-csrf');
  await sessionFetch('/api/handover/records', { method: 'POST' });
  setSessionToken('user-csrf');
  await sessionFetch('/api/handover/records', { method: 'PATCH' });
  setSessionToken('');
  await sessionFetch('/api/handover/records', { method: 'POST' });
  assert.deepEqual(
    calls.map((options) => options.headers.get('X-Arks-CSRF')),
    ['admin-csrf', 'user-csrf', null],
  );
  assert.ok(calls.every((options) => options.credentials === 'same-origin'));
});

test('账号切换清理所有项目的管理员缓存，新账号取得全新缓存', () => {
  const first = projectCache('source-A');
  const second = projectCache('source-B');
  first.setQueryData(['handover-events'], [{ opinion: 'admin-review' }]);
  second.setQueryData(['handover-history'], [{ role: 'admin' }]);
  clearProjectCaches();
  assert.equal(first.getQueryData(['handover-events']), undefined);
  assert.equal(second.getQueryData(['handover-history']), undefined);
  assert.notEqual(projectCache('source-A'), first);
  assert.equal(projectCache('source-A').getQueryData(['handover-events']), undefined);
});
