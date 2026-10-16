export type AccountRole = 'admin' | 'user';
export interface AuthSession {
  user: { id: string; username: string; display_name: string; role: AccountRole };
  csrf_token: string;
}

let csrfToken = '';
let sessionAccount = '';
export function setSessionAccount(id: string) {
  sessionAccount = id;
}
export function setSessionToken(token: string) {
  csrfToken = token;
}

export function parseSession(value: unknown): AuthSession {
  const session = value as Partial<AuthSession> | null;
  const user = session?.user;
  if (
    !user ||
    typeof user.id !== 'string' ||
    !user.id ||
    typeof user.username !== 'string' ||
    typeof user.display_name !== 'string' ||
    !['admin', 'user'].includes(user.role) ||
    typeof session?.csrf_token !== 'string' ||
    !session.csrf_token
  )
    throw new Error('登录信息无效，请重新登录。');
  return session as AuthSession;
}

export async function readSession(signal: AbortSignal): Promise<AuthSession | null> {
  const response = await fetch('/api/auth/session', {
    credentials: 'same-origin',
    cache: 'no-store',
    signal,
  });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error('暂时无法读取登录状态，请重试。');
  return parseSession(await response.json());
}

export async function sessionFetch(url: string, options: RequestInit = {}) {
  const expectedToken = csrfToken;
  const expectedAccount = sessionAccount;
  const headers = new Headers(options.headers);
  if (expectedAccount) headers.set('X-Arks-Account', expectedAccount);
  if (
    !['GET', 'HEAD', 'OPTIONS'].includes((options.method || 'GET').toUpperCase()) &&
    !headers.has('X-Arks-Submission-ID')
  )
    headers.set('X-Arks-Submission-ID', crypto.randomUUID());
  if (!['GET', 'HEAD', 'OPTIONS'].includes((options.method || 'GET').toUpperCase()) && csrfToken)
    headers.set('X-Arks-CSRF', csrfToken);
  const response = await fetch(url, { ...options, headers, credentials: 'same-origin' });
  if (expectedToken !== csrfToken || expectedAccount !== sessionAccount)
    throw new DOMException('账号已切换，忽略上一账号的响应', 'AbortError');
  if (response.status === 401 && typeof window !== 'undefined')
    window.dispatchEvent(new Event('arks-auth-required'));
  return response;
}
