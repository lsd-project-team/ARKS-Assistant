import { ApiError } from '../../../app/api/client';
import { sessionFetch } from '../../auth/session';

export function handoverClient() {
  const root = '/api/handover';
  async function request<T>(path = '', options?: RequestInit): Promise<T> {
    const response = await sessionFetch(root + path, options);
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new ApiError(
        typeof body?.detail === 'string' ? body.detail : `请求失败 (${response.status})`,
        response.status,
      );
    }
    return response.json() as Promise<T>;
  }
  return {
    get: <T>(path = '') => request<T>(path),
    send: <T>(path: string, body: unknown, method = 'POST') =>
      request<T>(path, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }),
    upload: <T>(file: File, metadata: Record<string, string>) =>
      request<T>(`/sources/import?${new URLSearchParams({ ...metadata, filename: file.name })}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/octet-stream' },
        body: file,
      }),
    download: async (path: string, filename: string) => {
      const response = await sessionFetch(root + path);
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || '下载失败，请重试');
      }
      const address = URL.createObjectURL(await response.blob());
      const anchor = document.createElement('a');
      anchor.href = address;
      anchor.download = filename;
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(address), 1000);
    },
  };
}
export type Client = ReturnType<typeof handoverClient>;
