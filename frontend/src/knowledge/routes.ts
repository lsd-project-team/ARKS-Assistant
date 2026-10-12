import type { EngineeringRoute } from './engineeringTypes';

export interface ChatRoute {
  kind: 'chat';
  flow?: string;
  method?: string;
  sourceFile?: string;
  path?: string;
  start?: number;
  end?: number;
  message?: string;
}
export type Route =
  | EngineeringRoute
  | ChatRoute
  | { kind: 'overview' | 'graphs' | 'modules' }
  | { kind: 'graph'; slug: string; signal?: string }
  | { kind: 'catalog' | 'topic'; id: string };

const positiveLine = (value: string | null, fallback = 1) => {
  const line = Number(value);
  return Number.isSafeInteger(line) && line > 0 ? line : fallback;
};
export function routeFromHash(hash = window.location.hash): Route {
  const [value, query] = hash.replace(/^#/, '').split('?');
  const params = new URLSearchParams(query);
  if (value === 'graphs' || value === 'modules' || value === 'overview') return { kind: value };
  const [kind, id] = value.split('/');
  if (kind === 'graph' && id) return { kind, slug: id, signal: params.get('signal') ?? undefined };
  if (['topic', 'catalog', 'source-module', 'source-method'].includes(kind) && id)
    return { kind, id } as Route;
  if (kind === 'source-file' && id) {
    const start = positiveLine(params.get('start'));
    return { kind, id, start, end: Math.max(start, positiveLine(params.get('end'), start)) };
  }
  return { kind: 'chat' };
}
export function routeHash(route: Route): string {
  if (route.kind === 'graph')
    return `graph/${route.slug}${route.signal ? `?signal=${encodeURIComponent(route.signal)}` : ''}`;
  if (route.kind === 'source-file')
    return `source-file/${route.id}?start=${route.start ?? 1}&end=${route.end ?? route.start ?? 1}`;
  if ('id' in route) return `${route.kind}/${route.id}`;
  return route.kind === 'project-source' || route.kind === 'source-import' ? 'chat' : route.kind;
}
// 旧资料带 trunk/ 前缀，当前工作区的根目录本身就是 trunk。
export function workspacePath(path: string): string {
  return path.replaceAll('\\', '/').replace(/^trunk\//, '');
}
export const routeNames: Record<string, string> = {
  overview: '系统总览',
  graphs: '流程图谱',
  modules: '功能说明',
  topic: '功能专题',
  graph: '流程阅读',
  catalog: '图谱阅读',
  'source-module': '模块职责与协作',
  'source-method': '方法与调用',
  'source-file': '源码依据',
  chat: '对话',
};
