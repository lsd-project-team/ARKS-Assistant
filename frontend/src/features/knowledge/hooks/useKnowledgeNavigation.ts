import { useEffect, useState } from 'react';
import { routeFromHash, routeHash, type Route } from '../routes';

export function useKnowledgeNavigation() {
  const [route, setRoute] = useState<Route>(() => routeFromHash());
  useEffect(() => {
    const update = () => setRoute(routeFromHash());
    window.addEventListener('hashchange', update);
    return () => window.removeEventListener('hashchange', update);
  }, []);
  function navigate(next: Route) {
    window.location.hash = routeHash(next);
    setRoute(next);
  }
  return { route, navigate, knowledgeOpen: route.kind !== 'chat' };
}
