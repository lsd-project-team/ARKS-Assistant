export interface ChatRoute {
  kind: 'chat';
  flow?: string;
  message?: string;
}
export type Route =
  | ChatRoute
  | { kind: 'overview' | 'graphs' | 'modules' }
  | { kind: 'graph'; slug: string; signal?: string }
  | { kind: 'catalog' | 'topic'; id: string };

export function routeFromHash(hash = window.location.hash): Route {
  const [value, query] = hash.replace(/^#/, '').split('?');
  const params = new URLSearchParams(query);
  if (value === 'graphs' || value === 'modules' || value === 'overview') return { kind: value };
  const [kind, id] = value.split('/');
  if (kind === 'graph' && id) return { kind, slug: id, signal: params.get('signal') ?? undefined };
  if (['topic', 'catalog'].includes(kind) && id) return { kind, id } as Route;
  // 历史源码链接回到功能目录，避免继续打开已删除的快照阅读页。
  if (['source-module', 'source-method', 'source-file', 'source-import'].includes(kind))
    return { kind: 'modules' };
  return { kind: 'chat' };
}
export function routeHash(route: Route): string {
  if (route.kind === 'graph')
    return `graph/${route.slug}${route.signal ? `?signal=${encodeURIComponent(route.signal)}` : ''}`;
  if ('id' in route) return `${route.kind}/${route.id}`;
  return route.kind;
}
export const routeNames: Record<string, string> = {
  overview: '功能与流程',
  graphs: '全部图谱',
  modules: '功能与流程',
  topic: '功能专题',
  graph: '流程阅读',
  catalog: '图谱阅读',
  chat: '对话',
};
