import { requestJsonResponse } from '../../shared/api/http';
export { ApiError } from '../../shared/api/http';
import { useWorkspace } from '../state/store';
import { invalidateProjectCaches } from '../../features/projects/lib/projectCache';
import { queryGroups } from '../../shared/api/querySync';
import { sessionFetch } from '../../features/auth/session';
import { scopedApiUrl } from '../../shared/api/apiRoutes';

export function apiUrl(path: string, projectId = useWorkspace.getState().projectId) {
  return scopedApiUrl(path, projectId);
}

export async function api<T>(path: string, options?: RequestInit, projectId?: string): Promise<T> {
  const response = await requestJsonResponse(sessionFetch, apiUrl(path, projectId), options);
  if (options?.method && !['GET', 'HEAD'].includes(options.method.toUpperCase())) {
    changed(path);
    if (/^\/projects(\/|\?|$)/.test(path)) invalidateProjectCaches(queryGroups(path));
  }
  return response.json() as Promise<T>;
}
export const jsonBody = (value: unknown) => JSON.stringify(value);
export const query = (value: string) => encodeURIComponent(value);
import { changed } from '../../shared/api/querySync';
