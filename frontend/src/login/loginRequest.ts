import { parseSession } from '../auth/session.ts';

export interface LoginCredentials {
  username: string;
  password: string;
}

const rememberedAccountKey = 'arks-login-account';

export function readRememberedAccount(): string {
  try {
    return localStorage.getItem(rememberedAccountKey) || '';
  } catch {
    return '';
  }
}

export function rememberAccount(username: string, enabled: boolean) {
  try {
    // “记住账号”只保存账号名称，密码和登录凭证不进入浏览器持久化存储。
    if (enabled) localStorage.setItem(rememberedAccountKey, username);
    else localStorage.removeItem(rememberedAccountKey);
  } catch {
    // 浏览器禁用本机存储时仍可填写和提交表单。
  }
}

export async function requestLogin(credentials: LoginCredentials, signal: AbortSignal) {
  let response: Response;
  try {
    // 认证接口属于全局入口，不经过当前项目的 API 路径转换。
    response = await fetch('/api/auth/login', {
      method: 'POST',
      credentials: 'same-origin',
      redirect: 'error',
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new Error('暂时无法连接登录服务，请稍后重试。');
  }
  if (response.ok) return parseSession(await response.json());
  if (response.status === 404 || response.status === 405)
    throw new Error('登录服务暂未开放，请联系管理员。');
  if (response.status === 401) throw new Error('账号或密码不正确，请重新输入。');
  if (response.status === 403) throw new Error('当前账号无法登录，请联系管理员。');
  if (response.status === 429) throw new Error('登录尝试过于频繁，请稍后重试。');
  // 不直接展示服务端返回内容，避免错误响应回显表单中的敏感字段。
  throw new Error('登录暂时不可用，请稍后重试。');
}
