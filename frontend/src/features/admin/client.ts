import { sessionFetch } from '../auth/session';

export async function adminApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await sessionFetch(`/api${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!response.ok) {
    const failure = await response.json().catch(() => null);
    throw new Error(
      typeof failure?.detail === 'string' ? failure.detail : `请求失败 (${response.status})`,
    );
  }
  return response.json();
}

export const dateTime = (value?: string | null) =>
  value ? new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) : '未记录';
export const runLabels: Record<string, string> = {
  queued: '等待中',
  running: '进行中',
  completed: '成功',
  failed: '失败',
  cancelled: '已停止',
  interrupted: '已中断',
};
export function duration(ms: number) {
  const seconds = Math.floor(ms / 1000);
  return seconds >= 3600
    ? `${(seconds / 3600).toFixed(1)} 小时`
    : seconds >= 60
      ? `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`
      : `${seconds} 秒`;
}
