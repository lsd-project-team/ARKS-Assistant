import { useSyncExternalStore } from 'react';

export function parseTimingHash(hash: string) {
  const match = /^#action-timing(?:\?(.*))?$/.exec(hash);
  const params = new URLSearchParams(match?.[1]);
  return { open: !!match, projectId: params.get('project') || '', runId: params.get('run') || '' };
}
export function timingHash(projectId = '', runId = '') {
  const params = new URLSearchParams();
  if (projectId) params.set('project', projectId);
  if (runId) params.set('run', runId);
  return `action-timing${params.size ? `?${params}` : ''}`;
}
function subscribe(listener: () => void) {
  window.addEventListener('hashchange', listener);
  return () => window.removeEventListener('hashchange', listener);
}
export function useTimingNavigation() {
  const hash = useSyncExternalStore(subscribe, () => window.location.hash);
  return parseTimingHash(hash);
}
