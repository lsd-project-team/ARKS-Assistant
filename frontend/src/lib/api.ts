export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}
import { useWorkspace } from './store';
import { invalidateProjectCaches } from './projectCache';
import { queryGroups } from './querySync';

const globalPath = /^\/(projects|sources|health|settings|backup|storage|data)(\/|\?|$)/;
export function apiUrl(path: string, projectId = useWorkspace.getState().projectId) {
  return `/api${projectId && !globalPath.test(path) ? `/p/${projectId}` : ''}${path}`;
}

export async function api<T>(path: string, options?: RequestInit, projectId?: string): Promise<T> {
  const response = await fetch(apiUrl(path, projectId), {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(
      typeof body?.detail === 'string' ? body.detail : `请求失败 (${response.status})`,
      response.status,
    );
  }
  if (options?.method && !['GET', 'HEAD'].includes(options.method.toUpperCase())) {
    changed(path);
    if (/^\/projects(\/|\?|$)/.test(path)) invalidateProjectCaches(queryGroups(path));
  }
  return response.json() as Promise<T>;
}
export const jsonBody = (value: unknown) => JSON.stringify(value);
export const query = (value: string) => encodeURIComponent(value);
import { changed } from './querySync';
