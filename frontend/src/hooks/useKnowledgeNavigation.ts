import { useEffect, useRef, useState } from 'react';
import { routeFromHash, routeHash, type Route } from '../knowledge/routes';
import { toast } from '../lib/toasts';

export function useKnowledgeNavigation() {
  const [route, setRoute] = useState<Route>(() => routeFromHash());
  const preparing = useRef(false);
  useEffect(() => {
    const update = () => setRoute(routeFromHash());
    window.addEventListener('hashchange', update);
    return () => window.removeEventListener('hashchange', update);
  }, []);
  function visit(next: Route) {
    window.location.hash = routeHash(next);
    setRoute(next);
  }
  async function navigate(next: Route) {
    if (preparing.current) return;
    preparing.current = true;
    try {
      if (next.kind === 'project-source' && next.path) {
        const { openKnowledgeSource } = await import('../knowledge/discussion');
        if (await openKnowledgeSource(next.path, next.start, next.end, next.expectedVersion))
          visit({ kind: 'chat' });
        return;
      }
      if (next.kind === 'chat' && (next.flow || next.method || next.sourceFile || next.message)) {
        const { discussKnowledge } = await import('../knowledge/discussion');
        if (await discussKnowledge(next)) {
          visit({ kind: 'chat' });
          requestAnimationFrame(() =>
            document.querySelector<HTMLTextAreaElement>('textarea[aria-label="对话输入"]')?.focus(),
          );
        }
        return;
      }
      visit(next);
    } catch (error) {
      toast(error instanceof Error ? error.message : '无法打开资料', undefined, 'error');
    } finally {
      preparing.current = false;
    }
  }
  return { route, navigate, knowledgeOpen: route.kind !== 'chat' };
}
