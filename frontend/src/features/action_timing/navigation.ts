import { useSyncExternalStore } from 'react';

export function parseTimingHash(hash: string) {
  const match = /^#action-timing(?:\?(.*))?$/.exec(hash);
  const params = new URLSearchParams(match?.[1]);
  return {
    open: !!match,
    timingProjectId: params.get('timing_project') || params.get('project') || '',
  };
}
export function timingHash(timingProjectId = '') {
  const params = new URLSearchParams();
  if (timingProjectId) params.set('timing_project', timingProjectId);
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
