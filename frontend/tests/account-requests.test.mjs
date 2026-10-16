import test from 'node:test';
import assert from 'node:assert/strict';
import {
  passwordError,
  requestLogout,
  requestPasswordChange,
} from '../src/auth/accountRequests.ts';
import { setSessionToken } from '../src/auth/session.ts';

const values = {
  current_password: 'old-password',
  new_password: '123456',
  confirm_password: '123456',
};

test('修改密码保留原始字符，检查长度、重复确认与新旧密码', () => {
  assert.equal(passwordError(values), '');
  assert.match(passwordError({ ...values, current_password: '' }), /当前密码/);
  assert.match(passwordError({ ...values, new_password: 'short' }), /长度/);
  assert.match(passwordError({ ...values, new_password: 'x'.repeat(257) }), /长度/);
  assert.match(passwordError({ ...values, confirm_password: 'different' }), /不一致/);
  assert.match(passwordError({ ...values, current_password: '123456' }), /相同/);
  assert.equal(
    passwordError({ ...values, new_password: ' pass ', confirm_password: ' pass ' }),
    '',
  );
});

test('改密使用当前会话校验，发送准确表单且不接受其他账号标识', async (t) => {
  let sent;
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    sent = { url, options };
    return new Response(null, { status: 204 });
  });
  setSessionToken('self-session');
  await requestPasswordChange(values, new AbortController().signal);
  assert.equal(sent.url, '/api/auth/password');
  assert.equal(sent.options.method, 'POST');
  assert.equal(sent.options.headers.get('X-Arks-CSRF'), 'self-session');
  assert.deepEqual(JSON.parse(sent.options.body), values);
  setSessionToken('');
});

test('改密失败只显示固定提示，不回显服务端表单内容', async (t) => {
  t.mock.method(
    globalThis,
    'fetch',
    async () => new Response('PRIVATE-PASSWORD-CONTENT', { status: 400 }),
  );
  await assert.rejects(
    requestPasswordChange(values, new AbortController().signal),
    /当前密码不正确/,
  );
});

test('退出必须撤销服务端会话，失败时保留重试机会', async (t) => {
  let status = 500;
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/api/auth/logout');
    assert.equal(options.method, 'POST');
    return new Response(null, { status });
  });
  await assert.rejects(requestLogout(), /退出登录失败/);
  status = 204;
  await requestLogout();
  status = 401;
  await requestLogout();
});
