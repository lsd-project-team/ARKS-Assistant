import { sessionFetch } from './session.ts';

export interface PasswordChange {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export function passwordError(values: PasswordChange): string {
  if (!values.current_password) return '请输入当前密码。';
  if (values.new_password.length < 6 || values.new_password.length > 256)
    return '新密码长度应为 6–256 个字符。';
  if (values.new_password !== values.confirm_password) return '两次新密码不一致。';
  if (values.current_password === values.new_password) return '新密码不能与当前密码相同。';
  return '';
}

export async function requestPasswordChange(values: PasswordChange, signal: AbortSignal) {
  const error = passwordError(values);
  if (error) throw new Error(error);
  const response = await sessionFetch('/api/auth/password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values),
    signal,
  });
  if (response.ok) return;
  // 只显示约定的错误，验证失败的响应可能含有原始表单数据。
  if (response.status === 400) throw new Error('当前密码不正确，请重新输入。');
  if (response.status === 401) throw new Error('登录已失效，请重新登录。');
  if (response.status === 403) throw new Error('登录校验已失效，请刷新页面后重试。');
  throw new Error('密码修改失败，请稍后重试。');
}

export async function requestLogout() {
  const response = await sessionFetch('/api/auth/logout', { method: 'POST' });
  if (!response.ok && response.status !== 401) throw new Error('退出登录失败，请重试。');
}
