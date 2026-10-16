import test from 'node:test';
import assert from 'node:assert/strict';
import { readRememberedAccount, rememberAccount, requestLogin } from '../src/login/loginRequest.ts';

test('登录失败不会被当作成功，也不会回显服务端返回的密码字段', async (t) => {
  const credentials = { username: 'ui-check', password: 'test-only-password' };
  const controller = new AbortController();
  let status = 404;
  const request = t.mock.method(
    globalThis,
    'fetch',
    async () => new Response(JSON.stringify({ detail: credentials.password }), { status }),
  );
  for (const failureStatus of [401, 403, 404, 405, 429, 500]) {
    status = failureStatus;
    await assert.rejects(requestLogin(credentials, controller.signal), (error) => {
      assert.ok(error instanceof Error);
      assert.ok(!error.message.includes(credentials.password));
      return true;
    });
  }
  const [url, options] = request.mock.calls[0].arguments;
  assert.equal(url, '/api/auth/login');
  assert.equal(options.credentials, 'same-origin');
  assert.equal(options.cache, 'no-store');
  assert.equal(options.redirect, 'error');
  assert.equal(options.signal, controller.signal);
  assert.deepEqual(JSON.parse(options.body), credentials);
});

test('离开登录页后取消请求，取消原因不转换成账号错误', async (t) => {
  const controller = new AbortController();
  const aborted = new DOMException('测试取消', 'AbortError');
  t.mock.method(globalThis, 'fetch', async () => {
    controller.abort();
    throw aborted;
  });
  await assert.rejects(
    requestLogin({ username: 'ui-check', password: 'test-only-password' }, controller.signal),
    (error) => error === aborted,
  );
});

test('记住账号只保存账号，取消记住后删除；存储被禁用时不影响表单', () => {
  const previous = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
  const values = new Map();
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key) => values.get(key),
      setItem: (key, value) => values.set(key, value),
      removeItem: (key) => values.delete(key),
    },
  });
  try {
    rememberAccount('ui-check', true);
    assert.equal(readRememberedAccount(), 'ui-check');
    assert.deepEqual([...values.values()], ['ui-check']);
    rememberAccount('', false);
    assert.equal(readRememberedAccount(), '');
    assert.equal(values.size, 0);
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      get() {
        throw new Error('本机存储已禁用');
      },
    });
    assert.equal(readRememberedAccount(), '');
    assert.doesNotThrow(() => rememberAccount('ui-check', true));
  } finally {
    if (previous) Object.defineProperty(globalThis, 'localStorage', previous);
    else delete globalThis.localStorage;
  }
});
