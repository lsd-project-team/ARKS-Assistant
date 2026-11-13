import { readingGraphPaths } from './data/readingDestinations.ts';
import { graphOwner, primaryWorkflowIds, selectedGraphId } from './data/graphCollections.ts';

export interface ChatRoute {
  kind: 'chat';
}
export type Route =
  | ChatRoute
  | { kind: 'graphs' }
  | ({ kind: 'graph'; slug: string } & DiagramLocation)
  | ({ kind: 'catalog'; id: string } & DiagramLocation);

export interface DiagramLocation {
  view?: string;
  signal?: string;
  section?: string;
}

export function diagramRoute(
  id: string,
  location: DiagramLocation = {},
): Extract<Route, { kind: 'graph' | 'catalog' }> {
  const owner = graphOwner(id);
  const selected = selectedGraphId(id, location.view);
  const details = {
    ...(selected !== owner ? { view: selected } : {}),
    ...(location.signal !== undefined ? { signal: location.signal } : {}),
    ...(location.section !== undefined ? { section: location.section } : {}),
  };
  return primaryWorkflowIds.has(owner)
    ? { kind: 'graph', slug: owner, ...details }
    : { kind: 'catalog', id: owner, ...details };
}

export function routeFromHash(hash = window.location.hash): Route {
  const [value, query] = hash.replace(/^#/, '').split('?');
  const params = new URLSearchParams(query);
  if (value === 'graphs' || value === 'modules' || value === 'overview') return { kind: 'graphs' };
  const [kind, id] = value.split('/');
  if ((kind === 'graph' || kind === 'catalog') && id)
    return diagramRoute(id, {
      view: params.get('view') ?? undefined,
      signal: params.get('signal') ?? undefined,
      section: params.get('section') ?? undefined,
    });
  if (kind === 'topic') {
    const destination = readingGraphPaths[id];
    return routeFromHash(typeof destination === 'string' ? destination : 'graphs');
  }
  // 历史源码链接回到功能目录，避免继续打开已删除的快照阅读页。
  if (['source-module', 'source-method', 'source-file', 'source-import'].includes(kind))
    return { kind: 'graphs' };
  return { kind: 'chat' };
}
export function routeHash(route: Route): string {
  if (route.kind === 'graph' || route.kind === 'catalog') {
    const current = diagramRoute(route.kind === 'graph' ? route.slug : route.id, route);
    const params = [
      ['view', current.view],
      ['signal', current.signal],
      ['section', current.section],
    ]
      .filter(([, value]) => value !== undefined)
      .map(([key, value]) => `${key}=${encodeURIComponent(value!)}`)
      .join('&');
    return `${current.kind}/${current.kind === 'graph' ? current.slug : current.id}${params ? '?' + params : ''}`;
  }
  return route.kind;
}
export const routeNames: Record<string, string> = {
  graphs: '全部图谱',
  graph: '流程阅读',
  catalog: '图谱阅读',
  chat: '对话',
};
