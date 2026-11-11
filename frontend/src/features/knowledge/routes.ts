import { readingGraphPaths } from './data/readingDestinations.ts';

export interface ChatRoute {
  kind: 'chat';
  flow?: string;
  message?: string;
}
export type Route =
  | ChatRoute
  | { kind: 'graphs' }
  | { kind: 'graph'; slug: string; signal?: string }
  | { kind: 'catalog'; id: string; section?: string };

export function routeFromHash(hash = window.location.hash): Route {
  const [value, query] = hash.replace(/^#/, '').split('?');
  const params = new URLSearchParams(query);
  if (value === 'graphs' || value === 'modules' || value === 'overview') return { kind: 'graphs' };
  const [kind, id] = value.split('/');
  if (kind === 'graph' && id) return { kind, slug: id, signal: params.get('signal') ?? undefined };
  if (kind === 'catalog' && id)
    return { kind, id, ...(params.has('section') ? { section: params.get('section')! } : {}) };
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
  if (route.kind === 'catalog' && route.section !== undefined)
    return `catalog/${route.id}?section=${encodeURIComponent(route.section)}`;
  if (route.kind === 'graph')
    return `graph/${route.slug}${route.signal ? `?signal=${encodeURIComponent(route.signal)}` : ''}`;
  if ('id' in route) return `${route.kind}/${route.id}`;
  return route.kind;
}
export const routeNames: Record<string, string> = {
  graphs: '全部图谱',
  graph: '流程阅读',
  catalog: '图谱阅读',
  chat: '对话',
};
