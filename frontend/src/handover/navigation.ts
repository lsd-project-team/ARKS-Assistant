import { useEffect, useState } from 'react';
import { tabs, type Tab } from './types.ts';

export function parseHandoverHash(hash: string) {
  const match = /^#handover(?:\/([^?]+))?(?:\?(.*))?$/.exec(hash);
  const tab = tabs.find((item) => item.id === match?.[1])?.id || 'overview';
  const parameters = new URLSearchParams(match?.[2]);
  const version = Number(parameters.get('version') || 0);
  return {
    open: !!match,
    tab,
    recordId: parameters.get('record') || '',
    ...(Number.isSafeInteger(version) && version > 0 ? { version } : {}),
  };
}
export function useHandoverNavigation() {
  const [route, setRoute] = useState(() => parseHandoverHash(location.hash));
  useEffect(() => {
    const update = () => setRoute(parseHandoverHash(location.hash));
    window.addEventListener('hashchange', update);
    return () => window.removeEventListener('hashchange', update);
  }, []);
  function navigate(tab: Tab = 'overview', recordId = '', version?: number) {
    location.hash = `handover/${tab}${recordId ? `?record=${encodeURIComponent(recordId)}${version ? `&version=${version}` : ''}` : ''}`;
    setRoute(parseHandoverHash(location.hash));
  }
  return { ...route, navigate };
}
